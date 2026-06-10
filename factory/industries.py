"""
Industry knowledge base — how real manufacturers lay out their plants, encoded.

Researched against published plant-design practice (sources in V3 release notes):
- General principle: straight-through value-stream flow, receiving at one end and
  shipping at the other, utilities in a parallel service band, offices/amenities
  at the front entrance (systematic layout planning / lean flow patterns).
- Aerospace (Airbus/Boeing FAL): component logistics -> subassembly -> a single
  giant final-assembly hangar with pulse stations and ~90 m sliding doors ->
  paint hall -> open flight-line apron where finished aircraft park.
- Automotive (Ford/Toyota): press (stamping) shop -> body-in-white shop -> paint
  shop (the tall sealed building) -> final assembly (the long one) -> marshalling
  yard for finished vehicles; coil steel arrives by rail.
- Food & beverage (Nestlé): hygiene zoning low->high along the flow: raw silos &
  receiving (low) -> processing (medium) -> filling/packaging (high hygiene,
  white cleanroom-like) -> high-bay warehouse -> dispatch docks; boiler house and
  water treatment in the utility band, QA lab near production.
- Brewery (Heineken/Guinness): grain silos -> brewhouse (the copper kettles) ->
  fermentation cellar (rows of tanks) -> packaging -> cold store -> shipping.
- Steel (ArcelorMittal/Nucor): ore & coal stockyard -> blast furnace w/ hot
  stoves -> casting hall -> rolling mill (the very long hall) -> finished yard;
  rail everywhere.
- Chemical/pharma (BASF/Pfizer): tank farm -> reactor/process structures with
  pipe racks -> finishing hall -> drum/pack -> warehouse; flare + cooling tower.
- Electronics (Intel/TSMC): central utility building feeds a huge white
  cleanroom fab (rooftop air plant) -> assembly & test -> automated warehouse.

Each flow entry: (stage_name, archetype, weight) — weight is the stage's share
of frontage along the value stream. `max_side` limits shell-based archetypes to
sizes the watertight envelope handles well; custom archetypes are unlimited (0).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Industry:
    label: str
    flow: tuple = ()                     # ((stage, archetype, weight), ...)
    support: tuple = ()                  # ((stage, archetype), ...) utility band
    link_kind: str = "conveyor"          # what joins consecutive process stages
    rail: bool = False                   # freight rail spur into the site
    palette_family: str = "steel_and_copper"
    era: str = "modern"
    product: str = "goods"


INDUSTRIES: dict[str, Industry] = {
    "aerospace": Industry(
        label="Aerospace final assembly",
        flow=(("component_warehouse", "warehouse", 1.4),
              ("subassembly_hall", "factory_hall", 1.6),
              ("final_assembly_hangar", "assembly_hangar", 3.2),
              ("paint_hall", "paint_shop", 1.4),
              ("flight_line", "apron", 2.4)),
        support=(("power_house", "power_station"), ("water_tower", "water_tower"),
                 ("office_hq", "office_block")),
        link_kind="none",                # airframes are towed, not conveyed
        rail=False, palette_family="steel_and_copper", product="aircraft"),

    "automotive": Industry(
        label="Automotive assembly plant",
        flow=(("press_shop", "press_shop", 1.6),
              ("body_shop", "factory_hall", 1.8),
              ("paint_shop", "paint_shop", 1.4),
              ("final_assembly", "assembly_hall", 2.6),
              ("marshalling_yard", "apron", 1.6)),
        support=(("power_house", "power_station"), ("water_tower", "water_tower"),
                 ("office_hq", "office_block")),
        link_kind="conveyor", rail=True,
        palette_family="steel_and_copper", product="vehicles"),

    "food_beverage": Industry(
        label="Food & beverage plant (hygiene-zoned)",
        flow=(("raw_silos", "silo_battery", 1.0),
              ("processing_hall", "factory_hall", 2.0),
              ("packaging_hall", "clean_hall", 1.8),
              ("high_bay_warehouse", "high_bay_warehouse", 1.6),
              ("dispatch_docks", "warehouse", 1.2)),
        support=(("boiler_house", "power_station"), ("water_treatment", "tank_farm"),
                 ("qa_lab", "office_block"), ("office_hq", "office_block")),
        link_kind="conveyor", rail=True,
        palette_family="brick_industrial", product="food products"),

    "brewery": Industry(
        label="Brewery",
        flow=(("grain_silos", "silo_battery", 1.0),
              ("brewhouse", "brewhouse", 1.6),
              ("fermentation_cellar", "fermentation_cellar", 2.0),
              ("packaging_hall", "clean_hall", 1.6),
              ("cold_store", "warehouse", 1.2)),
        support=(("boiler_house", "power_station"), ("water_tower", "water_tower"),
                 ("office_hq", "office_block")),
        link_kind="pipe", rail=False,
        palette_family="brick_industrial", era="victorian", product="beer"),

    "steel": Industry(
        label="Integrated steel works",
        flow=(("stockyard", "coal_yard", 1.4),
              ("blast_furnace", "blast_furnace", 1.6),
              ("casting_hall", "factory_hall", 1.6),
              ("rolling_mill", "rolling_mill", 2.6),
              ("finished_yard", "apron", 1.2)),
        support=(("power_house", "power_station"), ("cooling_tower", "cooling_tower"),
                 ("office_hq", "office_block")),
        link_kind="conveyor", rail=True,
        palette_family="gritty_deepslate", era="dieselpunk", product="steel"),

    "chemical": Industry(
        label="Chemical / pharma works",
        flow=(("tank_farm", "tank_farm", 1.6),
              ("reactor_block", "refinery", 2.0),
              ("finishing_hall", "factory_hall", 1.6),
              ("drumming_packing", "clean_hall", 1.4),
              ("product_warehouse", "warehouse", 1.4)),
        support=(("control_room", "office_block"), ("cooling_tower", "cooling_tower"),
                 ("office_hq", "office_block")),
        link_kind="pipe", rail=True,
        palette_family="steel_and_copper", product="chemicals"),

    "electronics": Industry(
        label="Semiconductor / electronics fab",
        flow=(("utility_building", "power_station", 1.2),
              ("cleanroom_fab", "cleanroom_fab", 3.0),
              ("assembly_test", "clean_hall", 1.6),
              ("automated_warehouse", "high_bay_warehouse", 1.4)),
        support=(("water_treatment", "tank_farm"), ("office_hq", "office_block")),
        link_kind="conveyor", rail=False,
        palette_family="steel_and_copper", product="chips"),

    "generic": Industry(
        label="General manufacturing",
        flow=(("receiving_warehouse", "warehouse", 1.2),
              ("production_hall", "factory_hall", 2.4),
              ("packaging_hall", "clean_hall", 1.4),
              ("shipping_warehouse", "warehouse", 1.2)),
        support=(("power_house", "power_station"), ("water_tower", "water_tower"),
                 ("office_hq", "office_block")),
        link_kind="conveyor", rail=False,
        palette_family="brick_industrial", product="goods"),
}

# Shell-based archetypes keep the watertight envelope happy below ~46 a side;
# custom open structures (0) take any size the planner gives them.
MAX_SIDE_BY_ARCHETYPE = {
    "warehouse": 46, "factory_hall": 46, "paint_shop": 46, "clean_hall": 46,
    "press_shop": 46, "assembly_hall": 60, "rolling_mill": 60, "brewhouse": 46,
    "office_block": 24, "power_station": 30, "high_bay_warehouse": 46,
}

# brand/company -> (industry, product). Deterministic: "build a Ford plant"
# resolves correctly even if the director LLM call fails entirely.
BRANDS: dict[str, tuple[str, str]] = {
    "airbus": ("aerospace", "airliners"), "boeing": ("aerospace", "airliners"),
    "embraer": ("aerospace", "regional jets"), "dassault": ("aerospace", "jets"),
    "lockheed": ("aerospace", "aircraft"), "spacex": ("aerospace", "rockets"),
    "ford": ("automotive", "trucks"), "toyota": ("automotive", "cars"),
    "tesla": ("automotive", "electric cars"), "volkswagen": ("automotive", "cars"),
    "bmw": ("automotive", "cars"), "mercedes": ("automotive", "cars"),
    "stellantis": ("automotive", "cars"), "renault": ("automotive", "cars"),
    "hyundai": ("automotive", "cars"), "general motors": ("automotive", "cars"),
    "nestle": ("food_beverage", "chocolate & coffee"),
    "nestlé": ("food_beverage", "chocolate & coffee"),
    "kraft": ("food_beverage", "packaged food"), "danone": ("food_beverage", "dairy"),
    "unilever": ("food_beverage", "consumer goods"),
    "mondelez": ("food_beverage", "snacks"), "mars": ("food_beverage", "confectionery"),
    "pepsi": ("food_beverage", "beverages"), "coca-cola": ("food_beverage", "beverages"),
    "coca cola": ("food_beverage", "beverages"),
    "heineken": ("brewery", "beer"), "guinness": ("brewery", "stout"),
    "carlsberg": ("brewery", "beer"), "budweiser": ("brewery", "beer"),
    "ab inbev": ("brewery", "beer"),
    "arcelormittal": ("steel", "steel"), "arcelor": ("steel", "steel"),
    "nucor": ("steel", "steel"), "tata steel": ("steel", "steel"),
    "thyssenkrupp": ("steel", "steel"), "posco": ("steel", "steel"),
    "basf": ("chemical", "chemicals"), "dow": ("chemical", "chemicals"),
    "bayer": ("chemical", "pharmaceuticals"), "pfizer": ("chemical", "pharmaceuticals"),
    "sanofi": ("chemical", "pharmaceuticals"),
    "intel": ("electronics", "processors"), "tsmc": ("electronics", "chips"),
    "samsung": ("electronics", "semiconductors"), "asml": ("electronics", "lithography tools"),
    "foxconn": ("electronics", "electronics"),
}

# Loose industry keywords for prompts without a brand name.
KEYWORDS: dict[str, str] = {
    "aircraft": "aerospace", "plane": "aerospace", "aerospace": "aerospace",
    "rocket": "aerospace", "car": "automotive", "vehicle": "automotive",
    "automotive": "automotive", "truck": "automotive", "gigafactory": "automotive",
    "food": "food_beverage", "chocolate": "food_beverage", "dairy": "food_beverage",
    "beverage": "food_beverage", "bottling": "food_beverage",
    "brewery": "brewery", "beer": "brewery", "distillery": "brewery",
    "steel": "steel", "smelter": "steel", "ironworks": "steel", "foundry": "steel",
    "chemical": "chemical", "pharma": "chemical", "refining": "chemical",
    "chip": "electronics", "semiconductor": "electronics", "fab": "electronics",
    "electronics": "electronics",
}


def match_industry(text: str) -> tuple[str, str, str] | None:
    """Return (company, industry, product) detected in `text`, or None.
    Brands win over keywords; longest brand match wins. Word-boundary matching
    so "ford" never fires inside "afford" or "car" inside "carpet"."""
    import re
    t = text.lower()
    best = None
    for brand, (industry, product) in BRANDS.items():
        if re.search(rf"\b{re.escape(brand)}\b", t) and (best is None or len(brand) > len(best[0])):
            best = (brand, industry, product)
    if best:
        return best[0].title(), best[1], best[2]
    for kw, industry in KEYWORDS.items():
        if re.search(rf"\b{re.escape(kw)}\b", t):
            return "", industry, INDUSTRIES[industry].product
    return None
