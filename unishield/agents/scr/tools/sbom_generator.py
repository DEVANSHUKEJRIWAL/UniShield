"""SBOM generator — Syft CycloneDX + Grype/Trivy/OSV dependency scan."""

from __future__ import annotations

import logging

from unishield.agents.scr.tools import scanner_integration as scanners

logger = logging.getLogger(__name__)


class SBOMGenerator:
    """Generates SBOM and scans dependencies for CVEs (CVSS >= 7)."""

    async def run_repo(self, repo_path: str) -> tuple[dict, list[dict], list[str]]:
        tools: list[str] = []
        sbom = await scanners.run_syft_sbom(repo_path)
        if sbom.get("components"):
            tools.append("syft" if any(c.get("purl") for c in sbom.get("components", [])) else "manifest")
        dep_findings = await scanners.run_grype_vulnerabilities(repo_path)
        if dep_findings:
            tools.append("grype")
        return sbom, dep_findings, tools

    async def run(self, files: list[str]) -> dict:
        """Legacy per-batch stub — returns empty; use run_repo instead."""
        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "components": [],
            "dependencies": [],
        }
