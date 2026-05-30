# Week 5 — Findings API, Search, RBAC, Reporting, Alembic

Week 5 deliverables: paginated findings/alerts APIs, Elasticsearch search with DB fallback, RBAC on endpoints, reporting synthesis, Alembic migrations.

## Implemented

| Deliverable | Location |
|-------------|----------|
| Pagination helpers | `packages/core/pagination.py` |
| Findings API | `GET /api/v1/findings/{client_id}` |
| Search API | `GET /api/v1/search/{client_id}?q=` |
| Reporting synthesis | `GET /api/v1/reporting/{client_id}/summary` |
| RBAC on routes | `require_permission()` on alerts, findings, search |
| Elasticsearch indexing | `services/search/service.py` |
| Alembic baseline | `alembic/versions/001_baseline.py` |

## Quick start

```bash
# Paginated findings
curl "http://localhost:8000/api/v1/findings/meridian-financial?page=1" \
  -H "Authorization: Bearer $TOKEN"

# Search
curl "http://localhost:8000/api/v1/search/meridian-financial?q=credential" \
  -H "Authorization: Bearer $TOKEN"

# Reporting summary
curl http://localhost:8000/api/v1/reporting/meridian-financial/summary \
  -H "Authorization: Bearer $TOKEN"

# Alembic (optional — init_db also creates tables)
pip install alembic
alembic upgrade head
```

## Week 5 checklist

- [ ] Alerts return `{ items, total, page, pages }`
- [ ] Findings API enforces tenant + RBAC
- [ ] Search falls back to DB when ES unavailable
- [ ] Alembic migration applies on Postgres
