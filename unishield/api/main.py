"""FastAPI application for UniShield orchestrator."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI

from unishield.api.routes import health, workflows
from unishield.infrastructure.kafka_client import KafkaClient
from unishield.infrastructure.postgres_client import PostgresClient
from unishield.infrastructure.redis_client import RedisClient
from unishield.memory.shared_memory import SharedMemoryClient
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _postgres, _kafka, _orchestrator, _state_store

    _redis = RedisClient.get_instance()
    await _redis.connect()

    _postgres = PostgresClient()
    await _postgres.connect()
    await _postgres.init_schema()

    _kafka = KafkaClient()
    await _kafka.start()

    shared_memory = SharedMemoryClient(_redis.client)
    _state_store = WorkflowStateStore(_redis.client)
    decision_engine = DecisionEngine()
    finalizer = WorkflowFinalizer(shared_memory, _postgres, _kafka, _state_store)
    _orchestrator = Orchestrator(_kafka, shared_memory, _state_store, decision_engine, finalizer)

    logger.info("UniShield orchestrator started")
    yield

    await _kafka.stop()
    await _postgres.disconnect()
    await _redis.disconnect()


app = FastAPI(title="UniShield Orchestrator", version="1.0.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(workflows.router)


def create_app() -> FastAPI:
    return app
