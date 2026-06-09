"""
Curated palette library — the "rule of three" enforced by data.

The intent agent picks a palette NAME; Python expands it into dominant/trim/accent
+ roof/glass/light block ids. Every block in every palette is validated against
the version registry AT IMPORT TIME, so a hallucinated or version-gated block in a
palette raises at startup, never at build time.

Block ids are stored bare (no namespace). Use BuildingPalette.mc(role) or the
geometry cmd helpers to namespace them when emitting commands.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields

import config
from knowledge.blocks_registry import resolve


@dataclass(frozen=True)
class BuildingPalette:
    name: str
    dominant: str
    trim: str
    accent: str
    roof: str          # stair block for slopes
    roof_solid: str    # full block for ridges / flat fields
    glass: str
    light: str
    wear: tuple[str, ...] = ()
    wear_density: float = 0.10
    floor: str = ""            # "" -> falls back to dominant
    min_version: str = "1.21"  # lowest MC version this palette is valid at

    def block_roles(self) -> dict[str, str]:
        return {"dominant": self.dominant, "trim": self.trim, "accent": self.accent,
                "roof": self.roof, "roof_solid": self.roof_solid, "glass": self.glass,
                "light": self.light, "floor": self.floor or self.dominant}

    def all_blocks(self) -> set[str]:
        blocks = set(self.block_roles().values())
        blocks.update(self.wear)
        return {b for b in blocks if b}

    @staticmethod
    def mc(block: str) -> str:
        return block if block.startswith("minecraft:") else f"minecraft:{block}"


PALETTES: dict[str, BuildingPalette] = {
    "medieval_castle": BuildingPalette(
        "medieval_castle", "stone_bricks", "cobblestone", "chiseled_stone_bricks",
        "dark_oak_stairs", "dark_oak_planks", "glass_pane", "lantern",
        wear=("cracked_stone_bricks", "mossy_stone_bricks"), floor="stone_bricks"),
    "gothic_manor": BuildingPalette(
        "gothic_manor", "dark_oak_planks", "deepslate_bricks", "iron_bars",
        "deepslate_tile_stairs", "deepslate_tiles", "gray_stained_glass_pane",
        "soul_lantern", wear=("cracked_deepslate_bricks",), floor="dark_oak_planks"),
    "modern_villa": BuildingPalette(
        "modern_villa", "white_concrete", "gray_concrete", "dark_oak_trapdoor",
        "smooth_quartz_stairs", "smooth_stone", "glass", "sea_lantern",
        wear=(), floor="smooth_stone"),
    "japanese_temple": BuildingPalette(
        "japanese_temple", "spruce_planks", "smooth_stone", "cherry_planks",
        "dark_oak_stairs", "dark_oak_planks", "glass_pane", "lantern",
        wear=(), floor="spruce_planks"),
    "viking_longhouse": BuildingPalette(
        "viking_longhouse", "spruce_planks", "dark_oak_log", "cobblestone",
        "dark_oak_stairs", "dark_oak_planks", "glass_pane", "lantern",
        wear=("mossy_cobblestone",), floor="spruce_planks"),
    "desert_palace": BuildingPalette(
        "desert_palace", "sandstone", "smooth_sandstone", "cut_sandstone",
        "smooth_sandstone_stairs", "smooth_sandstone", "yellow_stained_glass_pane",
        "lantern", wear=("cut_sandstone",), floor="smooth_sandstone"),
    "fantasy_tower": BuildingPalette(
        "fantasy_tower", "purpur_block", "end_stone_bricks", "amethyst_block",
        "purpur_stairs", "purpur_block", "purple_stained_glass_pane", "sea_lantern",
        wear=(), floor="end_stone_bricks"),
    "ruins": BuildingPalette(
        "ruins", "cobblestone", "mossy_stone_bricks", "mossy_cobblestone",
        "cobblestone_stairs", "cobblestone", "glass_pane", "lantern",
        wear=("mossy_cobblestone", "cracked_stone_bricks", "glow_lichen"),
        wear_density=0.30, floor="cobblestone"),
    "cottage_core": BuildingPalette(
        "cottage_core", "oak_planks", "oak_log", "stripped_oak_log",
        "spruce_stairs", "spruce_planks", "glass_pane", "lantern",
        wear=(), floor="oak_planks"),
    "brick_industrial": BuildingPalette(
        "brick_industrial", "bricks", "stone_bricks", "iron_bars",
        "brick_stairs", "bricks", "glass_pane", "lantern",
        wear=("cracked_stone_bricks",), floor="stone"),
    "steel_and_copper": BuildingPalette(
        "steel_and_copper", "cut_copper", "iron_block", "copper_grate",
        "exposed_cut_copper_stairs", "cut_copper", "tinted_glass", "copper_bulb",
        wear=("exposed_cut_copper", "weathered_cut_copper"), floor="smooth_stone"),
    "victorian_steam": BuildingPalette(
        "victorian_steam", "bricks", "dark_oak_log", "copper_block",
        "deepslate_tile_stairs", "deepslate_tiles", "brown_stained_glass_pane",
        "lantern", wear=("mossy_stone_bricks",), floor="spruce_planks"),
    "gritty_deepslate": BuildingPalette(
        "gritty_deepslate", "deepslate_bricks", "polished_deepslate", "deepslate_tiles",
        "deepslate_brick_stairs", "deepslate_bricks", "gray_stained_glass_pane",
        "soul_lantern", wear=("cracked_deepslate_bricks", "cracked_deepslate_tiles"),
        floor="polished_deepslate"),
    "copper_age_tech": BuildingPalette(
        "copper_age_tech", "copper_block", "cut_copper", "copper_grate",
        "cut_copper_stairs", "cut_copper", "tinted_glass", "copper_lantern",
        wear=("exposed_copper", "weathered_copper"), floor="cut_copper",
        min_version="1.21.9"),
    "worker_housing": BuildingPalette(
        "worker_housing", "bricks", "stone_bricks", "dark_oak_log",
        "brick_stairs", "bricks", "glass_pane", "lantern",
        wear=("cracked_stone_bricks",), floor="oak_planks"),
    "volcanic_works": BuildingPalette(
        "volcanic_works", "cinnabar_bricks", "polished_cinnabar", "chiseled_cinnabar",
        "cinnabar_brick_stairs", "cinnabar_bricks", "red_stained_glass_pane",
        "magma_block", wear=("cinnabar",), floor="polished_cinnabar",
        min_version="26.2"),
}

# City-level compatibility: which accents / palettes pair within a family.
PALETTE_FAMILIES: dict[str, dict] = {
    "brick_industrial": {
        "base": "brick_industrial",
        "accents": ["iron_bars", "copper_block", "dark_oak_log"],
        "compatible": ["worker_housing", "victorian_steam", "steel_and_copper"],
    },
    "steel_and_copper": {
        "base": "steel_and_copper",
        "accents": ["copper_grate", "iron_block", "weathered_cut_copper"],
        "compatible": ["copper_age_tech", "gritty_deepslate", "brick_industrial"],
    },
    "gritty_deepslate": {
        "base": "gritty_deepslate",
        "accents": ["deepslate_tiles", "iron_bars", "polished_deepslate"],
        "compatible": ["gothic_manor", "brick_industrial", "victorian_steam"],
    },
}

# Style keyword -> default palette name (IMPLEMENTATION_SPEC §10.1).
DEFAULT_PALETTE_BY_STYLE = {
    "medieval": "medieval_castle", "castle": "medieval_castle", "fortress": "medieval_castle",
    "cottage": "cottage_core", "rustic": "cottage_core",
    "gothic": "gothic_manor", "manor": "gothic_manor",
    "modern": "modern_villa", "villa": "modern_villa", "contemporary": "modern_villa",
    "japanese": "japanese_temple", "asian": "japanese_temple", "temple": "japanese_temple",
    "viking": "viking_longhouse", "nordic": "viking_longhouse",
    "desert": "desert_palace", "sandstone": "desert_palace",
    "fantasy": "fantasy_tower", "wizard": "fantasy_tower", "tower": "fantasy_tower",
    "church": "fantasy_tower", "ruins": "ruins", "ruined": "ruins",
    "industrial": "brick_industrial", "factory": "brick_industrial",
    "warehouse": "brick_industrial", "steampunk": "victorian_steam",
    "victorian": "victorian_steam", "copper": "copper_age_tech",
}


def _validate_palettes() -> None:
    for name, pal in PALETTES.items():
        valid = resolve(pal.min_version)
        for block in pal.all_blocks():
            if BuildingPalette.mc(block) not in valid:
                raise ValueError(
                    f"Palette '{name}' uses block '{block}' not valid at "
                    f"min_version {pal.min_version}")


_validate_palettes()


def palette_for_style(style: str) -> BuildingPalette:
    key = (style or "").lower()
    for kw, name in DEFAULT_PALETTE_BY_STYLE.items():
        if kw in key:
            return PALETTES[name]
    return PALETTES["cottage_core"]


def resolve_palette(intent: dict) -> BuildingPalette:
    """intent -> BuildingPalette. Honours intent['palette_name'] then falls back to
    style; applies intent['material_overrides'] (validated against the target set)."""
    name = intent.get("palette_name") or intent.get("palette")
    pal = PALETTES.get(name) if name else None
    if pal is None:
        pal = palette_for_style(intent.get("style", ""))

    overrides = intent.get("material_overrides") or {}
    # legacy intent carried free-block choices under "materials"
    legacy = intent.get("materials") or {}
    merged = {"dominant": legacy.get("walls"), "floor": legacy.get("floor"),
              "roof_solid": legacy.get("roof"), "accent": legacy.get("accent")}
    merged.update({k: v for k, v in overrides.items() if v})

    valid = resolve(config.TARGET_MC_VERSION)
    changes = {}
    for role, block in merged.items():
        if not block:
            continue
        if BuildingPalette.mc(block) in valid and role in {f.name for f in fields(pal)}:
            changes[role] = block.replace("minecraft:", "")
    if not changes:
        return pal
    return BuildingPalette(**{**pal.__dict__, **changes})
