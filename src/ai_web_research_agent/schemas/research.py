from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class ExtractionFieldSchema(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )
    description: str = Field(
        default="",
        max_length=500,
    )


class ExtractRequestSchema(BaseModel):
    goal: str = Field(
        min_length=1,
        max_length=1000,
    )
    source_url: HttpUrl
    fields: list[ExtractionFieldSchema] = Field(
        min_length=1,
        max_length=20,
    )


class ExtractedRecordSchema(BaseModel):
    source_url: str
    fields: dict[str, str]
    missing_fields: list[str]
    confidence: float | None = None


class ResearchSessionCreateSchema(BaseModel):
    goal: str = Field(
        min_length=1,
        max_length=2000,
    )


class ResearchSessionSchema(BaseModel):
    id: str
    goal: str
    status: str
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class RecordListQuerySchema(BaseModel):
    min_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    search: str | None = Field(
        default=None,
        max_length=200,
    )
    include_missing: bool | None = None
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
    )
    offset: int = Field(
        default=0,
        ge=0,
    )


class RecordListResponseSchema(BaseModel):
    total: int
    offset: int
    limit: int
    records: list[ExtractedRecordSchema]


class ReportRequestSchema(BaseModel):
    session_id: str = Field(min_length=1)
    format: str = Field(default="json", pattern="^(json|csv|markdown)$")
