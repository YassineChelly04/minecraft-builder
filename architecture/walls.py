"""
Shell 2.0 wall system — the depth rules pro builders use, as deterministic code.

Per exterior face, in order: plinth -> pillars (protruding 1 outward) -> infill ->
bays with recessed windows (never on a pillar) -> cornice lip -> door opening.

build_walls(rect, floor_y, height, palette, front_face, rng) -> (cmds, walls, door)
where `height` is the number of storeys' worth of total Y (floor..wall_top inclusive
is height-1 courses) and `door` is the front Opening.
"""
from __future__ import annotations

import random

from architecture.geometry import (
    Bay, Face, OUTWARD, OUTWARD_FACING, INWARD, Opening, Rect, Vec3, Wall,
    cmd_fill, cmd_set,
)
from architecture.texture import textured_fill


def pillar_offsets(length: int) -> list[int]:
    """Corners always, plus interior pillars so every bay is ≥3 wide."""
    if length <= 6:
        return [0, length - 1]
    # pick a spacing in 4..6 that leaves bays ≥3 (gap ≥4 between pillar centres)
    best = 5
    for step in (5, 6, 4):
        if (length - 1) % step != 1:  # avoid a 1-wide leftover bay at the end
            best = step
            break
    offs = list(range(0, length - 1, best))
    if offs[-1] != length - 1:
        offs.append(length - 1)
    return offs


def _face_axis(face: Face, rect: Rect):
    """Return (length, pos(t)->(x,z), outward(ox,oz))."""
    ox, oz = OUTWARD[face]
    if face == "N":
        return rect.width, (lambda t: (rect.x1 + t, rect.z1)), (ox, oz)
    if face == "S":
        return rect.width, (lambda t: (rect.x1 + t, rect.z2)), (ox, oz)
    if face == "W":
        return rect.depth, (lambda t: (rect.x1, rect.z1 + t)), (ox, oz)
    return rect.depth, (lambda t: (rect.x2, rect.z1 + t)), (ox, oz)


def build_walls(rect: Rect, floor_y: int, height: int, palette,
                front_face: Face, rng: random.Random
                ) -> tuple[list[str], list[Wall], Opening]:
    cmds: list[str] = []
    walls: list[Wall] = []
    wall_lo = floor_y + 1
    wall_top = floor_y + height - 1
    if wall_top < wall_lo + 1:
        wall_top = wall_lo + 1
    dom, trim, accent = palette.dominant, palette.trim, palette.accent
    glass, roof_stair = palette.glass, palette.roof

    door: Opening | None = None

    for face in ("N", "S", "E", "W"):
        length, pos, (ox, oz) = _face_axis(face, rect)
        offs = pillar_offsets(length)
        base_x, base_z = pos(0)
        wall = Wall(face=face, base=Vec3(base_x, wall_lo, base_z),
                    length=length, height=wall_top - wall_lo + 1,
                    pillars=offs, outward=(ox, oz))

        # 1. infill (dominant, textured if the palette has wear) across the face.
        a = Vec3(pos(0)[0], wall_lo, pos(0)[1])
        b = Vec3(pos(length - 1)[0], wall_top, pos(length - 1)[1])
        if palette.wear:
            cmds += textured_fill(a, b, dom, list(palette.wear),
                                  palette.wear_density, rng)
        else:
            cmds.append(cmd_fill(a, b, dom))

        # 2. plinth — bottom course in trim.
        cmds.append(cmd_fill(Vec3(pos(0)[0], wall_lo, pos(0)[1]),
                             Vec3(pos(length - 1)[0], wall_lo, pos(length - 1)[1]), trim))

        # 3. pillars — full height in trim, protruding 1 block outward.
        for t in offs:
            px, pz = pos(t)
            cmds.append(cmd_fill(Vec3(px, wall_lo, pz), Vec3(px, wall_top, pz), trim))
            cmds.append(cmd_fill(Vec3(px + ox, wall_lo, pz + oz),
                                 Vec3(px + ox, wall_top, pz + oz), trim))

        # 4. bays + recessed windows (skip the door bay on the front face).
        door_bay = _door_bay_index(offs, length) if face == front_face else -1
        for i in range(len(offs) - 1):
            p0, p1 = offs[i], offs[i + 1]
            bay_len = p1 - p0 - 1
            if bay_len < 1:
                continue
            bx0, bz0 = pos(p0 + 1)
            bay = Bay(face=face, start=Vec3(bx0, wall_lo, bz0), length=bay_len,
                      height=wall_top - wall_lo + 1)
            if i == door_bay:
                bay.on_door_segment = True
                wall.bays.append(bay)
                continue
            if bay_len >= 3:
                bay.has_window = True
                cmds += _window(pos, p0 + 1, p1 - 1, wall_lo, wall_top, ox, oz,
                                glass, trim, roof_stair, face)
            wall.bays.append(bay)

        # 5. cornice — outward-protruding upside-down stair lip in trim.
        for t in range(length):
            px, pz = pos(t)
            cmds.append(cmd_set(Vec3(px + ox, wall_top, pz + oz), roof_stair,
                                f"[facing={INWARD[face]},half=top]"))

        # 6. door on the front face.
        if face == front_face:
            door = _cut_door(cmds, pos, offs, door_bay, wall_lo, base_z, base_x,
                             ox, oz, face, palette)
            wall.openings.append(door)
        walls.append(wall)

    assert door is not None
    return cmds, walls, door


def _door_bay_index(offs: list[int], length: int) -> int:
    """Index of the bay nearest the face centre."""
    mid = length / 2
    best, bestd = 0, 1e9
    for i in range(len(offs) - 1):
        c = (offs[i] + offs[i + 1]) / 2
        if abs(c - mid) < bestd:
            best, bestd = i, abs(c - mid)
    return best


def _window(pos, t0: int, t1: int, wall_lo: int, wall_top: int, ox: int, oz: int,
            glass: str, trim: str, roof_stair: str, face: Face) -> list[str]:
    cmds: list[str] = []
    wy1 = wall_lo + 1
    wy2 = min(wall_lo + 2, wall_top - 1)
    if wy2 < wy1:
        return cmds
    facing = OUTWARD_FACING[face]
    for t in range(t0, t1 + 1):
        x, z = pos(t)
        # opening + glass at the wall plane
        cmds.append(cmd_fill(Vec3(x, wy1, z), Vec3(x, wy2, z), "air"))
        cmds.append(cmd_fill(Vec3(x, wy1, z), Vec3(x, wy2, z), glass))
        # sill below (stair, bottom half, facing outward) and lintel above (top half)
        cmds.append(cmd_set(Vec3(x, wy1 - 1, z), roof_stair, f"[facing={facing},half=bottom]"))
        if wy2 + 1 <= wall_top:
            cmds.append(cmd_set(Vec3(x, wy2 + 1, z), roof_stair, f"[facing={facing},half=top]"))
    return cmds


def _cut_door(cmds: list[str], pos, offs: list[int], door_bay: int, wall_lo: int,
              base_z: int, base_x: int, ox: int, oz: int, face: Face, palette) -> Opening:
    p0, p1 = offs[door_bay], offs[door_bay + 1]
    tc = (p0 + p1) // 2
    x, z = pos(tc)
    # 1-wide (door) + the cell beside it: a 2-wide, 3-high opening
    x2, z2 = pos(min(tc + 1, p1 - 1)) if p1 - p0 >= 3 else (x, z)
    cmds.append(cmd_fill(Vec3(min(x, x2), wall_lo, min(z, z2)),
                         Vec3(max(x, x2), wall_lo + 2, max(z, z2)), "air"))
    cmds.append(cmd_set(Vec3(x, wall_lo, z), palette.mc(_door_block(palette)),
                        f"[facing={OUTWARD_FACING[face]},half=lower]"))
    return Opening(face=face, x=x, y=wall_lo, z=z, w=2, h=3, kind="door")


def _door_block(palette) -> str:
    # pick a door material loosely matching the palette dominant
    dom = palette.dominant
    for wood in ("spruce", "dark_oak", "oak", "birch", "cherry", "acacia"):
        if wood in dom:
            return f"{wood}_door"
    return "oak_door"
