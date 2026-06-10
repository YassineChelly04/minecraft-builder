"""
Archetype ABC + registry.

An archetype produces (commands, BuildingGeometry) from a BuildingBrief. The
default building path delegates to shell2; specialised archetypes override the
roof, add signature detail (stacks, tanks, gantries), or build fully custom
geometry (cylinders, piers) when a watertight envelope doesn't apply.
"""
from __future__ import annotations

from abc import ABC

from architecture.brief import BuildingBrief
from architecture.geometry import BuildingGeometry, OUTWARD, Rect, Vec3
from architecture.shell2 import build_shell2


class Archetype(ABC):
    name: str = "generic_building"
    roof_kind: str | None = None
    furnished: bool = True

    def massing(self, brief: BuildingBrief) -> list[Rect]:
        return [brief.lot]

    def build(self, brief: BuildingBrief) -> tuple[list[str], BuildingGeometry]:
        cmds, geom = build_shell2(brief, roof_kind=self.roof_kind,
                                  furnish_program=self.furnished)
        cmds += self.detail(brief, geom)
        return cmds, geom

    def detail(self, brief: BuildingBrief, geom: BuildingGeometry) -> list[str]:
        return []


ARCHETYPES: dict[str, Archetype] = {}


def register(arch_cls: type[Archetype]) -> type[Archetype]:
    """Class decorator: instantiate the archetype and register it by name."""
    inst = arch_cls()
    ARCHETYPES[inst.name] = inst
    return arch_cls


def build_archetype(brief: BuildingBrief) -> tuple[list[str], BuildingGeometry]:
    arch = ARCHETYPES.get(brief.archetype) or ARCHETYPES["generic_building"]
    return arch.build(brief)


def minimal_geometry(brief: BuildingBrief, rect: Rect, top_y: int) -> BuildingGeometry:
    """A geometry stub for open/custom structures (no rooms): a front-face door
    anchor so the city can route a path to it, and the footprint for QA."""
    ox, oz = OUTWARD[brief.front_face]
    cx, cz = rect.center()
    door = Vec3(cx, brief.origin_y + 1, rect.z1 if brief.front_face == "N" else rect.z2)
    return BuildingGeometry(
        origin=Vec3(rect.x1, brief.origin_y, rect.z1), footprint=[rect], walls=[],
        roof_base_y=top_y, storeys=[(brief.origin_y, top_y)], zones=[],
        front_face=brief.front_face,
        anchors={"door_outside": Vec3(door.x + ox, door.y, door.z + oz),
                 "door_inside": Vec3(door.x - ox, door.y, door.z - oz)},
    )
