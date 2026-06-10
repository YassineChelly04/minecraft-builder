"""
CityPlan -> List[BuildingBrief]. Heights follow the skyline rule; palette is the
family base; landmarks get a specific archetype + the llm detail level, everything
else is kit (zero tokens).
"""
from __future__ import annotations

import hashlib
import random

import config
from architecture.brief import BuildingBrief
from city.model import CityPlan
from city.planner import LANDMARK_MAP
from knowledge.palettes import PALETTES, PALETTE_FAMILIES

ARCHETYPE_MENU = {
    "heavy_industry": ["factory_hall", "smokestack_plant", "power_station", "gasometer"],
    "warehouses": ["warehouse", "train_depot", "gantry_crane"],
    "housing": ["rowhouse_strip", "generic_building"],
    "civic": ["civic_hall", "office_block"],
    "docks": ["dock_finger", "warehouse", "water_tower"],
    "rail_yard": ["train_depot", "warehouse", "gantry_crane"],
}

# (lo, hi) height band by district kind, scaled by skyline rule.
_BANDS = {
    "heavy_industry": (10, 14), "warehouses": (8, 12), "housing": (6, 9),
    "civic": (10, 14), "docks": (6, 10),
}


def _seed(master: int, rect) -> int:
    h = hashlib.sha256(f"{master}|{rect.x1},{rect.z1},{rect.x2},{rect.z2}".encode()).hexdigest()
    return int(h[:16], 16)


def _palette(city_brief):
    fam = PALETTE_FAMILIES.get(city_brief.palette_family)
    base = fam["base"] if fam else "brick_industrial"
    return PALETTES.get(base, PALETTES["brick_industrial"])


def make_briefs(plan: CityPlan, city_brief, district_styles: dict | None,
                master_seed: int) -> list[BuildingBrief]:
    rng = random.Random(master_seed)
    palette = _palette(city_brief)
    briefs: list[BuildingBrief] = []

    for lot in plan.all_lots():
        seed = _seed(master_seed, lot.rect)
        lrng = random.Random(seed)
        kind = lot.district_kind

        if lot.landmark:
            archetype = LANDMARK_MAP.get(lot.landmark, (kind, "civic_hall"))[1]
            detail = "llm" if config.DETAIL_LLM_SHARE in ("landmarks", "all") else "kit"
        else:
            menu = ARCHETYPE_MENU.get(kind, ["generic_building"])
            archetype = lrng.choice(menu)
            detail = "llm" if config.DETAIL_LLM_SHARE == "all" else "kit"

        lo, hi = _BANDS.get(kind, (7, 9))
        if city_brief.skyline == "stacks_dominate" and archetype in ("smokestack_plant", "gasometer"):
            lo, hi = 18, 26
        h = lrng.randint(lo, hi)

        rooms = ["living", "kitchen", "bedroom"] if kind == "housing" else []
        briefs.append(BuildingBrief(
            archetype=archetype, lot=lot.rect, origin_y=plan.ground_y,
            style=city_brief.era, palette=palette, storeys=max(1, h // 5),
            height_band=(h, h), room_program=rooms, features=[],
            front_face=lot.faces_road, seed=seed, detail_level=detail,
        ))

    plan.briefs = briefs
    return briefs
