"""Application configuration via environment variables."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SQLITE = f"sqlite+aiosqlite:///{_REPO_ROOT / 'data' / 'unishield.db'}"


def _default_database_uri() -> str:
    """Use SQLite when Docker/Postgres is unavailable (no-docker dev)."""
    if os.getenv("UNISHIELD_USE_SQLITE", "").lower() in ("1", "true", "yes"):
        return _DEFAULT_SQLITE
    if os.getenv("POSTGRES_URI", "").startswith("sqlite"):
        return os.environ["POSTGRES_URI"]
    return "postgresql+asyncpg://unishield:password@localhost:5432/unishield"


class Settings(BaseSettings):
    """Validated environment configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    postgres_uri: str = ""
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    redis_url: str = "redis://localhost:6379"
    qdrant_url: str = "http://localhost:6333"
    elasticsearch_url: str = "http://localhost:9200"
    timescale_uri: str = "postgresql+asyncpg://unishield:password@localhost:5433/unishield_metrics"

    vault_addr: str = "http://localhost:8200"
    vault_token: str = ""

    jwt_secret: str = "change-me-in-production-use-rs256-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    refresh_expire_days: int = 7

    frontend_url: str = "http://localhost:3000"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    virustotal_api_key: str = ""
    shodan_api_key: str = ""
    nvd_api_key: str = ""
    splunk_url: str = ""
    splunk_token: str = ""

    auto_seed: bool = True

    def model_post_init(self, __context: object) -> None:
        """Apply SQLite when no-docker mode is enabled."""
        if os.getenv("UNISHIELD_USE_SQLITE", "").lower() in ("1", "true", "yes"):
            object.__setattr__(self, "postgres_uri", _DEFAULT_SQLITE)
        elif not self.postgres_uri:
            object.__setattr__(self, "postgres_uri", _default_database_uri())

    @property
    def database_uri(self) -> str:
        """Resolved database connection URI."""
        return self.postgres_uri or _default_database_uri()

    @property
    def uses_sqlite(self) -> bool:
        """True when using local SQLite file (no Docker required)."""
        return self.database_uri.startswith("sqlite")


settings = Settings()
