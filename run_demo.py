"""run_demo.py — one command spins up the Band room + 4 agents + feeds a sample packet.

Usage:
    uv run python run_demo.py --check                 # validate config/env, no network
    uv run python run_demo.py --sample acme_se_role   # full live run (needs credentials)

The four agents collaborate THROUGH the Band room:
    @Intake (LangGraph/AI/ML) -> @PolicyAgent (LangGraph/AI/ML) -> @RiskScorer (CrewAI/AI/ML)
    -> @Councel (CrewAI/AI/ML) -> audit.md + human sign-off, with a visible re-loop.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)

ROOT = Path(__file__).resolve().parent
SAMPLES_DIR = ROOT / "hireguard" / "samples"
CONFIG_PATH = ROOT / "agent_config.yaml"
AGENT_KEYS = ["intake", "policy", "risk", "counsel"]


def _check() -> int:
    """Validate everything that does NOT require a network connection."""
    load_dotenv()
    ok = True

    def line(label: str, good: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and good
        mark = "✅" if good else "❌"
        print(f"  {mark} {label}{(' — ' + detail) if detail else ''}")

    print("HireGuard preflight check\n")

    # 1. agent_config.yaml present with all 4 keys + non-placeholder values
    if CONFIG_PATH.exists():
        import yaml

        cfg = yaml.safe_load(CONFIG_PATH.read_text()) or {}
        for k in AGENT_KEYS:
            entry = cfg.get(k, {})
            aid = str(entry.get("agent_id", ""))
            key = str(entry.get("api_key", ""))
            filled = bool(aid) and "0000" not in aid and bool(key) and "..." not in key
            line(f"agent_config.yaml [{k}]", filled, "agent_id+api_key set" if filled else "missing/placeholder")
    else:
        line("agent_config.yaml present", False, "copy agent_config.yaml.example")

    # 2. env keys
    line("AIML_API_KEY set", bool(os.environ.get("AIML_API_KEY")))
    line("ANTHROPIC_API_KEY set", bool(os.environ.get("ANTHROPIC_API_KEY")))
    line("BAND_API_KEY set (for trigger)", bool(os.environ.get("BAND_API_KEY")))

    # 3. ruleset + samples parse
    from hireguard.tools import RULESET_PATH

    try:
        rs = json.loads(RULESET_PATH.read_text())
        line("ruleset.json valid", True, f"{len(rs['rules'])} rules")
    except Exception as e:  # noqa: BLE001
        line("ruleset.json valid", False, str(e))

    for name in ["acme_se_role", "northwind_pm_role"]:
        p = SAMPLES_DIR / f"{name}.json"
        line(f"sample {name}", p.exists())

    # 4. adapters construct
    try:
        from hireguard.agents import counsel, intake, policy, risk  # noqa: F401

        line("agent modules import", True)
    except Exception as e:  # noqa: BLE001
        line("agent modules import", False, f"{type(e).__name__}: {e}")

    print("\n" + ("All green — ready for a live run." if ok else "Blocked — fill the ❌ items above (see VERIFIED.md §3)."))
    return 0 if ok else 1


async def _run(sample: str) -> None:
    """Live run: start all 4 agents, then trigger the room at @Intake."""
    load_dotenv()
    from hireguard import band_client
    from hireguard.agents import counsel, intake, policy, risk

    sample_path = f"hireguard/samples/{sample}.json"
    if not (ROOT / sample_path).exists():
        sys.exit(f"sample not found: {sample_path}")

    agents = [intake.build(), policy.build(), risk.build(), counsel.build()]

    # Start all four; they connect to Band and listen for mentions.
    await asyncio.gather(*(a.start() for a in agents))
    print(f"4 agents connected. Triggering audit of {sample_path} ...")

    owner = os.environ.get("BAND_OWNER_HANDLE", "@owner").lstrip("@")

    # band-trigger requires agent auth; use policy agent's key so intake is visible as a peer.
    import yaml
    cfg = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    intake_key = cfg.get("policy", {}).get("api_key")

    chatroom = band_client.trigger_room(
        target_handle=f"@{owner}/intake",
        message=f"Audit the hiring packet in {sample_path}. Begin by extracting facts.",
        api_key=intake_key,
    )
    print(f"Room triggered: {chatroom}\nWatch the room; Ctrl+C to stop.")

    try:
        await asyncio.gather(*(a.run_forever() for a in agents))
    finally:
        await asyncio.gather(*(a.stop() for a in agents), return_exceptions=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="HireGuard demo runner")
    parser.add_argument("--check", action="store_true", help="Preflight validation, no network")
    parser.add_argument("--sample", default="acme_se_role", help="Sample packet id to audit")
    args = parser.parse_args()

    if args.check:
        sys.exit(_check())
    asyncio.run(_run(args.sample))


if __name__ == "__main__":
    main()
