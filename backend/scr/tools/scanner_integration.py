"""Subprocess integrations for SCR security tooling — no mock findings."""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import math
import re
import shutil
import tempfile
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SEVERITY_MAP = {
    "ERROR": "HIGH",
    "WARNING": "MEDIUM",
    "INFO": "LOW",
    "CRITICAL": "CRITICAL",
    "HIGH": "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW",
}

BFSI_KEYWORDS = (
    "payment",
    "swift",
    "transaction",
    "transfer",
    "wire",
    "card",
    "pci",
    "hsm",
    "trade",
    "settlement",
    "clearing",
    "balance",
    "account",
    "fx",
)

SECRET_EXCLUDE_GLOBS = [
    "tests/**",
    "test/**",
    "**/*mock*",
    "**/*fixture*",
    "**/*fake*",
]


def is_excluded_secret_path(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/").lower()
    for pattern in SECRET_EXCLUDE_GLOBS:
        if fnmatch.fnmatch(normalized, pattern.lower()):
            return True
    return False


async def _run_cmd(
    cmd: list[str],
    *,
    cwd: str | None = None,
    timeout: int = 300,
) -> tuple[int, str, str]:
    if cwd and not Path(cwd).exists():
        return -1, "", f"missing cwd: {cwd}"
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "timeout"
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


def _path_exists(path: str | None) -> bool:
    return bool(path) and Path(path).exists()


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def normalize_severity(raw: str) -> str:
    return SEVERITY_MAP.get(str(raw).upper(), str(raw).upper())


def _rel_path(path: str, repo_root: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(repo_root).resolve())).replace("\\", "/")
    except ValueError:
        return path.replace("\\", "/")


def _code_finding(
    *,
    file_path: str,
    line_start: int,
    line_end: int,
    snippet: str,
    severity: str,
    category: str,
    rule_id: str,
    language: str = "unknown",
    cwe_id: str | None = None,
    tool: str = "sast",
    confidence: float = 0.85,
) -> dict[str, Any]:
    return {
        "finding_id": str(uuid.uuid4()),
        "file_path": file_path,
        "language": language,
        "line_start": line_start,
        "line_end": line_end or line_start,
        "column_start": 0,
        "column_end": max(len(snippet), 1),
        "code_snippet": snippet[:500],
        "severity": normalize_severity(severity),
        "confidence": confidence,
        "category": category,
        "rule_id": rule_id,
        "cwe_id": cwe_id,
        "tool": tool,
    }


async def run_semgrep_scan(
    repo_path: str,
    configs: list[str],
    *,
    include_paths: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not shutil.which("semgrep") or not _path_exists(repo_path):
        return []
    configs = [c for c in configs if c]
    if not configs:
        configs = ["p/default"]
    cmd = ["semgrep", "--json", "--quiet", "--timeout", "120"]
    for cfg in configs:
        cmd.extend(["--config", cfg])
    if include_paths:
        for path in include_paths:
            cmd.append(str(Path(repo_path) / path))
    else:
        cmd.append(repo_path)
    code, out, err = await _run_cmd(cmd, cwd=repo_path, timeout=600)
    if code not in (0, 1) and not out:
        logger.warning("Semgrep failed (%s): %s", code, err[:300])
        return []
    try:
        data = json.loads(out or "{}")
    except json.JSONDecodeError:
        return []
    findings: list[dict[str, Any]] = []
    for result in data.get("results", []):
        rel = _rel_path(result.get("path", ""), repo_path)
        extra = result.get("extra", {}) or {}
        metadata = extra.get("metadata", {}) or {}
        findings.append(
            _code_finding(
                file_path=rel,
                line_start=result.get("start", {}).get("line", 0),
                line_end=result.get("end", {}).get("line", 0),
                snippet=extra.get("lines", "") or result.get("check_id", ""),
                severity=extra.get("severity", "MEDIUM"),
                category=metadata.get("category", result.get("check_id", "sast").split(".")[-1]),
                rule_id=result.get("check_id", "semgrep"),
                cwe_id=(metadata.get("cwe") or [None])[0] if isinstance(metadata.get("cwe"), list) else metadata.get("cwe"),
                tool="semgrep",
            )
        )
    return findings


async def run_bandit_scan(repo_path: str) -> list[dict[str, Any]]:
    if not shutil.which("bandit") or not _path_exists(repo_path):
        return []
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        report_path = tmp.name
    code, _, err = await _run_cmd(
        ["bandit", "-r", repo_path, "-f", "json", "-o", report_path, "-q"],
        timeout=300,
    )
    findings: list[dict[str, Any]] = []
    try:
        if Path(report_path).is_file():
            data = json.loads(Path(report_path).read_text(encoding="utf-8"))
            for item in data.get("results", []):
                rel = _rel_path(item.get("filename", ""), repo_path)
                findings.append(
                    _code_finding(
                        file_path=rel,
                        line_start=item.get("line_number", 0),
                        line_end=item.get("line_number", 0),
                        snippet=item.get("code", "")[:500],
                        severity=item.get("issue_severity", "MEDIUM"),
                        category=item.get("test_name", "bandit"),
                        rule_id=item.get("test_id", "bandit"),
                        cwe_id=str(item.get("issue_cwe", {}).get("id")) if item.get("issue_cwe") else None,
                        tool="bandit",
                    )
                )
    except (json.JSONDecodeError, OSError):
        logger.debug("Bandit parse failed: %s", err[:200])
    finally:
        Path(report_path).unlink(missing_ok=True)
    return findings if code in (0, 1) or findings else []


async def run_gosec_scan(repo_path: str) -> list[dict[str, Any]]:
    if not shutil.which("gosec") or not _path_exists(repo_path):
        return []
    code, out, err = await _run_cmd(
        ["gosec", "-fmt=json", "-quiet", "./..."],
        cwd=repo_path,
        timeout=300,
    )
    if not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    findings: list[dict[str, Any]] = []
    for issue in data.get("Issues", []):
        rel = _rel_path(issue.get("file", ""), repo_path)
        findings.append(
            _code_finding(
                file_path=rel,
                line_start=int(issue.get("line", 0) or 0),
                line_end=int(issue.get("line", 0) or 0),
                snippet=issue.get("code", "")[:500],
                severity=issue.get("severity", "MEDIUM"),
                category=issue.get("rule_id", "gosec"),
                rule_id=issue.get("rule_id", "gosec"),
                cwe_id=issue.get("cwe", {}).get("id") if isinstance(issue.get("cwe"), dict) else issue.get("cwe"),
                language="go",
                tool="gosec",
            )
        )
    return findings if code in (0, 1) or findings else []


async def run_eslint_security(repo_path: str) -> list[dict[str, Any]]:
    if not shutil.which("npx") or not _path_exists(repo_path):
        return []
    pkg = Path(repo_path) / "package.json"
    if not pkg.is_file():
        return []
    code, out, _ = await _run_cmd(
        [
            "npx",
            "--yes",
            "eslint",
            ".",
            "--ext",
            ".js,.jsx,.ts,.tsx",
            "-f",
            "json",
            "--no-error-on-unmatched-pattern",
        ],
        cwd=repo_path,
        timeout=300,
    )
    if not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    findings: list[dict[str, Any]] = []
    for file_result in data if isinstance(data, list) else []:
        rel = _rel_path(file_result.get("filePath", ""), repo_path)
        for msg in file_result.get("messages", []):
            rule = msg.get("ruleId") or "eslint"
            if "security" not in rule.lower() and msg.get("severity", 1) < 2:
                continue
            findings.append(
                _code_finding(
                    file_path=rel,
                    line_start=msg.get("line", 0),
                    line_end=msg.get("endLine", msg.get("line", 0)),
                    snippet=msg.get("message", "")[:500],
                    severity="HIGH" if msg.get("severity", 1) >= 2 else "MEDIUM",
                    category=rule,
                    rule_id=rule,
                    language="javascript",
                    tool="eslint",
                )
            )
    return findings if code in (0, 1) or findings else []


async def run_checkov_scan(repo_path: str) -> list[dict[str, Any]]:
    if not shutil.which("checkov") or not _path_exists(repo_path):
        return []
    code, out, _ = await _run_cmd(
        ["checkov", "-d", repo_path, "-o", "json", "--quiet"],
        timeout=300,
    )
    if not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    findings: list[dict[str, Any]] = []
    failed: list[dict] = []
    if isinstance(data, list):
        for block in data:
            failed.extend(block.get("results", {}).get("failed_checks", []))
    elif isinstance(data, dict):
        failed = data.get("results", {}).get("failed_checks", [])
        if not failed:
            failed = data.get("failed_checks", [])
    for check in failed:
        if not isinstance(check, dict):
            continue
        rel = check.get("repo_file_path") or check.get("file_path") or check.get("file", "")
        if rel.startswith("/"):
            rel = _rel_path(rel, repo_path)
        line_range = check.get("file_line_range") or [0, 0]
        findings.append(
            _code_finding(
                file_path=rel,
                line_start=line_range[0] if line_range else 0,
                line_end=line_range[-1] if line_range else 0,
                snippet=check.get("check_name", "")[:500],
                severity=check.get("severity", "MEDIUM") or "MEDIUM",
                category="iac",
                rule_id=check.get("check_id", "checkov"),
                language="terraform",
                tool="checkov",
            )
        )
    return findings if code in (0, 1) or findings else []


async def run_gitleaks_detect(repo_path: str, *, git_history: bool = True) -> list[dict[str, Any]]:
    if not shutil.which("gitleaks") or not _path_exists(repo_path):
        return []
    findings: list[dict[str, Any]] = []
    for history_flag, from_history in (["--no-git"], False), (["--log-opts=--all"], True):
        if not git_history and from_history:
            continue
        git_dir = Path(repo_path) / ".git"
        if from_history and not git_dir.is_dir():
            continue
        cmd = [
            "gitleaks",
            "detect",
            "--source",
            repo_path,
            "--no-banner",
            "--report-format",
            "json",
            "--report-path",
            "/dev/stdout",
            *history_flag,
        ]
        code, out, _ = await _run_cmd(cmd, cwd=repo_path, timeout=300)
        if code not in (0, 1) or not out.strip():
            continue
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else data.get("findings", [])
        for item in items:
            secret = item.get("Secret") or item.get("Match") or ""
            findings.append(
                {
                    "secret_type": item.get("RuleID", "secret"),
                    "file_path": _rel_path(item.get("File", ""), repo_path),
                    "line_number": item.get("StartLine", 0),
                    "masked_value": mask_secret(secret),
                    "entropy_score": shannon_entropy(secret) if secret else 4.5,
                    "verified_live": False,
                    "git_history_exposed": from_history,
                }
            )
    return _dedupe_secrets(findings)


def _dedupe_secrets(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int, str]] = set()
    unique: list[dict[str, Any]] = []
    for f in findings:
        key = (f["file_path"], f["line_number"], f["secret_type"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)
    return unique


def scan_entropy_secrets(content: str, file_path: str) -> list[dict[str, Any]]:
    if is_excluded_secret_path(file_path):
        return []
    findings: list[dict[str, Any]] = []
    string_pattern = re.compile(r"""['"]([A-Za-z0-9+/=_\-]{21,})['"]""")
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in string_pattern.finditer(line):
            token = match.group(1)
            entropy = shannon_entropy(token)
            if entropy <= 4.5 or len(token) <= 20:
                continue
            findings.append(
                {
                    "secret_type": "high_entropy_string",
                    "file_path": file_path,
                    "line_number": line_no,
                    "masked_value": mask_secret(token),
                    "entropy_score": round(entropy, 2),
                    "verified_live": False,
                    "git_history_exposed": False,
                }
            )
    return findings


async def run_syft_sbom(repo_path: str) -> dict[str, Any]:
    if not shutil.which("syft") or not _path_exists(repo_path):
        return _fallback_sbom(repo_path)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out_path = tmp.name
    code, _, err = await _run_cmd(
        ["syft", repo_path, "-o", "cyclonedx-json", "--file", out_path],
        timeout=300,
    )
    try:
        if Path(out_path).is_file():
            data = json.loads(Path(out_path).read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("components"):
                return data
    except (json.JSONDecodeError, OSError):
        logger.debug("Syft SBOM parse failed: %s", err[:200])
    finally:
        Path(out_path).unlink(missing_ok=True)
    return _fallback_sbom(repo_path)


def _fallback_sbom(repo_path: str) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    root = Path(repo_path)
    manifests = {
        "package.json": "npm",
        "requirements.txt": "pypi",
        "pyproject.toml": "pypi",
        "go.mod": "go",
        "pom.xml": "maven",
        "Gemfile": "rubygems",
    }
    for name, ecosystem in manifests.items():
        for path in root.rglob(name):
            if any(part in path.parts for part in (".git", "node_modules", "vendor")):
                continue
            components.append(
                {
                    "type": "library",
                    "name": name,
                    "version": "unknown",
                    "purl": f"pkg:{ecosystem}/{path.parent.name}@unknown",
                    "properties": [{"name": "manifest", "value": str(path.relative_to(root))}],
                }
            )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "components": components,
        "dependencies": [],
    }


async def run_grype_vulnerabilities(repo_path: str) -> list[dict[str, Any]]:
    if shutil.which("grype") and _path_exists(repo_path):
        code, out, _ = await _run_cmd(
            ["grype", repo_path, "-o", "json"],
            timeout=300,
        )
        if out:
            try:
                data = json.loads(out)
                return _parse_grype(data)
            except json.JSONDecodeError:
                pass
    return await _run_trivy_and_audits(repo_path)


def _parse_grype(data: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for match in data.get("matches", []):
        vuln = match.get("vulnerability", {}) or {}
        artifact = match.get("artifact", {}) or {}
        cvss = 0.0
        for entry in vuln.get("cvss", []) or []:
            metrics = entry.get("metrics", {}) or {}
            cvss = max(cvss, float(metrics.get("baseScore") or metrics.get("score") or 0))
        if cvss == 0.0:
            cvss = _severity_to_cvss(vuln.get("severity", "medium"))
        if cvss < 7.0:
            continue
        findings.append(
            {
                "package_name": artifact.get("name", "unknown"),
                "version": artifact.get("version", "unknown"),
                "ecosystem": artifact.get("type", "unknown"),
                "cve_id": vuln.get("id", "UNKNOWN"),
                "cvss_score": cvss,
                "severity": normalize_severity(vuln.get("severity", "HIGH")),
                "fixed_version": (vuln.get("fix", {}) or {}).get("versions", [None])[0],
                "is_transitive": bool(match.get("relatedVulnerabilities")),
                "dependency_path": [artifact.get("name", "")],
                "exploitable": cvss >= 9.0,
                "exploit_available": bool(vuln.get("urls")),
            }
        )
    return findings


async def _run_trivy_and_audits(repo_path: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if shutil.which("trivy") and _path_exists(repo_path):
        code, out, _ = await _run_cmd(
            ["trivy", "fs", "--format", "json", "--quiet", repo_path],
            timeout=300,
        )
        if out:
            try:
                data = json.loads(out)
                for result in data.get("Results", []):
                    for vuln in result.get("Vulnerabilities") or []:
                        cvss = float(vuln.get("CVSS", {}).get("nvd", {}).get("V3Score") or 0)
                        if cvss == 0:
                            cvss = _severity_to_cvss(vuln.get("Severity", "medium"))
                        if cvss < 7.0:
                            continue
                        findings.append(
                            {
                                "package_name": vuln.get("PkgName", "unknown"),
                                "version": vuln.get("InstalledVersion", "unknown"),
                                "ecosystem": result.get("Type", "unknown"),
                                "cve_id": vuln.get("VulnerabilityID", "UNKNOWN"),
                                "cvss_score": cvss,
                                "severity": normalize_severity(vuln.get("Severity", "HIGH")),
                                "fixed_version": vuln.get("FixedVersion"),
                                "is_transitive": False,
                                "dependency_path": [vuln.get("PkgName", "")],
                                "exploitable": cvss >= 9.0,
                                "exploit_available": bool(vuln.get("PrimaryURL")),
                            }
                        )
            except json.JSONDecodeError:
                pass
    root = Path(repo_path)
    req = root / "requirements.txt"
    if req.is_file() and shutil.which("pip-audit"):
        code, out, _ = await _run_cmd(["pip-audit", "-r", str(req), "--format", "json"], timeout=120)
        if out:
            try:
                deps = json.loads(out)
                deps_list = deps.get("dependencies", deps) if isinstance(deps, dict) else deps
                for dep in deps_list if isinstance(deps_list, list) else []:
                    for vuln in dep.get("vulns", []):
                        cvss = float(vuln.get("fix_versions") and 7.5 or 7.0)
                        findings.extend(await _osv_enrich(dep.get("name"), dep.get("version"), "PyPI", vuln))
            except json.JSONDecodeError:
                pass
    pkg = root / "package.json"
    if pkg.is_file() and shutil.which("npm"):
        code, out, _ = await _run_cmd(["npm", "audit", "--json"], cwd=str(root), timeout=120)
        if out:
            try:
                data = json.loads(out)
                for name, adv in (data.get("vulnerabilities") or {}).items():
                    cvss = float(adv.get("cvss", {}).get("score") or _severity_to_cvss(adv.get("severity", "high")))
                    if cvss < 7.0:
                        continue
                    findings.append(
                        {
                            "package_name": name,
                            "version": adv.get("range", "unknown"),
                            "ecosystem": "npm",
                            "cve_id": adv.get("via", ["npm-advisory"])[0] if adv.get("via") else "npm-advisory",
                            "cvss_score": cvss,
                            "severity": normalize_severity(adv.get("severity", "HIGH")),
                            "fixed_version": None,
                            "is_transitive": adv.get("isDirect") is False,
                            "dependency_path": [name],
                            "exploitable": cvss >= 9.0,
                            "exploit_available": True,
                        }
                    )
            except json.JSONDecodeError:
                pass
    return findings


async def _osv_enrich(name: str, version: str | None, ecosystem: str, vuln: dict) -> list[dict]:
    cve_id = vuln.get("id", "UNKNOWN")
    cvss = 7.5
    osv_data = await query_osv(name, version or "", ecosystem)
    for item in osv_data:
        if item.get("id") == cve_id or cve_id in str(item.get("aliases", [])):
            for sev in item.get("severity", []) or []:
                if sev.get("type") == "CVSS_V3":
                    cvss = float(sev.get("score", cvss))
    if cvss < 7.0:
        return []
    return [
        {
            "package_name": name,
            "version": version or "unknown",
            "ecosystem": ecosystem,
            "cve_id": cve_id,
            "cvss_score": cvss,
            "severity": "HIGH" if cvss >= 7 else "MEDIUM",
            "fixed_version": (vuln.get("fix_versions") or [None])[0],
            "is_transitive": False,
            "dependency_path": [name],
            "exploitable": cvss >= 9.0,
            "exploit_available": bool(vuln.get("aliases")),
        }
    ]


async def query_osv(package: str, version: str, ecosystem: str) -> list[dict[str, Any]]:
    payload = {"package": {"name": package, "ecosystem": ecosystem}, "version": version}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://api.osv.dev/v1/query", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("vulns", [])
    except Exception as exc:
        logger.debug("OSV query failed for %s@%s: %s", package, version, exc)
    return []


def _severity_to_cvss(severity: str) -> float:
    mapping = {"CRITICAL": 9.5, "HIGH": 8.0, "MEDIUM": 5.5, "LOW": 3.0, "MODERATE": 5.5}
    return mapping.get(str(severity).upper(), 5.0)


def sbom_summary(sbom: dict[str, Any]) -> dict[str, Any]:
    components = sbom.get("components", []) or []
    ecosystems: Counter[str] = Counter()
    for comp in components:
        purl = comp.get("purl", "")
        if purl.startswith("pkg:") and "/" in purl:
            eco = purl.split(":")[1].split("/")[0]
        else:
            eco = comp.get("type", "unknown")
        ecosystems[eco] += 1
    return {
        "components": len(components),
        "ecosystems": dict(ecosystems),
        "format": sbom.get("bomFormat", "CycloneDX"),
        "spec_version": sbom.get("specVersion", "1.5"),
    }


def bfsi_context_boost(file_path: str, snippet: str) -> bool:
    text = f"{file_path} {snippet}".lower()
    return any(kw in text for kw in BFSI_KEYWORDS)
