"""Repo-root .env Anthropic key sync."""

from unittest.mock import patch

from packages.core.api_keys import (
    read_repo_dotenv_anthropic_key,
    sync_anthropic_key_from_repo_dotenv,
)


def test_sync_anthropic_key_from_repo_dotenv(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    good_key = "sk-ant-api03-" + "a" * 24
    env_file.write_text(f"ANTHROPIC_API_KEY={good_key}\n")

    import packages.core.api_keys as api_keys

    monkeypatch.setattr(api_keys, "_REPO_ENV", env_file)

    from packages.core.config import settings

    monkeypatch.setattr(settings, "anthropic_api_key", "wrong-key")
    info = sync_anthropic_key_from_repo_dotenv()

    assert info["synced"] is True
    assert settings.anthropic_api_key == good_key


def test_read_repo_dotenv_anthropic_key_strips_quotes(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    key = "sk-ant-api03-" + "b" * 24
    env_file.write_text(f'ANTHROPIC_API_KEY="{key}"\n')

    import packages.core.api_keys as api_keys

    monkeypatch.setattr(api_keys, "_REPO_ENV", env_file)
    assert read_repo_dotenv_anthropic_key() == key
