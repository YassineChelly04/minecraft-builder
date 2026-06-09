"""
Build pipeline — the conductor that turns a prompt into runnable Minecraft commands.

Kept separate from the Flask layer (app.py) so the whole multi-agent flow is
importable and testable on its own:

    intent → [exterior ‖ interior] → normalize → merge → repair → air-clear → critic → repair

Each stage is a single-responsibility module, so new agents or post-processors slot
in here without touching the web layer.
"""
import contextvars
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from llm_client import usage_scope
from orchestrator import get_intent
from critic_agent import review_build
from exterior_agent import get_exterior_commands
from interior_agent import get_interior_commands
from shell import build_shell
from normalizer import normalize_commands, merge_fills
from repair import repair_commands
from validator import validate_commands


class PipelineError(Exception):
    """Raised when a build cannot be produced; carries a user-facing message."""


def _dims(intent: dict, origin: dict):
    x, y, z = origin["x"], origin["y"], origin["z"]
    sx = intent.get("size", {}).get("x", 10)
    sy = intent.get("size", {}).get("y", 6)
    sz = intent.get("size", {}).get("z", 10)
    return x, y, z, sx, sy, sz


def anchors(intent: dict, origin: dict) -> dict:
    """Pre-computed safe interior coordinates so the critic never has to do math."""
    x, y, z, sx, sy, sz = _dims(intent, origin)
    ix1, iz1 = x + 1, z + 1
    ix2, iz2 = x + sx - 2, z + sz - 2
    cx, cz = (ix1 + ix2) // 2, (iz1 + iz2) // 2
    floor_y, ceiling_y = y + 1, y + sy - 1
    return {
        "interior_center_floor": [cx, floor_y, cz],
        "interior_corner_floor": [ix1, floor_y, iz1],
        "front_door_floor": [cx, floor_y, z],          # in the front (north) wall
        "ceiling_center": [cx, ceiling_y, cz],
        "wall_sconce": [ix1, floor_y + 2, iz1],
    }


def _strip_air(commands: list[str]) -> list[str]:
    """Only the deterministic shell may place air. This prevents an LLM detail/furnish
    pass from ever punching holes in the watertight envelope."""
    kept = []
    for cmd in commands:
        p = cmd.split()
        block = (p[7] if p[0] == "/fill" and len(p) > 7
                 else p[4] if p[0] == "/setblock" and len(p) > 4 else "")
        if block.split("[")[0] == "minecraft:air":
            continue
        kept.append(cmd)
    return kept


def _run_build_agents(intent: dict, origin: dict) -> tuple[list[str], list[str]]:
    """Run exterior + interior agents in parallel; raise PipelineError if either fails."""
    exterior_cmds, interior_cmds = [], []
    errors_by_agent = {}

    # Copy the current context (stub flag + usage log) into the worker threads so
    # offline/stub runs and token accounting work across the thread boundary.
    ctx_ext = contextvars.copy_context()
    ctx_int = contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_ext = pool.submit(ctx_ext.run, get_exterior_commands, intent, origin)
        future_int = pool.submit(ctx_int.run, get_interior_commands, intent, origin)
        for future in as_completed([future_ext, future_int]):
            label = "Exterior" if future is future_ext else "Interior"
            try:
                result = future.result()
                if future is future_ext:
                    exterior_cmds = result
                else:
                    interior_cmds = result
            except Exception as e:  # noqa: BLE001 — re-raised as PipelineError below
                errors_by_agent[label] = str(e)

    if errors_by_agent:
        raise PipelineError(" | ".join(f"{k} agent failed: {v}" for k, v in errors_by_agent.items()))
    return exterior_cmds, interior_cmds


def _clean(commands: list[str]) -> tuple[list[str], list[str]]:
    """normalize → merge → repair: every returned command is guaranteed engine-valid."""
    return repair_commands(merge_fills(normalize_commands(commands)))


def build_structure(prompt: str, origin: dict, answers: dict | None = None,
                    brief: str | None = None, refine: bool = True,
                    mode: str | None = None) -> dict:
    """Full prompt-to-commands build. Returns the payload the web/UI layer serves,
    including a per-build `usage` token breakdown. `mode` selects legacy (original
    freeform path) or dsl (Shell 2.0); defaults to config.PIPELINE_MODE."""
    mode = (mode or config.PIPELINE_MODE).lower()
    with usage_scope() as usage:
        if mode == "dsl":
            result = _build_dsl(prompt, origin, answers, brief, refine)
        else:
            result = _build_structure(prompt, origin, answers, brief, refine)
    result["usage"] = usage.to_dict()
    return result


def _clean_ordered(commands: list[str]) -> tuple[list[str], list[str]]:
    """normalize -> repair WITHOUT merge_fills. The DSL/shell layer carves air
    (door/window openings) after solid fills; merge_fills globally reorders all
    fills ahead of setblocks, which would re-block those openings. Order must be
    preserved here, so we skip the merge optimisation on this path."""
    return repair_commands(normalize_commands(commands))


def _build_dsl(prompt: str, origin: dict, answers: dict | None,
               brief: str | None, refine: bool) -> dict:
    """Shell 2.0 deterministic path. Placers + DSL agents arrive in Phase D; for
    now this furnishes the watertight, recessed-window, real-roof envelope in kit
    mode (zero LLM beyond intent)."""
    from architecture.brief import intent_to_brief
    from architecture.shell2 import build_shell2

    try:
        intent = get_intent(prompt, answers=answers or {}, brief=brief)
    except Exception as e:  # noqa: BLE001
        raise PipelineError(f"Orchestrator failed: {e}")

    building = intent_to_brief(intent, origin, prompt=prompt, detail_level="kit")
    raw, geometry = build_shell2(building)
    commands, report = _clean_ordered(raw)
    if not commands:
        raise PipelineError("Build produced no commands")

    valid, errors = validate_commands(commands)
    return {
        "intent": intent,
        "mode": "dsl",
        "exterior_commands": commands,
        "interior_commands": [],
        "commands": commands,
        "geometry": geometry,
        "valid": valid,
        "errors": errors,
        "repairs": report,
        "review": "",
        "score": None,
    }


def _build_structure(prompt: str, origin: dict, answers: dict | None = None,
                     brief: str | None = None, refine: bool = True) -> dict:
    try:
        intent = get_intent(prompt, answers=answers or {}, brief=brief)
    except Exception as e:  # noqa: BLE001
        raise PipelineError(f"Orchestrator failed: {e}")

    # Deterministic, always-complete envelope: floor + 4 walls + roof + door + windows.
    shell_cmds, shell_report = _clean(build_shell(intent, origin))

    # LLM passes only DECORATE (facade) and FURNISH (interior); air stripped so they
    # can never breach the shell.
    exterior_raw, interior_raw = _run_build_agents(intent, origin)
    ext_detail, ext_report = _clean(_strip_air(exterior_raw))
    interior_cmds, int_report = _clean(_strip_air(interior_raw))

    exterior_cmds = shell_cmds + ext_detail
    all_commands = exterior_cmds + interior_cmds
    if not all_commands:
        raise PipelineError("Build produced no commands")

    critique = {"review": "", "score": None, "additions": []}
    if refine:
        # The shell guarantees the exterior; the critic focuses on furnishing completeness.
        critique = review_build(intent, anchors(intent, origin), interior_cmds)
        if critique["additions"]:
            patches, _ = repair_commands(_strip_air(normalize_commands(critique["additions"])))
            interior_cmds = interior_cmds + patches
            all_commands = exterior_cmds + interior_cmds

    valid, errors = validate_commands(all_commands)
    return {
        "intent": intent,
        "exterior_commands": exterior_cmds,
        "interior_commands": interior_cmds,
        "commands": all_commands,
        "valid": valid,
        "errors": errors,
        "repairs": shell_report + ext_report + int_report,
        "review": critique["review"],
        "score": critique["score"],
    }
