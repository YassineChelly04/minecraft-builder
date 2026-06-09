"""
Furniture placers — the interior_skills.py recipes promoted from prose to code,
parameterised by wall/orientation. Each places solid props along a wall and
claims the floor cells it uses (so ops don't overlap and walkability is preserved).

Signature: fn(zone, *, rng, palette, version) -> PlacerResult.
Facing is computed from the wall via INWARD — never guessed.
"""
from __future__ import annotations

import random

from architecture.geometry import INWARD, Vec3, Zone, cmd_fill, cmd_set
from placers.base import PlacerResult

_WALLS = ("N", "S", "E", "W")


def _pick_wall(zone: Zone, rng: random.Random, length: int) -> tuple[str, list[Vec3]] | None:
    for face in rng.sample(_WALLS, len(_WALLS)):
        cells = zone.along_wall(face, length, clearance=1)
        if cells:
            return face, cells
    return None


def _claim(zone: Zone, cells: list[Vec3]) -> set[tuple[int, int]]:
    s = {(c.x, c.z) for c in cells}
    zone.claim(s)
    return s


def fireplace(zone: Zone, *, rng, palette, version="1.21.9") -> PlacerResult:
    pick = _pick_wall(zone, rng, 3)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    face, cells = pick
    c = cells[1]
    cmds = [
        cmd_set(Vec3(c.x, c.y - 1, c.z), palette.trim),               # non-flammable base
        cmd_set(c, "campfire", "[lit=true]"),
        cmd_set(cells[0], "iron_bars"),
        cmd_set(cells[2], "iron_bars"),
        cmd_fill(Vec3(c.x, c.y + 1, c.z), Vec3(c.x, c.y + 2, c.z), palette.trim),  # flue stub
    ]
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


def sofa(zone: Zone, *, rng, palette, version="1.21.9") -> PlacerResult:
    pick = _pick_wall(zone, rng, 3)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    face, cells = pick
    facing = INWARD[face]
    stair = palette.roof
    cmds = [cmd_set(c, stair, f"[facing={facing},half=bottom]") for c in cells]
    cmds.append(cmd_set(cells[0], "oak_trapdoor", f"[facing={facing}]"))
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


def bed(zone: Zone, *, rng, palette, version="1.21.9") -> PlacerResult:
    pick = _pick_wall(zone, rng, 2)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    face, cells = pick
    cmds = [cmd_set(cells[0], "red_bed", f"[facing={INWARD[face]},part=foot]")]
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


def dining_set(zone: Zone, *, rng, palette, version="1.21.9") -> PlacerResult:
    c = zone.free_center()
    cells = [c]
    cmds = [cmd_set(c, "oak_fence"),
            cmd_set(Vec3(c.x, c.y + 1, c.z), "oak_pressure_plate")]
    for dx, dz in ((1, 0), (-1, 0)):
        chair = Vec3(c.x + dx, c.y, c.z + dz)
        face = "E" if dx < 0 else "W"
        cmds.append(cmd_set(chair, palette.roof, f"[facing={INWARD[face]},half=bottom]"))
        cells.append(chair)
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


def kitchen_run(zone: Zone, *, rng, palette, version="1.21.9") -> PlacerResult:
    pick = _pick_wall(zone, rng, 3)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    face, cells = pick
    cmds = [cmd_set(c, "smooth_stone_slab", "[type=top]") for c in cells]
    cmds.append(cmd_set(cells[0], "furnace", f"[facing={INWARD[face]}]"))
    cmds.append(cmd_set(cells[-1], "barrel"))
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


def desk(zone: Zone, *, rng, palette, version="1.21.9") -> PlacerResult:
    pick = _pick_wall(zone, rng, 2)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    face, cells = pick
    cmds = [cmd_set(cells[0], "smooth_stone_slab", "[type=top]"),
            cmd_set(cells[1], palette.roof, f"[facing={INWARD[face]},half=bottom]")]
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


def bookshelf_wall(zone: Zone, *, rng, palette, version="1.21.9") -> PlacerResult:
    pick = _pick_wall(zone, rng, 3)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    face, cells = pick
    cmds = []
    for c in cells:
        cmds.append(cmd_fill(c, Vec3(c.x, c.y + 1, c.z), "bookshelf"))
    cmds.append(cmd_set(cells[1], "lectern"))
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


def storage_wall(zone: Zone, *, rng, palette, version="1.21.9") -> PlacerResult:
    pick = _pick_wall(zone, rng, 3)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    face, cells = pick
    blocks = ["chest", "barrel", "chest"]
    cmds = [cmd_set(c, b, f"[facing={INWARD[face]}]" if b == "chest" else "")
            for c, b in zip(cells, blocks)]
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


def side_table(zone: Zone, *, rng, palette, version="1.21.9") -> PlacerResult:
    pick = _pick_wall(zone, rng, 1)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    face, cells = pick
    cmds = [cmd_set(cells[0], "oak_fence"),
            cmd_set(Vec3(cells[0].x, cells[0].y + 1, cells[0].z), palette.light,
                    "[hanging=false]" if "lantern" in palette.light else "")]
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


def plant(zone: Zone, *, rng, palette, version="1.21.9") -> PlacerResult:
    pick = _pick_wall(zone, rng, 1)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    face, cells = pick
    cmds = [cmd_set(cells[0], "flower_pot")]
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


# generic stand-ins for archetype/workshop kits
def crafting_bench(zone, *, rng, palette, version="1.21.9"):
    return storage_wall(zone, rng=rng, palette=palette, version=version)


def furnace_row(zone, *, rng, palette, version="1.21.9"):
    pick = _pick_wall(zone, rng, 3)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    face, cells = pick
    cmds = [cmd_set(c, "furnace", f"[facing={INWARD[face]}]") for c in cells]
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


def shelf_row(zone, *, rng, palette, version="1.21.9"):
    return bookshelf_wall(zone, rng=rng, palette=palette, version=version)


def barrel_stack(zone, *, rng, palette, version="1.21.9"):
    return storage_wall(zone, rng=rng, palette=palette, version=version)


def anvil_station(zone, *, rng, palette, version="1.21.9"):
    pick = _pick_wall(zone, rng, 1)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    return PlacerResult(cmds=[cmd_set(pick[1][0], "anvil")],
                        claimed=_claim(zone, pick[1]))


def rug(zone, *, rng, palette, version="1.21.9"):
    # rugs are decorative and must NOT block walking, so they don't claim/solidify
    c = zone.free_center()
    return PlacerResult(cmds=[], claimed=set())  # no-op in voxel terms (carpet passable)


def bathtub(zone, *, rng, palette, version="1.21.9"):
    pick = _pick_wall(zone, rng, 2)
    if not pick:
        return PlacerResult(ok=False, reason="no wall")
    face, cells = pick
    cmds = [cmd_set(cells[0], "white_concrete"), cmd_set(cells[1], "white_concrete")]
    return PlacerResult(cmds=cmds, claimed=_claim(zone, cells))


def ceiling_beams(zone, *, rng, palette, version="1.21.9"):
    cmds = []
    inner = zone.rect.inset(1)
    for x in range(inner.x1, inner.x2 + 1, 3):
        cmds.append(cmd_fill(Vec3(x, zone.ceil_y, inner.z1), Vec3(x, zone.ceil_y, inner.z2),
                             "spruce_log", "[axis=z]"))
    return PlacerResult(cmds=cmds, claimed=set())


FURNITURE_OPS = {
    "fireplace": fireplace, "sofa": sofa, "bed": bed, "dining_set": dining_set,
    "kitchen_run": kitchen_run, "desk": desk, "bookshelf_wall": bookshelf_wall,
    "storage_wall": storage_wall, "side_table": side_table, "plant": plant,
    "rug": rug, "bathtub": bathtub, "ceiling_beams": ceiling_beams,
    "crafting_bench": crafting_bench, "furnace_row": furnace_row,
    "shelf_row": shelf_row, "barrel_stack": barrel_stack, "anvil_station": anvil_station,
    "armchair": side_table, "coffee_table": dining_set, "chandelier": ceiling_beams,
    "bookshelf": bookshelf_wall,
}
