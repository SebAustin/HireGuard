"""@Councel — Legal/Review agent on the CrewAI adapter (AI/ML API).

Cross-references all findings, de-dupes, categorizes Critical/Risk/Gap/Suggestion,
bounces thin Criticals back to @PolicyAgent (the visible re-loop), writes the final
workspace/notes/audit.md, and requests human sign-off.  Reads/writes workspace notes
via explicit tool calls (COUNSEL_TOOLS).
"""

from __future__ import annotations

from hireguard import band_client, tools
from hireguard.agents._common import load_prompt, run_standalone


def build():
    adapter = band_client.make_crewai_adapter(
        role="Senior employment attorney and hiring-compliance auditor",
        goal="Produce the final, defensible compliance audit memo for the hiring packet",
        backstory=(
            "A meticulous employment lawyer who cross-references compliance findings, "
            "de-duplicates overlapping issues, bounces thin Criticals back for re-examination, "
            "and writes final audit memos that can withstand legal scrutiny."
        ),
        custom_section=load_prompt("counsel"),
        additional_tools=tools.COUNSEL_TOOLS,
    )
    return band_client.build_agent("counsel", adapter)


if __name__ == "__main__":
    run_standalone(build)
