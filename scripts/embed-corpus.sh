#!/usr/bin/env bash
# Embed threat intel corpus into Qdrant vector store
set -euo pipefail

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"

echo "==> Checking Qdrant at ${QDRANT_URL}..."
until curl -sf "${QDRANT_URL}/healthz" > /dev/null 2>&1; do
  echo "    Waiting for Qdrant..."
  sleep 2
done

echo "==> Running Python embedding pipeline..."
cd "$(dirname "$0")/.."
python3 scripts/embed_corpus.py

echo "==> Corpus embedding complete."
