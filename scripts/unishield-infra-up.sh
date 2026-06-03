#!/usr/bin/env bash
# Start Redis, Postgres, and Kafka for local UniShield orchestrator development.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="unishield/docker-compose.infra.yml"

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker is not running. Start Docker Desktop first."
  exit 1
fi

echo "Starting UniShield orchestrator infrastructure..."
echo "  compose: $COMPOSE_FILE"
echo "  Postgres host port: 5434 (avoids conflict with main stack on 5432)"
echo ""

docker compose -f "$COMPOSE_FILE" up -d

echo "Waiting for services to become healthy..."
for i in $(seq 1 45); do
  REDIS_OK=$(docker compose -f "$COMPOSE_FILE" ps redis 2>/dev/null | grep -c healthy || true)
  PG_OK=$(docker compose -f "$COMPOSE_FILE" ps postgres 2>/dev/null | grep -c healthy || true)
  KAFKA_OK=$(docker compose -f "$COMPOSE_FILE" ps kafka 2>/dev/null | grep -c healthy || true)
  if [ "$REDIS_OK" -ge 1 ] && [ "$PG_OK" -ge 1 ] && [ "$KAFKA_OK" -ge 1 ]; then
    echo ""
    echo "✅ All infrastructure services are healthy."
    echo ""
    echo "Use these environment variables:"
    echo "  export POSTGRES_DSN=postgresql://unishield:unishield@localhost:5434/unishield"
    echo "  export REDIS_HOST=localhost"
    echo "  export KAFKA_BOOTSTRAP_SERVERS=localhost:9092"
    echo "  export OPENCLAW_MOCK_MODE=true"
    echo "  export PYTHONPATH=."
    echo ""
    echo "Then run:"
    echo "  ./scripts/run-unishield-orchestrator.sh"
    exit 0
  fi
  sleep 2
done

echo ""
echo "ERROR: Infrastructure did not become healthy in time."
docker compose -f "$COMPOSE_FILE" ps
echo ""
echo "Logs:"
docker compose -f "$COMPOSE_FILE" logs --tail=20 postgres
exit 1
