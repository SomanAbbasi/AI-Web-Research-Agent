import json
import logging

from ai_web_research_agent.domain.agent import (
    AgentRequest,
    AgentResult,
    FieldResolution,
    SourceDiscoverer,
)
from ai_web_research_agent.domain.crawling import PageContent
from ai_web_research_agent.domain.llm import LLMProvider
from ai_web_research_agent.domain.research import (
    ExtractedRecord,
    ExtractionField,
    ResearchRequest,
)
from ai_web_research_agent.infrastructure.llm import LLMError
from ai_web_research_agent.infrastructure.persistence.repository import (
    ResearchRepository,
)
from ai_web_research_agent.services.research import (
    ResearchError,
    extract_page,
    fetch_page,
)
from ai_web_research_agent.services.research_service import (
    to_record_model,
)
from ai_web_research_agent.services.url_normalizer import normalize_url

logger = logging.getLogger(__name__)

MAX_PLAN_QUERIES = 3

PLAN_PROMPT = (
    "You are a web research planner. Decompose the research goal into a small "
    "number of focused search queries that will find pages answering it.\n"
    "Return ONLY a single JSON object in this exact shape:\n"
    '{{"queries": ["query one", "query two"]}}\n'
    "Do not include explanations.\n\n"
    "Research goal: {goal}\n"
    "Information needed: {fields}\n"
    "Still missing: {missing}"
)

SYNTHESIS_PROMPT = (
    "You are a research analyst. Write a concise summary of the findings below.\n"
    "Return ONLY a single JSON object in this exact shape:\n"
    '{{"summary": "two or three sentences"}}\n'
    "Do not invent facts that are not in the findings.\n\n"
    "Research goal: {goal}\n\n"
    "Resolved findings:\n{findings}\n\n"
    "Missing fields: {missing}\n"
    "Sources consulted: {sources}"
)


class AgentError(Exception):
    """Raised when the autonomous research run fails irrecoverably."""


class AgentOrchestrator:
    """Runs a full autonomous research loop over multiple sources.

    The flow is a deterministic state machine: plan, discover, extract,
    validate, retry on missing information, resolve conflicts, synthesize.
    An explicit graph framework (e.g. LangGraph) was deliberately avoided
    because the control flow is a single loop with one decision point, and a
    hand-written orchestrator is simpler to follow and test.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        discoverer: SourceDiscoverer,
        repository: ResearchRepository | None = None,
    ) -> None:
        self._llm_provider = llm_provider
        self._discoverer = discoverer
        self._repository = repository

    async def run(self, request: AgentRequest) -> AgentResult:
        session_id = None

        if self._repository is not None:
            session = await self._repository.create_session(request.goal)
            session_id = session.id

        steps: list[str] = []
        missing = [field.name for field in request.fields]

        try:
            known_sources = set(request.candidate_urls)
            pending = list(request.candidate_urls)
            records: list[ExtractedRecord] = []
            used_sources: list[str] = []
            retries_left = request.max_retries

            queries = await self._plan(request, missing)
            steps.append("plan")

            discovered = await self._discover(queries, request.max_sources)
            fresh = [u for u in discovered if u not in known_sources]
            known_sources.update(fresh)
            pending.extend(fresh)

            if fresh:
                steps.append("discover")

            while missing:
                if not pending:
                    if retries_left > 0:
                        queries = await self._plan(request, missing)
                        steps.append("plan")

                        discovered = await self._discover(
                            queries,
                            request.max_sources,
                        )
                        fresh = [u for u in discovered if u not in known_sources]
                        known_sources.update(fresh)

                        if not fresh:
                            steps.append("validate")
                            break

                        pending.extend(fresh)
                        retries_left -= 1
                        steps.append("discover")
                    else:
                        break

                if not pending:
                    break

                url = pending.pop(0)

                if self._repository is not None and session_id is not None:
                    await self._repository.add_source(session_id, url)

                try:
                    content, record = await self._extract_source(
                        request,
                        url,
                        session_id,
                    )
                except ResearchError:
                    logger.exception("Extraction failed for %s", url)
                    continue

                steps.append(f"extract:{url}")
                used_sources.append(content.url)
                records.append(record)

                missing = self._missing_fields(request.fields, records)

                if len(used_sources) >= request.max_sources:
                    break

            steps.append("validate")

            findings = self._resolve(request.fields, records)
            missing = self._missing_fields(request.fields, records)

            summary = await self._synthesize(
                request,
                findings,
                missing,
                used_sources,
            )
            steps.append("synthesize")

            if self._repository is not None and session_id is not None:
                await self._repository.complete_session(
                    session_id,
                    status="completed",
                )

            return AgentResult(
                goal=request.goal,
                session_id=session_id,
                status="completed",
                summary=summary,
                findings=findings,
                missing_fields=missing,
                sources_used=used_sources,
                steps=steps,
            )
        except Exception:
            logger.exception("Autonomous research failed")
            if self._repository is not None and session_id is not None:
                await self._repository.complete_session(
                    session_id,
                    status="failed",
                )
            raise

    async def _extract_source(
        self,
        request: AgentRequest,
        url: str,
        session_id: str | None,
    ) -> tuple[PageContent, ExtractedRecord]:
        research_request = ResearchRequest(
            goal=request.goal,
            source_url=url,
            fields=request.fields,
        )

        content = await fetch_page(research_request)
        record = await extract_page(
            research_request,
            content,
            llm_provider=self._llm_provider,
        )

        if self._repository is not None and session_id is not None:
            await self._repository.add_page(
                session_id,
                url=content.url,
                title=content.title,
                text=content.text,
                status_code=content.status_code,
                via_browser=content.via_browser,
            )
            await self._repository.add_record(
                session_id,
                to_record_model(session_id, record),
            )

        return content, record

    async def _plan(
        self,
        request: AgentRequest,
        missing: list[str],
    ) -> list[str]:
        fields = ", ".join(
            f"{field.name} ({field.description or 'no description'})" for field in request.fields
        )

        prompt = PLAN_PROMPT.format(
            goal=request.goal,
            fields=fields or "none",
            missing=", ".join(missing) or "none",
        )

        try:
            raw = await self._llm_provider.generate_json(prompt)
        except LLMError:
            logger.warning("LLM planning failed; using fallback query")
            return [self._default_query(request, missing)]

        queries = self._parse_queries(raw)

        if not queries:
            return [self._default_query(request, missing)]

        return queries[:MAX_PLAN_QUERIES]

    async def _discover(
        self,
        queries: list[str],
        limit: int,
    ) -> list[str]:
        urls: list[str] = []

        for query in queries:
            for url in await self._discoverer.discover(
                query,
                limit - len(urls),
            ):
                normalized = normalize_url(url)

                if normalized in urls:
                    continue

                urls.append(normalized)

                if len(urls) >= limit:
                    return urls

        return urls

    async def _synthesize(
        self,
        request: AgentRequest,
        findings: list[FieldResolution],
        missing: list[str],
        used_sources: list[str],
    ) -> str:
        if not findings and not missing:
            return self._fallback_summary(request, findings, missing)

        findings_lines = "\n".join(
            f"- {finding.field}: {finding.value} "
            f"(sources: {', '.join(finding.sources)}; conflicts: {finding.conflicts})"
            for finding in findings
        )

        prompt = SYNTHESIS_PROMPT.format(
            goal=request.goal,
            findings=findings_lines or "none",
            missing=", ".join(missing) or "none",
            sources=", ".join(used_sources) or "none",
        )

        try:
            raw = await self._llm_provider.generate_json(prompt)
        except LLMError:
            logger.warning("LLM synthesis failed; using fallback summary")
            return self._fallback_summary(request, findings, missing)

        data = self._parse_json_object(raw)

        if data is None:
            return self._fallback_summary(request, findings, missing)

        summary = data.get("summary")

        if isinstance(summary, str) and summary.strip():
            return summary.strip()

        return self._fallback_summary(request, findings, missing)

    @staticmethod
    def _missing_fields(
        fields: list[ExtractionField],
        records: list[ExtractedRecord],
    ) -> list[str]:
        return [f.name for f in fields if not _has_value(f.name, records)]

    @staticmethod
    def _resolve(
        fields: list[ExtractionField],
        records: list[ExtractedRecord],
    ) -> list[FieldResolution]:
        resolutions: list[FieldResolution] = []

        for field in fields:
            candidates = _candidates(field.name, records)

            if not candidates:
                continue

            counts: dict[str, int] = {}
            confidences: dict[str, float] = {}

            for value, confidence, _source in candidates:
                counts[value] = counts.get(value, 0) + 1
                confidences[value] = max(
                    confidences.get(value, 0.0),
                    confidence or 0.0,
                )

            winner = max(
                counts,
                key=lambda value: (counts[value], confidences[value]),
            )

            winning = [
                (confidence, source) for value, confidence, source in candidates if value == winner
            ]

            present = [confidence for confidence, _source in winning if confidence is not None]

            confidence = max(present) if present else None

            resolutions.append(
                FieldResolution(
                    field=field.name,
                    value=winner,
                    confidence=confidence,
                    sources=[source for _confidence, source in winning],
                    conflicts=len(counts) - 1,
                )
            )

        return resolutions

    @staticmethod
    def _default_query(
        request: AgentRequest,
        missing: list[str],
    ) -> str:
        parts = [request.goal]

        if missing:
            parts.extend(missing)

        return " ".join(parts)

    @staticmethod
    def _parse_queries(raw_output: str) -> list[str]:
        data = AgentOrchestrator._parse_json_object(raw_output)

        if data is None:
            return []

        queries = data.get("queries")

        if not isinstance(queries, list):
            return []

        return [str(query).strip() for query in queries if isinstance(query, str) and query.strip()]

    @staticmethod
    def _parse_json_object(raw_output: str) -> dict[str, object] | None:
        stripped = raw_output.strip()

        if stripped.startswith("```"):
            stripped = stripped.strip("`").removeprefix("json")

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, dict):
            return None

        return parsed

    @staticmethod
    def _fallback_summary(
        request: AgentRequest,
        findings: list[FieldResolution],
        missing: list[str],
    ) -> str:
        total = len(request.fields)
        found = len(findings)

        if missing:
            return (
                f"Researched {request.goal}. Found {found} of {total} "
                f"fields; still missing: {', '.join(missing)}."
            )

        return (
            f"Researched {request.goal}. Found all {total} fields across "
            f"{len(findings)} resolved findings."
        )


def _has_value(field_name: str, records: list[ExtractedRecord]) -> bool:
    return any(record.fields.get(field_name, "") for record in records)


def _candidates(
    field_name: str,
    records: list[ExtractedRecord],
) -> list[tuple[str, float | None, str]]:
    return [
        (record.fields[field_name], record.confidence, record.source_url)
        for record in records
        if record.fields.get(field_name, "")
    ]
