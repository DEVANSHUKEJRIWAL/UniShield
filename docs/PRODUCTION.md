# UniShield Production Deployment

This guide describes the production-hardened path for UniShield using Postgres, Redis, TimescaleDB metrics, background workers, and Kubernetes/Helm.

## Architecture overview

```mermaid
flowchart LR
  subgraph ingress [Ingress]
    FE[Next.js Frontend]
    API[API Gateway]
  end
  subgraph data [Data plane]
    PG[(Postgres)]
    TS[(TimescaleDB)]
    RD[(Redis)]
  end
  subgraph workers [Workers]
    AG[Agent workers]
    CW[Connector worker]
    CVE[CVE poller]
  end
  FE --> API
  API --> PG
  API --> TS
  API --> RD
  AG --> API
  CW --> API
```

## Prerequisites

- Kubernetes 1.28+ (EKS, GKE, or AKS)
- Helm 3.12+
- Managed Postgres 15+ (primary app DB)
- TimescaleDB (metrics hypertables — can be same cluster with extension)
- Redis 7+ (HITL queue, pub/sub)
- HashiCorp Vault or cloud secret manager

## Secrets (required)

Store these in Vault / K8s secrets — never commit to git:

| Secret | Purpose |
|--------|---------|
| `DATABASE_URL` | Async Postgres URI for SQLAlchemy |
| `TIMESCALE_URI` | Timescale connection for KPI sparklines |
| `REDIS_URL` | HITL queue + WebSocket fan-out |
| `JWT_SECRET` | Auth token signing |
| `ANTHROPIC_API_KEY` | Live agent orchestration (optional — mock without) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | GuardDuty CSPM connector |
| `VAULT_TOKEN` | Runtime secret bootstrap |

Bootstrap at startup is handled by `packages/core/secrets.py` and `bootstrap_secrets_into_settings()`.

## Environment variables

```bash
# Core
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/unishield
TIMESCALE_URI=postgresql+asyncpg://user:pass@timescale:5432/metrics
REDIS_URL=redis://redis:6379/0
JWT_SECRET=<random-256-bit>
FRONTEND_URL=https://app.example.com

# Workers
ENABLE_CONNECTOR_INGEST=1
ENABLE_CVE_POLLER=1
UNISHIELD_TENANT_ID=meridian-financial

# Optional integrations
AWS_REGION=us-east-1
ELASTICSEARCH_URL=http://elasticsearch:9200
```

## Database migration

1. Provision Postgres and run Alembic migrations (if present) or allow bootstrap on first boot for greenfield.
2. Enable Timescale extension and let the API create hypertables via `ensure_metrics_schema()` on startup.
3. Verify: `GET /api/v1/health` returns `healthy`.

## Helm deploy

Chart location: `infra/helm/unishield/`

```bash
helm upgrade --install unishield ./infra/helm/unishield \
  -f ./infra/helm/unishield/values.local.yml \
  --set image.tag=latest \
  --namespace unishield --create-namespace
```

Production overrides:

- Set API deployment `replicas` ≥ 2
- Configure ingress TLS (`templates/ingress.yaml`)
- Point probes at `/api/v1/health`
- Mount secrets as `envFrom` secretRef

## Worker scaling

### Agent workers

```bash
./scripts/run-agent-workers.sh
```

In K8s, deploy a Deployment with multiple replicas or a Job per agent type. Workers heartbeat as `listening` and appear **LIVE** in the dashboard.

### Connector worker

Started when `ENABLE_CONNECTOR_INGEST=1`. Ingests Splunk, QRadar, GuardDuty CSPM on interval.

Manual CSPM scan: `POST /api/v1/cloud/cspm/scan`

## Redis and HITL

Redis backs the HITL queue. Without Redis, the API falls back to DB-only HITL.

Production: run Redis with persistence (AOF) and set `REDIS_URL`.

## Frontend

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_URL=https://api.example.com npm run build
npm run start
```

## Health and observability

- Liveness: `GET /api/v1/health`
- Metrics: `GET /metrics` (Prometheus)
- KPI sparklines: `GET /api/v1/dashboard/{tenant}/kpi-sparklines?range=7d`

## Smoke test checklist

1. Login as analyst (replace with SSO in prod)
2. Dashboard loads KPI sparklines and threat geo map
3. Priority queue shows BFSI-tagged items first
4. Incident modal Acknowledge / Assign calls alerts API
5. Cloud page Run CSPM Scan persists findings
6. Search `CVE-2024-1234` routes to compliance entity

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| KPI sparklines flat | Check `TIMESCALE_URI`; DB fallback still works |
| Agents IDLE | Start worker processes |
| HITL queue empty with Redis down | Expected — DB fallback mode |
| CSPM mock findings only | Set AWS credentials for live GuardDuty |
