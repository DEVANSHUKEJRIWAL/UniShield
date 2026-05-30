# Week 8 — Reporting, Compliance UI, Executive, Month 2

## Deliverables

- [x] Reporting Agent PDF export (`export_pdf_report` in `agents/_openclaw/tools.py`)
- [x] Report persistence model + download API (`Report` model, `/report/{id}/download`)
- [x] Reporting UI: generate, list, download
- [x] Compliance coverage from findings + ATT&CK mapping API
- [x] Compliance heatmap UI with technique badges
- [x] Background CVE poller in API lifespan
- [x] Tenant isolation E2E tests

## Run

```bash
UNISHIELD_USE_SQLITE=1 pytest tests/integration/test_tenant_isolation_e2e.py -q
```
