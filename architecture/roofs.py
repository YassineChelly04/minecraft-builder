"""
Roof library — one function per type, chosen by style. The decorative roof is
built ABOVE the watertight enclosing slab that shell2 already placed at
roof_base_y, so a complex roof can never break watertightness.

Overhang (extend 1–2 past the walls) is non-negotiable on gable/pagoda — it is the
#1 visual difference between amateur and pro roofs.
"""
from __future__ import annotations

import random

from architecture.geometry import Rect, Vec3, cmd_fill, cmd_set

ROOF_BY_STYLE = {
    "medieval": "gable", "cottage": "gable", "rustic": "gable", "viking": "gable",
    "modern": "flat_parapet", "industrial": "sawtooth", "warehouse": "flat_parapet",
    "office": "flat_parapet", "castle": "crenellated", "fortress": "crenellated",
    "japanese": "pagoda", "asian": "pagoda",
    "church": "dome", "mosque": "dome",
    "tower": "spire", "wizard": "spire", "fantasy": "spire",
    "factory": "sawtooth",
}


def roof_kind_for(style: str, structure: str = "") -> str:
    tag = f"{style} {structure}".lower()
    for kw, kind in ROOF_BY_STYLE.items():
        if kw in tag:
            return kind
    return "gable"


def build_roof(kind: str, rect: Rect, roof_base_y: int, palette, rng: random.Random
               ) -> list[str]:
    fn = {
        "gable": _gable, "flat_parapet": _flat_parapet, "crenellated": _crenellated,
        "pagoda": _pagoda, "dome": _dome, "spire": _spire, "sawtooth": _sawtooth,
    }.get(kind, _gable)
    return fn(rect, roof_base_y, palette, rng)


def _gable(rect: Rect, y0: int, palette, rng) -> list[str]:
    """Ridge along X, slopes down in Z, 1-block overhang on all edges."""
    cmds: list[str] = []
    stair, solid, trim = palette.roof, palette.roof_solid, palette.trim
    x1, x2 = rect.x1 - 1, rect.x2 + 1          # overhang in X
    half = (rect.depth + 1) // 2
    for h in range(half + 1):
        y = y0 + h
        zn = rect.z1 - 1 + h
        zf = rect.z2 + 1 - h
        if zn > zf:
            break
        if zn == zf:
            cmds.append(cmd_fill(Vec3(x1, y, zn), Vec3(x2, y, zn), solid))  # ridge
        else:
            cmds.append(cmd_fill(Vec3(x1, y, zn), Vec3(x2, y, zn), stair, "[facing=south,half=bottom]"))
            cmds.append(cmd_fill(Vec3(x1, y, zf), Vec3(x2, y, zf), stair, "[facing=north,half=bottom]"))
            # gable-end chevron (close the triangles so they're not see-through)
            cmds.append(cmd_fill(Vec3(x1, y, zn), Vec3(x1, y, zf), trim))
            cmds.append(cmd_fill(Vec3(x2, y, zn), Vec3(x2, y, zf), trim))
    return cmds


def _flat_parapet(rect: Rect, y0: int, palette, rng) -> list[str]:
    """Slab field + 1-high trim ring + outward upside-down-stair lip."""
    cmds: list[str] = []
    solid, trim, stair = palette.roof_solid, palette.trim, palette.roof
    cmds.append(cmd_fill(Vec3(rect.x1, y0, rect.z1), Vec3(rect.x2, y0, rect.z2), solid))
    p = y0 + 1
    for (ax, az, bx, bz) in rect.edges().values():
        cmds.append(cmd_fill(Vec3(ax, p, az), Vec3(bx, p, bz), trim))
    # outward lip
    for face, facing in (("N", "south"), ("S", "north"), ("E", "west"), ("W", "east")):
        ax, az, bx, bz = rect.edges()[face]
        ox = -1 if face == "E" else 1 if face == "W" else 0
        oz = -1 if face == "S" else 1 if face == "N" else 0
        cmds.append(cmd_fill(Vec3(ax + (0 if face in "NS" else (1 if face == "E" else -1)), y0, az),
                             Vec3(bx + (0 if face in "NS" else (1 if face == "E" else -1)), y0, bz),
                             stair, f"[facing={facing},half=top]"))
    return cmds


def _crenellated(rect: Rect, y0: int, palette, rng) -> list[str]:
    """Parapet with alternating merlons — place merlons only, never air."""
    cmds: list[str] = []
    solid, trim = palette.roof_solid, palette.trim
    cmds.append(cmd_fill(Vec3(rect.x1, y0, rect.z1), Vec3(rect.x2, y0, rect.z2), solid))
    p = y0 + 1
    peri = []
    for x in range(rect.x1, rect.x2 + 1):
        peri += [(x, rect.z1), (x, rect.z2)]
    for z in range(rect.z1 + 1, rect.z2):
        peri += [(rect.x1, z), (rect.x2, z)]
    for i, (x, z) in enumerate(sorted(set(peri))):
        if i % 2 == 0:
            cmds.append(cmd_set(Vec3(x, p, z), trim))
    return cmds


def _pagoda(rect: Rect, y0: int, palette, rng) -> list[str]:
    """2–3 stacked flared gable tiers."""
    cmds: list[str] = []
    tiers = 2 if rect.depth < 12 else 3
    r = rect
    y = y0
    for _ in range(tiers):
        cmds += _gable(r, y, palette, rng)
        shrink = 2
        r = Rect(r.x1 + shrink, r.z1 + shrink, r.x2 - shrink, r.z2 - shrink)
        if r.width < 3 or r.depth < 3:
            break
        y += (r.depth + 1) // 2 + 1
    return cmds


def _dome(rect: Rect, y0: int, palette, rng) -> list[str]:
    """Concentric rings via circle equation, slab smoothing."""
    cmds: list[str] = []
    solid, slab = palette.roof_solid, palette.roof
    cx, cz = rect.center()
    radius = min(rect.width, rect.depth) // 2
    for h in range(radius + 1):
        # ring radius shrinks following a quarter circle
        rr = int((radius ** 2 - h ** 2) ** 0.5)
        if rr < 0:
            break
        y = y0 + h
        for x in range(cx - rr, cx + rr + 1):
            for z in range(cz - rr, cz + rr + 1):
                d = ((x - cx) ** 2 + (z - cz) ** 2) ** 0.5
                if rr - 0.6 <= d <= rr + 0.4:
                    cmds.append(cmd_set(Vec3(x, y, z), solid))
    cmds.append(cmd_set(Vec3(cx, y0 + radius + 1, cz), palette.light))
    return cmds


def _spire(rect: Rect, y0: int, palette, rng) -> list[str]:
    """Footprint −1 per side per level until 1×1, then a point."""
    cmds: list[str] = []
    solid, stair = palette.roof_solid, palette.roof
    r = rect
    y = y0
    while r.width >= 1 and r.depth >= 1:
        cmds.append(cmd_fill(Vec3(r.x1, y, r.z1), Vec3(r.x2, y, r.z2), solid))
        if r.width <= 1 and r.depth <= 1:
            break
        r = Rect(r.x1 + 1, r.z1 + 1, r.x2 - 1, r.z2 - 1)
        y += 1
    cmds.append(cmd_set(Vec3(r.x1, y + 1, r.z1), palette.light))
    return cmds


def _sawtooth(rect: Rect, y0: int, palette, rng) -> list[str]:
    """Repeating asymmetric teeth: vertical glass north face + sloped stair south
    face, period ~5. Classic factory clerestory roof."""
    cmds: list[str] = []
    stair, solid, glass = palette.roof, palette.roof_solid, palette.glass
    cmds.append(cmd_fill(Vec3(rect.x1, y0, rect.z1), Vec3(rect.x2, y0, rect.z2), solid))
    period = 5
    z = rect.z1
    while z + period - 1 <= rect.z2:
        # vertical clerestory (glass) at the north edge of the tooth
        cmds.append(cmd_fill(Vec3(rect.x1, y0 + 1, z), Vec3(rect.x2, y0 + 2, z), glass))
        # sloped stairs descending to the south
        for k in range(1, period):
            yy = y0 + max(1, 3 - (k * 3) // period)
            cmds.append(cmd_fill(Vec3(rect.x1, yy, z + k), Vec3(rect.x2, yy, z + k),
                                 stair, "[facing=north,half=bottom]"))
        z += period
    return cmds
