from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_web_research_agent.api.router import router
from ai_web_research_agent.config.settings import get_settings
from ai_web_research_agent.core.logging import configure_logging
from ai_web_research_agent.infrastructure.persistence.database import (
    init_db,
)


def create_app() -> FastAPI:
    settings = get_settings()

    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await init_db(settings)
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.include_router(router)

    return app


app = create_app()
