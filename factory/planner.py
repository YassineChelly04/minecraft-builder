"""
Factory planner — deterministic, seeded. Lays the site out the way industry
does (see industries.py): straight-through value stream west→east in a process
band, utilities in a parallel band behind it (with the rail spur between them),
offices + guardhouse + parking on the front apron by the gate, perimeter fence.

         +────────────────────── fence ──────────────────────+
         |  support band: power, water, cooling, tanks        |
         |  ───────────── rail spur (if industry.rail) ────── |
         |  process band: stage0 → stage1 → stage2 → …        |
         |  ══════════════════ spine road ═══════════════════ |
         |  front band: office HQ · gate+guardhouse · parking |
         +──────────────────── fence (gate) ──────────────────+
"""
from __future__ import annotations

import random

import config
from architecture.geometry import Rect, Vec3
from factory.industries import INDUSTRIES, MAX_SIDE_BY_ARCHETYPE
from factory.model import FactoryBrief, FactoryPlan, StagePlacement

ROAD_W = 5
FENCE_MARGIN = 2     # clear strip just inside the fence
STAGE_GAP = 6        # gap between process stages (room for conveyor bridges)
FRONT_DEPTH = 14
SUPPORT_DEPTH = 14
RAIL_DEPTH = 3

# (lo, hi) height bands per archetype — silhouettes that read as their industry.
HEIGHTS = {
    "assembly_hangar": (16, 20), "press_shop": (12, 14), "factory_hall": (10, 12),
    "paint_shop": (9, 11), "clean_hall": (8, 10), "assembly_hall": (9, 11),
    "rolling_mill": (10, 12), "brewhouse": (10, 12), "silo_battery": (12, 16),
    "fermentation_cellar": (8, 9), "blast_furnace": (14, 18),
    "cleanroom_fab": (12, 15), "high_bay_warehouse": (14, 18), "warehouse": (8, 10),
    "refinery": (10, 12), "coal_yard": (6, 6), "apron": (4, 4), "tank_farm": (6, 7),
    "power_station": (10, 12), "water_tower": (10, 12), "office_block": (12, 16),
    "cooling_tower": (12, 16), "guardhouse": (4, 4),
}

# Fixed footprints for the support band / front band buildings.
SUPPORT_SIZES = {
    "power_station": (18, 11), "water_tower": (9, 9), "tank_farm": (16, 11),
    "office_block": (13, 10), "cooling_tower": (12, 12),
}


def _band(lo: int, hi: int, rng: random.Random) -> tuple[int, int]:
    h = rng.randint(lo, hi)
    return (h, h)


def plan_factory(brief: FactoryBrief, origin: dict, *, seed: int) -> FactoryPlan:
    rng = random.Random(seed)
    template = INDUSTRIES.get(brief.industry, INDUSTRIES["generic"])

    length = config.FACTORY_SIZES.get(brief.size_class, 180)
    depth = int(length * 0.62)
    ox, oy, oz = origin["x"], origin["y"], origin["z"]
    bounds = Rect(ox, oz, ox + length - 1, oz + depth - 1)
    plan = FactoryPlan(bounds=bounds, ground_y=oy, industry=brief.industry,
                       link_kind=template.link_kind)

    # ── horizontal bands, north → south ──────────────────────────────────────
    support_z1 = bounds.z1 + FENCE_MARGIN
    support_z2 = support_z1 + SUPPORT_DEPTH - 1
    rail_z1 = support_z2 + 1
    rail_z2 = rail_z1 + (RAIL_DEPTH - 1 if template.rail else -1)
    front_z2 = bounds.z2 - FENCE_MARGIN
    front_z1 = front_z2 - FRONT_DEPTH + 1
    spine_z2 = front_z1 - 1
    spine_z1 = spine_z2 - ROAD_W + 1
    process_z1 = rail_z2 + 2
    process_z2 = spine_z1 - 2

    plan.spine = Rect(bounds.x1 + FENCE_MARGIN, spine_z1,
                      bounds.x2 - FENCE_MARGIN, spine_z2)
    if template.rail:
        plan.rail = [Rect(bounds.x1 + FENCE_MARGIN, rail_z1, bounds.x2 - 1, rail_z2)]

    # ── process stages along the value stream, west → east ───────────────────
    flow = list(template.flow)
    x_lo, x_hi = bounds.x1 + FENCE_MARGIN + 1, bounds.x2 - FENCE_MARGIN - 1
    usable = (x_hi - x_lo + 1) - STAGE_GAP * (len(flow) - 1)
    total_w = sum(w for _, _, w in flow) or 1.0
    band_depth = process_z2 - process_z1 + 1

    x = x_lo
    for i, (stage, archetype, weight) in enumerate(flow):
        w = max(10, int(usable * weight / total_w))
        cap = MAX_SIDE_BY_ARCHETYPE.get(archetype, 0)
        rw = min(w, cap) if cap else w
        rd = min(band_depth, cap) if cap else band_depth
        # south-align: doors open onto the spine road
        rect = Rect(x + (w - rw) // 2, process_z2 - rd + 1,
                    x + (w - rw) // 2 + rw - 1, process_z2)
        lo, hi = HEIGHTS.get(archetype, (8, 12))
        plan.stages.append(StagePlacement(stage=stage, archetype=archetype, rect=rect,
                                          order=i, role="process",
                                          height_band=_band(lo, hi, rng)))
        x += w + STAGE_GAP

    # ── conveyor / pipe bridges between consecutive stages ───────────────────
    if template.link_kind != "none":
        stages = plan.process_stages()
        for a, b in zip(stages, stages[1:]):
            if "apron" in (a.archetype, b.archetype):
                continue   # yards connect at grade, not by bridge
            zmid = (max(a.rect.z1, b.rect.z1) + process_z2) // 2
            if a.rect.x2 + 1 <= b.rect.x1 - 1:
                plan.links.append((Rect(a.rect.x2, zmid, b.rect.x1, zmid), 5))

    # ── support band, west → east ────────────────────────────────────────────
    sx = x_lo + 1
    for stage, archetype in template.support:
        w, d = SUPPORT_SIZES.get(archetype, (12, 10))
        if sx + w > x_hi:
            break
        rect = Rect(sx, support_z1, sx + w - 1, min(support_z1 + d - 1, support_z2))
        lo, hi = HEIGHTS.get(archetype, (8, 12))
        plan.stages.append(StagePlacement(stage=stage, archetype=archetype, rect=rect,
                                          order=-1, role="support",
                                          height_band=_band(lo, hi, rng)))
        sx += w + 4

    # ── front band: office HQ west of the gate, guardhouse at it, parking east ─
    gate_x = (bounds.x1 + bounds.x2) // 2
    plan.gate = Vec3(gate_x, oy, bounds.z2)
    plan.front_road = Rect(gate_x - 2, spine_z2 + 1, gate_x + 2, bounds.z2)

    office_w = 16
    office = Rect(max(x_lo, gate_x - 6 - office_w), front_z1,
                  max(x_lo, gate_x - 6 - office_w) + office_w - 1, front_z2 - 1)
    lo, hi = HEIGHTS["office_block"]
    plan.stages.append(StagePlacement(stage="hq_offices", archetype="office_block",
                                      rect=office, order=-1, role="front",
                                      height_band=_band(lo, hi, rng)))
    guard = Rect(gate_x + 4, front_z2 - 9, gate_x + 14, front_z2 - 1)
    plan.stages.append(StagePlacement(stage="gatehouse", archetype="guardhouse",
                                      rect=guard, order=-1, role="front",
                                      height_band=(4, 4)))
    park_x1 = guard.x2 + 4
    if park_x1 + 12 <= x_hi:
        plan.parking = Rect(park_x1, front_z1 + 2, min(park_x1 + 26, x_hi), front_z2 - 1)
    return plan
