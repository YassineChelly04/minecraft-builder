"""
Version-aware block registry.

`resolve(target)` returns the frozenset of valid `minecraft:` block ids available
at and below the target Minecraft version (the union of every version set ≤
target). repair.py / validator.py consume this via the blocks.py shim, so the set
of "valid" blocks tracks TARGET_MC_VERSION.

All ids are normalised to the `minecraft:` namespace. Version-addition sets may be
written bare (no namespace) for brevity; resolve() namespaces them.
"""
from __future__ import annotations

from functools import lru_cache

from knowledge._base_blocks import BASE_1_21

VERSION_ORDER = ["1.21", "1.21.4", "1.21.5", "1.21.9", "26.1", "26.2", "26.3"]


def oxidation_variants(*bases: str) -> set[str]:
    """Expand copper bases into their oxidation + waxed combinations:
    base, exposed_/weathered_/oxidized_base, and the four waxed_* forms."""
    stages = ["", "exposed_", "weathered_", "oxidized_"]
    out: set[str] = set()
    for base in bases:
        for st in stages:
            out.add(f"{st}{base}")
            out.add(f"waxed_{st}{base}")
    return out


BLOCKS_BY_VERSION: dict[str, set[str]] = {
    "1.21": set(BASE_1_21),
    "1.21.4": {
        "pale_oak_planks", "pale_oak_log", "pale_oak_stairs", "pale_oak_slab",
        "pale_oak_fence", "pale_oak_door", "pale_oak_trapdoor", "pale_oak_wood",
        "stripped_pale_oak_log", "stripped_pale_oak_wood", "pale_oak_fence_gate",
        "resin_block", "resin_bricks", "resin_brick_stairs", "resin_brick_slab",
        "resin_brick_wall", "chiseled_resin_bricks", "resin_clump",
    },
    "1.21.5": {
        "bush", "firefly_bush", "leaf_litter", "wildflowers", "cactus_flower",
        "short_dry_grass", "tall_dry_grass",
    },
    "1.21.9": {
        "copper_bars", "copper_chain", "copper_lantern", "copper_torch",
        "copper_chest", "copper_golem_statue", "shelf",
        *oxidation_variants("copper_bars", "copper_chain", "copper_lantern", "copper_chest"),
    },
    "26.1": set(),
    # NOTE: 26.2 (cinnabar/sulfur) releases 2026-06-16 — PROVISIONAL ids, kept
    # behind the version gate. See tools/verify_blocks_26_2.md before trusting.
    "26.2": {
        "cinnabar", "cinnabar_stairs", "cinnabar_slab", "cinnabar_wall",
        "polished_cinnabar", "polished_cinnabar_stairs", "polished_cinnabar_slab",
        "polished_cinnabar_wall", "cinnabar_bricks", "cinnabar_brick_stairs",
        "cinnabar_brick_slab", "cinnabar_brick_wall", "chiseled_cinnabar",
    },
    "26.3": set(),
}


def _full(b: str) -> str:
    return b if b.startswith("minecraft:") else f"minecraft:{b}"


@lru_cache(maxsize=None)
def resolve(target: str) -> frozenset[str]:
    """Union of all version sets at and below `target`. Unknown target -> highest
    known version."""
    if target not in VERSION_ORDER:
        target = VERSION_ORDER[-1]
    cutoff = VERSION_ORDER.index(target)
    acc: set[str] = set()
    for v in VERSION_ORDER[: cutoff + 1]:
        acc |= BLOCKS_BY_VERSION.get(v, set())
    return frozenset(_full(b) for b in acc)


def min_version_for(block: str) -> str | None:
    """Lowest version that introduces `block` (bare or namespaced), or None."""
    full = _full(block)
    for v in VERSION_ORDER:
        if full in {_full(b) for b in BLOCKS_BY_VERSION.get(v, set())}:
            return v
    return None
