import json
import logging

from ai_web_research_agent.domain.llm import LLMProvider
from ai_web_research_agent.domain.research import (
    ExtractedRecord,
    ResearchRequest,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a precise web-research assistant. Given a research goal, a list of "
    "fields and a page's text, extract the requested information.\n"
    "Return ONLY a single JSON object with exactly the requested field names as "
    "keys and their values as strings. Use an empty string when a field cannot "
    "be found. Do not include keys that were not requested and do not include "
    "explanations."
)


class ExtractionError(Exception):
    """Raised when the LLM output cannot be turned into structured data."""


class ExtractionService:
    """Turns page text into validated structured records using an LLM."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        max_context: int = 12_000,
    ) -> None:
        self._llm_provider = llm_provider
        self._max_context = max_context

    async def extract(
        self,
        request: ResearchRequest,
        page_text: str,
    ) -> ExtractedRecord:
        prompt = self._build_prompt(request, page_text)

        raw_output = await self._llm_provider.generate_json(prompt)

        parsed = self._parse_json(raw_output)

        fields, missing = self._validate(request, parsed)

        confidence = None

        if request.fields:
            confidence = (len(request.fields) - len(missing)) / len(request.fields)

        return ExtractedRecord(
            source_url=request.source_url,
            fields=fields,
            missing_fields=missing,
            confidence=confidence,
        )

    def _build_prompt(
        self,
        request: ResearchRequest,
        page_text: str,
    ) -> str:
        field_lines = "\n".join(
            f"- {field.name}: {field.description or 'No description'}" for field in request.fields
        )

        text = page_text[: self._max_context]

        return (
            f"Research goal: {request.goal}\n\n"
            f"Requested fields:\n{field_lines}\n\n"
            f"Page text (from {request.source_url}):\n{text}"
        )

    @staticmethod
    def _parse_json(raw_output: str) -> dict[str, object]:
        stripped = raw_output.strip()

        if stripped.startswith("```"):
            stripped = stripped.strip("`").removeprefix("json")

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"LLM returned invalid JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ExtractionError(f"LLM output is not a JSON object: {type(parsed).__name__}")

        return parsed

    @staticmethod
    def _validate(
        request: ResearchRequest,
        parsed: dict[str, object],
    ) -> tuple[dict[str, str], list[str]]:
        fields: dict[str, str] = {}
        missing: list[str] = []

        for field in request.fields:
            value = parsed.get(field.name)

            if value is None or value == "":
                missing.append(field.name)
                continue

            fields[field.name] = str(value)

        return fields, missing
