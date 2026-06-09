"""
Central configuration for the multi-agent build system.

Every agent reads its model + sampling settings from here so the whole pipeline
can be tuned in one place. Each value is overridable via an environment variable,
which is the key lever for "turning tiny Groq models into performant ones": you can
point cheap roles (intent, clarify) at a small fast model and keep the heavier
geometry roles on a stronger one without touching code.
"""
import os

# Default model when a role override is unset. A small, fast, NON-reasoning model is
# the right default here: the deterministic shell + repair layer guarantee structure and
# valid blocks, so the model only needs to emit reasonable detail/furniture commands —
# exactly the "make a tiny model performant" thesis. Reasoning models (e.g. gpt-oss) burn
# completion tokens on hidden reasoning and starve the output under a tight TPM budget.
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "llama-3.1-8b-instant")


# Stronger non-reasoning model for the spatial build roles; tiny model for the rest.
BUILD_MODEL = os.environ.get("LLM_MODEL_BUILD", "llama-3.3-70b-versatile")


def _model(role_env: str, default: str = DEFAULT_MODEL) -> str:
    return os.environ.get(role_env, default)


# Per-role model + sampling. Lower temperature = more deterministic (better for
# command syntax); higher = more creative (better for brainstorming).
# max_tokens are sized to fit a free-tier ~8000 TPM budget across one build
# (intent → exterior ‖ interior). Raise them if you're on a paid tier.
ROLES = {
    "intent":   {"model": _model("LLM_MODEL_INTENT"),               "temperature": 0.3,  "max_tokens": 1024,  "json": True},
    "clarify":  {"model": _model("LLM_MODEL_CLARIFY"),              "temperature": 0.6,  "max_tokens": 1280,  "json": True},
    "exterior": {"model": _model("LLM_MODEL_EXTERIOR", BUILD_MODEL), "temperature": 0.2,  "max_tokens": 2048,  "json": False},
    "interior": {"model": _model("LLM_MODEL_INTERIOR", BUILD_MODEL), "temperature": 0.3,  "max_tokens": 2560,  "json": False},
    "critic":   {"model": _model("LLM_MODEL_CRITIC"),               "temperature": 0.1,  "max_tokens": 1280,  "json": True},
}

# Network resilience for flaky/free-tier endpoints (rate limits reset per minute).
MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "4"))
RETRY_BASE_DELAY = float(os.environ.get("LLM_RETRY_DELAY", "2.0"))

# Minecraft engine limits (Java Edition 1.21.x).
MAX_FILL_VOLUME = 32768
WORLD_MIN_Y = -64
WORLD_MAX_Y = 319


def role_config(role: str) -> dict:
    if role not in ROLES:
        raise KeyError(f"Unknown agent role '{role}'. Known: {list(ROLES)}")
    return ROLES[role]
