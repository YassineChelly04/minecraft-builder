# DECISIONS.md

Running log of every spec ambiguity resolved during the v2 upgrade
(per IMPLEMENTATION_SPEC §0.4). Newest first.

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
