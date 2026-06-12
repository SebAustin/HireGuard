"""Cross-framework wiring + tool-layer tests (no network / no credentials).

Proves all four adapters construct with their role prompts + custom tools, and that
the workspace/ruleset/scoring tools behave. The AI/ML API call in score_exposure is
monkeypatched so this stays offline.
"""

from __future__ import annotations

import json

from hireguard import band_client as bc
from hireguard import tools
from hireguard.agents._common import load_prompt


def test_four_adapters_construct() -> None:
    claude = bc.make_claude_adapter(custom_section=load_prompt("intake"))
    langgraph = bc.make_langgraph_adapter(
        custom_section=load_prompt("policy"), additional_tools=tools.POLICY_TOOLS
    )
    crewai = bc.make_crewai_adapter(
        role="r", goal="g", backstory="b",
        custom_section=load_prompt("risk"), additional_tools=tools.RISK_TOOLS,
    )
    codex = bc.make_codex_adapter(custom_section=load_prompt("counsel"))
    assert type(claude).__name__ == "ClaudeSDKAdapter"
    assert type(langgraph).__name__ == "LangGraphAdapter"
    assert type(crewai).__name__ == "CrewAIAdapter"
    assert type(codex).__name__ == "CodexAdapter"


def test_role_prompts_load_and_define_handoffs() -> None:
    # Each prompt must name the next agent it hands off to (the coordination spine).
    assert "@PolicyAgent" in load_prompt("intake")
    assert "@RiskScorer" in load_prompt("policy")
    assert "@Counsel" in load_prompt("risk")
    assert "@PolicyAgent" in load_prompt("counsel")  # the visible re-loop bounce


def test_ruleset_tool_returns_all_rules() -> None:
    model, fn = tools.GET_RULESET_TOOL
    payload = json.loads(fn())
    assert len(payload["rules"]) >= 6


def test_score_exposure_is_load_bearing_on_aiml(monkeypatch, tmp_path) -> None:
    # The scoring tool MUST route through aiml_client.score.
    captured = {}

    def fake_score(system, user, **kw):
        captured["called"] = True
        return '{"exposure_score": 88, "severity": "severe", "likelihood": "high", "jurisdiction_attaches": true, "rationale": "x"}'

    monkeypatch.setattr(tools.aiml_client, "score", fake_score)
    model, fn = tools.SCORE_EXPOSURE_TOOL
    out = json.loads(fn(rule_id="PAYTRANS-CA-SB1162", citation="CA Labor Code 432.3",
                        evidence="no range posted", jurisdiction="San Francisco, CA"))
    assert captured.get("called") is True
    assert out["exposure_score"] == 88


def test_score_exposure_tolerates_non_json(monkeypatch) -> None:
    monkeypatch.setattr(tools.aiml_client, "score", lambda s, u, **k: "not json at all")
    _, fn = tools.SCORE_EXPOSURE_TOOL
    out = json.loads(fn(rule_id="X", citation="c", evidence="e", jurisdiction="j"))
    assert out["exposure_score"] is None
