"""
Manufacturer orchestration. build_factory(prompt, origin, answers) runs:
  director (1 LLM call, brand-mapped) -> planner (deterministic value-stream
  layout) -> per-stage archetype generation (0 tokens) -> siteworks -> QA.

Same contract as city_pipeline: every returned command is normalize->repair
clean, grouped for the datapack writer, with a usage/QA report for the UI.
"""
from __future__ import annotations

import hashlib

from agents.factory_director import get_factory_brief
from architecture.archetypes import build_archetype
from architecture.brief import BuildingBrief
from factory.connectivity import build_siteworks
from factory.planner import plan_factory
from factory.qa import score_factory
from execution.datapack import write_datapack
from knowledge.palettes import PALETTES, PALETTE_FAMILIES
from llm_client import usage_scope
from normalizer import normalize_commands
from repair import repair_commands

# white-skinned stages keep their clean look regardless of the site palette
_CLEAN_ARCHETYPES = {"clean_hall", "cleanroom_fab", "paint_shop"}


def _seed(prompt: str, origin: dict, variation: int = 0) -> int:
    key = f"{prompt}|{origin.get('x',0)},{origin.get('y',0)},{origin.get('z',0)}|{variation}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)


def _stage_seed(master: int, rect) -> int:
    h = hashlib.sha256(f"{master}|{rect.x1},{rect.z1},{rect.x2},{rect.z2}".encode()).hexdigest()
    return int(h[:16], 16)


def _clean(cmds: list[str]) -> list[str]:
    clean, _ = repair_commands(normalize_commands(cmds))
    return clean


def _palette(family: str):
    fam = PALETTE_FAMILIES.get(family)
    return PALETTES.get(fam["base"] if fam else "brick_industrial",
                        PALETTES["brick_industrial"])


def _white_variant(pal):
    from knowledge.palettes import BuildingPalette
    return BuildingPalette(**{**pal.__dict__, "name": pal.name + "_clean",
                              "dominant": "white_concrete",
                              "trim": "light_gray_concrete", "wear": ()})


def build_factory(prompt: str, origin: dict, answers: dict | None = None,
                  out_dir=None, variation: int = 0) -> dict:
    answers = answers or {}
    seed = _seed(prompt, origin, variation)
    with usage_scope() as usage:
        fbrief = get_factory_brief(prompt, answers)
        plan = plan_factory(fbrief, origin, seed=seed)
        palette = _palette(fbrief.palette_family)
        white = _white_variant(palette)

        groups: dict[str, list[str]] = {}
        for s in plan.stages:
            pal = white if s.archetype in _CLEAN_ARCHETYPES else palette
            brief = BuildingBrief(
                archetype=s.archetype, lot=s.rect, origin_y=plan.ground_y,
                style=fbrief.era, palette=pal,
                storeys=max(1, s.height_band[1] // 5), height_band=s.height_band,
                room_program=[], features=[], front_face="S",
                seed=_stage_seed(seed, s.rect), detail_level="kit",
            )
            raw, _geom = build_archetype(brief)
            order = f"{s.order:02d}" if s.role == "process" else "90"
            groups.setdefault(f"40_{order}_{s.stage}", []).extend(raw)

        for key in list(groups):
            groups[key] = _clean(groups[key])

        site = build_siteworks(plan, palette, seed)
        for k, v in site.items():
            groups[k] = _clean(v)

    commands = [c for k in sorted(groups) for c in groups[k]]
    qa = score_factory(plan)

    manifest = None
    if out_dir is not None:
        manifest = write_datapack(groups, out_dir, build_id="factory").to_dict()

    return {
        "plan": plan,
        "plan_summary": {
            "company": fbrief.company, "industry": fbrief.industry,
            "product": fbrief.product, "era": fbrief.era,
            "size_class": fbrief.size_class, "mood": fbrief.mood,
            "stages": [s.stage for s in plan.process_stages()],
            "support": [s.stage for s in plan.stages if s.role != "process"],
            "rail": bool(plan.rail), "signature": fbrief.signature,
        },
        "commands": commands,
        "command_count": len(commands),
        "usage": usage.to_dict(),
        "qa": qa.to_dict(),
        "manifest": manifest,
    }
