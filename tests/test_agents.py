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
    intake = bc.make_langgraph_adapter(
        custom_section=load_prompt("intake"), additional_tools=tools.INTAKE_TOOLS
    )
    policy = bc.make_langgraph_adapter(
        custom_section=load_prompt("policy"), additional_tools=tools.POLICY_TOOLS
    )
    risk = bc.make_crewai_adapter(
        role="r", goal="g", backstory="b",
        custom_section=load_prompt("risk"), additional_tools=tools.RISK_TOOLS,
    )
    counsel = bc.make_crewai_adapter(
        role="r", goal="g", backstory="b",
        custom_section=load_prompt("counsel"), additional_tools=tools.COUNSEL_TOOLS,
    )
    assert type(intake).__name__ == "LangGraphAdapter"
    assert type(policy).__name__ == "LangGraphAdapter"
    assert type(risk).__name__ == "CrewAIAdapter"
    assert type(counsel).__name__ == "CrewAIAdapter"


def test_role_prompts_load_and_define_handoffs() -> None:
    assert "@PolicyAgent" in load_prompt("intake")
    assert "@RiskScorer" in load_prompt("policy")
    assert "@Councel" in load_prompt("risk")
    assert "@PolicyAgent" in load_prompt("counsel")  # visible re-loop bounce


def test_tool_bundles_have_correct_tools() -> None:
    assert tools.READ_PACKET_TOOL in tools.INTAKE_TOOLS
    assert tools.WRITE_NOTE_TOOL in tools.INTAKE_TOOLS
    assert tools.READ_NOTE_TOOL in tools.COUNSEL_TOOLS
    assert tools.WRITE_NOTE_TOOL in tools.COUNSEL_TOOLS
    assert tools.GET_RULESET_TOOL in tools.COUNSEL_TOOLS


def test_ruleset_tool_returns_all_rules() -> None:
    _, fn = tools.GET_RULESET_TOOL
    payload = json.loads(fn())
    assert len(payload["rules"]) >= 6


def test_read_packet_tool_returns_error_for_missing_file() -> None:
    _, fn = tools.READ_PACKET_TOOL
    inp = tools.ReadPacketInput(path="hireguard/samples/__nonexistent__.json")
    result = json.loads(fn(inp))
    assert "error" in result


def test_score_exposure_is_load_bearing_on_aiml(monkeypatch) -> None:
    captured = {}

    def fake_score(system, user, **kw):
        captured["called"] = True
        return '{"exposure_score": 88, "severity": "severe", "likelihood": "high", "jurisdiction_attaches": true, "rationale": "x"}'

    monkeypatch.setattr(tools.aiml_client, "score", fake_score)
    _, fn = tools.SCORE_EXPOSURE_TOOL
    inp = tools.ScoreExposureInput(
        rule_id="PAYTRANS-CA-SB1162",
        citation="CA Labor Code 432.3",
        evidence="no range posted",
        jurisdiction="San Francisco, CA",
    )
    out = json.loads(fn(inp))
    assert captured.get("called") is True
    assert out["exposure_score"] == 88


def test_score_exposure_tolerates_non_json(monkeypatch) -> None:
    monkeypatch.setattr(tools.aiml_client, "score", lambda s, u, **k: "not json at all")
    _, fn = tools.SCORE_EXPOSURE_TOOL
    inp = tools.ScoreExposureInput(
        rule_id="X", citation="c", evidence="e", jurisdiction="j"
    )
    out = json.loads(fn(inp))
    assert out["exposure_score"] is None


def test_langchain_tool_conversion() -> None:
    """_to_langchain_tool must produce StructuredTool instances LangGraph can consume."""
    from langchain_core.tools import StructuredTool

    lt = bc._to_langchain_tool(tools.READ_NOTE_TOOL)
    assert isinstance(lt, StructuredTool)
    assert lt.name == "readnote"

    lt0 = bc._to_langchain_tool(tools.GET_RULESET_TOOL)
    assert isinstance(lt0, StructuredTool)
    assert lt0.name == "getruleset"
