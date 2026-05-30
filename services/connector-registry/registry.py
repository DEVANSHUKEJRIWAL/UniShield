"""Connector registry service."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class ConnectorRegistry:
    """Registry for all inbound/outbound integration adapters."""

    def __init__(self) -> None:
        self._connectors: dict[str, type[BaseConnector]] = {}

    def register(self, name: str, cls: type[BaseConnector]) -> None:
        """Register connector class."""
        self._connectors[name] = cls

    def get(self, name: str, tenant_id: str, config: dict[str, Any]) -> BaseConnector:
        """Instantiate connector."""
        cls = self._connectors.get(name)
        if not cls:
            raise KeyError(f"Unknown connector: {name}")
        return cls(tenant_id=tenant_id, config=config)

    def list_connectors(self) -> list[str]:
        """Return registered connector names."""
        return list(self._connectors.keys())


registry = ConnectorRegistry()

# Auto-register generated connectors
import importlib
import pkgutil
import services.connector_registry.connectors as connectors_pkg

for _, mod_name, _ in pkgutil.iter_modules(connectors_pkg.__path__):
    if mod_name == "base":
        continue
    mod = importlib.import_module(f"services.connector_registry.connectors.{mod_name}")
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, type) and issubclass(obj, BaseConnector) and obj is not BaseConnector:
            registry.register(mod_name, obj)
