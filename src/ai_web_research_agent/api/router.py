from fastapi import APIRouter

from ai_web_research_agent.api.crawl import router as crawl_router
from ai_web_research_agent.api.health import router as health_router


router = APIRouter()

router.include_router(health_router)
router.include_router(crawl_router)