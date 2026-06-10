"""
City planner — deterministic, seeded. Produces a CityPlan whose road grid makes
every block road-adjacent on all four sides, so door→road connectivity is
guaranteed by construction (QA verifies it).

Roads are spaced evenly across the bounds (no degenerate end blocks), and
district zoning follows the director's requested shares: each requested kind
gets a number of blocks proportional to its share, placed by suitability —
docks on the waterfront edge, heavy industry on the +x (downwind) edge,
rail yard and warehouses buffering it, civic at the centre, housing furthest
from the smoke.
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

# Assignment priority: edge-bound kinds claim their blocks first.
_KIND_PRIORITY = ["docks", "heavy_industry", "rail_yard", "warehouses",
                  "civic", "housing"]


def _road_positions(lo: int, hi: int) -> list[int]:
    """Evenly spaced road x/z start positions across [lo, hi], first at lo and
    last at hi-ROAD_W+1, with all blocks between roads near-equal width (no
    degenerate slivers)."""
    span = hi - lo + 1
    n_blocks = max(1, round((span - ROAD_W) / PITCH))
    return [lo + round(i * (span - ROAD_W) / n_blocks) for i in range(n_blocks + 1)]


def _share_targets(districts: list[dict], total: int) -> dict[str, int]:
    """Largest-remainder apportionment of `total` blocks over requested shares,
    guaranteeing every requested kind at least one block while blocks last."""
    kinds = [d["type"] for d in districts]
    shares = {d["type"]: d["share"] for d in districts}
    targets = {k: int(shares[k] * total) for k in kinds}
    remainders = sorted(kinds, key=lambda k: shares[k] * total - targets[k], reverse=True)
    short = total - sum(targets.values())
    for k in remainders[:short]:
        targets[k] += 1
    # every requested kind gets at least 1 block while supply allows
    if total >= len(kinds):
        for k in kinds:
            if targets[k] == 0:
                donor = max(kinds, key=lambda d: targets[d])
                if targets[donor] > 1:
                    targets[donor] -= 1
                    targets[k] = 1
    return targets


def _suitability(kind: str, bi: int, bj: int, cols: int, rows: int) -> float:
    """Higher = better block for this kind. Ties broken by (bi, bj) in the
    greedy sort, so allocation stays deterministic."""
    cx, cz = (cols - 1) / 2, (rows - 1) / 2
    if kind == "docks":
        return bj                      # waterfront = south edge
    if kind == "heavy_industry":
        return bi                      # downwind = +x edge
    if kind == "rail_yard":
        return bi - abs(bj - cz) * 0.1  # east, mid-depth
    if kind == "warehouses":
        return bi * 0.5 - abs(bj - cz) * 0.1  # buffer east of centre
    if kind == "civic":
        return -(abs(bi - cx) + abs(bj - cz))  # centre
    return -bi                         # housing: far from industry


def plan_city(city_brief, origin: dict, *, seed: int) -> CityPlan:
    rng = random.Random(seed)
    size = config.CITY_SIZES.get(city_brief.size_class, 200)
    ox, oy, oz = origin["x"], origin["y"], origin["z"]
    bounds = Rect(ox, oz, ox + size - 1, oz + size - 1)
    plan = CityPlan(bounds=bounds, ground_y=oy)

    # ── road grid ────────────────────────────────────────────────────────────
    xr = _road_positions(bounds.x1, bounds.x2)
    zr = _road_positions(bounds.z1, bounds.z2)

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

    # ── blocks ───────────────────────────────────────────────────────────────
    cols, rows = len(xr) - 1, len(zr) - 1
    blocks: list[tuple[int, int, Rect]] = []
    for bi in range(cols):
        for bj in range(rows):
            bx1, bx2 = xr[bi] + ROAD_W, xr[bi + 1] - 1
            bz1, bz2 = zr[bj] + ROAD_W, zr[bj + 1] - 1
            if bx2 - bx1 < 5 or bz2 - bz1 < 5:
                continue
            blocks.append((bi, bj, Rect(bx1, bz1, bx2, bz2)))

    # ── share-driven zoning ──────────────────────────────────────────────────
    districts = list(city_brief.districts) or [{"type": "housing", "share": 1.0}]
    requested = {d["type"] for d in districts}
    # docks only make sense on a waterfront
    if not city_brief.waterfront:
        districts = [d for d in districts if d["type"] != "docks"] or districts
        requested = {d["type"] for d in districts}
    targets = _share_targets(districts, len(blocks))

    fallback = max(districts, key=lambda d: d["share"])["type"]
    assignment: dict[tuple[int, int], str] = {}
    unassigned = {(bi, bj) for bi, bj, _ in blocks}
    for kind in _KIND_PRIORITY:
        if kind not in requested:
            continue
        want = targets.get(kind, 0)
        ranked = sorted(unassigned,
                        key=lambda b: (-_suitability(kind, b[0], b[1], cols, rows), b))
        for b in ranked[:want]:
            assignment[b] = kind
            unassigned.discard(b)
    for b in unassigned:  # rounding leftovers
        assignment[b] = fallback

    by_kind: dict[str, District] = {}
    for bi, bj, rect in blocks:
        kind = assignment[(bi, bj)]
        lot = Lot(rect=Rect(rect.x1 + SETBACK, rect.z1 + SETBACK,
                            rect.x2 - SETBACK, rect.z2 - SETBACK),
                  district_kind=kind, faces_road="N")
        dist = by_kind.setdefault(kind, District(kind=kind))
        dist.region.append(rect)
        dist.lots.append(lot)

    plan.districts = list(by_kind.values())
    _assign_landmarks(plan, city_brief, rng)
    return plan


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
