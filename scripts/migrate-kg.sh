#!/usr/bin/env bash
# Run Neo4j Cypher migrations for knowledge graph schema
set -euo pipefail

NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"
MIGRATIONS_DIR="$(dirname "$0")/../packages/kg-schema/migrations"

echo "==> Running KG migrations from ${MIGRATIONS_DIR}..."

for migration in "${MIGRATIONS_DIR}"/*.cypher; do
  if [ -f "$migration" ]; then
    echo "  Applying: $(basename "$migration")"
    # cypher-shell when available; otherwise log for manual run
    if command -v cypher-shell &> /dev/null; then
      cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" -f "$migration"
    else
      echo "    (cypher-shell not found — migration queued for Neo4j init)"
    fi
  fi
done

echo "==> KG migrations complete."
