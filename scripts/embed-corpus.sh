#!/usr/bin/env bash
# Embed threat intel corpus into Qdrant vector store
set -euo pipefail

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"

echo "==> Checking Qdrant at ${QDRANT_URL}..."
until curl -sf "${QDRANT_URL}/healthz" > /dev/null 2>&1; do
  sleep 2
done

COLLECTIONS=("threat_intel" "cve_descriptions" "ir_playbooks" "insider_patterns" "dark_web_corpus")

for collection in "${COLLECTIONS[@]}"; do
  echo "  Creating collection: ${collection}"
  curl -sf -X PUT "${QDRANT_URL}/collections/${collection}" \
    -H "Content-Type: application/json" \
    -d '{"vectors": {"size": 1536, "distance": "Cosine"}}' 2>/dev/null || true
done

echo "==> Qdrant collections ready. Full embedding pipeline in Week 3."
