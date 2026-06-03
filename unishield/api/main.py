"""FastAPI application for UniShield orchestrator."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from openclaw_sdk.core.config import ClientConfig

from unishield.agents.scr.scr_runner import SCRRunner
from unishield.api.routes import health, workflows
from unishield.config.settings import settings
from unishield.infrastructure.kafka_client import KafkaClient
from unishield.infrastructure.model_router import ModelRouter
from unishield.infrastructure.postgres_client import PostgresClient
from unishield.infrastructure.redis_client import RedisClient
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _postgres, _kafka, _orchestrator, _state_store, _action_gate

    _redis = RedisClient.get_instance()
    await _redis.connect()

    _postgres = PostgresClient()
    try:
        await _postgres.connect()
        await _postgres.init_schema()
    except OSError as exc:
        logger.error(
            "Cannot connect to PostgreSQL at %s — is it running?\n"
            "  Start infra: docker compose -f unishield/docker-compose.yml up -d redis postgres kafka\n"
            "  Or run: ./scripts/unishield-infra-up.sh",
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
    _orchestrator = Orchestrator(
        openclaw_config,
        shared_memory,
        _state_store,
        decision_engine,
        finalizer,
        _kafka.producer,
        settings,
        scr_runner,
    )

    logger.info("UniShield orchestrator started (openclaw_mock=%s)", settings.openclaw_mock_mode)
    yield

    await _kafka.stop()
    await _postgres.disconnect()
    await _redis.disconnect()


app = FastAPI(title="UniShield Orchestrator", version="2.0.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(workflows.router)


def create_app() -> FastAPI:
    return app
