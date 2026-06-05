#!/usr/bin/env bash
# Run UniShield locally without Docker (gateway :8000).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "==> Installing Python dependencies..."
pip install -e ".[dev]" -q 2>/dev/null || pip install -e . -q
pip install -r backend/requirements.txt -q 2>/dev/null || true

echo "==> Bootstrapping SQLite database + demo users..."
./scripts/seed-local.sh

echo ""
echo "==> Starting gateway on http://localhost:8000"
echo "    Demo login: analyst@meridian.com / analyst123"
echo ""
echo "In another terminal:"
echo "  ./scripts/run-orchestrator.sh   # orchestrator :8001"
echo "  cd frontend && npm run dev      # UI :3000"
echo ""
exec uvicorn gateway.main:app --reload --host 0.0.0.0 --port 8000
