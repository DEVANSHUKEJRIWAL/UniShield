#!/usr/bin/env bash
# Quick local API diagnostics — run from repo root
set -euo pipefail
cd "$(dirname "$0")/.."

API="${API_URL:-http://127.0.0.1:8000}"

echo "==> UniShield API check ($API)"
echo ""

if ! curl -sf "$API/api/v1/health" >/tmp/unishield-health.json 2>/dev/null; then
  echo "FAIL  API not reachable at $API"
  echo ""
  echo "Start the backend (pick ONE — do not run Docker api-gateway and dev-local.sh together):"
  echo "  ./scripts/dev-local.sh"
  echo ""
  echo "If port 8000 is busy:"
  echo "  docker compose stop api-gateway frontend"
  echo "  kill \$(lsof -t -i:8000) 2>/dev/null"
  echo ""
  echo "Frontend env (frontend/.env.local):"
  echo "  NEXT_PUBLIC_API_URL=http://127.0.0.1:8000"
  exit 1
fi

echo "OK    Health: $(cat /tmp/unishield-health.json)"

TOKEN=$(curl -sf -X POST "$API/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"analyst@meridian.com","password":"analyst123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)

if [ -z "$TOKEN" ]; then
  echo "FAIL  Login failed — run: curl -X POST $API/api/v1/dev/fix-login"
  exit 1
fi

echo "OK    Login (analyst@meridian.com)"

for path in \
  "/api/v1/agents/status/meridian-financial" \
  "/api/v1/hitl/queue/meridian-financial" \
  "/api/v1/alerts/meridian-financial" \
  "/api/v1/dashboard/meridian-financial?range=7d"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API$path")
  if [ "$code" = "200" ]; then
    echo "OK    GET $path"
  else
    echo "FAIL  GET $path (HTTP $code)"
  fi
done

if curl -sf "$API/api/v1/dev/anthropic-check" >/tmp/unishield-anthropic.json 2>/dev/null; then
  live=$(python3 -c "import json; print(json.load(open('/tmp/unishield-anthropic.json')).get('live_enabled', False))" 2>/dev/null || echo "false")
  if [ "$live" = "True" ]; then
    echo "OK    Anthropic live reasoning enabled"
  else
    echo "INFO  Anthropic mock mode (no valid API key — agents still run with mock findings)"
  fi
fi

echo ""
echo "Frontend: cd frontend && npm run dev  →  http://localhost:3000"
echo "Agents:   docker compose up -d redis && ./scripts/run-agent-workers.sh"
