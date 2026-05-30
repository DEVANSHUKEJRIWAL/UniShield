# API Keys & Data Sources Setup (Week 1)

Week 1 requires acquiring and configuring keys for external security data sources. This guide covers acquisition, `.env` configuration, and verification.

---

## 1. Required for live agent reasoning

| Service | Env variable | Acquire at | Notes |
|---------|--------------|------------|-------|
| **Anthropic (Claude)** | `ANTHROPIC_API_KEY` | https://console.anthropic.com/ | Required for real LLM reasoning; without it agents return mock findings |

---

## 2. Week 1 security data sources (shortlist)

| Source | Env variable | Acquire at | Free tier |
|--------|--------------|------------|-----------|
| **VirusTotal** | `VIRUSTOTAL_API_KEY` | https://www.virustotal.com/gui/join-us | Yes (rate limited) |
| **Shodan** | `SHODAN_API_KEY` | https://account.shodan.io/register | Limited free |
| **NVD / CVE** | `NVD_API_KEY` | https://nvd.nist.gov/developers/request-an-api-key | Yes (recommended for rate limits) |
| **MITRE ATT&CK** | *(none)* | https://attack.mitre.org/ — STIX/TAXII 2.1 | Free, no key |
| **OSINT feeds** | `OSINT_FEED_URLS` | See §4 below | Varies |

---

## 3. Configure `.env`

```bash
cp .env.example .env
```

Add your keys:

```env
ANTHROPIC_API_KEY=sk-ant-...

VIRUSTOTAL_API_KEY=your_vt_key
SHODAN_API_KEY=your_shodan_key
NVD_API_KEY=your_nvd_key

# Comma-separated RSS/TAXII/JSON feed URLs
OSINT_FEED_URLS=https://example.com/breach-rss,https://example.com/paste-feed
```

**Never commit `.env` to git.**

---

## 4. OSINT feed examples (pick at least one)

| Feed type | Example sources | Use case |
|-----------|-----------------|----------|
| Breach notification RSS | Have I Been Pwned domain search API, commercial breach feeds | Dark Web Agent |
| Paste site monitors | Configure via `OSINT_FEED_URLS` | Credential leak detection |
| TAXII 2.1 | MITRE ATT&CK STIX: `https://mitre.github.io/attack-stix-data/` | Threat Intel Agent |
| NVD JSON feed | `https://services.nvd.nist.gov/rest/json/cves/2.0` | Vulnerability Agent |

For Week 1, **document which feed you chose** in your team notes. Live polling is implemented in Week 3.

---

## 5. MITRE ATT&CK (no API key)

MITRE ATT&CK is accessed via:

- **STIX/TAXII** — public data sets
- **Local corpus** — embed into Qdrant in Week 3 (`scripts/embed-corpus.sh`)
- **Tool:** `lookup_mitre_attack` in Threat Intel Agent

No registration required for read-only STIX data.

---

## 6. Verify configuration

Start the API, then:

```bash
curl -s http://localhost:8000/api/v1/dev/status | python3 -m json.tool
```

Look for:

```json
{
  "integrations": {
    "virustotal": { "configured": true, ... },
    "shodan": { "configured": true, ... },
    "nvd": { "configured": true, ... },
    "mitre_attack": { "configured": true, ... }
  },
  "week1": {
    "external_intel_keys_configured": 3,
    "live_agent_reasoning": true
  }
}
```

---

## 7. Week 1 acceptance

- [ ] Anthropic key set (or team agrees to mock mode for Week 1)
- [ ] VirusTotal key acquired and in `.env`
- [ ] Shodan key acquired and in `.env`
- [ ] NVD key requested (or documented why public rate limit is acceptable)
- [ ] MITRE ATT&CK access confirmed (STIX URL bookmarked)
- [ ] At least one OSINT feed URL in `OSINT_FEED_URLS`
- [ ] `GET /api/v1/dev/status` shows integration status

---

## 8. Security handling

- Store keys only in `.env`, Vault (Week 9), or CI secrets — never in code
- Rotate keys if exposed
- Use separate keys per environment (dev/staging/prod)
- VirusTotal/Shodan keys are **read-only** — safe for analyst agents
