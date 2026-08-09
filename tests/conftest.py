import os

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)

import pytest

from ai_web_research_agent.config.settings import Settings
from ai_web_research_agent.infrastructure.persistence.database import (
    get_session_factory,
    init_db,
)
from ai_web_research_agent.infrastructure.persistence.repository import (
    ResearchRepository,
)


@pytest.fixture
def database_url(tmp_path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
async def repository(database_url: str) -> ResearchRepository:
    settings = Settings(database_url=database_url)

    await init_db(settings)

    return ResearchRepository(
        session_factory=get_session_factory(settings),
    )
