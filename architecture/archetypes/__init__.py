"""Industrial archetype library. `build_archetype(brief)` routes a BuildingBrief to
its Archetype (default: generic_building, a thin wrapper over shell2)."""
from architecture.archetypes.base import Archetype, ARCHETYPES, build_archetype, register
from architecture.archetypes import library   # noqa: F401  (registers all archetypes)
from architecture.archetypes import industry  # noqa: F401  (manufacturer archetypes)

__all__ = ["Archetype", "ARCHETYPES", "build_archetype", "register"]
