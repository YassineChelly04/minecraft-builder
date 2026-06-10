"""Phase E — every archetype generates validator-clean at multiple lot sizes."""
import pytest

from architecture.archetypes import ARCHETYPES, build_archetype
from architecture.brief import intent_to_brief
from normalizer import normalize_commands
from repair import repair_commands
from validator import validate_commands

NAMES = ["generic_building", "factory_hall", "smokestack_plant", "warehouse",
         "rowhouse_strip", "office_block", "water_tower", "gasometer",
         "gantry_crane", "train_depot", "dock_finger", "civic_hall", "power_station",
         "stadium", "refinery", "coal_yard"]

SIZES = [(12, 7, 10), (16, 9, 14), (24, 10, 18)]


def test_all_twelve_registered():
    for n in NAMES:
        assert n in ARCHETYPES, n


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}x{s[2]}")
def test_archetype_generates_clean(name, size):
    sx, sy, sz = size
    intent = {"size": {"x": sx, "y": sy, "z": sz}, "style": "industrial",
              "structure_type": name, "palette_name": "brick_industrial",
              "room_program": [], "features": []}
    brief = intent_to_brief(intent, {"x": 0, "y": 64, "z": 0}, prompt=name)
    brief.archetype = name
    raw, geom = build_archetype(brief)
    clean, report = repair_commands(normalize_commands(raw))
    valid, errors = validate_commands(clean)
    assert valid, f"{name}@{size}: {errors[:3]}"
    assert clean, f"{name}@{size}: produced no commands"
    assert geom.footprint, f"{name}: no footprint"


def test_stadium_routing_and_size_caps():
    """'stadium' must route to the stadium archetype with its own (larger)
    envelope — not get clamped into a 48x48 generic box."""
    intent = {"structure_type": "stadium", "size": {"x": 300, "y": 60, "z": 220}}
    b = intent_to_brief(intent, {"x": 0, "y": 64, "z": 0}, prompt="build a giant stadium")
    assert b.archetype == "stadium"
    assert 45 <= b.lot.width <= 160 and 45 <= b.lot.depth <= 160

    small = {"structure_type": "stadium", "size": {"x": 20, "y": 10, "z": 16}}
    b2 = intent_to_brief(small, {"x": 0, "y": 64, "z": 0}, prompt="a stadium")
    assert b2.lot.width >= 45 and b2.lot.depth >= 45  # stadium minimum


def test_stadium_has_pitch_and_floodlights():
    intent = {"structure_type": "stadium", "size": {"x": 90, "y": 16, "z": 70},
              "palette_name": "brick_industrial"}
    brief = intent_to_brief(intent, {"x": 0, "y": 64, "z": 0}, prompt="stadium")
    raw, _geom = build_archetype(brief)
    clean, _ = repair_commands(normalize_commands(raw))
    assert any("grass_block" in c for c in clean), "no pitch"
    assert sum("sea_lantern" in c for c in clean) >= 4, "missing floodlights"


def test_gallery_builds(tmp_path):
    import gallery
    gallery.main(str(tmp_path))
    assert (tmp_path / "aibuilder_datapack" / "pack.mcmeta").exists()
