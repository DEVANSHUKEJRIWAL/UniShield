"""Vault-backed secret loading with .env fallback (Week 9)."""

from functools import lru_cache
from typing import Any

from packages.core.config import settings


@lru_cache(maxsize=64)
def load_secret(path: str, key: str = "value") -> str:
    """
    Load secret from HashiCorp Vault KV v2, falling back to empty string.
    Path example: secret/unishield/anthropic
    """
    if not settings.vault_addr or not settings.vault_token:
        return ""
    try:
        import hvac

        client = hvac.Client(url=settings.vault_addr, token=settings.vault_token)
        if not client.is_authenticated():
            return ""
        mount, _, secret_path = path.partition("/")
        if mount != "secret":
            secret_path = path
        resp = client.secrets.kv.v2.read_secret_version(path=secret_path.replace("secret/data/", "").replace("secret/", ""))
        data = resp.get("data", {}).get("data", {})
        if isinstance(data, dict):
            return str(data.get(key, data.get("api_key", "")))
    except Exception:
        return ""
    return ""


def resolve_api_key(env_value: str, vault_path: str) -> str:
    """Prefer env var, then Vault."""
    if env_value:
        return env_value
    return load_secret(vault_path, "api_key")


def bootstrap_secrets_into_settings() -> dict[str, Any]:
    """Load optional secrets from Vault into runtime (called at startup)."""
    loaded: dict[str, Any] = {}
    if not settings.vault_token:
        return loaded
    mappings = {
        "anthropic_api_key": "secret/unishield/anthropic",
        "splunk_token": "secret/unishield/splunk",
        "nvd_api_key": "secret/unishield/nvd",
    }
    for attr, path in mappings.items():
        current = getattr(settings, attr, "")
        if not current:
            secret = load_secret(path, "api_key")
            if secret:
                object.__setattr__(settings, attr, secret)
                loaded[attr] = True
    return loaded
