import pytest

from ai_web_research_agent.config.settings import Settings
from ai_web_research_agent.domain.agent import (
    AgentRequest,
)
from ai_web_research_agent.domain.research import (
    ExtractedRecord,
    ExtractionField,
)
from ai_web_research_agent.infrastructure.llm import MockLLMProvider
from ai_web_research_agent.infrastructure.persistence.database import (
    get_session_factory,
    init_db,
)
from ai_web_research_agent.infrastructure.persistence.repository import (
    ResearchRepository,
)
from ai_web_research_agent.services.agent import AgentOrchestrator

HTML = "<html><head><title>Page</title></head><body><h1>Laptop</h1><p>Only $999</p></body></html>"

QUERIES = '{"queries": ["laptops price"]}'
EXTRACT_FULL = '{"name": "Laptop", "price": "$999"}'
EXTRACT_MISSING_PRICE = '{"name": "Laptop", "price": ""}'
SUMMARY = '{"summary": "Laptop costs $999."}'


class FakeDiscoverer:
    def __init__(self, *rounds: list[str]) -> None:
        self._rounds = list(rounds)
        self.calls: list[str] = []

    async def discover(self, query: str, limit: int) -> list[str]:
        self.calls.append(query)

        if not self._rounds:
            return []

        return self._rounds.pop(0)[:limit]


def make_fields() -> list[ExtractionField]:
    return [
        ExtractionField(name="name", description="Product name"),
        ExtractionField(name="price", description="Price"),
    ]


def make_request(
    *,
    max_retries: int = 2,
    candidate_urls: list[str] | None = None,
) -> AgentRequest:
    return AgentRequest(
        goal="Find laptop price",
        fields=make_fields(),
        max_retries=max_retries,
        candidate_urls=candidate_urls or [],
    )


def make_orchestrator(
    discoverer: FakeDiscoverer | None = None,
    provider: MockLLMProvider | None = None,
    repository: ResearchRepository | None = None,
) -> AgentOrchestrator:
    return AgentOrchestrator(
        llm_provider=provider or MockLLMProvider(),
        discoverer=discoverer or FakeDiscoverer(),
        repository=repository,
    )


@pytest.mark.asyncio
async def test_plan_returns_queries_from_llm():
    orchestrator = make_orchestrator(
        provider=MockLLMProvider(responses=[QUERIES]),
    )

    queries = await orchestrator._plan(make_request(), ["price"])

    assert queries == ["laptops price"]


@pytest.mark.asyncio
async def test_plan_falls_back_to_default_query_on_invalid_output():
    orchestrator = make_orchestrator(
        provider=MockLLMProvider(responses=["{invalid json"]),
    )

    queries = await orchestrator._plan(make_request(), ["price"])

    assert queries == ["Find laptop price price"]


@pytest.mark.asyncio
async def test_plan_falls_back_when_queries_empty():
    orchestrator = make_orchestrator(
        provider=MockLLMProvider(responses=['{"queries": []}']),
    )

    queries = await orchestrator._plan(make_request(), [])

    assert queries == ["Find laptop price"]


@pytest.mark.asyncio
async def test_full_run_with_candidate_url(httpx_mock):
    httpx_mock.add_response(
        url="https://a.com/1",
        status_code=200,
        headers={"content-type": "text/html"},
        text=HTML,
    )

    orchestrator = make_orchestrator(
        provider=MockLLMProvider(responses=[QUERIES, EXTRACT_FULL, SUMMARY]),
    )

    result = await orchestrator.run(make_request(candidate_urls=["https://a.com/1"]))

    assert result.status == "completed"
    assert result.missing_fields == []
    assert result.sources_used == ["https://a.com/1"]
    assert result.summary == "Laptop costs $999."

    by_field = {finding.field: finding for finding in result.findings}

    assert by_field["name"].value == "Laptop"
    assert by_field["price"].value == "$999"
    assert by_field["price"].conflicts == 0

    assert "plan" in result.steps
    assert "synthesize" in result.steps
    assert any(step.startswith("extract:") for step in result.steps)


@pytest.mark.asyncio
async def test_stops_extracting_once_all_fields_found(httpx_mock):
    httpx_mock.add_response(
        url="https://a.com/1",
        status_code=200,
        headers={"content-type": "text/html"},
        text=HTML,
    )

    orchestrator = make_orchestrator(
        provider=MockLLMProvider(responses=[QUERIES, EXTRACT_FULL, SUMMARY]),
    )

    result = await orchestrator.run(
        make_request(candidate_urls=["https://a.com/1", "https://a.com/2"])
    )

    assert result.sources_used == ["https://a.com/1"]
    assert result.missing_fields == []


@pytest.mark.asyncio
async def test_retries_discovery_to_fill_missing_fields(httpx_mock):
    httpx_mock.add_response(
        url="https://a.com/1",
        status_code=200,
        headers={"content-type": "text/html"},
        text="<html><body>Laptop</body></html>",
    )
    httpx_mock.add_response(
        url="https://b.com/2",
        status_code=200,
        headers={"content-type": "text/html"},
        text="<html><body>Laptop costs $999</body></html>",
    )

    discoverer = FakeDiscoverer(
        ["https://a.com/1"],
        ["https://b.com/2"],
    )

    orchestrator = make_orchestrator(
        discoverer=discoverer,
        provider=MockLLMProvider(
            responses=[
                QUERIES,
                EXTRACT_MISSING_PRICE,
                QUERIES,
                EXTRACT_FULL,
                SUMMARY,
            ]
        ),
    )

    result = await orchestrator.run(make_request())

    assert result.status == "completed"
    assert result.missing_fields == []
    assert result.sources_used == ["https://a.com/1", "https://b.com/2"]
    assert discoverer.calls == ["laptops price", "laptops price"]
    assert result.steps.count("discover") == 2


@pytest.mark.asyncio
async def test_incomplete_research_reports_missing_fields(httpx_mock):
    httpx_mock.add_response(
        url="https://a.com/1",
        status_code=200,
        headers={"content-type": "text/html"},
        text=HTML,
    )

    orchestrator = make_orchestrator(
        provider=MockLLMProvider(responses=[QUERIES, EXTRACT_MISSING_PRICE, SUMMARY]),
    )

    result = await orchestrator.run(make_request(max_retries=0, candidate_urls=["https://a.com/1"]))

    assert result.status == "completed"
    assert result.missing_fields == ["price"]

    by_field = {finding.field: finding for finding in result.findings}

    assert by_field["name"].value == "Laptop"
    assert "price" not in by_field


@pytest.mark.asyncio
async def test_stops_when_discovery_returns_no_new_sources(httpx_mock):
    httpx_mock.add_response(
        url="https://a.com/1",
        status_code=200,
        headers={"content-type": "text/html"},
        text="<html><body>Laptop</body></html>",
    )

    discoverer = FakeDiscoverer(
        ["https://a.com/1"],
        [],
        [],
    )

    orchestrator = make_orchestrator(
        discoverer=discoverer,
        provider=MockLLMProvider(
            responses=[
                QUERIES,
                EXTRACT_MISSING_PRICE,
                QUERIES,
                QUERIES,
            ]
        ),
    )

    result = await orchestrator.run(make_request(max_retries=3))

    assert result.status == "completed"
    assert result.missing_fields == ["price"]
    assert result.sources_used == ["https://a.com/1"]
    assert result.steps.count("discover") == 1


@pytest.mark.asyncio
async def test_persists_session_sources_pages_and_records(
    database_url,
    httpx_mock,
):
    settings = Settings(database_url=database_url)

    await init_db(settings)

    repository = ResearchRepository(
        session_factory=get_session_factory(settings),
    )

    httpx_mock.add_response(
        url="https://a.com/1",
        status_code=200,
        headers={"content-type": "text/html"},
        text=HTML,
    )

    orchestrator = make_orchestrator(
        provider=MockLLMProvider(responses=[QUERIES, EXTRACT_FULL, SUMMARY]),
        repository=repository,
    )

    result = await orchestrator.run(make_request(candidate_urls=["https://a.com/1"]))

    assert result.session_id is not None

    session = await repository.get_session(result.session_id)

    assert session is not None
    assert session.status == "completed"
    assert session.goal == "Find laptop price"

    records, total = await repository.list_records(result.session_id)

    assert total == 1
    assert records[0].fields == {"name": "Laptop", "price": "$999"}


def test_resolve_picks_majority_value_and_counts_conflicts():
    records = [
        ExtractedRecord(
            source_url="https://a.com/1",
            fields={"name": "Laptop", "price": "$999"},
            confidence=0.9,
        ),
        ExtractedRecord(
            source_url="https://a.com/2",
            fields={"name": "Laptop", "price": "$999"},
            confidence=0.8,
        ),
        ExtractedRecord(
            source_url="https://a.com/3",
            fields={"name": "Laptop", "price": "$1200"},
            confidence=0.7,
        ),
    ]

    findings = {
        finding.field: finding
        for finding in AgentOrchestrator._resolve(
            make_fields(),
            records,
        )
    }

    price = findings["price"]

    assert price.value == "$999"
    assert price.conflicts == 1
    assert set(price.sources) == {"https://a.com/1", "https://a.com/2"}


def test_resolve_breaks_count_tie_by_confidence():
    records = [
        ExtractedRecord(
            source_url="https://a.com/1",
            fields={"price": "$999"},
            confidence=0.9,
        ),
        ExtractedRecord(
            source_url="https://a.com/2",
            fields={"price": "$1200"},
            confidence=0.5,
        ),
    ]

    findings = AgentOrchestrator._resolve(make_fields(), records)

    price = next(finding for finding in findings if finding.field == "price")

    assert price.value == "$999"
