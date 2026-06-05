# Repository structure

UniShield is organized around **orchestrator workflows** and the **source code review (SCR) agent pipeline**.

```
/
├── unishield/                 # Orchestrator + SCR engine (canonical backend)
│   ├── orchestrator/          # Workflow engine, routing, state
│   ├── agents/
│   │   ├── scr/               # 10-stage source code review pipeline
│   │   ├── cma/               # Compliance mapping (post-SCR)
│   │   └── reporting/         # Executive report assembly
│   ├── api/                   # Orchestrator FastAPI (:8001)
│   ├── connectors/            # GitHub / GitLab / Bitbucket repo registry
│   ├── attack_path/           # Attack path analysis (optional Neo4j)
│   ├── memory/                # Shared + personal memory (Redis)
│   ├── infrastructure/        # Kafka, Postgres, ModelRouter
│   ├── tests/                 # Orchestrator + SCR test suite
│   └── docker-compose*.yml    # OpenClaw + orchestrator stack
│
├── services/api-gateway/      # Frontend BFF (:8000) — auth, workflows, repos
├── packages/
│   ├── core/                  # Auth, DB, seed, config
│   └── shared-types/          # RBAC roles, agent name constants
│
├── frontend/                  # Next.js UI (design unchanged)
├── skills/
│   ├── unishield-scr/         # SCR agent skill spec
│   └── unishield-orchestrator/
├── openclaw_sdk/              # OpenClaw gateway client stub
└── scripts/                   # Local dev + orchestrator runners
```

## Runtime services

| Service | Port | Purpose |
|---------|------|---------|
| API gateway | 8000 | JWT auth, proxies `/workflows` and `/repos` to orchestrator |
| Orchestrator | 8001 | Runs SCR/CMA/reporting workflow steps |
| Frontend | 3000 | Security Workflows, Connected Repos, scan results UI |
| Redis | 6379 | Workflow state + shared memory |
| Postgres | 5432 / 5434 | Repo connections + workflow snapshots |

## Primary workflows

| Workflow ID | Steps |
|-------------|-------|
| `code-review-only` | SCR → CMA → Reporting |
| `compliance-readiness` | SCR → CMA → Reporting |
| `incremental-pr-scan` | SCR → Reporting |

## Quick start

```bash
./scripts/unishield-infra-up.sh          # Redis, Postgres, Kafka
./scripts/run-unishield-orchestrator.sh  # :8001
./scripts/dev-local.sh                   # API gateway :8000
cd frontend && npm run dev               # UI :3000
```

Login: `analyst@meridian.com` / `analyst123`

Install SCR scanners: `./scripts/install-scr-tools.sh`
