#!/usr/bin/env bash
# Diagnose UniShield orchestrator infrastructure connectivity.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== UniShield Orchestrator Doctor ==="
echo ""

# Docker
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Docker CLI not found — install Docker Desktop"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker is not running — start Docker Desktop, then retry"
  exit 1
fi
echo "✅ Docker is running"

check_port() {
  local port=$1
  if (echo >/dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1; then
    echo "✅ Port $port is open"
    return 0
  fi
  echo "❌ Port $port is closed (nothing listening)"
  return 1
}

echo ""
echo "--- Port checks ---"
check_port 6379 || true
check_port 9092 || true
PG5432=0; PG5434=0
check_port 5432 && PG5432=1 || true
check_port 5434 && PG5434=1 || true

echo ""
echo "--- Docker containers ---"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null | grep -E 'unishield|postgres|redis|redpanda|NAMES' || docker ps --format 'table {{.Names}}\t{{.Status}}'

echo ""
echo "--- Kafka broker (host clients need 127.0.0.1:9092, not kafka:9092) ---"
if docker ps --format '{{.Names}}' | grep -q kafka; then
  KAFKA_C=$(docker ps --format '{{.Names}}' | grep kafka | head -1)
  docker exec "$KAFKA_C" rpk cluster info 2>/dev/null | grep -E 'HOST|127.0.0.1|kafka' || true
  echo "  Host orchestrator: export KAFKA_BOOTSTRAP_SERVERS=localhost:9092"
  echo "  If broker HOST is 'kafka', recreate: docker compose -p unishield-openclaw -f docker-compose.orchestrator.yml up -d --force-recreate kafka"
fi

echo ""
echo "--- Recommended POSTGRES_DSN ---"
if [ "$PG5434" -eq 1 ]; then
  echo "  export POSTGRES_DSN=postgresql://unishield:unishield@localhost:5434/unishield"
  echo "  (unishield orchestrator infra on port 5434)"
elif [ "$PG5432" -eq 1 ]; then
  echo "  export POSTGRES_DSN=postgresql://unishield:password@localhost:5432/unishield"
  echo "  (main UniShield docker-compose postgres — password is 'password', not 'unishield')"
else
  echo "  No Postgres detected. Start infra:"
  echo "    ./scripts/unishield-infra-up.sh"
fi

echo ""
echo "--- Quick start ---"
echo "  ./scripts/unishield-infra-up.sh"
echo "  ./scripts/run-unishield-orchestrator.sh"
