# Week 4 — SIEM schema, specialist handlers, adversarial tests

Week 4 deliverables: normalised SIEM event schema, structured handlers for **all** specialist agents, adversarial prompt-injection tests.

## Implemented

| Deliverable | Location |
|-------------|----------|
| SIEM normalised event | `packages/core/siem_schema.py` → `SiemNormalizedEvent` |
| All specialist structured handlers | `agents/*/` + `agents/_openclaw/structured.py` |
| Adversarial tests | `tests/security/test_adversarial.py` |
| E2E pipeline test | `tests/integration/test_pipeline_e2e.py` |

## Week 4 checklist

- [x] `SiemNormalizedEvent.to_agent_event()` used in SIEM handler
- [x] Orchestrator routes `siem_alert` → siem-analysis-agent
- [x] Adversarial payloads do not bypass structured validation
- [x] E2E orchestrator → DB pipeline test
