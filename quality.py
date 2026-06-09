"""
quality.py — deterministic build scorer (the measurement half of the harness).

score_build(commands, intent_or_brief, geometry=None) -> BuildScore

Every metric is computed from the voxel grid (plus an optional BuildingGeometry
for the precise metrics). The scorer NEVER raises — a metric that cannot be
computed for the given inputs returns None and is excluded from the weighted
total. This lets the legacy pipeline (intent dict, no geometry) produce a real
baseline while the dsl pipeline (full geometry) gets the precise version.

Sub-scores are 0..100. `total` is the weighted mean over non-None metrics.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from voxel import VoxelGrid, propagate_light, flood_walkable, LIGHT_SOURCES, _base

# Weighting of each metric in the total. Correctness metrics dominate.
WEIGHTS = {
    "watertight": 3.0,
    "door_reachable": 2.0,
    "walkability": 2.0,
    "headroom": 1.5,
    "light_coverage": 1.5,
    "palette_ratio": 1.0,
    "depth_score": 1.0,
    "furniture_density": 1.0,
    "feature_presence": 1.0,
    "roof_complexity": 1.0,
}

# Targets used to mark a metric as "failing" in the report.
TARGETS = {
    "watertight": 100, "door_reachable": 100, "walkability": 100, "headroom": 100,
    "light_coverage": 85, "palette_ratio": 70, "depth_score": 60,
    "furniture_density": 50, "feature_presence": 100, "roof_complexity": 60,
}


@dataclass
class BuildScore:
    metrics: dict[str, float | None] = field(default_factory=dict)
    total: float = 0.0
    failing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"total": round(self.total, 1),
                "metrics": {k: (round(v, 1) if v is not None else None)
                            for k, v in self.metrics.items()},
                "failing": self.failing}


# ── envelope detection (grid-only fallback when geometry is absent) ──────────

@dataclass
class _Env:
    x1: int; z1: int; x2: int; z2: int
    floor_y: int; wall_top: int


def _envelope_from_grid(grid: VoxelGrid) -> _Env | None:
    """Recover footprint + floor + wall-top from a finished build's grid.

    Robust to the legacy foundation skirt (a course wider than the building and
    one below the floor): the footprint is taken from *wall columns* (tall solid
    stacks), not the widest solid layer, and the floor level is the lowest course
    whose interior is solid with air directly above it (the surface you stand on)."""
    if not grid.cells:
        return None
    mn, mx = grid.bounds()

    # footprint = bbox of (x,z) columns that are tall enough to be walls (≥3),
    # which excludes a 1-course foundation skirt and thin roof overhang.
    col_height: dict[tuple[int, int], int] = {}
    for (x, y, z), b in grid.cells.items():
        if _base(b) != "air":
            col_height[(x, z)] = col_height.get((x, z), 0) + 1
    walls = [xz for xz, h in col_height.items() if h >= 3]
    if not walls:
        walls = list(col_height)
    x1 = min(c[0] for c in walls); x2 = max(c[0] for c in walls)
    z1 = min(c[1] for c in walls); z2 = max(c[1] for c in walls)

    interior = [(x, z) for x in range(x1 + 1, x2) for z in range(z1 + 1, z2)]
    if not interior:
        interior = [(x, z) for x in range(x1, x2 + 1) for z in range(z1, z2 + 1)]

    # floor = lowest course where the interior is mostly solid and the course
    # above it is mostly air (i.e. a standable surface, not the foundation).
    floor_y = mn.y
    for y in range(mn.y, mx.y):
        solid = sum(1 for (x, z) in interior if grid.is_solid(x, y, z))
        air_above = sum(1 for (x, z) in interior if not grid.is_solid(x, y + 1, z))
        if solid >= 0.6 * len(interior) and air_above >= 0.5 * len(interior):
            floor_y = y
            break

    # walls exist while the perimeter of the footprint stays mostly solid.
    peri = _perimeter_cells(x1, z1, x2, z2)
    wall_top = floor_y
    for y in range(floor_y + 1, mx.y + 1):
        solid = sum(1 for (x, z) in peri if grid.is_solid(x, y, z))
        if peri and solid / len(peri) >= 0.5:
            wall_top = y
        else:
            break
    return _Env(x1, z1, x2, z2, floor_y, wall_top)


def _env_from_geometry(geometry) -> _Env | None:
    """Precise envelope straight from BuildingGeometry (no grid guessing)."""
    fp = getattr(geometry, "footprint", None)
    if not fp:
        return None
    out = geometry.outline()
    floor_y = geometry.origin.y
    wall_top = max(floor_y + 1, geometry.roof_base_y - 1)
    return _Env(out.x1, out.z1, out.x2, out.z2, floor_y, wall_top)


def _perimeter_cells(x1, z1, x2, z2) -> list[tuple[int, int]]:
    cells = []
    for x in range(x1, x2 + 1):
        cells.append((x, z1)); cells.append((x, z2))
    for z in range(z1 + 1, z2):
        cells.append((x1, z)); cells.append((x2, z))
    return cells


# ── metric implementations ───────────────────────────────────────────────────

def _watertight(grid: VoxelGrid, env: _Env) -> float:
    """Floor plane + roof coverage + wall coverage, averaged. Door/window
    openings cost a little; a missing face costs a lot."""
    # floor coverage
    floor = [(x, z) for x in range(env.x1, env.x2 + 1) for z in range(env.z1, env.z2 + 1)]
    floor_solid = sum(1 for (x, z) in floor if grid.is_solid(x, env.floor_y, z))
    floor_cov = floor_solid / len(floor) if floor else 0
    # roof: at least one solid cell above each footprint column past wall_top
    roofed = 0
    for (x, z) in floor:
        if any(grid.is_solid(x, y, z) for y in range(env.wall_top, env.wall_top + 8)):
            roofed += 1
    roof_cov = roofed / len(floor) if floor else 0
    # walls: perimeter coverage across the wall band
    peri = _perimeter_cells(env.x1, env.z1, env.x2, env.z2)
    band = range(env.floor_y + 1, env.wall_top + 1)
    total = sum(1 for _ in band) * len(peri)
    wsolid = sum(1 for y in band for (x, z) in peri if grid.is_solid(x, y, z))
    wall_cov = wsolid / total if total else 0
    return 100.0 * (0.4 * floor_cov + 0.3 * roof_cov + 0.3 * wall_cov)


def _interior_floor(grid: VoxelGrid, env: _Env) -> list[tuple[int, int, int]]:
    """Standable layer just above the floor, strictly inside the walls."""
    y = env.floor_y + 1
    return [(x, y, z)
            for x in range(env.x1 + 1, env.x2)
            for z in range(env.z1 + 1, env.z2)
            if not grid.is_solid(x, y, z)]


def _find_door(grid: VoxelGrid, env: _Env) -> tuple[int, int, int] | None:
    """A perimeter opening at standable height -> the outside cell in front."""
    y = env.floor_y + 1
    for (x, z) in _perimeter_cells(env.x1, env.z1, env.x2, env.z2):
        if not grid.is_solid(x, y, z) and not grid.is_solid(x, y + 1, z):
            # outward normal
            for dx, dz in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                ox, oz = x + dx, z + dz
                if not (env.x1 <= ox <= env.x2 and env.z1 <= oz <= env.z2):
                    if not grid.is_solid(ox, y, z):
                        return (ox, y, oz)
    return None


def _door_reachable(grid: VoxelGrid, env: _Env) -> float:
    return 100.0 if _find_door(grid, env) is not None else 0.0


def _walkability(grid: VoxelGrid, env: _Env) -> float:
    floor = _interior_floor(grid, env)
    if not floor:
        return 0.0
    door = _find_door(grid, env)
    # start from the interior cell adjacent to the door, else interior center
    start = None
    if door:
        for dx, dz in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            c = (door[0] + dx, door[1], door[2] + dz)
            if c in set(floor):
                start = c
                break
    if start is None:
        start = floor[len(floor) // 2]
    region = set(floor)
    reached = flood_walkable(grid, start, region)
    return 100.0 * len(reached & region) / len(region)


def _headroom(grid: VoxelGrid, env: _Env) -> float:
    floor = _interior_floor(grid, env)
    if not floor:
        return 0.0
    ok = sum(1 for (x, y, z) in floor if not grid.is_solid(x, y + 1, z))
    return 100.0 * ok / len(floor)


def _light_coverage(grid: VoxelGrid, env: _Env) -> float:
    floor = _interior_floor(grid, env)
    if not floor:
        return 0.0
    light = propagate_light(grid)
    lit = sum(1 for c in floor if light.get(c, 0) >= 8)
    return 100.0 * lit / len(floor)


def _depth_score(grid: VoxelGrid, env: _Env) -> float:
    """Fraction of facade columns that protrude or recess from the mean wall
    plane (pillars/recesses/overhang). Rewards non-flat walls."""
    peri = _perimeter_cells(env.x1, env.z1, env.x2, env.z2)
    if not peri:
        return 0.0
    # count solid cells that sit just outside the footprint bbox (protrusions)
    band = range(env.floor_y + 1, env.wall_top + 1)
    protrude = 0
    for y in band:
        for (x, z) in peri:
            for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ox, oz = x + dx, z + dz
                if not (env.x1 <= ox <= env.x2 and env.z1 <= oz <= env.z2):
                    if grid.is_solid(ox, y, oz):
                        protrude += 1
                        break
    facade = sum(1 for _ in band) * len(peri)
    return min(100.0, 100.0 * protrude / facade * 4) if facade else 0.0


def _roof_complexity(grid: VoxelGrid, env: _Env) -> float:
    """Distinct Y layers with solid cells in the roof region + overhang."""
    layers = set()
    overhang = False
    for (c, b) in grid.cells.items():
        if _base(b) == "air":
            continue
        x, y, z = c
        if y > env.wall_top:
            layers.add(y)
            if not (env.x1 <= x <= env.x2 and env.z1 <= z <= env.z2):
                overhang = True
    n = len(layers)
    score = min(100.0, n * 35.0)
    if overhang:
        score = min(100.0, score + 30.0)
    return score


def _palette_ratio(grid: VoxelGrid, env: _Env, palette) -> float | None:
    if palette is None:
        return None
    roles = {"dominant": getattr(palette, "dominant", None),
             "trim": getattr(palette, "trim", None),
             "accent": getattr(palette, "accent", None)}
    counts = {"dominant": 0, "trim": 0, "accent": 0, "other": 0}
    wear = set(_base(w) for w in getattr(palette, "wear", ()) or ())
    total = 0
    for b in grid.cells.values():
        base = _base(b)
        if base == "air":
            continue
        total += 1
        matched = "other"
        for role, blk in roles.items():
            if blk and base == _base(blk):
                matched = role
                break
        if matched == "other" and base in wear:
            matched = "dominant"
        counts[matched] += 1
    if total == 0:
        return 0.0
    dom = counts["dominant"] / total
    trim = counts["trim"] / total
    acc = counts["accent"] / total
    # distance from the 65/25/10 ideal
    dist = abs(dom - 0.65) + abs(trim - 0.25) + abs(acc - 0.10)
    return max(0.0, 100.0 * (1 - dist))


# feature detectors: feature keyword -> (bare blocks that prove it)
_FEATURE_BLOCKS = {
    "fireplace": {"campfire", "soul_campfire"},
    "chimney": {"campfire"},
    "garden": {"oak_leaves", "grass_block", "bush", "wildflowers", "leaf_litter"},
    "balcony": {"oak_fence", "spruce_fence"},
    "tower": set(),
    "pool": {"water"},
    "fountain": {"water"},
    "library": {"bookshelf", "chiseled_bookshelf"},
    "bookshelf": {"bookshelf", "chiseled_bookshelf"},
}


def _feature_presence(grid: VoxelGrid, features: list[str]) -> float | None:
    if not features:
        return None
    present = {_base(b) for b in grid.cells.values()}
    hits = 0
    checkable = 0
    for f in features:
        key = str(f).lower().strip()
        blocks = None
        for k, v in _FEATURE_BLOCKS.items():
            if k in key:
                blocks = v
                break
        if blocks is None:
            continue
        checkable += 1
        if not blocks or present & blocks:
            hits += 1
    if checkable == 0:
        return None
    return 100.0 * hits / checkable


def _furniture_density(grid: VoxelGrid, env: _Env) -> float | None:
    """Occupied interior floor cells / interior area, scored against 0.10–0.25."""
    floor_area = max(1, (env.x2 - env.x1 - 1) * (env.z2 - env.z1 - 1))
    y = env.floor_y + 1
    occupied = sum(1 for x in range(env.x1 + 1, env.x2) for z in range(env.z1 + 1, env.z2)
                   if grid.is_solid(x, y, z))
    density = occupied / floor_area
    if density <= 0:
        return 0.0
    if 0.10 <= density <= 0.25:
        return 100.0
    if density < 0.10:
        return 100.0 * density / 0.10
    return max(0.0, 100.0 * (1 - (density - 0.25) / 0.5))


# ── orchestration ─────────────────────────────────────────────────────────────

def score_build(commands: list[str], intent_or_brief, geometry=None) -> BuildScore:
    grid = VoxelGrid.from_commands(commands)
    env = _env_from_geometry(geometry) if geometry is not None else None
    if env is None:
        env = _envelope_from_grid(grid)

    intent = intent_or_brief if isinstance(intent_or_brief, dict) else {}
    features = list(intent.get("features", []) or [])
    palette = getattr(intent_or_brief, "palette", None)

    metrics: dict[str, float | None] = {}
    if env is None:
        # empty build
        score = BuildScore(metrics={k: 0.0 for k in WEIGHTS}, total=0.0,
                           failing=list(WEIGHTS))
        return score

    metrics["watertight"] = _watertight(grid, env)
    metrics["door_reachable"] = _door_reachable(grid, env)
    metrics["walkability"] = _walkability(grid, env)
    metrics["headroom"] = _headroom(grid, env)
    metrics["light_coverage"] = _light_coverage(grid, env)
    metrics["depth_score"] = _depth_score(grid, env)
    metrics["roof_complexity"] = _roof_complexity(grid, env)
    metrics["palette_ratio"] = _palette_ratio(grid, env, palette)
    metrics["feature_presence"] = _feature_presence(grid, features)
    metrics["furniture_density"] = _furniture_density(grid, env)

    num = 0.0
    den = 0.0
    failing: list[str] = []
    for name, val in metrics.items():
        if val is None:
            continue
        w = WEIGHTS.get(name, 1.0)
        num += w * val
        den += w
        if val < TARGETS.get(name, 0):
            failing.append(name)
    total = num / den if den else 0.0
    return BuildScore(metrics=metrics, total=total, failing=failing)
