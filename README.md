# UniShield — Orchestrator & Source Code Review

Security workflows centered on the **SCR (source code review) agent**: connect a repo, run a scan, review findings in the UI.

## Repository layout

| Directory | Purpose |
|-----------|---------|
| `backend/` | Orchestrator + SCR/CMA/reporting pipeline |
| `gateway/` | Auth and UI API (proxies to orchestrator) |
| `core/` | Shared database and authentication |
| `frontend/` | Next.js dashboard |
| `tests/` | Test suite |

See [docs/STRUCTURE.md](docs/STRUCTURE.md) for the full tree.

## Quick start

```bash
cp .env.example .env
pip install -e ".[dev]"
pip install -r backend/requirements.txt

./scripts/infra-up.sh              # Redis, Postgres :5434, Kafka
./scripts/run-orchestrator.sh      # :8001 — terminal 1
./scripts/dev-local.sh             # :8000 — terminal 2
cd frontend && npm install && npm run dev   # :3000 — terminal 3
```

**Login:** `analyst@meridian.com` / `analyst123`

**SCR tools:** `./scripts/install-scr-tools.sh`

**Verify:** `./scripts/check-api.sh`

## Architecture

```
Frontend (:3000)
  → Gateway (:8000)     auth, /api/v1/workflows, /api/v1/repos
    → Orchestrator (:8001)   SCRRunner → scanners → shared memory
```

## Workflows

- **Code Review** (`code-review-only`) — full repo scan + compliance + report
- **Compliance Readiness** — SCR mapped to control frameworks
- **Incremental PR Scan** — diff-scoped review

## Tests

```bash
pytest tests openclaw_sdk/tests -v
cd frontend && npm run build
```
