import os
import json
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """\
You are a Minecraft command generator. Given a build intent and origin coordinates, output the exact /fill and /setblock commands needed.

STRICT RULES:
- Output ONLY commands, one per line. No explanations, no numbering, no markdown.
- Every line must start with /fill or /setblock.
- /fill syntax:    /fill x1 y1 z1 x2 y2 z2 minecraft:block_name
- /setblock syntax: /setblock x y z minecraft:block_name
- All coordinates are absolute integers (no ~ or ^ notation).
- Each /fill must cover at most 32768 blocks (dx*dy*dz <= 32768). Split larger fills.
- Build order: floor → walls → roof → details.
- Walls are hollow — do NOT fill the interior.
- Leave at least one 2-block-tall door opening on one wall using air blocks.
- Use minecraft: prefix on every block name.\
"""


def get_commands(intent: dict, origin: dict) -> list[str]:
    x, y, z = origin["x"], origin["y"], origin["z"]

    user_msg = (
        f"Build intent:\n{json.dumps(intent, indent=2)}\n\n"
        f"Origin: x={x}, y={y}, z={z}\n\n"
        "Generate the Minecraft commands to build this structure starting at the origin."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    commands = [
        line.strip()
        for line in raw.splitlines()
        if line.strip().startswith("/fill") or line.strip().startswith("/setblock")
    ]
    return commands
