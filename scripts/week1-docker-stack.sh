#!/usr/bin/env bash
# Week 1 canonical local stack: PostgreSQL + Redis + Qdrant
# Usage: ./scripts/week1-docker-stack.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Week 1 stack: starting PostgreSQL, Redis, Qdrant..."
docker compose up -d postgres redis qdrant

echo ""
echo "==> Waiting for services to be healthy..."
sleep 5

for i in {1..30}; do
  if docker compose exec -T postgres pg_isready -U unishield &>/dev/null; then
    echo "    PostgreSQL: ready"
    break
  fi
  sleep 2
done

if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
  echo "    Redis: ready"
else
  echo "    Redis: starting (may need a few more seconds)"
fi

echo ""
echo "==> Configure .env for Week 1 canonical stack:"
echo ""
echo "  UNISHIELD_USE_POSTGRES=1"
echo "  POSTGRES_URI=postgresql+asyncpg://unishield:password@localhost:5432/unishield"
echo "  REDIS_URL=redis://localhost:6379"
echo "  QDRANT_URL=http://localhost:6333"
echo ""
echo "Then run:"
echo "  pip install -e \".[dev]\""
echo "  ./scripts/seed-local.sh"
echo "  uvicorn services.api_gateway.main:app --reload --port 8000"
echo ""
echo "Verify: curl http://localhost:8000/api/v1/dev/status"
echo ""
echo "Full guide: docs/week1/local-dev-stack.md"
