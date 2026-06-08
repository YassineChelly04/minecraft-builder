import re
import json
from llm_client import get_client, get_model
from skills.exterior_skills import EXTERIOR_SKILLS

SYSTEM_PROMPT = f"""\
You are a professional Minecraft architect. You generate exterior /fill and /setblock commands only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR SCOPE — generate ONLY these:
  ✓ Foundation (1-2 block step wider than walls, heavier material)
  ✓ Outer walls — 1 BLOCK THICK SHELL ONLY — do NOT fill interior
  ✓ Roof structure
  ✓ Window openings (use minecraft:air to cut holes: 2W×3H standard)
  ✓ Door openings (use minecraft:air: 2W×3H minimum, leave at least 1 door on front wall)
  ✓ Exterior pillars, cornices, overhangs, ledges (facade depth)
  ✓ Entry path (3-wide stone/gravel from front door outward)
  ✓ Exterior lighting (lantern or sea_lantern on pillars, embedded in path)

  ✗ Do NOT fill the building interior — it will be handled separately
  ✗ Do NOT place floor inside — exterior walls only
  ✗ Do NOT place furniture

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOLLOW WALL RULE — CRITICAL:
  Build walls as a HOLLOW BOX:
    Step 1: /fill x1 y1 z1 x2 y2 z2 block          ← full solid box
    Step 2: /fill (x1+1) y1 (z1+1) (x2-1) y2 (z2-1) minecraft:air  ← carve out interior

  OR build each face as a flat plane (1 block thick):
    North wall: /fill x1 y1 z1  x2 y2 z1  block
    South wall: /fill x1 y1 z2  x2 y2 z2  block
    West wall:  /fill x1 y1 z1  x1 y2 z2  block
    East wall:  /fill x2 y1 z1  x2 y2 z2  block

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMAND EFFICIENCY RULE:
  Use the MINIMUM number of commands. ONE large /fill beats 10 small ones.
  Think in volumes: floor row → one fill. Wall face → one fill.
  Only use /setblock for individual decorative blocks (lanterns, corners).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT RULES:
  - Output ONLY commands, one per line. Zero explanations, zero comments.
  - All coordinates are absolute integers — no ~ or ^.
  - /fill:     /fill x1 y1 z1 x2 y2 z2 minecraft:block_name
  - /setblock: /setblock x y z minecraft:block_name
  - Max 32768 blocks per /fill (split if larger).
  - Build order: foundation → walls (hollow) → roof → cut windows/doors → details → lighting → path

REFERENCE SKILLS (safe blocks + design principles):
{EXTERIOR_SKILLS}\
"""


def get_exterior_commands(intent: dict, origin: dict) -> list[str]:
    x, y, z = origin["x"], origin["y"], origin["z"]
    sx = intent.get("size", {}).get("x", 10)
    sy = intent.get("size", {}).get("y", 6)
    sz = intent.get("size", {}).get("z", 10)

    user_msg = (
        f"Build intent:\n{json.dumps(intent, indent=2)}\n\n"
        f"Origin corner: x={x}, y={y}, z={z}\n"
        f"Building footprint: {sx} wide (X) × {sy} tall (Y) × {sz} deep (Z)\n"
        f"Wall corners: ({x},{y},{z}) to ({x+sx-1},{y+sy-1},{z+sz-1})\n\n"
        "Generate exterior commands.\n"
        "MANDATORY:\n"
        "- Walls must be HOLLOW (1 block thick shell — carve interior with air)\n"
        "- Cut at least 1 door opening (2W×3H air) on the front wall\n"
        "- Cut window openings on each visible wall\n"
        "- Use ONE /fill per large area — do not repeat row by row\n"
        "- Add facade depth (pillars, cornices, ledges)\n"
        "- Add exterior lighting and entry path"
    )

    client = get_client()
    response = client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
    )

    raw = response.choices[0].message.content
    return _extract_commands(raw)


def _extract_commands(raw: str) -> list[str]:
    commands = []
    for line in raw.splitlines():
        m = re.search(r'(/(?:fill|setblock)\s+\S.*)', line)
        if m:
            commands.append(m.group(1).strip())
    return commands
