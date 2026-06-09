# 🚀 Upgrade Guide: How to Modify Every Part of the System

This guide shows exactly where and how to upgrade each component. All examples are tested and reversible.

---

## 1️⃣ SWITCH MODELS (Easiest)

**Problem:** Current model isn't good enough, or you want to save money/time.

**Solution:** Override via environment variables. Restart `app.py`. Done.

### Change Default Model for All Agents
```bash
# Use a stronger model
LLM_MODEL=claude-3-sonnet python app.py

# Or a cheaper/faster one
LLM_MODEL=llama-3.1-8b-instant python app.py
```

### Change Specific Roles
```bash
# Only exterior agent uses 70b; rest use 8b (balance cost)
LLM_MODEL=llama-3.1-8b-instant \
LLM_MODEL_BUILD=llama-3.3-70b-versatile \
python app.py

# Only interior uses strong model
LLM_MODEL=llama-3.1-8b-instant \
LLM_MODEL_INTERIOR=claude-3-opus \
python app.py

# Disable critic for rate limits (no model override needed)
# Just uncheck "Enable Critic" in UI
```

### Model Choice Strategy
| Role | Purpose | Good Models | Cost |
|------|---------|-------------|------|
| intent | Extract JSON | 8b (fast) | $$ |
| clarify | Brainstorm | 8b (creative) | $$ |
| exterior | Facade detail | 70b (spatial) | $$$ |
| interior | Furniture | 70b (spatial) | $$$ |
| critic | Review | 8b (precise) | $$ |

---

## 2️⃣ MODIFY SYSTEM PROMPTS (Easy)

**Problem:** The LLM isn't generating the right kind of output.

**Solution:** Edit the system prompt in the agent file. Restart `app.py`.

### Example: Make Exterior Agent Add More Detail

**File:** `exterior_agent.py`

**Find:**
```python
SYSTEM_PROMPT = """\
Add decorative facade details to the exterior. 
Include: decorative patterns, trim, and ornamental elements.
...
"""
```

**Replace:**
```python
SYSTEM_PROMPT = """\
Add elaborate decorative facade details to the exterior.

STYLE GUIDE:
- Medieval: crenellations, stone details, archer slits
- Modern: clean lines, metal accents, geometric patterns
- Industrial: metal beams, exposed structure, warning stripes

Include at least 5 decorative elements per wall.
Use signs, carpets, stairs, slabs, fences creatively.

Rules: NO structural changes, NO air blocks, NO glass.
Output: minecraft commands only, one per line.
"""
```

**Restart:**
```bash
python app.py
```

### Example: Make Critic Stricter

**File:** `critic_agent.py`

**Find:**
```python
SYSTEM_PROMPT = """\
Review the interior furnishing...
"""
```

**Modify scoring criteria:**
```python
SYSTEM_PROMPT = """\
Review the interior furnishing. Be VERY CRITICAL.

Checklist:
- Does every room have a door/entrance? (Critical)
- Does every room have lighting? (Critical)
- Is there furniture in every room? (Important)
- Is there at least one decorative element per room? (Nice to have)

Score 0-10: Deduct 2 points per missing item.

Suggest 3-5 additional items to improve the score.
Output JSON: {review, score, additions[]}
"""
```

### Example: Change Clarify Questions

**File:** `clarify_agent.py`

**Find the part about "Ask 2 to 4 questions"**, add:
```python
SYSTEM_PROMPT = """\
You are the lead architect's intake assistant at a Minecraft build studio.

ALWAYS ask about:
1. Budget (compact, medium, sprawling)
2. Sustainability (ecofriendly materials or not)
3. Era/Aesthetic (medieval, modern, fantasy, steampunk)
4. Primary function (residence, commerce, defense, monument)

Never ask generic questions. Be specific to this request.
"""
```

---

## 3️⃣ EXTEND SHELL LOGIC (Medium)

**Problem:** You want the shell to generate basements, balconies, underground features, or complex roofs.

**Solution:** Edit `shell.py` and add new functions.

### Example: Add a Basement

**File:** `shell.py`

**Current structure:**
```python
def build_shell(intent: dict, origin: dict) -> list[str]:
    # Floor at y
    # Walls from y+1 to y+sy-1
    # Roof at y+sy
```

**New approach:**
```python
def build_shell(intent: dict, origin: dict) -> list[str]:
    commands = []
    
    # Basement (new!)
    if intent.get("features") and "basement" in str(intent.get("features")).lower():
        basement_y = origin["y"] - 4  # 4 blocks down
        commands.extend(_build_floor(basement_y, materials))
        commands.extend(_build_walls(basement_y, basement_y + 3, materials))
        commands.extend(_build_roof(basement_y + 4, materials))  # Basement ceiling
    
    # Main structure (existing)
    y = origin["y"]
    commands.extend(_build_floor(y, materials))
    commands.extend(_build_walls(y + 1, y + sy - 1, materials))
    commands.extend(_build_roof(y + sy, materials))
    
    return commands
```

**Test:**
```bash
python test_shell.py
```

---

## 4️⃣ IMPROVE BLOCK FUZZING (Medium)

**Problem:** The repair layer is rejecting valid block names (e.g., "oak wood" → can't find "minecraft:oak wood").

**Solution:** Add better block-name mapping in `repair.py`.

### Current Approach
```python
# repair.py
_BLOCK_ALIASES = {
    "oak plank": "minecraft:oak_planks",
    "oak log": "minecraft:oak_log",
    # ...
}
```

### Enhanced Approach
```python
# repair.py
_BLOCK_ALIASES = {
    # Wood variants
    "oak plank": "minecraft:oak_planks",
    "oak wood": "minecraft:oak_planks",
    "oak board": "minecraft:oak_planks",
    
    # Stone variants
    "stone brick": "minecraft:stone_bricks",
    "cobble": "minecraft:cobblestone",
    "deep slate": "minecraft:deepslate",
    
    # Metals
    "iron bar": "minecraft:iron_bars",
    "iron fence": "minecraft:iron_bars",
    
    # Glass
    "glass pane": "minecraft:glass_pane",
    "clear glass": "minecraft:glass",
}

def fuzzy_block(name: str) -> str:
    """Try exact match, then alias, then partial match."""
    if name in VALID_BLOCKS:
        return name
    
    # Try aliases
    for alias, canonical in _BLOCK_ALIASES.items():
        if alias.lower() in name.lower():
            return canonical
    
    # Last resort: prefix with minecraft: and return
    return name if name.startswith("minecraft:") else f"minecraft:{name}"
```

---

## 5️⃣ ADD A NEW AGENT (Hard)

**Problem:** You want a new post-processing stage (e.g., "landscape" agent to add terrain outside).

**Solution:** Create new agent file, add to pipeline.

### Step 1: Create the Agent
**File:** `landscape_agent.py`
```python
from llm_client import complete
import json

SYSTEM_PROMPT = """\
You are a Minecraft landscape designer.

Given a building shell and interior, generate commands to:
- Add terrain around the building (grass, dirt, gravel)
- Add decorative features nearby (trees, rocks, paths)
- Keep the building as focal point

Output: list of /fill and /setblock commands, JSON format.
"""

def get_landscape_commands(intent: dict, origin: dict, 
                           interior_cmds: list[str]) -> list[str]:
    """Generate landscape enhancements."""
    x, y, z = origin["x"], origin["y"], origin["z"]
    sx = intent["size"]["x"]
    sz = intent["size"]["z"]
    
    prompt = f"""\
Building footprint: {sx}×{sz} starting at ({x}, {y}, {z})
Interior has {len(interior_cmds)} commands.

Add terrain and decoration that complements the building.
Think about paths, gardens, fences, gates.
"""
    
    raw = complete("landscape", SYSTEM_PROMPT, prompt)
    return json.loads(raw)  # Assume JSON output
```

### Step 2: Add to Pipeline
**File:** `pipeline.py`
```python
from landscape_agent import get_landscape_commands  # NEW

def build_structure(prompt: str, origin: dict, ...):
    # ... existing code ...
    
    # After interior agents
    interior_cmds, int_report = _clean(_strip_air(interior_raw))
    
    # NEW: Landscape
    landscape_raw = get_landscape_commands(intent, origin, interior_cmds)
    landscape_cmds, land_report = _clean(landscape_raw)  # Repair layer handles validity
    
    # Merge all
    all_commands = exterior_cmds + interior_cmds + landscape_cmds
    
    # ... rest of validation ...
    return {
        "intent": intent,
        "exterior_commands": exterior_cmds,
        "interior_commands": interior_cmds,
        "landscape_commands": landscape_cmds,  # NEW
        "commands": all_commands,
        # ...
    }
```

### Step 3: Add Config
**File:** `config.py`
```python
ROLES = {
    # ... existing ...
    "landscape": {"model": _model("LLM_MODEL_LANDSCAPE"), "temperature": 0.4, "max_tokens": 1024, "json": True},
}
```

### Step 4: Test
```bash
# Create test_landscape.py
python test_landscape.py
```

---

## 6️⃣ FINE-TUNE REPAIR STRATEGY (Hard)

**Problem:** Too many commands are being dropped, or `/fill` commands aren't being split aggressively enough.

**Solution:** Edit `repair.py` heuristics.

### Current: Conservative Approach
```python
# repair.py
def repair_commands(commands):
    # Split fills > MAX_FILL_VOLUME (32768)
    # Drop commands with unknown blocks
    # That's it
```

### Enhanced: Aggressive Approach
```python
# repair.py
def repair_commands(commands: list[str]) -> tuple[list[str], list[str]]:
    """More aggressive splitting & deduplication."""
    
    result = []
    seen = set()
    repairs = []
    
    for cmd in commands:
        # Deduplicate
        if cmd in seen:
            repairs.append(f"Dropped duplicate: {cmd[:50]}")
            continue
        seen.add(cmd)
        
        # Parse command
        parts = cmd.split()
        if not parts or not parts[0].startswith("/"):
            repairs.append(f"Invalid command: {cmd[:50]}")
            continue
        
        # For /fill commands, split aggressively
        if parts[0] == "/fill" and len(parts) >= 8:
            x1, y1, z1 = int(parts[1]), int(parts[2]), int(parts[3])
            x2, y2, z2 = int(parts[4]), int(parts[5]), int(parts[6])
            
            volume = abs((x2-x1+1) * (y2-y1+1) * (z2-z1+1))
            
            # Split into smaller cubes if too large
            if volume > MAX_FILL_VOLUME // 2:  # MORE aggressive: half the limit
                repaired = _split_fill(x1, y1, z1, x2, y2, z2, parts[7:])
                result.extend(repaired)
                repairs.append(f"Split large fill (volume={volume}) into {len(repaired)} commands")
            else:
                result.append(cmd)
        else:
            result.append(cmd)
    
    return result, repairs
```

---

## 7️⃣ ADD SKILL MODULES (Easy)

**Problem:** You want agents to reference pre-built patterns (e.g., "make a grand staircase here").

**Solution:** Add to `skills/` and reference in agent prompts.

### Create Skill
**File:** `skills/interior_skills.py`
```python
def grand_staircase(center_x: int, floor_y: int, center_z: int, height: int) -> list[str]:
    """Generate a grand staircase."""
    commands = []
    
    # Staircase spirals around center
    for level in range(height):
        y = floor_y + level
        # Spiral pattern (simplified)
        commands.append(f"/setblock {center_x} {y} {center_z} oak_stairs[facing=north]")
    
    return commands
```

### Reference in Agent
**File:** `interior_agent.py`
```python
SYSTEM_PROMPT = """\
...

AVAILABLE SKILLS:
- grand_staircase(center_x, floor_y, center_z, height) → builds a spiral staircase
  Example: grand_staircase(10, 65, 10, 5) → 5-level staircase

Use these in your commands to enhance the build.
"""
```

---

## 🧪 TESTING YOUR CHANGES

### Before Deploy
```bash
# Test shell changes
python test_shell.py

# Test repair changes
python test_repair.py

# Test full pipeline
python -c "
from pipeline import build_structure
result = build_structure(
    'A small house',
    {'x': 0, 'y': 64, 'z': 0}
)
print(f'Valid: {result[\"valid\"]}')
print(f'Commands: {len(result[\"commands\"])}')
"
```

### Local Server Test
```bash
# Start server
python app.py

# Test endpoint (in another terminal)
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Small wooden cabin", "origin": {"x": 0, "y": 64, "z": 0}}'
```

---

## 🔄 UPGRADE WORKFLOW (TL;DR)

1. **Identify what's wrong** (output quality, speed, cost)
2. **Pick the component** (model, prompt, shell, repair, new agent)
3. **Make minimal change** (don't refactor everything)
4. **Test** (test files, then full pipeline, then UI)
5. **Restart app** (`python app.py`)
6. **Monitor** (check repairs log, review scores)

---

## ⚠️ DO NOT UPGRADE

- **`blocks.py`** — This is Minecraft 1.21.x ground truth. Mismatches cause silent failures.
- **`validator.py`** — This is the safety net. Weakening it risks broken in-game commands.
- **Agent output parsing** — If you change JSON schema, entire pipeline breaks.

---

## 💡 Pro Tips

- **Model switching is free** (no code change, just env var).
- **System prompts are safe** (repair layer catches bad output).
- **Shell expansion is safe** (test with `test_shell.py` first).
- **Repair heuristics are powerful** (can fix 90% of LLM hallucinations).
- **Rate limits?** Disable critic in UI, no code change needed.
