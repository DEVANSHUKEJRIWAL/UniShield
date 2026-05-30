# UI Wireframes — Week 1 (6–8 screens)

Week 1 wireframes for **agent monitoring**, **agent status**, and **demo interface**.  
**Implementation status:** Built in Next.js — this doc maps wireframe intent to live routes.

---

## Screen map

| # | Wireframe | Route | Purpose |
|---|-----------|-------|---------|
| 1 | **Login / Mission Control** | `/login` | Auth entry, demo credentials |
| 2 | **SOC Dashboard** | `/dashboard` | KPI strip, threat score, live alerts, agent strip |
| 3 | **Agent Neural Network** | `/agents` | Graph of 13 agents, per-agent run + SSE output |
| 4 | **Alert Command Center** | `/alerts` | Severity filters, expand detail, HITL actions |
| 5 | **Agent Status Panel** | `/dashboard` (agent strip) + API | Per-agent health, idle/running/error |
| 6 | **Compliance Overview** | `/compliance` | Framework selector, control coverage |
| 7 | **Executive Summary** | `/dashboard/executive` | Risk trend, critical findings (board view) |
| 8 | **Investigation Timeline** | `/investigation` | Kill chain, IOCs, case narrative |

Additional demo screens (Month 1): `/network`, `/cloud`, `/clients`, `/settings`

---

## Screen 1 — Login

```
┌─────────────────────────────────────┐
│         [UniShield logo]            │
│      AI-NATIVE CYBER DEFENSE        │
│  ┌─────────────────────────────┐    │
│  │ Email                        │    │
│  ├─────────────────────────────┤    │
│  │ Password                     │    │
│  ├─────────────────────────────┤    │
│  │   [ Enter Mission Control ]  │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

**Data:** `POST /api/v1/auth/login` → JWT stored in localStorage

---

## Screen 2 — SOC Dashboard

```
┌──────────────────────────────────────────────────────────┐
│ Nav: SOC | Agents | Alerts | Compliance | Network | Cloud │
├──────────────────────────────────────────────────────────┤
│  THREAT LEVEL ████████░░ 72    │ KPI: Alerts | Findings  │
│  [Risk trend chart — 6 weeks]  │ Agents | HITL | Critical│
├──────────────────────────────────────────────────────────┤
│  Live Alert Feed          │  Active Agents (status dots)  │
│  ● Critical - cred leak   │  🧠 orchestrator  running     │
│  ● High - priv login      │  🕸️ dark-web      running     │
└──────────────────────────────────────────────────────────┘
```

**APIs:** `GET /api/v1/dashboard/{tenant}`, `/api/v1/alerts/{tenant}`, `/api/v1/agents/status/{tenant}`

---

## Screen 3 — Agent Neural Network

```
┌──────────────────────────────────────────────────────────┐
│              AGENT NEURAL NETWORK                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │     [React Flow graph — orchestrator center]       │  │
│  │         edges to 12 specialist nodes               │  │
│  └────────────────────────────────────────────────────┘  │
│  Selected: dark-web-agent    [ Run Agent ]               │
│  Output stream: data: {"status":"completed",...}         │
└──────────────────────────────────────────────────────────┘
```

**API:** `POST /agent/run` (SSE)

---

## Screen 4 — Alert Command Center

```
┌──────────────────────────────────────────────────────────┐
│  [critical] [high] [medium] [low]  ← severity filters    │
├──────────────────────────────────────────────────────────┤
│ ▌ Credential exposure on dark web     CRITICAL   [HITL]   │
│ ▌ Anomalous privileged login          HIGH                │
│ ▌ MITRE T1078 SIEM correlation        MEDIUM              │
└──────────────────────────────────────────────────────────┘
```

**API:** `GET /api/v1/alerts/{tenant}` — assign/status via PUT endpoints

---

## Screen 5 — Agent Status (embedded)

Per-agent row in dashboard or dedicated panel:

| Agent | Status | Health | Last run |
|-------|--------|--------|----------|
| orchestrator | idle | healthy | — |
| dark-web-agent | idle | healthy | — |

**API:** `GET /api/v1/agents/status/{client_id}`

---

## Screen 6 — Compliance

Framework tabs + control list with status colours (implemented / partial / gap).

**API:** `GET /api/v1/compliance/{client_id}/{framework}`

---

## Screen 7 — Executive Dashboard

Risk trend bars, critical summary cards, compliance percentages.

**API:** `GET /api/v1/dashboard/executive/{client_id}`

---

## Screen 8 — Investigation

Kill chain timeline (6 stages), IOC table, risk gauge.

**Planned API (Week 7):** `GET /api/v1/investigation/{case_id}` — UI currently static demo

---

## Wireframe acceptance (Week 1)

- [ ] Product/security reviewed all 8 screens
- [ ] API data sources identified per screen
- [ ] Priority agents highlighted on Screen 3 (dark-web, source-code, insider-threat)
- [ ] HITL interaction point agreed (Screen 4)

---

## Figma / design tokens

Live implementation uses:

- **Themes:** Obsidian (dark) / Arctic (light) — `frontend/src/app/globals.css`
- **Components:** `frontend/src/components/ui/`
- **Motion:** Framer Motion page transitions

Formal Figma files optional — running app serves as interactive wireframe for Week 1 demo.
