# Week 6 — Live Dashboard, WebSocket, CSP, Frontend Wiring

Week 6 deliverables: live dashboard KPIs, WebSocket streaming for all 13 agents, CSP middleware, full frontend API wiring.

## Implemented

| Deliverable | Location |
|-------------|----------|
| Live dashboard KPIs | `services/api-gateway/routers/dashboard.py` |
| Risk trend from DB | `risk_trend` in dashboard response |
| WebSocket all agents | `services/api-gateway/routers/ws.py` |
| CSP middleware | `services/api-gateway/middleware/csp.py` |
| Agent run history API | `GET /api/v1/agents/{id}/runs` |
| Investigation IOCs from API | `GET /api/v1/investigation/{case_id}` |
| HITL on alerts (server-side match) | `services/api-gateway/routers/alerts.py` |
| Frontend live agents / WS / reporting generate | `frontend/src/` |

## Week 6 checklist

- [x] Dashboard shows live alert/finding counts (not hardcoded)
- [x] HITL queue depth matches Redis queue
- [x] Risk trend chart uses API data
- [x] CSP header present on API responses
- [x] Investigation page loads case + IOCs from API
- [x] Agents page uses live status from API
- [x] Dashboard threat feed uses agent WebSocket stream
- [x] Reporting Generate buttons call API
