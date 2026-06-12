"""Shared helpers for agent modules."""

from __future__ import annotations

import asyncio
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a role prompt (persistent behavior + handoff protocol)."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def run_standalone(build_fn) -> None:
    """Run a single agent standalone (for `python -m hireguard.agents.<name>`)."""
    from dotenv import load_dotenv

    load_dotenv()
    agent = build_fn()
    asyncio.run(agent.run())
