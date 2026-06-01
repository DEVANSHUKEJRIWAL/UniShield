"""SAST / secret / dependency scanning subprocess tools (Phase 2)."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any


def _path_exists(path: str) -> bool:
    """Return True when path is non-empty and exists on disk."""
    return bool(path) and Path(path).exists()


async def _run_cmd(cmd: list[str], cwd: str | None = None, timeout: int = 120) -> tuple[int, str, str]:
    if cwd and not _path_exists(cwd):
        return -1, "", "missing cwd"
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
    return proc.returncode or 0, stdout.decode(), stderr.decode()


async def run_gitleaks(path: str) -> list[dict[str, Any]]:
    """Run gitleaks detect when installed."""
    if not shutil.which("gitleaks") or not _path_exists(path):
        return []
    code, out, err = await _run_cmd(
        ["gitleaks", "detect", "--source", path, "--no-banner", "--report-format", "json", "--report-path", "/dev/stdout"],
        timeout=180,
    )
    if code not in (0, 1):
        return []
    try:
        data = json.loads(out or "[]")
        if isinstance(data, list):
            return [
                {
                    "file": i.get("File", ""),
                    "line": i.get("StartLine", 0),
                    "rule": i.get("RuleID", "secret"),
                    "severity": "ERROR",
                    "live": True,
                    "description": i.get("Description", "secret detected"),
                }
                for i in data
            ]
    except json.JSONDecodeError:
        pass
    return []


async def run_pip_audit(requirements_file: str) -> list[dict[str, Any]]:
    if not shutil.which("pip-audit") or not Path(requirements_file).is_file():
        return []
    code, out, _ = await _run_cmd(["pip-audit", "-r", requirements_file, "--format", "json"], timeout=120)
    if code != 0:
        return []
    try:
        data = json.loads(out)
        deps = data.get("dependencies", data) if isinstance(data, dict) else data
        findings: list[dict[str, Any]] = []
        for dep in deps if isinstance(deps, list) else []:
            for vuln in dep.get("vulns", []):
                findings.append(
                    {
                        "package": dep.get("name"),
                        "cve": vuln.get("id"),
                        "severity": "high",
                        "live": True,
                        "description": vuln.get("description", "")[:200],
                    }
                )
        return findings
    except json.JSONDecodeError:
        return []


async def run_npm_audit(project_dir: str) -> list[dict[str, Any]]:
    if not shutil.which("npm") or not _path_exists(project_dir):
        return []
    code, out, _ = await _run_cmd(["npm", "audit", "--json"], cwd=project_dir, timeout=120)
    try:
        data = json.loads(out)
        advisories = data.get("vulnerabilities", {})
        findings: list[dict[str, Any]] = []
        for name, adv in advisories.items():
            findings.append(
                {
                    "package": name,
                    "severity": adv.get("severity", "moderate"),
                    "live": True,
                    "description": f"npm advisory {name}",
                }
            )
        return findings
    except json.JSONDecodeError:
        return []


async def run_trivy_fs(path: str) -> list[dict[str, Any]]:
    if not shutil.which("trivy") or not _path_exists(path):
        return []
    code, out, _ = await _run_cmd(["trivy", "fs", "--format", "json", "--quiet", path], timeout=180)
    if code not in (0, 1):
        return []
    try:
        data = json.loads(out)
        findings: list[dict[str, Any]] = []
        for result in data.get("Results", []):
            for vuln in result.get("Vulnerabilities") or []:
                findings.append(
                    {
                        "file": result.get("Target", path),
                        "cve": vuln.get("VulnerabilityID"),
                        "severity": vuln.get("Severity", "MEDIUM"),
                        "live": True,
                        "description": vuln.get("Title", "")[:200],
                    }
                )
        return findings
    except json.JSONDecodeError:
        return []
