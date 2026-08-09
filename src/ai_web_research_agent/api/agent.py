from fastapi import APIRouter

from ai_web_research_agent.config.settings import get_settings
from ai_web_research_agent.domain.agent import AgentRequest
from ai_web_research_agent.domain.research import ExtractionField
from ai_web_research_agent.infrastructure.llm import build_llm_provider
from ai_web_research_agent.infrastructure.persistence.database import (
    get_session_factory,
)
from ai_web_research_agent.infrastructure.persistence.repository import (
    ResearchRepository,
)
from ai_web_research_agent.infrastructure.search import (
    DuckDuckGoDiscoverer,
)
from ai_web_research_agent.schemas.agent import (
    AgentRequestSchema,
    AgentResultSchema,
    FieldResolutionSchema,
)
from ai_web_research_agent.services.agent import AgentOrchestrator

router = APIRouter(
    prefix="/research",
    tags=["Research"],
)


@router.post(
    "/agent",
    response_model=AgentResultSchema,
)
async def run_agent(
    request: AgentRequestSchema,
) -> AgentResultSchema:
    settings = get_settings()

    llm_provider = build_llm_provider(settings)

    repository = ResearchRepository(
        session_factory=get_session_factory(settings),
    )

    discoverer = DuckDuckGoDiscoverer(
        timeout=settings.request_timeout,
        user_agent=settings.user_agent,
    )

    orchestrator = AgentOrchestrator(
        llm_provider=llm_provider,
        discoverer=discoverer,
        repository=repository,
    )

    result = await orchestrator.run(
        AgentRequest(
            goal=request.goal,
            fields=[
                ExtractionField(
                    name=field.name,
                    description=field.description,
                )
                for field in request.fields
            ],
            max_sources=request.max_sources,
            max_retries=request.max_retries,
            candidate_urls=[str(url) for url in request.candidate_urls],
        )
    )

    return AgentResultSchema(
        goal=result.goal,
        session_id=result.session_id,
        status=result.status,
        summary=result.summary,
        findings=[
            FieldResolutionSchema(
                field=finding.field,
                value=finding.value,
                confidence=finding.confidence,
                sources=finding.sources,
                conflicts=finding.conflicts,
            )
            for finding in result.findings
        ],
        missing_fields=result.missing_fields,
        sources_used=result.sources_used,
        steps=result.steps,
    )
