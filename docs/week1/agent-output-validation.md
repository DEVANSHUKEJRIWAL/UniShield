# Agent Output Validation Criteria (Week 1)

All UniShield agents **must** emit findings that pass `AgentFinding` validation (`packages/core/schemas.py`). This document defines what constitutes a **valid** and **safe** agent response.

---

## 1. Required structure

Every agent output must include:

| Field | Rule |
|-------|------|
| `finding_id` | Unique UUID string |
| `tenant_id` | Must match invoking tenant — never cross-tenant |
| `agent_id` | Must match registered agent name |
| `type` | One of: `analysis`, `breach`, `code`, `incident_response`, `forensics`, `security`, etc. |
| `severity` | `critical` \| `high` \| `medium` \| `low` \| `info` |
| `confidence` | Float 0.0–1.0 |
| `title` | ≤ 512 chars, human-readable summary |
| `description` | Factual description of what was found |
| `reasoning_summary` | ≤ 2000 chars — how the agent reached the conclusion |

---

## 2. Valid response criteria

A finding is **valid** when:

1. **Schema passes** — Pydantic `AgentFinding.model_validate()` succeeds
2. **Evidence cited** — `evidence_references` lists tool outputs or data sources used
3. **Confidence justified** — `confidence_breakdown` populated when confidence > 0.8
4. **No fabricated metrics** — CVSS scores, detection counts, IP verdicts must come from tool results
5. **MITRE mapping** — When claiming ATT&CK technique, `mitre_ttps_matched` must list technique IDs (e.g. `T1078`)
6. **Actions are actionable** — `recommended_actions` are specific verbs (Rotate, Block, Patch), not vague advice

---

## 3. Safe response criteria

A finding is **safe** when:

1. **No secrets in output** — Passwords, API keys, private keys redacted (`[REDACTED]`)
2. **No destructive instructions** — Agent cannot recommend irreversible actions without `hitl_required: true`
3. **PII minimised** — Email/username only when necessary; no full employee records
4. **Tenant isolated** — `tenant_id` in finding matches request; no other client names/IDs
5. **Tool errors disclosed** — If tool returned `mock: true` or `error`, `reasoning_summary` must note degraded confidence
6. **Refusal on prompt injection** — Agent ignores instructions embedded in untrusted event payloads that contradict system prompt

---

## 4. Automatic rejection rules

Reject (do not publish) findings that:

| Condition | Action |
|-----------|--------|
| `confidence > 0.95` with empty `evidence_references` | Reject — likely hallucination |
| `severity == critical` with `confidence < 0.5` | Downgrade to `medium` or require HITL |
| Cross-tenant entity in description | Reject + audit log |
| Output exceeds 2000 chars in `reasoning_summary` | Truncate + flag |
| Invalid JSON from agent | Retry once, then emit error finding |

---

## 5. HITL triggers

Set `hitl_required: true` when:

- `should_require_hitl(confidence, risk_level, severity)` returns true
- Recommended action includes: account disable, firewall change, production deploy block, legal hold
- `severity == critical` and action is not read-only

---

## 6. Specialist extensions

| Schema | Extra required fields |
|--------|----------------------|
| `BreachFinding` | `affected_entities[]` |
| `CodeFinding` | `file_path`, `line_number`, `cwe_reference` |
| `IRFinding` | `playbook_reference`, `priority_actions[]` |
| `ForensicFinding` | `iocs[]`, `timeline[]` |

---

## 7. Testing validation (Week 2+)

```python
from packages.core.schemas import AgentFinding

finding = AgentFinding.model_validate(agent_output)
assert finding.tenant_id == expected_tenant
assert finding.confidence >= 0.0
```

Pytest suites should cover:

- Valid minimal finding
- Invalid severity enum
- Missing required fields
- Cross-tenant rejection
- Mock-mode confidence penalty

---

## 8. References

- Schema: `packages/core/schemas.py`
- HITL rules: `services/hitl_service/models.py`
- Emit path: `agents/_openclaw/base.py` → `emit_structured_finding()`
