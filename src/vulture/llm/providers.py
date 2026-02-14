from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from vulture.config import Settings
from vulture.types import ModelResponse

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    timeout_sec: int


class LLMProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=float(config.timeout_sec),
        )

    def complete_text(self, *, model: str, prompt: str) -> ModelResponse:
        response = self.client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
        )
        text = getattr(response, "output_text", "") or ""
        raw = response.model_dump() if hasattr(response, "model_dump") else {}
        return ModelResponse(content=text, raw=raw)

    def complete_json(self, *, model: str, prompt: str) -> dict[str, Any]:
        text_response = self.complete_text(model=model, prompt=prompt)
        return parse_json(text_response.content)


def parse_json(content: str) -> dict[str, Any]:
    candidate = content.strip()
    if not candidate:
        return {}

    if "```" in candidate:
        parts = candidate.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") and part.endswith("}"):
                candidate = part
                break

    try:
        value = json.loads(candidate)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON model output")
        return {}


class ProviderPool:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._openai: LLMProvider | None = None
        self._local: LLMProvider | None = None

    def openai(self) -> LLMProvider:
        if self._openai is None:
            self._openai = LLMProvider(
                ProviderConfig(
                    name="openai",
                    base_url=self.settings.openai_base_url,
                    api_key=self.settings.openai_api_key,
                    timeout_sec=self.settings.openai_timeout_sec,
                )
            )
        return self._openai

    def local(self) -> LLMProvider:
        if self._local is None:
            self._local = LLMProvider(
                ProviderConfig(
                    name="local",
                    base_url=self.settings.local_llm_base_url,
                    api_key=self.settings.local_llm_api_key,
                    timeout_sec=self.settings.local_llm_timeout_sec,
                )
            )
        return self._local
