#!/usr/bin/env bash
# Repair or reset OpenClaw gateway config used by UniShield Docker.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.orchestrator.yml}"
COMPOSE_PROJECT="${COMPOSE_OPENCLAW_PROJECT:-unishield-openclaw}"
CONTAINER="${OPENCLAW_CONTAINER:-${COMPOSE_PROJECT}-openclaw-1}"
MODE="${1:-doctor}"

CONFIG_DIR="${OPENCLAW_CONFIG_DIR:-$ROOT/.openclaw-docker}"
CONFIG_FILE="$CONFIG_DIR/openclaw.json"
TEMPLATE="$ROOT/config/openclaw-gateway.json"

usage() {
  cat <<EOF
Usage: $0 [doctor|reset|host]

  doctor  Run openclaw doctor --fix inside the gateway container (default)
  reset   Replace config with UniShield template at $TEMPLATE
  host    Run doctor --fix against ~/.openclaw on the host (legacy mount)

Examples:
  $0
  $0 reset
  OPENCLAW_CONFIG_DIR=~/.openclaw $0 host
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

case "$MODE" in
  doctor)
    if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
      echo "Starting OpenClaw container..."
      docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" up -d openclaw
      sleep 3
    fi
    echo "==> Running openclaw doctor --fix in $CONTAINER"
    docker exec "$CONTAINER" node dist/index.js doctor --fix --yes
    echo "==> Restarting gateway"
    docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" restart openclaw
    ;;
  reset)
    mkdir -p "$CONFIG_DIR/workspace"
    cp -f "$TEMPLATE" "$CONFIG_FILE"
    echo "==> Reset config from $TEMPLATE to $CONFIG_FILE"
    docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" up -d --force-recreate openclaw
    ;;
  host)
    HOST_CONFIG="${OPENCLAW_CONFIG_DIR:-$HOME/.openclaw}"
    echo "==> Repairing host config at $HOST_CONFIG/openclaw.json"
    docker run --rm \
      -v "$HOST_CONFIG:/home/node/.openclaw" \
      -e HOME=/home/node \
      -e OPENCLAW_STATE_DIR=/home/node/.openclaw \
      -e OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json \
      ghcr.io/openclaw/openclaw:latest \
      node dist/index.js doctor --fix --yes
    docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" up -d --force-recreate openclaw
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    usage >&2
    exit 1
    ;;
esac

echo ""
echo "Verify:"
echo "  ./scripts/check-openclaw.sh"
echo "  curl -s http://127.0.0.1:18789/healthz"
