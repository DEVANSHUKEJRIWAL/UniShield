# Repository layout

```
/
├── backend/                 # Orchestrator engine + SCR pipeline
│   ├── orchestrator/        # Workflow engine, routing, state
│   ├── scr/                 # 10-stage source code review
│   ├── cma/                 # Compliance mapping (post-SCR)
│   ├── reporting/           # Executive report assembly
│   ├── api/                 # Orchestrator HTTP API (:8001)
│   ├── connectors/          # GitHub / GitLab / Bitbucket repos
│   ├── attack_path/         # Attack path analysis
│   ├── memory/              # Redis shared + personal memory
│   ├── infrastructure/      # Kafka, Postgres, ModelRouter
│   ├── config/              # Settings
│   └── schemas/             # Workflow + agent contracts
│
├── gateway/                 # UI API (:8000) — auth + workflow/repo proxy
├── core/                    # Shared auth, database, seed
├── frontend/                # Next.js UI (unchanged design)
├── tests/                   # Backend test suite
├── skills/                  # Agent skill specs (SCR, orchestrator)
├── openclaw_sdk/            # OpenClaw gateway client
└── scripts/                 # Local dev helpers
```

## Services

| Service | Port | Module |
|---------|------|--------|
| Gateway | 8000 | `gateway.main:app` |
| Orchestrator | 8001 | `backend.api.main:app` |
| Frontend | 3000 | `frontend/` |

## Workflows

| ID | Pipeline |
|----|----------|
| `code-review-only` | SCR → CMA → Reporting |
| `compliance-readiness` | SCR → CMA → Reporting |
| `incremental-pr-scan` | SCR → Reporting |

## Quick start

```bash
./scripts/infra-up.sh
./scripts/run-orchestrator.sh    # terminal 1 — :8001
./scripts/dev-local.sh           # terminal 2 — :8000
cd frontend && npm run dev       # terminal 3 — :3000
```

Login: `analyst@meridian.com` / `analyst123`

Install SCR scanners: `./scripts/install-scr-tools.sh`
