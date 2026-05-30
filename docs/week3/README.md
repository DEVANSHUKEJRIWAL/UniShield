"""Week 3 — Persistence, CVE poller, vector corpus, insider schema."""

Week 3 deliverables: DB persistence for findings/alerts/risk scores, agent run logs, NVD CVE poller, UEBA schemas, vector corpus embedding.

## Implemented

| Deliverable | Location |
|-------------|----------|
| Finding persistence + alerts + risk scores | `packages/core/persistence.py` |
| Agent run history | `AgentRunLog` in `packages/core/models.py`, `log_agent_run()` |
| CVE poller + storage | `services/cve_poller/service.py`, `CVERecord` model |
| Insider / UEBA schema | `packages/core/insider_schema.py` |
| Structured specialist handlers | `agents/_openclaw/structured.py`, insider agent |
| Vector corpus embed | `services/vector-store/service.py` → `embed_corpus()` |
| CVE poll API | `POST /api/v1/cve/poll` |

## Quick start

```bash
# Persist finding via agent (mock mode — no Anthropic key)
curl -N -X POST http://localhost:8000/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"agent_name":"insider-threat-agent","tenant_id":"meridian-financial","input":{"type":"anomalous_login","user_id":"alice"}}'

# Poll CVEs
curl -X POST http://localhost:8000/api/v1/cve/poll \
  -H "Authorization: Bearer $TOKEN"

# Agent run history
curl http://localhost:8000/api/v1/agents/insider-threat-agent/runs?client_id=meridian-financial \
  -H "Authorization: Bearer $TOKEN"
```

## Tests

```bash
UNISHIELD_USE_SQLITE=1 pytest tests/unit/test_persistence.py tests/unit/test_specialist_agents.py -v
```

## Week 3 checklist

- [ ] Findings persist to SQLite/Postgres after agent run
- [ ] CVE poller stores records (`GET /api/v1/cve/recent`)
- [ ] Agent run logs visible via API
- [ ] Qdrant collections created via `embed_corpus`
