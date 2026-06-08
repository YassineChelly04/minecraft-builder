"""
Maps generic block names that LLMs hallucinate to real Minecraft Java Edition block IDs.
Applied before validation so bad generic names don't fail the whole build.
"""

_REMAP = {
    "minecraft:bed":            "minecraft:red_bed",
    "minecraft:fence":          "minecraft:oak_fence",
    "minecraft:door":           "minecraft:oak_door",
    "minecraft:trapdoor":       "minecraft:oak_trapdoor",
    "minecraft:planks":         "minecraft:oak_planks",
    "minecraft:log":            "minecraft:oak_log",
    "minecraft:wood":           "minecraft:oak_wood",
    "minecraft:stairs":         "minecraft:oak_stairs",
    "minecraft:slab":           "minecraft:oak_slab",
    "minecraft:pressure_plate": "minecraft:oak_pressure_plate",
    "minecraft:button":         "minecraft:oak_button",
    "minecraft:sign":           "minecraft:oak_sign",
    "minecraft:wall_sign":      "minecraft:oak_wall_sign",
    "minecraft:boat":           "minecraft:oak_boat",
    "minecraft:carpet":         "minecraft:white_carpet",
    "minecraft:concrete":       "minecraft:white_concrete",
    "minecraft:terracotta":     "minecraft:white_terracotta",
    "minecraft:glazed_terracotta": "minecraft:white_glazed_terracotta",
    "minecraft:stained_glass":  "minecraft:white_stained_glass",
    "minecraft:stained_glass_pane": "minecraft:white_stained_glass_pane",
    "minecraft:wool":           "minecraft:white_wool",
    "minecraft:shulker_box":    "minecraft:white_shulker_box",
    "minecraft:banner":         "minecraft:white_banner",
    "minecraft:wall_banner":    "minecraft:white_wall_banner",
    "minecraft:candle":         "minecraft:white_candle",
    "minecraft:wall":           "minecraft:cobblestone_wall",
    "minecraft:sapling":        "minecraft:oak_sapling",
    "minecraft:leaves":         "minecraft:oak_leaves",
}


def normalize_commands(commands: list[str]) -> list[str]:
    result = []
    for cmd in commands:
        parts = cmd.split()
        normalized = [_remap_part(p) for p in parts]
        result.append(" ".join(normalized))
    return sanitize_commands(result)


def sanitize_commands(commands: list[str]) -> list[str]:
    """Drop structurally broken commands so they never reach the validator."""
    kept = []
    for cmd in commands:
        parts = cmd.strip().split()
        if not parts:
            continue
        if parts[0] == "/fill" and len(parts) >= 8:
            if _block_ok(parts[7]):
                kept.append(cmd)
        elif parts[0] == "/setblock" and len(parts) >= 5:
            if _block_ok(parts[4]):
                kept.append(cmd)
    return kept


def _block_ok(token: str) -> bool:
    """Block name must have something after 'minecraft:'."""
    base = token.split("[")[0]
    return base != "minecraft:" and len(base) > len("minecraft:")


# ── Fill merger ────────────────────────────────────────────────────────────────

def merge_fills(commands: list[str]) -> list[str]:
    """
    Collapse adjacent /fill commands with the same block into one.
    Handles the common LLM pattern of generating N row-by-row fills
    that could be expressed as a single volumetric fill.
    """
    fills, others = _parse_fills(commands)

    changed = True
    while changed:
        changed = False
        merged: list[tuple] = []
        used: set[int] = set()

        for i in range(len(fills)):
            if i in used:
                continue
            for j in range(i + 1, len(fills)):
                if j in used:
                    continue
                result = _try_merge(fills[i], fills[j])
                if result:
                    merged.append(result)
                    used.add(i)
                    used.add(j)
                    changed = True
                    break
            if i not in used:
                merged.append(fills[i])

        fills = merged

    reconstructed = [
        f"/fill {x1} {y1} {z1} {x2} {y2} {z2} {block}"
        for x1, y1, z1, x2, y2, z2, block in fills
    ]
    return reconstructed + others


def _parse_fills(commands: list[str]) -> tuple[list[tuple], list[str]]:
    fills, others = [], []
    for cmd in commands:
        parts = cmd.strip().split()
        if parts[0] == "/fill" and len(parts) >= 8:
            try:
                x1, y1, z1 = int(parts[1]), int(parts[2]), int(parts[3])
                x2, y2, z2 = int(parts[4]), int(parts[5]), int(parts[6])
                block = parts[7]
                fills.append((
                    min(x1, x2), min(y1, y2), min(z1, z2),
                    max(x1, x2), max(y1, y2), max(z1, z2),
                    block,
                ))
                continue
            except (ValueError, IndexError):
                pass
        others.append(cmd)
    return fills, others


def _try_merge(a: tuple, b: tuple):
    """Return merged fill if two fills share 2 axes and are adjacent on the 3rd."""
    ax1, ay1, az1, ax2, ay2, az2, block = a
    bx1, by1, bz1, bx2, by2, bz2, _   = b
    if block != _:
        return None

    # X-axis merge: same Y and Z, adjacent X
    if ay1 == by1 and ay2 == by2 and az1 == bz1 and az2 == bz2:
        if ax2 + 1 == bx1 or bx2 + 1 == ax1:
            return (min(ax1, bx1), ay1, az1, max(ax2, bx2), ay2, az2, block)

    # Y-axis merge: same X and Z, adjacent Y
    if ax1 == bx1 and ax2 == bx2 and az1 == bz1 and az2 == bz2:
        if ay2 + 1 == by1 or by2 + 1 == ay1:
            return (ax1, min(ay1, by1), az1, ax2, max(ay2, by2), az2, block)

    # Z-axis merge: same X and Y, adjacent Z
    if ax1 == bx1 and ax2 == bx2 and ay1 == by1 and ay2 == by2:
        if az2 + 1 == bz1 or bz2 + 1 == az1:
            return (ax1, ay1, min(az1, bz1), ax2, ay2, max(az2, bz2), block)

    return None


def _remap_part(token: str) -> str:
    base = token.split("[")[0]
    if base in _REMAP:
        suffix = token[len(base):]
        return _REMAP[base] + suffix
    return token
