#!/usr/bin/env bash
# Diagnose OpenClaw gateway Docker container and host port 18789.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.orchestrator.yml}"
COMPOSE_PROJECT="${COMPOSE_OPENCLAW_PROJECT:-unishield-openclaw}"
GATEWAY_PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
CONTAINER="${OPENCLAW_CONTAINER:-${COMPOSE_PROJECT}-openclaw-1}"
START_IF_DOWN="${START_IF_DOWN:-0}"

port_open() {
  (echo >/dev/tcp/127.0.0.1/"$1") >/dev/null 2>&1
}

echo "==> OpenClaw gateway check"
echo "    Project:  $COMPOSE_PROJECT"
echo "    Port:     $GATEWAY_PORT"
echo "    Container: $CONTAINER"
echo ""

if ! command -v docker >/dev/null 2>&1; then
  echo "FAIL  Docker CLI not found"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "FAIL  Docker daemon is not running"
  exit 1
fi
echo "OK    Docker is running"

echo ""
echo "--- Container status ---"
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  docker inspect "$CONTAINER" --format 'Status={{.State.Status}} ExitCode={{.State.ExitCode}} Health={{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}'
  docker ps -a --filter "name=^${CONTAINER}$" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
else
  echo "WARN  Container $CONTAINER not found"
  if [ "$START_IF_DOWN" = "1" ]; then
    echo "Starting OpenClaw via compose..."
    docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" up -d openclaw
  fi
fi

echo ""
echo "--- Recent logs (last 40 lines) ---"
CONFIG_ERROR=0
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  LOGS="$(docker logs --tail 40 "$CONTAINER" 2>&1 || true)"
  printf '%s\n' "$LOGS"
  if printf '%s\n' "$LOGS" | grep -qE 'Invalid config|agents\.defaults: Invalid input|Gateway failed to start|missing gateway\.mode|Gateway start blocked'; then
    CONFIG_ERROR=1
  fi
else
  echo "(no container logs)"
fi

if [ "$CONFIG_ERROR" = "1" ]; then
  echo ""
  echo "FAIL  OpenClaw config is invalid (see logs above)"
  echo ""
  echo "Quick fix (UniShield project config):"
  echo "  ./scripts/fix-openclaw-config.sh reset"
  echo ""
  echo "Or repair in place:"
  echo "  ./scripts/fix-openclaw-config.sh doctor"
  echo ""
  echo "If you mounted ~/.openclaw manually:"
  echo "  ./scripts/fix-openclaw-config.sh host"
fi

echo ""
echo "--- Host port $GATEWAY_PORT ---"
HEALTH_OK=0
if port_open "$GATEWAY_PORT"; then
  if curl -sf "http://127.0.0.1:${GATEWAY_PORT}/healthz" >/dev/null 2>&1; then
    echo "OK    Gateway healthy on 127.0.0.1:$GATEWAY_PORT"
    HEALTH_OK=1
  else
    echo "WARN  Port $GATEWAY_PORT is mapped but /healthz failed (gateway may be crash-looping)"
  fi
else
  echo "FAIL  Nothing listening on 127.0.0.1:$GATEWAY_PORT"
  echo ""
  echo "Common causes:"
  echo "  1. Gateway binds to 127.0.0.1 inside the container (fixed by OPENCLAW_GATEWAY_BIND=lan)"
  echo "  2. Container exited — inspect logs above"
  echo "  3. Invalid openclaw.json — run ./scripts/fix-openclaw-config.sh reset"
  echo "  4. Gateway still starting — wait ~30s and retry"
  echo ""
  echo "Fix and restart:"
  echo "  docker compose -p $COMPOSE_PROJECT -f $COMPOSE_FILE down openclaw"
  echo "  docker compose -p $COMPOSE_PROJECT -f $COMPOSE_FILE up -d openclaw"
  echo "  START_IF_DOWN=1 $ROOT/scripts/check-openclaw.sh"
fi

echo ""
echo "--- In-container health ---"
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  if docker exec "$CONTAINER" node -e \
    "fetch('http://127.0.0.1:${GATEWAY_PORT}/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" \
    >/dev/null 2>&1; then
    echo "OK    /healthz responds inside container"
    HEALTH_OK=1
  else
    echo "FAIL  /healthz not ready inside container yet"
  fi
else
  echo "SKIP  Container is not running"
fi

echo ""
echo "--- macOS checks (no ss required) ---"
echo "  nc -zv 127.0.0.1 $GATEWAY_PORT"
echo "  lsof -nP -iTCP:$GATEWAY_PORT -sTCP:LISTEN"
echo "  curl -s http://127.0.0.1:$GATEWAY_PORT/healthz"
echo ""
echo "UniShield live env:"
echo "  export OPENCLAW_MOCK_MODE=false"
echo "  export OPENCLAW_GATEWAY_WS_URL=ws://127.0.0.1:${GATEWAY_PORT}/"
echo "  export OPENCLAW_API_KEY=\${OPENCLAW_GATEWAY_TOKEN:-your-token}"

if [ "$CONFIG_ERROR" = "0" ] && [ "$HEALTH_OK" = "1" ]; then
  exit 0
fi
exit 1