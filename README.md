# UniShield

**UniShield** is an AI-native cybersecurity defense platform built by Uniqus. It delivers continuous threat detection, compliance automation, and risk intelligence through self-managed Anthropic Claude agents orchestrated via the internal OpenClaw framework.

## Quick Start

### Prerequisites

- Docker >= 24.0, Docker Compose >= 2.20
- Python >= 3.11, Node >= 20 LTS
- k3d >= 5.6, kubectl >= 1.29, helm >= 3.14 (optional for K8s)
- terraform >= 1.7, vault >= 1.15 (optional)

### Bootstrap

```bash
# 1. Copy environment template
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, NEO4J_PASSWORD, VAULT_DEV_ROOT_TOKEN

# 2. Start infrastructure
docker compose up -d postgres timescaledb neo4j redis qdrant elasticsearch vault

# 3. Bootstrap Vault
./scripts/vault-init.sh

# 4. Run KG migrations
./scripts/migrate-kg.sh

# 5. Embed threat intel corpus
./scripts/embed-corpus.sh

# 6. (Optional) Start k3d cluster
k3d cluster create unishield-local --config infra/k3d-config.yml

# 7. Seed mock data
./scripts/seed-local.sh

# 8. Install Python dependencies
pip install -e ".[dev]"

# 9. Start API gateway
uvicorn services.api_gateway.main:app --reload --port 8000

# 10. Start frontend
cd frontend && npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000) for the SOC dashboard.

## Monorepo Structure

```
unishield/
├── agents/           # 13 AI agents + OpenClaw runtime
├── services/         # FastAPI microservices
├── frontend/         # Next.js 14 App Router (Obsidian theme)
├── packages/         # Shared schemas and types
├── infra/            # K8s, Terraform, Helm, Vault
├── tests/            # Unit, integration, e2e, security
├── scripts/          # Bootstrap and migration scripts
└── docs/             # Architecture and runbooks
```

## Technology Stack

| Layer | Technology |
|---|---|
| Agents | OpenClaw (Python), Anthropic Claude, LangGraph |
| Backend | FastAPI, PostgreSQL 16, Neo4j 5, Qdrant, Redis 7 |
| Frontend | Next.js 14, Tailwind CSS, Zustand |
| Infra | Docker Compose, Kubernetes, Terraform, Helm |

## Development

```bash
# Lint
ruff check agents services packages
cd frontend && npm run lint

# Test
pytest tests/unit -v
cd frontend && npm run type-check

# Agent API (Phase 1 bridge)
curl http://localhost:8000/agent/status
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"dark-web-agent","tenant_id":"meridian-financial","input":{}}'
```

## Team

| Role | Colour | Responsibility |
|---|---|---|
| Lead AI | `#492079` | OpenClaw, agents, orchestrator |
| Systems | `#2563EB` | Infrastructure, backend, CI/CD |
| Sec1 | `#D97706` | Data sources, connectors, IAM |
| Sec2 | `#C53030` | Testing, adversarial validation |
| UX | `#059669` | Frontend, design system |

## License

Proprietary — Uniqus. All rights reserved.
