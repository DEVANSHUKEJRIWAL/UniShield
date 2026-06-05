# UniShield — Orchestrator & Source Code Review

UniShield runs **security workflows** centered on the **source code review (SCR) agent**: connect a repo, trigger a scan, and review findings in the dashboard.

## What this repo contains

| Component | Path | Role |
|-----------|------|------|
| **Orchestrator** | `unishield/orchestrator/` | Workflow engine (OpenClaw + local Python runners) |
| **SCR pipeline** | `unishield/agents/scr/` | 10-stage scan: SAST, secrets, SBOM, dataflow, AI enrichment |
| **API gateway** | `services/api-gateway/` | Auth + BFF for frontend (`:8000`) |
| **Frontend** | `frontend/` | Security Workflows, Connected Repos, scan results UI |
| **Skills** | `skills/unishield-scr/` | Agent skill specification |

## Quick start (local)

```bash
cp .env.example .env
pip install -e ".[dev]"
pip install -r unishield/requirements.txt

# Infrastructure (Redis, Postgres on :5434, Kafka)
./scripts/unishield-infra-up.sh

# Orchestrator API (:8001)
./scripts/run-unishield-orchestrator.sh

# API gateway (:8000) — second terminal
./scripts/dev-local.sh

# Frontend (:3000) — third terminal
cd frontend && npm install && npm run dev
```

**Login:** `analyst@meridian.com` / `analyst123`

**SCR tools:** `./scripts/install-scr-tools.sh` (semgrep, gitleaks, syft, grype)

**Verify:** `./scripts/check-api.sh`

## Workflows

Trigger from **Security Workflows** or **Connected Repos** in the UI:

- **Code Review** (`code-review-only`) — full repo SCR + compliance mapping + report
- **Compliance Readiness** — SCR findings mapped to control frameworks
- **Incremental PR Scan** — diff-scoped review

## Architecture

```
Frontend (:3000)
    → API Gateway (:8000)  auth, /workflows, /repos
        → Orchestrator (:8001)  SCRRunner, CMARunner, ReportingRunner
            → Redis shared memory + Postgres snapshots
            → Subprocess scanners (Semgrep, Gitleaks, Syft, Grype, …)
```

See [docs/STRUCTURE.md](docs/STRUCTURE.md) for the full layout.

## Tests

```bash
pytest unishield/tests -v
cd frontend && npm run build
```

## Docker (minimal stack)

```bash
docker compose up -d postgres redis
docker compose --profile app up -d api-gateway frontend
# Run orchestrator separately on host :8001
```

Full OpenClaw stack: `unishield/docker-compose.yml`
