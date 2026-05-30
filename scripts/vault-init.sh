#!/usr/bin/env bash
# Bootstrap HashiCorp Vault for local development
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_DEV_ROOT_TOKEN:-dev-root-token}"

echo "==> Waiting for Vault at ${VAULT_ADDR}..."
until curl -sf "${VAULT_ADDR}/v1/sys/health" > /dev/null 2>&1; do
  sleep 2
done

export VAULT_ADDR VAULT_TOKEN

echo "==> Enabling KV secrets engine..."
vault secrets enable -path=secret kv-v2 2>/dev/null || true

echo "==> Seeding dev secrets..."
vault kv put secret/unishield/anthropic api_key="${ANTHROPIC_API_KEY:-placeholder}"
vault kv put secret/unishield/postgres uri="${POSTGRES_URI:-postgresql://unishield:password@localhost:5432/unishield}"

echo "==> Vault bootstrap complete."
