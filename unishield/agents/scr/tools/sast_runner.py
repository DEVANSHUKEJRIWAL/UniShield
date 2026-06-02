"""SAST runner — static analysis via Semgrep (stub for tests)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class SASTRunner:
    """Runs static analysis rules against source files."""

    async def run(self, files: list[str], rule_sets: dict) -> list[dict]:
        findings: list[dict] = []
        for file_path in files:
            if "vulnerable" in file_path or "sql" in file_path.lower():
                findings.append(
                    {
                        "finding_id": str(uuid.uuid4()),
                        "file_path": file_path,
                        "language": "python",
                        "line_start": 10,
                        "line_end": 12,
                        "column_start": 0,
                        "column_end": 40,
                        "code_snippet": "query = f'SELECT * FROM users WHERE id={user_id}'",
                        "severity": "HIGH",
                        "confidence": 0.9,
                        "category": "injection",
                        "rule_id": "python.sql-injection",
                        "cwe_id": "CWE-89",
                    }
                )
        logger.debug("SAST found %d findings in %d files", len(findings), len(files))
        return findings
