"""FastAPI application for UniShield orchestrator."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from openclaw_sdk.core.config import ClientConfig

from unishield.agents.cma.cma_runner import CMARunner
from unishield.agents.reporting.reporting_runner import ReportingRunner
from unishield.agents.scr.scr_runner import SCRRunner
from unishield.api.routes import health, repos, workflows
from unishield.config.settings import settings
from unishield.connectors.repo_registry import RepoRegistry
from unishield.infrastructure.kafka_client import KafkaClient
from unishield.infrastructure.model_router import ModelRouter
from unishield.infrastructure.postgres_client import PostgresClient
from unishield.infrastructure.redis_client import RedisClient
from unishield.infrastructure.vault_client import VaultClient
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import SharedMemoryClient
from unishield.orchestrator.action_gate import ActionGate
from unishield.orchestrator.decision_engine import DecisionEngine
from unishield.orchestrator.finalizer import WorkflowFinalizer
from unishield.orchestrator.orchestrator import Orchestrator
from unishield.orchestrator.workflow_state import WorkflowStateStore

logger = logging.getLogger(__name__)

_redis: Optional[RedisClient] = None
_postgres: Optional[PostgresClient] = None
_kafka: Optional[KafkaClient] = None
_orchestrator: Optional[Orchestrator] = None
_state_store: Optional[WorkflowStateStore] = None
_action_gate: Optional[ActionGate] = None
_repo_registry: Optional[RepoRegistry] = None


def get_orchestrator() -> Orchestrator:
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized")
    return _orchestrator


def get_state_store() -> WorkflowStateStore:
    if _state_store is None:
        raise RuntimeError("State store not initialized")
    return _state_store


def get_postgres() -> PostgresClient:
    if _postgres is None:
        raise RuntimeError("Postgres not initialized")
    return _postgres


def get_action_gate() -> ActionGate:
    if _action_gate is None:
        raise RuntimeError("ActionGate not initialized")
    return _action_gate


def get_repo_registry() -> RepoRegistry:
    if _repo_registry is None:
        raise RuntimeError("RepoRegistry not initialized")
    return _repo_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _postgres, _kafka, _orchestrator, _state_store, _action_gate, _repo_registry

    _redis = RedisClient.get_instance()
    await _redis.connect()

    _postgres = PostgresClient()
    try:
        await _postgres.connect()
        await _postgres.init_schema()
        vault = VaultClient(local_path=settings.vault_path)
        _repo_registry = RepoRegistry(_postgres, vault, settings)
        await _repo_registry.init_schema()
    except OSError as exc:
        logger.error(
            "Cannot connect to PostgreSQL at %s — is it running?\n"
            "  Diagnose:  ./scripts/unishield-doctor.sh\n"
            "  Start infra: ./scripts/unishield-infra-up.sh\n"
            "  Note: orchestrator Postgres uses host port 5434 (not 5432).\n"
            "  If using main docker-compose postgres on 5432, set:\n"
            "    export POSTGRES_DSN=postgresql://unishield:password@localhost:5432/unishield",
            settings.postgres_dsn,
        )
        raise RuntimeError(f"PostgreSQL connection failed: {exc}") from exc

    _kafka = KafkaClient()
    await _kafka.start()

    shared_memory = SharedMemoryClient(_redis.client)
    personal_memory = PersonalMemoryClient(_redis.client)
    _state_store = WorkflowStateStore(_redis.client)
    decision_engine = DecisionEngine()
    finalizer = WorkflowFinalizer(shared_memory, _postgres, _kafka, _state_store)
    _action_gate = ActionGate(_postgres, _kafka.producer, _state_store)

    openclaw_config = ClientConfig(
        gateway_ws_url=settings.openclaw_gateway_ws_url,
        api_key=settings.openclaw_api_key,
        mock_mode=settings.openclaw_mock_mode,
    )
    model_router = ModelRouter(settings)
    scr_runner = SCRRunner(
        openclaw_config,
        shared_memory,
        personal_memory,
        _kafka.producer,
        settings,
        model_router,
    )
    cma_runner = CMARunner(shared_memory, settings, model_router)
    reporting_runner = ReportingRunner(shared_memory, settings, model_router)
    _orchestrator = Orchestrator(
        openclaw_config,
        shared_memory,
        _state_store,
        decision_engine,
        finalizer,
        _kafka.producer,
        settings,
        scr_runner,
        cma_runner,
        reporting_runner,
    )

    logger.info(
        "UniShield orchestrator started (openclaw_mock=%s, gateway=%s)",
        settings.openclaw_mock_mode,
        settings.openclaw_gateway_ws_url,
    )
    yield

    await _kafka.stop()
    await _postgres.disconnect()
    await _redis.disconnect()


app = FastAPI(title="UniShield Orchestrator", version="2.0.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(workflows.router)
app.include_router(repos.router)


def create_app() -> FastAPI:
    return app
