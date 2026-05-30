#!/usr/bin/env bash
# Run UniShield locally without Docker
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "==> Installing Python dependencies..."
pip install -e ".[dev]" -q 2>/dev/null || pip install -e . -q

echo "==> Bootstrapping SQLite database + demo users..."
./scripts/seed-local.sh

echo ""
echo "==> Starting API on http://localhost:8000"
echo "    Demo login: analyst@meridian.com / analyst123"
echo ""
echo "In another terminal:"
echo "  cd frontend && npm install && npm run dev"
echo ""
exec uvicorn services.api_gateway.main:app --reload --host 0.0.0.0 --port 8000
