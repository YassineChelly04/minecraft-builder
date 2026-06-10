"""
Clarify agent — the studio's intake desk.

Before a single block is placed, this agent brainstorms the request and asks the
user 2-4 high-leverage questions whose answers most change the build. This is what
lets the rest of the pipeline commit to one concrete design instead of guessing,
and it's how a small model is kept on-task: it decides *what to build* up front so
the build agents only have to execute.

Anti-sameness: every call draws two random "creative lenses" from a curated list
and injects them into the prompt, so the same request brainstormed twice produces
genuinely different concepts (the role also runs at high temperature). Every
question must map to a build lever the engine actually has (palette, storeys,
size, signature feature) so a ticked answer is guaranteed to change the output —
the deterministic overlay in architecture/brief.py enforces it.
"""
import json
import random

from llm_client import complete

# Lenses are concrete, buildable directions — not vague moods. Two get sampled
# per call so consecutive brainstorms of the same prompt diverge.
CREATIVE_LENSES = [
    "dramatic silhouette: push one element far taller or wider than expected",
    "weathered and lived-in: visible age, moss/cracks, mismatched repairs",
    "two-material color blocking: one bold accent material used decisively",
    "vertical drama: towers, chimneys or masts that change the skyline",
    "asymmetry: off-center entrance, unequal wings, a leaning annex",
    "glow at night: where the light sources become the design feature",
    "a signature 'wow' moment: one feature a visitor would screenshot",
    "framing the approach: gates, paths or arches that stage the entrance",
    "industrial honesty: exposed structure, pipes, gantries as ornament",
    "soft landscaping: gardens, water or trees pressed up against the build",
    "interior reveal: one big window/opening exposing the best interior",
    "rooftop life: terraces, dormers, vents, skylights that animate the roof",
]

SYSTEM_PROMPT = """\
You are the lead architect's intake assistant at a Minecraft build studio.
Given a build request, you do two things:
  1. Brainstorm ONE bold, specific concept — give it a short evocative NAME and
     describe the architectural direction, the mood, and two or three concrete
     pro-builder touches (real materials, shapes, placements — not adjectives).
     Make it opinionated: a design someone could veto, not a safe summary.
  2. Ask the FEWEST clarifying questions that most change the final build.

Output ONLY valid JSON with this exact schema:
{
  "concept_name": "2-4 word name for the design concept",
  "brainstorm": "3-5 sentences: the concrete design direction and standout details",
  "assumptions": ["sensible defaults you'll use if the user doesn't answer"],
  "questions": [
    {
      "id": "short_snake_case_id",
      "question": "the question text",
      "options": ["2-4 concrete answer choices"],
      "allow_custom": true
    }
  ]
}

Rules:
- Ask 2 to 4 questions, never more. Each question must target a lever that
  visibly changes the build: material palette / colour, scale or storey count,
  the signature feature, the roof or silhouette, or the setting.
- Every option must be CONCRETE and distinct (e.g. "weathered copper + deepslate"
  not "metallic"); at least one option per question should be daring.
- No generic filler questions; be specific to THIS request.
- Keep brainstorm and assumptions tight, concrete and buildable.\
"""


def get_clarification(prompt: str) -> dict:
    lenses = random.sample(CREATIVE_LENSES, 2)
    user = (f"Build request:\n{prompt}\n\n"
            f"Creative lenses to colour this concept (commit to them):\n"
            f"- {lenses[0]}\n- {lenses[1]}")
    raw = complete("clarify", SYSTEM_PROMPT, user)
    data = json.loads(raw)
    # Defensive shape-normalising so the UI always gets a predictable payload.
    data.setdefault("brainstorm", "")
    if data.get("concept_name"):
        data["brainstorm"] = f"“{data['concept_name']}” — {data['brainstorm']}"
    data.setdefault("assumptions", [])
    questions = data.get("questions") or []
    data["questions"] = [
        {
            "id": q.get("id") or f"q{i}",
            "question": q.get("question", ""),
            "options": q.get("options") or [],
            "allow_custom": q.get("allow_custom", True),
        }
        for i, q in enumerate(questions)
        if q.get("question")
    ][:4]
    return data
