from typing import Protocol


class LLMProvider(Protocol):
    """Abstraction over an LLM backend.

    Implementations return raw JSON text. Validation is the caller's
    responsibility; providers are never trusted blindly.
    """

    async def generate_json(self, prompt: str) -> str: ...
