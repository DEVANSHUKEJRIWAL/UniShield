#!/usr/bin/env bash
# Run UniShield in LIVE mode — real OpenClaw gateway + SCR/CMA/reporting runners.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8001}"
COMPOSE_INFRA="docker-compose.infra.yml"
COMPOSE_OPENCLAW_PROJECT="${COMPOSE_OPENCLAW_PROJECT:-unishield-openclaw}"

if [ -d "$ROOT/.venv" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

port_open() {
  (echo >/dev/tcp/127.0.0.1/"$1") >/dev/null 2>&1
}

echo "==> UniShield LIVE stack"
echo ""

# --- Infrastructure (Redis, Postgres:5434, Kafka) ---
if ! port_open 5434 || ! port_open 6379 || ! port_open 9092; then
  echo "Starting orchestrator infrastructure..."
  "$ROOT/scripts/infra-up.sh"
fi

export POSTGRES_DSN="${POSTGRES_DSN:-postgresql://unishield:unishield@localhost:5434/unishield}"
export REDIS_HOST="${REDIS_HOST:-localhost}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export PYTHONPATH="$ROOT"

# --- OpenClaw gateway ---
export OPENCLAW_MOCK_MODE="${OPENCLAW_MOCK_MODE:-false}"
export OPENCLAW_GATEWAY_WS_URL="${OPENCLAW_GATEWAY_WS_URL:-ws://127.0.0.1:18789/}"

if ! port_open 18789; then
  echo "Starting OpenClaw gateway (Docker)..."
  if docker info >/dev/null 2>&1; then
    docker compose -p "$COMPOSE_OPENCLAW_PROJECT" -f docker-compose.orchestrator.yml up -d openclaw
    echo "Waiting for OpenClaw on :18789 (gateway binds with --bind lan for Docker)..."
    for _ in $(seq 1 45); do
      port_open 18789 && break
      sleep 2
    done
    if ! port_open 18789; then
      echo "WARNING: OpenClaw port 18789 still closed — run: ./scripts/check-openclaw.sh"
    fi
  else
    echo "WARNING: Docker not available — start OpenClaw gateway manually on port 18789"
  fi
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
  echo ""
  echo "WARNING: No LLM API key set. SCR AI enrichment and reporting narratives will use templates."
  echo "  export ANTHROPIC_API_KEY=sk-ant-..."
  echo ""
fi

pip install -q -r backend/requirements.txt 2>/dev/null || true

if ! command -v gitleaks >/dev/null 2>&1 || ! command -v syft >/dev/null 2>&1 || ! command -v grype >/dev/null 2>&1; then
  echo "Installing SCR tools (gitleaks, syft, grype)..."
  bash "$ROOT/scripts/install-scr-tools.sh" || echo "WARNING: SCR tool install failed — scans will fail until tools are on PATH"
  export PATH="${HOME}/.local/bin:${PATH}"
fi

echo ""
echo "Configuration:"
echo "  Orchestrator:  http://127.0.0.1:${PORT}"
echo "  OpenClaw:      ${OPENCLAW_GATEWAY_WS_URL} (mock=${OPENCLAW_MOCK_MODE})"
echo "  Postgres:      ${POSTGRES_DSN}"
echo ""
echo "Verify after start:"
echo "  curl -s http://127.0.0.1:${PORT}/health | python3 -m json.tool"
echo ""
echo "In separate terminals (optional):"
echo "  ./scripts/run-scr-worker.sh           # Kafka SCR worker"
echo "  ./scripts/dev-local.sh                    # API gateway :8000"
echo "  cd frontend && npm run dev                # UI :3000"
echo ""

exec uvicorn backend.api.main:app --host 0.0.0.0 --port "$PORT"
