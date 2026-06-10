"""
District stylist — one batched LLM call picking per-district accent / street_set /
motif. Always falls back to a deterministic default per kind, so a failure only
degrades style, never breaks the build.
"""
from __future__ import annotations

import json

from llm_client import complete

_SYSTEM = "You style city districts. JSON only."

DEFAULT_DISTRICT_STYLE = {
    "heavy_industry": {"street_set": "pole_lights", "motif": "pipes_overhead"},
    "warehouses": {"street_set": "pole_lights", "motif": "rail_spurs"},
    "housing": {"street_set": "gas_lamps", "motif": "none"},
    "civic": {"street_set": "gas_lamps", "motif": "none"},
    "docks": {"street_set": "catenary", "motif": "canal_side"},
    "rail_yard": {"street_set": "catenary", "motif": "rail_spurs"},
}


def get_district_styles(city_brief) -> dict:
    kinds = sorted({d["type"] for d in city_brief.districts})
    prompt = (f"City era {city_brief.era}, family {city_brief.palette_family}. "
              f"For each district type {kinds} pick street_set "
              f"(gas_lamps|pole_lights|catenary) and motif "
              f"(pipes_overhead|rail_spurs|canal_side|crane_row|none). "
              f'JSON: {{"districts":{{"<type>":{{"street_set":..,"motif":..}}}}}}. JSON only.')
    styles: dict = {}
    try:
        data = json.loads(complete("district_stylist", _SYSTEM, prompt))
        styles = data.get("districts", {}) if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        styles = {}
    # fill defaults
    out = {}
    for kind in kinds:
        d = DEFAULT_DISTRICT_STYLE.get(kind, {"street_set": "pole_lights", "motif": "none"})
        s = styles.get(kind, {}) if isinstance(styles, dict) else {}
        out[kind] = {"street_set": s.get("street_set", d["street_set"]),
                     "motif": s.get("motif", d["motif"])}
    return out
