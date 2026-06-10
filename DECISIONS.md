# DECISIONS.md

Running log of every spec ambiguity resolved during the v2 upgrade
(per IMPLEMENTATION_SPEC §0.4). Newest first.

## Phase G — UI redesign (Editorial Light)

- **Full rethink of `templates/index.html`** at the user's explicit request (this
  overrides spec §9.4's "don't regenerate index.html"). Direction chosen by the
  user: **Editorial Light** — paper `#FAFAF8`, ink `#16181D`, single blue accent
  `#2F6BFF`, hairline borders (no glow), big type scale, Inter + JetBrains Mono,
  zero emoji (the old `◈ ✦ ▣ ★ ▶` glyphs and rainbow-quadrant logo read as "AI
  slop"). The empty canvas uses a faint dotted blueprint grid.
- **All flows preserved** (`/clarify` → `/generate` → `/execute`) and the JS
  contract kept. **New v2 controls wired in:** Engine toggle (Shell 2.0 / Legacy →
  sends `mode`), MC-version selector (feeds `target_mc_version` to generate +
  export), a live **token meter** (usage vs the 6000 soft budget), **Copy** and
  **Export datapack** actions (the latter downloads the zip from
  `/export_datapack`), and a mode-aware pipeline strip (Intent→Architecture→
  Furnish→Light→Validate for dsl). Verified via Flask test client: template
  renders, dsl generate returns valid + token usage, datapack zip downloads.

## Phase E — Execution + industrial archetypes — COMPLETE

- **All 12 archetypes** in `architecture/archetypes/` (factory_hall, smokestack_
  plant, warehouse, rowhouse_strip, office_block, water_tower, gasometer,
  gantry_crane, train_depot, dock_finger, civic_hall, power_station) + a
  `generic_building` that wraps shell2. Shell-based ones override the roof and add
  signature detail; open structures (tower/gasometer/gantry/pier) build custom
  cylinder/leg geometry and return a `minimal_geometry` stub (footprint + door
  anchor for city pathing, no rooms). `register` is a class decorator that
  instantiates — `ARCHETYPES` holds instances. Pipeline routes via
  `build_archetype(brief)`. Parametrized test: validator-clean at 3 lot sizes ×13.
- **`execution/rcon_client.py`** — pure-stdlib Source RCON (socket+struct), `run`
  / `run_many`, auth-guarded. `gallery.py` writes one datapack with all 12 in a row.
- Benchmark unchanged (dsl mean ~95).

(datapack writer details below remain as built in the earlier partial.)

## Phase E (datapack writer, built first)

- **Delivered: `execution/datapack.py` + `/export_datapack`.** The spec calls the
  datapack writer the de-risking piece to build first; it's the universal
  execution path (Aternos has no RCON; pyautogui is too slow for 10k+ cmds). Writes
  `pack.mcmeta` (pack_format by version table, unknown→highest+warn), per-group
  `.mcfunction` files (leading `/` stripped), a `build_all` master in BUILD_ORDER,
  shards any group over `FUNCTION_CMD_BUDGET`, plus a best-effort `undo`. CI asserts
  structure/format; the in-world load is a manual smoke test. `/export_datapack`
  zips it for download. `/generate` now accepts `mode` and strips the
  non-serialisable geometry before jsonify.
- **NOT yet done in Phase E:** RCON client, the 12 industrial archetypes
  (`architecture/archetypes/`), and `gallery.py`. These are a large surface and
  are the main outstanding single-building work.

## Phase F — City engine — NOT STARTED

The full city engine (planner/zoning/roads/parceling, city_director +
district_stylist agents, briefs, connectivity, QA, city_pipeline, city tab UI) is
the largest remaining phase and is not yet implemented. Config + budgets
(`CITY_SIZES`, `CITY_TOKEN_BUDGET`) and the `prompts_cities.json` benchmark +
`run_benchmark` city plumbing (graceful "not built yet") are in place as the
landing pad.

## Phase D — DSL + placers + deterministic critic

- **DoD-D / G2 result (dsl, `--no-llm`).** Mean quality **95.4/100** (baseline
  72.9), 15/15 valid, ~310 tokens/build (≤5500 budget). `light_coverage` →~100
  via `auto_light`, furniture in band, fireplace feature detected. dsl beats
  legacy on **15/15** prompts → G2 gate (≥13/15) satisfied.
- **auto_light = greedy set-cover over a BFS light field.** Ceiling-hung lanterns
  (supported by the roof slab) so they never block the 2-high walk clearance; in
  tall halls a supported bracket+lantern drops within ~6 of the floor so the floor
  still reaches ≥8.
- **The LLM never writes a coordinate or block id.** `dsl_interior.parse_ops`
  keeps only known op NAMES (fuzzy-matched to the room menu) and discards any
  coords/block ids the model emits — verified by a guard test feeding malicious
  JSON. Parse failure → kit defaults, so a build never breaks.
- **Furnishing preserves walkability.** Placers run along walls and claim
  occupancy; the walkability metric measures reachability over the *remaining* air
  floor, so wall-hugging furniture doesn't count against it. A few large rooms with
  centre dining sets sit ~92–93 (a couple of pinched cells) — the spec's
  "remove-blocker" walkability repair is noted as a refinement, not yet added.
- **Scope delivered vs deferred in Phase D.** Delivered: `placers/base.py`,
  `placers/lighting.py` (auto_light + road_lighting), `placers/furniture.py` (full
  furniture kit), deterministic `critic.py` (furnish + auto_light + feature patch),
  and the **interior** DSL agent (`agents/dsl_interior.py`). Deferred:
  `placers/exterior_ops.py` (facade ops) and the **exterior** DSL agent — the
  facade op placers are a large additional surface; the interior agent already
  proves the menu-pick→placer thesis end-to-end. Live 8b-vs-70b A/B needs a
  GROQ_API_KEY (manual run); the offline kit/StubLLM path is fully tested.

## Phase C — Shell 2.0

- **DoD-C result (dsl kit mode, `--no-llm`).** 15/15 valid, mean quality
  **83.4/100** vs legacy baseline **72.9**. `depth_score` 0→100 (protruding
  pillars), `roof_complexity` →100 (real gable/flat/pagoda/dome/spire/sawtooth
  with overhang), walkability/headroom/door 100. Tokens **~310/build** (intent
  only) vs ~2085. Remaining gaps — `light_coverage`, `furniture_density`,
  `feature_presence` — are Phase D (auto_light + placers) by design.
- **Command convention deviation.** Spec §2 says generators emit commands WITHOUT
  a leading slash. We keep the leading `/` (cmd_fill/cmd_set) so Shell 2.0 flows
  through the EXISTING normalize→repair→validate chain unchanged (invariant 2).
  The datapack writer (Phase E) strips the slash for `.mcfunction`.
- **`merge_fills` breaks carve ordering — DSL path skips it.** `merge_fills`
  globally reorders *all* `/fill` ahead of all `/setblock`. Shell 2.0 carves air
  (door/window openings) after solid fills and sprinkles texture via `/setblock`;
  under the reorder a sprinkle setblock could re-block a door. The dsl path uses
  `_clean_ordered = repair(normalize(...))` (no merge) to preserve order. Legacy
  keeps merge_fills.
- **BSP doors carved last.** Each recursive split inserts one wall + one door, so
  the room graph is the BSP tree (connected). Deeper-split walls were overwriting
  shallower doors, so ALL internal doors are now carved after ALL internal walls
  (doors win), guaranteeing reachability — verified by a flood test on every zone.
- **Single rectangular footprint in v1.** massing returns the lot rect; L / T /
  courtyard / tower+wing (multi-rect with shared-wall skipping via a boundary-cell
  wall builder) are deferred — they need the general union-outline wall pass and
  aren't required for DoD-C. Watertightness + reachability are guaranteed on the
  rect path. Multi-storey: storey bands are computed and a straight-staircase
  placer is unit-tested, but shell2 currently builds one tall interior storey;
  full upper-floor slabs + furnished upstairs deferred with the multi-rect work.
- **score_build is geometry-aware.** When a BuildingGeometry is supplied the
  envelope comes straight from it (true footprint), instead of the grid heuristic
  which protruding pillars/overhang would otherwise fool.

## Phase B — Knowledge layer

- **No import cycle.** `blocks.py` becomes a shim that resolves the valid set from
  the registry, so the literal 1.21 set was moved to `knowledge/_base_blocks.py`
  (pure data, imports nothing). `blocks_registry` imports that; `blocks.py` imports
  the registry + config. No cycle.
- **resolve() returns full `minecraft:` ids.** repair/validator compare against
  namespaced ids, so the registry namespaces everything (version-addition sets may
  be written bare). `VALID_BLOCKS` now tracks `TARGET_MC_VERSION` (default 1.21.9,
  626 blocks) — repair/validator are *extended*, never weakened (invariant 4).
- **Palette block ids stored bare.** Cleaner palette tables; namespaced via
  `BuildingPalette.mc()` at command-build time. Import-time `_validate_palettes()`
  raises if any palette block is invalid at its `min_version` (fail at startup).
- **material_overrides policy.** A user/legacy override block is applied only if it
  resolves valid at the target version; otherwise it is silently ignored (the
  palette default stands) rather than failing the build. Fuzzy-repair of overrides
  deferred — repair.py still catches bad ids downstream.
- **Deferred to Phase E/F:** `target_mc_version` request param + UI version
  dropdown and the `mode` per-request override are config-ready (`PIPELINE_MODE`,
  `TARGET_MC_VERSION`) but not yet surfaced in app.py/UI; wired when the dsl path
  and city tab land.

## Phase A — Measurement harness

- **DoD-A baseline (legacy pipeline, `--no-llm`).** 15/15 buildings valid, mean
  quality total **72.9/100**, ~2085 tokens/build (stub-approx). Consistently
  failing metrics: `watertight` (openings counted against blended craftsmanship
  score), `light_coverage`, `depth_score`, `furniture_density` — i.e. the exact
  weaknesses Shell 2.0 (Phase C) and placers (Phase D) exist to fix. Scores are
  identical across prompts because the offline stub returns one canned intent;
  live runs differentiate. This is the number every later phase must beat.
- **Root test scripts kept.** `test_shell.py` / `test_repair.py` at repo root are
  left as standalone smoke scripts (memory references them); their logic is now
  the source-of-truth pytest suite under `tests/`. They are not collected by
  pytest (`testpaths = tests`).


- **`voxel.py` extraction.** The grid simulator in `test_shell.py` is promoted
  verbatim in behaviour (last-write-wins, parses `/fill` + `/setblock`, strips
  block state for grid storage but keeps the full id available). `test_shell`'s
  local `simulate()` now delegates to `VoxelGrid` so there is one source of truth.
- **Light model.** `propagate_light` is a BFS from every light source, −1 per
  step (Chebyshev/6-neighbour), blocked by solid non-light blocks. This is a
  deterministic approximation of Minecraft light, sufficient for scoring "is the
  floor lit ≥ 8". Light value of a source = `LIGHT_SOURCES[base_name]`.
- **`flood_walkable`.** 2-high clearance flood fill on the floor plane: a cell is
  walkable if the cell and the cell above it are non-solid (air). 4-neighbour.
- **Scorer altitude.** `quality.py` works off the voxel grid + an optional
  `BuildingGeometry`. Where geometry is absent (legacy intent dict), metrics that
  strictly need zones/walls degrade gracefully to a heuristic or are reported as
  `None` rather than crashing — the legacy baseline must still score.
- **StubLLM.** Offline LLM stand-in keyed by role; returns canned JSON from
  `tests/fixtures/`. Selected when `--no-llm` is passed or `LLM_STUB=1` env set.
  This keeps the deterministic ~90% of the system testable with zero network.
- **Token logging.** `llm_client.complete` now returns `(text, UsageLog)` via a
  new `complete_logged`; the old `complete(role, system, user) -> str` signature
  is preserved as a thin wrapper so no existing caller breaks. A thread-local
  accumulator collects per-request usage; `pipeline` attaches it to the result.
