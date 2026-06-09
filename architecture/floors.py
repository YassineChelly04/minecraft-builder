"""
Floors, storey bands, and staircases — pure geometry, never an LLM.
"""
from __future__ import annotations

import random

from architecture.geometry import Rect, Vec3, cmd_fill, cmd_set

STOREY_H = 5  # blocks of vertical space per storey (floor to ceiling)


def storey_bands(floor_y: int, total_height: int, storeys: int) -> list[tuple[int, int]]:
    """(floor_y, ceil_y) per storey. ceil_y is the underside of the slab/roof above."""
    if storeys <= 1:
        return [(floor_y, floor_y + total_height - 1)]
    bands = []
    y = floor_y
    for _ in range(storeys):
        bands.append((y, y + STOREY_H - 1))
        y += STOREY_H
    return bands


def floor_slab(rect: Rect, y: int, palette) -> list[str]:
    """Solid floor + a 1-block contrasting border trim around the inside edge."""
    cmds = [cmd_fill(Vec3(rect.x1, y, rect.z1), Vec3(rect.x2, y, rect.z2), palette.floor or palette.dominant)]
    inner = rect.inset(1)
    if inner.width >= 1 and inner.depth >= 1:
        for (ax, az, bx, bz) in inner.edges().values():
            cmds.append(cmd_fill(Vec3(ax, y, az), Vec3(bx, y, bz), palette.trim))
    return cmds


def intermediate_slab(rect: Rect, y: int, palette, stair_hole: Rect | None) -> list[str]:
    """A storey-dividing slab with an optional cut-out for a staircase."""
    cmds = [cmd_fill(Vec3(rect.x1 + 1, y, rect.z1 + 1),
                     Vec3(rect.x2 - 1, y, rect.z2 - 1), palette.floor or palette.dominant)]
    if stair_hole:
        cmds.append(cmd_fill(Vec3(stair_hole.x1, y, stair_hole.z1),
                             Vec3(stair_hole.x2, y, stair_hole.z2), "air"))
    return cmds


def straight_staircase(rect: Rect, floor_y: int, top_y: int, palette,
                       rng: random.Random) -> tuple[list[str], Rect]:
    """A straight run of stairs up a wall, with a 1×3 headroom hole in the slab
    above. Returns (cmds, stair_hole_rect)."""
    cmds: list[str] = []
    inner = rect.inset(1)
    rise = top_y - floor_y
    if rise < 2 or inner.width < 3:
        return cmds, Rect(inner.x1, inner.z1, inner.x1 + 1, inner.z1 + 2)
    x = inner.x1                       # run along the west wall, ascending +z
    z0 = inner.z1
    for step in range(rise):
        z = z0 + step
        if z > inner.z2:
            break
        cmds.append(cmd_set(Vec3(x, floor_y + step, z), palette.roof, "[facing=south,half=bottom]"))
    hole = Rect(x, z0, x + 1, min(z0 + rise, inner.z2))
    return cmds, hole
