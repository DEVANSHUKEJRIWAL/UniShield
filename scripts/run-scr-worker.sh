#!/usr/bin/env bash
# Run the SCR Kafka worker (optional — orchestrator runs SCR inline by default).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -d "$ROOT/.venv" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

export PYTHONPATH="$ROOT"
export POSTGRES_DSN="${POSTGRES_DSN:-postgresql://unishield:unishield@localhost:5434/unishield}"
export REDIS_HOST="${REDIS_HOST:-localhost}"
export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export OPENCLAW_MOCK_MODE="${OPENCLAW_MOCK_MODE:-false}"
export OPENCLAW_GATEWAY_WS_URL="${OPENCLAW_GATEWAY_WS_URL:-ws://127.0.0.1:18789/}"

pip install -q -r backend/requirements.txt 2>/dev/null || true

echo "Starting SCR worker (Kafka topic: agent.execute.scr)"
exec python3 -m backend.scr.worker
