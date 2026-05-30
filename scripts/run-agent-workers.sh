#!/usr/bin/env bash
# Start Redis agent workers (Week 2 producer/consumer pattern)
set -euo pipefail
cd "$(dirname "$0")/.."

if ! docker compose ps redis 2>/dev/null | grep -q running; then
  echo "==> Starting Redis..."
  docker compose up -d redis 2>/dev/null || echo "Warning: start Redis manually (redis://localhost:6379)"
fi

echo "==> Starting agent workers (all specialists + orchestrator)..."
echo "    Requires: pip install -e . && REDIS_URL=redis://localhost:6379"
echo ""
exec python3 -m agents.worker --include-orchestrator --tenant "${TENANT_ID:-meridian-financial}"
