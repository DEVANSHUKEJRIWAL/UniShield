#!/usr/bin/env bash
# Apply TimescaleDB metrics schema (Week 7)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SQL="$ROOT/scripts/migrate-timescale.sql"
TS_URI="${TIMESCALE_URI:-postgresql://unishield:password@localhost:5433/unishield_metrics}"

if command -v psql >/dev/null 2>&1; then
  psql "$TS_URI" -f "$SQL"
  echo "TimescaleDB schema applied via psql"
else
  python3 - <<'PY'
import asyncio
from packages.core.metrics_db import ensure_metrics_schema
asyncio.run(ensure_metrics_schema())
print("TimescaleDB schema applied via Python")
PY
fi
