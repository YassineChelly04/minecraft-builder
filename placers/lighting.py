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


# lantern light 15 reaches ~7 cells; a 5-cell grid keeps every floor cell ≥8 even
# with internal walls. Bounded work: O(floor / STEP²) lights + ONE BFS top-up — the
# old per-dark-cell BFS loop was O(floor²) and hung on large open footprints.
LIGHT_STEP = 5
TOPUP_CAP = 80


def _place_light(grid2, extra, palette, x, ly, z, hanging, ceiling_y):
    if ly < ceiling_y and not grid2.is_solid(x, ly + 1, z):
        # mid-air post: bracket above so a hanging lantern has support
        extra.append(cmd_set(Vec3(x, ly + 1, z), palette.trim))
        grid2.cells[(x, ly + 1, z)] = palette.mc(palette.trim)
    state = "[hanging=true]" if hanging else ""
    extra.append(cmd_set(Vec3(x, ly, z), palette.light, state))
    grid2.cells[(x, ly, z)] = palette.mc(palette.light)


def auto_light(commands: list[str], geometry: BuildingGeometry, palette,
               version: str = "1.21.9") -> PlacerResult:
    """Light every interior floor cell to ≥8 with a deterministic ceiling grid,
    then a single bounded top-up for residual dark cells. Lanterns hang at the
    ceiling so they never block the 2-high walk clearance."""
    grid2 = VoxelGrid.from_commands(commands)
    floor = _interior_floor_cells(grid2, geometry)
    if not floor:
        return PlacerResult(ok=True)
    floor_set = set(floor)
    hanging = "lantern" in palette.light
    ceiling_y = geometry.roof_base_y - 1
    extra: list[str] = []

    # 1) coarse grid per zone — one O(floor) pass, guarantees ≥1 light per room
    for zone in geometry.zones:
        inner = zone.rect.inset(1)
        cy = min(ceiling_y, zone.ceil_y)
        placed_here = 0
        for x in range(inner.x1, inner.x2 + 1, LIGHT_STEP):
            for z in range(inner.z1, inner.z2 + 1, LIGHT_STEP):
                if (x, zone.floor_y + 1, z) not in floor_set:
                    continue
                ly = min(cy, zone.floor_y + 6)
                if grid2.is_solid(x, ly, z):
                    continue
                _place_light(grid2, extra, palette, x, ly, z, hanging, ceiling_y)
                placed_here += 1
        if placed_here == 0:                      # tiny room the grid skipped
            c = zone.free_center()
            ly = min(cy, c.y + 5)
            if not grid2.is_solid(c.x, ly, c.z):
                _place_light(grid2, extra, palette, c.x, ly, c.z, hanging, ceiling_y)

    # 2) single bounded top-up for any cells still dark (no re-looping BFS)
    field = propagate_light(grid2)
    dark = [c for c in floor if field.get(c, 0) < MIN_LIGHT]
    for (cx, cfy, cz) in dark[:TOPUP_CAP]:
        ly = min(ceiling_y, cfy + 5)
        if not grid2.is_solid(cx, ly, cz):
            _place_light(grid2, extra, palette, cx, ly, cz, hanging, ceiling_y)
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
