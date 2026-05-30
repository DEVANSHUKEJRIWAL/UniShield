# Week 1 — Foundation Deliverables

Week 1 establishes architecture alignment, the agent roster, orchestrator design, local dev stack, data-source shortlist, output validation criteria, UI wireframes, and team rituals.

## Documents in this folder

| Document | Week 1 output |
|----------|----------------|
| [agent-roster.md](./agent-roster.md) | Name, role, input/output schema, tool list per agent |
| [orchestrator-design.md](./orchestrator-design.md) | Routing logic, escalation paths, parallelism model |
| [agent-output-validation.md](./agent-output-validation.md) | Valid/safe agent response criteria |
| [api-keys-setup.md](./api-keys-setup.md) | Acquire and configure VirusTotal, Shodan, NVD, MITRE, OSINT |
| [local-dev-stack.md](./local-dev-stack.md) | Canonical Week 1 stack: FastAPI + PostgreSQL + Redis + frontend |
| [sprint-rituals.md](./sprint-rituals.md) | Standups, PR review, definition of done |
| [ui-wireframes.md](./ui-wireframes.md) | 6–8 screens for agent monitoring and alerts |
| [agent-roster.json](./agent-roster.json) | Machine-readable roster for tooling |

## Quick verification

```bash
# Week 1 Docker stack (Postgres + Redis + Qdrant)
./scripts/week1-docker-stack.sh

# Check integration + login readiness
curl -s http://localhost:8000/api/v1/dev/status | python3 -m json.tool
```

## Week 1 checklist

- [x] Agent roster + orchestrator design documented
- [x] Local stack scripts (`dev-local.sh`, `week1-docker-stack.sh`)
- [x] API keys documented in [api-keys-setup.md](./api-keys-setup.md)
- [x] MITRE ATT&CK access confirmed (STIX/TAXII — no key required)
- [x] `OSINT_FEED_URLS` supported in config (set in `.env` for live feeds)
- [x] UI wireframes in [ui-wireframes.md](./ui-wireframes.md)
- [x] Sprint rituals in [sprint-rituals.md](./sprint-rituals.md)
- [x] `GET /api/v1/dev/status` returns `week1` readiness block
