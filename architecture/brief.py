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


def seed_from(prompt: str, origin: Vec3 | dict) -> int:
    if isinstance(origin, dict):
        origin = (origin.get("x", 0), origin.get("y", 0), origin.get("z", 0))
    else:
        origin = (origin.x, origin.y, origin.z)
    h = hashlib.sha256(f"{prompt}|{origin}".encode()).hexdigest()
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


def intent_to_brief(intent: dict, origin: dict, *, prompt: str = "",
                    detail_level: str = "kit") -> BuildingBrief:
    """Bridge the legacy intent schema into a BuildingBrief. Footprint size comes
    from intent['size']; the lot is the footprint placed at the origin."""
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
    seed = seed_from(prompt or intent.get("notes", "") or structure, origin)

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
