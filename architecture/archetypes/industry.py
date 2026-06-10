"""
Manufacturer archetypes — the building blocks of factory.planner layouts. Same
contract as library.py: deterministic + seeded, validator-clean at any lot size.
Shell-based stages add signature detail over the watertight envelope; the big
process structures (hangar, fab, blast furnace, silos, tanks) are custom open
builds like Stadium/Refinery.
"""
from __future__ import annotations

from architecture.archetypes.base import Archetype, minimal_geometry, register
from architecture.archetypes.library import _column, _cylinder, _ring
from architecture.geometry import Rect, Vec3, cmd_fill, cmd_set


def _box_walls(rect: Rect, y0: int, y1: int, block: str) -> list[str]:
    return [cmd_fill(Vec3(rect.x1, y0, rect.z1), Vec3(rect.x2, y1, rect.z1), block),
            cmd_fill(Vec3(rect.x1, y0, rect.z2), Vec3(rect.x2, y1, rect.z2), block),
            cmd_fill(Vec3(rect.x1, y0, rect.z1), Vec3(rect.x1, y1, rect.z2), block),
            cmd_fill(Vec3(rect.x2, y0, rect.z1), Vec3(rect.x2, y1, rect.z2), block)]


def _window_band(rect: Rect, y0: int, y1: int, glass: str) -> list[str]:
    """Glass strip around all four walls (inset 2 from the corners)."""
    return [cmd_fill(Vec3(rect.x1 + 2, y0, rect.z1), Vec3(rect.x2 - 2, y1, rect.z1), glass),
            cmd_fill(Vec3(rect.x1 + 2, y0, rect.z2), Vec3(rect.x2 - 2, y1, rect.z2), glass),
            cmd_fill(Vec3(rect.x1, y0, rect.z1 + 2), Vec3(rect.x1, y1, rect.z2 - 2), glass),
            cmd_fill(Vec3(rect.x2, y0, rect.z1 + 2), Vec3(rect.x2, y1, rect.z2 - 2), glass)]


def _vent_stacks(rect: Rect, roof_y: int, n: int, block: str) -> list[str]:
    """Short rooftop extraction stacks along the centreline."""
    cmds = []
    cx_step = max(3, rect.width // (n + 1))
    cz = (rect.z1 + rect.z2) // 2
    for i in range(n):
        x = rect.x1 + cx_step * (i + 1)
        if x >= rect.x2:
            break
        cmds.append(cmd_fill(Vec3(x, roof_y + 1, cz), Vec3(x, roof_y + 3, cz), block))
        cmds.append(cmd_set(Vec3(x, roof_y + 4, cz), "iron_bars"))
    return cmds


# ── shell-based process stages ───────────────────────────────────────────────

@register
class AssemblyHall(Archetype):
    """The long final-assembly hall (automotive): sawtooth roofline, a line of
    big door bays down the front, and the conveyor strip visible at each gate."""
    name = "assembly_hall"
    roof_kind = "sawtooth"
    furnished = False

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        pal = brief.palette
        y = brief.origin_y
        cmds = []
        for x in range(rect.x1 + 3, rect.x2 - 2, 8):
            cmds.append(cmd_fill(Vec3(x, y + 1, rect.z2), Vec3(x + 2, y + 3, rect.z2), "air"))
            cmds.append(cmd_fill(Vec3(x - 1, y + 1, rect.z2), Vec3(x - 1, y + 4, rect.z2), pal.trim))
            cmds.append(cmd_fill(Vec3(x + 3, y + 1, rect.z2), Vec3(x + 3, y + 4, rect.z2), pal.trim))
            cmds.append(cmd_fill(Vec3(x, y, rect.z2 + 1), Vec3(x + 2, y, rect.z2 + 2), "smooth_stone"))
        return cmds


@register
class PressShop(Archetype):
    """Stamping plant: tall sealed hall, roof crane rail, steel coils in the yard."""
    name = "press_shop"
    roof_kind = "flat_parapet"
    furnished = False

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        pal = brief.palette
        y = brief.origin_y
        top = geom.roof_base_y
        cmds = [cmd_fill(Vec3(rect.x1 + 1, top - 1, (rect.z1 + rect.z2) // 2),
                         Vec3(rect.x2 - 1, top - 1, (rect.z1 + rect.z2) // 2), "iron_bars")]
        # steel coil stacks beside the entrance (lying cylinders abstracted as rings)
        for i, cx in enumerate(range(rect.x1 + 2, min(rect.x1 + 11, rect.x2 - 1), 4)):
            cmds += _cylinder(cx, rect.z2 + 3, 1.4, y + 1, y + 2, "iron_block")
        cmds.append(cmd_fill(Vec3(rect.x1 + 1, y + 1, rect.z2), Vec3(rect.x1 + 3, y + 4, rect.z2), "air"))
        cmds.append(cmd_fill(Vec3(rect.x1, y + 1, rect.z2), Vec3(rect.x1, y + 5, rect.z2), pal.trim))
        cmds.append(cmd_fill(Vec3(rect.x1 + 4, y + 1, rect.z2), Vec3(rect.x1 + 4, y + 5, rect.z2), pal.trim))
        return cmds


@register
class PaintShop(Archetype):
    """Paint hall: sealed white box (no shell windows to keep dust out is faked
    with a white band), rooftop extraction stacks."""
    name = "paint_shop"
    roof_kind = "flat_parapet"
    furnished = False

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        y = brief.origin_y
        top = geom.roof_base_y
        cmds = _box_walls(rect, y + 2, y + 3, "white_concrete")
        cmds += _vent_stacks(rect, top, 3, "white_concrete")
        return cmds


@register
class CleanHall(Archetype):
    """High-hygiene packaging / assembly-and-test hall: white skin, one blue
    glass clerestory band, minimal ground openings."""
    name = "clean_hall"
    roof_kind = "flat_parapet"
    furnished = False

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        y = brief.origin_y
        h = max(4, geom.roof_base_y - y - 1)
        cmds = _box_walls(rect, y + 1, y + h, "white_concrete")
        cmds += _window_band(rect, y + h - 1, y + h - 1, "light_blue_stained_glass_pane")
        # personnel airlock porch on the front
        cx = (rect.x1 + rect.x2) // 2
        cmds.append(cmd_fill(Vec3(cx, y + 1, rect.z2), Vec3(cx + 1, y + 3, rect.z2), "air"))
        cmds.append(cmd_fill(Vec3(cx - 1, y + 1, rect.z2 + 1), Vec3(cx + 2, y + 3, rect.z2 + 1), "white_concrete"))
        cmds.append(cmd_fill(Vec3(cx, y + 1, rect.z2 + 1), Vec3(cx + 1, y + 3, rect.z2 + 1), "air"))
        return cmds


@register
class RollingMill(Archetype):
    """The very long steel hall: open gates at BOTH ends so the line runs
    straight through, monitor vents down the spine."""
    name = "rolling_mill"
    roof_kind = "sawtooth"
    furnished = False

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        pal = brief.palette
        y = brief.origin_y
        cz = (rect.z1 + rect.z2) // 2
        cmds = []
        for x in (rect.x1, rect.x2):   # through-gates on the flow axis
            cmds.append(cmd_fill(Vec3(x, y + 1, cz - 1), Vec3(x, y + 4, cz + 1), "air"))
        # glowing strand: the hot slab line through the hall
        cmds.append(cmd_fill(Vec3(rect.x1 + 1, y, cz), Vec3(rect.x2 - 1, y, cz), "magma_block"))
        cmds += _vent_stacks(rect, geom.roof_base_y, 4, pal.trim)
        return cmds


@register
class Brewhouse(Archetype):
    """Brewhouse: the showpiece — copper kettle domes rising through the roof."""
    name = "brewhouse"
    roof_kind = "flat_parapet"
    furnished = False

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        y = brief.origin_y
        top = geom.roof_base_y
        cmds = []
        cz = (rect.z1 + rect.z2) // 2
        for i, cx in enumerate(range(rect.x1 + 4, rect.x2 - 3, 7)):
            if cx + 2 > rect.x2 - 1:
                break
            cmds += _cylinder(cx, cz, 2.2, top, top + 2, "copper_block")
            cmds += _ring(cx, cz, 1.4, top + 3, "copper_block")
            cmds.append(cmd_set(Vec3(cx, top + 4, cz), "cut_copper"))
        return cmds


@register
class HighBayWarehouse(Archetype):
    """Automated high-bay store: the tall windowless slab next to packaging."""
    name = "high_bay_warehouse"
    roof_kind = "flat_parapet"
    furnished = False

    def detail(self, brief, geom):
        rect = geom.footprint[0]
        pal = brief.palette
        y = brief.origin_y
        h = max(4, geom.roof_base_y - y - 1)
        cmds = _box_walls(rect, y + 3, y + h, pal.dominant)        # seal the windows
        # vertical accent ribs every 5 blocks
        for x in range(rect.x1 + 2, rect.x2 - 1, 5):
            cmds.append(cmd_fill(Vec3(x, y + 1, rect.z2), Vec3(x, y + h, rect.z2), pal.accent))
        # truck dock canopy
        cmds.append(cmd_fill(Vec3(rect.x1 + 1, y + 4, rect.z2 + 1), Vec3(rect.x2 - 1, y + 4, rect.z2 + 2), pal.trim))
        return cmds


# ── custom open structures ───────────────────────────────────────────────────

@register
class AssemblyHangar(Archetype):
    """Aerospace FAL: one giant hall with a near-full-width sliding door,
    clerestory glazing, and roof trusses — the Airbus/Boeing silhouette."""
    name = "assembly_hangar"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        pal = brief.palette
        y = brief.origin_y
        h = max(12, brief.height_band[1])
        cmds = [cmd_fill(Vec3(rect.x1, y, rect.z1), Vec3(rect.x2, y, rect.z2), "smooth_stone")]
        cmds += _box_walls(rect, y + 1, y + h, pal.dominant)
        cmds += _window_band(rect, y + h - 2, y + h - 1, pal.glass)
        # roof deck + truss beams across
        cmds.append(cmd_fill(Vec3(rect.x1, y + h + 1, rect.z1), Vec3(rect.x2, y + h + 1, rect.z2), pal.trim))
        for x in range(rect.x1 + 3, rect.x2 - 2, 6):
            cmds.append(cmd_fill(Vec3(x, y + h, rect.z1 + 1), Vec3(x, y + h, rect.z2 - 1), "iron_bars"))
        # the giant sliding door: nearly the whole front face opens
        dx1, dx2 = rect.x1 + 3, rect.x2 - 3
        cmds.append(cmd_fill(Vec3(dx1, y + 1, rect.z2), Vec3(dx2, y + h - 3, rect.z2), "air"))
        third = max(1, (dx2 - dx1) // 3)
        cmds.append(cmd_fill(Vec3(dx1, y + 1, rect.z2), Vec3(dx1 + third, y + h - 3, rect.z2),
                             "light_gray_concrete"))
        cmds.append(cmd_fill(Vec3(dx2 - third, y + 1, rect.z2), Vec3(dx2, y + h - 3, rect.z2),
                             "light_gray_concrete"))
        # company-stripe across the door header
        cmds.append(cmd_fill(Vec3(dx1, y + h - 2, rect.z2), Vec3(dx2, y + h - 2, rect.z2), pal.accent))
        return cmds, minimal_geometry(brief, rect, y + h + 1)


@register
class Apron(Archetype):
    """Open hardstand: flight line / marshalling / finished-goods yard with
    painted bay markings and perimeter floodlights."""
    name = "apron"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        pal = brief.palette
        y = brief.origin_y
        cmds = [cmd_fill(Vec3(rect.x1, y, rect.z1), Vec3(rect.x2, y, rect.z2), "light_gray_concrete")]
        for x in range(rect.x1 + 4, rect.x2 - 2, 8):   # bay stripes
            cmds.append(cmd_fill(Vec3(x, y, rect.z1 + 2), Vec3(x, y, rect.z2 - 2), "white_concrete"))
        for fx, fz in ((rect.x1 + 1, rect.z1 + 1), (rect.x2 - 1, rect.z1 + 1),
                       (rect.x1 + 1, rect.z2 - 1), (rect.x2 - 1, rect.z2 - 1)):
            cmds += _column(fx, fz, y + 1, y + 6, pal.trim)
            cmds.append(cmd_set(Vec3(fx, y + 7, fz), "sea_lantern"))
        return cmds, minimal_geometry(brief, rect, y + 7)


@register
class SiloBattery(Archetype):
    """Raw-material silos: a rank of tall cylinders, top gallery, fill chutes."""
    name = "silo_battery"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        pal = brief.palette
        y = brief.origin_y
        h = max(10, brief.height_band[1])
        r = max(2, min(3, rect.depth // 3))
        cmds = [cmd_fill(Vec3(rect.x1, y, rect.z1), Vec3(rect.x2, y, rect.z2), "gravel")]
        cz = (rect.z1 + rect.z2) // 2
        xs = list(range(rect.x1 + r + 1, rect.x2 - r, 2 * r + 2))
        for cx in xs:
            cmds += _cylinder(cx, cz, r, y + 1, y + h, "smooth_stone")
            cmds += _ring(cx, cz, r, y + h // 2, pal.accent)
            cmds.append(cmd_fill(Vec3(cx - r + 1, y + h, cz - r + 1),
                                 Vec3(cx + r - 1, y + h, cz + r - 1), pal.trim))
        if xs:  # top conveyor gallery linking all silos
            cmds.append(cmd_fill(Vec3(xs[0], y + h + 1, cz), Vec3(xs[-1], y + h + 1, cz), pal.trim))
            cmds.append(cmd_fill(Vec3(xs[0], y + h + 2, cz), Vec3(xs[-1], y + h + 2, cz), "iron_bars"))
        return cmds, minimal_geometry(brief, rect, y + h + 2)


@register
class FermentationCellar(Archetype):
    """Two rows of upright fermenters with a catwalk between — the brewery
    cellar yard."""
    name = "fermentation_cellar"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        pal = brief.palette
        y = brief.origin_y
        h = 7 + brief.seed % 3
        cmds = [cmd_fill(Vec3(rect.x1, y, rect.z1), Vec3(rect.x2, y, rect.z2), "smooth_stone")]
        for cz in (rect.z1 + 3, rect.z2 - 3):
            for cx in range(rect.x1 + 3, rect.x2 - 2, 6):
                cmds += _cylinder(cx, cz, 2, y + 1, y + h, "iron_block")
                cmds.append(cmd_set(Vec3(cx, y + h + 1, cz), pal.accent))  # cone top
        midz = (rect.z1 + rect.z2) // 2
        cmds.append(cmd_fill(Vec3(rect.x1 + 1, y + 3, midz), Vec3(rect.x2 - 1, y + 3, midz), pal.trim))
        cmds.append(cmd_fill(Vec3(rect.x1 + 1, y + 4, midz), Vec3(rect.x2 - 1, y + 4, midz), "iron_bars"))
        return cmds, minimal_geometry(brief, rect, y + h + 1)


@register
class BlastFurnace(Archetype):
    """Ironmaking block: the furnace stack with glowing taphole, three hot
    stoves, and the inclined charge conveyor — unmistakably a steelworks."""
    name = "blast_furnace"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        pal = brief.palette
        y = brief.origin_y
        h = max(14, brief.height_band[1] + 4)
        cx = rect.x1 + rect.width // 3
        cz = (rect.z1 + rect.z2) // 2
        cmds = [cmd_fill(Vec3(rect.x1, y, rect.z1), Vec3(rect.x2, y, rect.z2), "gravel")]
        # furnace stack: wide base, narrow throat
        cmds += _cylinder(cx, cz, 4, y + 1, y + h // 2, pal.dominant)
        cmds += _cylinder(cx, cz, 3, y + h // 2, y + h, pal.dominant)
        cmds += _ring(cx, cz, 3, y + h, "iron_bars")
        cmds.append(cmd_set(Vec3(cx, y + h + 1, cz), "campfire", "[lit=true]"))
        # glowing taphole + slag runner at the base
        cmds.append(cmd_fill(Vec3(cx + 4, y + 1, cz), Vec3(min(cx + 8, rect.x2 - 1), y + 1, cz), "magma_block"))
        # three hot stoves in a rank
        for i in range(3):
            sx = cx - 4 - i * 4
            if sx - 2 < rect.x1:
                break
            cmds += _cylinder(sx, rect.z1 + 3, 1.6, y + 1, y + h - 4, "iron_block")
            cmds += _ring(sx, rect.z1 + 3, 1.6, y + h - 4, pal.accent)
        # inclined charge conveyor up to the throat
        steps = min(h, rect.x2 - cx - 1)
        for i in range(steps):
            cmds.append(cmd_set(Vec3(cx + 1 + i, y + h - i, cz), pal.trim))
        return cmds, minimal_geometry(brief, rect, y + h + 1)


@register
class CleanroomFab(Archetype):
    """Semiconductor fab: a huge white monolith, blue glazing stripe, and the
    rooftop air-handling plant with stack farm (Intel/TSMC silhouette)."""
    name = "cleanroom_fab"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        y = brief.origin_y
        h = max(12, brief.height_band[1])
        cmds = [cmd_fill(Vec3(rect.x1, y, rect.z1), Vec3(rect.x2, y, rect.z2), "smooth_stone")]
        cmds += _box_walls(rect, y + 1, y + h, "white_concrete")
        cmds += _window_band(rect, y + h // 2, y + h // 2, "light_blue_stained_glass_pane")
        cmds.append(cmd_fill(Vec3(rect.x1, y + h + 1, rect.z1), Vec3(rect.x2, y + h + 1, rect.z2),
                             "light_gray_concrete"))
        # rooftop AHU boxes + exhaust stacks
        plant = rect.inset(max(2, rect.width // 6))
        cmds.append(cmd_fill(Vec3(plant.x1, y + h + 2, plant.z1),
                             Vec3(plant.x2, y + h + 3, plant.z2), "light_gray_concrete"))
        for x in range(plant.x1 + 2, plant.x2 - 1, 6):
            cmds.append(cmd_fill(Vec3(x, y + h + 4, (plant.z1 + plant.z2) // 2),
                                 Vec3(x, y + h + 6, (plant.z1 + plant.z2) // 2), "iron_block"))
        # main entrance
        cx = (rect.x1 + rect.x2) // 2
        cmds.append(cmd_fill(Vec3(cx - 1, y + 1, rect.z2), Vec3(cx + 1, y + 3, rect.z2), "air"))
        return cmds, minimal_geometry(brief, rect, y + h + 6)


@register
class CoolingTower(Archetype):
    """Hyperboloid cooling tower: rings that pinch at two-thirds height."""
    name = "cooling_tower"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        y = brief.origin_y
        cx, cz = rect.center()
        rmax = max(3, min(rect.width, rect.depth) // 2 - 1)
        h = max(12, brief.height_band[1] + 2)
        waist = int(h * 0.66)
        cmds = []
        for dy in range(h + 1):
            t = abs(dy - waist) / max(1, waist)
            r = max(2.0, rmax * (0.62 + 0.38 * t * t))
            cmds += _ring(cx, cz, r, y + dy, "white_concrete" if dy % 2 else "light_gray_concrete")
        cmds.append(cmd_set(Vec3(cx, y + h + 1, cz), "campfire", "[lit=true]"))  # plume
        return cmds, minimal_geometry(brief, rect, y + h)


@register
class TankFarm(Archetype):
    """Bulk liquid storage: big tanks inside bund walls + a pipe rack edge."""
    name = "tank_farm"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        pal = brief.palette
        y = brief.origin_y
        cmds = [cmd_fill(Vec3(rect.x1, y, rect.z1), Vec3(rect.x2, y, rect.z2), "gravel")]
        cmds += _box_walls(rect, y + 1, y + 1, pal.trim)            # bund wall
        r = max(2, min(rect.width, rect.depth) // 5)
        th = 5 + brief.seed % 3
        for cx in range(rect.x1 + r + 2, rect.x2 - r - 1, 2 * r + 3):
            for cz in range(rect.z1 + r + 2, rect.z2 - r - 1, 2 * r + 3):
                cmds += _cylinder(cx, cz, r, y + 1, y + th, "iron_block")
                cmds += _ring(cx, cz, r, y + th, pal.accent)
        # pipe rack along the back edge
        pz = rect.z1 + 1
        for py in (y + 3, y + 4):
            cmds.append(cmd_fill(Vec3(rect.x1 + 1, py, pz), Vec3(rect.x2 - 1, py, pz), "iron_bars"))
        for x in range(rect.x1 + 2, rect.x2 - 1, 5):
            cmds += _column(x, pz, y + 1, y + 2, pal.trim)
        return cmds, minimal_geometry(brief, rect, y + th + 1)


@register
class Guardhouse(Archetype):
    """Gate kiosk with a barrier arm — every plant entrance has one."""
    name = "guardhouse"
    furnished = False

    def build(self, brief):
        rect = brief.lot
        pal = brief.palette
        y = brief.origin_y
        cx, cz = rect.center()
        hut = Rect(cx - 2, cz - 2, cx + 2, cz + 2)
        cmds = [cmd_fill(Vec3(hut.x1, y, hut.z1), Vec3(hut.x2, y, hut.z2), pal.trim)]
        cmds += _box_walls(hut, y + 1, y + 3, pal.dominant)
        cmds += _window_band(hut, y + 2, y + 2, pal.glass)
        cmds.append(cmd_fill(Vec3(hut.x1, y + 4, hut.z1), Vec3(hut.x2, y + 4, hut.z2), pal.trim))
        cmds.append(cmd_fill(Vec3(cx, y + 1, hut.z2), Vec3(cx, y + 2, hut.z2), "air"))  # door
        # barrier arm across the gate lane
        cmds.append(cmd_fill(Vec3(hut.x2 + 1, y + 1, cz), Vec3(hut.x2 + 1, y + 1, cz), pal.accent))
        cmds.append(cmd_fill(Vec3(hut.x2 + 1, y + 2, cz), Vec3(min(hut.x2 + 5, rect.x2), y + 2, cz),
                             "white_concrete"))
        return cmds, minimal_geometry(brief, rect, y + 4)
