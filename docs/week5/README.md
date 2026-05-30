# Week 5 — Findings API, Search, RBAC, Reporting, Alembic

Week 5 deliverables: paginated findings/alerts APIs, Elasticsearch search with DB fallback, RBAC on all endpoints, reporting synthesis, workflow templates, Alembic migrations.

## Implemented

| Deliverable | Location |
|-------------|----------|
| Pagination helpers | `packages/core/pagination.py` |
| Findings / search / reporting APIs | `services/api-gateway/routers/` |
| RBAC on all protected routes | `require_permission()` on all routers |
| Workflow templates | `packages/core/workflow_templates.py` |
| P0–P3 priority queues | `packages/core/dispatch.py` → `RedisStream.priority_queue()` |
| Alembic baseline | `alembic/versions/001_baseline.py`, `alembic` in `pyproject.toml` |

## Week 5 checklist

- [x] Alerts return `{ items, total, page, pages }`
- [x] Findings API enforces tenant + RBAC
- [x] Search falls back to DB when ES unavailable
- [x] Alembic migration available (`alembic upgrade head`)
- [x] Workflow templates resolve agents + priority
- [x] Priority queue streams published on dispatch
