"""OpenClaw execution types."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ExecutionResult:
    """Result from an OpenClaw agent execution."""

    success: bool
    content: str
    latency_ms: int
    metadata: Optional[dict[str, Any]] = None

    @classmethod
    def from_json(cls, text: str) -> "ExecutionResult":
        return cls(success=True, content=text, latency_ms=0)
