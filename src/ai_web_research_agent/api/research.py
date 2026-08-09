from fastapi import APIRouter, HTTPException

from ai_web_research_agent.domain.research import (
    ExtractionField,
    ResearchRequest,
)
from ai_web_research_agent.schemas.research import (
    ExtractedRecordSchema,
    ExtractRequestSchema,
)
from ai_web_research_agent.services.research import (
    ResearchError,
    extract_from_url,
)

router = APIRouter(
    prefix="/research",
    tags=["Research"],
)


@router.post(
    "/extract",
    response_model=ExtractedRecordSchema,
)
async def extract(
    request: ExtractRequestSchema,
) -> ExtractedRecordSchema:
    research_request = ResearchRequest(
        goal=request.goal,
        source_url=str(request.source_url),
        fields=[
            ExtractionField(
                name=field.name,
                description=field.description,
            )
            for field in request.fields
        ],
    )

    try:
        record = await extract_from_url(research_request)
    except ResearchError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return ExtractedRecordSchema(
        source_url=record.source_url,
        fields=record.fields,
        missing_fields=record.missing_fields,
        confidence=record.confidence,
    )
