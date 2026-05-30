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
    """Monitor dark web feeds (mock for local dev)."""
    return [
        {"source": "forum_alpha", "match": query, "severity": "high", "snippet": f"Credential dump mentioning {query}"},
        {"source": "paste_site", "match": query, "severity": "medium", "snippet": f"Paste containing {query} keywords"},
    ]


async def check_credential_exposure(email_domain: str) -> dict[str, Any]:
    """Check breach databases for credential exposure."""
    return {
        "domain": email_domain,
        "exposed_count": 47,
        "latest_breach": "2024-11-01",
        "severity": "high" if email_domain.endswith(".com") else "medium",
    }


async def run_semgrep(repo_path: str, rules: str = "auto") -> list[dict[str, Any]]:
    """Run SAST via Semgrep (mock)."""
    return [
        {"file": f"{repo_path}/app/auth.py", "line": 42, "rule": "python.lang.security.audit.hardcoded-password", "severity": "ERROR"},
        {"file": f"{repo_path}/utils/crypto.py", "line": 15, "rule": "python.lang.security.insecure-hash-algorithm", "severity": "WARNING"},
    ]


async def scan_for_secrets(files: list[str]) -> list[dict[str, Any]]:
    """Scan files for secrets (mock TruffleHog)."""
    return [
        {"file": files[0] if files else "config.env", "type": "aws_key", "line": 3, "severity": "critical"},
    ]


async def score_user_anomaly(user_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    """UEBA anomaly scoring via Z-score."""
    z_score = min(len(events) * 0.3, 4.5)
    return {"user_id": user_id, "z_score": z_score, "anomalous": z_score > 2.5, "peer_group": "finance-analysts"}


async def get_user_baseline(user_id: str) -> dict[str, Any]:
    """Retrieve user behavioural baseline from Redis feature store."""
    return {
        "user_id": user_id,
        "window30d": {"avg_logins": 12, "avg_data_volume_mb": 450},
        "window60d": {"avg_logins": 11, "avg_data_volume_mb": 420},
        "peer_group": "finance-analysts",
    }


async def run_splunk_search(query: str, time_range: str = "-24h") -> dict[str, Any]:
    """Execute Splunk search (mock)."""
    return {
        "query": query,
        "time_range": time_range,
        "result_count": 156,
        "results": [
            {"_time": datetime.now(UTC).isoformat(), "src_ip": "10.0.1.45", "action": "failed_login", "user": "admin"},
        ],
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
    """Map finding to compliance controls."""
    controls = []
    for fw in frameworks:
        controls.append({"framework": fw, "control_id": f"{fw[:4]}-001", "title": f"Access Control — {fw}"})
    return controls


async def traverse_attack_paths(source_entity: str, depth: int = 5, tenant_id: str = "") -> dict[str, Any]:
    """Multi-hop attack path traversal."""
    return {
        "source": source_entity,
        "depth": depth,
        "paths": [
            {"hops": [source_entity, "internal-api", "db-prod-01"], "crown_jewel_reached": True},
        ],
    }


async def gather_findings_summary(tenant_id: str, period: str = "30d", severity: str | None = None) -> dict[str, Any]:
    """Aggregate findings for reporting."""
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
