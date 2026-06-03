#!/usr/bin/env bash
# Run the UniShield workflow orchestrator API locally (requires infra).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8001}"

# Ensure infra is up
if ! docker compose -f unishield/docker-compose.yml ps postgres 2>/dev/null | grep -q healthy; then
  echo "Postgres is not running. Starting infrastructure first..."
  "$ROOT/scripts/unishield-infra-up.sh"
fi

export PYTHONPATH="$ROOT"
export OPENCLAW_MOCK_MODE="${OPENCLAW_MOCK_MODE:-true}"
export REDIS_HOST="${REDIS_HOST:-localhost}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_PASSWORD="${REDIS_PASSWORD:-}"
export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export POSTGRES_DSN="${POSTGRES_DSN:-postgresql://unishield:unishield@localhost:5432/unishield}"

if [ -d "$ROOT/.venv" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

echo "Starting UniShield orchestrator on http://127.0.0.1:${PORT}"
echo "  PYTHONPATH=$PYTHONPATH"
echo "  POSTGRES_DSN=$POSTGRES_DSN"
echo ""
exec uvicorn unishield.api.main:app --host 0.0.0.0 --port "$PORT" --reload
