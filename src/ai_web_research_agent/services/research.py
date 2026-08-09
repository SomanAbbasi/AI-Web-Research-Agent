from ai_web_research_agent.config.settings import get_settings
from ai_web_research_agent.domain.crawling import PageContent
from ai_web_research_agent.domain.llm import LLMProvider
from ai_web_research_agent.domain.research import (
    ExtractedRecord,
    ResearchRequest,
)
from ai_web_research_agent.infrastructure.html_parser import HTMLParser
from ai_web_research_agent.infrastructure.http import (
    HTTPClient,
    HttpPageFetcher,
    RetryPolicy,
)
from ai_web_research_agent.infrastructure.llm import build_llm_provider
from ai_web_research_agent.services.extraction import (
    ExtractionError,
    ExtractionService,
)
from ai_web_research_agent.services.fetching import HybridPageFetcher
from ai_web_research_agent.services.url_normalizer import normalize_url


class ResearchError(Exception):
    """Raised when a page cannot be fetched or parsed for research."""


async def fetch_page(request: ResearchRequest) -> PageContent:
    """Fetch ``request.source_url`` and parse it into page content."""
    settings = get_settings()

    async with HTTPClient(
        timeout=settings.request_timeout,
        user_agent=settings.user_agent,
        retry_policy=RetryPolicy(
            max_attempts=settings.max_retries,
        ),
    ) as http_client:
        page_fetcher = HybridPageFetcher(
            http_fetcher=HttpPageFetcher(http_client),
            min_text_length=settings.min_visible_text,
        )

        url = normalize_url(request.source_url)

        fetched = await page_fetcher.fetch(url)

        if fetched.status_code >= 400:
            raise ResearchError(f"Page returned HTTP {fetched.status_code}")

        if "text/html" not in fetched.content_type.lower():
            raise ResearchError("Page is not an HTML document")

        return HTMLParser().parse(
            url=fetched.url,
            status_code=fetched.status_code,
            html=fetched.html,
        )


async def extract_page(
    request: ResearchRequest,
    content: PageContent,
    llm_provider: LLMProvider | None = None,
) -> ExtractedRecord:
    """Extract the requested fields from already-parsed page content."""
    settings = get_settings()

    extraction_service = ExtractionService(
        llm_provider=llm_provider or build_llm_provider(settings),
        max_context=settings.llm_max_context,
    )

    try:
        return await extraction_service.extract(
            request=request,
            page_text=content.text,
        )
    except ExtractionError as exc:
        raise ResearchError(str(exc)) from exc


async def extract_from_url(
    request: ResearchRequest,
    llm_provider: LLMProvider | None = None,
) -> ExtractedRecord:
    """Fetch ``request.source_url`` and extract the requested fields."""
    content = await fetch_page(request)

    return await extract_page(
        request,
        content,
        llm_provider=llm_provider,
    )
