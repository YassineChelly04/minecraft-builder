import json
from llm_client import get_client, get_model

SYSTEM_PROMPT = """\
You are a Minecraft build planner. Given a user's build request, extract structured intent as JSON.

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
  }
}

Rules:
- Use only valid Minecraft Java Edition block names with the minecraft: prefix.
- Keep sizes reasonable: max 50 blocks in any dimension.
- size.x = width (east-west), size.y = height, size.z = depth (north-south).\
"""


def get_intent(prompt: str) -> dict:
    client = get_client()
    response = client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_completion_tokens=2048,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
