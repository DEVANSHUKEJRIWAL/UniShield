"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """UniShield orchestrator and SCR agent configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenClaw
    openclaw_gateway_ws_url: str = "ws://127.0.0.1:18789/"
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
    postgres_dsn: str = "postgresql://unishield:unishield@localhost:5434/unishield"
    postgres_min_pool: int = 5
    postgres_max_pool: int = 20

    # SCR
    scr_batch_size: int = 200
    scr_ai_concurrency: int = 5
    scr_max_file_size_kb: int = 500
    scr_use_ai_fp_filter: bool = False

    # Orchestrator
    human_gate_timeout_hours: int = 4
    max_agent_retries: int = 3
    inline_workflows: bool = False

    # Neo4j (attack path graph)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_browser_url: str = "http://localhost:7474/browser/"

    # VCS connectors
    gitlab_base_url: str = "https://gitlab.com"
    bitbucket_url: str = "https://api.bitbucket.org"
    bitbucket_is_cloud: bool = True
    vault_path: str = "/tmp/unishield-vault"


settings = Settings()
