from fastapi import FastAPI

from ai_web_research_agent.api.router import router
from ai_web_research_agent.config.settings import get_settings
from ai_web_research_agent.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()

    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )

    app.include_router(router)

    return app


app = create_app()
