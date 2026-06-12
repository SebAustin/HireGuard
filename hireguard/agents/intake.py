"""@Intake — Policy/Operations agent on the Claude SDK adapter.

Parses the hiring packet into structured facts, writes workspace/notes/facts.md
(via Claude SDK's native filesystem tools), and hands off to @PolicyAgent.
"""

from __future__ import annotations

from hireguard import band_client
from hireguard.agents._common import load_prompt, run_standalone


def build():
    adapter = band_client.make_claude_adapter(custom_section=load_prompt("intake"))
    return band_client.build_agent("intake", adapter)


if __name__ == "__main__":
    run_standalone(build)
