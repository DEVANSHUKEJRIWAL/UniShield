# Week 1 Local Dev Stack

Week 1 deliverable: **running local dev stack** with FastAPI + PostgreSQL + Redis + frontend scaffold.

UniShield supports two paths:

| Path | When to use |
|------|-------------|
| **Week 1 canonical (Docker)** | Team alignment, Postgres + Redis + Qdrant as spec |
| **Quick start (SQLite)** | No Docker installed — see root README |

---

## Option A — Week 1 canonical stack (recommended)

### Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 20+

### 1. Start infrastructure

```bash
./scripts/week1-docker-stack.sh
```

This starts **PostgreSQL**, **Redis**, and **Qdrant** (Week 1 minimum).

### 2. Configure environment

```bash
cp .env.example .env
```

Ensure these are set:

```env
UNISHIELD_USE_POSTGRES=1
POSTGRES_URI=postgresql+asyncpg://unishield:password@localhost:5432/unishield
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
```

### 3. Install and seed

```bash
pip install -e ".[dev]"
./scripts/seed-local.sh
```

### 4. Start API

```bash
uvicorn services.api_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Start frontend

```bash
cd frontend && npm install && npm run dev
```

### 6. Verify

| Check | Command / URL |
|-------|----------------|
| API health | `curl http://localhost:8000/api/v1/health` |
| Week 1 status | `curl http://localhost:8000/api/v1/dev/status` |
| Login | http://localhost:3000/login — `analyst@meridian.com` / `analyst123` |
| OpenAPI | http://localhost:8000/docs |

Expected `dev/status`:

```json
{
  "database": "postgresql",
  "week1": {
    "week1_stack_postgres": true,
    "week1_stack_redis_url_set": true
  }
}
```

---

## Option B — Quick start (SQLite, no Docker)

```bash
cp .env.example .env
pip install -e ".[dev]"
./scripts/dev-local.sh
cd frontend && npm install && npm run dev
```

SQLite is fine for UI/API development. Switch to Option A before Week 3 agent persistence work.

---

## Services matrix

| Service | Week 1 | Port | Purpose |
|---------|--------|------|---------|
| PostgreSQL | **Required** | 5432 | Users, findings, alerts, agent state |
| Redis | **Required** | 6379 | Agent message bus, HITL |
| Qdrant | **Required** | 6333 | Vector store (Week 3 corpus) |
| FastAPI | **Required** | 8000 | API gateway |
| Next.js | **Required** | 3000 | Frontend scaffold |
| Neo4j | Week 7 | 7687 | Knowledge graph |
| Elasticsearch | Week 5 | 9200 | Search |
| TimescaleDB | Week 7 | 5433 | Metrics |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Login 401 | `curl -X POST http://localhost:8000/api/v1/dev/fix-login` |
| Postgres connection refused | `docker compose up -d postgres` |
| Redis connection refused | `docker compose up -d redis` |
| Agent run fails | Ensure Redis is running |
| Wrong database mode | Check `UNISHIELD_USE_POSTGRES=1` in `.env` |

---

## Stop stack

```bash
docker compose stop postgres redis qdrant
```
