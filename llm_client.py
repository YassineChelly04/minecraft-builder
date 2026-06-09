import os
import time

from groq import Groq

import config


def get_client() -> Groq:
    return Groq(api_key=os.environ.get("GROQ_API_KEY"))


def get_model() -> str:
    """Back-compat: the default model used when no role override is set."""
    return config.DEFAULT_MODEL


def complete(role: str, system: str, user: str) -> str:
    """
    Run a single chat completion for the given agent role.

    Model, temperature, max_tokens and JSON mode all come from config.ROLES[role],
    so call sites stay declarative. Retries transient failures with exponential
    backoff so a flaky free-tier endpoint doesn't break a whole build.
    """
    cfg = config.role_config(role)
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
                # A rate-limited endpoint can return an empty 200; retry rather than
                # silently yielding zero commands.
                raise RuntimeError("empty completion (likely rate limited)")
            return content
        except Exception as e:  # noqa: BLE001 — surface after retries exhausted
            last_err = e
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(config.RETRY_BASE_DELAY * (2 ** attempt))

    raise RuntimeError(f"{role} agent LLM call failed after {config.MAX_RETRIES} attempts: {last_err}")
