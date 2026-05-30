"""API key sanitization and live-vs-mock gating for external services."""

from __future__ import annotations

import re

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
        from packages.core.config import settings

        key = settings.anthropic_api_key
    cleaned = sanitize_api_key(key)
    if not cleaned or _looks_like_placeholder(cleaned):
        return False
    return anthropic_key_format_valid(cleaned)
