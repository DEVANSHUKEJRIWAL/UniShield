#!/usr/bin/env bash
# Start orchestrator infrastructure (Redis, Postgres :5434, Kafka, Neo4j).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
docker compose -f docker-compose.infra.yml up -d
echo "Infra ready — Postgres :5434, Redis :6379, Kafka :9092, Neo4j :7474"
