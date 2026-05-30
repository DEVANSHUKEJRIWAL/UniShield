# Week 4 — SIEM schema, specialist handlers, adversarial tests

Week 4 deliverables: normalised SIEM event schema, structured handlers for threat-intel / vulnerability / SIEM agents, adversarial prompt-injection tests.

## Implemented

| Deliverable | Location |
|-------------|----------|
| SIEM normalised event | `packages/core/siem_schema.py` → `SiemNormalizedEvent` |
| Threat intel structured handler | `agents/threat-intel-agent/agent.py` |
| Vulnerability structured handler | `agents/vulnerability-agent/agent.py` |
| SIEM analysis structured handler | `agents/siem-analysis-agent/agent.py` |
| Adversarial tests | `tests/security/test_adversarial.py` |

## Event types (mock mode)

| Event type | Agent |
|------------|-------|
| `ioc_observed` | threat-intel-agent |
| `cve_alert` | vulnerability-agent |
| `siem_alert` | siem-analysis-agent |
| `anomalous_login` | insider-threat-agent |

## Tests

```bash
pytest tests/security/test_adversarial.py tests/unit/test_specialist_agents.py -v
```

## Week 4 checklist

- [ ] `SiemNormalizedEvent.to_agent_event()` used in SIEM handler
- [ ] Orchestrator routes `siem_alert` → siem-analysis-agent
- [ ] Adversarial payloads do not bypass structured validation
