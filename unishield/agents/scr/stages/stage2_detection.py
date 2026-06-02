"""Stage 2 — language detection and rule set selection."""

from __future__ import annotations

import logging
from pathlib import Path

from unishield.memory.personal_memory import PersonalMemoryClient

logger = logging.getLogger(__name__)

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
}


class DetectionStage:
    """Detects languages and selects analysis rule sets."""

    def __init__(self, personal_memory: PersonalMemoryClient) -> None:
        self._memory = personal_memory

    async def run(self, scan_id: str, files: list[str]) -> dict:
        language_map: dict[str, str] = {}
        languages: set[str] = set()

        for file_path in files:
            ext = Path(file_path).suffix.lower()
            lang = LANGUAGE_MAP.get(ext, "unknown")
            language_map[file_path] = lang
            if lang != "unknown":
                languages.add(lang)

        rule_sets = {lang: f"rules/{lang}" for lang in languages}
        detection = {
            "language_map": language_map,
            "languages": sorted(languages),
            "rule_sets": rule_sets,
        }
        await self._memory.save_detection(scan_id, detection)
        logger.info("Detection: languages=%s", languages)
        return detection
