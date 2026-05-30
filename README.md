# UniShield

**UniShield** is a full-stack AI-native cybersecurity defense platform built by Uniqus. It delivers continuous threat detection, compliance automation, and risk intelligence through 13 Anthropic Claude agents orchestrated via the OpenClaw framework.

## Platform Capabilities

| Layer | Components |
|---|---|
| **Agents (13)** | Orchestrator, Dark Web, Source Code Review, Insider Threat, Threat Intel, Vulnerability, Incident Response, SIEM Analysis, Network Security, Compliance, Forensics, Graph Query, Reporting |
| **Backend** | FastAPI gateway with JWT auth, RBAC, WebSocket/SSE streaming, 30+ REST endpoints |
| **Frontend** | Next.js 14 SOC dashboard, executive view, alerts, investigation, compliance, reporting, network, cloud, HITL |
| **Data** | PostgreSQL, Neo4j, Qdrant, Redis Streams, TimescaleDB, Elasticsearch |
| **Integrations** | 33 connectors (Splunk, CrowdStrike, Okta, GitHub, VirusTotal, Shodan, NVD, etc.) |
| **Infra** | Docker Compose, Kubernetes, Helm, Terraform (local + AWS) |

## Quick Start

```bash
cp .env.example .env

# Start infrastructure
docker compose up -d postgres timescaledb neo4j redis qdrant elasticsearch vault

# Bootstrap
./scripts/vault-init.sh
./scripts/migrate-kg.sh
./scripts/embed-corpus.sh
pip install -e ".[dev]"
./scripts/seed-local.sh

# Start API
uvicorn services.api_gateway.main:app --reload --port 8000

# Start frontend
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000** → Login with `analyst@meridian.com` / `analyst123`

## Demo Accounts

| Email | Password | Role |
|---|---|---|
| admin@unishield.io | admin123 | PLATFORM_ADMIN |
| ciso@meridian.com | ciso123 | CISO |
| analyst@meridian.com | analyst123 | SOC_ANALYST |
| board@meridian.com | board123 | READONLY_BOARD |
| devsecops@meridian.com | devsec123 | DEVSECOPS |
| grc@meridian.com | grc123 | GRC |

## API Endpoints

Full OpenAPI docs at **http://localhost:8000/docs**

```
POST /api/v1/auth/login          JWT authentication
GET  /api/v1/dashboard/{id}      SOC dashboard KPIs
GET  /api/v1/alerts/{id}         Alert management
POST /api/v1/agents/run          Trigger agents
GET  /api/v1/hitl/queue/{id}     HITL work queue
GET  /api/v1/risk/score/{id}     12-dimension risk scoring
GET  /api/v1/compliance/{id}/{fw}  Control coverage
GET  /api/v1/kg/blast-radius/{id}  Knowledge graph
WS   /api/v1/ws/{id}             Real-time events
POST /agent/run                  Agent SSE bridge
```

## Testing

```bash
pytest tests/ -v                  # 17+ tests
cd frontend && npm run type-check
```

## Architecture

```
Agents (OpenClaw + LangGraph)
    ↕ Redis Streams
API Gateway (FastAPI + JWT/RBAC)
    ↕
PostgreSQL | Neo4j | Qdrant | Redis | ES
    ↕
Next.js Frontend (Obsidian theme)
```

## License

Proprietary — Uniqus. All rights reserved.
