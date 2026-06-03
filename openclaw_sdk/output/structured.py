"""Structured output parsing from OpenClaw agent responses."""

from __future__ import annotations

import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel

from openclaw_sdk.core.types import ExecutionResult

T = TypeVar("T", bound=BaseModel)


class StructuredOutput:
    """Parse agent responses into validated Pydantic models."""

    @staticmethod
    async def execute(agent, prompt: str, model: Type[T]) -> T:
        result: ExecutionResult = await agent.execute(prompt)
        data = StructuredOutput._parse_json(result.content)
        return model.model_validate(data)

    @staticmethod
    def _parse_json(content: str) -> dict:
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                return json.loads(match.group())
            raise
