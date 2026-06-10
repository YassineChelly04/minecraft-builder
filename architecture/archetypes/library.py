"""
The twelve industrial archetypes. Shell-based ones override the roof and add
signature detail; open structures (tower/gasometer/gantry/pier) build custom
geometry. Every archetype is deterministic + seeded and emits validator-clean
commands at any lot size.
"""
from __future__ import annotations

import math

from architecture.archetypes.base import Archetype, minimal_geometry, register
from architecture.brief import BuildingBrief
from architecture.geometry import (
    BuildingGeometry, OUTWARD, Rect, Vec3, cmd_fill, cmd_set,
)
from architecture.shell2 import build_shell2


# ── geometry helpers ─────────────────────────────────────────────────────────

def _column(x: int, z: int, y0: int, y1: int, block: str, state: str = "") -> list[str]:
    return [cmd_fill(Vec3(x, y0, z), Vec3(x, y1, z), block, state)]


def _ring(cx: int, cz: int, r: float, y: int, block: str) -> list[str]:
    cmds, seen = [], set()
    steps = max(8, int(2 * math.pi * r))
    for i in range(steps):
        a = 2 * math.pi * i / steps
        x, z = round(cx + r * math.cos(a)), round(cz + r * math.sin(a))
        if (x, z) not in seen:
            seen.add((x, z))
            cmds.append(cmd_set(Vec3(x, y, z), block))
    return cmds


def _cylinder(cx: int, cz: int, r: float, y0: int, y1: int, block: str) -> list[str]:
    cmds = []
    for y in range(y0, y1 + 1):
        cmds += _ring(cx, cz, r, y, block)
    return cmds


def _smokestack(cx: int, cz: int, y0: int, height: int, palette) -> list[str]:
    cmds = _column(cx, cz, y0, y0 + height, palette.dominant)
    # 3x3 base taper for the first few courses
    for dy in range(3):
        cmds.append(cmd_fill(Vec3(cx - 1, y0 + dy, cz - 1), Vec3(cx + 1, y0 + dy, cz + 1),
                             palette.trim))
    for band in range(8, height, 8):
        cmds += _ring(cx, cz, 1.2, y0 + band, palette.accent)
    cmds.append(cmd_set(Vec3(cx, y0 + height + 1, cz), "campfire", "[lit=true]"))
    cmds += _ring(cx, cz, 1.0, y0 + height, "iron_bars")
    return cmds


# ── shell-based archetypes ───────────────────────────────────────────────────

@register
class GenericBuilding(Archetype):
    name = "generic_building"


@register
class FactoryHall(Archetype):
    name = "factory_hall"
    roof_kind = "sawtooth"

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        pal = brief.palette
        # wide sliding-door gate on the front face
        cx, _ = rect.center()
        z = rect.z1
        return [cmd_fill(Vec3(cx - 1, brief.origin_y + 1, z), Vec3(cx + 1, brief.origin_y + 4, z), "air"),
                cmd_fill(Vec3(cx - 2, brief.origin_y + 1, z), Vec3(cx - 2, brief.origin_y + 4, z), pal.trim),
                cmd_fill(Vec3(cx + 2, brief.origin_y + 1, z), Vec3(cx + 2, brief.origin_y + 4, z), pal.trim)]


@register
class SmokestackPlant(FactoryHall):
    name = "smokestack_plant"

    def detail(self, brief, geom):
        cmds = super().detail(brief, geom)
        rect = geom.footprint[0]
        n = 1 + (brief.seed % 3)
        for i in range(n):
            cx = rect.x1 + 2 + i * 3
            cmds += _smokestack(cx, rect.z2 - 1, geom.roof_base_y, 8 + (brief.seed % 6), brief.palette)
        return cmds


@register
class Warehouse(Archetype):
    name = "warehouse"
    roof_kind = "flat_parapet"

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        pal = brief.palette
        y = brief.origin_y
        # loading dock platform on the front
        return [cmd_fill(Vec3(rect.x1, y + 1, rect.z1 - 2), Vec3(rect.x2, y + 1, rect.z1 - 1), pal.trim),
                cmd_set(Vec3(rect.x1 + 1, y + 2, rect.z1 - 2), "barrel"),
                cmd_set(Vec3(rect.x2 - 1, y + 2, rect.z1 - 2), "barrel")]


@register
class RowhouseStrip(Archetype):
    name = "rowhouse_strip"
    roof_kind = "gable"


@register
class OfficeBlock(Archetype):
    name = "office_block"
    roof_kind = "flat_parapet"
    furnished = False


@register
class TrainDepot(Archetype):
    name = "train_depot"
    roof_kind = "gable"
    furnished = False

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        y = brief.origin_y
        cmds = []
        # two parallel rail lines on a gravel bed through the depot
        for dz in (rect.z1 + 2, rect.z2 - 2):
            cmds.append(cmd_fill(Vec3(rect.x1, y, dz), Vec3(rect.x2, y, dz), "gravel"))
            cmds.append(cmd_fill(Vec3(rect.x1, y + 1, dz), Vec3(rect.x2, y + 1, dz), "iron_bars"))
        return cmds


@register
class CivicHall(Archetype):
    name = "civic_hall"
    roof_kind = "flat_parapet"

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        pal = brief.palette
        y = brief.origin_y
        cmds = []
        # entry colonnade: a row of columns + capitals in front of the door
        for x in range(rect.x1 + 1, rect.x2, 3):
            cmds += _column(x, rect.z1 - 2, y + 1, y + 4, pal.trim)
            cmds.append(cmd_set(Vec3(x, y + 5, rect.z1 - 2), pal.accent))
        # entry stair
        cmds.append(cmd_fill(Vec3(rect.x1, y, rect.z1 - 1), Vec3(rect.x2, y, rect.z1 - 1),
                             pal.roof, "[facing=north,half=bottom]"))
        return cmds


@register
class PowerStation(Archetype):
    name = "power_station"
    roof_kind = "flat_parapet"
    furnished = False

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        y = brief.origin_y
        cmds = []
        # transformer frames + a pole run leaving the lot front
        for x in range(rect.x1 + 1, rect.x2, 4):
            cmds.append(cmd_fill(Vec3(x, y + 1, rect.z1 - 3), Vec3(x, y + 3, rect.z1 - 3), "iron_bars"))
            cmds.append(cmd_set(Vec3(x, y + 4, rect.z1 - 3), "iron_bars"))
        return cmds


# ── custom open structures ───────────────────────────────────────────────────

@register
class WaterTower(Archetype):
    name = "water_tower"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        pal = brief.palette
        y = brief.origin_y
        cx, cz = rect.center()
        legh = 6 + (brief.seed % 4)
        cmds = []
        # four legs with an X-brace
        legs = [(rect.x1 + 1, rect.z1 + 1), (rect.x2 - 1, rect.z1 + 1),
                (rect.x1 + 1, rect.z2 - 1), (rect.x2 - 1, rect.z2 - 1)]
        for (lx, lz) in legs:
            cmds += _column(lx, lz, y, y + legh, pal.trim)
        cmds.append(cmd_fill(Vec3(rect.x1 + 1, y + legh // 2, cz), Vec3(rect.x2 - 1, y + legh // 2, cz), "oak_fence"))
        # tank cylinder
        r = min(rect.width, rect.depth) // 2 - 1
        cmds += _cylinder(cx, cz, max(2, r), y + legh, y + legh + 4, pal.dominant)
        cmds.append(cmd_fill(Vec3(cx - r, y + legh, cz - r), Vec3(cx + r, y + legh, cz + r), pal.trim))
        # spire cap
        cmds.append(cmd_column := cmd_set(Vec3(cx, y + legh + 6, cz), pal.light))
        top = y + legh + 6
        return cmds, minimal_geometry(brief, rect, top)


@register
class Gasometer(Archetype):
    name = "gasometer"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        pal = brief.palette
        y = brief.origin_y
        cx, cz = rect.center()
        r = max(4, min(rect.width, rect.depth) // 2 - 1)
        h = 8 + (brief.seed % 5)
        cmds = _cylinder(cx, cz, r, y, y + h, pal.dominant)
        # external frame ring of iron-bar columns
        for i in range(8):
            a = 2 * math.pi * i / 8
            fx, fz = round(cx + (r + 1) * math.cos(a)), round(cz + (r + 1) * math.sin(a))
            cmds += _column(fx, fz, y, y + h + 1, "iron_bars")
        cmds += _ring(cx, cz, r, y + h, pal.accent)
        return cmds, minimal_geometry(brief, rect, y + h)


@register
class GantryCrane(Archetype):
    name = "gantry_crane"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        pal = brief.palette
        y = brief.origin_y
        h = 7 + (brief.seed % 4)
        cmds = []
        # two towers + a beam across, with a chain+hook drop
        for lx in (rect.x1 + 1, rect.x2 - 1):
            cmds += _column(lx, rect.z1 + 1, y, y + h, pal.trim)
            cmds += _column(lx, rect.z2 - 1, y, y + h, pal.trim)
        cmds.append(cmd_fill(Vec3(rect.x1 + 1, y + h, (rect.z1 + rect.z2) // 2),
                             Vec3(rect.x2 - 1, y + h, (rect.z1 + rect.z2) // 2), "iron_bars"))
        midx = (rect.x1 + rect.x2) // 2
        cmds += _column(midx, (rect.z1 + rect.z2) // 2, y + h - 3, y + h - 1, "chain", "[axis=y]")
        return cmds, minimal_geometry(brief, rect, y + h)


@register
class DockFinger(Archetype):
    name = "dock_finger"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        pal = brief.palette
        y = brief.origin_y
        cmds = []
        # pier deck on log piles
        cmds.append(cmd_fill(Vec3(rect.x1, y, rect.z1), Vec3(rect.x2, y, rect.z2),
                             pal.floor or "spruce_planks"))
        for x in range(rect.x1, rect.x2 + 1, 3):
            for z in (rect.z1, rect.z2):
                cmds += _column(x, z, y - 3, y - 1, "spruce_log", "[axis=y]")
        # bollards
        for x in range(rect.x1 + 1, rect.x2, 4):
            cmds.append(cmd_set(Vec3(x, y + 1, rect.z1), "oak_fence"))
        return cmds, minimal_geometry(brief, rect, y + 1)
