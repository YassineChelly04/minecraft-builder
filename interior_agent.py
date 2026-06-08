import re
import json
from llm_client import get_client, get_model
from skills.interior_skills import INTERIOR_SKILLS

SYSTEM_PROMPT = f"""\
You are a professional Minecraft interior designer. You generate interior /fill and /setblock commands only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR SCOPE — generate ONLY these:
  ✓ Interior floor (1 block inside walls, at floor_y)
  ✓ Interior ceiling (1 block inside walls, at ceiling_y)
  ✓ Room divider walls
  ✓ Furniture: sofa (stairs), chairs (stairs), dining table (fence+pressure_plate),
               bed (colored bed block), bookshelves (bookshelf block),
               desk (slab+lectern), kitchen counter (slab+cauldron+campfire),
               storage (barrel/chest grid), fireplace (nether_bricks+campfire)
  ✓ Interior lighting (glowstone hidden above ceiling slab, shroomlight in alcoves)
  ✓ Decorative details

  ✗ Do NOT place exterior walls, roof, or foundation
  ✗ Do NOT go outside the interior bounds given below

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMAND EFFICIENCY RULE — CRITICAL:
  Use the MINIMUM number of /fill commands.
  Cover entire floor with ONE /fill. Cover entire ceiling with ONE /fill.
  Only use multiple fills when using genuinely different blocks.
  NEVER generate 5 fills for 5 rows — use 1 fill for the whole area.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY ELEMENTS — you MUST include ALL of these:
  1. Floor fill (one /fill covering the full interior floor area)
  2. Ceiling fill (one /fill covering the full interior ceiling area)
  3. At least ONE bed (minecraft:red_bed or any colored bed)
  4. At least ONE bookshelf or chiseled_bookshelf
  5. At least ONE light source (glowstone, sea_lantern, shroomlight, or lantern)
  6. At least ONE seating element (stairs used as chair or sofa)
  7. At least ONE storage block (chest, barrel, or ender_chest)
  8. Furniture appropriate to the building type

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT RULES:
  - Output ONLY commands, one per line. Zero explanations, zero comments.
  - All coordinates are absolute integers — no ~ or ^.
  - /fill:     /fill x1 y1 z1 x2 y2 z2 minecraft:block_name
  - /setblock: /setblock x y z minecraft:block_name
  - Max 32768 blocks per /fill.
  - Build order: floor → ceiling → room dividers → furniture → lighting → decoration

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
    floor_y   = y + 1
    ceiling_y = y + sy - 1

    user_msg = (
        f"Build intent:\n{json.dumps(intent, indent=2)}\n\n"
        f"Origin corner: x={x}, y={y}, z={z}\n"
        f"Building footprint: {sx}W × {sy}H × {sz}D\n\n"
        f"INTERIOR BOUNDS (stay inside these):\n"
        f"  X: {ix1} to {ix2}\n"
        f"  Y: {floor_y} (floor) to {ceiling_y} (ceiling)\n"
        f"  Z: {iz1} to {iz2}\n\n"
        "Generate interior commands.\n"
        "MANDATORY CHECKLIST — every item below must appear in your output:\n"
        f"  [ ] /fill {ix1} {floor_y} {iz1} {ix2} {floor_y} {iz2} <floor_block>   ← ONE fill for full floor\n"
        f"  [ ] /fill {ix1} {ceiling_y} {iz1} {ix2} {ceiling_y} {iz2} <ceil_block> ← ONE fill for full ceiling\n"
        "  [ ] At least 1 bed (/setblock ... minecraft:red_bed or similar)\n"
        "  [ ] At least 1 bookshelf or chiseled_bookshelf row\n"
        "  [ ] At least 1 lighting block (glowstone/sea_lantern/shroomlight)\n"
        "  [ ] At least 1 sofa or chair (stairs block facing inward)\n"
        "  [ ] At least 1 storage block (chest/barrel)\n"
        "  [ ] Furniture matching the building style and type"
    )

    client = get_client()
    response = client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.25,
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
