import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ai_web_research_agent.models import (
    CrawledPage,
    ExtractedRecord,
    ResearchSession,
    Source,
    utc_now,
)


class ResearchRepository:
    """Persistence operations for research sessions and their data.

    Pages, sources and records are deduplicated per session by URL.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def create_session(self, goal: str) -> ResearchSession:
        session_model = ResearchSession(
            id=uuid.uuid4().hex,
            goal=goal,
        )

        async with self._session_factory() as session:
            session.add(session_model)
            await session.commit()

        return session_model

    async def complete_session(
        self,
        session_id: str,
        status: str = "completed",
        error: str | None = None,
    ) -> ResearchSession | None:
        async with self._session_factory() as session:
            result = await session.get(ResearchSession, session_id)

            if result is None:
                return None

            result.status = status
            result.error = error
            result.completed_at = result.completed_at or utc_now()

            await session.commit()

            return result

    async def get_session(
        self,
        session_id: str,
    ) -> ResearchSession | None:
        async with self._session_factory() as session:
            return await session.get(ResearchSession, session_id)

    async def list_sessions(self) -> list[ResearchSession]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ResearchSession).order_by(ResearchSession.created_at.desc())
            )

            return list(result.scalars().all())

    async def add_source(self, session_id: str, url: str) -> bool:
        return await self._add_deduplicated(
            Source(session_id=session_id, url=url),
        )

    async def add_page(
        self,
        session_id: str,
        url: str,
        title: str | None,
        text: str,
        status_code: int,
        via_browser: bool,
    ) -> bool:
        return await self._add_deduplicated(
            CrawledPage(
                session_id=session_id,
                url=url,
                title=title,
                text=text,
                status_code=status_code,
                via_browser=via_browser,
            )
        )

    async def add_record(
        self,
        session_id: str,
        record: ExtractedRecord,
    ) -> bool:
        return await self._add_deduplicated(record)

    async def list_records(
        self,
        session_id: str,
        *,
        min_confidence: float | None = None,
        search: str | None = None,
        include_missing: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ExtractedRecord], int]:
        statement = select(ExtractedRecord).where(ExtractedRecord.session_id == session_id)

        if min_confidence is not None:
            statement = statement.where(ExtractedRecord.confidence >= min_confidence)

        if search:
            statement = statement.where(ExtractedRecord.searchable_text.ilike(f"%{search}%"))

        if include_missing is not None:
            statement = statement.where(ExtractedRecord.has_missing == include_missing)

        async with self._session_factory() as session:
            count_statement = select(func.count()).select_from(statement.subquery())

            total = (await session.execute(count_statement)).scalar_one()

            statement = (
                statement.order_by(ExtractedRecord.created_at.desc()).limit(limit).offset(offset)
            )

            records = list((await session.execute(statement)).scalars().all())

            return records, total

    async def get_record(self, record_id: int) -> ExtractedRecord | None:
        async with self._session_factory() as session:
            return await session.get(ExtractedRecord, record_id)

    async def _add_deduplicated(self, model: object) -> bool:
        async with self._session_factory() as session:
            session.add(model)

            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return False

            return True
