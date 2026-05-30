"""API key sanitization and Anthropic live-mode gating."""

from packages.core.api_keys import (
    anthropic_key_format_valid,
    anthropic_live_enabled,
    sanitize_api_key,
)


def test_sanitize_api_key_strips_quotes_and_whitespace() -> None:
    assert sanitize_api_key('  "sk-ant-test-key"  ') == "sk-ant-test-key"
    assert sanitize_api_key("'sk-ant-test-key'") == "sk-ant-test-key"


def test_anthropic_key_format_valid() -> None:
    assert anthropic_key_format_valid("sk-ant-api03-" + "x" * 20) is True
    assert anthropic_key_format_valid("not-a-key") is False
    assert anthropic_key_format_valid("sk-ant-short") is False


def test_anthropic_live_enabled_rejects_placeholders() -> None:
    assert anthropic_live_enabled("") is False
    assert anthropic_live_enabled("changeme") is False
    assert anthropic_live_enabled("sk-ant-api03-placeholder") is False
    assert anthropic_live_enabled("sk-ant-api03-" + "a" * 24) is True
