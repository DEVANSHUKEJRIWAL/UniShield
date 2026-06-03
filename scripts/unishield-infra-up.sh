#!/usr/bin/env bash
# Start Redis, Postgres, and Kafka for local UniShield orchestrator development.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Starting UniShield infrastructure (redis, postgres, kafka)..."
docker compose -f unishield/docker-compose.yml up -d redis postgres kafka

echo "Waiting for services to become healthy..."
for i in $(seq 1 30); do
  REDIS_OK=$(docker compose -f unishield/docker-compose.yml ps redis 2>/dev/null | grep -c healthy || true)
  PG_OK=$(docker compose -f unishield/docker-compose.yml ps postgres 2>/dev/null | grep -c healthy || true)
  KAFKA_OK=$(docker compose -f unishield/docker-compose.yml ps kafka 2>/dev/null | grep -c healthy || true)
  if [ "$REDIS_OK" -ge 1 ] && [ "$PG_OK" -ge 1 ] && [ "$KAFKA_OK" -ge 1 ]; then
    echo "All infrastructure services are healthy."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "Timed out waiting for infrastructure. Check: docker compose -f unishield/docker-compose.yml ps"
    exit 1
  fi
  sleep 2
done

echo ""
echo "Infrastructure ready:"
echo "  Redis:    localhost:6379"
echo "  Postgres: localhost:5432 (user/pass/db: unishield)"
echo "  Kafka:    localhost:9092"
echo ""
echo "Run the orchestrator API:"
echo "  ./scripts/run-unishield-orchestrator.sh"
