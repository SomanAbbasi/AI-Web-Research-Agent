import json
import logging
import re

from openai import AsyncOpenAI

from ai_web_research_agent.config.settings import Settings
from ai_web_research_agent.domain.llm import LLMProvider

logger = logging.getLogger(__name__)


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Factory for LLM providers selected by configuration."""
    if settings.llm_provider == "mock":
        return MockLLMProvider()

    if settings.llm_provider == "openai":
        if not settings.llm_api_key:
            raise ValueError("LLM_PROVIDER=openai requires LLM_API_KEY to be set")

        return OpenAILLMProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")


class LLMError(Exception):
    """Raised when the LLM backend fails or returns unusable output."""


class OpenAILLMProvider:
    """LLM provider backed by the OpenAI chat completions API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout,
        )
        self._model = model

    async def generate_json(self, prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": "Return only valid JSON matching the request.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        if content is None:
            raise LLMError("Empty response from LLM provider")

        return content


class MockLLMProvider:
    """Deterministic provider for demos and tests.

    With no canned responses configured it echoes every requested field as
    an empty string, exercising the full extraction pipeline without an API
    key. Canned responses are returned in order, one per call.
    """

    def __init__(
        self,
        responses: list[str] | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self.calls: list[str] = []

    async def generate_json(self, prompt: str) -> str:
        self.calls.append(prompt)

        if self._responses:
            return self._responses.pop(0)

        field_names = re.findall(
            r"^- ([a-zA-Z0-9_ ]+?):",
            prompt,
            re.MULTILINE,
        )

        return json.dumps({name: "" for name in field_names})
