# HireGuard — Multi-Agent Hiring-Compliance Auditor

Four specialized agents collaborate **through a Band room** to audit a company's hiring
artifacts for U.S. employment-compliance risk (EEOC anti-discrimination + state
pay-transparency law) and produce a defensible audit memo.

> Band of Agents Hackathon · Track 3 (Regulated & High-Stakes). Targets the Main prize
> (Application of Technology) and Best Use of AI/ML API.

## The collaboration (this is the demo)

```
@Intake ──facts.md──▶ @PolicyAgent ──findings──▶ @RiskScorer ──risk.md──▶ @Counsel ──▶ audit.md
 (Claude SDK)          (LangGraph*)               (CrewAI → AI/ML API)     (Codex)      + human sign-off
                                                                              │
                                          visible re-loop: @Counsel ⤴ bounces a Critical back to @PolicyAgent
```

- **Chat is for coordination, files are for content** (Band's convention). Agents hand off
  via `@mentions`; shared content lives in `hireguard/workspace/notes/`.
- **AI/ML API is load-bearing:** `@RiskScorer` cannot produce a risk score without a call
  through `aiml_client.py`.

\* Cross-framework mapping (LangGraph + CrewAI) is pending the operator's originality-angle
decision — see [VERIFIED.md](VERIFIED.md) §1. Fallback is all-Claude/Codex with distinct roles.

## Status

Phase 0 (verification) complete — see [VERIFIED.md](VERIFIED.md). Seam + scaffold + ruleset +
samples + role prompts in place; `uv run pytest -q` is green. Agent logic and `run_demo.py`
are next, gated on Band credentials + AI/ML API key.

## Layout

| Path | Role |
|---|---|
| `hireguard/band_client.py` | **Only** file importing `band-sdk` (the seam) |
| `hireguard/aiml_client.py` | AI/ML API client — @RiskScorer's reasoning backend |
| `hireguard/rules/ruleset.json` | 10 real, citeable EEOC + pay-transparency rules |
| `hireguard/prompts/*.md` | Persistent role prompts + handoff protocol |
| `hireguard/samples/` | `acme_se_role` (planted violations) · `northwind_pm_role` (clean) |
| `hireguard/agents/` | Per-agent wiring (next phase) |
| `VERIFIED.md` | Phase-0 ground truth — everything downstream reads from here |

## Setup

```bash
uv sync
cp .env.example .env                      # fill in AIML_API_KEY, ANTHROPIC_API_KEY, ...
cp agent_config.yaml.example agent_config.yaml   # fill 4 agent_id + api_key from app.band.ai
uv run pytest -q                          # seam smoke tests (no creds needed)
```

## How we used Band  <!-- submission section, fill at the end -->
_Screenshot of the 4-agent room + handoff snippet from `band_client.py`._

## How we used AI/ML API  <!-- submission section, fill at the end -->
_Screenshot + the `@RiskScorer` scoring call + why it is load-bearing._
