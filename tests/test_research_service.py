from ai_web_research_agent.config.settings import Settings
from ai_web_research_agent.domain.research import (
    ExtractedRecord as DomainRecord,
)
from ai_web_research_agent.infrastructure.persistence.database import (
    get_session_factory,
    init_db,
)
from ai_web_research_agent.services import research_service


async def _override_service_factory(database_url, monkeypatch):
    settings = Settings(database_url=database_url)

    await init_db(settings)

    factory = get_session_factory(settings)

    monkeypatch.setattr(
        research_service,
        "_session_factory_override",
        factory,
    )


async def test_service_create_session(database_url, monkeypatch):
    await _override_service_factory(database_url, monkeypatch)

    session = await research_service.create_research_session("research goal")

    fetched = await research_service.get_session(session.id)

    assert fetched is not None
    assert fetched.goal == "research goal"


async def test_service_save_extraction_maps_metadata(
    database_url,
    monkeypatch,
):
    await _override_service_factory(database_url, monkeypatch)

    session = await research_service.create_research_session("goal")

    record = DomainRecord(
        source_url="https://a.com/p",
        fields={"name": "Laptop"},
        missing_fields=["price"],
        confidence=0.5,
    )

    await research_service.save_extraction(session.id, record)

    records, _total = await research_service.list_records(session.id)

    assert len(records) == 1
    assert records[0].has_missing is True
    assert records[0].missing_fields == ["price"]
    assert records[0].searchable_text == "Laptop"
    assert records[0].confidence == 0.5


async def test_service_save_extraction_deduplicates(
    database_url,
    monkeypatch,
):
    await _override_service_factory(database_url, monkeypatch)

    session = await research_service.create_research_session("goal")

    record = DomainRecord(
        source_url="https://a.com/p",
        fields={"name": "Laptop"},
        missing_fields=[],
        confidence=1.0,
    )

    await research_service.save_extraction(session.id, record)

    duplicate = DomainRecord(
        source_url="https://a.com/p",
        fields={"name": "Laptop"},
        missing_fields=[],
        confidence=1.0,
    )

    await research_service.save_extraction(session.id, duplicate)

    records, total = await research_service.list_records(session.id)

    assert total == 1
    assert len(records) == 1
