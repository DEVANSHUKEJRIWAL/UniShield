"""API key sanitization and live-vs-mock gating for external services."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REPO_ENV = _REPO_ROOT / ".env"

_PLACEHOLDER_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"placeholder",
        r"your[-_]?key",
        r"changeme",
        r"insert[-_]?key",
        r"xxx+",
        r"sk-ant-\.{3}",
    )
)


def sanitize_api_key(value: str | None) -> str:
    """Strip whitespace and surrounding quotes from env-loaded secrets."""
    if not value:
        return ""
    cleaned = str(value).strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in "\"'":
        cleaned = cleaned[1:-1].strip()
    return cleaned


def anthropic_key_format_valid(key: str) -> bool:
    """Anthropic keys use the sk-ant- prefix."""
    return key.startswith("sk-ant-") and len(key) >= 24


def _looks_like_placeholder(key: str) -> bool:
    return any(p.search(key) for p in _PLACEHOLDER_PATTERNS)


def anthropic_live_enabled(key: str | None = None) -> bool:
    """
    True when a non-placeholder Anthropic key is present with valid format.
    Invalid or placeholder keys fall back to structured mock handlers.
    """
    if key is None:
        from core.config import settings

        key = settings.anthropic_api_key
    cleaned = sanitize_api_key(key)
    if not cleaned or _looks_like_placeholder(cleaned):
        return False
    return anthropic_key_format_valid(cleaned)


def read_repo_dotenv_anthropic_key() -> str:
    """Read ANTHROPIC_API_KEY directly from repo-root .env (ignores shell env)."""
    if not _REPO_ENV.is_file():
        return ""
    try:
        from dotenv import dotenv_values

        raw = dotenv_values(_REPO_ENV).get("ANTHROPIC_API_KEY", "")
        return sanitize_api_key(raw or "")
    except Exception:
        return ""


def anthropic_key_fingerprint(key: str) -> dict[str, Any]:
    """Safe key metadata for diagnostics (never returns full secret)."""
    cleaned = sanitize_api_key(key)
    return {
        "length": len(cleaned),
        "prefix": cleaned[:12] + "..." if len(cleaned) > 12 else cleaned,
        "suffix": "..." + cleaned[-4:] if len(cleaned) > 4 else "",
        "format_valid": anthropic_key_format_valid(cleaned),
    }


def sync_anthropic_key_from_repo_dotenv() -> dict[str, Any]:
    """
    Prefer repo-root .env when the process has a different Anthropic key.

    Fixes local dev when a stale shell export or Docker env overrides .env.
    """
    from core.config import settings

    file_key = read_repo_dotenv_anthropic_key()
    runtime_key = settings.anthropic_api_key
    info: dict[str, Any] = {
        "repo_dotenv_path": str(_REPO_ENV),
        "repo_dotenv_present": _REPO_ENV.is_file(),
        "runtime": anthropic_key_fingerprint(runtime_key),
        "repo_dotenv": anthropic_key_fingerprint(file_key),
        "keys_match": runtime_key == file_key if file_key else None,
        "synced": False,
    }
    if file_key and file_key != runtime_key and anthropic_key_format_valid(file_key):
        object.__setattr__(settings, "anthropic_api_key", file_key)
        info["synced"] = True
        info["runtime"] = anthropic_key_fingerprint(file_key)
        info["keys_match"] = True
    return info
