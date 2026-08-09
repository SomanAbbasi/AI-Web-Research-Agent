from fastapi import APIRouter

from ai_web_research_agent.api.agent import router as agent_router
from ai_web_research_agent.api.crawl import router as crawl_router
from ai_web_research_agent.api.health import router as health_router
from ai_web_research_agent.api.research import router as research_router

router = APIRouter()

router.include_router(health_router)
router.include_router(crawl_router)
router.include_router(research_router)
router.include_router(agent_router)
