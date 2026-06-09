"""
Deterministic BSP floorplan — rooms, internal walls, and door openings.

Connectivity is guaranteed *by construction*: every recursive split inserts
exactly one wall with exactly one door between its two halves, so the room
adjacency graph is the BSP tree — connected and acyclic. No search needed; a BFS
assertion in the tests confirms it.
"""
from __future__ import annotations

import random

from architecture.geometry import Opening, Rect, Vec3, Zone, cmd_fill


def generate_floorplan(interior: Rect, room_program: list[str], floor_y: int,
                       ceil_y: int, palette, rng: random.Random
                       ) -> tuple[list[str], list[Zone]]:
    """interior = the space inside the outer walls (already inset by 1)."""
    n = len(room_program)
    if n <= 1 or interior.width < 8 or interior.depth < 8:
        zone = Zone(name=(room_program[0] if room_program else "living"),
                    rect=interior, floor_y=floor_y, ceil_y=ceil_y)
        return [], [zone]

    leaves: list[Rect] = []
    wall_cmds: list[str] = []
    doors: list[tuple[Rect, Rect, Opening]] = []
    _split(interior, n, floor_y, ceil_y, palette, rng, leaves, wall_cmds, doors)

    # Carve every door AFTER all internal walls so a deeper split's wall can never
    # re-block a shallower split's opening. Order is preserved by _clean_ordered.
    door_cmds: list[str] = []
    for _, _, op in doors:
        if op.face in ("E", "W"):       # vertical wall along z -> carve in x line cell
            door_cmds.append(cmd_fill(Vec3(op.x, op.y, op.z), Vec3(op.x, op.y + 1, op.z), "air"))
            door_cmds.append(cmd_fill(Vec3(op.x - 1, op.y, op.z), Vec3(op.x + 1, op.y + 1, op.z), "air"))
        else:                            # horizontal wall along x
            door_cmds.append(cmd_fill(Vec3(op.x, op.y, op.z), Vec3(op.x, op.y + 1, op.z), "air"))
            door_cmds.append(cmd_fill(Vec3(op.x, op.y, op.z - 1), Vec3(op.x, op.y + 1, op.z + 1), "air"))
    cmds = wall_cmds + door_cmds

    # assign program: largest leaf -> first program entry (living), etc.
    order = sorted(range(len(leaves)), key=lambda i: leaves[i].area, reverse=True)
    names = list(room_program) + ["room"] * (len(leaves) - len(room_program))
    zones: list[Zone] = []
    for rank, idx in enumerate(order):
        zones.append(Zone(name=names[rank], rect=leaves[idx],
                          floor_y=floor_y, ceil_y=ceil_y))
    # attach door openings to the zones they touch
    for ra, rb, opening in doors:
        for z in zones:
            if z.rect is ra or z.rect is rb:
                z.doors.append(opening)
    return cmds, zones


def _split(rect: Rect, n: int, floor_y: int, ceil_y: int, palette, rng,
           leaves: list[Rect], cmds: list[str],
           doors: list[tuple[Rect, Rect, Opening]]) -> None:
    if n <= 1 or (rect.width < 8 and rect.depth < 8):
        leaves.append(rect)
        return
    n_left = n // 2
    n_right = n - n_left
    horizontal = rect.width >= rect.depth  # split across the longer axis

    if horizontal and rect.width >= 8:
        sx = rect.x1 + _split_point(rect.width, rng)
        left = Rect(rect.x1, rect.z1, sx, rect.z2)
        right = Rect(sx, rect.z1, rect.x2, rect.z2)
        cmds.append(cmd_fill(Vec3(sx, floor_y + 1, rect.z1), Vec3(sx, ceil_y, rect.z2), palette.trim))
        dz = (rect.z1 + rect.z2) // 2
        opening = Opening("E", sx, floor_y + 1, dz, 1, 2, "door")
        _recurse(left, right, n_left, n_right, floor_y, ceil_y, palette, rng,
                 leaves, cmds, doors, opening)
    elif rect.depth >= 8:
        sz = rect.z1 + _split_point(rect.depth, rng)
        left = Rect(rect.x1, rect.z1, rect.x2, sz)
        right = Rect(rect.x1, sz, rect.x2, rect.z2)
        cmds.append(cmd_fill(Vec3(rect.x1, floor_y + 1, sz), Vec3(rect.x2, ceil_y, sz), palette.trim))
        dx = (rect.x1 + rect.x2) // 2
        opening = Opening("S", dx, floor_y + 1, sz, 1, 2, "door")
        _recurse(left, right, n_left, n_right, floor_y, ceil_y, palette, rng,
                 leaves, cmds, doors, opening)
    else:
        leaves.append(rect)


def _recurse(left, right, n_left, n_right, floor_y, ceil_y, palette, rng,
             leaves, cmds, doors, opening) -> None:
    before = len(leaves)
    _split(left, n_left, floor_y, ceil_y, palette, rng, leaves, cmds, doors)
    la = leaves[before] if len(leaves) > before else left
    before2 = len(leaves)
    _split(right, n_right, floor_y, ceil_y, palette, rng, leaves, cmds, doors)
    rb = leaves[before2] if len(leaves) > before2 else right
    doors.append((la, rb, opening))


def _split_point(length: int, rng: random.Random) -> int:
    lo = max(4, int(length * 0.40))
    hi = min(length - 4, int(length * 0.60))
    if hi < lo:
        return length // 2
    return rng.randint(lo, hi)
