"""
City orchestration. build_city(prompt, origin, answers, mode) runs:
  director (1 call) -> planner (deterministic) -> stylist (1 call) -> briefs ->
  per-building generation (kit = 0 tokens) -> connectivity -> QA.

Token budget guard (CITY_TOKEN_BUDGET): if exceeded mid-run, remaining landmark
briefs downgrade to kit.
"""
from __future__ import annotations

import hashlib

import config
from agents.city_director import get_city_brief
from agents.district_stylist import get_district_styles
from architecture.archetypes import build_archetype
from city.briefs import make_briefs
from city.connectivity import build_connectivity
from city.planner import plan_city
from city.qa import score_city
from execution.datapack import write_datapack
from knowledge.palettes import PALETTES, PALETTE_FAMILIES
from llm_client import usage_scope
from normalizer import normalize_commands
from repair import repair_commands


def _seed(prompt: str, origin: dict) -> int:
    key = f"{prompt}|{origin.get('x',0)},{origin.get('y',0)},{origin.get('z',0)}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)


def _clean(cmds: list[str]) -> list[str]:
    clean, _ = repair_commands(normalize_commands(cmds))
    return clean


def build_city(prompt: str, origin: dict, answers: dict | None = None,
               mode: str = "datapack", out_dir=None) -> dict:
    answers = answers or {}
    seed = _seed(prompt, origin)
    with usage_scope() as usage:
        city_brief = get_city_brief(prompt, answers)
        plan = plan_city(city_brief, origin, seed=seed)
        styles = get_district_styles(city_brief)
        briefs = make_briefs(plan, city_brief, styles, seed)

        fam = PALETTE_FAMILIES.get(city_brief.palette_family)
        palette = PALETTES.get(fam["base"] if fam else "brick_industrial",
                               PALETTES["brick_industrial"])

        # per-building generation, grouped by district kind for the datapack
        groups: dict[str, list[str]] = {}
        for brief in briefs:
            # token guard: downgrade remaining llm briefs once over budget
            if brief.detail_level == "llm" and usage.total_tokens > config.CITY_TOKEN_BUDGET:
                brief.detail_level = "kit"
            raw, _geom = build_archetype(brief)
            key = f"40_{brief.archetype}"
            groups.setdefault(key, []).extend(raw)

        for key in list(groups):
            groups[key] = _clean(groups[key])

        conn = build_connectivity(plan, palette, seed)
        for k, v in conn.items():
            groups[k] = _clean(v)

    commands = [c for k in sorted(groups) for c in groups[k]]
    qa = score_city(plan, commands)

    manifest = None
    if out_dir is not None:
        manifest = write_datapack(groups, out_dir, build_id="city").to_dict()

    return {
        "plan": plan,
        "plan_summary": {
            "size_class": city_brief.size_class, "era": city_brief.era,
            "districts": [d.kind for d in plan.districts],
            "lots": len(plan.all_lots()), "buildings": len(briefs),
            "landmarks": city_brief.landmarks, "waterfront": city_brief.waterfront,
        },
        "commands": commands,
        "command_count": len(commands),
        "usage": usage.to_dict(),
        "qa": qa.to_dict(),
        "manifest": manifest,
    }
