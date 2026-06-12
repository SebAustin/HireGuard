"""AI/ML API client — the load-bearing reasoning backend for @RiskScorer.

A finding has no risk score until a call through this module returns. Pinned to the
OpenAI-compatible AI/ML API surface (https://api.aimlapi.com/v1). Model id format is
``<vendor>/<model>`` (e.g. ``openai/gpt-4.1``, ``deepseek/deepseek-r1``).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from openai import OpenAI

AIML_BASE_URL = os.environ.get("AIML_BASE_URL", "https://api.aimlapi.com/v1")
AIML_MODEL = os.environ.get("AIML_MODEL", "openai/gpt-4.1")

# Demo reproducibility: cache responses keyed by prompt hash so the recorded
# run is deterministic and immune to rate limits / model-id drift mid-demo.
_CACHE_DIR = Path(os.environ.get("HIREGUARD_CACHE_DIR", ".cache/aiml"))


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    api_key = os.environ.get("AIML_API_KEY")
    if not api_key:
        raise RuntimeError(
            "AIML_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    return OpenAI(base_url=AIML_BASE_URL, api_key=api_key)


def _cache_path(key: str) -> Path:
    import hashlib

    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return _CACHE_DIR / f"{digest}.json"


def score(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    use_cache: bool = True,
    temperature: float = 0.2,
) -> str:
    """Run one reasoning call through the AI/ML API and return the text content.

    When ``use_cache`` is True (default), responses are cached on disk keyed by
    (model, system, user) so the demo recording is reproducible.
    """
    model = model or AIML_MODEL
    cache_key = f"{model}\x00{system_prompt}\x00{user_prompt}"
    cache_file = _cache_path(cache_key)

    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text())["content"]

    resp = _client().chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = resp.choices[0].message.content or ""

    if use_cache:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"model": model, "content": content}))

    return content


def ping(model: str | None = None) -> str:
    """Phase-0 proof-of-life. Returns the model's reply to 'ping'."""
    return score(
        system_prompt="You are a health check.",
        user_prompt="ping",
        model=model,
        use_cache=False,
    )


def health() -> dict[str, Any]:
    """Non-raising status used by run_demo --check."""
    info: dict[str, Any] = {"base_url": AIML_BASE_URL, "model": AIML_MODEL}
    info["api_key_present"] = bool(os.environ.get("AIML_API_KEY"))
    return info
