"""V3 — manufacturer engine: brand mapping, plan integrity over seeds/industries,
QA gates, end-to-end stub build validity, and the creativity/binding guarantees
(variation salt changes the build; ticked answers change the intent)."""
import pytest

from architecture.archetypes import ARCHETYPES
from architecture.brief import _apply_answer_overlay, seed_from
from factory.industries import INDUSTRIES, match_industry
from factory.model import FactoryBrief
from factory.planner import plan_factory
from factory.qa import score_factory
from llm_client import stub_mode
from validator import validate_commands

ORIGIN = {"x": 0, "y": 64, "z": 0}


# ── brand / keyword mapping ───────────────────────────────────────────────────

@pytest.mark.parametrize("prompt,industry", [
    ("build me an Airbus factory", "aerospace"),
    ("a Ford assembly plant", "automotive"),
    ("Nestlé chocolate factory", "food_beverage"),
    ("a Heineken brewery", "brewery"),
    ("ArcelorMittal steelworks", "steel"),
    ("a TSMC fab", "electronics"),
    ("BASF chemical plant", "chemical"),
])
def test_brand_mapping(prompt, industry):
    matched = match_industry(prompt)
    assert matched is not None
    assert matched[1] == industry


def test_brand_word_boundaries():
    assert match_industry("an affordable carpet warehouse") is None


# ── plan integrity across industries and seeds ───────────────────────────────

@pytest.mark.parametrize("industry", list(INDUSTRIES))
@pytest.mark.parametrize("seed", [1, 99173])
def test_plan_integrity(industry, seed):
    fb = FactoryBrief(industry=industry, size_class=["S", "M", "L"][seed % 3])
    plan = plan_factory(fb, ORIGIN, seed=seed)
    sc = score_factory(plan)
    assert sc.metrics["flow_order"] == 100, "stages out of value-stream order"
    assert sc.metrics["stage_coverage"] == 100, "missing process stages"
    assert sc.metrics["no_overlap"] == 100, "footprints overlap"
    assert sc.metrics["gate_road"] == 100, "gate not connected to spine"
    assert sc.metrics["links"] >= 80
    # every placed archetype must exist in the registry
    for s in plan.stages:
        assert s.archetype in ARCHETYPES, f"unregistered archetype {s.archetype}"
    # everything inside the fence
    for s in plan.stages:
        assert plan.bounds.intersect(s.rect) == s.rect


# ── end-to-end (offline stub) ────────────────────────────────────────────────

@pytest.mark.parametrize("prompt", ["a Ford assembly plant", "Nestlé factory",
                                    "a Guinness brewery"])
def test_build_factory_stub(prompt):
    from factory_pipeline import build_factory
    with stub_mode():
        result = build_factory(prompt, ORIGIN)
    assert result["command_count"] > 200
    assert result["qa"]["total"] >= 90
    valid, errors = validate_commands(result["commands"])
    assert valid, f"invalid commands: {errors[:5]}"
    assert len(result["plan_summary"]["stages"]) >= 4


def test_build_factory_variation_changes_output():
    from factory_pipeline import build_factory
    with stub_mode():
        a = build_factory("a Ford assembly plant", ORIGIN, variation=1)
        b = build_factory("a Ford assembly plant", ORIGIN, variation=2)
        c = build_factory("a Ford assembly plant", ORIGIN, variation=1)
    assert a["commands"] == c["commands"], "same variation must be reproducible"
    assert a["commands"] != b["commands"], "different variation must differ"


# ── creativity / binding guarantees (single-building path) ───────────────────

def test_seed_salt_changes_seed():
    assert seed_from("a house", ORIGIN, salt=1) != seed_from("a house", ORIGIN, salt=2)
    assert seed_from("a house", ORIGIN, salt=0) == seed_from("a house", ORIGIN)


def test_answer_overlay_binds_palette_and_size():
    intent = {"structure_type": "house", "size": {"x": 11, "y": 6, "z": 9}}
    out = _apply_answer_overlay(intent, {"Which palette?": "weathered copper and steel",
                                         "How big?": "huge", "Floors?": "3 floors"})
    assert out["palette_name"] == "copper_age_tech" or "copper" in out["palette_name"]
    assert out["size"]["x"] > 11 and out["size"]["z"] > 9
    assert out["size"]["y"] >= 13


def test_answer_overlay_binds_features():
    intent = {"structure_type": "house"}
    out = _apply_answer_overlay(intent, {"Signature feature?": "grand fireplace"})
    assert "grand fireplace" in out.get("features", [])
