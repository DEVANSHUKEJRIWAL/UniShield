# OpenClaw Gateway Setup

UniShield runs SCR and orchestrator agents through a live OpenClaw gateway. Each agent loads its contract from `SKILL.md` and injects it as the OpenClaw `systemPrompt`.

## Agents

| Agent ID | Skill file |
|----------|------------|
| `unishield-scr` | `skills/unishield-scr/SKILL.md` |
| `unishield-orchestrator` | `skills/unishield-orchestrator/SKILL.md` |

## Quick setup

```bash
docker compose -p unishield-openclaw -f docker-compose.orchestrator.yml up -d openclaw
./scripts/check-openclaw.sh
./scripts/setup-openclaw-agents.sh
```

This starts the gateway (with `--bind lan` so Docker port forwarding works), verifies port `18789`, registers agents, and prints required environment variables.

### Troubleshooting: connection refused on 18789

If `docker compose up` reports **Started** but `nc -zv 127.0.0.1 18789` fails:

1. **Check container state and logs**
   ```bash
   ./scripts/check-openclaw.sh
   docker logs unishield-openclaw-openclaw-1
   ```
2. **Recreate with the fixed compose** (binds gateway to `0.0.0.0` inside the container):
   ```bash
   docker compose -p unishield-openclaw -f docker-compose.orchestrator.yml down openclaw
   docker compose -p unishield-openclaw -f docker-compose.orchestrator.yml up -d openclaw
   ```
3. **Wait for health** (~30s on first start), then:
   ```bash
   curl -s http://127.0.0.1:18789/healthz
   nc -zv 127.0.0.1 18789
   ```
4. **Work without a live gateway** (mock skill session):
   ```bash
   export OPENCLAW_MOCK_MODE=true
   export SCR_EXECUTION_MODE=skill
   ./scripts/run-orchestrator.sh
   ```

On macOS, `ss` is not installed by default — use `nc`, `lsof`, or `./scripts/check-openclaw.sh` instead.

## Required environment

```bash
export OPENCLAW_MOCK_MODE=false
export OPENCLAW_GATEWAY_WS_URL=ws://127.0.0.1:18789/
export OPENCLAW_API_KEY=your-gateway-key
export SCR_EXECUTION_MODE=skill          # skill-first SCR (Python tools only)
export ANTHROPIC_API_KEY=...             # Stage 7 enrichment (optional)
export NEO4J_PASSWORD=...                # Neo4j attack path (optional)
```

## Kafka event-driven mode (production)

```bash
export EVENT_DRIVEN_ORCHESTRATION=true   # agent.complete consumer drives workflow
export SCR_VIA_KAFKA=true                # SCR runs in worker via agent.execute.scr
./scripts/run-scr-worker.sh              # separate SCR Kafka worker
```

Flow:

1. Orchestrator publishes `agent.execute.scr` (when `SCR_VIA_KAFKA=true`)
2. SCR worker consumes and runs `SCRRunner`
3. Stage 10 publishes `agent.complete`
4. Orchestrator Kafka consumer calls `on_agent_complete`

## Human gate escalation

Paused workflows expire after `HUMAN_GATE_TIMEOUT_HOURS` (default 4). The `HumanGateWatcher` publishes `workflow.human_gate_escalated` with `notify: board`.

## HITL action execution

Approved write-scope actions (`POST /hitl/{action_id}/decide` with `accept`) run through `ActionExecutor` and emit `action.executed`.

## CI/CD triggers

```bash
curl -X POST http://localhost:8001/triggers/cicd/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "meridian",
    "repo_url": "https://github.com/org/repo",
    "repo_ref": "main",
    "diff_base": "abc123",
    "diff_head": "def456",
    "workflow_id": "incremental-pr-scan"
  }'
```

Scheduled scans: `POST /triggers/scheduled/scan` or enable `UNISHIELD_SCHEDULER_ENABLED=true`.
