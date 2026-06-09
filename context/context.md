# Minecraft Builder — Full Codebase Context

## What This Project Does

An AI-powered Minecraft structure generator. The user describes a building in natural language; the system produces valid Minecraft `/fill` and `/setblock` commands that, when executed, build the structure in-game. Execution is automated by controlling the Minecraft client keyboard via `pyautogui`.

The system is a Flask web app with a React-style frontend. The backend is a multi-agent LLM pipeline backed by the **Groq API** (Llama models by default).

---

## Design Philosophy: Two-Layer Guarantee

The core architectural decision is that **LLMs cannot break structural integrity**:

1. **Deterministic Layer** — `shell.py` generates the building envelope (floor, 4 walls, roof, door, windows) in pure Python math. No LLM involved. Always watertight. Always complete.

2. **LLM Detail Layer** — Two agents (exterior + interior) run in parallel threads and decorate/furnish the shell. They cannot place air (which would punch holes) and cannot overwrite the shell.

3. **Repair Chain** — After LLM output, a deterministic pipeline normalizes block names, fuzzy-matches unknown blocks, strips invalid block states, and splits oversized `/fill` commands to stay within Minecraft's 32,768-block engine limit.

---

## Directory Structure

```
minecraft builder/
├── app.py                    # Flask entry point — HTTP routes
├── pipeline.py               # Main orchestration — calls all agents in order
├── config.py                 # All LLM model/sampling config + Minecraft engine limits
├── llm_client.py             # Groq API wrapper with retry/backoff
├── orchestrator.py           # Intent extraction agent (8b, temp 0.3)
├── clarify_agent.py          # Brainstorm + clarifying questions (8b, temp 0.6)
├── exterior_agent.py         # Facade detailing agent (70b, temp 0.2)
├── interior_agent.py         # Interior furnishing agent (70b, temp 0.3)
├── critic_agent.py           # Post-build review + patch generation (8b, temp 0.1)
├── shell.py                  # Deterministic structural envelope — no LLM
├── normalizer.py             # Block name remapping + adjacent /fill merging
├── repair.py                 # Block ID correction, state stripping, volume splitting
├── validator.py              # Final syntax validation
├── blocks.py                 # ~600 valid Minecraft 1.21.x block IDs
├── input_agent.py            # Keyboard automation to execute commands in-game
├── skills/
│   ├── exterior_skills.py    # Reference patterns: facade decoration (quoins, lanterns, paths…)
│   └── interior_skills.py    # Reference patterns: furniture recipes (sofa, bed, counter…)
├── templates/
│   └── index.html            # Frontend UI (React-style, single page)
├── test_shell.py             # Tests shell produces watertight buildings
├── test_repair.py            # Tests repair chain correctness
├── requirements.txt          # flask, groq, pyautogui, pyperclip, python-dotenv
├── .env.example              # API key + per-agent model override template
├── CLAUDE.md                 # Coding guidelines
└── UPGRADE_GUIDE.md          # How to modify each component
```

---

## HTTP API (app.py)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve `index.html` |
| `/clarify` | POST | Run clarify agent → brainstorm + questions |
| `/generate` | POST | Run full build pipeline → command list |
| `/execute` | POST | Forward commands to input_agent → automate in-game |

### `/clarify` Request/Response
```json
// Request
{ "prompt": "build me a medieval house" }

// Response
{
  "brainstorm": "...",
  "assumptions": "...",
  "questions": ["What size?", "What materials?"]
}
```

### `/generate` Request/Response
```json
// Request
{
  "prompt": "build me a medieval house",
  "origin": {"x": 0, "y": 64, "z": 0},
  "answers": {"size": "medium", "style": "medieval"},
  "brief": "optional one-line summary",
  "refine": true
}

// Response
{
  "intent": { ... },
  "commands": ["/fill 0 64 0 10 64 10 minecraft:stone_bricks", ...],
  "exterior_commands": [...],
  "interior_commands": [...],
  "valid": true,
  "errors": [],
  "repairs": ["Remapped wood_planks → oak_planks"],
  "review": "Solid structure. Missing a fireplace.",
  "score": 82
}
```

### `/execute` Request
```json
{ "commands": ["/fill ...", "/setblock ..."], "delay": 0.15 }
```

---

## Full Data Flow

```
User Prompt
    │
    ▼
clarify_agent.get_clarification(prompt)
    │  returns {brainstorm, assumptions, questions[]}
    │  (user answers questions in UI)
    ▼
orchestrator.get_intent(prompt, answers, brief)
    │  returns Intent JSON (structure_type, size, style, materials, features)
    ▼
┌───────────────────────────────────────────┐
│  shell.build_shell(intent, origin)        │  ← deterministic Python
│  exterior_agent.get_exterior_commands()   │  ← LLM (parallel thread)
│  interior_agent.get_interior_commands()   │  ← LLM (parallel thread)
└───────────────────────────────────────────┘
    │  all three streams merged
    ▼
_clean() pipeline (applied to each LLM stream):
    1. normalize_commands()   — remap generic block names
    2. merge_fills()          — collapse adjacent same-block /fills
    3. repair_commands()      — fuzzy-match, strip bad states, split big fills
    │
    ▼
validate_commands()   — final syntax check (errors list for diagnostics)
    │
    ▼
critic_agent.review_build(intent, anchors, commands)   [if refine=True]
    │  returns {review, score 0-100, additions[]}
    │  patch commands appended to final list
    ▼
Return JSON response to UI
    │
    ▼ (user clicks Execute)
input_agent.execute_commands(commands)
    │  presses T → pastes each command → Enter → repeat
    ▼
Commands execute in Minecraft client
```

---

## Intent Object Schema

Produced by `orchestrator.py`, consumed by shell + all agents:

```json
{
  "structure_type": "house",
  "size": { "x": 15, "y": 6, "z": 12 },
  "style": "medieval",
  "materials": {
    "walls": "minecraft:stone_bricks",
    "floor": "minecraft:oak_planks",
    "roof":  "minecraft:dark_oak_planks",
    "accent": "minecraft:cobblestone"
  },
  "features": ["fireplace", "bookshelves", "cellar entrance"],
  "notes": "Rustic medieval house with stone exterior"
}
```

---

## Coordinate System

- **Origin:** user-provided `{x, y, z}` (defaults to `{0, 64, 0}`)
- **Floor:** `y = origin.y`
- **Walls:** `y = origin.y+1` to `origin.y + size.y - 1`
- **Roof:** `y = origin.y + size.y`
- **Interior X range:** `[origin.x+1, origin.x + size.x - 2]`
- **Interior Z range:** `[origin.z+1, origin.z + size.z - 2]`
- **Interior Y range:** `[origin.y+1, origin.y + size.y - 1]`
- **Anchors:** pre-computed safe coordinates passed to critic agent:
  - `interior_center_floor`, `interior_corner_floor`, `front_door_floor`, `ceiling_center`, `wall_sconce`

---

## Agent Details

### orchestrator.py — Intent Extraction
- **Model:** 8b, temperature 0.3 (deterministic)
- **Input:** raw prompt + user answers + optional brief
- **Output:** structured Intent JSON
- **Role:** translate vague natural language into concrete build parameters

### clarify_agent.py — Intake
- **Model:** 8b, temperature 0.6 (creative)
- **Input:** raw user prompt
- **Output:** `{brainstorm, assumptions, questions[2-4]}`
- **Role:** think through the build and surface ambiguities before committing
- Note: has defensive shape-normalization; always returns a dict even on partial parse failure

### exterior_agent.py — Facade Detailing
- **Model:** 70b, temperature 0.2 (precise)
- **Input:** intent + shell bounds + `exterior_skills.py` reference
- **Output:** 15-30 `/fill` and `/setblock` commands
- **Decorates:** pillars, cornices, window sills, lanterns, entry paths, plinths
- **Constraint:** no air placement; stays within facade surface

### interior_agent.py — Furnishing
- **Model:** 70b, temperature 0.3 (balanced)
- **Input:** intent + interior bounds + `interior_skills.py` reference
- **Output:** 25-45 `/fill` and `/setblock` commands
- **Places:** furniture, rugs, lighting, storage, counters, beds, fireplaces
- **Constraint:** no air placement; stays within interior bounds

### critic_agent.py — Build Review
- **Model:** 8b, temperature 0.1 (analytical)
- **Input:** intent + final command list + anchors (exact coordinates)
- **Output:** `{review: "...", score: 0-100, additions: [commands]}`
- **Role:** checks if mandatory elements are present (e.g., fireplace if requested, enough seating); emits patch commands
- **Design:** best-effort — never fatal; errors produce empty additions

---

## Deterministic Shell (shell.py)

`build_shell(intent, origin) → List[str]`

Always generates these elements in order:
1. **Foundation fill** — solid floor slab
2. **Wall frames** — 4 perimeter walls, full height
3. **Interior air** — clears interior volume (floor+1 to roof-1)
4. **Roof** — either pitched gable or flat parapet, based on style
5. **Door** — 2-block-high opening on front face center
6. **Windows** — placed on all 4 faces at wall midpoints (up to 24 windows)

Material fallback: any invalid block name → `minecraft:oak_planks` (walls), `minecraft:stone` (floor), etc.

---

## Repair Chain Details

### normalizer.py
- `normalize_commands(cmds)` — remaps generic/deprecated names:
  - `minecraft:wood_planks` → `minecraft:oak_planks`
  - `minecraft:stone_slab` → `minecraft:smooth_stone_slab`
  - etc.
- `merge_fills(cmds)` — collapses adjacent `/fill` commands with the same block into one larger fill. Reduces command count.

### repair.py — Core Correctness Layer
`repair_commands(cmds) → (valid_cmds, report)`

Three-stage repair per command:

1. **Block ID correction** — multi-stage lookup:
   - Exact match in `blocks.py` → keep
   - Synonym map → remap
   - Family fallback (e.g., `cherry_stairs` → `oak_stairs`)
   - Fuzzy match (token overlap, Levenshtein-style)
   - Still unknown → drop command, log to report

2. **State stripping** — checks if block supports states; strips `[facing=north]` etc. if block doesn't accept states. Keeps states for blocks like stairs, slabs, doors that legitimately use them.

3. **Volume splitting** — if `/fill` volume > 32,768 blocks, recursively splits along longest axis until all chunks are within engine limit.

### validator.py
`validate_commands(cmds) → (bool, List[str])`

Final syntax check: correct coordinate count, valid block ID, proper `/fill` vs `/setblock` form. Returns error list for diagnostic display in UI.

---

## Block Registry (blocks.py)

~600 valid Minecraft 1.21.x block IDs as a Python `set`. Covers:
- Stone variants (stone, cobblestone, stone_bricks, deepslate, basalt…)
- Wood variants (oak, spruce, birch, jungle, acacia, dark_oak, cherry, mangrove, bamboo…)
- Slabs, stairs, walls, fences, trapdoors
- Concrete, terracotta, wool (all 16 colors)
- Glass, glass panes, tinted glass
- Lighting (lantern, torch, sea_lantern, glowstone, shroomlight, candle…)
- Furniture proxies (crafting_table, fletching_table, cartography_table, chiseled_bookshelf…)
- Nature (leaves, logs, flowers, azalea…)
- Functional (chest, barrel, furnace, blast_furnace, smoker, brewing_stand…)

---

## Configuration (config.py + .env)

### config.py constants
```python
MAX_FILL_VOLUME = 32768     # Minecraft engine /fill limit
WORLD_MIN_Y     = -64       # Minecraft 1.18+ world floor
WORLD_MAX_Y     = 319       # Minecraft 1.18+ world ceiling
DEFAULT_MODEL   = "llama-3.1-8b-instant"
BUILD_MODEL     = "llama-3.3-70b-versatile"
MAX_RETRIES     = 4
RETRY_BASE_DELAY = 2.0      # seconds; doubles each retry
```

### Per-role config
| Role | Model | Temp | Max Tokens | JSON mode |
|------|-------|------|------------|-----------|
| intent | 8b | 0.3 | 1024 | yes |
| clarify | 8b | 0.6 | 1280 | yes |
| exterior | 70b | 0.2 | 2048 | no |
| interior | 70b | 0.3 | 2560 | no |
| critic | 8b | 0.1 | 1280 | yes |

### .env overrides
```
GROQ_API_KEY=...
LLM_MODEL=llama-3.1-8b-instant       # global fallback
LLM_MODEL_INTENT=...                  # per-role overrides
LLM_MODEL_CLARIFY=...
LLM_MODEL_EXTERIOR=...
LLM_MODEL_INTERIOR=...
LLM_MODEL_CRITIC=...
LLM_MAX_RETRIES=4
LLM_RETRY_DELAY=2.0
```

---

## In-Game Automation (input_agent.py)

`execute_commands(commands, delay=0.15)`

For each command:
1. Press `T` to open chat
2. Copy command to clipboard via `pyperclip`
3. `Ctrl+V` paste into chat
4. Press `Enter`
5. Sleep `delay` seconds

Requires Minecraft Java Edition to be the focused window.

---

## Skills / Reference Patterns

These files are included in agent system prompts as reference material:

### skills/exterior_skills.py
Design patterns for facade decoration:
- Quoins (corner pillar blocks)
- Cornice (decorative top-of-wall strip)
- Window sills and lintels
- Entry path (stone/gravel approach to door)
- Wall lanterns / sconces
- Plinth (decorative base strip)

### skills/interior_skills.py
Furniture recipes (which blocks to use for what):
- Sofa: stairs facing each other + carpet
- Bed: standard bed block + decorative headboard
- Dining table: fence post + slab top + chairs (stairs)
- Kitchen counter: slab + trapdoor + barrel/furnace
- Fireplace: netherrack + iron bars + campfire
- Bookshelf cluster: chiseled_bookshelf + lectern
- Storage: chest + barrel + shulker box
- Rugs: carpet patterns on floor
- Lighting: lantern / sea_lantern / glowstone / shroomlight combos

Room kits: living room, bedroom, kitchen, study — predefined sets of furniture for each room type.

---

## Failure Modes and Mitigations

| Failure | Cause | Fix |
|---------|-------|-----|
| Unknown block name | LLM hallucination | repair.py fuzzy-matches; drops if unfixable |
| Invalid block state | LLM doesn't know syntax | repair.py strips states for non-stateful blocks |
| `/fill` > 32k volume | LLM arithmetic error | repair.py splits recursively along longest axis |
| Y coord out of -64..319 | LLM hallucination | repair.py drops command; validator logs error |
| Air punches hole in wall | LLM places air | `_strip_air()` removes all air from agent output |
| Missing mandatory feature | Incomplete furnishing | critic_agent patches; appended to final list |
| Groq API timeout | Network error | llm_client retries up to 4x with exponential backoff |
| Malformed JSON from LLM | Incomplete generation | clarify_agent + critic_agent have defensive parse wrappers |

---

## Tests

### test_shell.py
Simulates commands on a voxel grid, then asserts:
- Every floor cell is solid
- Every roof cell is solid
- Interior cells are air (hollow)
- Door opening exists (2 blocks high)
- No air leaks on any face

Test cases: medieval gable roof, modern flat roof, tiny 5x5 cottage, bad/missing material fallbacks.

**Run:** `python test_shell.py`

### test_repair.py
Asserts:
- Generic names are remapped correctly
- Family fallback works (unknown variant → known base type)
- Invalid block states are stripped
- Valid block states are preserved
- Oversized `/fill` is split into legal-sized chunks
- Unfixable blocks are dropped with log entry

**Run:** `python test_repair.py`

---

## Key Invariants

- Shell is **always** generated first and **always** complete. LLM agents only add detail.
- LLM agents **never** place `minecraft:air` — `_strip_air()` enforces this.
- All commands pass through repair before validation. Validator output is diagnostic only (does not block execution).
- Critic is best-effort — if it fails for any reason, the build proceeds without patches.
- Origin coordinates are user-controlled. The system trusts the user knows where to build.
- Block IDs always include the `minecraft:` namespace prefix in final output.
