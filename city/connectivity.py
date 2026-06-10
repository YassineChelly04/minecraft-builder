"""
City connectivity layer — ground, road paving, canal, and street lighting.
Returns command groups keyed by datapack build order.
"""
from __future__ import annotations

import random

from architecture.geometry import Rect, Vec3, cmd_fill, cmd_set
from architecture.texture import textured_fill
from city.model import CityPlan

ROAD_PRIMARY = "stone_bricks"
ROAD_VARIANTS = ["cracked_stone_bricks", "andesite", "gravel"]
LAMP_SPACING = 7


def build_connectivity(plan: CityPlan, palette, seed: int) -> dict[str, list[str]]:
    rng = random.Random(seed ^ 0xC17)
    g = plan.ground_y
    groups: dict[str, list[str]] = {}

    # 10 terrain — a flat ground slab under the whole city
    b = plan.bounds
    groups["10_terrain"] = [cmd_fill(Vec3(b.x1, g - 1, b.z1), Vec3(b.x2, g - 1, b.z2), "grass_block")]

    # 20 roads — textured paving at ground level
    roads: list[str] = []
    for r in plan.roads.all_rects():
        roads += textured_fill(Vec3(r.x1, g, r.z1), Vec3(r.x2, g, r.z2),
                               ROAD_PRIMARY, ROAD_VARIANTS, 0.20, rng)
    groups["20_roads"] = roads

    # 30 rail / canal
    rc: list[str] = []
    for c in plan.canal:
        rc.append(cmd_fill(Vec3(c.x1, g - 1, c.z1), Vec3(c.x2, g - 1, c.z2), "water"))
        rc.append(cmd_fill(Vec3(c.x1, g, c.z1), Vec3(c.x1, g, c.z2), palette.trim))
        rc.append(cmd_fill(Vec3(c.x2, g, c.z1), Vec3(c.x2, g, c.z2), palette.trim))
    for r in plan.rail:
        rc.append(cmd_fill(Vec3(r.x1, g, r.z1), Vec3(r.x2, g, r.z2), "gravel"))
    groups["30_rail_canal"] = rc

    # 90 lighting — lamps along road centrelines
    lamps: list[str] = []
    light = palette.light
    for r in plan.roads.all_rects():
        horizontal = r.width >= r.depth
        cz = (r.z1 + r.z2) // 2
        cx = (r.x1 + r.x2) // 2
        if horizontal:
            for x in range(r.x1, r.x2 + 1, LAMP_SPACING):
                lamps += _lamp(x, cz, g, light)
        else:
            for z in range(r.z1, r.z2 + 1, LAMP_SPACING):
                lamps += _lamp(cx, z, g, light)
    groups["90_lighting"] = lamps
    return groups


def _lamp(x: int, z: int, g: int, light: str) -> list[str]:
    state = "[hanging=false]" if "lantern" in light else ""
    return [cmd_fill(Vec3(x, g + 1, z), Vec3(x, g + 3, z), "oak_fence"),
            cmd_set(Vec3(x, g + 4, z), light, state)]
