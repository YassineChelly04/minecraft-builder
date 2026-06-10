"""
BuildingBrief — the universal input to single-building generation, plus the
adapter that bridges the existing intent dict into a brief.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Literal

import config
from architecture.geometry import Face, Rect, Vec3
from knowledge.palettes import BuildingPalette, resolve_palette


@dataclass
class BuildingBrief:
    archetype: str
    lot: Rect
    origin_y: int
    style: str
    palette: BuildingPalette
    storeys: int
    height_band: tuple[int, int]
    room_program: list[str]
    features: list[str]
    front_face: Face
    seed: int
    detail_level: Literal["kit", "llm"] = "kit"
    material_overrides: dict[str, str] = field(default_factory=dict)

    def rng(self) -> random.Random:
        return random.Random(self.seed)


def seed_from(prompt: str, origin: Vec3 | dict, salt: int = 0) -> int:
    """Build seed. `salt` is the per-run variation nonce: 0 keeps the historic
    deterministic behaviour (tests, benchmarks); the web layer sends a random
    salt per Build click so the same prompt never produces the same build twice."""
    if isinstance(origin, dict):
        origin = (origin.get("x", 0), origin.get("y", 0), origin.get("z", 0))
    else:
        origin = (origin.x, origin.y, origin.z)
    # salt==0 must reproduce the historic key byte-for-byte (benchmarks/tests)
    key = f"{prompt}|{origin}" if salt == 0 else f"{prompt}|{origin}|{salt}"
    h = hashlib.sha256(key.encode()).hexdigest()
    return int(h[:16], 16)


MAX_SIDE = 48      # max footprint side for a single building
MAX_HEIGHT = 32    # max total height for a single building

_ARCHETYPE_BY_STRUCTURE = {
    "stadium": "stadium", "arena": "stadium", "refinery": "refinery",
    "gasometer": "gasometer", "coal yard": "coal_yard", "water tower": "water_tower",
    "warehouse": "warehouse", "factory": "factory_hall", "office": "office_block",
    "rowhouse": "rowhouse_strip", "depot": "train_depot", "tower": "generic_building",
}

# Open/custom archetypes have no interior furnish/light pass, so they can be far
# larger than a watertight shell: (min_side, max_side, max_height).
_SIZE_LIMITS = {"stadium": (45, 160, 48)}


def _apply_answer_overlay(intent: dict, answers: dict) -> dict:
    """Deterministically fold the user's ticked clarify answers into the intent.
    The intent LLM also sees the answers, but a small model can ignore them —
    this overlay GUARANTEES every answer changes the build: palette/style words
    set the palette, storey counts set height, size words scale the footprint,
    and feature-ish answers land in features (the critic patches them in)."""
    import re
    from knowledge.palettes import DEFAULT_PALETTE_BY_STYLE, PALETTES

    intent = dict(intent)
    text_all = " ".join(str(v) for v in answers.values() if v).lower()
    if not text_all:
        return intent

    # palette: exact palette name first, then style keyword
    for name in PALETTES:
        if name.replace("_", " ") in text_all or name in text_all:
            intent["palette_name"] = name
            break
    else:
        for kw, name in DEFAULT_PALETTE_BY_STYLE.items():
            if kw in text_all:
                intent["palette_name"] = name
                intent.setdefault("style", kw)
                break

    # storeys / floors
    m = re.search(r"(\d+)\s*(?:floors?|storeys?|stories|levels?)", text_all)
    if m:
        size = dict(intent.get("size", {}) or {})
        size["y"] = max(int(size.get("y", 6)), 1 + int(m.group(1)) * 4)
        intent["size"] = size

    # size words scale the footprint
    scale = (0.75 if any(w in text_all for w in ("tiny", "small", "compact", "cozy"))
             else 1.35 if any(w in text_all for w in ("huge", "grand", "massive", "large", "epic"))
             else 1.0)
    if scale != 1.0:
        size = dict(intent.get("size", {}) or {})
        for ax in ("x", "z"):
            size[ax] = round(int(size.get(ax, 11)) * scale)
        intent["size"] = size

    # answers tied to feature-style questions become must-have features
    feats = list(intent.get("features", []) or [])
    for q, a in answers.items():
        if not a:
            continue
        ql = str(q).lower()
        if any(k in ql for k in ("feature", "signature", "include", "focal", "highlight")):
            feats.append(str(a))
    if feats:
        intent["features"] = feats
    return intent


def intent_to_brief(intent: dict, origin: dict, *, prompt: str = "",
                    detail_level: str = "kit", answers: dict | None = None,
                    variation: int = 0) -> BuildingBrief:
    """Bridge the legacy intent schema into a BuildingBrief. Footprint size comes
    from intent['size']; the lot is the footprint placed at the origin."""
    if answers:
        intent = _apply_answer_overlay(intent, answers)
    x, y, z = origin["x"], origin["y"], origin["z"]
    size = intent.get("size", {}) or {}

    style = str(intent.get("style", "") or "")
    structure = str(intent.get("structure_type", "house") or "house").lower()
    archetype = "generic_building"
    # structure_type match first; the raw prompt only as a fallback signal
    for source in (structure, prompt.lower()):
        match = next((arch for key, arch in _ARCHETYPE_BY_STRUCTURE.items()
                      if key in source), None)
        if match:
            archetype = match
            break

    # Clamp to engine-sane bounds. The intent model can ask for huge structures;
    # shell-based buildings stay within MAX_SIDE (the deterministic furnish/light
    # passes scale with interior area), while open archetypes (stadium) get their
    # own, larger envelope.
    min_side, max_side, max_h = _SIZE_LIMITS.get(archetype, (5, MAX_SIDE, MAX_HEIGHT))
    sx = min(max_side, max(min_side, int(size.get("x", 11))))
    sz = min(max_side, max(min_side, int(size.get("z", 9))))
    sy = min(max_h, max(4, int(size.get("y", 6))))
    lot = Rect(x, z, x + sx - 1, z + sz - 1)

    palette = resolve_palette(intent)
    storeys = 2 if (sy >= 9 or "storey" in structure or "2" in str(intent.get("notes", ""))) else 1
    room_program = list(intent.get("room_program", []) or _default_rooms(structure, sx, sz))
    seed = seed_from(prompt or intent.get("notes", "") or structure, origin, salt=variation)

    return BuildingBrief(
        archetype=archetype, lot=lot, origin_y=y, style=style, palette=palette,
        storeys=storeys, height_band=(sy, sy), room_program=room_program,
        features=list(intent.get("features", []) or []),
        front_face="N", seed=seed,
        detail_level="llm" if detail_level == "llm" else "kit",
        material_overrides=intent.get("material_overrides", {}) or {},
    )


def _default_rooms(structure: str, sx: int, sz: int) -> list[str]:
    if any(k in structure for k in ("warehouse", "factory", "depot", "hall", "barn",
                                    "stadium", "arena", "refinery", "yard")):
        return []  # non-furnished open archetypes
    area = (sx - 2) * (sz - 2)
    if area < 36:
        return ["living"]
    if area < 80:
        return ["living", "kitchen", "bedroom"]
    return ["living", "kitchen", "bedroom", "study"]
