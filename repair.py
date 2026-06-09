"""
Command repair layer — the guarantee that every command we hand to Minecraft runs.

Small LLMs reliably fail at four things when emitting /fill and /setblock:
  1. Block IDs       — they hallucinate names like minecraft:wood_planks, glass_block.
  2. Block states    — they bolt [facing=...] onto plain cubes, which is a parse error.
  3. Volume limits   — a single /fill can exceed the 32768-block engine cap.
  4. Build bounds    — Y coordinates outside the -64..319 world range error out.

This module fixes the first three deterministically and drops the genuinely
unfixable, so a single bad token can never block an entire build. It runs AFTER
normalize_commands (which handles the common generic-name remaps) and replaces
ad-hoc sanitising with a single auditable pass that returns a report of what changed.
"""
import re
from difflib import get_close_matches

from blocks import VALID_BLOCKS
from config import MAX_FILL_VOLUME, WORLD_MIN_Y, WORLD_MAX_Y
from normalizer import _REMAP

# ── Block families that legitimately carry a [block state]. Anything else gets
#    its state stripped, because a state on a plain cube is a hard parse failure. ──
_STATEFUL_SUFFIXES = (
    "_stairs", "_slab", "_log", "_wood", "_stem", "_pillar", "_door", "_trapdoor",
    "_fence", "_fence_gate", "_wall", "_bed", "_button", "_glass_pane", "_bars",
    "_banner", "_sign", "_head", "_skull", "_candle", "_lantern", "_chain",
)
_STATEFUL_EXACT = {
    "minecraft:lantern", "minecraft:soul_lantern", "minecraft:chain", "minecraft:ladder",
    "minecraft:iron_bars", "minecraft:glass_pane", "minecraft:campfire", "minecraft:soul_campfire",
    "minecraft:chest", "minecraft:trapped_chest", "minecraft:barrel", "minecraft:furnace",
    "minecraft:blast_furnace", "minecraft:smoker", "minecraft:hopper", "minecraft:dropper",
    "minecraft:dispenser", "minecraft:observer", "minecraft:piston", "minecraft:sticky_piston",
    "minecraft:lectern", "minecraft:grindstone", "minecraft:stonecutter", "minecraft:loom",
    "minecraft:end_rod", "minecraft:vine", "minecraft:jack_o_lantern", "minecraft:quartz_pillar",
    "minecraft:purpur_pillar", "minecraft:bone_block", "minecraft:basalt", "minecraft:polished_basalt",
    "minecraft:hay_block", "minecraft:anvil", "minecraft:chipped_anvil", "minecraft:damaged_anvil",
}

# Semantic hallucinations difflib can't reach (different word, similar meaning).
_SYNONYMS = {
    "minecraft:wood_planks": "minecraft:oak_planks",
    "minecraft:wooden_planks": "minecraft:oak_planks",
    "minecraft:wood_stairs": "minecraft:oak_stairs",
    "minecraft:wooden_stairs": "minecraft:oak_stairs",
    "minecraft:wood_slab": "minecraft:oak_slab",
    "minecraft:wooden_slab": "minecraft:oak_slab",
    "minecraft:wood_fence": "minecraft:oak_fence",
    "minecraft:wooden_fence": "minecraft:oak_fence",
    "minecraft:wooden_door": "minecraft:oak_door",
    "minecraft:wood_door": "minecraft:oak_door",
    "minecraft:glass_block": "minecraft:glass",
    "minecraft:glass_window": "minecraft:glass_pane",
    "minecraft:window": "minecraft:glass_pane",
    "minecraft:stone_block": "minecraft:stone",
    "minecraft:cobblestone_block": "minecraft:cobblestone",
    "minecraft:cobble": "minecraft:cobblestone",
    "minecraft:brick": "minecraft:bricks",
    "minecraft:brick_block": "minecraft:bricks",
    "minecraft:stone_brick": "minecraft:stone_bricks",
    "minecraft:stonebrick": "minecraft:stone_bricks",
    "minecraft:torch": "minecraft:lantern",       # torch fails mid-air; lantern keeps the light
    "minecraft:wall_torch": "minecraft:lantern",
    "minecraft:lamp": "minecraft:redstone_lamp",
    "minecraft:light": "minecraft:glowstone",
    "minecraft:light_block": "minecraft:glowstone",
    "minecraft:white_glass": "minecraft:white_stained_glass",
    "minecraft:dark_wood": "minecraft:dark_oak_planks",
    "minecraft:wood": "minecraft:oak_planks",
}

# Wood/stone families where an unknown prefix can fall back to a default that exists.
_FAMILY_FALLBACK = (
    ("_planks", "minecraft:oak_planks"),
    ("_stairs", "minecraft:oak_stairs"),
    ("_slab",   "minecraft:oak_slab"),
    ("_fence",  "minecraft:oak_fence"),
    ("_door",   "minecraft:oak_door"),
    ("_trapdoor", "minecraft:oak_trapdoor"),
    ("_log",    "minecraft:oak_log"),
    ("_wood",   "minecraft:oak_wood"),
    ("_bed",    "minecraft:red_bed"),
    ("_wall",   "minecraft:cobblestone_wall"),
    ("_carpet", "minecraft:white_carpet"),
    ("_wool",   "minecraft:white_wool"),
    ("_concrete", "minecraft:white_concrete"),
    ("_terracotta", "minecraft:white_terracotta"),
)

# Fuzzy index: bare name (no prefix) -> full id, for difflib near-miss matching.
_BARE_INDEX = {b[len("minecraft:"):]: b for b in VALID_BLOCKS}
_FUZZY_CUTOFF = 0.84

_STATE_RE = re.compile(r"^(?P<base>[^\[]+)(?P<state>\[.*\])?$")


def repair_commands(commands: list[str]) -> tuple[list[str], list[str]]:
    """Return (clean_commands, report). Every clean command is guaranteed valid."""
    out: list[str] = []
    report: list[str] = []

    for cmd in commands:
        parts = cmd.strip().split()
        if not parts:
            continue
        if parts[0] == "/fill":
            fixed = _repair_fill(parts, report)
        elif parts[0] == "/setblock":
            fixed = _repair_setblock(parts, report)
        else:
            report.append(f"dropped (unknown command): {cmd}")
            continue
        out.extend(fixed)

    return out, report


# ── /fill ────────────────────────────────────────────────────────────────────

def _repair_fill(parts: list[str], report: list[str]) -> list[str]:
    raw = " ".join(parts)
    if len(parts) < 8:
        report.append(f"dropped (incomplete /fill): {raw}")
        return []

    coords = _ints(parts[1:7])
    if coords is None:
        report.append(f"dropped (bad coords): {raw}")
        return []
    x1, y1, z1, x2, y2, z2 = coords

    if not _y_in_range(y1) or not _y_in_range(y2):
        report.append(f"dropped (Y out of -64..319): {raw}")
        return []

    block = _correct_block(parts[7], report)
    if block is None:
        report.append(f"dropped (unfixable block '{parts[7]}'): {raw}")
        return []

    # Optional tail: a "replace <block>" filter also needs a valid block id.
    tail = list(parts[8:])
    if len(tail) >= 2 and tail[0] == "replace":
        filt = _correct_block(tail[1], report)
        if filt is None:
            report.append(f"dropped (unfixable replace filter '{tail[1]}'): {raw}")
            return []
        tail[1] = filt
    tail_str = (" " + " ".join(tail)) if tail else ""

    fills = _split_volume(x1, y1, z1, x2, y2, z2)
    if len(fills) > 1:
        report.append(f"split oversized /fill into {len(fills)} chunks: {raw}")

    return [f"/fill {a} {b} {c} {d} {e} {f} {block}{tail_str}"
            for (a, b, c, d, e, f) in fills]


# ── /setblock ──────────────────────────────────────────────────────────────────

def _repair_setblock(parts: list[str], report: list[str]) -> list[str]:
    raw = " ".join(parts)
    if len(parts) < 5:
        report.append(f"dropped (incomplete /setblock): {raw}")
        return []

    coords = _ints(parts[1:4])
    if coords is None:
        report.append(f"dropped (bad coords): {raw}")
        return []
    x, y, z = coords

    if not _y_in_range(y):
        report.append(f"dropped (Y out of -64..319): {raw}")
        return []

    block = _correct_block(parts[4], report)
    if block is None:
        report.append(f"dropped (unfixable block '{parts[4]}'): {raw}")
        return []

    tail = " ".join(parts[5:])
    tail_str = (" " + tail) if tail else ""
    return [f"/setblock {x} {y} {z} {block}{tail_str}"]


# ── Block-name correction ──────────────────────────────────────────────────────

def _correct_block(token: str, report: list[str]):
    """Return a valid 'minecraft:...' id (with a kept/stripped state) or None."""
    m = _STATE_RE.match(token.strip())
    if not m:
        return None
    base = m.group("base")
    state = m.group("state") or ""

    if ":" not in base:
        base = "minecraft:" + base

    fixed = _resolve_base(base)
    if fixed is None:
        return None

    if fixed != base:
        report.append(f"block '{base}' -> '{fixed}'")

    # Keep the state only for blocks that legitimately take one.
    if state and not _is_stateful(fixed):
        report.append(f"stripped invalid state from {fixed}: {state}")
        state = ""

    return fixed + state


def _resolve_base(base: str):
    if base in VALID_BLOCKS:
        return base
    if base in _REMAP:
        return _REMAP[base]
    if base in _SYNONYMS:
        return _SYNONYMS[base]

    # Unknown wood/colour prefix on a known family -> default member of that family.
    for suffix, fallback in _FAMILY_FALLBACK:
        if base.endswith(suffix):
            return fallback

    # Last resort: fuzzy match a near-miss spelling.
    bare = base[len("minecraft:"):]
    match = get_close_matches(bare, _BARE_INDEX.keys(), n=1, cutoff=_FUZZY_CUTOFF)
    if match:
        return _BARE_INDEX[match[0]]

    return None


def _is_stateful(block_id: str) -> bool:
    if block_id in _STATEFUL_EXACT:
        return True
    return any(block_id.endswith(s) for s in _STATEFUL_SUFFIXES)


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _ints(tokens):
    try:
        return [int(t) for t in tokens]
    except ValueError:
        return None


def _y_in_range(y: int) -> bool:
    return WORLD_MIN_Y <= y <= WORLD_MAX_Y


def _split_volume(x1, y1, z1, x2, y2, z2):
    """Split a fill box into chunks each within MAX_FILL_VOLUME, along the longest axis."""
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    z1, z2 = sorted((z1, z2))

    dx, dy, dz = x2 - x1 + 1, y2 - y1 + 1, z2 - z1 + 1
    if dx * dy * dz <= MAX_FILL_VOLUME:
        return [(x1, y1, z1, x2, y2, z2)]

    # Cut along the longest axis into the fewest pieces that fit the volume cap.
    axis = max((dx, "x"), (dy, "y"), (dz, "z"))[1]
    length = {"x": dx, "y": dy, "z": dz}[axis]
    other = (dx * dy * dz) // length
    chunk = max(1, MAX_FILL_VOLUME // other)

    result = []
    start = {"x": x1, "y": y1, "z": z1}[axis]
    end = {"x": x2, "y": y2, "z": z2}[axis]
    s = start
    while s <= end:
        e = min(s + chunk - 1, end)
        if axis == "x":
            result += _split_volume(s, y1, z1, e, y2, z2)
        elif axis == "y":
            result += _split_volume(x1, s, z1, x2, e, z2)
        else:
            result += _split_volume(x1, y1, s, x2, y2, e)
        s = e + 1
    return result
