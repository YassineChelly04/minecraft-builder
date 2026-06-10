"""
Factory director — ONE LLM call returning a FactoryBrief. The deterministic
brand/keyword map in factory.industries decides the industry FIRST (so "a Ford
plant" can never come back as a bakery); the LLM only adds taste: product detail,
era, mood, signature elements. Validated/defaulted so it NEVER fails the build.
"""
from __future__ import annotations

import json

from factory.industries import INDUSTRIES, match_industry
from factory.model import FactoryBrief
from llm_client import complete

_SYSTEM = "You are an industrial architect planning a manufacturer's plant in Minecraft."

_PROMPT = """\
Plan a manufacturing site for: {prompt}
{decisions}The industry template is already fixed: {industry} ({label}).
Return JSON only:
{{"company":"display name or empty",
 "product":"specific product this plant makes",
 "era":"victorian|interwar|modern|dieselpunk",
 "palette_family":"brick_industrial|steel_and_copper|gritty_deepslate",
 "mood":"<max 8 words>",
 "signature":["1-3 short site-specific touches, e.g. 'test track loop'"]}}
JSON only. No prose."""

_ERAS = ("victorian", "interwar", "modern", "dieselpunk")
_FAMILIES = ("brick_industrial", "steel_and_copper", "gritty_deepslate")


def get_factory_brief(prompt: str, answers: dict | None) -> FactoryBrief:
    answers = answers or {}
    matched = match_industry(prompt + " " + " ".join(str(v) for v in answers.values()))
    company, industry, product = matched if matched else ("", "generic",
                                                          INDUSTRIES["generic"].product)
    template = INDUSTRIES[industry]

    decisions = "\n".join(f"- {q}: {a}" for q, a in answers.items() if a)
    decisions = f"User decisions (HONOUR them):\n{decisions}\n" if decisions else ""
    try:
        raw = complete("factory_director", _SYSTEM,
                       _PROMPT.format(prompt=prompt, decisions=decisions,
                                      industry=industry, label=template.label))
        data = json.loads(raw)
    except Exception:  # noqa: BLE001 — never fail the build
        data = {}

    # deterministic answer overrides (same guarantee as the city director)
    text = " ".join(str(v) for v in answers.values() if v).lower()
    era = next((e for e in _ERAS if e in text), None) or data.get("era") or template.era
    if any(w in text for w in ("copper", "steel", "metal")):
        family = "steel_and_copper"
    elif any(w in text for w in ("deepslate", "dark", "gritty")):
        family = "gritty_deepslate"
    elif "brick" in text:
        family = "brick_industrial"
    else:
        family = data.get("palette_family") or template.palette_family

    size = str(answers.get("size", "M")).upper()
    return FactoryBrief(
        company=str(data.get("company") or company or "").strip()[:40],
        industry=industry,
        product=str(data.get("product") or product)[:60],
        era=era if era in _ERAS else "modern",
        palette_family=family if family in _FAMILIES else template.palette_family,
        size_class=size if size in ("S", "M", "L") else "M",
        mood=str(data.get("mood", ""))[:60],
        signature=[str(s)[:40] for s in (data.get("signature") or [])][:3],
    )
