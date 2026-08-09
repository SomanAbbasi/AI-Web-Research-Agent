from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from ai_web_research_agent.config.settings import get_settings
from ai_web_research_agent.domain.research import (
    ExtractedRecord as DomainRecord,
)
from ai_web_research_agent.infrastructure.persistence.database import (
    get_session_factory,
)
from ai_web_research_agent.infrastructure.persistence.repository import (
    ResearchRepository,
)
from ai_web_research_agent.models import (
    ExtractedRecord,
    ResearchSession,
)

_session_factory_override: async_sessionmaker[AsyncSession] | None = None


def _session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory_override is not None:
        return _session_factory_override

    return get_session_factory(get_settings())


def _repository() -> ResearchRepository:
    return ResearchRepository(_session_factory())


async def create_research_session(goal: str) -> ResearchSession:
    return await _repository().create_session(goal)


async def list_sessions() -> list[ResearchSession]:
    return await _repository().list_sessions()


async def get_session(
    session_id: str,
) -> ResearchSession | None:
    return await _repository().get_session(session_id)


async def complete_session(
    session_id: str,
    status: str = "completed",
    error: str | None = None,
) -> ResearchSession | None:
    return await _repository().complete_session(
        session_id,
        status=status,
        error=error,
    )


async def save_source(session_id: str, url: str) -> bool:
    return await _repository().add_source(session_id, url)


async def save_page(
    session_id: str,
    *,
    url: str,
    title: str | None,
    text: str,
    status_code: int,
    via_browser: bool,
) -> bool:
    return await _repository().add_page(
        session_id,
        url,
        title,
        text,
        status_code,
        via_browser,
    )


def to_record_model(
    session_id: str,
    record: DomainRecord,
) -> ExtractedRecord:
    return ExtractedRecord(
        session_id=session_id,
        source_url=record.source_url,
        fields=record.fields,
        missing_fields=record.missing_fields,
        has_missing=bool(record.missing_fields),
        searchable_text=" ".join(record.fields.values()),
        confidence=record.confidence,
    )


async def save_extraction(
    session_id: str,
    record: DomainRecord,
) -> bool:
    model = to_record_model(session_id, record)

    return await _repository().add_record(session_id, model)


async def list_records(
    session_id: str,
    *,
    min_confidence: float | None = None,
    search: str | None = None,
    include_missing: bool | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[ExtractedRecord], int]:
    return await _repository().list_records(
        session_id,
        min_confidence=min_confidence,
        search=search,
        include_missing=include_missing,
        limit=limit,
        offset=offset,
    )
