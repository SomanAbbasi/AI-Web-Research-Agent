from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from ai_web_research_agent.domain.research import (
    ExtractionField,
    ResearchRequest,
)
from ai_web_research_agent.schemas.research import (
    ExtractedRecordSchema,
    ExtractRequestSchema,
    RecordListResponseSchema,
    ResearchSessionCreateSchema,
    ResearchSessionSchema,
)
from ai_web_research_agent.services import (
    reporting,
    research_service,
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


@router.post(
    "/sessions",
    response_model=ResearchSessionSchema,
    status_code=201,
)
async def create_session(
    request: ResearchSessionCreateSchema,
) -> ResearchSessionSchema:
    session = await research_service.create_research_session(request.goal)

    return ResearchSessionSchema(
        id=session.id,
        goal=session.goal,
        status=session.status,
        error=session.error,
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


@router.get(
    "/sessions",
    response_model=list[ResearchSessionSchema],
)
async def list_sessions() -> list[ResearchSessionSchema]:
    sessions = await research_service.list_sessions()

    return [
        ResearchSessionSchema(
            id=session.id,
            goal=session.goal,
            status=session.status,
            error=session.error,
            created_at=session.created_at,
            completed_at=session.completed_at,
        )
        for session in sessions
    ]


@router.get(
    "/sessions/{session_id}",
    response_model=ResearchSessionSchema,
)
async def get_session(
    session_id: str,
) -> ResearchSessionSchema:
    session = await research_service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Research session not found",
        )

    return ResearchSessionSchema(
        id=session.id,
        goal=session.goal,
        status=session.status,
        error=session.error,
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


@router.get(
    "/sessions/{session_id}/records",
    response_model=RecordListResponseSchema,
)
async def list_records(
    session_id: str,
    min_confidence: float | None = Query(default=None),
    search: str | None = Query(default=None),
    include_missing: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> RecordListResponseSchema:
    records, total = await research_service.list_records(
        session_id,
        min_confidence=min_confidence,
        search=search,
        include_missing=include_missing,
        limit=limit,
        offset=offset,
    )

    return RecordListResponseSchema(
        total=total,
        offset=offset,
        limit=limit,
        records=[
            ExtractedRecordSchema(
                source_url=record.source_url,
                fields=record.fields,
                missing_fields=record.missing_fields,
                confidence=record.confidence,
            )
            for record in records
        ],
    )


@router.get(
    "/sessions/{session_id}/report",
    response_class=PlainTextResponse,
)
async def export_report(
    session_id: str,
    format: str = Query(default="json", pattern="^(json|csv|markdown)$"),
) -> PlainTextResponse:
    session = await research_service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Research session not found",
        )

    records, _total = await research_service.list_records(
        session_id,
        limit=10_000,
    )

    if format == "json":
        content = reporting.records_to_json(records)
        media_type = "application/json"
    elif format == "csv":
        content = reporting.records_to_csv(records)
        media_type = "text/csv"
    else:
        content = reporting.records_to_markdown(records)
        media_type = "text/markdown"

    return PlainTextResponse(
        content=content,
        media_type=media_type,
    )
