#!/usr/bin/env bash
# Seed local development environment with mock client and security data
set -euo pipefail

POSTGRES_URI="${POSTGRES_URI:-postgresql://unishield:password@localhost:5432/unishield}"

echo "==> Seeding mock tenant data..."

CLIENTS=(
  "meridian-financial|Meridian Financial Group|BFSI"
  "aerodyne-corp|AeroDyne Corp|Aerospace"
  "novatech-industries|NovaTech Industries|Technology"
  "vantage-health|Vantage Health Systems|Healthcare"
  "globaledge-logistics|GlobalEdge Logistics|Logistics"
)

echo "  Target clients:"
for client in "${CLIENTS[@]}"; do
  IFS='|' read -r id name industry <<< "$client"
  echo "    - ${name} (${id}) — ${industry}"
done

echo "==> Seed script ready. Full PostgreSQL seed in Week 2."
