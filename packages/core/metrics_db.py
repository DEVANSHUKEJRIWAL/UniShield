"""TimescaleDB metrics store for agent runs, alerts, and API latency (Week 7)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.core.config import settings

_metrics_engine = None
_MetricsSession: async_sessionmaker[AsyncSession] | None = None
_schema_ready = False


def _engine():
    global _metrics_engine, _MetricsSession
    if _metrics_engine is None:
        _metrics_engine = create_async_engine(settings.timescale_uri, echo=False, pool_pre_ping=True)
        _MetricsSession = async_sessionmaker(_metrics_engine, class_=AsyncSession, expire_on_commit=False)
    return _MetricsSession


async def ensure_metrics_schema() -> None:
    """Create hypertables if TimescaleDB is reachable."""
    global _schema_ready
    if _schema_ready:
        return
    session_factory = _engine()
    if session_factory is None:
        return
    ddl = """
    CREATE TABLE IF NOT EXISTS agent_run_metrics (
        time TIMESTAMPTZ NOT NULL,
        tenant_id TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        status TEXT NOT NULL,
        duration_ms DOUBLE PRECISION DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS alert_volume_metrics (
        time TIMESTAMPTZ NOT NULL,
        tenant_id TEXT NOT NULL,
        severity TEXT NOT NULL,
        count INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS api_latency_metrics (
        time TIMESTAMPTZ NOT NULL,
        route TEXT NOT NULL,
        method TEXT NOT NULL,
        latency_ms DOUBLE PRECISION NOT NULL,
        status_code INTEGER NOT NULL
    );
    """
    try:
        async with session_factory() as db:
            for stmt in ddl.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    await db.execute(text(stmt))
            for table in ("agent_run_metrics", "alert_volume_metrics", "api_latency_metrics"):
                try:
                    await db.execute(
                        text(f"SELECT create_hypertable('{table}', 'time', if_not_exists => TRUE)")
                    )
                except Exception:
                    pass
            await db.commit()
        _schema_ready = True
    except Exception:
        pass


async def record_agent_run(
    tenant_id: str,
    agent_name: str,
    status: str,
    duration_ms: float = 0.0,
) -> None:
    """Insert agent run metric."""
    session_factory = _engine()
    if session_factory is None:
        return
    await ensure_metrics_schema()
    try:
        async with session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO agent_run_metrics (time, tenant_id, agent_name, status, duration_ms) "
                    "VALUES (:time, :tenant_id, :agent_name, :status, :duration_ms)"
                ),
                {
                    "time": datetime.now(UTC),
                    "tenant_id": tenant_id,
                    "agent_name": agent_name,
                    "status": status,
                    "duration_ms": duration_ms,
                },
            )
            await db.commit()
    except Exception:
        pass


async def record_alert_volume(tenant_id: str, severity: str, count: int = 1) -> None:
    """Insert alert volume metric."""
    session_factory = _engine()
    if session_factory is None:
        return
    await ensure_metrics_schema()
    try:
        async with session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO alert_volume_metrics (time, tenant_id, severity, count) "
                    "VALUES (:time, :tenant_id, :severity, :count)"
                ),
                {
                    "time": datetime.now(UTC),
                    "tenant_id": tenant_id,
                    "severity": severity,
                    "count": count,
                },
            )
            await db.commit()
    except Exception:
        pass


async def record_api_latency(route: str, method: str, latency_ms: float, status_code: int) -> None:
    """Insert API latency sample."""
    session_factory = _engine()
    if session_factory is None:
        return
    await ensure_metrics_schema()
    try:
        async with session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO api_latency_metrics (time, route, method, latency_ms, status_code) "
                    "VALUES (:time, :route, :method, :latency_ms, :status_code)"
                ),
                {
                    "time": datetime.now(UTC),
                    "route": route,
                    "method": method,
                    "latency_ms": latency_ms,
                    "status_code": status_code,
                },
            )
            await db.commit()
    except Exception:
        pass


async def query_metrics_trends(tenant_id: str, hours: int = 24) -> dict[str, Any]:
    """Aggregate recent metrics for dashboard."""
    session_factory = _engine()
    if session_factory is None:
        return {"tenant_id": tenant_id, "mock": True, "agent_runs": [], "alert_volume": []}
    await ensure_metrics_schema()
    try:
        async with session_factory() as db:
            runs = await db.execute(
                text(
                    "SELECT agent_name, count(*) AS cnt FROM agent_run_metrics "
                    "WHERE tenant_id = :tenant_id AND time > NOW() - make_interval(hours => :hours) "
                    "GROUP BY agent_name ORDER BY cnt DESC LIMIT 10"
                ),
                {"tenant_id": tenant_id, "hours": hours},
            )
            alerts = await db.execute(
                text(
                    "SELECT severity, sum(count) AS total FROM alert_volume_metrics "
                    "WHERE tenant_id = :tenant_id AND time > NOW() - make_interval(hours => :hours) "
                    "GROUP BY severity"
                ),
                {"tenant_id": tenant_id, "hours": hours},
            )
            return {
                "tenant_id": tenant_id,
                "hours": hours,
                "agent_runs": [{"agent": r[0], "count": int(r[1])} for r in runs.fetchall()],
                "alert_volume": [{"severity": r[0], "count": int(r[1])} for r in alerts.fetchall()],
            }
    except Exception:
        return {"tenant_id": tenant_id, "mock": True, "agent_runs": [], "alert_volume": []}
