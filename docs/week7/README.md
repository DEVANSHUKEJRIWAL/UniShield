# Week 7 — SIEM, Neo4j, Graph Query, Investigation

## Deliverables

- [x] Neo4j KG write-back on `persist_finding()` via `packages/core/kg_sync.py`
- [x] Splunk connector live REST + mock fallback (`services/connector-registry/connectors/splunk.py`)
- [x] QRadar demo mock pipeline to agents (`connectors/qradar.py`)
- [x] Connector ingest worker (`services/connector-registry/worker.py`)
- [x] Graph Query real Neo4j traversal (`services/knowledge-graph/service.py`)
- [x] TimescaleDB metrics (`packages/core/metrics_db.py`, `scripts/migrate-timescale.sh`)
- [x] Investigation UI → case API → evidence chain + kill chain progress
- [x] Connector credential injection tests (`tests/security/test_connector_injection.py`)

## Run

```bash
docker compose --profile infra --profile app up -d
./scripts/migrate-kg.sh
./scripts/migrate-timescale.sh
curl -X POST -H "Authorization: Bearer $TOKEN" /api/v1/connectors/ingest -d '{"client_id":"meridian-financial"}'
```
