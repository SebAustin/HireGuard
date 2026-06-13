"""Custom tools given to LangGraph and CrewAI agents.

band-sdk calling convention (``execute_custom_tool``):
- 0-field model  → callable takes no args:   ``def fn() -> str``
- N-field model  → callable takes the validated Pydantic instance as the sole
                   positional arg: ``def fn(inp: MyInput) -> str``

A band-sdk custom tool is ``(PydanticInputModel, callable)``; the tool name
derives from the model class name minus ``Input``, lowercased.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from hireguard import aiml_client, band_client

RULESET_PATH = Path(__file__).resolve().parent / "rules" / "ruleset.json"


# --- read a shared workspace note -------------------------------------------
class ReadNoteInput(BaseModel):
    """Read a shared workspace note (e.g. 'facts.md', 'risk.md'). Returns its text."""

    name: str = Field(description="File name within workspace/notes, e.g. 'facts.md'")


def _read_note(inp: ReadNoteInput) -> str:
    if not band_client.note_exists(inp.name):
        return f"(note '{inp.name}' does not exist yet)"
    return band_client.read_note(inp.name)


READ_NOTE_TOOL = (ReadNoteInput, _read_note)


# --- write/append a shared workspace note -----------------------------------
class WriteNoteInput(BaseModel):
    """Overwrite a shared workspace note with the given Markdown content."""

    name: str = Field(description="File name, e.g. 'risk.md'")
    content: str = Field(description="Full Markdown content to write")


def _write_note(inp: WriteNoteInput) -> str:
    band_client.write_note(inp.name, inp.content)
    return f"wrote {inp.name} ({len(inp.content)} chars)"


WRITE_NOTE_TOOL = (WriteNoteInput, _write_note)


class AppendNoteInput(BaseModel):
    """Append Markdown to a shared workspace note, creating it if absent."""

    name: str = Field(description="File name, e.g. 'facts.md'")
    content: str = Field(description="Markdown to append")


def _append_note(inp: AppendNoteInput) -> str:
    band_client.append_note(inp.name, inp.content)
    return f"appended to {inp.name}"


APPEND_NOTE_TOOL = (AppendNoteInput, _append_note)


# --- read the compliance ruleset --------------------------------------------
class GetRulesetInput(BaseModel):
    """Return the full HireGuard compliance ruleset (EEOC + pay-transparency) as JSON."""


def _get_ruleset() -> str:
    return RULESET_PATH.read_text(encoding="utf-8")


GET_RULESET_TOOL = (GetRulesetInput, _get_ruleset)


# --- score legal exposure via AI/ML API (LOAD-BEARING) ----------------------
class ScoreExposureInput(BaseModel):
    """Score the legal exposure of one compliance finding (0-100) using the AI/ML API.

    A finding has no risk score until this returns. Provide the rule citation, the
    quoted evidence, and the employer's jurisdiction so the model can weigh severity,
    likelihood, and whether the jurisdiction attaches.
    """

    rule_id: str = Field(description="The cited rule_id, e.g. 'PAYTRANS-CA-SB1162'")
    citation: str = Field(description="The statute/guidance citation for the rule")
    evidence: str = Field(description="The exact offending text or noted omission")
    jurisdiction: str = Field(description="Employer primary work location, e.g. 'San Francisco, CA'")


def _score_exposure(inp: ScoreExposureInput) -> str:
    """Returns a JSON string: {exposure_score, severity, likelihood, jurisdiction_attaches, rationale}."""
    system = (
        "You are a U.S. employment-law risk analyst. Score the legal exposure of a single "
        "hiring-compliance finding. Respond ONLY with strict JSON: "
        '{"exposure_score": <0-100 int>, "severity": "<low|moderate|high|severe>", '
        '"likelihood": "<low|moderate|high>", "jurisdiction_attaches": <true|false>, '
        '"rationale": "<one sentence>"}.'
    )
    user = (
        f"Rule: {inp.rule_id}\nCitation: {inp.citation}\n"
        f"Employer jurisdiction: {inp.jurisdiction}\nEvidence: {inp.evidence}\n\n"
        "Weigh statutory penalty/litigation exposure (severity), how clearly the evidence "
        "establishes a violation (likelihood), and whether this jurisdiction puts the "
        "employer squarely under the rule."
    )
    raw = aiml_client.score(system, user)
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
    try:
        parsed = json.loads(text)
        parsed["_model"] = aiml_client.AIML_MODEL
        return json.dumps(parsed)
    except json.JSONDecodeError:
        return json.dumps({"exposure_score": None, "rationale": raw[:400], "_model": aiml_client.AIML_MODEL})


SCORE_EXPOSURE_TOOL = (ScoreExposureInput, _score_exposure)


# --- read any project file by relative path (for @Intake) -------------------
class ReadPacketInput(BaseModel):
    """Read a hiring packet JSON file and return its raw text.

    Pass the path relative to the project root, e.g.
    'hireguard/samples/acme_se_role.json'.
    """

    path: str = Field(
        description="Path relative to the project root, e.g. 'hireguard/samples/acme_se_role.json'"
    )


def _read_packet(inp: ReadPacketInput) -> str:
    full = band_client.PROJECT_ROOT / inp.path
    if not full.exists():
        return json.dumps({"error": f"File not found: {inp.path}"})
    return full.read_text(encoding="utf-8")


READ_PACKET_TOOL = (ReadPacketInput, _read_packet)


# Tool bundles per agent
POLICY_TOOLS = [GET_RULESET_TOOL, READ_NOTE_TOOL, APPEND_NOTE_TOOL]
RISK_TOOLS = [READ_NOTE_TOOL, WRITE_NOTE_TOOL, SCORE_EXPOSURE_TOOL]
INTAKE_TOOLS = [READ_PACKET_TOOL, WRITE_NOTE_TOOL]
COUNSEL_TOOLS = [READ_NOTE_TOOL, WRITE_NOTE_TOOL, GET_RULESET_TOOL]
