"""OpenClaw callback handlers."""

from abc import ABC


class CallbackHandler(ABC):
    """Lifecycle hooks for OpenClaw agent execution."""

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        pass

    async def on_execution_end(self, agent_id: str, result) -> None:
        pass

    async def on_execution_error(self, agent_id: str, error: Exception) -> None:
        pass
