"""Scorer smoke tests against the legacy shell (no geometry)."""
from shell import build_shell
from quality import score_build

INTENT = {
    "size": {"x": 11, "y": 6, "z": 9}, "style": "medieval", "structure_type": "house",
    "materials": {"walls": "minecraft:stone_bricks", "floor": "minecraft:oak_planks",
                  "roof": "minecraft:dark_oak_planks"},
    "features": [],
}


def test_score_build_runs_on_legacy_shell():
    cmds = build_shell(INTENT, {"x": 0, "y": 64, "z": 0})
    score = score_build(cmds, INTENT, None)
    # watertight envelope should score high; door should be reachable
    assert score.metrics["watertight"] >= 90
    assert score.metrics["door_reachable"] == 100
    assert 0 <= score.total <= 100


def test_empty_build_scores_zero():
    score = score_build([], INTENT, None)
    assert score.total == 0.0


def test_score_is_deterministic():
    cmds = build_shell(INTENT, {"x": 0, "y": 64, "z": 0})
    a = score_build(cmds, INTENT, None).total
    b = score_build(cmds, INTENT, None).total
    assert a == b
