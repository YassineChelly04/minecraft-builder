"""
Deterministic critic + furnishing — replaces the LLM critic's core with a voxel
checklist and placer-library auto-patches (always valid).

Pipeline (dsl): furnish each zone (kit defaults or LLM-picked ops) -> auto_light
(guarantee light ≥ 8) -> patch missing must-include features. The optional 8b
"architect's note" lives in agents/critic_agent.py and only runs when refine=True.
"""
from __future__ import annotations

import random

from architecture.brief import BuildingBrief
from architecture.geometry import BuildingGeometry, Zone
from knowledge.room_kits import FOCAL_RESOLUTION, kit_for
from placers.base import match_op
from placers.furniture import FURNITURE_OPS
from placers.lighting import auto_light


def furnish_zone(zone: Zone, ops: list[str] | None, palette, rng: random.Random,
                 version: str) -> tuple[list[str], list[str]]:
    """Run an op list (LLM picks or kit defaults) against the zone occupancy grid.
    Must-include focal ops run first. Returns (cmds, report)."""
    kit = kit_for(zone.name)
    must = [FOCAL_RESOLUTION.get(m, m) for m in kit.get("must", [])]
    chosen = list(must) + list(ops if ops else kit.get("default", []))

    cmds: list[str] = []
    report: list[str] = []
    seen: set[str] = set()
    for raw in chosen:
        name = match_op(raw, FURNITURE_OPS)
        if not name or name in seen:
            continue
        seen.add(name)
        res = FURNITURE_OPS[name](zone, rng=rng, palette=palette, version=version)
        if res.ok:
            cmds += res.cmds
        else:
            report.append(f"{zone.name}: {name} skipped ({res.reason})")
    return cmds, report


def furnish_building(geometry: BuildingGeometry, brief: BuildingBrief,
                     ops_by_zone: dict[str, list[str]] | None = None
                     ) -> tuple[list[str], list[str]]:
    rng = random.Random(brief.seed ^ 0xF00D)
    version = "1.21.9"
    cmds: list[str] = []
    report: list[str] = []
    for zone in geometry.zones:
        ops = (ops_by_zone or {}).get(zone.name)
        zc, zr = furnish_zone(zone, ops, brief.palette, rng, version)
        cmds += zc
        report += zr
    return cmds, report


def critic_patch(commands: list[str], geometry: BuildingGeometry, brief: BuildingBrief
                 ) -> tuple[list[str], list[str]]:
    """Deterministic auto-patch: always run auto_light; ensure requested features
    have a placer-built presence. Returns (extra_cmds, report)."""
    report: list[str] = []
    extra: list[str] = []

    light = auto_light(commands, geometry, brief.palette)
    if light.cmds:
        extra += light.cmds
        report.append(f"auto_light added {len(light.cmds)} fixtures")

    # missing must-include / requested features -> place via the placer library
    feats = {f.lower() for f in brief.features}
    if any("fireplace" in f or "hearth" in f for f in feats) and geometry.zones:
        rng = random.Random(brief.seed ^ 0xBEEF)
        from placers.furniture import fireplace
        res = fireplace(geometry.zones[0], rng=rng, palette=brief.palette)
        if res.ok:
            extra += res.cmds
            report.append("patched feature: fireplace")
    return extra, report
