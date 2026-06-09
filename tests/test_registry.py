"""Version registry + palette validation (Phase B / DoD-B)."""
import pytest

from knowledge.blocks_registry import resolve, oxidation_variants, VERSION_ORDER
from knowledge.palettes import PALETTES, resolve_palette, palette_for_style


def test_version_gating_copper_lantern():
    assert "minecraft:copper_lantern" not in resolve("1.21")
    assert "minecraft:copper_lantern" in resolve("1.21.9")


def test_version_gating_cinnabar():
    assert "minecraft:cinnabar" not in resolve("1.21.9")
    assert "minecraft:cinnabar" in resolve("26.2")


def test_resolve_is_monotonic():
    prev = set()
    for v in VERSION_ORDER:
        cur = resolve(v)
        assert prev <= cur, f"{v} dropped blocks"
        prev = set(cur)


def test_copper_deco_family_present_at_1_21():
    base = resolve("1.21")
    for b in ("chiseled_copper", "copper_grate", "copper_bulb",
              "copper_door", "copper_trapdoor"):
        assert f"minecraft:{b}" in base, b


def test_oxidation_variants_expansion():
    v = oxidation_variants("copper_bars")
    assert "copper_bars" in v
    assert "exposed_copper_bars" in v
    assert "waxed_oxidized_copper_bars" in v
    assert len(v) == 8


def test_unknown_target_falls_back_to_highest():
    assert resolve("99.9") == resolve(VERSION_ORDER[-1])


def test_all_palettes_validate_at_import():
    # import already ran _validate_palettes(); just assert coverage + roles exist
    assert len(PALETTES) >= 16
    for name, pal in PALETTES.items():
        valid = resolve(pal.min_version)
        for b in pal.all_blocks():
            assert pal.mc(b) in valid, f"{name}:{b}"


def test_volcanic_works_is_version_gated():
    assert PALETTES["volcanic_works"].min_version == "26.2"


def test_resolve_palette_by_style_and_override():
    pal = palette_for_style("a grand medieval castle")
    assert pal.name == "medieval_castle"
    # legacy material override (valid) wins on the dominant role
    pal2 = resolve_palette({"style": "medieval", "materials": {"walls": "deepslate_bricks"}})
    assert pal2.dominant == "deepslate_bricks"
    # invalid override is ignored, not fatal
    pal3 = resolve_palette({"style": "medieval", "materials": {"walls": "nonsense_block"}})
    assert pal3.dominant == "stone_bricks"
