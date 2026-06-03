"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """UniShield orchestrator and SCR agent configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenClaw
    openclaw_gateway_ws_url: str = "ws://openclaw:18789/gateway"
    openclaw_api_key: str = ""
    openclaw_mock_mode: bool = True

    # Model providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_max_connections: int = 50

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "unishield-orchestrator"

    # PostgreSQL
    postgres_dsn: str = "postgresql://unishield:unishield@localhost:5432/unishield"
    postgres_min_pool: int = 5
    postgres_max_pool: int = 20

    # SCR
    scr_batch_size: int = 200
    scr_ai_concurrency: int = 5
    scr_max_file_size_kb: int = 500

    # Orchestrator
    human_gate_timeout_hours: int = 4
    max_agent_retries: int = 3


settings = Settings()
