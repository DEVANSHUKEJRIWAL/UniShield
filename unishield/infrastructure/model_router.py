"""Vendor-agnostic LLM router."""

from __future__ import annotations

import asyncio
import json
import logging
from enum import Enum
from typing import Optional, Type

from pydantic import BaseModel

from unishield.config.settings import Settings

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    CODE_ANALYSIS = "code_analysis"
    THREAT_INTEL = "threat_intel"
    COMPLIANCE_MAPPING = "compliance_mapping"
    EXECUTIVE_NARRATIVE = "executive_narrative"
    STRUCTURED_OUTPUT = "structured_output"
    BEHAVIORAL_ANALYSIS = "behavioral_analysis"


class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


PROVIDER_CONFIGS = {
    ModelProvider.ANTHROPIC: {"model": "claude-sonnet-4-6"},
    ModelProvider.OPENAI: {"model": "gpt-4o"},
    ModelProvider.GOOGLE: {"model": "gemini-1.5-pro"},
}

TASK_ROUTING: dict[TaskType, list[ModelProvider]] = {
    TaskType.CODE_ANALYSIS: [ModelProvider.ANTHROPIC, ModelProvider.OPENAI, ModelProvider.GOOGLE],
    TaskType.THREAT_INTEL: [ModelProvider.ANTHROPIC, ModelProvider.OPENAI, ModelProvider.GOOGLE],
    TaskType.COMPLIANCE_MAPPING: [ModelProvider.ANTHROPIC, ModelProvider.GOOGLE, ModelProvider.OPENAI],
    TaskType.EXECUTIVE_NARRATIVE: [ModelProvider.ANTHROPIC, ModelProvider.OPENAI, ModelProvider.GOOGLE],
    TaskType.STRUCTURED_OUTPUT: [ModelProvider.OPENAI, ModelProvider.ANTHROPIC, ModelProvider.GOOGLE],
    TaskType.BEHAVIORAL_ANALYSIS: [ModelProvider.OPENAI, ModelProvider.ANTHROPIC, ModelProvider.GOOGLE],
}


class RateLimitError(Exception):
    pass


class ProviderUnavailableError(Exception):
    pass


class AllProvidersFailedError(Exception):
    def __init__(
        self,
        task_type: TaskType,
        providers_tried: list[ModelProvider],
        last_error: Exception | None,
    ) -> None:
        self.task_type = task_type
        self.providers_tried = providers_tried
        self.last_error = last_error
        super().__init__(
            f"All providers failed for {task_type}: "
            f"{[p.value for p in providers_tried]}. Last error: {last_error}"
        )


class ModelRouter:
    """Routes LLM calls to the best available provider with fallback."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._anthropic = None
        self._openai = None
        self._google_model = None

        if settings.anthropic_api_key:
            import anthropic

            self._anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        if settings.openai_api_key:
            import openai

            self._openai = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        if settings.google_api_key:
            import google.generativeai as genai

            genai.configure(api_key=settings.google_api_key)
            self._google_model = genai.GenerativeModel(PROVIDER_CONFIGS[ModelProvider.GOOGLE]["model"])

    async def complete(
        self,
        task_type: TaskType,
        prompt: str,
        output_schema: Optional[Type[BaseModel]] = None,
        max_tokens: int = 4096,
        fallback: bool = True,
    ) -> str:
        providers = TASK_ROUTING[task_type]
        last_error: Exception | None = None

        if output_schema:
            schema_str = output_schema.model_json_schema(indent=2)
            prompt = (
                f"{prompt}\n\nRespond with a single valid JSON object "
                f"matching this exact schema. No markdown, no explanation:\n"
                f"{schema_str}"
            )

        for provider in providers:
            try:
                return await self._call_provider(provider, prompt, max_tokens)
            except (RateLimitError, ProviderUnavailableError) as exc:
                last_error = exc
                if not fallback:
                    raise
                continue

        raise AllProvidersFailedError(task_type, providers, last_error)

    async def _call_provider(
        self,
        provider: ModelProvider,
        prompt: str,
        max_tokens: int,
    ) -> str:
        if provider == ModelProvider.ANTHROPIC:
            if not self._anthropic:
                raise ProviderUnavailableError("Anthropic API key not configured")
            response = await self._anthropic.messages.create(
                model=PROVIDER_CONFIGS[ModelProvider.ANTHROPIC]["model"],
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        if provider == ModelProvider.OPENAI:
            if not self._openai:
                raise ProviderUnavailableError("OpenAI API key not configured")
            response = await self._openai.chat.completions.create(
                model=PROVIDER_CONFIGS[ModelProvider.OPENAI]["model"],
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""

        if provider == ModelProvider.GOOGLE:
            if not self._google_model:
                raise ProviderUnavailableError("Google API key not configured")
            response = await asyncio.to_thread(
                self._google_model.generate_content,
                prompt,
                generation_config={"max_output_tokens": max_tokens},
            )
            return response.text

        raise ValueError(f"Unknown provider: {provider}")

    async def score_json(self, prompt: str, client_id: str = "") -> dict:
        """Score a finding — returns parsed JSON dict."""
        try:
            text = await self.complete(
                TaskType.STRUCTURED_OUTPUT,
                prompt,
                max_tokens=512,
                fallback=True,
            )
            return json.loads(text)
        except Exception as exc:
            raise ProviderUnavailableError(str(exc)) from exc
