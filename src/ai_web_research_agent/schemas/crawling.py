from pydantic import BaseModel, Field, HttpUrl


class CrawlRequestSchema(BaseModel):
    start_url: HttpUrl
    max_depth: int = Field(
        default=2,
        ge=0,
        le=10,
    )
    max_pages: int = Field(
        default=20,
        ge=1,
        le=100,
    )
    allowed_domain: str | None = None


class PageLinkSchema(BaseModel):
    url: str
    text: str


class PageSchema(BaseModel):
    url: str
    status_code: int
    title: str | None
    text: str
    links: list[PageLinkSchema]


class CrawlResultSchema(BaseModel):
    url: str
    status: str
    page: PageSchema | None = None
    error: str | None = None


class CrawlResponseSchema(BaseModel):
    start_url: str
    pages: list[CrawlResultSchema]
    total: int
