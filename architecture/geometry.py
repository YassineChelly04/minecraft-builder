"""
Core geometry contracts + the ONLY command formatters.

Face convention (documented, relied on everywhere):
    N = -z   S = +z   E = +x   W = -x

Command convention: helpers emit a leading '/' (matching the legacy pipeline) so
Shell 2.0 output flows through the existing normalize -> repair -> validate chain
unchanged. The datapack writer strips the slash for .mcfunction lines. NOTHING
else may format a command by hand — always go through cmd_fill / cmd_set.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Axis = Literal["x", "z"]
Face = Literal["N", "S", "E", "W"]

FACES: tuple[Face, ...] = ("N", "S", "E", "W")

# Outward unit normal per face (XZ).
OUTWARD: dict[Face, tuple[int, int]] = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
# Direction a block faces to point INTO the building from a given wall.
INWARD: dict[Face, str] = {"N": "south", "S": "north", "E": "west", "W": "east"}
# The compass word a stair/door uses to face OUTWARD from a wall.
OUTWARD_FACING: dict[Face, str] = {"N": "north", "S": "south", "E": "east", "W": "west"}
OPPOSITE: dict[Face, Face] = {"N": "S", "S": "N", "E": "W", "W": "E"}


@dataclass(frozen=True)
class Vec3:
    x: int
    y: int
    z: int

    def offset(self, dx: int = 0, dy: int = 0, dz: int = 0) -> "Vec3":
        return Vec3(self.x + dx, self.y + dy, self.z + dz)


@dataclass(frozen=True)
class Rect:
    """Axis-aligned, inclusive bounds in the XZ plane."""
    x1: int
    z1: int
    x2: int
    z2: int

    @property
    def width(self) -> int:   # x extent
        return self.x2 - self.x1 + 1

    @property
    def depth(self) -> int:   # z extent
        return self.z2 - self.z1 + 1

    @property
    def area(self) -> int:
        return self.width * self.depth

    def center(self) -> tuple[int, int]:
        return (self.x1 + self.x2) // 2, (self.z1 + self.z2) // 2

    def contains(self, x: int, z: int) -> bool:
        return self.x1 <= x <= self.x2 and self.z1 <= z <= self.z2

    def inset(self, n: int) -> "Rect":
        return Rect(self.x1 + n, self.z1 + n, self.x2 - n, self.z2 - n)

    def intersect(self, o: "Rect") -> "Rect | None":
        x1, z1 = max(self.x1, o.x1), max(self.z1, o.z1)
        x2, z2 = min(self.x2, o.x2), min(self.z2, o.z2)
        if x1 > x2 or z1 > z2:
            return None
        return Rect(x1, z1, x2, z2)

    def edges(self) -> dict[Face, tuple[int, int, int, int]]:
        return {"N": (self.x1, self.z1, self.x2, self.z1),
                "S": (self.x1, self.z2, self.x2, self.z2),
                "W": (self.x1, self.z1, self.x1, self.z2),
                "E": (self.x2, self.z1, self.x2, self.z2)}


@dataclass(frozen=True)
class Opening:
    face: Face
    x: int
    y: int
    z: int
    w: int
    h: int
    kind: Literal["door", "window", "gate"]


@dataclass
class Bay:
    face: Face
    start: Vec3
    length: int
    height: int
    has_window: bool = False
    on_door_segment: bool = False


@dataclass
class Wall:
    face: Face
    base: Vec3
    length: int
    height: int
    pillars: list[int] = field(default_factory=list)
    bays: list[Bay] = field(default_factory=list)
    openings: list[Opening] = field(default_factory=list)
    outward: tuple[int, int] = (0, 0)


@dataclass
class Zone:
    name: str
    rect: Rect
    floor_y: int
    ceil_y: int
    doors: list[Opening] = field(default_factory=list)
    occupancy: set[tuple[int, int]] = field(default_factory=set)

    def interior(self) -> Rect:
        return self.rect.inset(1)

    def is_clear(self, cells: set[tuple[int, int]]) -> bool:
        return not (cells & self.occupancy)

    def claim(self, cells: set[tuple[int, int]]) -> None:
        self.occupancy |= cells

    def along_wall(self, face: Face, length: int, clearance: int = 1
                   ) -> list[Vec3] | None:
        """A run of `length` floor cells one block in from the given wall, or None
        if it doesn't fit / is occupied."""
        r = self.rect.inset(1)
        if face in ("N", "S"):
            z = r.z1 if face == "N" else r.z2
            if r.width < length:
                return None
            x0 = r.x1 + (r.width - length) // 2
            cells = [(x, z) for x in range(x0, x0 + length)]
        else:
            x = r.x1 if face == "W" else r.x2
            if r.depth < length:
                return None
            z0 = r.z1 + (r.depth - length) // 2
            cells = [(x, z) for z in range(z0, z0 + length)]
        if not self.is_clear(set(cells)):
            return None
        return [Vec3(c[0], self.floor_y, c[1]) for c in cells]

    def free_center(self) -> Vec3:
        cx, cz = self.rect.center()
        return Vec3(cx, self.floor_y, cz)


@dataclass
class BuildingGeometry:
    origin: Vec3
    footprint: list[Rect]
    walls: list[Wall] = field(default_factory=list)
    roof_base_y: int = 0
    storeys: list[tuple[int, int]] = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)
    front_face: Face = "N"
    anchors: dict[str, Vec3] = field(default_factory=dict)

    def outline(self) -> Rect:
        x1 = min(r.x1 for r in self.footprint)
        z1 = min(r.z1 for r in self.footprint)
        x2 = max(r.x2 for r in self.footprint)
        z2 = max(r.z2 for r in self.footprint)
        return Rect(x1, z1, x2, z2)


# ── command formatters (the only ones allowed) ───────────────────────────────

def mc(block: str) -> str:
    return block if block.startswith("minecraft:") else f"minecraft:{block}"


def cmd_fill(a: Vec3, b: Vec3, block: str, state: str = "") -> str:
    return f"/fill {a.x} {a.y} {a.z} {b.x} {b.y} {b.z} {mc(block)}{state}"


def cmd_set(p: Vec3, block: str, state: str = "") -> str:
    return f"/setblock {p.x} {p.y} {p.z} {mc(block)}{state}"
