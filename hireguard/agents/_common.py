"""Shared helpers for agent modules."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a role prompt, substituting {OWNER} with the Band owner handle."""
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    owner = os.environ.get("BAND_OWNER_HANDLE", "@owner").lstrip("@")
    return text.replace("{OWNER}", owner)


def run_standalone(build_fn) -> None:
    """Run a single agent standalone (for `python -m hireguard.agents.<name>`)."""
    from dotenv import load_dotenv

    load_dotenv()
    agent = build_fn()
    asyncio.run(agent.run())
