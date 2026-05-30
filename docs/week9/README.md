# Week 9 — Containerisation & K8s

## Deliverables

- [x] Per-agent worker containers (`docker compose --profile agents`)
- [x] Agent worker Dockerfile (`services/agent-worker/Dockerfile`)
- [x] K8s agent deployment + HPA + securityContext (`infra/k8s/deployments/agent-siem.yaml`)
- [x] Vault secret loader (`packages/core/secrets.py`)
- [x] Deployment status page (`/deployment`, `/api/v1/deployment/status`)
- [x] API healthchecks + read-only root FS in compose
- [x] Prometheus + Grafana in compose

## Run

```bash
docker compose --profile app --profile agents up -d
./scripts/vault-init.sh
```
