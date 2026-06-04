#!/usr/bin/env bash
# Run the UniShield workflow orchestrator API locally (requires infra).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8001}"
COMPOSE_FILE="unishield/docker-compose.infra.yml"

if [ -d "$ROOT/.venv" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

port_open() {
  (echo >/dev/tcp/127.0.0.1/"$1") >/dev/null 2>&1
}

# Auto-detect Postgres or start infra
if port_open 5434; then
  export POSTGRES_DSN="${POSTGRES_DSN:-postgresql://unishield:unishield@localhost:5434/unishield}"
elif port_open 5432; then
  export POSTGRES_DSN="${POSTGRES_DSN:-postgresql://unishield:password@localhost:5432/unishield}"
else
  echo "Postgres not detected on 5434 or 5432. Starting orchestrator infrastructure..."
  "$ROOT/scripts/unishield-infra-up.sh"
  export POSTGRES_DSN="${POSTGRES_DSN:-postgresql://unishield:unishield@localhost:5434/unishield}"
fi

if ! port_open 6379 || ! port_open 9092; then
  echo "Redis or Kafka not running — starting infrastructure..."
  docker compose -f "$COMPOSE_FILE" up -d redis kafka 2>/dev/null || "$ROOT/scripts/unishield-infra-up.sh"
fi

export PYTHONPATH="$ROOT"
export OPENCLAW_MOCK_MODE="${OPENCLAW_MOCK_MODE:-true}"
export REDIS_HOST="${REDIS_HOST:-localhost}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_PASSWORD="${REDIS_PASSWORD:-}"
export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"

echo "Starting UniShield orchestrator on http://127.0.0.1:${PORT}"
echo "  PYTHONPATH=$PYTHONPATH"
echo "  POSTGRES_DSN=$POSTGRES_DSN"
echo "  OPENCLAW_MOCK_MODE=$OPENCLAW_MOCK_MODE"
echo "  After start, verify: curl -s http://127.0.0.1:${PORT}/health"
echo ""
exec uvicorn unishield.api.main:app --host 0.0.0.0 --port "$PORT" --reload
