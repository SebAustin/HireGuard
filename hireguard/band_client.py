"""band_client.py — the ONLY module that imports band-sdk.

Everything Band-specific lives here. If the platform's API differs from what we
verified in VERIFIED.md, we fix this one file and nothing else cascades.

Two responsibilities:
  1. Adapter factories + agent construction (the band-sdk surface).
  2. Shared-workspace file IO (local files; Band has no platform file tool, so
     `facts.md` / `risk.md` / `audit.md` are plain local files in workspace/notes/).
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Any

# --- band-sdk imports (confined to this module) -----------------------------
from band import Agent  # noqa: F401  (re-exported for type clarity)

# Adapters are lazily imported in their factories so this module loads even when
# an optional extra (langgraph / crewai) is not installed yet.

# --- paths -------------------------------------------------------------------
PKG_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PKG_ROOT.parent
WORKSPACE = PKG_ROOT / "workspace" / "notes"
DEFAULT_CONFIG = PROJECT_ROOT / "agent_config.yaml"

WS_URL = os.environ.get("BAND_WS_URL", "wss://app.band.ai/api/v1/socket/websocket")
REST_URL = os.environ.get("BAND_REST_URL", "https://app.band.ai")


# --- shared workspace file IO (content lives in files, not chat) -------------
def _note_path(name: str) -> Path:
    return WORKSPACE / name


def write_note(name: str, text: str) -> Path:
    """Write (overwrite) a shared note. Returns the path."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    path = _note_path(name)
    path.write_text(text, encoding="utf-8")
    return path


def append_note(name: str, text: str) -> Path:
    """Append to a shared note, creating it if needed."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    path = _note_path(name)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text)
    return path


def read_note(name: str) -> str:
    return _note_path(name).read_text(encoding="utf-8")


def note_exists(name: str) -> bool:
    return _note_path(name).exists()


async def wait_for_note(name: str, *, timeout: float = 120.0, poll: float = 1.0) -> bool:
    """Deterministic upstream-dependency gate (see failure-mode #1 in CLAUDE.md).

    An agent calls this to block until its input file is ready before starting.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if note_exists(name):
            return True
        await asyncio.sleep(poll)
    return False


# --- adapter factories (band-sdk adapter surface) ----------------------------
def make_claude_adapter(*, custom_section: str, model: str | None = None, **kwargs: Any):
    """ClaudeSDKAdapter. `custom_section` is the agent's persistent role prompt."""
    from band.adapters import ClaudeSDKAdapter

    return ClaudeSDKAdapter(
        model=model,
        custom_section=custom_section,
        cwd=str(PROJECT_ROOT),  # so the agent's filesystem tools see workspace/notes
        **kwargs,
    )


def make_codex_adapter(*, custom_section: str = "", model: str | None = None, **kwargs: Any):
    """CodexAdapter for @Counsel (via CodexAdapterConfig).

    `custom_section` is the role prompt. `cwd` is set to the project root so the
    agent's filesystem tools see workspace/notes when writing audit.md.
    """
    from band.adapters import CodexAdapter, CodexAdapterConfig

    config = CodexAdapterConfig(
        custom_section=custom_section,
        model=model,
        cwd=str(PROJECT_ROOT),
    )
    return CodexAdapter(config=config, **kwargs)


def make_crewai_adapter(
    *, role: str, goal: str, backstory: str, model: str | None = None, **kwargs: Any
):
    """CrewAIAdapter. Routes model calls through litellm.

    Set OPENAI_BASE_URL=https://api.aimlapi.com/v1 + OPENAI_API_KEY=$AIML_API_KEY in
    the environment so @RiskScorer's reasoning runs through the AI/ML API.
    """
    from band.adapters import CrewAIAdapter

    model = model or os.environ.get("AIML_MODEL", "openai/gpt-4.1")
    return CrewAIAdapter(model=model, role=role, goal=goal, backstory=backstory, **kwargs)


def make_langgraph_adapter(*, custom_section: str, llm: Any = None, additional_tools=None, **kwargs: Any):
    """LangGraphAdapter for @PolicyAgent. Requires `band-sdk[langgraph]`.

    Pass an `llm` (a LangChain chat model) + `custom_section` (role prompt); the
    adapter builds a default tool-using graph and injects the Band tools plus any
    `additional_tools` (our workspace/ruleset tools). If `llm` is None, builds a
    ChatOpenAI pointed at the AI/ML API.
    """
    from band.adapters import LangGraphAdapter

    if llm is None:
        llm = make_aiml_langchain_llm()
    return LangGraphAdapter(
        llm=llm,
        custom_section=custom_section,
        additional_tools=additional_tools,
        **kwargs,
    )


def make_aiml_langchain_llm(model: str | None = None):
    """A LangChain ChatOpenAI bound to the AI/ML API (OpenAI-compatible).

    Note the model-id handling: litellm/LangChain send the model string as-is to
    the base URL, so for AI/ML API we use the full `openai/<model>` id.
    """
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model or os.environ.get("AIML_MODEL", "openai/gpt-4.1"),
        base_url=os.environ.get("AIML_BASE_URL", "https://api.aimlapi.com/v1"),
        api_key=os.environ.get("AIML_API_KEY", "missing"),
        temperature=0.2,
    )


# --- agent construction ------------------------------------------------------
def build_agent(agent_key: str, adapter: Any, *, config_path: str | Path | None = None) -> Agent:
    """Build a Band Agent from agent_config.yaml + a constructed adapter.

    `agent_key` is the top-level key in agent_config.yaml (intake/policy/risk/counsel).
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    return Agent.from_config(
        agent_key,
        adapter=adapter,
        config_path=path,
        ws_url=WS_URL,
        rest_url=REST_URL,
    )


# --- room kickoff (the spine of run_demo.py) ---------------------------------
def trigger_room(target_handle: str, message: str, *, api_key: str | None = None) -> str:
    """Create a chatroom, add the target agent, and post the first message.

    Wraps the verified `band-trigger` CLI. Returns the chatroom id (stdout).
    """
    key = api_key or os.environ.get("BAND_API_KEY")
    if not key:
        raise RuntimeError("BAND_API_KEY (or api_key=) required to trigger a room.")
    result = subprocess.run(
        [
            "band-trigger",
            "--api-key", key,
            "--target-handle", target_handle,
            "--message", message,
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"band-trigger failed: {result.stderr.strip()}")
    return result.stdout.strip()
