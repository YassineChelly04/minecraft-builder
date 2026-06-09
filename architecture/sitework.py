"""
Site work — cheap, high-effect surroundings: foundation skirt, entry path,
corner lanterns, garden strip. All deterministic and seeded.
"""
from __future__ import annotations

import random

import config
from architecture.geometry import OUTWARD, Opening, Rect, Vec3, cmd_fill, cmd_set
from architecture.texture import textured_fill
from knowledge.blocks_registry import resolve


def foundation_skirt(rect: Rect, floor_y: int, palette) -> list[str]:
    """One course of trim around the base, one below the floor."""
    y = floor_y - 1
    return [cmd_fill(Vec3(rect.x1 - 1, y, rect.z1 - 1),
                     Vec3(rect.x2 + 1, y, rect.z2 + 1), palette.trim)]


def entry_path(door: Opening, floor_y: int, palette, rng: random.Random,
               length: int = 6) -> list[str]:
    ox, oz = OUTWARD[door.face]
    cmds: list[str] = []
    primary = "gravel"
    variants = ["cobblestone", "stone"]
    for step in range(1, length + 1):
        cx, cz = door.x + ox * step, door.z + oz * step
        if door.face in ("N", "S"):
            a, b = Vec3(cx - 1, floor_y, cz), Vec3(cx + 1, floor_y, cz)
        else:
            a, b = Vec3(cx, floor_y, cz - 1), Vec3(cx, floor_y, cz + 1)
        cmds += textured_fill(a, b, primary, variants, 0.30, rng)
    # lantern-on-fence pair at the path end
    end_x, end_z = door.x + ox * length, door.z + oz * length
    fence = _fence_for(palette)
    for dx, dz in (((-2, 0), (2, 0)) if door.face in ("N", "S") else ((0, -2), (0, 2))):
        px, pz = end_x + dx, end_z + dz
        cmds.append(cmd_fill(Vec3(px, floor_y + 1, pz), Vec3(px, floor_y + 2, pz), fence))
        cmds.append(cmd_set(Vec3(px, floor_y + 3, pz), palette.light, "[hanging=false]"))
    return cmds


def garden_strip(rect: Rect, floor_y: int, door: Opening, palette,
                 rng: random.Random) -> list[str]:
    """A row of clutter along the front wall (version-gated 1.21.5 flora)."""
    valid = resolve(config.TARGET_MC_VERSION)
    flora = [b.replace("minecraft:", "") for b in
             ("minecraft:bush", "minecraft:wildflowers", "minecraft:leaf_litter")
             if b in valid] or ["oak_leaves"]
    cmds: list[str] = []
    front = rect.edges()[door.face]
    ax, az, bx, bz = front
    ox, oz = OUTWARD[door.face]
    for x in range(min(ax, bx), max(ax, bx) + 1):
        z = az
        if abs(x - door.x) <= 1:
            continue
        if rng.random() < 0.5:
            cmds.append(cmd_set(Vec3(x + ox, floor_y + 1, z + oz), rng.choice(flora)))
    return cmds


def _fence_for(palette) -> str:
    for wood in ("spruce", "dark_oak", "oak", "birch"):
        if wood in palette.trim or wood in palette.dominant:
            return f"{wood}_fence"
    return "oak_fence"
