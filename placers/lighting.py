"""
Deterministic lighting solver — guarantees light ≥ 8 on every interior floor cell
via greedy set-cover over a BFS light field. Always runs last, regardless of any
LLM picks.
"""
from __future__ import annotations

from architecture.geometry import BuildingGeometry, Vec3, cmd_set
from placers.base import PlacerResult
from voxel import VoxelGrid, propagate_light

MIN_LIGHT = 8


def _interior_floor_cells(grid: VoxelGrid, geometry: BuildingGeometry
                          ) -> list[tuple[int, int, int]]:
    cells: list[tuple[int, int, int]] = []
    for zone in geometry.zones:
        inner = zone.rect.inset(1)
        y = zone.floor_y + 1
        for x in range(inner.x1, inner.x2 + 1):
            for z in range(inner.z1, inner.z2 + 1):
                if not grid.is_solid(x, y, z) and grid.is_solid(x, zone.floor_y, z):
                    cells.append((x, y, z))
    return cells


def auto_light(commands: list[str], geometry: BuildingGeometry, palette,
               version: str = "1.21.9") -> PlacerResult:
    """Add ceiling lights until every interior floor cell is lit ≥ 8. Lanterns
    hang at the ceiling so they never block the walkable 2-high clearance."""
    grid = VoxelGrid.from_commands(commands)
    floor = _interior_floor_cells(grid, geometry)
    if not floor:
        return PlacerResult(ok=True)

    light_block = palette.light
    hanging = "lantern" in light_block
    ceiling_y = geometry.roof_base_y - 1

    extra: list[str] = []
    grid2 = VoxelGrid.from_commands(commands)  # mutable working grid
    for _ in range(len(floor) + 2):
        field = propagate_light(grid2)
        dark = [c for c in floor if field.get(c, 0) < MIN_LIGHT]
        if not dark:
            break
        # darkest, tie-broken deterministically by coordinate
        dark.sort(key=lambda c: (field.get(c, 0), c))
        cx, cfy, cz = dark[0]
        # keep the light within ~6 of the floor so tall halls actually get lit;
        # in a short room this resolves to the ceiling (supported by the roof slab).
        ly = min(ceiling_y, cfy + 5)
        if grid2.is_solid(cx, ly, cz):
            ly = cfy + 1
        if ly < ceiling_y and not grid2.is_solid(cx, ly + 1, cz):
            # mid-air post: add a bracket above so a hanging lantern has support
            extra.append(cmd_set(Vec3(cx, ly + 1, cz), palette.trim))
            grid2.cells[(cx, ly + 1, cz)] = palette.mc(palette.trim)
        state = "[hanging=true]" if hanging else ""
        extra.append(cmd_set(Vec3(cx, ly, cz), light_block, state))
        grid2.cells[(cx, ly, cz)] = palette.mc(light_block)
    return PlacerResult(cmds=extra, ok=True)


def road_lighting(road_cells: list[tuple[int, int, int]], street_block: str,
                  light_block: str, spacing: int = 7) -> list[str]:
    """Lamps every `spacing` cells along a road (Phase F connectivity helper)."""
    cmds: list[str] = []
    for i, (x, y, z) in enumerate(sorted(road_cells)):
        if i % spacing == 0:
            cmds.append(cmd_set(Vec3(x, y + 1, z), street_block))
            cmds.append(cmd_set(Vec3(x, y + 4, z), light_block, "[hanging=false]"))
    return cmds
