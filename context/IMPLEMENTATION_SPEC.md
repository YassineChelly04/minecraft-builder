# IMPLEMENTATION SPEC — Minecraft Builder v2
## Executor handoff document for Claude (Opus 4.8) — transform UPGRADE_PLAN_V2.md into working code

> **READ FIRST.** You are upgrading an EXISTING, WORKING codebase. The prime directive:
> **never break the current single-building pipeline while building the new one.**
> All new behavior ships behind flags. Every phase ends with passing tests and a benchmark run.

---

# PART 0 — CONTEXT YOU MUST INTERNALIZE

## 0.1 What this project is
Flask web app → multi-agent LLM pipeline (Groq API, Llama models) → valid Minecraft Java `/fill` & `/setblock` commands → executed in-game. Current guarantee architecture:
- `shell.py` — deterministic watertight envelope (floor/walls/roof/door/windows). No LLM.
- `exterior_agent.py` / `interior_agent.py` — 70b LLMs emit raw commands (parallel threads). Air stripped via `_strip_air()`.
- `normalizer.py` → `repair.py` → `validator.py` — deterministic cleaning: block-name fuzzy match, state stripping, /fill volume splitting (limit 32,768), world Y −64..319.
- `critic_agent.py` — 8b review + patch commands (best-effort).
- `orchestrator.py` (intent, 8b) and `clarify_agent.py` (brainstorm/questions, 8b).
- `blocks.py` — ~600 valid 1.21.x block IDs (Python set).
- `input_agent.py` — pyautogui keyboard automation (T → paste → Enter, 0.15 s delay).
- `config.py` — models/temps/max_tokens per role + engine limits. `.env` overrides per role (`LLM_MODEL_*`).
- HTTP: `POST /clarify`, `POST /generate`, `POST /execute`. UI: `templates/index.html`.
- Tests: `test_shell.py` (voxel-grid simulation asserting watertightness), `test_repair.py`.

## 0.2 The strategic inversion you are implementing
**Current:** deterministic layer = validity; LLM layer = creativity (raw commands).
**Target:** deterministic layer = validity AND craftsmanship (architecture, coordinates, blockstates); LLM layer = ONLY small taste decisions (menu picks, JSON ≤ ~150 output tokens per call).
**Hard rule for all new code: an LLM never writes a coordinate, never writes a block ID.** LLM output is a tiny JSON of op/archetype/palette NAMES. Python placers expand names into commands.

End goal: one prompt → brainstorm with user → a full coordinated industrial CITY (districts, roads, rail, canals, ~50–300 buildings) generated for ~23k total LLM tokens, executed via datapack functions.

## 0.3 Non-negotiable invariants (carry forward + new)
1. Shell/deterministic layers MAY place `minecraft:air` (door cuts, crenellation gaps, room door openings). LLM-derived streams may NOT — `_strip_air()` stays on every LLM stream.
2. Every command path still flows through `normalize → repair → validate` (it becomes a near-idle safety net; keep it).
3. `/fill` volume ≤ 32,768; Y ∈ [−64, 319]; `minecraft:` namespace on all final block IDs.
4. `repair.py`, `validator.py` are NOT to be weakened or bypassed. Extend only.
5. All randomness seeded: `seed = sha256(prompt + str(origin)) → random.Random(seed)`. Same prompt+origin ⇒ identical build. Thread the `rng` object explicitly; never use the global `random`.
6. Legacy mode must keep working: `PIPELINE_MODE=legacy|dsl` (env + per-request override `{"mode": "legacy"}`). Default stays `legacy` until Gate G3 (see Part 9) flips it.
7. Python 3.10+; type hints everywhere; dataclasses for all geometry/contract objects; no new heavy dependencies (stdlib + existing requirements only; `numpy` allowed if already used by tests, otherwise pure-python voxel dict grids are fine at these sizes).

## 0.4 Working style required of you (the executor)
- Work phase by phase in the order of Part 9. Do NOT start a phase before the previous phase's Definition of Done (DoD) is green.
- After each phase: run `python -m pytest` (migrate existing test scripts into pytest as part of Phase A) and `python run_benchmark.py --quick`, and print the score/token table in your summary.
- When the spec under-determines something, choose the simplest deterministic option, document the decision in `DECISIONS.md`, and continue. Do not block on questions unless an invariant would be violated.
- Commit (or checkpoint) at every DoD with message `phase-<id>: <summary>`.

---

# PART 1 — TARGET REPO LAYOUT (create incrementally; final state)

```
minecraft builder/
├── app.py                      # + /generate_city, /export_datapack, mode param
├── pipeline.py                 # single-building orchestration (legacy + dsl paths)
├── city_pipeline.py            # NEW — city orchestration loop
├── config.py                   # + TARGET_MC_VERSION, PIPELINE_MODE, budgets
├── llm_client.py               # + usage logging, json_schema support, model registry
├── agents/
│   ├── clarify_agent.py        # moved; city-aware brainstorm added
│   ├── intent_agent.py         # renamed from orchestrator.py (keep shim import)
│   ├── exterior_agent.py       # DSL menu-pick version (legacy path preserved)
│   ├── interior_agent.py       # DSL per-room version (legacy path preserved)
│   ├── critic_agent.py         # optional style-note only (det. critic replaces core)
│   ├── city_director.py        # NEW
│   └── district_stylist.py     # NEW
├── architecture/
│   ├── geometry.py             # Rect, Zone, Wall, Bay, Opening, Anchor, Footprint
│   ├── massing.py              # footprint generators: rect/L/T/courtyard/tower+wing
│   ├── walls.py                # Shell 2.0 wall system (plinth/pillars/bays/cornice)
│   ├── roofs.py                # gable/flat+parapet/crenellated/pagoda/dome/spire/sawtooth
│   ├── floors.py               # floor slabs, border trim, multi-storey, staircases
│   ├── floorplan.py            # BSP partition, door graph, hallway insertion
│   ├── shell2.py               # build_shell2(brief) → (commands, BuildingGeometry)
│   ├── sitework.py             # entry path, lamps, garden strips, foundation skirt
│   ├── texture.py              # textured_fill, oxidation gradients, wear sprinkles
│   └── archetypes/             # CITY: factory_hall.py, smokestack_plant.py, warehouse.py,
│       │                       #  rowhouse_strip.py, office_block.py, water_tower.py,
│       │                       #  gasometer.py, gantry_crane.py, train_depot.py,
│       │                       #  dock_finger.py, civic_hall.py, power_station.py
│       └── base.py             # Archetype ABC: massing(brief)->Footprint, detail(geom)->cmds
├── placers/
│   ├── base.py                 # occupancy grid, op registry, fuzzy op matcher
│   ├── exterior_ops.py         # window_box, shutters, awning, lantern_pair, chimney, ...
│   ├── furniture.py            # sofa, bed, dining_set, kitchen_run, fireplace, desk, ...
│   ├── lighting.py             # auto_light(zone) — BFS light solver
│   └── props.py                # CITY: street lamps, power poles, pipe runs, crates, ...
├── knowledge/
│   ├── blocks_registry.py      # BLOCKS_BY_VERSION + resolve(target_version) -> set
│   ├── palettes.py             # PALETTES + BuildingPalette dataclass + validation
│   ├── style_cards.py          # STYLE_CARDS dict (≤120 tokens each)
│   └── room_kits.py            # per-room default furniture kits & must-include rules
├── city/
│   ├── model.py                # CityBrief, District, Lot, RoadGraph, CityPlan dataclasses
│   ├── planner.py              # zoning, road network, parceling, reservations
│   ├── briefs.py               # CityPlan -> List[BuildingBrief] (seeded)
│   ├── connectivity.py         # lamps, poles, pipes, rail spurs, bridges, clutter
│   └── qa.py                   # door↔road A*, skyline check, city palette ratio
├── execution/
│   ├── datapack.py             # NEW — .mcfunction writer, master/undo, forceload
│   ├── rcon_client.py          # NEW — optional, stdlib socket impl of RCON
│   └── input_agent.py          # moved; kept as fallback Mode D
├── quality.py                  # NEW — voxel sim scorer (Part 3)
├── voxel.py                    # NEW — shared command→grid simulator (extracted from test_shell)
├── benchmarks/
│   ├── prompts_buildings.json  # 15 fixed building prompts
│   ├── prompts_cities.json     # 5 fixed city prompts
│   └── runs.jsonl              # appended results (scores + tokens)
├── run_benchmark.py            # NEW
├── tests/                      # pytest; absorb test_shell.py & test_repair.py
├── blocks.py                   # KEEP as shim: from knowledge.blocks_registry import ...
├── normalizer.py / repair.py / validator.py   # unchanged behavior, extended tests
├── DECISIONS.md                # your running decision log
└── (everything else unchanged)
```

Backwards-compat shims: keep `orchestrator.py`, `blocks.py`, `input_agent.py` import paths working via re-export modules so nothing external breaks.

---

# PART 2 — CORE DATA CONTRACTS (define these EXACTLY; everything depends on them)

All in `architecture/geometry.py` and `city/model.py`. Frozen dataclasses unless noted.

```python
# ---- geometry.py ----
Axis = Literal["x", "z"]
Face = Literal["N", "S", "E", "W"]          # N = −z, S = +z, E = +x, W = −x  (document this!)

@dataclass(frozen=True)
class Vec3:  x: int; y: int; z: int

@dataclass(frozen=True)
class Rect:                                  # axis-aligned, inclusive bounds, XZ plane
    x1: int; z1: int; x2: int; z2: int
    # methods: width, depth, area, center, contains, intersect, inset(n), edges()

@dataclass(frozen=True)
class Opening:                               # door/window hole in a wall
    face: Face; x: int; y: int; z: int; w: int; h: int; kind: Literal["door","window","gate"]

@dataclass
class Bay:                                   # wall segment between two pillars
    face: Face; start: Vec3; length: int; height: int
    has_window: bool = False; on_door_segment: bool = False

@dataclass
class Wall:
    face: Face; base: Vec3; length: int; height: int
    pillars: list[int]                       # offsets along the wall where pillars sit
    bays: list[Bay]
    openings: list[Opening]
    outward: Vec3                            # unit normal pointing outside

@dataclass
class Zone:                                  # a room or any furnishable region
    name: str                                # "living", "bedroom_1", ...
    rect: Rect; floor_y: int; ceil_y: int
    doors: list[Opening]                     # openings INTO this zone
    occupancy: set[tuple[int,int]] = field(default_factory=set)   # XZ cells used
    # methods: along_wall(face, length, clearance) -> list[Vec3] | None  (None if no fit)
    #          free_center(w,d), corner(face_pair), is_clear(cells), claim(cells)

@dataclass
class BuildingGeometry:                      # produced by shell2; consumed by placers/agents
    origin: Vec3
    footprint: list[Rect]
    walls: list[Wall]
    roof_base_y: int
    storeys: list[tuple[int,int]]            # (floor_y, ceil_y) per storey
    zones: list[Zone]                        # filled by floorplan
    front_face: Face
    anchors: dict[str, Vec3]                 # door_outside, door_inside, ...
```

```python
# ---- knowledge/palettes.py ----
@dataclass(frozen=True)
class BuildingPalette:
    name: str
    dominant: str; trim: str; accent: str
    roof: str                                # stair block for slopes
    roof_solid: str                          # full block for ridges/flat
    glass: str; light: str
    wear: tuple[str, ...] = ()               # variant sprinkle blocks
    wear_density: float = 0.10
    floor: str = ""                          # defaults to dominant-compatible plank/stone
# ALL block ids validated against blocks_registry.resolve(TARGET_MC_VERSION) at import.
# A failing palette raises at startup — never at build time.
```

```python
# ---- BuildingBrief: the universal input to single-building generation ----
@dataclass
class BuildingBrief:
    archetype: str                           # "house" | "factory_hall" | "warehouse" | ...
    lot: Rect                                # building must fit lot minus setback
    origin_y: int
    style: str; palette: BuildingPalette
    storeys: int; height_band: tuple[int,int]
    room_program: list[str]                  # [] for non-furnished archetypes
    features: list[str]
    front_face: Face                         # faces the road
    seed: int
    detail_level: Literal["kit","llm"]       # kit = deterministic only; llm = DSL agents run
    material_overrides: dict[str,str] = field(default_factory=dict)
```

```python
# ---- city/model.py ----
@dataclass
class CityBrief:        # OUTPUT OF CITY DIRECTOR (LLM) — full JSON schema in Part 7
    theme: str; era: str; palette_family: str
    districts: list[dict]        # [{"type": "...", "share": 0.3}, ...]
    landmarks: list[str]; skyline: str; mood: str
    size_class: Literal["S","M","L"]; waterfront: bool

@dataclass
class District:
    kind: str; region: list[Rect]; accent: str = ""; street_set: str = ""
    motif: str = ""; lots: list["Lot"] = field(default_factory=list)

@dataclass
class Lot:
    rect: Rect; district_kind: str; faces_road: Face; reserved: str = ""   # "" | "rail_spur" | "plaza" | ...

@dataclass
class RoadGraph:
    arterial: list[Rect]; secondary: list[Rect]; alley: list[Rect]
    bridges: list[Rect]; nodes: list[Vec3]
    # method: nearest_road_cell(p: Vec3) -> Vec3

@dataclass
class CityPlan:
    bounds: Rect; ground_y: int
    districts: list[District]; roads: RoadGraph
    rail: list[Rect]; canal: list[Rect]; plaza: Rect | None
    briefs: list[BuildingBrief]
```

**Command stream convention:** every generator returns `list[str]` of commands WITHOUT leading slash internally; the slash is added at the serialization boundary (pipeline output / datapack writer strips it again for .mcfunction). Add `cmd_fill(a: Vec3, b: Vec3, block: str, state: str = "") -> str` and `cmd_set(p: Vec3, block, state="")` helpers in `architecture/geometry.py`; NOTHING else may format commands by hand.

---

# PART 3 — PHASE A: MEASUREMENT HARNESS (build FIRST)

## 3.1 `voxel.py` — shared simulator
Extract the grid simulation from `test_shell.py` into a reusable module:

```python
class VoxelGrid:
    def __init__(self): self.cells: dict[tuple[int,int,int], str] = {}
    def apply(self, commands: list[str]) -> None      # parses /fill & /setblock incl. states
    def block_at(self, x,y,z) -> str                  # "minecraft:air" default
    def bounds(self) -> tuple[Vec3, Vec3]
LIGHT_SOURCES = {"lantern":15,"soul_lantern":10,"sea_lantern":15,"glowstone":15,
                 "shroomlight":15,"torch":14,"soul_torch":10,"copper_bulb":15,
                 "copper_torch":14,"copper_lantern":15,"campfire":15,"end_rod":14,
                 "froglight":15,"candle":3}           # extend from blocks registry
def propagate_light(grid) -> dict[cell,int]          # BFS, −1 per step, blocked by solids
def flood_walkable(grid, start, zones) -> set[cell]  # 2-high clearance walk check
```

## 3.2 `quality.py` — the scorer
Implement `score_build(commands, intent_or_brief, geometry|None) -> BuildScore` with sub-scores 0–100 and a weighted `total`:

| metric | computation | target |
|---|---|---|
| watertight | reuse shell test logic on envelope faces | 100 required |
| door_reachable | door opening exists, 2-high, outside cell walkable | 100 required |
| palette_ratio | % of non-air cells per palette role; score by distance from 65/25/10 (dominant counts wear variants) | ≥ 70 |
| depth_score | count exterior cells protruding/inset ±1 from wall plane (pillars, recesses, overhang) ÷ facade area | ≥ 60 |
| light_coverage | % interior floor cells with light ≥ 8 | ≥ 85 |
| walkability | % interior floor reachable from door via flood_walkable | 100 |
| furniture_density | occupied floor cells / room area per zone, scored against band 0.10–0.25 | in band |
| feature_presence | each requested feature mapped to detector (fireplace→campfire+surround present, etc.) | 100 |
| roof_complexity | distinct Y layers in roof region + overhang detection | ≥ 2 layers + overhang |
| headroom | min clearance above every walkable cell ≥ 2 | 100 |

City-level additions (Phase F): `score_city(plan, commands)` → door_to_road (A* on road cells from every brief's door anchor, must be 100), road_connectivity (single component), road_lighting (light ≥ 8 along all road cells), skyline_match (height histogram vs rule), district_palette_coherence.

## 3.3 Token accounting in `llm_client.py`
Wrap every Groq call; accumulate `{"role": ..., "model": ..., "prompt_tokens": ..., "completion_tokens": ...}` into a per-request `UsageLog` returned alongside pipeline output and appended to `benchmarks/runs.jsonl`. Add `usage` to `/generate` and `/generate_city` responses.

## 3.4 `run_benchmark.py`
- `--suite buildings|cities|all`, `--quick` (3 prompts), `--agent/--model/--prompt-variant` overrides for A/B.
- Loads fixed prompts; runs pipeline with `refine` off; prints table: prompt | total score | failing metrics | tokens | Δ vs last run (read previous from runs.jsonl).
- `--no-llm` flag: runs with a `StubLLM` (canned JSON responses checked into `tests/fixtures/`) so the deterministic 90% of the system is testable offline and in CI. **Build StubLLM now; every later phase's tests use it.**

## 3.5 Create `benchmarks/prompts_buildings.json`
15 prompts covering: tiny 5×5 cottage, medieval house, 2-storey manor, modern villa, japanese temple, wizard tower, warehouse, factory, rowhouse, desert palace, ruins, church (dome), viking longhouse, office block, "surprise me" free prompt. Each entry: `{"id","prompt","answers",{"origin"}}`.

**DoD-A:** pytest green; `run_benchmark.py --suite buildings --no-llm` produces a score table for the legacy pipeline (scores will be low — that's the baseline); token logging visible on a real `/generate` call.

---

# PART 4 — PHASE B: KNOWLEDGE LAYER (registry, palettes, style cards)

## 4.1 `knowledge/blocks_registry.py`
```python
BLOCKS_BY_VERSION: dict[str, set[str]] = {
  "1.21":   { ...current blocks.py contents, audited... },
  "1.21.4": {"pale_oak_planks","pale_oak_log","pale_oak_stairs","pale_oak_slab",
             "pale_oak_fence","pale_oak_door","pale_oak_trapdoor","resin_block",
             "resin_bricks","resin_brick_stairs","resin_brick_slab","resin_brick_wall",
             "chiseled_resin_bricks","resin_clump"},
  "1.21.5": {"bush","firefly_bush","leaf_litter","wildflowers","cactus_flower",
             "short_dry_grass","tall_dry_grass"},
  "1.21.9": {"copper_bars","copper_chain","copper_lantern","copper_torch","copper_chest",
             "copper_golem_statue","shelf",   # plus oxidation/waxed variants:
             *oxidation_variants("copper_bars","copper_chain","copper_lantern","copper_chest")},
  "26.2":   {"cinnabar","cinnabar_stairs","cinnabar_slab","cinnabar_wall",
             "polished_cinnabar","polished_cinnabar_stairs","polished_cinnabar_slab",
             "polished_cinnabar_wall","cinnabar_bricks","cinnabar_brick_stairs",
             "cinnabar_brick_slab","cinnabar_brick_wall","chiseled_cinnabar"},
             # NOTE: 26.2 releases 2026-06-16. Mark set PROVISIONAL; add
             # `verify_against_release_notes` TODO + keep behind version gate.
}
VERSION_ORDER = ["1.21","1.21.4","1.21.5","1.21.9","26.1","26.2","26.3"]
def resolve(target: str) -> frozenset[str]   # union of all sets ≤ target; cached
```
`config.py`: `TARGET_MC_VERSION = os.getenv("TARGET_MC_VERSION", "1.21.9")`. `repair.py` and `validator.py` switch from `blocks.VALID_BLOCKS` to `resolve(TARGET_MC_VERSION)` (keep `blocks.py` as a shim exporting the resolved set for compat). Add `target_mc_version` to `/generate` request schema (optional, falls back to config) and a UI dropdown.

Also add `oxidation_variants(*bases)` helper generating `exposed_/weathered_/oxidized_/waxed_*` combinations, and audit that the 1.21 copper deco family (`chiseled_copper`, `copper_grate`, `copper_bulb`, `copper_door`, `copper_trapdoor`, cut copper + stairs/slabs ×4 stages ×waxed) is present in the `"1.21"` set.

## 4.2 `knowledge/palettes.py`
Implement `BuildingPalette` + `PALETTES` with AT LEAST these entries (block roles per the v2 plan §7.3): `medieval_castle, gothic_manor, modern_villa, japanese_temple, viking_longhouse, desert_palace, fantasy_tower, ruins, cottage_core, brick_industrial, steel_and_copper, victorian_steam, gritty_deepslate, copper_age_tech, worker_housing, volcanic_works(26.2-gated)`. Startup assertion: every block in every palette ∈ resolve(its min_version). Palette compatibility map for cities: `PALETTE_FAMILIES = {"brick_industrial": {"accents": [...], "compatible": [...]}}`.

`resolve_palette(intent) -> BuildingPalette`: looks up by name; applies `material_overrides` (user-requested blocks win, after registry validation w/ existing fuzzy-repair as fallback).

## 4.3 `knowledge/style_cards.py` + `knowledge/room_kits.py`
- STYLE_CARDS: one per style; ≤120 tokens; format: positives, lighting rule, 2-4 explicit AVOIDs. Include `industrial_victorian` and `industrial_modern` from plan §7.5.
- ROOM_KITS: `{"living": {"must": ["fireplace_or_focal"], "default": ["sofa","rug","side_table","lighting"], "menu": [...]}, "bedroom": ..., "kitchen": ..., "study": ..., "workshop": ..., "storage": ...}` — the per-room op menus served to the interior agent and used by kit-mode furnishing.

**DoD-B:** registry resolves per version with tests (e.g. `copper_lantern` invalid at target 1.21, valid at 1.21.9; cinnabar invalid at 1.21.9); all palettes validate at import; repair chain consumes the gated set; benchmark unchanged (no regressions).

---

# PART 5 — PHASE C: SHELL 2.0 (architecture/)

Implement in this order, each with unit tests against `VoxelGrid`.

## 5.1 `massing.py`
`make_footprint(brief|intent, rng) -> list[Rect]` with shapes rect/L/T/courtyard/tower+wing. Deterministic selection table: size < 9 per side ⇒ rect; house ≥ 12 ⇒ 30% L; manor ⇒ tower+wing; temple/villa(L size) ⇒ courtyard option. Output rects share edges; compute the union outline and interior shared-wall segments (needed by walls.py to skip shared walls).

## 5.2 `walls.py` — the depth system (order per wall face)
```
build_walls(footprint, base_y, height, palette, openings_plan, rng) -> (cmds, list[Wall])
1. plinth: y..y+1 ring in trim
2. pillars: at every outline corner + every 4–6 blocks (choose spacing s.t. bays ≥ 3 wide);
   full height, protrude 1 block OUTWARD (wall_plane + outward normal)
3. infill: dominant block between pillars (use textured_fill if palette.wear)
4. bays: compute Bay list; place windows in every bay with width ≥ 3 except door bay;
   window = glass at inset-1 plane, stair sill below [facing=outward,half=bottom],
   stair/slab lintel above [half=top], trim side frames; window y: floor_y+2..+3
5. cornice: top ring of upside-down stairs (trim) [half=top, facing=inward]
6. door: 2-high opening centered on front_face bay nearest road; cut with air (allowed),
   place door block [facing=...] or leave open archway for industrial gates
```
Geometry invariants to test: pillars never host windows; bay arithmetic exact for lengths 5..50; protruding pillars don't collide between adjacent faces at corners.

## 5.3 `roofs.py`
`build_roof(kind, footprint, top_y, palette, rng) -> cmds` for: `gable` (staircase, ±1 inset/+1 rise, stair blocks with correct `[facing]` per slope side, ridge in roof_solid, **overhang: start 1–2 outside walls — REQUIRED**, gable-end chevron in trim), `flat_parapet` (slab + 1-high trim ring + upside-down-stair lip), `crenellated` (merlon pattern WITHOUT placing air — place merlons only), `pagoda` (2–3 stacked flared gable tiers), `dome` (concentric rings via circle eq, slab smoothing), `spire` (−1 per side per level), `sawtooth` (Phase E detail: repeating asymmetric teeth: vertical glass north face + sloped stair south face, period 4–6). Style→roof selection table in one place.

## 5.4 `floors.py`, `floorplan.py`, `sitework.py`, `texture.py`
- floors: slab per storey + 1-block contrasting border trim; `storeys(brief)` computes (floor_y, ceil_y) bands (storey height 4–5); staircase placer: straight run along a wall (stairs `[facing]` per step, 1×3 headroom hole cut in slab above) and spiral variant for towers/footprints < 7 wide.
- floorplan: BSP per Part 2 Zone contract. Algorithm: recursive split (alternate axis, split point ∈ [40%,60%] via rng; reject leaf < 4×4) until leaves == len(room_program); if interior < 8×8 ⇒ single zone. Room assignment rules: living = largest & adjacent to entrance; kitchen adjacent to living or entrance; bedrooms farthest; hallway spine (width 2) inserted when rooms > 3. Internal walls 1 thick in trim; door opening (1×2 + lintel trim) between every adjacent pair needed to make the room adjacency graph a connected tree (BFS assert). Multi-storey: bedrooms/study upstairs; stair zone reserved & kept clear.
- sitework: entry path (width 2–3, length 5–8, 70/20/10 textured mix), lantern-on-fence pair at path end, garden strip (style-gated; use 1.21.5 clutter: `bush`,`leaf_litter`,`wildflowers` when version ≥ 1.21.5), foundation skirt ring.
- texture: `textured_fill(region, primary, variants, weights, rng)` emitting 1 fill + ≤15% setblock sprinkles; `oxidation_gradient(region, stage_by_height)` mapping copper stages by Y band (fresh low/corners, weathered mid, oxidized peaks) for copper palettes.

## 5.5 `shell2.py`
`build_shell2(brief: BuildingBrief) -> tuple[list[str], BuildingGeometry]` orchestrating 5.1–5.4 and producing the full `BuildingGeometry` (walls, bays, zones, anchors). `pipeline.py` dsl-mode uses this instead of `shell.build_shell`; legacy path untouched. Adapter `intent_to_brief(intent, origin) -> BuildingBrief` bridges the existing intent schema.

**DoD-C:** new tests: pillar spacing law, window-not-on-pillar, overhang present on all gable edges, cornice ring closed, every BSP room reachable from front door, staircase headroom, watertight still 100 on all 15 benchmark prompts in `--no-llm` kit mode. Benchmark: depth_score and roof_complexity jump vs baseline (record the delta in DECISIONS.md).

---

# PART 6 — PHASE D: SEMANTIC DSL + PLACERS

## 6.1 `placers/base.py`
```python
@dataclass
class PlacerResult: cmds: list[str]; claimed: set[tuple[int,int]]; ok: bool; reason: str = ""
OpFn = Callable[..., PlacerResult]
EXTERIOR_OPS: dict[str, OpSpec]    # OpSpec: fn, params schema, valid_styles, cost_rank
FURNITURE_OPS: dict[str, OpSpec]
def match_op(name: str, registry) -> str | None     # exact → fuzzy (reuse repair.py
                                                    # token/Levenshtein machinery) → None
def menu_for(style: str, room: str | None, registry) -> list[str]   # subsetting
```
Execution contract for any op list: sort by priority (must-include features first, large furniture, then small, lighting last is ALWAYS auto), execute sequentially against the Zone occupancy grid; an op that can't fit returns ok=False and is skipped silently (log to repairs report); after all ops, run `flood_walkable`; if a region became unreachable, remove lowest-priority claimed op and re-check; finally `auto_light(zone)` regardless of LLM picks.

## 6.2 `placers/exterior_ops.py` — implement at least
`window_box(face)`, `shutters(face)` (trapdoors `[facing]` beside each window in bays of face), `awning(face)`, `lantern_pair(at=door|corners)`, `climbing_vines(face,density)`, `banner_pair(at)`, `chimney(corner)` (column through roof, trim cap, campfire on top, hole NOT cut — build beside ridge or pass through overhang region computed from geometry), `dormer(face)` (gable roofs only), `flower_strip(face)` (≥1.21.5), `log_framing(faces)`, `path_lamps()`, `doorstep_arch()` (stairs+slabs over door). Every op derives ALL coordinates from `BuildingGeometry` (bays, pillars, roof region) — zero magic numbers.

## 6.3 `placers/furniture.py` — promote `skills/interior_skills.py` prose to code
`sofa(zone,wall,len)` (stairs facing inward + trapdoor armrests + carpet front), `bed(zone,wall)` (+headboard trim), `dining_set(zone,center,size)` (fence+pressure-plate table, stair chairs facing table), `kitchen_run(zone,wall,len)` (slab counter + trapdoor fronts + smoker/barrel/cauldron mix), `fireplace(zone,wall)` (non-flammable surround check vs palette, campfire + iron bars, flue column suppressed if storey above), `desk`, `bookshelf_wall` (chiseled_bookshelf + lectern), `storage_wall` (chest/barrel, ≥1.21.9 may use `copper_chest` + `shelf` rows in workshop/industrial styles), `rug(size,pattern)`, `plant(corner)`, `chandelier()` (fence drop + lanterns; chains ≥ trivial, `copper_chain` if version ≥ 1.21.9), `side_table`, `armchair`, `bathtub`, `ceiling_beams()` (log rows every 3–4 flush to ceiling). Signature pattern: `(zone: Zone, *, rng, palette, version) -> PlacerResult`; facing computed via `INWARD[wall]`.

## 6.4 `placers/lighting.py`
`auto_light(zone|building, palette, version) -> PlacerResult`: greedy set-cover using `propagate_light` — repeatedly place palette.light at the darkest valid cell (wall sconce y+2 preferred, then ceiling) until all floor cells ≥ 8. Deterministic. Also `road_lighting(road_rects, street_set)` for Phase F.

## 6.5 DSL agents (rewrite `exterior_agent.py`, `interior_agent.py` for dsl mode)
Prompt template (exterior, ~450 tokens):
```
You are a Minecraft build designer. Decorating a {style} {archetype}. Palette: {palette_name}.
Facade bays: {bays_summary}. Door: {front_face} face. {style_card}
Pick 6-12 ops from: {menu_for(style)}
Rules: 1) JSON list only 2) ops from the menu only 3) at most 2 ops per face.
Example: [{"op":"lantern_pair","at":"door"},{"op":"chimney","corner":"NE"}]
JSON only. No prose.
```
Interior: ONE batched call for ≤3 small rooms or one call per room ≥ 6×6; context = room name/size/doors/must-include + `menu_for(style, room)`; 4–7 picks. Both agents: Groq `response_format={"type":"json_object"}` (wrap list as `{"ops":[...]}`), temperature 0.15, retry once on parse failure then fall back to ROOM_KITS default kit (never fail the build). Parse → `match_op` fuzzy → drop unknowns. `detail_level=="kit"` skips agents entirely and furnishes from ROOM_KITS via rng.

## 6.6 Deterministic critic (replaces critic core)
`critic.py` (new, deterministic): run `score_build`; auto-patch loop: light gap → auto_light; missing feature → its placer at best free anchor; density below band → +1–2 kit ops; walkability fail → remove blocker. Patches are placer outputs ⇒ always valid. Keep optional `agents/critic_agent.py` 8b call producing ONLY `{"note": "<2 sentences>"}` for the UI when `refine=true`.

**DoD-D:** `--no-llm` (StubLLM canned op lists) full-suite run: zero validator errors, light_coverage = 100 via auto_light, walkability = 100, furniture in band; live run on 3 prompts with 8b AND 70b on agent roles — record score/token comparison in DECISIONS.md (expect dsl-8b ≈ dsl-70b ≫ legacy-70b). Token total per medium house ≤ 5,500.


---

# PART 7 — PHASE E: EXECUTION AT SCALE + INDUSTRIAL ARCHETYPES

## 7.1 `execution/datapack.py` — build this EARLY in Phase E (it de-risks everything)
```python
def write_datapack(commands_by_group: dict[str, list[str]], out_dir: Path,
                   namespace="aibuilder", mc_version=TARGET_MC_VERSION) -> DatapackManifest
```
Requirements:
- Layout: `<out>/aibuilder_datapack/pack.mcmeta` + `data/aibuilder/function/<group>.mcfunction`. `pack.mcmeta` pack_format chosen from a `PACK_FORMAT_BY_VERSION` table (include entries for 1.21.x and 26.x; if unknown, use the highest known and log a warning).
- .mcfunction lines = commands WITHOUT leading `/`; `#` comment header per file (group, command count, build id).
- Shard any group so each file ≤ `FUNCTION_CMD_BUDGET = 60000` (safety margin under default maxCommandChainLength 65536); master function `build_all.mcfunction` runs `function aibuilder:<part>` lines in build order: `00_forceload → 10_terrain → 20_roads → 30_rail_canal → 40_district_* → 80_connectivity → 90_lighting → 99_forceload_off`.
- `00_forceload.mcfunction`: `forceload add x1 z1 x2 z2` over city bounds (chunk-aligned); `99` removes it.
- `undo.mcfunction`: generated inverse — fill the city bounding volumes back to air above ground_y and restore a flat ground slab (best-effort; document limitation in file header).
- Manifest JSON (counts per group, total, paths) returned to UI.
- `POST /export_datapack` → zips the datapack, returns download; UI button + instructions text ("drop into world's datapacks/, run /reload then /function aibuilder:build_all").
- `input_agent.py` gains `trigger_function(name)` (types just `/reload` + `/function ...` via the existing automation) = hybrid mode.

## 7.2 `execution/rcon_client.py` (optional, small)
Pure-stdlib RCON (socket, struct): `RconClient(host, port, password).run(cmd) -> str`, batched `run_many(cmds, per_second=200)` with response check. `/execute` accepts `{"mode":"rcon"|"keyboard"|"function_trigger"}`. Guard: refuse rcon mode unless env `RCON_PASSWORD` set.

## 7.3 `architecture/archetypes/` — industrial library
`base.py`: `class Archetype(ABC): def massing(self, brief) -> list[Rect]; def shell(self, brief) -> (cmds, BuildingGeometry); def detail_kit(self, geom, rng) -> cmds` — default shell delegates to shell2 with archetype-specific wall/roof params. Implement (minimum viable geometry per v2 plan §4, each ~deterministic + seeded jitter):
1. `factory_hall` — sawtooth roof, clerestory strips, sliding-door gate (3-wide × 4-high inset, trapdoor rails), interior: open zone + `workshop` kit (shelves/crates/furnaces rows)
2. `smokestack_plant` — factory_hall + 1–3 stacks: tapering square→octagon column (radius bands), trim band every 8 y, campfire + iron bars top
3. `warehouse` — flat_parapet, pilaster rhythm 4, loading dock platform (slab y+1, stairs, barrel/crate clutter), rail-spur gate on reserved face
4. `rowhouse_strip` — N units 7–10 wide sharing party walls; per-unit: door/window rhythm alternation, accent jitter, chimney; one BSP floorplan template mirrored alternately
5. `office_block` — 3–5 storeys, window grid (window every bay every storey), storefront band (glass + trim) on ground, cornice
6. `water_tower` — 4 legs (log/fence lattice X-brace), tank cylinder (r 3–5), spire cap
7. `gasometer` — cylinder r 8–14 h 8–12, external frame ring of iron_bars columns
8. `gantry_crane` — two towers + beam over reserved rail/dock lane + chain+hook drop
9. `train_depot` — stair-arch barrel roof over 2 parallel rail lines, open gables, platform
10. `dock_finger` — pier slab on log piles over water line, bollards, small crane, boat-hull gesture (stairs)
11. `civic_hall` — symmetric, entry stair, column colonnade (pillar + chiseled capital), dome or clock-tower option (tower w/ clock face: white concrete + black setblock hands)
12. `power_station` — hall + yard: copper_bar "transformer" frames + pole run leaving lot

Register all in `ARCHETYPES: dict[str,Archetype]`; `BuildingBrief.archetype` routes; plain "house/villa/tower/etc." map to a `generic_building` archetype wrapping vanilla shell2.

**DoD-E:** datapack from a benchmark single building loads in a real 1.21.x world (manual smoke test instruction emitted for the user; CI asserts structure/format only); every archetype generates with zero validator errors at 3 lot sizes via parametrized tests; archetype gallery command `python gallery.py` writes one datapack containing all 12 in a row for visual review.

---

# PART 8 — PHASE F: CITY ENGINE

## 8.1 Agents
`agents/city_director.py` — ONE call. JSON schema (enforce via response_format + post-validate):
```json
{"era":"victorian|interwar|modern|dieselpunk",
 "palette_family":"<key of PALETTE_FAMILIES>",
 "districts":[{"type":"heavy_industry|warehouses|housing|civic|rail_yard|docks","share":0.30}],
 "landmarks":["grand_station","power_cathedral","clock_tower","gasometer_park","harbor_crane_row","city_hall"],
 "skyline":"stacks_dominate|center_peak|waterfront_wall",
 "mood":"<max 8 words>"}
```
Validation: shares normalized to sum 1.0; unknown district types fuzzy-matched or dropped with redistribution; 3 ≤ landmarks ≤ 6; defaults injected on any miss (NEVER fail — log substitutions). Model: BUILD_MODEL, temp 0.3, ~400 max output.

`agents/district_stylist.py` — one call PER district (batch all districts in ONE call if total districts ≤ 6: output `{"districts":[...]}` keyed by type). Picks: `archetype_mix` (weights over archetypes valid for the district kind), `accent` (from PALETTE_FAMILIES[family]["accents"]), `street_set` (`gas_lamps|pole_lights|catenary`), `motif` (`pipes_overhead|rail_spurs|canal_side|crane_row|none`). DEFAULT_DISTRICT_STYLE fallback per kind on any failure.

`clarify_agent.py` city-awareness: when prompt matches city-scale regex/keywords (city, town, village, district, "whole …"), brainstorm asks: era, size S/M/L, waterfront?, landmarks wishlist, mood. Same JSON shape as today.

## 8.2 `city/planner.py` — all deterministic, all seeded
- Size table: S=120×120, M=200×200, L=300×300 (config). `ground_y` from origin.
- Reservations first: if waterfront → canal/river strip (width 8–12) along one edge + dock band; rail corridor (width 5) crossing the city tangent to industry side; central plaza in civic district.
- Zoning: weighted seeded region growth on a coarse 10×10-cell grid — seed one cell per district (industry at downwind edge = +x side by convention; civic center; housing opposite industry), grow proportional to share, enforce: housing never adjacent to heavy_industry (insert green/rail buffer cells), docks must touch water.
- Roads: arterial ring/cross (width 9: 7 road + 2 sidewalk), secondary grid pitch 24–36 per district kind (housing denser), alleys 3 wide inside housing superblocks; snap to cell grid; bridge rects where road crosses canal/rail (deck +1y, side walls, support pillars).
- Parceling: district region minus roads → blocks → recursive lot subdivision: industry 24–48/side, housing 7–10 wide × 12–16 deep rows facing road, civic 1–2 oversized lots; every lot gets `faces_road` = side adjacent to nearest road (assert exists); reserve rail-spur lanes from corridor into 30% of industry lots.
- Output `CityPlan` (Part 2 contract) + debug SVG plot (`city/plot.py`, pure-python SVG writer) saved per run — essential for development.

## 8.3 `city/briefs.py`
`make_briefs(plan, city_brief, district_styles, master_seed) -> list[BuildingBrief]`:
height bands by skyline rule (e.g. stacks_dominate: industry stacks 18–28, halls 8–12, housing 6–9, civic 10–14; ±15% jitter); palette = family base + district accent override; `detail_level="llm"` ONLY for lots assigned a landmark (map each landmark name to an archetype + the largest fitting lot in the right district), everything else `"kit"`; per-brief `seed = hash(master_seed, lot.rect)`; rowhouse lots in the same block merged into single `rowhouse_strip` briefs.

## 8.4 `city/connectivity.py`
Road paving with `textured_fill` per tier (e.g. brick_industrial: arterial = stone_bricks/cracked/andesite 70/15/15, sidewalk polished trim, alley = gravel/cobble); street furniture per district `street_set` (lamps every 6–8 on sidewalks via `placers/props.py`; catenary = chain runs across alleys between facade anchors); power poles (log + crossarm + chain sag approximated by 1-block dip midspan) along a route from power_station to each industry district; elevated pipe runs (waxed copper or iron_bars on支columns y+4) power_station→2 nearest factories, following road edges; rail: rails on gravel bed along corridor + spurs into reserved lots through warehouse gates; canal walls (trim) + water fill + moored dock_finger props; plaza kit (paving pattern, statue plinth, benches=stairs, planters w/ 1.21.5 clutter); smoke: ensure every smokestack_plant campfire present (connectivity layer double-checks).

## 8.5 `city_pipeline.py` + API
`build_city(prompt, origin, answers, mode) -> CityResult{plan_summary, usage, manifest, svg_path, qa: CityScore, commands|datapack}`. Flow per v2 plan §3 with per-building generation loop calling the Phase D pipeline (kit briefs run with StubLLM-equivalent kit path = zero tokens). Hard token budget guard: `CITY_TOKEN_BUDGET=40000` — if exceeded mid-run, remaining landmark briefs downgrade to kit mode (log it). `POST /generate_city {prompt, origin, answers?, size?, execute_mode}`; UI: city tab with plan SVG preview + district summary + Export Datapack button. City QA (`city/qa.py`) runs before returning; failing door_to_road auto-fixes by carving a path lot→road (gravel) then re-checks.

**DoD-F:** `--suite cities --no-llm` (StubLLM director/stylist fixtures): all 5 city prompts produce QA-passing plans (door_to_road 100, roads one component, road light 100, no lot overlaps — property-based test with 20 random seeds too); datapack export ≤ 60s for size M on dev machine; live run of 1 city ≤ 40k tokens with usage breakdown printed.

---

# PART 9 — EXECUTION ORDER, GATES, AND BUDGETS

## 9.1 Strict phase order with gates
```
A  Measurement harness (voxel, quality, tokens, StubLLM, benchmarks)    [gate G0]
B  Knowledge layer (version registry, palettes, style cards, kits)      [gate G1]
C  Shell 2.0 (massing, walls, roofs, floors, floorplan, sitework, texture)
D  DSL + placers + det. critic                                          [gate G2]
E  Datapack execution + archetypes                                      [gate G3: flip
                                                                          PIPELINE_MODE default→dsl]
F  City engine (agents, planner, briefs, connectivity, QA, API/UI)      [gate G4: ship]
```
G2 gate criteria (must ALL hold before E): dsl mode beats legacy on benchmark total score for ≥ 13/15 prompts; zero validator errors across suite; mean tokens/house ≤ 5,500; 8b-vs-70b comparison recorded.

## 9.2 Config additions (config.py + .env.example) — single source of truth
```python
PIPELINE_MODE = "legacy"           # legacy | dsl   (flip at G3)
TARGET_MC_VERSION = "1.21.9"
CITY_SIZES = {"S": 120, "M": 200, "L": 300}
FUNCTION_CMD_BUDGET = 60000
CITY_TOKEN_BUDGET = 40000
HOUSE_TOKEN_BUDGET = 6000          # soft warn in logs
DETAIL_LLM_SHARE = "landmarks"     # landmarks | all | none
EXEC_MODES = ["datapack", "keyboard", "rcon", "function_trigger"]
```

## 9.3 Prompt-engineering rules for ALL new agent prompts (enforce in code review)
1. ≤ 7 numbered rules; output-format instruction LAST ("JSON only. No prose.").
2. Exactly ONE perfect few-shot example, loaded from `prompts/examples/<agent>/<style>.json` so Phase-6 few-shot mining can rotate them (mining script: `tools/mine_fewshots.py` picks top-scoring runs from runs.jsonl).
3. Menus are subsetted (style/room/district-valid options only) and rendered compactly: `name(params)` comma-separated.
4. One-line persona max. No essays. Token-count each template in a test: exterior ≤ 500, interior/room ≤ 550, director ≤ 300, stylist ≤ 400 prompt tokens (tiktoken-approx by chars/4 is fine).
5. Every agent has a deterministic fallback (kit/default) — an LLM failure may degrade style, never break a build.

## 9.4 Things you must NOT do
- Do not let any LLM output coordinates or block IDs in dsl mode (assert in tests: agent outputs contain no integers > 3 except lengths/counts ≤ 12, no "minecraft:").
- Do not remove/weaken `_strip_air`, repair, validator, or shell watertight tests.
- Do not introduce network calls in tests (StubLLM only; live runs are manual/benchmark).
- Do not regenerate `templates/index.html` from scratch — extend it (add mode toggle, version dropdown, city tab, datapack button) preserving existing flows.
- Do not exceed file scope: pyautogui stays functional as fallback; Aternos-style hosts have no RCON — datapack is the universal path.
- 26.2 (cinnabar/sulfur) block IDs are PROVISIONAL until 2026-06-16 release notes — keep behind the version gate and add a `tools/verify_blocks_26_2.md` checklist rather than guessing additional IDs.

## 9.5 Deliverables checklist (final PR description must include)
- [ ] Benchmark table: legacy vs dsl (15 buildings), scores + tokens
- [ ] City run report: 1 live city (size M) — plan SVG, QA scores, token usage breakdown, datapack manifest
- [ ] DECISIONS.md — every spec ambiguity you resolved
- [ ] Updated UPGRADE_GUIDE.md + CLAUDE.md sections for the new modules
- [ ] Migration notes: how to flip PIPELINE_MODE, how to install/run the datapack, RCON setup
- [ ] Test count before/after; all green

---

# PART 10 — REFERENCE TABLES (copy into knowledge/ modules)

## 10.1 Style → roof → footprint defaults
| style | roof | footprint bias | palette default |
|---|---|---|---|
| medieval / cottage / rustic | gable | rect, L at ≥12 | medieval_castle / cottage_core |
| modern / industrial-modern | flat_parapet | rect | modern_villa / steel_and_copper |
| castle / fortress | crenellated | tower+wing | medieval_castle |
| japanese | pagoda | courtyard at L | japanese_temple |
| church / fantasy-dome | dome | rect | fantasy_tower |
| tower / wizard | spire | rect (≤9 wide) | fantasy_tower |
| factory / industrial | sawtooth | long rect 1:2+ | brick_industrial |
| victorian-industrial | gable + stacks | L | victorian_steam |

## 10.2 District → archetype menus (stylist picks weights)
| district | archetypes |
|---|---|
| heavy_industry | factory_hall, smokestack_plant, power_station, gasometer |
| warehouses | warehouse, train_depot, gantry_crane |
| housing | rowhouse_strip, generic_building(house), corner_shop(office_block s) |
| civic | civic_hall, office_block, plaza(reserved) |
| rail_yard | train_depot, warehouse, gantry_crane |
| docks | dock_finger, warehouse, gantry_crane, water_tower |

## 10.3 Blockstate cheat sheet (placers must use; never strip these)
`stairs[facing=north|south|east|west, half=bottom|top]` · `slab[type=bottom|top|double]` · `log[axis=x|y|z]` · `trapdoor[facing=…, open=true|false, half=…]` · `door[facing=…, half=lower|upper, hinge=left|right]` (place lower; upper auto) · `lantern[hanging=true|false]` · `campfire[lit=true]` · `chest[facing=…]` · `bed[facing=…, part=foot]` (head auto) · `chain[axis=…]`. Facing convention: the SIDE THE PLAYER FACES varies per block family — encode per-placer, test on voxel grid by asserting state strings, and add an in-game smoke-test function `aibuilder:test/blockstates` generated by `gallery.py`.

## 10.4 Execution math (sanity constants)
- /fill ≤ 32,768 blocks; world Y −64..319 (already in config)
- pyautogui ≈ 6–7 cmd/s ⇒ 20k cmds ≈ 50 min (why datapack mode exists)
- maxCommandChainLength default 65,536 ⇒ FUNCTION_CMD_BUDGET 60,000 with margin
- Size-M city rough budget: terrain 200–600 cmds, roads 800–2,000, buildings 60–150 × (40–220), connectivity 1,500–4,000 ⇒ plan sharding for 10k–40k total

— END OF SPEC —
