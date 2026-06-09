"""
Interior DSL agent — the LLM picks furniture op NAMES from a per-room menu; Python
places them. The model never writes a coordinate or a block id (assert in tests).
Parse failures fall back to the room's kit defaults, so a build never breaks.
"""
from __future__ import annotations

import json

from architecture.geometry import BuildingGeometry
from knowledge.room_kits import kit_for
from knowledge.style_cards import style_card
from llm_client import complete
from placers.base import match_op
from placers.furniture import FURNITURE_OPS

_SYSTEM = "You are a Minecraft interior designer."

_PROMPT = """\
Room: {room} ({w}x{d}). Style: {style}. Palette: {palette}.
{card}
Must include: {must}. Keep doorways clear.
Pick 4-7 ops from this menu (names only): {menu}
Rules:
1) JSON only, shape {{"ops":[{{"op":"<name>"}}, ...]}}.
2) Ops from the menu only.
3) No coordinates, no block ids, no prose.
Example: {{"ops":[{{"op":"sofa"}},{{"op":"bookshelf_wall"}},{{"op":"rug"}}]}}
JSON only. No prose."""


def parse_ops(raw: str, menu: list[str]) -> list[str]:
    """Extract op names, fuzzy-match to the menu, drop anything unknown. This is
    what makes an LLM hallucination harmless: only known op NAMES survive."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    items = data.get("ops", data) if isinstance(data, dict) else data
    out: list[str] = []
    menu_set = {m: m for m in menu}
    for it in items if isinstance(items, list) else []:
        name = it.get("op") if isinstance(it, dict) else it
        m = match_op(str(name), {**FURNITURE_OPS, **menu_set})
        if m and m in FURNITURE_OPS and m not in out:
            out.append(m)
    return out


def get_interior_ops(geometry: BuildingGeometry, brief) -> dict[str, list[str]]:
    """One call per furnishable zone; returns {zone_name: [op,...]}. Empty list
    for a zone means "use the kit default" (handled by furnish_zone)."""
    out: dict[str, list[str]] = {}
    for zone in geometry.zones:
        kit = kit_for(zone.name)
        menu = kit.get("menu", [])
        inner = zone.rect.inset(1)
        prompt = _PROMPT.format(
            room=zone.name, w=inner.width, d=inner.depth, style=brief.style,
            palette=brief.palette.name, card=style_card(brief.style),
            must=", ".join(kit.get("must", [])) or "none",
            menu=", ".join(menu),
        )
        try:
            raw = complete("interior", _SYSTEM, prompt)
            ops = parse_ops(raw, menu)
        except Exception:  # noqa: BLE001 — never fail a build on the agent
            ops = []
        out[zone.name] = ops
    return out
