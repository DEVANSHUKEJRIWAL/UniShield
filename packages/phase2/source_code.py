"""Phase 2 Source Code / mythos-review pipeline."""

from __future__ import annotations

import json
from typing import Any

from agents._openclaw import tools as T
from packages.core.bfsi import BFSIFinding, confidence_label, now_iso, regulators_for_industry, stable_bfsi_id
from packages.core.config import settings
from packages.core.industry_prompts import mythos_system_prompt
from packages.integrations.sast import run_gitleaks, run_npm_audit, run_pip_audit, run_trivy_fs


async def run_mythos_review(
    code: str,
    language: str,
    filename: str,
    industry: str = "banking",
    repo_path: str | None = None,
) -> dict[str, Any]:
    """BFSI source code review — SAST tools + optional Claude synthesis."""
    regulators = regulators_for_industry(industry)
    findings: list[BFSIFinding] = []
    scan_path = repo_path or "."

    semgrep = await T.run_semgrep(scan_path)
    bandit = await T.run_bandit(scan_path) if language.lower() in ("python", "py") else []
    gitleaks = await run_gitleaks(scan_path)
    trivy = await run_trivy_fs(scan_path)
    deps: list[dict[str, Any]] = []
    if repo_path:
        deps.extend(await run_pip_audit(f"{scan_path}/requirements.txt"))
        deps.extend(await run_npm_audit(scan_path))

    for item in semgrep + bandit + gitleaks:
        live = item.get("live", not item.get("mock", False))
        findings.append(
            BFSIFinding(
                id=stable_bfsi_id("sc-sast", str(item.get("file")), str(item.get("rule"))),
                agentId="unishield-codescan",
                kind="code-vulnerability",
                severity=_map_severity(item.get("severity", "medium")),
                confidence="high" if live else "medium",
                title=f"SAST: {item.get('rule', 'finding')}",
                description=str(item.get("description", item.get("rule", "")))[:500],
                evidence=item,
                asset=str(item.get("file", filename)),
                feedSource="semgrep/bandit/gitleaks",
                remediation="Remediate per CWE and re-run pipeline",
                regulators=regulators,
                detectedAt=now_iso(),
                dataMode="live" if live else "mock-fallback",
            )
        )

    for item in trivy + deps:
        findings.append(
            BFSIFinding(
                id=stable_bfsi_id("sc-dep", str(item.get("package")), str(item.get("cve", ""))),
                agentId="unishield-codescan",
                kind="code-vulnerability",
                severity=_map_severity(item.get("severity", "high")),
                confidence="high",
                title=f"Dependency: {item.get('package', 'package')} {item.get('cve', '')}",
                description=str(item.get("description", "dependency vulnerability"))[:500],
                evidence=item,
                asset=str(item.get("package", filename)),
                feedSource="trivy/pip-audit/npm-audit",
                remediation="Upgrade dependency or apply vendor patch",
                regulators=regulators,
                detectedAt=now_iso(),
                dataMode="live" if item.get("live") else "mock-fallback",
            )
        )

    if settings.anthropic_api_key and code.strip():
        claude_findings = await _claude_sast(code, language, filename, industry, regulators)
        findings.extend(claude_findings)

    if not findings and code.strip():
        findings.append(
            BFSIFinding(
                id=stable_bfsi_id("sc-manual", filename),
                agentId="unishield-codescan",
                kind="code-vulnerability",
                severity="medium",
                confidence="medium",
                title=f"Manual review required: {filename}",
                description="No automated SAST hits; review submitted snippet",
                evidence={"filename": filename, "language": language, "lines": len(code.splitlines())},
                asset=filename,
                feedSource="manual-snippet",
                remediation="Apply secure coding standards for " + industry,
                regulators=regulators,
                detectedAt=now_iso(),
                dataMode="mock-fallback",
            )
        )

    summary = {
        "total": len(findings),
        "critical": sum(1 for f in findings if f.severity == "critical"),
        "high": sum(1 for f in findings if f.severity == "high"),
        "medium": sum(1 for f in findings if f.severity == "medium"),
        "low": sum(1 for f in findings if f.severity == "low"),
        "industry": industry,
        "language": language,
    }
    return {"findings": [f.model_dump() for f in findings], "summary": summary}


async def _claude_sast(
    code: str,
    language: str,
    filename: str,
    industry: str,
    regulators: list[str],
) -> list[BFSIFinding]:
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        system = mythos_system_prompt(industry, language, filename)
        user = f"Analyse this {language} code:\n\n```{language}\n{code[:12000]}\n```"
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = next((b.text for b in resp.content if hasattr(b, "text")), "{}")
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            return []
        data = json.loads(text[start:end])
        out: list[BFSIFinding] = []
        for raw in data.get("findings", [])[:10]:
            sev = _map_severity(raw.get("severity", "medium"))
            conf = float(raw.get("confidence", 0.8)) if isinstance(raw.get("confidence"), (int, float)) else 0.8
            out.append(
                BFSIFinding(
                    id=raw.get("id") or stable_bfsi_id("sc-claude", raw.get("title", filename)),
                    agentId="unishield-codescan",
                    kind="code-vulnerability",
                    severity=sev,
                    confidence=confidence_label(conf),
                    title=str(raw.get("title", "Claude SAST finding")),
                    description=str(raw.get("description", ""))[:500],
                    evidence=raw.get("evidence", {}),
                    asset=str(raw.get("asset", filename)),
                    feedSource="anthropic-claude",
                    remediation=str(raw.get("remediation", "Fix per recommendation")),
                    regulators=raw.get("regulators") or regulators,
                    detectedAt=now_iso(),
                    dataMode="live",
                )
            )
        return out
    except Exception:
        return []


def _map_severity(value: str) -> str:
    v = str(value).upper()
    if v in ("CRITICAL", "ERROR"):
        return "critical"
    if v in ("HIGH", "WARNING"):
        return "high"
    if v in ("MEDIUM", "MODERATE"):
        return "medium"
    return "low"
