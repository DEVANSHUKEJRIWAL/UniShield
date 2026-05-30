# Week 2 — Agent Pipeline & First Specialists

Week 2 deliverables: orchestrator dispatch, agent messaging, Redis workers, Dark Web + Source Code agents v1, credential schemas, pytest suites.

## Implemented

| Deliverable | Location |
|-------------|----------|
| Orchestrator dispatch + aggregation + retry | `agents/orchestrator/agent.py`, `packages/core/dispatch.py` |
| Event routing table | `agents/orchestrator/routing.py` |
| Agent-to-agent message protocol | `packages/core/agent_messages.py` |
| Redis task publish/consume | `packages/core/redis_client.py`, `agents/worker.py` |
| Worker startup script | `scripts/run-agent-workers.sh` |
| Credential alert schema | `packages/core/schemas.py` → `CredentialExposureAlert` |
| Dark Web v1 + structured breach findings | `agents/dark-web-agent/agent.py` |
| Source Code v1 + Semgrep/Bandit tools | `agents/source-code-agent/agent.py`, `agents/_openclaw/tools.py` |
| Multi-agent SSE API | `POST /agent/orchestrate` |
| Structured queue API | `POST /api/v1/agents/run` uses `AgentTaskMessage` |
| Pytest suites | `tests/unit/test_routing.py`, `test_orchestrator.py`, `test_dark_web_agent.py`, `test_source_code_agent.py` |

## Quick start

### 1. Start Redis

```bash
docker compose up -d redis
```

### 2. Start workers (terminal 1)

```bash
chmod +x scripts/run-agent-workers.sh
./scripts/run-agent-workers.sh
```

### 3. Start API (terminal 2)

```bash
./scripts/dev-local.sh
```

### 4. Run multi-agent orchestration

```bash
curl -N -X POST http://localhost:8000/agent/orchestrate \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant_id": "meridian-financial",
    "event": {
      "type": "credential_leak",
      "domain": "meridian.com",
      "severity": "critical"
    }
  }'
```

### 5. Run single agent (SSE)

```bash
curl -N -X POST http://localhost:8000/agent/run \
  -H 'Content-Type: application/json' \
  -d '{
    "agent_name": "source-code-agent",
    "tenant_id": "meridian-financial",
    "input": {"type": "code_commit", "repo_path": "/workspace"}
  }'
```

## Message protocol

**Task (orchestrator → specialist):**

```json
{
  "task_id": "uuid",
  "tenant_id": "meridian-financial",
  "priority": "P1",
  "input": { "type": "credential_leak", "domain": "meridian.com" },
  "context": { "event": {}, "prior_findings": [] },
  "triggered_by": "orchestrator"
}
```

**Result (specialist → orchestrator):** `AgentResultMessage` in `packages/core/agent_messages.py`

## Routing reference

See [Week 1 orchestrator design](../week1/orchestrator-design.md) — now implemented in `agents/orchestrator/routing.py`.

## Tests

```bash
UNISHIELD_USE_SQLITE=1 pytest tests/unit/test_routing.py \
  tests/unit/test_agent_messages.py \
  tests/unit/test_orchestrator.py \
  tests/unit/test_dark_web_agent.py \
  tests/unit/test_source_code_agent.py -v
```

## Week 2 checklist

- [ ] Redis running locally
- [ ] Workers consuming task streams
- [ ] `POST /agent/orchestrate` returns aggregated finding
- [ ] Dark Web credential leak produces `BreachFinding`
- [ ] Source Code commit produces `CodeFinding`
- [ ] Optional: `semgrep` / `bandit` installed for live SAST
- [ ] Optional: `OSINT_FEED_URLS` set for live feed fetch
