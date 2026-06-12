"""Seam smoke tests — run without any credentials.

Verifies the band-sdk seam loads, local workspace IO works, the ruleset is valid
and fully cited, and both sample packets carry the three required artifacts.

    uv run pytest -q
"""

from __future__ import annotations

import json
from pathlib import Path

from hireguard import aiml_client as ai
from hireguard import band_client as bc

ROOT = Path(__file__).resolve().parent.parent


def test_band_sdk_imports_through_seam() -> None:
    from band import Agent

    assert Agent.__name__ == "Agent"


def test_workspace_file_io(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(bc, "WORKSPACE", tmp_path)
    bc.write_note("facts.md", "# Facts\nhello\n")
    assert bc.note_exists("facts.md")
    bc.append_note("facts.md", "more\n")
    body = bc.read_note("facts.md")
    assert "hello" in body and "more" in body


def test_ruleset_valid_and_cited() -> None:
    rs = json.loads((ROOT / "hireguard/rules/ruleset.json").read_text())
    ids = [r["rule_id"] for r in rs["rules"]]
    assert len(ids) == len(set(ids)), "duplicate rule_ids"
    assert len(ids) >= 6, "need >=6 rules for a credible demo"
    for r in rs["rules"]:
        assert r["citation"], f"{r['rule_id']} missing citation"
        assert r["category_default"] in {"Critical", "Risk", "Gap", "Suggestion"}


def test_sample_packets_have_three_artifacts() -> None:
    for name in ["acme_se_role", "northwind_pm_role"]:
        pk = json.loads((ROOT / f"hireguard/samples/{name}.json").read_text())
        assert pk["job_posting"]
        assert pk["comp_band"]
        assert pk["interview_scorecard"]


def test_claude_adapter_factory_constructs() -> None:
    adapter = bc.make_claude_adapter(custom_section="role prompt")
    assert type(adapter).__name__ == "ClaudeSDKAdapter"


def test_aiml_health_reports_config() -> None:
    h = ai.health()
    assert h["base_url"].endswith("/v1")
    assert "model" in h
