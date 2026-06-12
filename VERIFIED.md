# VERIFIED.md — Phase 0 ground truth

> Everything downstream reads from this file, never from assumptions.
> Last verified: 2026-06-12 against `band-sdk==1.0.0` (PyPI, publisher `band.ai`).

---

## 0. Toolchain (confirmed on this machine)

| Item | Value |
|---|---|
| Python (system) | 3.14.5 — too new for band-sdk classifiers |
| Python (project, via uv) | **3.12** (pinned in `.python-version` / `pyproject.toml`) |
| uv | 0.11.18 |
| `band-sdk` | **1.0.0** (extras installed: `claude-sdk`, `codex`) |
| Underlying transport | Phoenix WebSocket channels + `thenvoi-client-rest` (THENVOI is the backend; `band.ai` is the product surface) |

Install line used:
```bash
uv add "band-sdk[claude-sdk,codex]"
```

---

## 1. GENERIC ADAPTER DECISION → **YES** ✅

`band-sdk` ships a public generic base **and** first-class framework adapters. Cross-framework
collaboration (LangGraph + CrewAI + Claude SDK + Codex, all participating in one Band room) is
fully supported by the SDK.

- **Generic / BYO base:** `band.core.simple_adapter.SimpleAdapter`
  - `__init__(self, *, history_converter=None, features: AdapterFeatures | None = None)`
  - Override `on_message(...)` / `on_event(...)` / `on_started(...)` / `on_cleanup(...)` to make
    ANY logic a Band participant. This is the seam for a hand-rolled agent.
- **First-class adapters present** (in `band.adapters`, lazily imported):
  `LangGraphAdapter`, `CrewAIAdapter`, `CrewAIFlowAdapter`, `ClaudeSDKAdapter`, `CodexAdapter`,
  `AnthropicAdapter`, `PydanticAIAdapter`, `GeminiAdapter`, `GoogleADKAdapter`, `LangChain*`,
  `LettaAdapter`, `ParlantAdapter`, `OpencodeAdapter`, `A2AAdapter`, `ACP*`, `SlackAdapter`.

**Implication for HireGuard:** the strongest Originality story (cross-framework) is on the table.
Recommended mapping (pending operator sign-off):
| Agent | Adapter | Extra to install |
|---|---|---|
| `@Intake` | `ClaudeSDKAdapter` | `claude-sdk` ✅ installed |
| `@PolicyAgent` | `LangGraphAdapter` | `band-sdk[langgraph]` (NOT yet installed) |
| `@RiskScorer` | `CrewAIAdapter` (model routed through AI/ML API) | `band-sdk[crewai]` (NOT yet installed) |
| `@Counsel` | `CodexAdapter` | `codex` ✅ installed |

Fallback if LangGraph/CrewAI integration burns too much time (still satisfies every hard
requirement): all four on `ClaudeSDKAdapter`/`CodexAdapter` with sharply distinct roles + tools.

---

## 2. Confirmed import paths & signatures

### Public surface (`from band import ...`)
```python
from band import (
    Agent,                  # composition entry point
    BandLink, PlatformEvent,
    AgentRuntime, RoomPresence, Execution, ExecutionContext, ExecutionHandler,
    AgentTools, PlatformMessage, AgentConfig, SessionConfig,
)
from band.adapters import (
    ClaudeSDKAdapter, CodexAdapter, CodexAdapterConfig,
    LangGraphAdapter, CrewAIAdapter,
)
from band.core.simple_adapter import SimpleAdapter
```

### Agent creation
```python
Agent.create(
    adapter,                      # FrameworkAdapter | SimpleAdapter
    agent_id: str,
    api_key: str,
    ws_url: str = "wss://app.band.ai/api/v1/socket/websocket",   # DEFAULT — band.ai
    rest_url: str = "https://app.band.ai",                       # DEFAULT — band.ai
    config: AgentConfig | None = None,
    session_config: SessionConfig | None = None,
    ...
) -> Agent

# Loads agent_id + api_key from agent_config.yaml by key:
Agent.from_config(name: str, *, adapter, config_path=None, **kwargs) -> Agent

# Lifecycle
await agent.start()
await agent.run()            # start + run_forever + graceful stop (shutdown_timeout=30s)
await agent.run_forever()
await agent.stop(timeout=None)
async with agent: ...        # context-manager form
```
> NOTE: default endpoints are `app.band.ai`. No separate `THENVOI_REST_URL`/`THENVOI_WS_URL`
> needed unless the dashboard says otherwise. `.env` keeps overridable `BAND_WS_URL`/`BAND_REST_URL`.

### Adapter constructors (verified via introspection)
```python
SimpleAdapter(*, history_converter=None, features=None)

ClaudeSDKAdapter(
    model=None, fallback_model=None, custom_section=None,
    max_thinking_tokens=None, permission_mode='acceptEdits',
    enable_execution_reporting=False, enable_memory_tools=False,
    additional_tools=None, cwd=None,
    # --- HUMAN-IN-THE-LOOP (this is our @HumanGate / sign-off mechanism) ---
    approval_mode=None, approval_text_notifications=True,
    approval_wait_timeout_s=300.0, approval_timeout_decision='decline',
    max_pending_approvals_per_room=50, approval_authorized_senders=None,
    features=None, send_message_dedup_ttl_seconds=30.0,
)

CodexAdapter(config: CodexAdapterConfig | None = None, *,
    additional_tools=None, history_converter=None, client_factory=None, features=None)

CrewAIAdapter(
    model='gpt-5.4',                # OVERRIDE to AI/ML API model id for @RiskScorer
    role=None, goal=None, backstory=None, custom_section=None,
    enable_execution_reporting=False, enable_memory_tools=False,
    verbose=False, max_iter=20, max_rpm=None, allow_delegation=False,
    additional_tools=None, system_prompt=None, features=None,
)
# CrewAI uses litellm internally → set OPENAI_BASE_URL=https://api.aimlapi.com/v1
# + OPENAI_API_KEY=$AIML_API_KEY to route @RiskScorer reasoning through AI/ML API.

LangGraphAdapter(...)   # requires `band-sdk[langgraph]`; not yet installed
```

### Platform tools (`AgentTools`)
```python
tools = AgentTools.from_context(ctx)
await tools.send_message(text, mentions=["@PolicyAgent"])   # @mention = handoff trigger
tools.add_participant / remove_participant / get_participants / lookup_peers
tools.create_chatroom
tools.store_memory / get_memory / list_memories / supersede_memory / archive_memory
tools.get_anthropic_tool_schemas() / get_openai_tool_schemas()
```
**There is NO platform file-read/write tool.** Shared content (`facts.md`, `risk.md`,
`audit.md`) lives in the **local `workspace/notes/` directory**. Claude SDK & Codex adapters
have native filesystem tools; LangGraph/CrewAI nodes write these files in their own logic.
This matches Band's "chat = coordination, files = content" convention via a shared local FS.

### Room kickoff — `band-trigger` CLI
```bash
band-trigger \
  --api-key "$BAND_API_KEY" \
  --target-handle "@owner/intake-agent" \
  --message "Audit the packet in samples/acme_se_role.json"
# Creates a chatroom, adds the target agent, posts the message. Prints chatroom ID to stdout.
# auth-mode user|agent. Default REST: https://app.band.ai/
```
`run_demo.py` will either shell out to `band-trigger` or use `thenvoi_rest.AsyncRestClient`
(`ChatRoomRequest`, `ChatMessageRequest`, `ParticipantRequest`) directly.

### agent_config.yaml format (keyed — what we use)
```yaml
intake:
  agent_id: "<uuid>"
  api_key: "<key>"
policy:
  agent_id: "<uuid>"
  api_key: "<key>"
risk:
  agent_id: "<uuid>"
  api_key: "<key>"
counsel:
  agent_id: "<uuid>"
  api_key: "<key>"
```

---

## 3. STILL BLOCKED — needs operator (Sebastien) from band.ai dashboard / kickoff

These cannot be self-served and gate the live smoke test:

- [ ] **Band: 4 remote agents created** on app.band.ai → record each `agent_id` (UUID) + `api_key`
      into `agent_config.yaml` (gitignored). Agents MUST be pre-created as remote agents.
- [ ] **Band: owner handle** for `--target-handle "@<owner>/<agent>"` in the trigger.
- [ ] **Band: confirm endpoints** match defaults (`wss://app.band.ai/...`, `https://app.band.ai`)
      or paste dashboard-specific URLs into `.env`.
- [ ] **AI/ML API key** → `AIML_API_KEY`. Confirm a known-good reasoning model id
      (`openai/gpt-4.1` or `deepseek/deepseek-r1`) via the proof-of-life snippet in §4.
- [ ] **ANTHROPIC_API_KEY** (Claude SDK adapter) and Codex/OpenAI key as needed by adapters.

### §4 — AI/ML API proof-of-life (run once key is set)
```python
from openai import OpenAI; import os
client = OpenAI(base_url="https://api.aimlapi.com/v1", api_key=os.environ["AIML_API_KEY"])
r = client.chat.completions.create(model="openai/gpt-4.1",
        messages=[{"role":"user","content":"ping"}])
print(r.choices[0].message.content)
```
Result: ⏳ PENDING (no key yet). Record working model id here once confirmed: `__________`

---

## 4. Smoke test status

- [x] `band-sdk` installs, imports resolve, adapter signatures introspected.
- [ ] One agent connects to a live Band room and posts one message — **blocked on credentials.**
