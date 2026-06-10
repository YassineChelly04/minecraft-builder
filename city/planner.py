"""
City planner — deterministic, seeded. Produces a CityPlan whose road grid makes
every block road-adjacent on all four sides, so door→road connectivity is
guaranteed by construction (QA verifies it).

Zoning convention: heavy industry on the +x edge (downwind), civic at the centre,
housing opposite the industry, docks along the waterfront edge.
"""
from __future__ import annotations

import random

import config
from architecture.geometry import Rect, Vec3
from city.model import CityPlan, District, Lot, RoadGraph

ROAD_W = 5
PITCH = 24
SETBACK = 1

# landmark name -> (district kind it belongs in, archetype it maps to)
LANDMARK_MAP = {
    "grand_station": ("warehouses", "train_depot"),
    "power_cathedral": ("heavy_industry", "power_station"),
    "clock_tower": ("civic", "civic_hall"),
    "gasometer_park": ("heavy_industry", "gasometer"),
    "harbor_crane_row": ("docks", "gantry_crane"),
    "city_hall": ("civic", "civic_hall"),
}


def plan_city(city_brief, origin: dict, *, seed: int) -> CityPlan:
    rng = random.Random(seed)
    size = config.CITY_SIZES.get(city_brief.size_class, 200)
    ox, oy, oz = origin["x"], origin["y"], origin["z"]
    bounds = Rect(ox, oz, ox + size - 1, oz + size - 1)
    plan = CityPlan(bounds=bounds, ground_y=oy)

    # ── road grid ────────────────────────────────────────────────────────────
    xr = list(range(bounds.x1, bounds.x2 - ROAD_W + 2, PITCH))
    zr = list(range(bounds.z1, bounds.z2 - ROAD_W + 2, PITCH))
    if xr[-1] != bounds.x2 - ROAD_W + 1:
        xr.append(bounds.x2 - ROAD_W + 1)
    if zr[-1] != bounds.z2 - ROAD_W + 1:
        zr.append(bounds.z2 - ROAD_W + 1)

    roads = RoadGraph()
    for z in zr:
        roads.arterial.append(Rect(bounds.x1, z, bounds.x2, z + ROAD_W - 1))
    for x in xr:
        roads.arterial.append(Rect(x, bounds.z1, x + ROAD_W - 1, bounds.z2))
    for x in xr:
        for z in zr:
            roads.nodes.append(Vec3(x + ROAD_W // 2, oy, z + ROAD_W // 2))
    plan.roads = roads

    # waterfront canal along the south edge
    if city_brief.waterfront:
        plan.canal = [Rect(bounds.x1, bounds.z2 - 7, bounds.x2, bounds.z2)]

    # ── blocks -> lots -> districts ──────────────────────────────────────────
    cols, rows = len(xr) - 1, len(zr) - 1
    by_kind: dict[str, District] = {}
    center = (cols // 2, rows // 2)

    for bi in range(cols):
        for bj in range(rows):
            bx1, bx2 = xr[bi] + ROAD_W, xr[bi + 1] - 1
            bz1, bz2 = zr[bj] + ROAD_W, zr[bj + 1] - 1
            if bx2 - bx1 < 5 or bz2 - bz1 < 5:
                continue
            kind = _zone(bi, bj, cols, rows, center, city_brief.waterfront)
            lot = Lot(rect=Rect(bx1 + SETBACK, bz1 + SETBACK, bx2 - SETBACK, bz2 - SETBACK),
                      district_kind=kind, faces_road="N")
            dist = by_kind.setdefault(kind, District(kind=kind))
            dist.region.append(Rect(bx1, bz1, bx2, bz2))
            dist.lots.append(lot)

    plan.districts = list(by_kind.values())
    _assign_landmarks(plan, city_brief, rng)
    return plan


def _zone(bi, bj, cols, rows, center, waterfront) -> str:
    if waterfront and bj == rows - 1:
        return "docks"
    if (bi, bj) == center:
        return "civic"
    if bi >= cols - 1:
        return "heavy_industry"
    if bi >= cols - 2:
        return "warehouses"
    return "housing"


def _assign_landmarks(plan: CityPlan, city_brief, rng) -> None:
    for name in city_brief.landmarks:
        kind, _arch = LANDMARK_MAP.get(name, ("civic", "civic_hall"))
        dist = next((d for d in plan.districts if d.kind == kind), None)
        if not dist or not dist.lots:
            dist = plan.districts[0] if plan.districts else None
        if not dist:
            continue
        # largest free lot in the district
        free = [l for l in dist.lots if not l.landmark]
        if not free:
            continue
        lot = max(free, key=lambda l: l.rect.area)
        lot.landmark = name
