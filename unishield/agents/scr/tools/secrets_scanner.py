"""Secrets scanner — detects leaked credentials (stub)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SecretsScanner:
    """Scans files for leaked secrets and credentials."""

    async def run(self, files: list[str]) -> list[dict]:
        findings: list[dict] = []
        for file_path in files:
            if "secret" in file_path.lower() or ".env" in file_path:
                findings.append(
                    {
                        "secret_type": "api_key",
                        "file_path": file_path,
                        "line_number": 5,
                        "masked_value": "sk-****abcd",
                        "entropy_score": 4.5,
                        "verified_live": False,
                        "git_history_exposed": True,
                    }
                )
        logger.debug("Secrets scan found %d findings", len(findings))
        return findings
