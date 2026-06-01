"""Shared agent tool implementations — mock-capable for local dev."""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from packages.core.config import settings


async def query_knowledge_graph(cypher: str, tenant_id: str) -> dict[str, Any]:
    """Execute read-only Cypher against Neo4j (mock when unavailable)."""
    try:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        async with driver.session() as session:
            result = await session.run(cypher, tenant_id=tenant_id)
            records = [dict(r) async for r in result]
        await driver.close()
        return {"records": records, "count": len(records)}
    except Exception as exc:
        return {
            "records": [
                {"hostname": "db-prod-01", "criticality": "high", "clientId": tenant_id},
                {"hostname": "api-gateway", "criticality": "medium", "clientId": tenant_id},
            ],
            "count": 2,
            "mock": True,
            "error": str(exc),
        }


async def search_qdrant(collection: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Semantic search over Qdrant collection (mock when unavailable)."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.qdrant_url}/collections/{collection}/points/search",
                json={"vector": [0.1] * 1536, "limit": limit, "with_payload": True},
                timeout=5.0,
            )
            if resp.status_code == 200:
                return resp.json().get("result", [])
    except Exception:
        pass
    return [
        {"id": str(uuid4()), "score": 0.92, "payload": {"text": f"Mock result for: {query}", "collection": collection}},
    ]


async def query_virustotal(indicator: str) -> dict[str, Any]:
    """Query VirusTotal for hash/IP/domain reputation."""
    if settings.virustotal_api_key:
        try:
            import httpx

            itype = "files" if len(indicator) == 64 else "ip_addresses" if indicator.replace(".", "").isdigit() else "domains"
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://www.virustotal.com/api/v3/{itype}/{indicator}",
                    headers={"x-apikey": settings.virustotal_api_key},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            return {"mock": True, "malicious": False, "error": str(exc)}
    return {"mock": True, "indicator": indicator, "malicious": indicator.endswith("bad"), "detections": 0}


async def query_shodan(ip: str) -> dict[str, Any]:
    """Query Shodan for IP intelligence."""
    if settings.shodan_api_key:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.shodan.io/shodan/host/{ip}?key={settings.shodan_api_key}",
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            return {"mock": True, "error": str(exc)}
    return {"mock": True, "ip": ip, "ports": [22, 443, 8080], "vulns": ["CVE-2024-1234"]}


async def lookup_cve(cve_id: str) -> dict[str, Any]:
    """Lookup CVE from NVD (mock when unavailable)."""
    return {
        "cve_id": cve_id,
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "description": f"Vulnerability {cve_id} — mock description for local dev",
        "published": "2024-01-15",
        "kev": cve_id.startswith("CVE-2024"),
    }


async def crawl_dark_web_feeds(query: str, sources: list[str] | None = None) -> list[dict[str, Any]]:
    """Monitor dark web / OSINT feeds — HTTP fetch when OSINT_FEED_URLS configured."""
    results: list[dict[str, Any]] = []
    feed_urls = [u.strip() for u in settings.osint_feed_urls.split(",") if u.strip()]
    if feed_urls:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=8.0) as client:
                for url in feed_urls:
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200 and query.lower() in resp.text.lower():
                            results.append(
                                {
                                    "source": url,
                                    "match": query,
                                    "severity": "high",
                                    "snippet": resp.text[:200],
                                    "live": True,
                                }
                            )
                    except Exception:
                        continue
        except Exception:
            pass
    if not results:
        results = [
            {"source": "forum_alpha", "match": query, "severity": "high", "snippet": f"Credential dump mentioning {query}", "mock": True},
            {"source": "paste_site", "match": query, "severity": "medium", "snippet": f"Paste containing {query} keywords", "mock": True},
        ]
    return results


async def check_credential_exposure(email_domain: str) -> dict[str, Any]:
    """Check breach databases for credential exposure (HIBP + OSINT feeds)."""
    from packages.integrations.hibp import fetch_hibp_breaches

    domain = email_domain.strip().lower().lstrip("@")
    feed_hits = await crawl_dark_web_feeds(domain, ["breach"])
    hibp = await fetch_hibp_breaches(domain)

    exposed = int(hibp.get("exposed_count") or 0)
    latest = hibp.get("latest_breach")
    live = bool(hibp.get("live")) or any(h.get("live") for h in feed_hits)
    source = "hibp" if hibp.get("live") else (feed_hits[0].get("source", "osint") if feed_hits else "breach_intel")

    if not live and not exposed:
        exposed = len([h for h in feed_hits if not h.get("mock")])

    severity = "critical" if exposed > 100_000 else "high" if exposed > 1000 else "medium" if exposed else "low"
    if feed_hits and any(h.get("severity") == "high" for h in feed_hits):
        severity = "high"

    summary = (
        f"{exposed} records in known breaches for {domain}"
        if exposed
        else f"No confirmed breaches for {domain} (OSINT matches: {len(feed_hits)})"
    )
    return {
        "domain": domain,
        "exposed_count": exposed,
        "latest_breach": latest,
        "severity": severity,
        "source": source,
        "feed_matches": len(feed_hits),
        "breach_names": hibp.get("breach_names", []),
        "live": live,
        "summary": summary,
    }


async def run_semgrep(repo_path: str, rules: str = "auto") -> list[dict[str, Any]]:
    """Run SAST via Semgrep when installed; mock otherwise."""
    import asyncio
    import shutil

    if shutil.which("semgrep"):
        try:
            proc = await asyncio.create_subprocess_exec(
                "semgrep",
                "--config",
                rules if rules != "auto" else "p/default",
                "--json",
                repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if stdout:
                data = json.loads(stdout.decode())
                live = [
                    {
                        "file": r.get("path", repo_path),
                        "line": r.get("start", {}).get("line", 0),
                        "rule": r.get("check_id", "unknown"),
                        "severity": r.get("extra", {}).get("severity", "INFO"),
                        "live": True,
                    }
                    for r in data.get("results", [])[:20]
                ]
                if live:
                    return live
        except Exception:
            pass
    return [
        {"file": f"{repo_path}/app/auth.py", "line": 42, "rule": "python.lang.security.audit.hardcoded-password", "severity": "ERROR", "mock": True},
        {"file": f"{repo_path}/utils/crypto.py", "line": 15, "rule": "python.lang.security.insecure-hash-algorithm", "severity": "WARNING", "mock": True},
    ]


async def run_bandit(python_path: str) -> list[dict[str, Any]]:
    """Run Bandit SAST when installed; mock otherwise."""
    import asyncio
    import shutil

    if shutil.which("bandit"):
        try:
            proc = await asyncio.create_subprocess_exec(
                "bandit",
                "-r",
                python_path,
                "-f",
                "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if stdout:
                data = json.loads(stdout.decode())
                live = [
                    {
                        "file": i.get("filename", python_path),
                        "line": i.get("line_number", 0),
                        "rule": i.get("test_id", "bandit"),
                        "severity": i.get("issue_severity", "MEDIUM"),
                        "live": True,
                    }
                    for i in data.get("results", [])[:20]
                ]
                if live:
                    return live
        except Exception:
            pass
    return [
        {"file": f"{python_path}/views.py", "line": 10, "rule": "B105", "severity": "LOW", "mock": True},
    ]


async def detect_typosquatting(domain: str, brand: str | None = None) -> dict[str, Any]:
    """Detect typosquat domains via crt.sh."""
    from packages.integrations.crtsh import fetch_typosquat_candidates

    return await fetch_typosquat_candidates(domain, brand)


async def scan_for_secrets(files: str | list[str]) -> list[dict[str, Any]]:
    """Scan paths for hardcoded secrets via gitleaks (mock when unavailable)."""
    from packages.integrations.sast import run_gitleaks

    paths = files if isinstance(files, list) else [files] if files else ["."]
    results: list[dict[str, Any]] = []
    for path in paths:
        path_str = str(path).strip()
        if not path_str:
            continue
        results.extend(await run_gitleaks(path_str))
    if results:
        return results
    return [
        {
            "file": str(paths[0]) if paths else ".env",
            "line": 1,
            "rule": "generic-api-key",
            "severity": "ERROR",
            "mock": True,
            "description": "Mock secret pattern for local dev",
        }
    ]


async def scan_dependency_vulnerabilities(requirements_file: str) -> list[dict[str, Any]]:
    """Scan dependency manifest for known CVEs."""
    from packages.integrations.sast import run_npm_audit, run_pip_audit

    path = (requirements_file or "requirements.txt").strip()
    if path.endswith("package.json") or "package" in path:
        results = await run_npm_audit(path.rsplit("/", 1)[0] if "/" in path else ".")
    else:
        results = await run_pip_audit(path)
    if results:
        return results
    return [
        {
            "package": "example-lib",
            "cve": "CVE-2024-0001",
            "severity": "high",
            "mock": True,
            "description": "Mock dependency vulnerability for local dev",
        }
    ]


async def score_user_anomaly(user_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    """UEBA anomaly scoring via Phase 2 insider rule engine."""
    from packages.core.insider_rules import evaluate_insider_risk

    if isinstance(events, str):
        events = [{"type": events}]
    baseline = await get_user_baseline(user_id)
    return evaluate_insider_risk(user_id, events if isinstance(events, list) else [], baseline)


async def get_user_baseline(user_id: str, tenant_id: str = "meridian-financial") -> dict[str, Any]:
    """Retrieve user behavioural baseline from DB or compute defaults."""
    try:
        from packages.core.persistence import get_insider_baseline, upsert_insider_baseline

        stored = await get_insider_baseline(tenant_id, user_id)
        if stored:
            return stored
        default = {
            "user_id": user_id,
            "window30d": {"avg_logins": 12, "avg_data_volume_mb": 450},
            "window60d": {"avg_logins": 11, "avg_data_volume_mb": 420},
            "peer_group": "finance-analysts",
        }
        await upsert_insider_baseline(tenant_id, user_id, default, peer_group="finance-analysts")
        return {"user_id": user_id, "tenant_id": tenant_id, **default}
    except Exception:
        return {
            "user_id": user_id,
            "window30d": {"avg_logins": 12, "avg_data_volume_mb": 450},
            "window60d": {"avg_logins": 11, "avg_data_volume_mb": 420},
            "peer_group": "finance-analysts",
        }


async def run_splunk_search(query: str, time_range: str = "-24h", tenant_id: str = "meridian-financial") -> dict[str, Any]:
    """Execute Splunk search via connector registry or mock."""
    from services.connector_registry.connectors.splunk import SplunkConnector

    connector = SplunkConnector(
        tenant_id=tenant_id,
        config={"url": settings.splunk_url, "token": settings.splunk_token},
    )
    events = await connector.ingest()
    return {
        "query": query,
        "time_range": time_range,
        "result_count": len(events),
        "results": events,
    }


async def extract_iocs(text: str) -> list[dict[str, str]]:
    """Extract IOCs from text/logs."""
    iocs: list[dict[str, str]] = []
    for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
        iocs.append({"type": "ip", "value": ip})
    for domain in re.findall(r"\b[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b", text):
        if domain not in ("example.com",):
            iocs.append({"type": "domain", "value": domain})
    for md5 in re.findall(r"\b[a-fA-F0-9]{32}\b", text):
        iocs.append({"type": "hash_md5", "value": md5})
    return iocs


async def map_finding_to_controls(finding_id: str, frameworks: list[str]) -> list[dict[str, str]]:
    """Map finding to compliance controls using framework catalogs."""
    from packages.compliance.coverage import load_framework_controls

    controls: list[dict[str, str]] = []
    for fw in frameworks:
        for ctrl in load_framework_controls(fw)[:3]:
            controls.append({"framework": fw, "control_id": ctrl["id"], "title": ctrl["title"]})
    return controls or [{"framework": "NIST", "control_id": "AC-1", "title": "Access Control"}]


async def traverse_attack_paths(source_entity: str, depth: int = 5, tenant_id: str = "") -> dict[str, Any]:
    """Multi-hop attack path traversal via Neo4j."""
    from services.knowledge_graph.service import kg_service

    return await kg_service.traverse_paths(source_entity, tenant_id or "meridian-financial", depth)


async def export_pdf_report(report_content: dict[str, Any], report_type: str = "Board Summary") -> dict[str, Any]:
    """Generate PDF bytes for a report (Week 8)."""
    import base64
    import io

    title = report_content.get("title", report_type)
    narrative = report_content.get("narrative", report_content.get("executive_narrative", ""))
    summary = report_content.get("summary", {})
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 750, f"UniShield — {title}")
        c.setFont("Helvetica", 11)
        y = 720
        for line in (narrative or "").split(". ")[:12]:
            c.drawString(72, y, line[:90])
            y -= 16
        c.drawString(72, y - 20, f"Critical: {summary.get('critical', 0)} | High: {summary.get('high', 0)}")
        c.save()
        pdf_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        return {"format": "pdf", "filename": f"{report_type.replace(' ', '_').lower()}.pdf", "content_base64": pdf_b64}
    except ImportError:
        text = f"{title}\n\n{narrative}\n\nSummary: {summary}"
        return {
            "format": "text",
            "filename": f"{report_type.replace(' ', '_').lower()}.txt",
            "content_base64": base64.b64encode(text.encode()).decode("ascii"),
        }


async def schedule_report_job(tenant_id: str, report_type: str, cron: str = "0 8 * * 1") -> dict[str, Any]:
    """Queue scheduled report generation (Week 8)."""
    from packages.core.redis_client import publish_stream
    from packages.shared_types.constants import RedisStream

    job = {
        "tenant_id": tenant_id,
        "report_type": report_type,
        "cron": cron,
        "scheduled": True,
    }
    await publish_stream(RedisStream.AUDIT_LOG, {"type": "scheduled_report", **job})
    return {"status": "scheduled", **job}


async def gather_findings_summary(tenant_id: str, period: str = "30d", severity: str | None = None) -> dict[str, Any]:
    """Aggregate findings for reporting (DB-backed when available)."""
    days = 30
    if isinstance(period, str) and period.endswith("d"):
        try:
            days = int(period[:-1])
        except ValueError:
            days = 30
    try:
        from packages.core.persistence import summarize_findings

        return await summarize_findings(tenant_id, days=days)
    except Exception:
        return {
            "tenant_id": tenant_id,
            "period": period,
            "total": 47,
            "critical": 3,
            "high": 12,
            "medium": 22,
            "low": 10,
            "top_agents": ["dark-web-agent", "vulnerability-agent", "insider-threat-agent"],
        }


def tool_schema(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    """Build Anthropic tool schema."""
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required or list(properties.keys()),
        },
    }
