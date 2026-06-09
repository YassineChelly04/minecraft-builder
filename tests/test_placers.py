"""Phase D — placers, auto_light, deterministic critic, interior DSL agent."""
import json
import re
from pathlib import Path

import pytest

from agents.dsl_interior import parse_ops
from architecture.brief import intent_to_brief
from architecture.shell2 import build_shell2
from critic import furnish_building, critic_patch
from llm_client import stub_mode
from normalizer import normalize_commands
from quality import score_build
from repair import repair_commands
from validator import validate_commands

BENCH = json.loads((Path(__file__).resolve().parent.parent /
                    "benchmarks" / "prompts_buildings.json").read_text())


def _dsl_build(prompt, origin):
    from pipeline import build_structure
    with stub_mode(True):
        return build_structure(prompt, origin, mode="dsl", refine=False)


# ── auto_light + critic close the metric gaps ────────────────────────────────

def test_auto_light_lights_a_house():
    intent = {"size": {"x": 13, "y": 7, "z": 11}, "style": "medieval",
              "structure_type": "house", "palette_name": "medieval_castle",
              "room_program": ["living", "kitchen", "bedroom"], "features": ["fireplace"]}
    res = _dsl_build("medieval house with a fireplace", {"x": 0, "y": 64, "z": 0})
    sc = score_build(res["commands"], intent, res["geometry"])
    assert sc.metrics["light_coverage"] >= 85
    assert sc.metrics["feature_presence"] == 100  # fireplace -> campfire present


@pytest.mark.parametrize("entry", BENCH, ids=[e["id"] for e in BENCH])
def test_dsl_suite_zero_validator_errors(entry):
    res = _dsl_build(entry["prompt"], entry["origin"])
    assert res["valid"], res["errors"][:3]


def test_dsl_tokens_under_budget():
    res = _dsl_build("a cozy medieval house", {"x": 0, "y": 64, "z": 0})
    assert res["usage"]["total_tokens"] <= 5500


# ── the LLM never writes a coordinate or a block id ──────────────────────────

def test_parse_ops_drops_coordinates_and_blocks():
    malicious = json.dumps({"ops": [
        {"op": "sofa", "x": 103, "y": 65, "z": 207, "block": "minecraft:stone"},
        {"op": "place dirt at 10 20 30"},
        {"op": "bookshelf_wall"},
    ]})
    menu = ["sofa", "bookshelf_wall", "rug", "plant"]
    ops = parse_ops(malicious, menu)
    assert ops == ["sofa", "bookshelf_wall"]
    # output is pure op names — no integers, no namespace
    blob = " ".join(ops)
    assert "minecraft:" not in blob
    assert not re.search(r"\d{2,}", blob)


def test_parse_ops_fuzzy_matches_typo():
    assert parse_ops(json.dumps({"ops": [{"op": "lanterns"}, {"op": "book_shelf_wall"}]}),
                     ["bookshelf_wall"]) == ["bookshelf_wall"]


# ── furnishing is deterministic ──────────────────────────────────────────────

def test_furnishing_is_deterministic():
    intent = {"size": {"x": 13, "y": 7, "z": 11}, "style": "cottage",
              "structure_type": "house", "palette_name": "cottage_core",
              "room_program": ["living", "kitchen"]}
    b1 = intent_to_brief(intent, {"x": 0, "y": 64, "z": 0}, prompt="p")
    _, g1 = build_shell2(b1)
    a, _ = furnish_building(g1, b1)
    b2 = intent_to_brief(intent, {"x": 0, "y": 64, "z": 0}, prompt="p")
    _, g2 = build_shell2(b2)
    b, _ = furnish_building(g2, b2)
    assert a == b
