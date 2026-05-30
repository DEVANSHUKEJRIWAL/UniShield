# UniShield Agent Roster (Week 1)

**Version:** 1.0.0  
**Framework:** OpenClaw (`agents/_openclaw/base.py`)  
**Standard output:** `AgentFinding` — see [agent-output-validation.md](./agent-output-validation.md)

All agents share:

- **Runtime input:** JSON event or query string + `tenant_id` + optional `kg_context`
- **Runtime output:** Structured `AgentFinding` published to Redis stream `unishield:agent:{name}:findings`
- **Trigger:** `POST /agent/run` (SSE) or Redis task stream `unishield:agent:{name}:tasks`

---

## 1. Orchestrator

| Field | Value |
|-------|-------|
| **ID** | `orchestrator` |
| **Role** | Route security events to specialist agents; manage P0–P3 priority; aggregate findings |
| **Implementation** | `agents/orchestrator/agent.py` (LangGraph) |

**Input schema**

```json
{
  "event": { "type": "string", "source": "string", "payload": {} },
  "tenant_id": "string",
  "priority": "P0 | P1 | P2 | P3"
}
```

**Output schema**

```json
{
  "aggregated_finding": {
    "contributing_agents": ["string"],
    "findings": ["AgentFinding"]
  }
}
```

**Tools**

| Tool | Purpose |
|------|---------|
| `dispatch_agent` | Queue task to specialist agent |
| `aggregate_findings` | Merge findings by ID |

---

## 2. Dark Web Monitoring Agent

| Field | Value |
|-------|-------|
| **ID** | `dark-web-agent` |
| **Role** | Tor-accessible feeds, paste sites, breach DBs, credential leaks, threat actor forums |
| **Output type** | `BreachFinding` |

**Input:** `{ "query": "string", "sources": ["paste","forum"], "email_domain": "string" }`

**Tools:** `crawl_dark_web_feeds`, `check_credential_exposure`, `monitor_paste_sites`, `detect_typosquatting`, `lookup_threat_actor`, `query_knowledge_graph`

**Week 1 data sources:** OSINT feed URLs (`OSINT_FEED_URLS`), breach intel APIs (see [api-keys-setup.md](./api-keys-setup.md))

---

## 3. Source Code Review Agent

| Field | Value |
|-------|-------|
| **ID** | `source-code-agent` |
| **Role** | SAST (Semgrep, Bandit), secret scanning, dependency CVEs |
| **Output type** | `CodeFinding` |

**Input:** `{ "repo_path": "string", "diff_text": "string", "files": ["string"] }`

**Tools:** `run_semgrep`, `run_bandit`, `scan_for_secrets`, `scan_dependency_vulnerabilities`, `analyse_diff_semantics`

---

## 4. Insider Threat Intelligence Agent

| Field | Value |
|-------|-------|
| **ID** | `insider-threat-agent` |
| **Role** | UEBA, access pattern anomalies, privilege escalation, internal risk scores |

**Input:** `{ "user_id": "string", "events": [], "access_logs": "string" }`

**Tools:** `score_user_anomaly`, `detect_anomalous_access`, `check_privilege_escalation`, `get_user_baseline`, `retrieve_insider_patterns`

---

## 5. Threat Intelligence Agent

| Field | Value |
|-------|-------|
| **ID** | `threat-intel-agent` |
| **Role** | VirusTotal, Shodan, MITRE ATT&CK, IOC correlation |

**Input:** `{ "indicator": "string", "ioc_list": "string" }`

**Tools:** `query_virustotal`, `query_shodan`, `lookup_mitre_attack`, `search_threat_intel_corpus`, `correlate_iocs`

**Required API keys:** `VIRUSTOTAL_API_KEY`, `SHODAN_API_KEY` (MITRE via STIX — no key)

---

## 6. Vulnerability Assessment Agent

| Field | Value |
|-------|-------|
| **ID** | `vulnerability-agent` |
| **Role** | NVD/CVE lookup, CVSS, patch prioritisation, KEV checks |

**Input:** `{ "cve_id": "string", "cve_list": "string", "asset_context": {} }`

**Tools:** `lookup_cve`, `score_exploitability`, `prioritise_patches`, `check_known_exploitation`, `query_sbom_for_cve`

**Required API keys:** `NVD_API_KEY` (optional but recommended)

---

## 7. Incident Response Agent

| Field | Value |
|-------|-------|
| **ID** | `incident-response-agent` |
| **Role** | Playbook retrieval, triage, escalation paths, containment |
| **Output type** | `IRFinding` |

**Tools:** `retrieve_playbook`, `triage_incident`, `generate_escalation_path`, `suggest_containment_actions`

---

## 8. SIEM Analysis Agent

| Field | Value |
|-------|-------|
| **ID** | `siem-analysis-agent` |
| **Role** | Splunk/ES queries, log anomalies, alert correlation |

**Tools:** `run_splunk_search`, `detect_log_anomaly`, `correlate_alerts`, `query_elasticsearch`

---

## 9. Network Security Agent

| Field | Value |
|-------|-------|
| **ID** | `network-security-agent` |
| **Role** | Nmap/port scan analysis, traffic anomalies, firewall rules |

**Tools:** `analyse_port_scan_result`, `detect_traffic_anomaly`, `recommend_firewall_rules`, `check_lateral_movement_indicators`, `query_knowledge_graph`

---

## 10. Compliance Agent

| Field | Value |
|-------|-------|
| **ID** | `compliance-agent` |
| **Role** | Map findings to NIST CSF, ISO 27001, RBI, DPDP, PCI-DSS controls |

**Tools:** `map_finding_to_controls`, `assess_control_coverage`, `identify_gaps`, `generate_evidence_pack`

---

## 11. Forensics / Analysis Agent

| Field | Value |
|-------|-------|
| **ID** | `forensics-agent` |
| **Role** | IOC extraction, timeline reconstruction, artefact analysis |
| **Output type** | `ForensicFinding` |

**Tools:** `extract_iocs`, `reconstruct_timeline`, `analyse_artefact`, `correlate_iocs_with_graph`

---

## 12. Graph Query Agent

| Field | Value |
|-------|-------|
| **ID** | `graph-query-agent` |
| **Role** | Neo4j attack paths, crown jewels, blast radius, NL→Cypher |

**Tools:** `traverse_attack_paths`, `find_crown_jewels_reachable`, `identify_chokepoints`, `get_blast_radius`, `nl_to_cypher`

---

## 13. Reporting Agent

| Field | Value |
|-------|-------|
| **ID** | `reporting-agent` |
| **Role** | Multi-audience summaries (Board/CISO/Analyst), compliance reports, PDF |

**Tools:** `gather_findings_summary`, `generate_executive_summary`, `generate_compliance_report`, `export_pdf`, `schedule_report`

---

## Communication patterns

| Pattern | Stream / endpoint |
|---------|-------------------|
| Task dispatch | `unishield:agent:{agent}:tasks` |
| Finding emit | `unishield:agent:{agent}:findings` |
| Normalised events | `unishield:events:normalised` |
| HITL queue | `unishield:hitl:queue` |
| Direct invoke (dev) | `POST /agent/run` |

See [orchestrator-design.md](./orchestrator-design.md) for routing and escalation rules.
