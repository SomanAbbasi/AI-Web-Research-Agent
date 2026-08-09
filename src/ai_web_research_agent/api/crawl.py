from fastapi import APIRouter

from ai_web_research_agent.domain.crawling import (
    CrawlRequest,
)
from ai_web_research_agent.schemas.crawling import (
    CrawlRequestSchema,
    CrawlResponseSchema,
    CrawlResultSchema,
    PageLinkSchema,
    PageSchema,
)
from ai_web_research_agent.services.crawl_service import (
    crawl_website,
)

router = APIRouter(
    prefix="/crawl",
    tags=["Crawling"],
)


@router.post(
    "",
    response_model=CrawlResponseSchema,
)
async def crawl(
    request: CrawlRequestSchema,
) -> CrawlResponseSchema:
    crawl_request = CrawlRequest(
        start_url=str(request.start_url),
        max_depth=request.max_depth,
        max_pages=request.max_pages,
        allowed_domain=request.allowed_domain,
    )

    results = await crawl_website(crawl_request)

    response_pages: list[CrawlResultSchema] = []

    for result in results:
        page_schema = None

        if result.page is not None:
            page_schema = PageSchema(
                url=result.page.url,
                status_code=result.page.status_code,
                title=result.page.title,
                text=result.page.text,
                links=[
                    PageLinkSchema(
                        url=link.url,
                        text=link.text,
                    )
                    for link in result.page.links
                ],
            )

        response_pages.append(
            CrawlResultSchema(
                url=result.url,
                status=result.status.value,
                page=page_schema,
                error=result.error,
            )
        )

    return CrawlResponseSchema(
        start_url=str(request.start_url),
        pages=response_pages,
        total=len(response_pages),
    )
