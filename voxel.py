"""
voxel.py — the shared command→grid simulator.

Extracted from test_shell.py so the test suite, the quality scorer, and the
deterministic critic all reason about builds through one source of truth. Pure
stdlib; pure-python dict grid (plenty fast at building/city sizes).

A "cell" is a (x, y, z) int tuple. block_at returns "minecraft:air" for empty.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Vec3:
    x: int
    y: int
    z: int


AIR = "minecraft:air"

# Light emission by bare block name (no namespace, no state). Extend as the
# block registry grows. Value = light level the source emits.
LIGHT_SOURCES: dict[str, int] = {
    "lantern": 15, "soul_lantern": 10, "sea_lantern": 15, "glowstone": 15,
    "shroomlight": 15, "torch": 14, "soul_torch": 10, "copper_bulb": 15,
    "copper_torch": 14, "copper_lantern": 15, "campfire": 15, "soul_campfire": 10,
    "end_rod": 14, "redstone_lamp": 15, "jack_o_lantern": 15,
    "ochre_froglight": 15, "verdant_froglight": 15, "pearlescent_froglight": 15,
    "candle": 3, "beacon": 15, "conduit": 15, "lava": 15, "fire": 15,
    "magma_block": 3, "crying_obsidian": 10, "amethyst_cluster": 5,
}


def _base(block: str) -> str:
    """Strip namespace and [state] -> bare name, e.g. 'minecraft:oak_stairs[..]' -> 'oak_stairs'."""
    b = block.split("[")[0]
    if b.startswith("minecraft:"):
        b = b[len("minecraft:"):]
    return b


class VoxelGrid:
    """Last-write-wins voxel grid built by replaying /fill and /setblock."""

    def __init__(self) -> None:
        self.cells: dict[tuple[int, int, int], str] = {}

    # ── construction ────────────────────────────────────────────────────────
    def apply(self, commands: list[str]) -> "VoxelGrid":
        for cmd in commands:
            p = cmd.strip().split()
            if not p:
                continue
            if p[0] == "/fill" and len(p) >= 8:
                try:
                    x1, y1, z1, x2, y2, z2 = (int(v) for v in p[1:7])
                except ValueError:
                    continue
                block = p[7]
                for xx in range(min(x1, x2), max(x1, x2) + 1):
                    for yy in range(min(y1, y2), max(y1, y2) + 1):
                        for zz in range(min(z1, z2), max(z1, z2) + 1):
                            self.cells[(xx, yy, zz)] = block
            elif p[0] == "/setblock" and len(p) >= 5:
                try:
                    x, y, z = (int(v) for v in p[1:4])
                except ValueError:
                    continue
                self.cells[(x, y, z)] = p[4]
        return self

    @classmethod
    def from_commands(cls, commands: list[str]) -> "VoxelGrid":
        return cls().apply(commands)

    # ── queries ─────────────────────────────────────────────────────────────
    def block_at(self, x: int, y: int, z: int) -> str:
        """Full block id (with state) or 'minecraft:air'."""
        return self.cells.get((x, y, z), AIR)

    def base_at(self, x: int, y: int, z: int) -> str:
        """Bare block name (no namespace/state) or 'air'."""
        return _base(self.cells.get((x, y, z), AIR))

    def is_solid(self, x: int, y: int, z: int) -> bool:
        b = self.base_at(x, y, z)
        return b != "air"

    def bounds(self) -> tuple[Vec3, Vec3]:
        if not self.cells:
            return Vec3(0, 0, 0), Vec3(0, 0, 0)
        xs = [c[0] for c in self.cells]
        ys = [c[1] for c in self.cells]
        zs = [c[2] for c in self.cells]
        return Vec3(min(xs), min(ys), min(zs)), Vec3(max(xs), max(ys), max(zs))


# ── analysis helpers ────────────────────────────────────────────────────────

_NEIGHBORS_6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]


def propagate_light(grid: VoxelGrid) -> dict[tuple[int, int, int], int]:
    """BFS light propagation: −1 per step through air; solids block (and don't
    receive). Returns {cell: light_level} for every reachable air cell. The
    source cell itself carries its emission level."""
    from collections import deque

    light: dict[tuple[int, int, int], int] = {}
    q: deque[tuple[int, int, int]] = deque()

    for cell, block in grid.cells.items():
        lvl = LIGHT_SOURCES.get(_base(block), 0)
        if lvl > 0:
            if light.get(cell, -1) < lvl:
                light[cell] = lvl
                q.append(cell)

    while q:
        cx, cy, cz = q.popleft()
        cur = light[(cx, cy, cz)]
        if cur <= 1:
            continue
        for dx, dy, dz in _NEIGHBORS_6:
            nx, ny, nz = cx + dx, cy + dy, cz + dz
            ncell = (nx, ny, nz)
            # Light cannot pass into a solid (non-source) block.
            if grid.is_solid(nx, ny, nz) and LIGHT_SOURCES.get(grid.base_at(nx, ny, nz), 0) == 0:
                continue
            nlvl = cur - 1
            if light.get(ncell, -1) < nlvl:
                light[ncell] = nlvl
                q.append(ncell)
    return light


def flood_walkable(grid: VoxelGrid, start: tuple[int, int, int],
                   region: set[tuple[int, int, int]] | None = None) -> set[tuple[int, int, int]]:
    """4-neighbour flood over floor cells reachable from `start`, requiring
    2-high clearance (cell and the cell above are non-solid). `start` is a floor
    cell (the air just above a floor block). If `region` is given, the flood is
    clamped to it."""
    from collections import deque

    def standable(c: tuple[int, int, int]) -> bool:
        x, y, z = c
        if region is not None and c not in region:
            return False
        return (not grid.is_solid(x, y, z)) and (not grid.is_solid(x, y + 1, z))

    if not standable(start):
        return set()

    seen = {start}
    q = deque([start])
    while q:
        x, y, z = q.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y, z + dz)
            if n not in seen and standable(n):
                seen.add(n)
                q.append(n)
    return seen
