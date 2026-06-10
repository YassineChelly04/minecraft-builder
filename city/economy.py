"""
Deterministic economy agent — the supply-chain brain of an industrial city.

plan_economy(city_brief, plan, seed) derives an EconomyProfile from the
director's brief: which industries the city runs, the producer→consumer chains
between them, era-weighted archetype menus per district, and height bands. It
then lays freight rail into the plan connecting heavy industry to its logistics
districts (warehouses / rail yard / docks), so the industrial flow is visible
on the ground, not just implied.

Consistent with the project thesis: the LLM (city director) makes the taste
picks (era, district mix); this module turns them into a coherent economy
deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from architecture.geometry import Rect

RAIL_W = 2  # gravel bed width; rail runs along its first row

# era -> weighted archetype menu per district kind. Weights bias the mix so a
# victorian city reads coal-and-brick while a modern one reads tanks-and-steel.
_MENUS: dict[str, dict[str, list[tuple[str, int]]]] = {
    "victorian": {
        "heavy_industry": [("smokestack_plant", 3), ("factory_hall", 3),
                           ("coal_yard", 2), ("gasometer", 1), ("power_station", 1)],
        "warehouses": [("warehouse", 4), ("train_depot", 1), ("gantry_crane", 1)],
    },
    "interwar": {
        "heavy_industry": [("factory_hall", 3), ("power_station", 2),
                           ("smokestack_plant", 2), ("coal_yard", 1), ("refinery", 1)],
        "warehouses": [("warehouse", 3), ("train_depot", 2), ("water_tower", 1)],
    },
    "modern": {
        "heavy_industry": [("refinery", 3), ("power_station", 2),
                           ("factory_hall", 2), ("gasometer", 1)],
        "warehouses": [("warehouse", 4), ("gantry_crane", 1), ("water_tower", 1)],
    },
    "dieselpunk": {
        "heavy_industry": [("smokestack_plant", 3), ("refinery", 2),
                           ("gasometer", 2), ("power_station", 2), ("coal_yard", 1)],
        "warehouses": [("warehouse", 3), ("gantry_crane", 2), ("train_depot", 1)],
    },
}

_COMMON_MENUS: dict[str, list[tuple[str, int]]] = {
    "housing": [("rowhouse_strip", 3), ("generic_building", 1)],
    "civic": [("civic_hall", 2), ("office_block", 2)],
    "docks": [("dock_finger", 2), ("warehouse", 2), ("gantry_crane", 1), ("water_tower", 1)],
    "rail_yard": [("train_depot", 3), ("coal_yard", 1), ("warehouse", 1), ("gantry_crane", 1)],
}

# producer -> consumer adjacencies in the supply chain (only pairs whose both
# ends exist in the city make it into the profile).
_CHAIN_RULES = [
    ("coal_yard", "smokestack_plant"), ("coal_yard", "power_station"),
    ("smokestack_plant", "warehouse"), ("factory_hall", "warehouse"),
    ("refinery", "warehouse"), ("gasometer", "power_station"),
    ("warehouse", "train_depot"), ("warehouse", "dock_finger"),
]

# height bands per district kind (the economy raises industry above housing).
_BANDS = {
    "heavy_industry": (11, 16), "warehouses": (8, 12), "housing": (6, 9),
    "civic": (10, 14), "docks": (6, 10), "rail_yard": (7, 10),
}


@dataclass
class EconomyProfile:
    era: str
    menus: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    bands: dict[str, tuple[int, int]] = field(default_factory=dict)
    industries: list[str] = field(default_factory=list)
    chains: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"era": self.era, "industries": self.industries,
                "chains": [f"{a} -> {b}" for a, b in self.chains]}


def plan_economy(city_brief, plan, seed: int) -> EconomyProfile:
    era = city_brief.era if city_brief.era in _MENUS else "victorian"
    menus = dict(_COMMON_MENUS)
    menus.update(_MENUS[era])

    present_kinds = {d.kind for d in plan.districts}
    industries = sorted({arch for kind in present_kinds
                         for arch, _w in menus.get(kind, [])
                         if kind in ("heavy_industry", "rail_yard", "docks")})
    chains = [(a, b) for a, b in _CHAIN_RULES if a in industries or b in industries]

    profile = EconomyProfile(era=era, menus=menus, bands=dict(_BANDS),
                             industries=industries, chains=chains)
    _lay_freight_rail(plan)
    return profile


def menu_for(profile: EconomyProfile | None, kind: str) -> list[tuple[str, int]]:
    if profile and kind in profile.menus:
        return profile.menus[kind]
    return _COMMON_MENUS.get(kind, [("generic_building", 1)])


def _district_span(plan, kind: str) -> Rect | None:
    """Bounding rect of a district's blocks."""
    regions = [r for d in plan.districts if d.kind == kind for r in d.region]
    if not regions:
        return None
    return Rect(min(r.x1 for r in regions), min(r.z1 for r in regions),
                max(r.x2 for r in regions), max(r.z2 for r in regions))


def _lay_freight_rail(plan) -> None:
    """Street trackage: a freight mainline along the road nearest heavy
    industry, from the logistics belt (warehouses / rail yard, else city edge)
    to industry's east edge — plus a dock spur down a vertical road when the
    city has a waterfront. Track beds sit one row off the road centreline so
    they never collide with the street lamps."""
    industry = _district_span(plan, "heavy_industry")
    if industry is None:
        return
    icx, icz = industry.center()

    # mainline: horizontal arterial whose centreline is closest to industry
    horiz = [r for r in plan.roads.arterial if r.width >= r.depth]
    if not horiz:
        return
    road = min(horiz, key=lambda r: abs((r.z1 + r.z2) // 2 - icz))
    rz = (road.z1 + road.z2) // 2 + 1  # off-centre: lamps own the centreline
    west = _district_span(plan, "warehouses") or _district_span(plan, "rail_yard")
    x_start = west.x1 if west else plan.bounds.x1
    plan.rail.append(Rect(x_start, rz, industry.x2, rz + RAIL_W - 1))

    # dock spur: down the vertical arterial nearest industry's west edge
    docks = _district_span(plan, "docks")
    if docks is None or docks.z1 <= rz:
        return
    vert = [r for r in plan.roads.arterial if r.depth > r.width]
    if not vert:
        return
    vroad = min(vert, key=lambda r: abs((r.x1 + r.x2) // 2 - industry.x1))
    vx = (vroad.x1 + vroad.x2) // 2 + 1
    plan.rail.append(Rect(vx, rz, vx + RAIL_W - 1, docks.z1))
