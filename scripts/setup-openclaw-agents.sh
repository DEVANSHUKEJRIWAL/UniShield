#!/usr/bin/env bash
# Register UniShield SCR + orchestrator agents with OpenClaw gateway (SKILL.md mounted).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCLAW_GATEWAY_URL="${OPENCLAW_GATEWAY_URL:-http://127.0.0.1:18789}"
OPENCLAW_API_KEY="${OPENCLAW_API_KEY:-}"

SCR_SKILL="$ROOT/skills/unishield-scr/SKILL.md"
ORCH_SKILL="$ROOT/skills/unishield-orchestrator/SKILL.md"

if [[ ! -f "$SCR_SKILL" || ! -f "$ORCH_SKILL" ]]; then
  echo "Missing SKILL.md files under $ROOT/skills/" >&2
  exit 1
fi

echo "==> UniShield OpenClaw agent registration"
echo "    Gateway: $OPENCLAW_GATEWAY_URL"
echo "    SCR skill: $SCR_SKILL"
echo "    Orchestrator skill: $ORCH_SKILL"

register_agent() {
  local agent_id="$1"
  local skill_path="$2"
  local payload
  payload=$(python3 - <<PY
import json, pathlib
skill = pathlib.Path("$skill_path").read_text(encoding="utf-8")
print(json.dumps({
    "agent_id": "$agent_id",
    "system_prompt": skill,
    "skills": [{"name": "$agent_id", "path": "$skill_path"}],
}))
PY
)
  if command -v curl >/dev/null 2>&1; then
    curl -sf -X POST "$OPENCLAW_GATEWAY_URL/api/v1/agents/register" \
      -H "Content-Type: application/json" \
      ${OPENCLAW_API_KEY:+-H "Authorization: Bearer $OPENCLAW_API_KEY"} \
      -d "$payload" \
      && echo "Registered $agent_id" \
      || echo "WARN: gateway register endpoint unavailable for $agent_id — mount SKILL.md manually"
  else
    echo "curl not found — mount skills manually:"
    echo "  $agent_id -> $skill_path"
  fi
}

register_agent "unishield-scr" "$SCR_SKILL"
register_agent "unishield-orchestrator" "$ORCH_SKILL"

cat <<EOF

Live run environment:
  export OPENCLAW_MOCK_MODE=false
  export OPENCLAW_GATEWAY_WS_URL=ws://127.0.0.1:18789/
  export OPENCLAW_API_KEY=\${OPENCLAW_API_KEY:-your-key}
  export SCR_EXECUTION_MODE=skill
  export EVENT_DRIVEN_ORCHESTRATION=true   # optional Kafka orchestration
  export SCR_VIA_KAFKA=true                # optional SCR worker
  export ANTHROPIC_API_KEY=...             # Stage 7 AI enrichment
  export NEO4J_PASSWORD=...                # attack path graph persistence

Start stack:
  ./scripts/infra-up.sh
  ./scripts/run-orchestrator.sh
  ./scripts/run-scr-worker.sh              # when SCR_VIA_KAFKA=true
EOF
