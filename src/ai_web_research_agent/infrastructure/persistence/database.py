from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from ai_web_research_agent.config.settings import Settings
from ai_web_research_agent.models import Base


@lru_cache
def create_session_factory(
    database_url: str,
) -> async_sessionmaker[AsyncSession]:
    engine_kwargs: dict[str, object] = {
        "echo": False,
    }

    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {
            "check_same_thread": False,
        }

    if database_url == "sqlite+aiosqlite:///:memory:":
        engine_kwargs["poolclass"] = StaticPool

    engine = create_async_engine(
        database_url,
        **engine_kwargs,
    )

    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def get_session_factory(
    settings: Settings,
) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(settings.database_url)


def _create_all(sync_session: Session) -> None:
    Base.metadata.create_all(bind=sync_session.get_bind())


async def init_db(settings: Settings) -> None:
    """Create tables if they do not exist."""
    session_factory = get_session_factory(settings)

    async with session_factory() as session:
        await session.run_sync(_create_all)
