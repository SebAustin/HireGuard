"""@Counsel — Legal/Review agent on the Codex adapter.

Cross-references all findings, de-dupes, categorizes Critical/Risk/Gap/Suggestion,
bounces thin Criticals back to @PolicyAgent (the visible re-loop), writes the final
workspace/notes/audit.md, and requests human sign-off. Codex has native filesystem
tools, so it reads/writes the workspace notes directly.
"""

from __future__ import annotations

from hireguard import band_client
from hireguard.agents._common import load_prompt, run_standalone


def build():
    adapter = band_client.make_codex_adapter(custom_section=load_prompt("counsel"))
    return band_client.build_agent("counsel", adapter)


if __name__ == "__main__":
    run_standalone(build)
