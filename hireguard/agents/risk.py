"""@RiskScorer — Risk agent on the CrewAI adapter.

Scores legal exposure per finding and overall. The load-bearing scoring runs through
the AI/ML API via the `score_exposure` custom tool (aiml_client) — a finding has no
score until that call returns. Writes workspace/notes/risk.md and hands off to @Counsel.
"""

from __future__ import annotations

from hireguard import band_client
from hireguard.agents._common import load_prompt, run_standalone
from hireguard.tools import RISK_TOOLS


def build():
    adapter = band_client.make_crewai_adapter(
        role="Senior employment-law risk analyst",
        goal="Quantify legal exposure for each compliance finding and an overall verdict",
        backstory=(
            "A meticulous paralegal-analyst who scores EEOC and pay-transparency risk "
            "using the AI/ML API and never drops a finding silently."
        ),
        custom_section=load_prompt("risk"),
        additional_tools=RISK_TOOLS,
    )
    return band_client.build_agent("risk", adapter)


if __name__ == "__main__":
    run_standalone(build)
