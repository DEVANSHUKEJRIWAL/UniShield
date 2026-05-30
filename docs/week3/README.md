# Week 3 — Persistence, CVE poller, vector corpus, insider schema

Week 3 deliverables: DB persistence for findings/alerts/risk scores, agent run logs, NVD CVE poller, UEBA schemas, vector corpus embedding.

## Implemented

| Deliverable | Location |
|-------------|----------|
| Finding persistence + alerts + risk scores | `packages/core/persistence.py` |
| Agent run history | `AgentRunLog` in `packages/core/models.py`, `log_agent_run()` |
| CVE poller + storage | `services/cve_poller/service.py`, `CVERecord` model |
| Insider / UEBA schema + persistence | `packages/core/insider_schema.py`, `upsert_insider_baseline()` |
| Structured specialist handlers | All 13 agents (mock mode) |
| Vector corpus embed | `services/vector-store/service.py`, `scripts/embed_corpus.py` |
| CVE poll API | `POST /api/v1/cve/poll` |

## Week 3 checklist

- [x] Findings persist to SQLite/Postgres after agent run
- [x] CVE poller stores records (`GET /api/v1/cve/recent`)
- [x] Agent run logs visible via API
- [x] Qdrant collections populated via `./scripts/embed-corpus.sh`
