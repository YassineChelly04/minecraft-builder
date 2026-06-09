"""
Clarify agent — the studio's intake desk.

Before a single block is placed, this agent brainstorms the request and asks the
user 2-4 high-leverage questions whose answers most change the build. This is what
lets the rest of the pipeline commit to one concrete design instead of guessing,
and it's how a small model is kept on-task: it decides *what to build* up front so
the build agents only have to execute.
"""
import json
from llm_client import complete

SYSTEM_PROMPT = """\
You are the lead architect's intake assistant at a Minecraft build studio.
Given a build request, you do two things:
  1. Brainstorm the build briefly — the architectural direction, the mood, and
     two or three pro builder / interior-designer touches that would make it shine.
  2. Ask the FEWEST clarifying questions that most change the final build.

Output ONLY valid JSON with this exact schema:
{
  "brainstorm": "2-4 sentences: the design direction and standout details you propose",
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
- Ask 2 to 4 questions, never more. Target the biggest ambiguities only:
  scale/footprint, architectural style, setting/biome, number of rooms or floors,
  signature feature, and colour palette are the usual suspects — pick what matters
  most for THIS request.
- Every question must offer concrete options the user can one-click.
- Be specific to the request; do not ask generic filler.
- Keep brainstorm and assumptions tight and concrete.\
"""


def get_clarification(prompt: str) -> dict:
    raw = complete("clarify", SYSTEM_PROMPT, f"Build request:\n{prompt}")
    data = json.loads(raw)
    # Defensive shape-normalising so the UI always gets a predictable payload.
    data.setdefault("brainstorm", "")
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
