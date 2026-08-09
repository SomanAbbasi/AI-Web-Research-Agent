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
