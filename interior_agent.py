import re
import json
from llm_client import complete
from skills.interior_skills import INTERIOR_SKILLS

SYSTEM_PROMPT = f"""\
You are a professional Minecraft interior designer. A complete building shell with a
finished FLOOR, ROOF and four WALLS already exists. The interior is empty and hollow.
Your job is to furnish and dress it so it feels lived-in and beautiful.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADD (everything sits on the existing floor surface and inside the walls):
  ✓ Area rugs (carpet over the floor) to zone rooms
  ✓ Room divider walls / railings where the build has multiple rooms
  ✓ Furniture: sofa & chairs (stairs), tables (fence+pressure_plate), beds,
               bookshelves, desks (slab+lectern), kitchen counters (slab+cauldron+campfire),
               storage (barrel/chest), fireplace (nether_bricks+campfire)
  ✓ Plenty of interior lighting (lanterns, sea_lantern, glowstone, shroomlight, froglight)
  ✓ Decorative accents along the walls (paintings via item frames are NOT allowed — use blocks)

✗ Do NOT place minecraft:air. Do NOT build or carve floor, ceiling, roof, or outer walls.
✗ Do NOT go outside the interior bounds below.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY — include ALL of these:
  bed · seating (sofa/chairs) · table · storage · bookshelf · 3+ light sources · a rug

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT RULES:
  - Output ONLY commands, one per line. Zero explanations.
  - Absolute integer coordinates. No ~ or ^.
  - /fill x1 y1 z1 x2 y2 z2 minecraft:block   ·   /setblock x y z minecraft:block
  - Furnish densely but tastefully (~25-45 commands).

REFERENCE SKILLS (safe blocks + furniture recipes):
{INTERIOR_SKILLS}\
"""


def get_interior_commands(intent: dict, origin: dict) -> list[str]:
    x, y, z = origin["x"], origin["y"], origin["z"]
    sx = intent.get("size", {}).get("x", 10)
    sy = intent.get("size", {}).get("y", 6)
    sz = intent.get("size", {}).get("z", 10)

    ix1, iz1 = x + 1, z + 1
    ix2, iz2 = x + sx - 2, z + sz - 2
    floor_surface = y + 1          # furniture sits one above the floor blocks
    head_room = y + sy - 1         # just under the roof

    user_msg = (
        f"Build intent:\n{json.dumps(intent, indent=2)}\n\n"
        f"INTERIOR BOUNDS (stay strictly inside):\n"
        f"  X: {ix1} to {ix2}\n"
        f"  Z: {iz1} to {iz2}\n"
        f"  Floor surface (place furniture here): Y={floor_surface}\n"
        f"  Headroom up to Y={head_room}\n\n"
        "Furnish this space richly: rugs, furniture, storage, bookshelves, a bed, "
        "and several light sources so it is bright. No air, no floor/ceiling/wall building."
    )

    raw = complete("interior", SYSTEM_PROMPT, user_msg)
    return _extract_commands(raw)


def _extract_commands(raw: str) -> list[str]:
    commands = []
    for line in raw.splitlines():
        m = re.search(r'(/(?:fill|setblock)\s+\S.*)', line)
        if m:
            commands.append(m.group(1).strip())
    return commands
