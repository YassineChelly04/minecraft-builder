# Minecraft Builder — Full Upgrade Plan
### From "valid boxes" to "pro-grade architecture" on zero budget

---

## 0. Executive Diagnosis

Your pipeline is well-engineered for **correctness** (watertight shell, repair chain, air stripping). What it lacks is **architecture**. The root causes, ranked by impact:

| # | Root cause | Symptom you see | Fix class |
|---|-----------|-----------------|-----------|
| 1 | **LLMs do coordinate math.** Weak models cannot do spatial arithmetic reliably. Every `/setblock 103 65 207` they emit is a dice roll. | Floating furniture, furniture inside walls, decorations in wrong spots, wasted repair cycles | Replace raw commands with a **semantic placement DSL** — LLM picks *what & where conceptually*, Python computes coordinates |
| 2 | **The shell is a flat box.** Flat walls, flat roof option, windows at midpoints. No pro builder ever makes a flat box. | "Basic", "no architectural vision" | **Shell 2.0** — parametric architecture engine, pure Python, zero LLM cost |
| 3 | **The interior is one open room.** No floorplan, no internal walls, no hallways, no doors between spaces. | "Lack of connectivity" | **Deterministic BSP floorplan generator** + per-room furnishing |
| 4 | **Pro knowledge lives in prompt prose.** Skill files are pasted as text the weak LLM must "understand" and re-derive into coordinates. | Tokens burned, knowledge ignored | Encode techniques as **Python placer functions**; LLM only references them by name |
| 5 | **Palette is per-block, not per-system.** Intent agent picks individual block IDs; no dominant/trim/accent discipline. | Monotone, flat-textured walls | **Curated palette library** keyed by style; LLM picks a palette *name* |
| 6 | **Critic is an LLM doing a checklist job.** | Token spend, vague reviews | **Deterministic critic** (voxel-sim checklist) + optional 1-call style note |

**The strategic inversion:** today your deterministic layer guarantees *validity* and the LLM layer provides *creativity*. After this plan, the deterministic layer provides *validity AND craftsmanship* (depth, palettes, roofs, floorplans, furniture geometry), and the LLM layer provides only *taste decisions* — tiny, cheap, hard to get wrong.

Weak LLMs are excellent at: classification, picking from menus, filling small JSON schemas, ordering preferences.
Weak LLMs are terrible at: arithmetic, 3D spatial reasoning, long structured output, remembering 30 constraints.
Design every agent call so it lives entirely in the first list.

---

## 1. Target Architecture (after upgrade)

```
User Prompt
    │
    ▼
CLARIFY (8b, 1 call, ~400 output tokens)
    │  brainstorm + 2-4 questions (unchanged, slightly compressed)
    ▼
INTENT (8b, JSON-schema mode, ~250 output tokens)
    │  {structure_type, size_class, style, palette_name, room_program[], features[]}
    │   NOTE: picks palette NAME and room LIST — never block IDs, never coordinates
    ▼
┌─────────────────────────── DETERMINISTIC CORE (Python, 0 tokens) ───────────────────────────┐
│ 1. PALETTE RESOLVER     palette_name → {dominant, trim, accent, roof, glass, light} blocks  │
│ 2. MASSING ENGINE       size_class + style → footprint (rect / L / T / courtyard), heights  │
│ 3. SHELL 2.0            walls w/ pillar rhythm, recessed windows, plinth, cornice,          │
│                         roof library (gable/hip/pagoda/dome/crenellated/flat+parapet),      │
│                         1-2 block roof overhang, gable-end detailing                        │
│ 4. FLOORPLAN (BSP)      interior → rooms + internal walls + door openings + hallway,        │
│                         room rects exported as named zones                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────── PARALLEL SEMANTIC AGENTS (70b or 8b, DSL output only) ──────────────┐
│ EXTERIOR AGENT: picks 6-12 facade ops from a MENU                                 │
│   [{"op":"window_boxes","faces":["S"]},{"op":"lantern_pair","at":"door"}, ...]    │
│ INTERIOR AGENT (per room, batched): picks furniture kits + placements             │
│   [{"room":"living","place":"sofa","wall":"N"},{"room":"living","place":"rug",    │
│     "size":"large"}, ...]                                                         │
└────────────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
PLACER LIBRARY (Python, 0 tokens)
    │  Each op/kit name → exact /fill & /setblock commands with correct
    │  blockstates ([facing=...], [half=...]) computed from zone geometry
    ▼
NORMALIZE → REPAIR (unchanged, but now mostly idle — DSL can't produce bad blocks)
    ▼
DETERMINISTIC CRITIC (voxel sim checklist: light coverage, walkability,
    │                  feature presence, palette ratio) → auto-patch from placer lib
    ▼
[optional] LLM STYLE NOTE (8b, 1 call, ~120 tokens) — flavor text for the UI only
    ▼
Commands → execute
```

Key property: **an LLM hallucination can no longer produce a bad block, a bad coordinate, or a bad blockstate** — it can only produce an unknown op name, which the DSL parser drops or fuzzy-matches against the menu. Your repair chain becomes a safety net that almost never fires.

---

## 2. Phase Plan Overview

| Phase | Name | Effort | Token impact | Visual impact | Depends on |
|-------|------|--------|--------------|---------------|------------|
| 0 | Measurement harness | 1-2 days | — | — (enables everything) | — |
| 1 | Shell 2.0 (parametric architecture) | 3-5 days | 0 (pure Python) | ★★★★★ | 0 |
| 2 | Palette library + style cards | 1 day | −30% intent tokens | ★★★★ | 0 |
| 3 | Semantic placement DSL + placer library | 4-6 days | −80% agent tokens | ★★★★ | 1 |
| 4 | BSP floorplan + per-room furnishing | 3-4 days | neutral | ★★★★★ (connectivity) | 1, 3 |
| 5 | Deterministic critic + auto-patch | 2 days | −95% critic tokens | ★★ | 0, 3 |
| 6 | Prompt compression + few-shot mining | ongoing | −40% remaining | ★★ | 0 |
| 7 | Fine-tuning track (only if still needed) | 1-2 weeks | — | ★ | 0-6 |

Do them in order. Phase 1 alone will make builds look dramatically better with **zero** extra LLM cost. Phase 3 is the big token win. Phase 7 is deliberately last — read §9 before assuming you need it.


---

## 3. Phase 0 — Measurement Harness (do this first)

You can't optimize what you can't score. You already have a voxel simulator in `test_shell.py` — promote it into a **build quality scorer**.

### `quality.py` — automated metrics (all computable from the voxel grid, no LLM)

```python
def score_build(commands, intent, zones) -> dict:
    grid = simulate(commands)                  # reuse test_shell voxel sim
    return {
        # CORRECTNESS (you already have these)
        "watertight":        check_watertight(grid),
        "door_reachable":    check_door(grid),

        # CRAFTSMANSHIP (new)
        "palette_ratio":     palette_distribution(grid),   # target: dominant 60-70%,
                                                            # trim 20-30%, accent 5-10%
        "depth_score":       count_depth_features(grid),   # pillars, recesses, overhang
                                                            # cells protruding/inset vs wall plane
        "light_coverage":    pct_floor_cells_lit(grid),    # BFS light propagation,
                                                            # target ≥ 85% of floor at light ≥ 8
        "walkability":       pct_floor_reachable(grid),    # flood-fill from door;
                                                            # furniture must not block rooms
        "furniture_density": furniture_per_room(grid, zones),  # target 0.10-0.25
                                                                # occupied floor cells per room
        "feature_presence":  features_found(grid, intent["features"]),
        "roof_complexity":   roof_layer_count(grid),       # flat slab = 1 → bad
        "headroom":          min_clearance_over_floor(grid),
    }
```

### Regression suite

Create `benchmarks/` with ~15 fixed prompts (cottage, medieval manor, modern villa, tower, Japanese temple, tiny 5×5, warehouse…). After every change, run:

```
python run_benchmark.py   →  prints score table + diff vs last run + total tokens used
```

Log **tokens per build** (Groq returns usage in every response — sum them in `llm_client.py` and persist to `runs.jsonl`). Your two dashboards from now on: *quality score up, tokens down*.

This harness is also what makes Phase 6 (prompt optimization) and Phase 7 (fine-tuning data) possible — every good build you ever generate becomes labeled training data for free.

---

## 4. Phase 1 — Shell 2.0: Parametric Architecture Engine

**The single highest-impact change, and it costs zero tokens.** Everything below is deterministic Python in `shell.py` (or a new `architecture/` package). These are the techniques pro builders use, encoded as geometry:

### 4.1 Massing (footprint) — kill the rectangle

```python
FOOTPRINTS = {
    "rect":      lambda sx, sz: [Rect(0, 0, sx, sz)],
    "L":         lambda sx, sz: [Rect(0, 0, sx, int(sz*0.6)),
                                 Rect(0, int(sz*0.6), int(sx*0.55), sz)],
    "T":         ...,
    "courtyard": ...,   # ring of rects around an open center (style: villa, temple)
    "tower+wing": ...,  # square tower attached to a rect hall (medieval)
}
```

Selection rule (deterministic, from intent): houses ≥ 12 blocks on a side get a 30% chance of L-shape, manors get tower+wing, temples get courtyard, etc. Shapes are unions of rects, so your existing wall/floor/roof code generalizes: iterate over rects, then knock out shared walls.

### 4.2 Wall system — the depth rules from pro builders, as code

For every exterior wall face, generate in this order:

1. **Plinth** — bottom row (y to y+1) in trim block, protruding 0 or kept flush with accent
2. **Pillar rhythm** — full-height trim-block columns at every corner **and every 4-6 blocks** along the wall, protruding 1 block outward (`/fill` thin columns at wall_plane+1)
3. **Wall infill** — dominant block between pillars
4. **Window recesses** — windows are placed **between** pillars (never on them), inset 1 block from the wall plane, with:
   - sill: stair block `[facing=outward, half=bottom]` below the window
   - lintel: stair block `[facing=outward, half=top]` or slab above
   - frame sides: trim block
5. **Cornice** — top row: upside-down stairs (`[half=top]`) in trim block running the perimeter, creating a lip under the roof
6. **Gable-end detailing** — on gable walls, a trim-block chevron following the roof line

Window placement upgrade: instead of "midpoint of each face," compute bays = wall segments between pillars; place a window in each bay whose width ≥ 3, skip bays on the door segment. This alone makes facades look *designed*.

### 4.3 Roof library — one function per type, chosen by style

| Style keyword | Roof | Construction |
|---|---|---|
| medieval, cottage, rustic | **Staircase gable** | per-layer: inset ±1, rise +1, stair blocks `[facing]` on slopes, planks on ridge; **overhang: start 1-2 blocks past the wall** |
| modern, industrial | **Flat + parapet** | slab layer + 1-high trim wall around edge; add a 1-block roof lip (upside-down stairs) |
| castle, fortress | **Crenellated** | parapet with alternating merlon/gap (place merlons, never air — gaps are simply not filled) |
| japanese, asian | **Pagoda** | 2-3 stacked staircase layers with exaggerated stair-block flare at each tier edge |
| church, mosque, fantasy | **Dome** | concentric rings, radius shrinks following circle equation, slabs for smoothing |
| tower, wizard | **Pointed spire** | footprint −1 per side per level until 1×1 |

Each roof function takes (footprint_rects, base_y, palette) and returns commands. The overhang rule (extend 1-2 past walls) is non-negotiable — it's the #1 visual difference between amateur and pro roofs.

**Note on gaps/openings:** Shell 2.0 is the deterministic layer, so it *is* allowed to place air (crenellation gaps, recesses, dormers). Keep `_strip_air()` for LLM streams only — unchanged.

### 4.4 Multi-storey support

If `size.y ≥ 9` or intent says "2 floors": insert intermediate floor slab(s) every 4-5 blocks of height, add a deterministic **staircase placer** (spiral in a corner for towers, straight run along a wall for houses — stairs with correct `[facing]` per step, headroom hole cut in the slab above). This is pure geometry; never let an LLM attempt a staircase.

### 4.5 Site work (cheap, huge effect)

- **Entry path**: 2-3 wide path (path/gravel/stone variants randomized 70/20/10) from door extending 5-8 blocks out
- **Foundation skirt**: if origin terrain is uneven, one ring of trim block around the base
- **Corner lanterns**: lantern-on-fence posts flanking the path end
- **Garden strip** (style-gated): leaves/flower row along front wall

### 4.6 Texture variance (the "worn" look)

Pro builds never use 100% one block on large surfaces. Add a deterministic randomizer:

```python
def textured_fill(region, primary, variants, weights, rng):
    # e.g. stone_bricks 75%, cracked_stone_bricks 15%, mossy_stone_bricks 10%
    # emit one /fill for the primary, then sprinkle /setblock for variant cells
```

Seed the RNG from the prompt hash → reproducible builds. Gate by style (modern concrete stays clean; medieval/ruins get variance). Keep sprinkle density ≤ 15% so command count stays sane (a 15×6 wall ≈ 13 extra setblocks).


---

## 5. Phase 2 — Palette Library + Style Cards

### 5.1 `palettes.py` — the rule of three, enforced by data

The intent agent currently invents block IDs (then you repair them). Stop that. Curate ~15-20 palettes; the LLM picks a **name**:

```python
PALETTES = {
    "medieval_castle":  {"dominant": "tuff_bricks",      "trim": "cobblestone",
                         "accent": "chiseled_tuff",       "roof": "dark_oak_stairs",
                         "roof_solid": "dark_oak_planks",  "glass": "glass_pane",
                         "light": "lantern",
                         "wear": ["cracked_stone_bricks", "mossy_stone_bricks"]},
    "gothic_manor":     {"dominant": "dark_oak_planks",  "trim": "deepslate_bricks",
                         "accent": "iron_bars",            "roof": "deepslate_tile_stairs", ...},
    "modern_villa":     {"dominant": "white_concrete",   "trim": "gray_concrete",
                         "accent": "dark_oak_trapdoor",    "roof": "smooth_stone_slab",
                         "glass": "glass", "light": "sea_lantern", "wear": []},
    "japanese_temple":  {"dominant": "spruce_planks",    "trim": "smooth_stone",
                         "accent": "cherry_planks",        "roof": "dark_oak_stairs", ...},
    "viking_longhouse": {"dominant": "spruce_planks",    "trim": "dark_oak_log",
                         "accent": "cobblestone", ...},
    "desert_palace":    {"dominant": "sandstone",        "trim": "smooth_sandstone",
                         "accent": "terracotta", ...},
    "fantasy_tower":    {"dominant": "purpur_block",     "trim": "end_stone_bricks",
                         "accent": "amethyst_block", ...},
    "ruins":            {"dominant": "cobblestone",      "trim": "mossy_stone_bricks",
                         "accent": "glow_lichen", "wear_density": 0.30, ...},
    # ... copper_manor, industrial, cottage_core, pale_horror, pirate, nordic_modern ...
}
```

Every palette entry is pre-validated against `blocks.py` at import time (assert on startup). Hallucinated palettes impossible. User-specified materials still win: if the user says "make walls out of quartz," intent captures it in a `material_overrides` field that the resolver applies on top of the palette.

### 5.2 Style cards — ≤120 tokens of taste, injected per call

Replace the long skill-file prose in agent prompts with one tiny card looked up by style:

```python
STYLE_CARDS = {
  "medieval": "Asymmetry ok. Heavy timber accents. Warm light only (lantern/torch/"
              "campfire). Banners + barrels outside. Inside: rugs, bookshelf walls, "
              "big hearth as focal point. Avoid: concrete, sea lanterns, quartz.",
  "modern":   "Symmetry + clean lines. Large glass. Cool light (sea lantern, end rod). "
              "Minimal furniture, low profile (slabs not stairs). Monochrome rugs. "
              "Avoid: cobble, fences as legs, torches.",
  ...
}
```

This is where the "pro tips" live in LLM-visible form — short, opinionated, with explicit *avoid* lists (negative guidance is disproportionately effective on weak models).

---

## 6. Phase 3 — Semantic Placement DSL (the big one)

### 6.1 Principle

> **The LLM never writes a number. The LLM never writes a block ID.**

Agents output compact JSON ops chosen from a menu. A Python **placer library** expands ops into commands with perfect coordinates and blockstates.

### 6.2 Exterior agent — before/after

**Before (now):** prompt ≈ 1,500 tokens (skill prose + bounds + rules), output ≈ 1,200 tokens of raw commands, ~30% of which need repair.

**After:** prompt ≈ 450 tokens:

```
You are decorating a {style} {structure_type}. Palette: {palette_name}.
Facade bays: S:4 N:4 E:2 W:2. Door: S face. Style: {style_card}

Pick 6-12 ops from this menu (JSON list only):
window_box(face) · shutters(face) · awning(face) · lantern_pair(at: door|corners)
· climbing_vines(face, density) · banner_pair(at) · chimney(corner) · dormer(face)
· flower_strip(face) · log_framing(faces) · path_lamps() · doorstep_arch()

Example: [{"op":"lantern_pair","at":"door"},{"op":"chimney","corner":"NE"}]
```

Output ≈ 120 tokens. The placer knows where bays, corners, and the door are (from Shell 2.0's geometry objects) and emits exact commands — stairs facing the right way, trapdoor shutters `[facing=...]` on the correct side of each window, chimney punched through the roof overhang with a campfire on top.

### 6.3 Placer library structure

```
placers/
├── geometry.py        # Zone, Wall, Bay, Anchor dataclasses (built by Shell 2.0)
├── exterior_ops.py    # one function per menu op: window_box(), chimney(), ...
├── furniture.py       # sofa(), bed(), dining_set(), kitchen_run(), fireplace(),
│                      #   desk(), bookshelf_wall(), bathtub(), storage_wall(), rug() ...
└── lighting.py        # auto_light(room): computes lantern/sconce positions to
                       #   guarantee light ≥ 8 everywhere (deterministic, from quality.py BFS)
```

Each furniture function is your existing `interior_skills.py` recipes **promoted from prose to code**, parameterized by wall/orientation:

```python
def sofa(room: Zone, wall: str, length: int = 3) -> list[str]:
    """Stairs in a row facing into the room + end trapdoor armrests + carpet in front."""
    facing = INWARD[wall]                  # correct [facing=] computed, not guessed
    cells  = room.along_wall(wall, length, clearance=1)
    ...
```

This is also exactly where Minecraft pro tricks get encoded once, correctly, forever: armrests via trapdoors, table legs via fence+pressure-plate top, fridge via iron-door+iron-block, fireplace with campfire + iron bars + non-flammable surround + chimney hole check, headboards, kitchen counters with smoker/barrel runs, item-frame "paintings," and so on.

### 6.4 Interior agent — per-room calls with tiny context

With the Phase 4 floorplan, furnish **per room** (or batch 2-3 small rooms per call):

```
Room: living (7x5). Style: {style_card}. Palette: {palette_name}.
Doors on: S,E walls (keep clear). Must include: fireplace.
Menu: sofa(wall,len) · armchair(corner) · coffee_table(center) · fireplace(wall)
· rug(size) · bookshelf_wall(wall) · plant(corner) · chandelier() · side_table(corner)
Pick 4-7 ops. JSON only.
Example: [{"place":"fireplace","wall":"N"},{"place":"sofa","wall":"S","len":3}]
```

Why per-room beats one big call for weak LLMs: short context → fewer constraints to juggle → near-zero violation rate. Five tiny calls at ~500 prompt + 80 output tokens each ≈ **2,900 tokens total**, vs your current single interior call at ~4,000+, with far better results. (If rate limits bite harder than tokens, batch rooms 2-at-a-time.)

The placer enforces what the LLM can't be trusted with: door clearance, walkable paths (run the flood-fill check after placement, drop the lowest-priority op if blocked), no overlapping furniture (occupancy grid per room), `auto_light()` always runs last regardless of what the LLM picked.

### 6.5 Reliability mechanics for weak models

1. **JSON schema mode** — Groq supports `response_format: {"type": "json_object"}` and (on newer models) `json_schema`. Use it on every agent. Malformed JSON drops to ~0.
2. **One perfect few-shot example** in every prompt (as shown above). For weak models, 1 example > 300 tokens of rules.
3. **Fuzzy op matching** — LLM writes `"lanterns"` instead of `"lantern_pair"`? Levenshtein-match against the menu (reuse your repair.py machinery). Unknown after fuzzy → drop silently.
4. **Temperature 0.1-0.2 + retry-on-parse-failure only.** Creativity should come from menu richness and per-style weighting, not sampling noise.
5. **Menu subsetting** — only show ops valid for this style/room (modern rooms don't see `banner_pair`). Shorter menu = better picks.

### 6.6 Token budget — before vs after (typical medium house)

| Call | Now (in+out) | After (in+out) |
|---|---|---|
| clarify | 900 + 400 | 600 + 300 |
| intent | 800 + 350 | 450 + 180 |
| exterior | 1500 + 1200 | 450 + 120 |
| interior | 1800 + 1800 | 5×(500 + 80) = 2900 |
| critic | 1200 + 400 | 0 (deterministic) — opt. 300 + 120 style note |
| **Total** | **≈ 10,350** | **≈ 5,000** (−52%) |

…while quality goes *up*, because the 70b's capacity is spent on taste instead of arithmetic. Bonus: with the DSL, test whether **8b can replace 70b** for exterior/interior (it's now a menu-picking task). If benchmark scores hold, your rate-limit headroom roughly 10x's.


---

## 7. Phase 4 — Floorplan & Connectivity (BSP)

This directly fixes "the buildings lack connectivity."

### 7.1 Deterministic room partition

```python
def generate_floorplan(interior: Rect, room_program: list[str], rng) -> Floorplan:
    """
    Binary Space Partition:
      - recursively split the interior rect (alternating axes, split point 40-60%)
        until the number of leaves == len(room_program)
      - reject splits creating rooms < 4x4; tiny interiors (< 8x8) stay single-room
      - assign room types to leaves by simple rules:
          kitchen/living adjacent to entrance · bedrooms farthest from door ·
          largest leaf = living · hallway inserted if >3 rooms (1-2 wide spine)
    Walls: 1-block internal partitions in trim or dominant block.
    Doors: every room gets >=1 two-high opening to an adjacent room/hallway,
           chosen so the whole-floor connectivity graph is a connected tree
           (BFS check on the room adjacency graph — guaranteed reachable).
    """
```

`room_program` comes from intent (the 8b is great at this: *"medium medieval house" → ["living","kitchen","bedroom"]*). For 2 storeys: bedrooms upstairs, staircase placed in hallway or living room, landing kept clear.

Output: a `Floorplan` object with named `Zone`s — exactly what the per-room interior agent and placers consume. Internal door openings are cut by the deterministic layer (allowed to place air), and lintels get a trim block for polish.

### 7.2 Inter-building connectivity (future-friendly)

Because everything is anchored to geometry objects, "build me a village" later becomes: massing engine places N footprints → A* path placer connects doors with roads → lamp posts every 6 blocks. The architecture you're building in Phases 1-4 makes this nearly free.

---

## 8. Phase 5 — Deterministic Critic + Auto-Patch

Your critic is an LLM doing a checklist's job. Replace its core with `quality.py` (Phase 0):

```
score_build() →
  light_coverage < 85%      → auto_light() patches (computed positions, not suggested)
  walkability < 100%        → remove lowest-priority furniture op blocking the path
  requested feature missing → look up its placer; place at best free anchor
  furniture_density < 0.10  → add 1-2 ops from the room's default kit
  palette_ratio off         → flag in UI (informational)
```

Patches come from the **placer library**, so they're always valid. The numeric score shown in the UI is now real and reproducible instead of an 8b's vibe. Keep an *optional* single 8b call ("Write 2 sentences of architect's commentary on this build: …") purely for UX flavor — 120 tokens, skippable.

---

## 9. Phase 6 — Squeezing the Weak LLMs (prompt-level optimization)

Discipline that compounds across all remaining calls:

1. **Prompt structure for small Llamas:** task statement first, hard rules as a numbered list of ≤7 items, menu, ONE example, then "JSON only. No prose." Weak models obey the last instruction best — put the output-format command last.
2. **Strip dead weight:** no personas longer than one line, no "you are a world-class architect with 20 years…" — costs tokens, adds nothing measurable. One line: "You are a Minecraft build designer."
3. **Few-shot mining (free fine-tuning):** every benchmark run stores (prompt context → agent JSON → resulting quality score). Periodically take the top-scoring exemplars and rotate them in as the few-shot example for that style. Your prompts literally learn from your best builds, no training required. (This is DSPy-style optimization done by hand; if you want to automate it, DSPy itself is free and works with Groq.)
4. **Cache clarify/intent for repeated prompts** (hash → response) during development; you'll re-run benchmarks constantly.
5. **Rate-limit-aware scheduling:** Groq free tier limits are per-model. Spread roles across model families (e.g. intent on `llama-3.1-8b-instant`, interior on `llama-3.3-70b-versatile`, exterior on `qwen` or `gemma2-9b-it` if benchmark scores allow) so one build never burns a single model's quota. Re-benchmark per model — menus make models far more interchangeable.
6. **A/B harness:** `run_benchmark.py --agent interior --model X --prompt-variant Y`. Decide with score deltas, never with vibes.

---

## 10. Phase 7 — Fine-Tuning Track (honest assessment: probably unnecessary)

**Read this before spending weeks here.** After Phases 1-5, your LLM tasks are: pick a palette name, list rooms, pick ops from a menu. 8b-class models do this near-perfectly with a good prompt. Fine-tuning attacks a problem (spatial command generation) that the new architecture *deletes*.

If benchmarks still show a gap (e.g., op selections are stylistically bland), here's the zero-budget path:

1. **Data is the product of Phase 0/6:** accumulate `(context → op-JSON)` pairs from your highest-scoring builds + hand-curate ~200-500 gold examples (an evening of work per agent — you're picking JSON, not writing commands).
2. **Train a small open model free:** Unsloth + QLoRA on Google Colab free tier (T4) or Kaggle (P100, 30 h/week) fine-tunes Llama-3.2-3B / Qwen2.5-7B on a few hundred examples in under an hour. Export GGUF.
3. **Serving is the real constraint:** Groq does **not** host your fine-tunes (LoRA hosting is enterprise-only). Your free options: run the 3B GGUF locally via llama.cpp/Ollama on your own machine (a 3B menu-picker runs fine on CPU), or keep Groq for everything and use the fine-tune only if you have a machine to serve it from. Wire it in via your existing `LLM_MODEL_*` env override + an OpenAI-compatible local endpoint in `llm_client.py`.
4. **What to fine-tune for, if anything:** style-conditioned op selection (taste), intent extraction from messy prompts, clarify-question quality. **Never** fine-tune for coordinate generation — that war is unwinnable with small models and already won by the DSL.

Decision rule: only start Phase 7 if, after Phase 6, a specific agent's benchmark score is the bottleneck AND prompt iteration has plateaued across 5+ variants.

---

## 11. Pro Tips & Tricks — Master Encoding Checklist

Where each piece of pro-builder knowledge lives after the upgrade:

| Technique | Encode in | Phase |
|---|---|---|
| Pillar rhythm every 4-6 blocks, corners always | shell walls | 1 |
| Window recess + stair sill + lintel | shell windows | 1 |
| Roof overhang 1-2 blocks | roof library | 1 |
| Roof type per style (gable/pagoda/dome/spire/crenellation) | roof library | 1 |
| Plinth + cornice (upside-down stair lip) | shell walls | 1 |
| Rule of three palettes (60-70 / 20-30 / 5-10) | palettes.py + quality.py ratio check | 2, 0 |
| Texture variance (cracked/mossy sprinkle) | textured_fill | 1 |
| Gradient/aging (copper oxidation stages, moss near ground) | palette `wear` fields + sprinkle weighting by height | 2 |
| Furniture recipes (sofa=stairs+trapdoor armrests, table=fence+plate, fridge=iron door…) | placers/furniture.py | 3 |
| Light level ≥ 8 everywhere (no mob spawns, no gloom) | auto_light() | 3, 5 |
| Door clearance + walkable paths | placer occupancy grid + flood fill | 3 |
| Focal point per room (hearth/bed/table) | room kit "must include first" ordering | 3, 4 |
| Rooms sized ≥ 4×4, bedrooms private, kitchen near entry | BSP assignment rules | 4 |
| Entry path + lamp posts + garden strip | site work | 1 |
| Chimney through roof + campfire smoke | exterior_ops.chimney | 3 |
| Ceiling beams every 3-4 blocks (logs flush to ceiling) | interior op `ceiling_beams()` | 3 |
| Floor border trim (1-block contrasting perimeter) | shell floor | 1 |
| Style avoid-lists (no torches in modern, no quartz in medieval) | style cards + menu subsetting | 2, 3 |

---

## 12. Suggested Schedule (solo dev, ~3-4 weeks part-time)

```
Week 1   Phase 0 (scorer + benchmark + token logging)
         Phase 2 (palettes + style cards — small, do it early)
         Phase 1 start (wall system: pillars, recesses, plinth, cornice)
Week 2   Phase 1 finish (roof library, massing, site work, texture variance)
         → run benchmark: expect the biggest visual jump of the whole plan
Week 3   Phase 3 (geometry objects, placer library, DSL prompts for both agents)
         → run benchmark: expect the biggest token drop; try 8b on agent roles
Week 4   Phase 4 (BSP floorplan, per-room furnishing, staircases)
         Phase 5 (deterministic critic + auto-patch)
         Phase 6 begins and never ends (few-shot mining loop)
```

### Migration safety
- Keep the old freeform-command path behind a flag (`PIPELINE_MODE=legacy|dsl`) until DSL benchmark scores dominate on all 15 prompts.
- `repair.py` / `validator.py` stay exactly as they are — they're your safety net and your test oracle.
- Extend `test_shell.py` with Shell 2.0 cases: pillar count per wall length, overhang present on all roof edges, every BSP room reachable from the front door, no window placed on a pillar.

---

## 13. TL;DR

1. **Stop asking LLMs for coordinates.** Menu-driven semantic DSL + Python placers: −80% agent tokens, near-zero repairs, weak models perform like strong ones.
2. **Put the architecture in Python.** Pillar rhythm, recessed windows, roof library with overhangs, plinth/cornice, texture variance, footprint massing — all deterministic, all free, biggest visual win.
3. **BSP floorplans** give you rooms, internal walls, doors, hallways → real connectivity, plus per-room furnishing that small models handle easily.
4. **Palettes by name, taste by 120-token style cards** — the pro knowledge lives in code and tiny cards, not prompt essays.
5. **Score every build automatically** (light, walkability, palette ratio, depth) and let the deterministic critic auto-patch from the placer library.
6. **Fine-tuning last, and probably never** — the new architecture deletes the problem fine-tuning would have solved; if you do it, Unsloth+Colab is free but you must self-host the result.
