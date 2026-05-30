# Week 6 — Live Dashboard, WebSocket, CSP, Frontend Wiring

Week 6 deliverables: live dashboard KPIs, WebSocket streaming for all 13 agents, CSP middleware, frontend API wiring for risk trend / HITL / investigation / reporting.

## Implemented

| Deliverable | Location |
|-------------|----------|
| Live dashboard KPIs | `services/api-gateway/routers/dashboard.py` |
| Risk trend from DB | `risk_trend` in dashboard response |
| WebSocket all agents | `services/api-gateway/routers/ws.py` |
| CSP middleware | `services/api-gateway/middleware/csp.py` |
| Agent run history API | `GET /api/v1/agents/{id}/runs` |
| Investigation cases list | `GET /api/v1/investigation/cases/{client_id}` |
| Frontend wiring | `frontend/src/lib/api.ts`, dashboard, alerts, investigation, reporting, AppShell |

## Quick start

```bash
# Dashboard with live KPIs + risk trend
curl http://localhost:8000/api/v1/dashboard/meridian-financial \
  -H "Authorization: Bearer $TOKEN"

# WebSocket (all 13 agent finding streams)
wscat -c ws://localhost:8000/api/v1/agents/stream/meridian-financial

# Dev readiness
curl http://localhost:8000/api/v1/dev/status | python3 -m json.tool
```

## Week 6 checklist

- [ ] Dashboard shows live alert/finding counts (not hardcoded)
- [ ] HITL queue depth matches Redis queue
- [ ] Risk trend chart uses API data
- [ ] CSP header present on API responses
- [ ] Investigation page loads seeded case
