import json
from llm_client import complete

SYSTEM_PROMPT = """\
You are a Minecraft build planner. Given a user's build request (plus any design
decisions they made), extract structured intent as JSON.

Output ONLY valid JSON with this exact schema:
{
  "structure_type": "string (e.g. warehouse, house, tower, wall, bridge)",
  "size": {"x": int, "y": int, "z": int},
  "style": "string (e.g. modern, medieval, industrial, fantasy)",
  "materials": {
    "walls": "minecraft:block_name",
    "floor": "minecraft:block_name",
    "roof":  "minecraft:block_name",
    "accent":"minecraft:block_name"
  },
  "features": ["short strings — special elements the user asked for"],
  "notes": "string — one-line summary of the design direction for the build agents"
}

Rules:
- Use only valid Minecraft Java Edition block names with the minecraft: prefix.
- Keep sizes reasonable: max 50 blocks in any dimension.
- size.x = width (east-west), size.y = height, size.z = depth (north-south).
- Honour every explicit design decision the user provided.\
"""


def get_intent(prompt: str, answers: dict | None = None, brief: str | None = None) -> dict:
    """Extract structured intent, folding in clarifying answers and the brainstorm brief."""
    user = f"Build request:\n{prompt}\n"
    if answers:
        decisions = "\n".join(f"- {q}: {a}" for q, a in answers.items() if a)
        if decisions:
            user += f"\nDesign decisions made by the user:\n{decisions}\n"
    if brief:
        user += f"\nDesign brief (brainstorm) to honour:\n{brief}\n"

    raw = complete("intent", SYSTEM_PROMPT, user)
    return json.loads(raw)
