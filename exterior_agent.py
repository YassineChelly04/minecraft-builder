import re
import json
from llm_client import complete
from skills.exterior_skills import EXTERIOR_SKILLS

SYSTEM_PROMPT = f"""\
You are a professional Minecraft facade detailer. A COMPLETE, watertight building shell
(foundation, floor, four walls, roof, a front door, and windows) has ALREADY been built
for you. Your job is to make its exterior look designed and expensive — nothing structural.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADD ONLY decorative facade depth (all on or just outside the existing walls):
  ✓ Corner pillars / quoins (a column of accent block up each corner)
  ✓ A cornice line — a slab or upside-down stair row just under the roof
  ✓ Window sills (slab under windows) and lintels (stair above windows)
  ✓ Lanterns flanking the front door and along the facade
  ✓ A 3-wide entry path of stone/gravel leading out from the front door
  ✓ Planters, benches, small garden details beside the entrance

✗ Do NOT place minecraft:air anywhere. Do NOT carve, cut, or hollow anything.
✗ Do NOT build walls, roof, floor, or foundation — they already exist.
✗ Do NOT cover the windows.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT RULES:
  - Output ONLY commands, one per line. Zero explanations.
  - Absolute integer coordinates. No ~ or ^.
  - /fill x1 y1 z1 x2 y2 z2 minecraft:block   ·   /setblock x y z minecraft:block
  - Prefer /setblock and small /fill for detail. Keep it tasteful, ~15-30 commands.

REFERENCE SKILLS (safe blocks + design principles):
{EXTERIOR_SKILLS}\
"""


def get_exterior_commands(intent: dict, origin: dict) -> list[str]:
    x, y, z = origin["x"], origin["y"], origin["z"]
    sx = intent.get("size", {}).get("x", 10)
    sy = intent.get("size", {}).get("y", 6)
    sz = intent.get("size", {}).get("z", 10)

    x2, z2 = x + sx - 1, z + sz - 1
    wall_lo, wall_hi = y + 1, y + sy - 1
    door_x = (x + x2) // 2

    user_msg = (
        f"Build intent:\n{json.dumps(intent, indent=2)}\n\n"
        f"The shell already exists. Footprint corners: ({x},{z}) to ({x2},{z2}).\n"
        f"Wall courses run Y={wall_lo} (bottom) to Y={wall_hi} (top under the roof).\n"
        f"Front (north) wall is at Z={z}. The door is at X={door_x}, Z={z}, floor Y={wall_lo}.\n"
        f"Roof sits at Y={y+sy}.\n\n"
        "Add tasteful exterior DETAIL only (pillars, cornice, window sills/lintels, "
        "door lanterns, entry path, small garden). No air, no walls, no roof, no carving."
    )

    raw = complete("exterior", SYSTEM_PROMPT, user_msg)
    return _extract_commands(raw)


def _extract_commands(raw: str) -> list[str]:
    commands = []
    for line in raw.splitlines():
        m = re.search(r'(/(?:fill|setblock)\s+\S.*)', line)
        if m:
            commands.append(m.group(1).strip())
    return commands
