"""Base connector interface for UniShield integrations."""

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """All inbound/outbound integration adapters extend this class."""

    def __init__(self, tenant_id: str, config: dict[str, Any]) -> None:
        self.tenant_id = tenant_id
        self.config = config

    @abstractmethod
    async def ingest(self) -> list[dict[str, Any]]:
        """Pull or receive events from the external source."""
        ...

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute an outbound action — requires OPA policy permission."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support act()")
