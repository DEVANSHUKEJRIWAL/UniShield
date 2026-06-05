"""FastAPI application for UniShield orchestrator."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from openclaw_sdk.core.config import ClientConfig

from backend.agents.openclaw_setup import configure_openclaw_agents
from backend.cma.cma_runner import CMARunner
from backend.reporting.reporting_runner import ReportingRunner
from backend.scr.scr_progress import ScrProgressTracker
from backend.scr.scr_runner import SCRRunner
from backend.memory.repo_memory import RepoMemoryClient
from backend.orchestrator.action_executor import ActionExecutor
from backend.orchestrator.bulk_scan_store import BulkScanStore
from backend.orchestrator.event_consumers import OrchestratorEventConsumers
from backend.orchestrator.human_gate_watcher import HumanGateWatcher
from backend.orchestrator.metrics_history import MetricsHistoryStore
from backend.orchestrator.scheduler import WorkflowScheduler
from backend.api.routes import attack_path, health, hitl, repos, triggers, workflows
from backend.config.settings import settings
from backend.connectors.repo_registry import RepoRegistry
from backend.infrastructure.kafka_client import KafkaClient
from backend.infrastructure.model_router import ModelRouter
from backend.infrastructure.postgres_client import PostgresClient
from backend.infrastructure.redis_client import RedisClient
from backend.infrastructure.vault_client import VaultClient
from backend.memory.personal_memory import PersonalMemoryClient
from backend.memory.shared_memory import SharedMemoryClient
from backend.orchestrator.action_gate import ActionGate
from backend.orchestrator.decision_engine import DecisionEngine
from backend.orchestrator.finalizer import WorkflowFinalizer
from backend.orchestrator.hitl_service import HitlService
from backend.orchestrator.orchestrator import Orchestrator
from backend.orchestrator.workflow_state import WorkflowStateStore

logger = logging.getLogger(__name__)

_redis: Optional[RedisClient] = None
_postgres: Optional[PostgresClient] = None
_kafka: Optional[KafkaClient] = None
_orchestrator: Optional[Orchestrator] = None
_state_store: Optional[WorkflowStateStore] = None
_action_gate: Optional[ActionGate] = None
_repo_registry: Optional[RepoRegistry] = None
_shared_memory: Optional[SharedMemoryClient] = None
_scr_progress: Optional[ScrProgressTracker] = None
_hitl_service: Optional[HitlService] = None
_action_executor: Optional[ActionExecutor] = None
_bulk_scan_store: Optional[BulkScanStore] = None
_metrics_history: Optional[MetricsHistoryStore] = None
_event_consumers: Optional[OrchestratorEventConsumers] = None
_human_gate_watcher: Optional[HumanGateWatcher] = None
_scheduler: Optional[WorkflowScheduler] = None
_repo_memory: Optional[RepoMemoryClient] = None


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


def get_shared_memory() -> SharedMemoryClient:
    if _shared_memory is None:
        raise RuntimeError("Shared memory not initialized")
    return _shared_memory


def get_scr_progress() -> ScrProgressTracker:
    if _scr_progress is None:
        raise RuntimeError("SCR progress tracker not initialized")
    return _scr_progress


def get_action_executor() -> ActionExecutor:
    if _action_executor is None:
        raise RuntimeError("ActionExecutor not initialized")
    return _action_executor


def get_bulk_scan_store() -> BulkScanStore:
    if _bulk_scan_store is None:
        raise RuntimeError("BulkScanStore not initialized")
    return _bulk_scan_store


def get_metrics_history() -> MetricsHistoryStore:
    if _metrics_history is None:
        raise RuntimeError("MetricsHistoryStore not initialized")
    return _metrics_history


def get_hitl_service() -> HitlService:
    if _hitl_service is None:
        raise RuntimeError("HITL service not initialized")
    return _hitl_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _postgres, _kafka, _orchestrator, _state_store, _action_gate, _repo_registry
    global _shared_memory, _scr_progress, _hitl_service, _repo_memory
    global _action_executor, _bulk_scan_store, _metrics_history
    global _event_consumers, _human_gate_watcher, _scheduler

    configure_openclaw_agents(mock_mode=settings.openclaw_mock_mode)

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
    _shared_memory = shared_memory
    personal_memory = PersonalMemoryClient(_redis.client)
    _scr_progress = ScrProgressTracker(_redis.client)
    _repo_memory = RepoMemoryClient(_redis.client)
    _state_store = WorkflowStateStore(_redis.client)
    decision_engine = DecisionEngine()
    _metrics_history = MetricsHistoryStore(_postgres)
    _bulk_scan_store = BulkScanStore(_redis.client, _postgres)
    finalizer = WorkflowFinalizer(
        shared_memory, _postgres, _kafka, _state_store, metrics_store=_metrics_history
    )
    _action_gate = ActionGate(_postgres, _kafka.producer, _state_store)
    _action_executor = ActionExecutor(_postgres, _action_gate, _kafka.producer)
    _hitl_service = HitlService(_action_gate, _state_store, shared_memory, _postgres)

    openclaw_config = ClientConfig(
        gateway_ws_url=settings.openclaw_gateway_ws_url,
        api_key=settings.openclaw_api_key,
        mock_mode=settings.openclaw_mock_mode,
    )
    model_router = ModelRouter(settings)
    if not settings.anthropic_api_key and not settings.openai_api_key:
        logger.warning(
            "AI enrichment disabled — set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable Stage 7 analysis"
        )
    scr_runner = SCRRunner(
        openclaw_config,
        shared_memory,
        personal_memory,
        _kafka.producer,
        settings,
        model_router,
        progress_tracker=_scr_progress,
        action_gate=_action_gate,
        repo_memory=_repo_memory,
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

    _human_gate_watcher = HumanGateWatcher(_state_store, _kafka.producer)
    await _human_gate_watcher.start()

    if settings.event_driven_orchestration:
        _event_consumers = OrchestratorEventConsumers(_orchestrator)
        await _event_consumers.start()

    def _trigger_factory():
        from backend.orchestrator.trigger_handler import TriggerHandler

        return TriggerHandler(_orchestrator)

    _scheduler = WorkflowScheduler(_redis.client, _trigger_factory)
    await _scheduler.start()

    logger.info(
        "UniShield orchestrator started (openclaw_mock=%s, gateway=%s, event_driven=%s, scr_kafka=%s)",
        settings.openclaw_mock_mode,
        settings.openclaw_gateway_ws_url,
        settings.event_driven_orchestration,
        settings.scr_via_kafka,
    )
    yield

    if _event_consumers:
        await _event_consumers.stop()
    if _human_gate_watcher:
        await _human_gate_watcher.stop()
    if _scheduler:
        await _scheduler.stop()

    await _kafka.stop()
    await _postgres.disconnect()
    await _redis.disconnect()


app = FastAPI(title="UniShield Orchestrator", version="2.0.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(workflows.router)
app.include_router(repos.router)
app.include_router(hitl.router)
app.include_router(triggers.router)
app.include_router(attack_path.router)


def create_app() -> FastAPI:
    return app
