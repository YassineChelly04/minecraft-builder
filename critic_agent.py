"""
Critic agent — the second-pass reviewer.

After the exterior and interior agents build, the critic inspects the whole command
set against the intent and reports what's strong and what's missing. Where a mandatory
element is absent (a door opening, a light, a bed, seating, storage), it emits a small
number of additive patch commands at pre-computed safe anchor points — so it never has
to do spatial math, the thing small models are worst at. Every command it produces still
flows through the repair layer, so the critic can only ever improve a build, never break it.
"""
import json
from llm_client import complete

SYSTEM_PROMPT = """\
You are a senior Minecraft build reviewer. You are given a build's intent, the safe
anchor coordinates inside the structure, and the full list of commands already generated.

Judge the build, then PATCH only what is missing. Output ONLY valid JSON:
{
  "review": "2-3 sentences: what works, what is missing or weak",
  "score": 0-100,
  "additions": ["extra /fill or /setblock commands that fix gaps — may be empty"]
}

Rules for "additions":
- Add ONLY for genuinely missing MANDATORY elements: a door opening (air) on the front
  wall, at least one interior light, a bed, a seat, a storage block, a window if there are none.
- Use ONLY the anchor coordinates provided. Do not invent coordinates or do arithmetic.
- Use only valid Minecraft Java Edition block names with the minecraft: prefix.
- If the build already covers the essentials, return "additions": [].
- Never duplicate something already present. Keep additions minimal (typically 0-6 commands).\
"""


def review_build(intent: dict, anchors: dict, commands: list[str]) -> dict:
    user = (
        f"Intent:\n{json.dumps(intent, indent=2)}\n\n"
        f"Safe anchor coordinates (use these exact points):\n{json.dumps(anchors, indent=2)}\n\n"
        f"Commands generated so far ({len(commands)}):\n" + "\n".join(commands)
    )
    try:
        raw = complete("critic", SYSTEM_PROMPT, user)
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001 — critique is best-effort, never fatal
        return {"review": f"(critic skipped: {e})", "score": None, "additions": []}

    additions = data.get("additions") or []
    additions = [c.strip() for c in additions if isinstance(c, str) and c.strip().startswith("/")]
    return {
        "review": data.get("review", ""),
        "score": data.get("score"),
        "additions": additions,
    }
