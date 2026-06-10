"""
LLM client — single chat-completion entry point plus token accounting.

Adds two things over the original:
  1. UsageLog — every Groq call's prompt/completion tokens are accumulated into a
     thread-local log so the pipeline can report tokens-per-build and append to
     benchmarks/runs.jsonl.
  2. StubLLM — an offline stand-in (env LLM_STUB=1, or stub_mode() context) that
     returns canned JSON from tests/fixtures/, so the deterministic ~90% of the
     system runs with zero network in CI and benchmarks.

The legacy `complete(role, system, user) -> str` signature is preserved.
"""
from __future__ import annotations

import contextvars
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import config


# ── Usage accounting ─────────────────────────────────────────────────────────

@dataclass
class UsageEntry:
    role: str
    model: str
    prompt_tokens: int
    completion_tokens: int

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class UsageLog:
    entries: list[UsageEntry] = field(default_factory=list)

    def add(self, entry: UsageEntry) -> None:
        self.entries.append(entry)

    @property
    def prompt_tokens(self) -> int:
        return sum(e.prompt_tokens for e in self.entries)

    @property
    def completion_tokens(self) -> int:
        return sum(e.completion_tokens for e in self.entries)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def by_role(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.entries:
            out[e.role] = out.get(e.role, 0) + e.total
        return out

    def to_dict(self) -> dict:
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "by_role": self.by_role(),
            "calls": len(self.entries),
        }


# contextvars (not threading.local) so state propagates into pool workers that
# run inside a copied context (see pipeline._run_build_agents).
_usage_var: contextvars.ContextVar = contextvars.ContextVar("llm_usage", default=None)
_stub_var: contextvars.ContextVar = contextvars.ContextVar("llm_stub", default=False)


def _current_log() -> UsageLog | None:
    return _usage_var.get()


@contextmanager
def usage_scope():
    """Collect all LLM usage emitted inside the block into a fresh UsageLog."""
    log = UsageLog()
    token = _usage_var.set(log)
    try:
        yield log
    finally:
        _usage_var.reset(token)


# ── Stub mode (offline) ──────────────────────────────────────────────────────

_FIXTURES = Path(__file__).parent / "tests" / "fixtures"


def stub_enabled() -> bool:
    return os.environ.get("LLM_STUB") == "1" or _stub_var.get()


@contextmanager
def stub_mode(enabled: bool = True):
    token = _stub_var.set(enabled)
    try:
        yield
    finally:
        _stub_var.reset(token)


def _stub_response(role: str, system: str, user: str) -> str:
    """Return a canned response for a role. Looks for tests/fixtures/<role>.json;
    falls back to a minimal valid payload so a build never crashes offline. The
    intent stub keys off prompt keywords so offline benchmarks exercise varied
    styles/roofs deterministically (no network)."""
    fixture = _FIXTURES / f"{role}.json"
    if fixture.exists():
        return fixture.read_text(encoding="utf-8")
    if role == "intent":
        return _stub_intent(user)
    # Minimal safe defaults per role.
    defaults = {
        "clarify": json.dumps({"brief": "A cozy stub build.", "questions": []}),
        "exterior": json.dumps({"ops": []}),
        "interior": json.dumps({"ops": []}),
        "critic": json.dumps({"note": ""}),
        "city_director": json.dumps(_stub_city_director(user)),
        "district_stylist": json.dumps({"districts": []}),
        # industry/product come from the deterministic brand map; the stub only
        # needs to fill the taste fields.
        "factory_director": json.dumps({"company": "", "product": "", "era": "modern",
                                        "palette_family": "", "mood": "stub plant",
                                        "signature": []}),
    }
    return defaults.get(role, "{}")


def _stub_city_director(user: str) -> dict:
    """Keyword-aware city brief so offline runs exercise the full district mix."""
    t = user.lower()
    districts = [{"type": "heavy_industry", "share": 0.30},
                 {"type": "warehouses", "share": 0.20},
                 {"type": "housing", "share": 0.30},
                 {"type": "civic", "share": 0.10}]
    landmarks = ["clock_tower", "gasometer_park", "city_hall"]
    if any(k in t for k in ("dock", "harbor", "harbour", "port", "waterfront")):
        districts.append({"type": "docks", "share": 0.10})
        landmarks.append("harbor_crane_row")
    if any(k in t for k in ("rail", "train", "station")):
        districts.append({"type": "rail_yard", "share": 0.10})
        landmarks.append("grand_station")
    return {"era": "victorian", "palette_family": "brick_industrial",
            "districts": districts, "landmarks": landmarks[:6],
            "skyline": "stacks_dominate", "mood": "smoky riverside town"}


def _stub_intent(user: str) -> str:
    """Keyword-based intent so offline runs vary by prompt (deterministic)."""
    t = user.lower()

    def has(*kw):
        return any(k in t for k in kw)

    style, structure, palette = "medieval", "house", "medieval_castle"
    size = {"x": 11, "y": 6, "z": 9}
    rooms = ["living", "kitchen", "bedroom"]
    features: list[str] = []
    if has("modern", "villa"):
        style, structure, palette = "modern", "villa", "modern_villa"
        size = {"x": 13, "y": 8, "z": 11}
    elif has("japanese", "temple", "pagoda"):
        style, structure, palette = "japanese", "temple", "japanese_temple"
        size = {"x": 13, "y": 8, "z": 13}
    elif has("wizard", "tower", "spire"):
        style, structure, palette = "wizard", "tower", "fantasy_tower"
        size = {"x": 9, "y": 14, "z": 9}
        rooms = ["living"]
    elif has("stadium", "arena"):
        style, structure, palette = "industrial", "stadium", "brick_industrial"
        size = {"x": 90, "y": 16, "z": 70}
        rooms = []
        features = ["floodlights"]
    elif has("refinery"):
        style, structure, palette = "industrial", "refinery", "steel_and_copper"
        size = {"x": 20, "y": 12, "z": 16}
        rooms = []
    elif has("warehouse"):
        style, structure, palette = "warehouse", "warehouse", "brick_industrial"
        size = {"x": 18, "y": 8, "z": 13}
        rooms = []
    elif has("factory", "smokestack"):
        style, structure, palette = "factory", "factory", "brick_industrial"
        size = {"x": 20, "y": 9, "z": 12}
        rooms = []
        features = ["smokestack"]
    elif has("rowhouse"):
        style, structure, palette = "victorian", "rowhouse", "victorian_steam"
        size = {"x": 20, "y": 8, "z": 10}
        rooms = ["living", "kitchen", "bedroom"]
    elif has("desert", "palace", "sandstone"):
        style, structure, palette = "desert", "palace", "desert_palace"
        size = {"x": 15, "y": 8, "z": 15}
        rooms = ["living", "kitchen", "bedroom", "study"]
    elif has("ruin"):
        style, structure, palette = "ruins", "keep", "ruins"
        size = {"x": 13, "y": 7, "z": 11}
    elif has("church", "dome"):
        style, structure, palette = "church", "church", "fantasy_tower"
        size = {"x": 13, "y": 9, "z": 15}
        rooms = ["living"]
    elif has("viking", "longhouse"):
        style, structure, palette = "viking", "longhouse", "viking_longhouse"
        size = {"x": 11, "y": 7, "z": 19}
    elif has("office"):
        style, structure, palette = "modern", "office", "modern_villa"
        size = {"x": 14, "y": 12, "z": 12}
        rooms = []
    elif has("cottage", "tiny"):
        style, structure, palette = "cottage", "cottage", "cottage_core"
        size = {"x": 7, "y": 5, "z": 7}
        rooms = ["living"]
    if has("fireplace") and "fireplace" not in features:
        features.append("fireplace")
    if has("library", "bookshelf"):
        features.append("library")
    return json.dumps({
        "structure_type": structure, "size": size, "style": style,
        "palette_name": palette, "room_program": rooms, "features": features,
        "notes": "stub", "materials": {},
    })


# ── Real client ──────────────────────────────────────────────────────────────

def get_client():
    from groq import Groq
    return Groq(api_key=os.environ.get("GROQ_API_KEY"))


def get_model() -> str:
    """Back-compat: the default model used when no role override is set."""
    return config.DEFAULT_MODEL


def complete_logged(role: str, system: str, user: str) -> tuple[str, UsageEntry]:
    """Run one completion; return (text, usage). Records usage into the active
    usage_scope if one is open."""
    cfg = config.role_config(role)

    if stub_enabled():
        text = _stub_response(role, system, user)
        # Approximate tokens (chars/4) so offline runs still produce a usage table.
        entry = UsageEntry(role, "stub", len(system + user) // 4, len(text) // 4)
        log = _current_log()
        if log is not None:
            log.add(entry)
        return text, entry

    client = get_client()
    kwargs = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": cfg["temperature"],
        "max_completion_tokens": cfg["max_tokens"],
    }
    if cfg.get("json"):
        kwargs["response_format"] = {"type": "json_object"}

    last_err = None
    for attempt in range(config.MAX_RETRIES):
        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            if not content.strip():
                raise RuntimeError("empty completion (likely rate limited)")
            usage = getattr(response, "usage", None)
            entry = UsageEntry(
                role, cfg["model"],
                getattr(usage, "prompt_tokens", 0) or 0,
                getattr(usage, "completion_tokens", 0) or 0,
            )
            log = _current_log()
            if log is not None:
                log.add(entry)
            return content, entry
        except Exception as e:  # noqa: BLE001 — surface after retries exhausted
            last_err = e
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(config.RETRY_BASE_DELAY * (2 ** attempt))

    raise RuntimeError(
        f"{role} agent LLM call failed after {config.MAX_RETRIES} attempts: {last_err}")


def complete(role: str, system: str, user: str) -> str:
    """Back-compat wrapper: text only."""
    text, _ = complete_logged(role, system, user)
    return text
