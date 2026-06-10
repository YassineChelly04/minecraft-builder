"""
City QA — deterministic checks on a finished plan (IMPLEMENTATION_SPEC §3.2 city
additions): door→road reachability, road connectivity (single component), road
lighting presence, and lot-overlap freedom.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from city.model import CityPlan

CITY_WEIGHTS = {"door_to_road": 3.0, "road_connectivity": 2.0,
                "road_lighting": 1.0, "no_overlap": 2.0, "skyline_match": 1.0}
CITY_TARGETS = {"door_to_road": 100, "road_connectivity": 100,
                "road_lighting": 80, "no_overlap": 100, "skyline_match": 60}


@dataclass
class CityScore:
    metrics: dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    failing: list[str] = field(default_factory=list)

    def to_dict(self):
        return {"total": round(self.total, 1),
                "metrics": {k: round(v, 1) for k, v in self.metrics.items()},
                "failing": self.failing}


def _door_to_road(plan: CityPlan) -> float:
    cells = plan.roads.cell_set()
    if not plan.briefs:
        return 100.0
    ok = 0
    for brief in plan.briefs:
        # door is on the front (N) face, just outside the lot
        cx, _ = brief.lot.center()
        dz = brief.lot.z1 - 1
        # nearest road cell distance (lots are road-adjacent by construction)
        near = min((abs(x - cx) + abs(z - dz) for (x, z) in cells), default=999)
        if near <= 3:
            ok += 1
    return 100.0 * ok / len(plan.briefs)


def _road_connectivity(plan: CityPlan) -> float:
    cells = plan.roads.cell_set()
    if not cells:
        return 0.0
    start = next(iter(cells))
    seen = {start}
    q = deque([start])
    while q:
        x, z = q.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n in cells and n not in seen:
                seen.add(n)
                q.append(n)
    return 100.0 if len(seen) == len(cells) else 100.0 * len(seen) / len(cells)


def _road_lighting(plan: CityPlan, commands: list[str]) -> float:
    """% of road cells within reach of a street lamp. Lamp positions are derived
    the same way connectivity places them (centrelines every LAMP_SPACING)."""
    from city.connectivity import LAMP_SPACING
    road_cells = plan.roads.cell_set()
    if not road_cells:
        return 100.0
    lamps: set[tuple[int, int]] = set()
    for r in plan.roads.all_rects():
        cz, cx = (r.z1 + r.z2) // 2, (r.x1 + r.x2) // 2
        if r.width >= r.depth:
            lamps.update((x, cz) for x in range(r.x1, r.x2 + 1, LAMP_SPACING))
        else:
            lamps.update((cx, z) for z in range(r.z1, r.z2 + 1, LAMP_SPACING))
    reach = 6
    covered = sum(1 for (x, z) in road_cells
                  if any(abs(x - lx) + abs(z - lz) <= reach for (lx, lz) in lamps))
    return 100.0 * covered / len(road_cells)


def _no_overlap(plan: CityPlan) -> float:
    lots = [l.rect for l in plan.all_lots()]
    for i in range(len(lots)):
        for j in range(i + 1, len(lots)):
            if lots[i].intersect(lots[j]):
                return 0.0
    return 100.0


def _skyline_match(plan: CityPlan) -> float:
    if not plan.briefs:
        return 100.0
    heights = [b.height_band[1] for b in plan.briefs]
    return 100.0 if max(heights) - min(heights) >= 4 else 60.0


def score_city(plan: CityPlan, commands: list[str]) -> CityScore:
    metrics = {
        "door_to_road": _door_to_road(plan),
        "road_connectivity": _road_connectivity(plan),
        "road_lighting": _road_lighting(plan, commands),
        "no_overlap": _no_overlap(plan),
        "skyline_match": _skyline_match(plan),
    }
    num = den = 0.0
    failing = []
    for k, v in metrics.items():
        w = CITY_WEIGHTS[k]
        num += w * v
        den += w
        if v < CITY_TARGETS[k]:
            failing.append(k)
    return CityScore(metrics=metrics, total=num / den if den else 0.0, failing=failing)
