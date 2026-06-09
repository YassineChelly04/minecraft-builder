"""Repair-layer correctness — migrated from the standalone test_repair.py."""
from repair import repair_commands
from validator import validate_commands


def _dropped(report):
    return sum(1 for r in report if r.startswith("dropped"))


def test_synonym_correction():
    clean, report = repair_commands([
        "/fill 0 64 0 5 64 5 minecraft:wood_planks",
        "/setblock 2 65 2 minecraft:glass_block",
        "/fill 0 65 0 5 68 0 minecraft:stone_brick",
    ])
    valid, errors = validate_commands(clean)
    assert valid, errors
    assert _dropped(report) == 0


def test_family_fallback():
    clean, report = repair_commands([
        "/fill 0 64 0 3 64 3 minecraft:pine_planks",
        "/setblock 1 65 1 minecraft:redwood_stairs",
    ])
    valid, _ = validate_commands(clean)
    assert valid and _dropped(report) == 0


def test_fuzzy_match():
    clean, report = repair_commands([
        "/fill 0 64 0 3 64 3 minecraft:cobbleston",
        "/fill 0 64 0 3 64 3 minecraft:sea_lantren",
    ])
    valid, _ = validate_commands(clean)
    assert valid and _dropped(report) == 0


def test_strip_bogus_state():
    clean, _ = repair_commands(["/fill 0 64 0 3 64 3 minecraft:stone[facing=north]"])
    valid, _ = validate_commands(clean)
    assert valid


def test_keep_valid_stairs_state():
    clean, _ = repair_commands(["/setblock 1 65 1 minecraft:oak_stairs[facing=east]"])
    assert clean == ["/setblock 1 65 1 minecraft:oak_stairs[facing=east]"]


def test_split_oversized_fill():
    clean, _ = repair_commands(["/fill 0 64 0 99 99 99 minecraft:stone"])
    valid, _ = validate_commands(clean)
    assert valid and len(clean) > 1


def test_drop_unfixable_keep_rest():
    clean, report = repair_commands([
        "/fill 0 64 0 3 64 3 minecraft:zzqqxx_nonsense_block",
        "/setblock 1 65 1 minecraft:stone",
    ])
    valid, _ = validate_commands(clean)
    assert valid and _dropped(report) == 1


def test_add_missing_prefix():
    clean, _ = repair_commands(["/fill 0 64 0 3 64 3 oak_planks"])
    valid, _ = validate_commands(clean)
    assert valid
