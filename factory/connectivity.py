"""
Factory site works — everything between the buildings: ground slab, perimeter
security fence + gate, spine + gate road, conveyor/pipe bridges along the value
stream, rail spur, parking bays, and yard lighting. Command groups are keyed by
datapack build order.
"""
from __future__ import annotations

import random

from architecture.geometry import Rect, Vec3, cmd_fill, cmd_set
from architecture.texture import textured_fill
from factory.model import FactoryPlan

ROAD_PRIMARY = "stone_bricks"
ROAD_VARIANTS = ["cracked_stone_bricks", "andesite", "gravel"]
LAMP_SPACING = 9


def build_siteworks(plan: FactoryPlan, palette, seed: int) -> dict[str, list[str]]:
    rng = random.Random(seed ^ 0xFAC7)
    g = plan.ground_y
    b = plan.bounds
    groups: dict[str, list[str]] = {}

    # 10 terrain — site slab: grass verge with a hardstand core
    groups["10_terrain"] = [
        cmd_fill(Vec3(b.x1, g - 1, b.z1), Vec3(b.x2, g - 1, b.z2), "grass_block"),
        cmd_fill(Vec3(b.x1 + 1, g - 1, b.z1 + 1), Vec3(b.x2 - 1, g - 1, b.z2 - 1), "coarse_dirt"),
    ]

    # 20 roads — spine + gate stub, textured paving
    roads: list[str] = []
    for r in (plan.spine, plan.front_road):
        if r:
            roads += textured_fill(Vec3(r.x1, g, r.z1), Vec3(r.x2, g, r.z2),
                                   ROAD_PRIMARY, ROAD_VARIANTS, 0.18, rng)
    # parking: hardstand + white bay stripes
    if plan.parking:
        p = plan.parking
        roads.append(cmd_fill(Vec3(p.x1, g, p.z1), Vec3(p.x2, g, p.z2), "smooth_stone"))
        for x in range(p.x1 + 2, p.x2 - 1, 4):
            roads.append(cmd_fill(Vec3(x, g, p.z1 + 1), Vec3(x, g, p.z2 - 1), "white_concrete"))
    groups["20_roads"] = roads

    # 30 rail — freight spur on a gravel bed, buffer stop at the west end
    rail: list[str] = []
    for r in plan.rail:
        rail.append(cmd_fill(Vec3(r.x1, g, r.z1), Vec3(r.x2, g, r.z2), "gravel"))
        cz = (r.z1 + r.z2) // 2
        rail.append(cmd_fill(Vec3(r.x1, g + 1, cz), Vec3(r.x2, g + 1, cz),
                             "rail", "[shape=east_west]"))
        rail.append(cmd_set(Vec3(r.x1, g + 1, cz), "iron_block"))
    groups["30_rail_canal"] = rail

    # 80 links — elevated conveyor/pipe galleries joining consecutive stages
    links: list[str] = []
    for rect, lift in plan.links:
        y = g + lift
        cz = (rect.z1 + rect.z2) // 2
        if plan.link_kind == "pipe":
            for py in (y, y + 1):   # twin pipe runs on support frames
                links.append(cmd_fill(Vec3(rect.x1, py, cz), Vec3(rect.x2, py, cz), "iron_bars"))
        else:                       # enclosed conveyor gallery
            links.append(cmd_fill(Vec3(rect.x1, y, cz), Vec3(rect.x2, y, cz), "smooth_stone"))
            links.append(cmd_fill(Vec3(rect.x1, y + 1, cz), Vec3(rect.x2, y + 1, cz),
                                  palette.glass))
            links.append(cmd_fill(Vec3(rect.x1, y + 2, cz), Vec3(rect.x2, y + 2, cz),
                                  palette.trim))
        for x in range(rect.x1 + 2, rect.x2 - 1, 6):   # support legs
            links.append(cmd_fill(Vec3(x, g + 1, cz), Vec3(x, y - 1, cz), palette.trim))
    groups["80_connectivity"] = links

    # 85 fence — security wall: stone base + iron bars, opening at the gate
    fence: list[str] = []
    gate_x = plan.gate.x if plan.gate else (b.x1 + b.x2) // 2
    for (x1, z1, x2, z2) in ((b.x1, b.z1, b.x2, b.z1), (b.x1, b.z2, b.x2, b.z2),
                             (b.x1, b.z1, b.x1, b.z2), (b.x2, b.z1, b.x2, b.z2)):
        fence.append(cmd_fill(Vec3(x1, g + 1, z1), Vec3(x2, g + 1, z2), palette.trim))
        fence.append(cmd_fill(Vec3(x1, g + 2, z1), Vec3(x2, g + 3, z2), "iron_bars"))
    # main gate: carve the south fence, post lights either side
    fence.append(cmd_fill(Vec3(gate_x - 3, g + 1, b.z2), Vec3(gate_x + 3, g + 3, b.z2), "air"))
    for px in (gate_x - 4, gate_x + 4):
        fence.append(cmd_fill(Vec3(px, g + 1, b.z2), Vec3(px, g + 4, b.z2), palette.trim))
        fence.append(cmd_set(Vec3(px, g + 5, b.z2), palette.light,
                             "[hanging=false]" if "lantern" in palette.light else ""))
    groups["85_fence"] = fence

    # 90 lighting — yard masts along the spine road
    lamps: list[str] = []
    if plan.spine:
        cz = (plan.spine.z1 + plan.spine.z2) // 2
        for x in range(plan.spine.x1 + 2, plan.spine.x2, LAMP_SPACING):
            lamps.append(cmd_fill(Vec3(x, g + 1, cz), Vec3(x, g + 4, cz), "oak_fence"))
            lamps.append(cmd_set(Vec3(x, g + 5, cz), palette.light,
                                 "[hanging=false]" if "lantern" in palette.light else ""))
    groups["90_lighting"] = lamps
    return groups
