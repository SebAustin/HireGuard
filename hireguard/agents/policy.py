"""@PolicyAgent — Policy agent on the LangGraph adapter.

Checks the extracted facts against the EEOC + pay-transparency ruleset and flags
candidate findings with rule citations. Its LangGraph LLM runs through the AI/ML API.
Uses custom tools (get_ruleset / read_note / append_note) since LangGraph has no
native filesystem tools.
"""

from __future__ import annotations

from hireguard import band_client
from hireguard.agents._common import load_prompt, run_standalone
from hireguard.tools import POLICY_TOOLS


def build():
    adapter = band_client.make_langgraph_adapter(
        custom_section=load_prompt("policy"),
        additional_tools=POLICY_TOOLS,
    )
    return band_client.build_agent("policy", adapter)


if __name__ == "__main__":
    run_standalone(build)
