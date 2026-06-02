"""SBOM generator — CycloneDX supply chain manifest (stub)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SBOMGenerator:
    """Generates Software Bill of Materials for scanned files."""

    async def run(self, files: list[str]) -> dict:
        components = []
        for file_path in files:
            if file_path.endswith(("package.json", "requirements.txt", "pyproject.toml")):
                components.append(
                    {
                        "name": file_path.split("/")[-1],
                        "type": "library",
                        "version": "unknown",
                    }
                )
        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "components": components,
            "dependencies": [],
        }
