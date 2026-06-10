"""
City director — ONE LLM call returning a CityBrief. Validated/defaulted so it
NEVER fails the build (unknown district types fuzzy-matched or dropped, shares
renormalised, 3–6 landmarks). size_class/waterfront come from clarify answers.
"""
from __future__ import annotations

import json

from city.model import CityBrief
from city.planner import LANDMARK_MAP
from llm_client import complete

_SYSTEM = "You are an urban designer for an industrial Minecraft city."
_DISTRICTS = ["heavy_industry", "warehouses", "housing", "civic", "rail_yard", "docks"]

_PROMPT = """\
Design an industrial city for: {prompt}
Return JSON only:
{{"era":"victorian|interwar|modern|dieselpunk",
 "palette_family":"brick_industrial|steel_and_copper|gritty_deepslate",
 "districts":[{{"type":"heavy_industry|warehouses|housing|civic|rail_yard|docks","share":0.3}}],
 "landmarks":["grand_station","power_cathedral","clock_tower","gasometer_park","harbor_crane_row","city_hall"],
 "skyline":"stacks_dominate|center_peak|waterfront_wall",
 "mood":"<max 8 words>"}}
Rules: 3-6 landmarks; shares sum ~1; districts from the list only.
JSON only. No prose."""


def get_city_brief(prompt: str, answers: dict | None) -> CityBrief:
    answers = answers or {}
    raw = ""
    try:
        raw = complete("city_director", _SYSTEM, _PROMPT.format(prompt=prompt))
        data = json.loads(raw)
    except Exception:  # noqa: BLE001 — never fail
        data = {}

    districts = _valid_districts(data.get("districts"))
    landmarks = _valid_landmarks(data.get("landmarks"))
    size = str(answers.get("size", "M")).upper()
    size = size if size in ("S", "M", "L") else "M"
    waterfront = str(answers.get("waterfront", "")).lower().startswith(("y", "true"))
    # docks imply a waterfront
    if any(d["type"] == "docks" for d in districts):
        waterfront = True

    return CityBrief(
        theme=prompt[:60], era=data.get("era", "victorian"),
        palette_family=data.get("palette_family", "brick_industrial"),
        districts=districts, landmarks=landmarks,
        skyline=data.get("skyline", "stacks_dominate"),
        mood=data.get("mood", ""), size_class=size, waterfront=waterfront,
    )


def _valid_districts(raw) -> list[dict]:
    out = []
    for d in (raw or []):
        if isinstance(d, dict) and d.get("type") in _DISTRICTS:
            out.append({"type": d["type"], "share": float(d.get("share", 0.2) or 0.2)})
    if not out:
        out = [{"type": "heavy_industry", "share": 0.35},
               {"type": "warehouses", "share": 0.20},
               {"type": "housing", "share": 0.30},
               {"type": "civic", "share": 0.15}]
    total = sum(d["share"] for d in out) or 1.0
    for d in out:
        d["share"] /= total
    return out


def _valid_landmarks(raw) -> list[str]:
    out = [l for l in (raw or []) if l in LANDMARK_MAP]
    if len(out) < 3:
        for cand in ("clock_tower", "city_hall", "gasometer_park", "grand_station"):
            if cand not in out:
                out.append(cand)
            if len(out) >= 3:
                break
    return out[:6]
