from pydantic import BaseModel, Field, HttpUrl

from ai_web_research_agent.schemas.research import (
    ExtractionFieldSchema,
)


class AgentRequestSchema(BaseModel):
    goal: str = Field(
        min_length=1,
        max_length=1000,
    )
    fields: list[ExtractionFieldSchema] = Field(
        min_length=1,
        max_length=20,
    )
    max_sources: int = Field(
        default=5,
        ge=1,
        le=20,
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
    )
    candidate_urls: list[HttpUrl] = Field(
        default_factory=list,
        max_length=20,
    )


class FieldResolutionSchema(BaseModel):
    field: str
    value: str
    confidence: float | None = None
    sources: list[str]
    conflicts: int


class AgentResultSchema(BaseModel):
    goal: str
    session_id: str | None = None
    status: str
    summary: str
    findings: list[FieldResolutionSchema]
    missing_fields: list[str]
    sources_used: list[str]
    steps: list[str]
