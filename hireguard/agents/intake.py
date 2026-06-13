"""@Intake — Policy/Operations agent on the LangGraph adapter (AI/ML API).

Parses the hiring packet into structured facts, writes workspace/notes/facts.md
via explicit tool calls (READ_PACKET_TOOL + WRITE_NOTE_TOOL), and hands off to
@PolicyAgent.
"""

from __future__ import annotations

from hireguard import band_client, tools
from hireguard.agents._common import load_prompt, run_standalone


def build():
    adapter = band_client.make_langgraph_adapter(
        custom_section=load_prompt("intake"),
        additional_tools=tools.INTAKE_TOOLS,
    )
    return band_client.build_agent("intake", adapter)


if __name__ == "__main__":
    run_standalone(build)
