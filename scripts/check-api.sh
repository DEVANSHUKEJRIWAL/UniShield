#!/usr/bin/env bash
# Quick local API diagnostics — run from repo root
set -euo pipefail
cd "$(dirname "$0")/.."

API="${API_URL:-http://127.0.0.1:8000}"
ORCH="${ORCHESTRATOR_URL:-http://127.0.0.1:8001}"

echo "==> UniShield API check ($API)"
echo ""

if ! curl -sf "$API/api/v1/health" >/tmp/unishield-health.json 2>/dev/null; then
  echo "FAIL  API gateway not reachable at $API"
  echo "  ./scripts/dev-local.sh"
  exit 1
fi

echo "OK    Gateway health: $(cat /tmp/unishield-health.json)"

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
  "/api/v1/workflows/health" \
  "/api/v1/workflows/definitions" \
  "/api/v1/workflows/meridian-financial"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API$path")
  if [ "$code" = "200" ]; then
    echo "OK    GET $path"
  else
    echo "WARN  GET $path (HTTP $code)"
  fi
done

if curl -sf "$ORCH/health" >/tmp/unishield-orch-health.json 2>/dev/null; then
  echo "OK    Orchestrator health ($ORCH)"
else
  echo "WARN  Orchestrator not reachable at $ORCH — run ./scripts/run-unishield-orchestrator.sh"
fi

echo ""
echo "Frontend: cd frontend && npm run dev  →  http://localhost:3000"
echo "Orchestrator: ./scripts/run-unishield-orchestrator.sh  →  http://localhost:8001"
