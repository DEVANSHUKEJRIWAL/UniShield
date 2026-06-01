"""Agent presence helpers for dashboard and status APIs."""

from datetime import UTC, datetime

LISTENING_STALE_SECONDS = 120


def effective_agent_status(status: str, last_run_at: datetime | None) -> str:
    """Treat stale listening workers as idle."""
    if status != "listening" or not last_run_at:
        return status
    if last_run_at.tzinfo is None:
        last_run_at = last_run_at.replace(tzinfo=UTC)
    age = (datetime.now(UTC) - last_run_at).total_seconds()
    return "idle" if age > LISTENING_STALE_SECONDS else "listening"
