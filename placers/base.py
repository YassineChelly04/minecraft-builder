"""
Placer foundation — result type, op registry, and fuzzy op matching (reuses the
repair.py Levenshtein machinery so an LLM typo like "lanterns" resolves to
"lantern_pair").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import Callable


@dataclass
class PlacerResult:
    cmds: list[str] = field(default_factory=list)
    claimed: set[tuple[int, int]] = field(default_factory=set)
    ok: bool = True
    reason: str = ""


OpFn = Callable[..., PlacerResult]


def match_op(name: str, registry: dict) -> str | None:
    """Exact -> fuzzy -> None against the keys of an op registry."""
    if not name:
        return None
    name = str(name).strip().lower().replace(" ", "_")
    if name in registry:
        return name
    m = get_close_matches(name, list(registry.keys()), n=1, cutoff=0.8)
    return m[0] if m else None


def menu_for(registry: dict, valid_styles: set[str] | None = None) -> list[str]:
    """Subset a registry to ops valid for the given styles (None = all)."""
    if valid_styles is None:
        return list(registry.keys())
    out = []
    for name, spec in registry.items():
        ok = spec.get("valid_styles") if isinstance(spec, dict) else None
        if ok is None or valid_styles & set(ok):
            out.append(name)
    return out
