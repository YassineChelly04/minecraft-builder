"""
CityPlan -> List[BuildingBrief]. The economy profile drives the archetype mix
(era-weighted menus) and height bands; landmarks get a specific archetype + the
llm detail level, everything else is kit (zero tokens).
"""
from __future__ import annotations

import hashlib
import random

import config
from architecture.brief import BuildingBrief
from city.economy import EconomyProfile, menu_for
from city.model import CityPlan
from city.planner import LANDMARK_MAP
from knowledge.palettes import PALETTES, PALETTE_FAMILIES

# fallback (lo, hi) height band by district kind when no economy profile given.
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
                master_seed: int, economy: EconomyProfile | None = None) -> list[BuildingBrief]:
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
            menu = menu_for(economy, kind)
            names = [a for a, _w in menu]
            weights = [w for _a, w in menu]
            archetype = lrng.choices(names, weights=weights, k=1)[0]
            detail = "llm" if config.DETAIL_LLM_SHARE == "all" else "kit"

        bands = economy.bands if economy else _BANDS
        lo, hi = bands.get(kind, (7, 9))
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
