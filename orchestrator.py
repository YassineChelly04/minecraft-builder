import os
import json
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

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
    "roof": "minecraft:block_name",
    "accent": "minecraft:block_name"
  }
}

Rules:
- Use only valid Minecraft Java Edition block names with the minecraft: prefix.
- Keep sizes reasonable: max 50 blocks in any dimension.
- Pick materials that match the requested style.
- size.x is width (east-west), size.y is height, size.z is depth (north-south).\
"""


def get_intent(prompt: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
