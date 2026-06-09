"""
Shell 2.0 orchestrator.

build_shell2(brief) -> (commands, BuildingGeometry)

Assembles massing -> floor -> walls (pillars/recessed windows/cornice/door) ->
watertight enclosing slab -> decorative roof -> BSP floorplan -> sitework, and
returns the full BuildingGeometry that placers and DSL agents consume.

Single rectangular footprint in v1 (L/T/courtyard massing deferred — see
DECISIONS.md); fully watertight and reachable.
"""
from __future__ import annotations

from architecture.brief import BuildingBrief
from architecture.floorplan import generate_floorplan
from architecture.floors import floor_slab, storey_bands
from architecture.geometry import (
    BuildingGeometry, OUTWARD, Rect, Vec3, cmd_fill,
)
from architecture.roofs import build_roof, roof_kind_for
from architecture.sitework import entry_path, foundation_skirt, garden_strip
from architecture.walls import build_walls


def build_shell2(brief: BuildingBrief, *, roof_kind: str | None = None,
                 furnish_program: bool = True) -> tuple[list[str], BuildingGeometry]:
    rng = brief.rng()
    rect = brief.lot
    pal = brief.palette
    floor_y = brief.origin_y
    total_h = max(5, brief.height_band[1])
    wall_top = floor_y + total_h - 1
    roof_base_y = floor_y + total_h
    front = brief.front_face

    cmds: list[str] = []

    # 1. foundation skirt + solid base under the floor
    cmds += foundation_skirt(rect, floor_y, pal)
    cmds.append(cmd_fill(Vec3(rect.x1, floor_y - 1, rect.z1),
                         Vec3(rect.x2, floor_y - 1, rect.z2), pal.trim))

    # 2. floor slab + border trim
    cmds += floor_slab(rect, floor_y, pal)

    # 3. clear the interior cavity (build-over-terrain safe)
    if rect.width > 2 and rect.depth > 2:
        cmds.append(cmd_fill(Vec3(rect.x1 + 1, floor_y + 1, rect.z1 + 1),
                             Vec3(rect.x2 - 1, wall_top, rect.z2 - 1), "air"))

    # 4. walls: plinth, pillars, infill, recessed windows, cornice, door
    wcmds, walls, door = build_walls(rect, floor_y, total_h, pal, front, rng)
    cmds += wcmds

    # 5. watertight enclosing slab, then the decorative roof on top
    cmds.append(cmd_fill(Vec3(rect.x1, roof_base_y, rect.z1),
                         Vec3(rect.x2, roof_base_y, rect.z2), pal.roof_solid))
    kind = roof_kind or roof_kind_for(brief.style, brief.archetype)
    cmds += build_roof(kind, rect, roof_base_y, pal, rng)

    # 6. interior floorplan (BSP rooms, internal walls, doors)
    interior = rect.inset(1)
    zones = []
    if furnish_program and brief.room_program:
        fcmds, zones = generate_floorplan(interior, brief.room_program,
                                          floor_y, wall_top, pal, rng)
        cmds += fcmds
    if not zones:
        from architecture.geometry import Zone
        zones = [Zone(name="hall", rect=interior, floor_y=floor_y, ceil_y=wall_top)]

    # 7. sitework
    cmds += entry_path(door, floor_y, pal, rng)
    cmds += garden_strip(rect, floor_y, door, pal, rng)

    ox, oz = OUTWARD[door.face]
    anchors = {
        "door_outside": Vec3(door.x + ox, door.y, door.z + oz),
        "door_inside": Vec3(door.x - ox, door.y, door.z - oz),
    }
    geom = BuildingGeometry(
        origin=Vec3(rect.x1, floor_y, rect.z1), footprint=[rect], walls=walls,
        roof_base_y=roof_base_y, storeys=storey_bands(floor_y, total_h, brief.storeys),
        zones=zones, front_face=front, anchors=anchors,
    )
    return cmds, geom
