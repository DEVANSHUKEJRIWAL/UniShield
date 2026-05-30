"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated environment configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    postgres_uri: str = "postgresql+asyncpg://unishield:password@localhost:5432/unishield"
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


settings = Settings()
