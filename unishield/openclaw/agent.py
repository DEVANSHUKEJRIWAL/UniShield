"""OpenClaw agent base class stub for UniShield agents."""

from abc import ABC, abstractmethod
from typing import Any


class Agent(ABC):
    """Base class for all UniShield OpenClaw agents."""

    name: str = "base-agent"
    version: str = "0.0.0"

    @abstractmethod
    async def run(self, input: Any) -> Any:
        """Execute the agent's main workflow."""
        ...
