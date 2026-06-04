"""Stage 2 — language detection, framework detection, Semgrep ruleset selection."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from unishield.agents.scr.tools.repo_acquirer import read_repo_file
from unishield.memory.personal_memory import PersonalMemoryClient

logger = logging.getLogger(__name__)

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".tf": "terraform",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sql": "sql",
    ".html": "html",
    ".jsp": "java",
    ".xml": "xml",
}

SEMGREP_RULESETS: dict[str, list[str]] = {
    "python": ["p/python", "p/flask", "p/django"],
    "javascript": ["p/javascript", "p/nodejs", "p/react"],
    "typescript": ["p/typescript", "p/nodejs", "p/react"],
    "go": ["p/golang"],
    "java": ["p/java"],
    "ruby": ["p/ruby"],
    "php": ["p/php"],
    "terraform": ["p/terraform"],
    "docker": ["p/docker"],
    "kubernetes": ["p/kubernetes"],
    "csharp": ["p/csharp"],
}

FRAMEWORK_MARKERS: list[tuple[str, str, list[str]]] = [
    ("spring", "java", ["org.springframework", "spring-boot"]),
    ("express", "javascript", ["express", "require('express')"]),
    ("django", "python", ["django", "DJANGO_SETTINGS_MODULE"]),
    ("flask", "python", ["from flask", "Flask("]),
    ("rails", "ruby", ["Rails.application"]),
    ("laravel", "php", ["Illuminate\\", "laravel/framework"]),
    ("terraform", "terraform", ["provider \"aws\"", "resource \"aws_"]),
    ("docker", "docker", ["FROM ", "docker-compose"]),
    ("kubernetes", "kubernetes", ["apiVersion:", "kind: Deployment", "kind: Service"]),
]


class DetectionStage:
    """Detects languages, frameworks, and selects analysis rule sets."""

    def __init__(self, personal_memory: PersonalMemoryClient) -> None:
        self._memory = personal_memory

    async def run(
        self,
        scan_id: str,
        files: list[str],
        *,
        archive_path: str | None = None,
    ) -> dict:
        language_map: dict[str, str] = {}
        languages: set[str] = set()

        for file_path in files:
            ext = Path(file_path).suffix.lower()
            lang = LANGUAGE_MAP.get(ext, "unknown")
            language_map[file_path] = lang
            if lang != "unknown":
                languages.add(lang)

        frameworks = self._detect_frameworks(files, archive_path)
        for fw in frameworks:
            if fw == "docker":
                languages.add("docker")
            elif fw == "kubernetes":
                languages.add("kubernetes")

        rule_sets = self._select_rule_sets(languages, frameworks)
        detection = {
            "language_map": language_map,
            "languages": sorted(languages),
            "frameworks": frameworks,
            "rule_sets": rule_sets,
            "semgrep_configs": self._semgrep_configs(languages, frameworks),
        }
        await self._memory.save_detection(scan_id, detection)
        logger.info("Detection: languages=%s frameworks=%s", languages, frameworks)
        return detection

    def _detect_frameworks(self, files: list[str], archive_path: str | None) -> list[str]:
        detected: set[str] = set()
        scan_files = list(files)
        if archive_path:
            for marker in ("package.json", "pom.xml", "requirements.txt", "pyproject.toml", "go.mod", "Gemfile"):
                candidate = os.path.join(archive_path, marker)
                if os.path.isfile(candidate) and marker not in scan_files:
                    scan_files.append(marker)
            for path in Path(archive_path).rglob("Dockerfile"):
                scan_files.append(str(path.relative_to(archive_path)).replace("\\", "/"))
            for path in Path(archive_path).rglob("*.tf"):
                scan_files.append(str(path.relative_to(archive_path)).replace("\\", "/"))
            for path in Path(archive_path).rglob("*.yaml"):
                scan_files.append(str(path.relative_to(archive_path)).replace("\\", "/"))

        for file_path in scan_files[:200]:
            content = read_repo_file(file_path, archive_path)
            if not content:
                continue
            lowered = content.lower()
            name = Path(file_path).name.lower()
            if name == "dockerfile" or "docker-compose" in name:
                detected.add("docker")
            if file_path.endswith((".tf", ".tfvars")):
                detected.add("terraform")
            if "kind:" in content and "apiversion:" in lowered:
                detected.add("kubernetes")
            for fw, _lang, markers in FRAMEWORK_MARKERS:
                if any(m.lower() in lowered for m in markers):
                    detected.add(fw)
            if name == "package.json":
                try:
                    pkg = json.loads(content)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    if "express" in deps:
                        detected.add("express")
                    if "@nestjs/core" in deps:
                        detected.add("nestjs")
                except json.JSONDecodeError:
                    pass
        return sorted(detected)

    @staticmethod
    def _select_rule_sets(languages: set[str], frameworks: list[str]) -> dict[str, str]:
        rule_sets: dict[str, str] = {}
        for lang in languages:
            configs = SEMGREP_RULESETS.get(lang, ["p/default"])
            rule_sets[lang] = configs[0]
        for fw in frameworks:
            if fw in ("spring",):
                rule_sets["java"] = "p/java"
            elif fw in ("express", "nestjs"):
                rule_sets["javascript"] = "p/nodejs"
            elif fw == "django":
                rule_sets["python"] = "p/django"
            elif fw == "flask":
                rule_sets["python"] = "p/flask"
            elif fw == "terraform":
                rule_sets["terraform"] = "p/terraform"
            elif fw == "docker":
                rule_sets["docker"] = "p/docker"
            elif fw == "kubernetes":
                rule_sets["kubernetes"] = "p/kubernetes"
        return rule_sets

    @staticmethod
    def _semgrep_configs(languages: set[str], frameworks: list[str]) -> list[str]:
        configs: list[str] = ["p/default", "p/security-audit", "p/owasp-top-ten"]
        for lang in languages:
            configs.extend(SEMGREP_RULESETS.get(lang, []))
        if "django" in frameworks:
            configs.append("p/django")
        if "express" in frameworks or "nestjs" in frameworks:
            configs.append("p/nodejs")
        if "terraform" in frameworks:
            configs.append("p/terraform")
        if "docker" in frameworks:
            configs.append("p/docker")
        if "kubernetes" in frameworks:
            configs.append("p/kubernetes")
        # preserve order, dedupe
        seen: set[str] = set()
        unique: list[str] = []
        for cfg in configs:
            if cfg not in seen:
                seen.add(cfg)
                unique.append(cfg)
        return unique
