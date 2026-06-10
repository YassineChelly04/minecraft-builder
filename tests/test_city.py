"""Phase F — city engine QA + property-based plan integrity (DoD-F)."""
import json
from pathlib import Path

import pytest

from city.briefs import make_briefs
from city.model import CityBrief
from city.planner import plan_city
from city.qa import score_city
from llm_client import stub_mode
from validator import validate_commands

CITIES = json.loads((Path(__file__).resolve().parent.parent /
                     "benchmarks" / "prompts_cities.json").read_text())


def _make_plan(seed: int, size="M", waterfront=False, districts=None):
    cb = CityBrief(size_class=size, waterfront=waterfront,
                   districts=districts or [{"type": "heavy_industry", "share": .4},
                                           {"type": "housing", "share": .4},
                                           {"type": "civic", "share": .2}],
                   landmarks=["clock_tower", "city_hall", "gasometer_park"])
    plan = plan_city(cb, {"x": 0, "y": 64, "z": 0}, seed=seed)
    make_briefs(plan, cb, None, seed)
    return plan


# ── property-based: 20 random seeds, plan integrity ──────────────────────────

@pytest.mark.parametrize("seed", range(20))
def test_plan_integrity_over_seeds(seed):
    size = ["S", "M", "L"][seed % 3]
    plan = _make_plan(seed * 7919 + 13, size=size, waterfront=(seed % 2 == 0))
    sc = score_city(plan, [])
    assert sc.metrics["no_overlap"] == 100, "lots overlap"
    assert sc.metrics["door_to_road"] == 100, "a lot has no road"
    assert sc.metrics["road_connectivity"] == 100, "roads not one component"
    assert sc.metrics["road_lighting"] >= 80


# ── the 5 benchmark cities build, validate, and pass QA (offline) ────────────

@pytest.mark.parametrize("entry", CITIES, ids=[c["id"] for c in CITIES])
def test_benchmark_city_qa_passes(entry):
    from city_pipeline import build_city
    # keep tests fast: force size S regardless of prompt answers
    answers = dict(entry.get("answers") or {})
    answers["size"] = "S"
    with stub_mode(True):
        res = build_city(entry["prompt"], entry["origin"], answers)
    assert res["qa"]["total"] >= 90, res["qa"]
    assert not res["qa"]["failing"], res["qa"]["failing"]
    assert res["usage"]["total_tokens"] <= 40000


def test_city_commands_validate():
    from city_pipeline import build_city
    with stub_mode(True):
        res = build_city("a worker housing town beside a power station",
                         {"x": 0, "y": 64, "z": 0}, {"size": "S"})
    valid, errors = validate_commands(res["commands"])
    assert valid, errors[:5]


INDUSTRIAL_MIX = [{"type": "heavy_industry", "share": .30},
                  {"type": "warehouses", "share": .20},
                  {"type": "housing", "share": .30},
                  {"type": "civic", "share": .10},
                  {"type": "docks", "share": .10}]


@pytest.mark.parametrize("size", ["S", "M", "L"])
def test_every_requested_district_is_built(size):
    """Regression: the old grid dropped the degenerate +x column / south row,
    silently deleting heavy_industry and docks from M/L cities."""
    cb = CityBrief(size_class=size, waterfront=True, districts=INDUSTRIAL_MIX,
                   landmarks=["clock_tower", "city_hall", "gasometer_park"])
    plan = plan_city(cb, {"x": 0, "y": 64, "z": 0}, seed=99)
    built = {d.kind for d in plan.districts}
    assert {d["type"] for d in INDUSTRIAL_MIX} <= built, built
    # shares approximately respected
    total = len(plan.all_lots())
    heavy = sum(len(d.lots) for d in plan.districts if d.kind == "heavy_industry")
    assert abs(heavy / total - 0.30) < 0.15, f"{heavy}/{total}"


def test_economy_lays_freight_rail():
    from city.economy import plan_economy
    cb = CityBrief(size_class="M", waterfront=True, districts=INDUSTRIAL_MIX,
                   landmarks=["clock_tower", "city_hall", "gasometer_park"])
    plan = plan_city(cb, {"x": 0, "y": 64, "z": 0}, seed=7)
    profile = plan_economy(cb, plan, 7)
    assert plan.rail, "no freight rail laid"
    assert profile.chains, "no supply chains derived"
    assert "heavy_industry" in profile.menus


def test_plan_svg_writes(tmp_path):
    from city.plot import write_plan_svg
    plan = _make_plan(1, size="S")
    p = write_plan_svg(plan, tmp_path / "plan.svg")
    assert Path(p).exists() and Path(p).read_text().startswith("<svg")
