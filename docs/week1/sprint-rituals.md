# Sprint Rituals & Definition of Done (Week 1)

Agreed team practices for UniShield development.

---

## 1. Sprint cadence

| Ritual | Frequency | Duration | Purpose |
|--------|-----------|----------|---------|
| **Daily standup** | Mon–Fri | 15 min | Blockers, yesterday/today, agent integration status |
| **Backlog refinement** | Weekly (Wed) | 30 min | Groom next week’s stories against 12-week plan |
| **PR review block** | Daily | 2–4 pm team TZ | Dedicated review window — no meetings |
| **Demo prep** | End of Month 1 / 2 | 1 h | Stakeholder walkthrough rehearsal |
| **Retrospective** | End of each month | 45 min | What worked, what blocked, action items |

---

## 2. Daily standup format

Each person answers:

1. What did I complete since last standup?
2. What am I working on today?
3. Any blockers (API keys, infra, agent failures)?

**Agent-specific prompt (Wed/Fri):** Which agent pipeline was tested end-to-end?

---

## 3. Pull request rules

| Rule | Detail |
|------|--------|
| **Branch naming** | `cursor/<description>-bcba` or `feature/<week>-<topic>` |
| **PR size** | ≤ 400 lines changed when possible |
| **Reviewers** | Minimum 1 approval before merge |
| **CI must pass** | pytest, type-check, lint (when enforced) |
| **Description** | What, why, how to test |
| **No secrets** | Never commit `.env`, API keys, or credentials |

### PR review checklist

- [ ] Matches week deliverable scope
- [ ] No unrelated refactors
- [ ] Auth/tenant isolation preserved on new endpoints
- [ ] Agent findings pass `AgentFinding` schema
- [ ] Docs updated if API or agent contract changed
- [ ] Demo steps included for UI changes

---

## 4. Definition of Done (DoD)

A story is **done** when:

### Code
- [ ] Implementation merged to `main`
- [ ] Unit tests added for new logic (or documented why N/A)
- [ ] No new critical linter/security findings

### Agents
- [ ] Agent registered in `agents/registry.py`
- [ ] Tools documented in [agent-roster.md](./agent-roster.md)
- [ ] Output validates against `AgentFinding`
- [ ] Runnable via `POST /agent/run` (mock or live)

### API
- [ ] Endpoint in OpenAPI `/docs`
- [ ] JWT + tenant isolation on protected routes
- [ ] Error responses use consistent `{ "detail": "..." }`

### Frontend
- [ ] Page loads without console errors
- [ ] Authenticated routes redirect to login when unauthenticated
- [ ] Loading and error states handled

### Documentation
- [ ] README or `docs/weekN/` updated for new capabilities
- [ ] `.env.example` updated for new config vars

### Demo
- [ ] Reproducible demo steps in PR or week doc
- [ ] Seed data sufficient to show feature

---

## 5. Week 1 exit criteria

Week 1 is complete when:

- [ ] [agent-roster.md](./agent-roster.md) reviewed by team
- [ ] [orchestrator-design.md](./orchestrator-design.md) reviewed by team
- [ ] [local-dev-stack.md](./local-dev-stack.md) — at least 2 engineers ran canonical stack
- [ ] [api-keys-setup.md](./api-keys-setup.md) — keys acquired or mock mode documented
- [ ] [ui-wireframes.md](./ui-wireframes.md) — screens agreed
- [ ] This rituals doc acknowledged in team channel
- [ ] `GET /api/v1/dev/status` returns `week1` readiness block

---

## 6. Communication

| Channel | Use for |
|---------|---------|
| GitHub Issues | Bugs, feature tracking |
| GitHub PRs | Code review, design discussion |
| Standup | Blockers, daily sync |
| Week docs (`docs/weekN/`) | Durable decisions and specs |

---

## 7. Escalation

| Blocker type | Escalate to |
|--------------|-------------|
| Missing API key / vendor access | Platform lead — same day |
| Architecture change to agent protocol | Team review — before coding |
| Security concern in agent output | Security lead — immediate |
| Infra down > 2h | DevOps — immediate |
