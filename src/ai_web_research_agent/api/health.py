
from fastapi import APIRouter

from ai_web_research_agent.config.settings import get_settings
from ai_web_research_agent.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/", summary="Application status")
async def root():
    settings = get_settings()

    return {
        "message": settings.app_name,
        "version": settings.app_version,
    }


@router.get(
    "/health",
    response_model=HealthResponse,
)
async def health():
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
    )


@router.get("/version")
async def version():
    settings = get_settings()

    return {"version": settings.app_version}