from ai_web_research_agent.config.settings import get_settings
from ai_web_research_agent.domain.crawling import (
    CrawlRequest,
    CrawlResult,
)
from ai_web_research_agent.infrastructure.browser import (
    BrowserPageFetcher,
)
from ai_web_research_agent.infrastructure.html_parser import (
    HTMLParser,
)
from ai_web_research_agent.infrastructure.http import (
    HTTPClient,
    HttpPageFetcher,
    RetryPolicy,
)
from ai_web_research_agent.infrastructure.robots import (
    RobotsPolicy,
)
from ai_web_research_agent.services.crawler import (
    Crawler,
)
from ai_web_research_agent.services.fetching import (
    HybridPageFetcher,
)
from ai_web_research_agent.services.rate_limiter import (
    RateLimiter,
)
from ai_web_research_agent.services.url_normalizer import (
    normalize_url,
)


async def crawl_website(
    request: CrawlRequest,
) -> list[CrawlResult]:
    settings = get_settings()

    async with HTTPClient(
        timeout=settings.request_timeout,
        user_agent=settings.user_agent,
        retry_policy=RetryPolicy(
            max_attempts=settings.max_retries,
        ),
    ) as http_client:
        robots_policy = RobotsPolicy(
            http_client=http_client,
            user_agent=settings.user_agent,
        )

        http_fetcher = HttpPageFetcher(http_client)

        browser_fetcher = None

        if settings.use_browser:
            browser_fetcher = BrowserPageFetcher(
                timeout=settings.browser_timeout,
                render_delay=settings.browser_render_delay,
                user_agent=settings.user_agent,
            )

        page_fetcher = HybridPageFetcher(
            http_fetcher=http_fetcher,
            browser_fetcher=browser_fetcher,
            min_text_length=settings.min_visible_text,
        )

        parser = HTMLParser()

        crawler = Crawler(
            page_fetcher=page_fetcher,
            robots_policy=robots_policy,
            html_parser=parser,
            rate_limiter=RateLimiter(
                delay=settings.crawl_delay,
            ),
        )

        normalized_request = CrawlRequest(
            start_url=normalize_url(request.start_url),
            max_depth=request.max_depth,
            max_pages=request.max_pages,
            allowed_domain=request.allowed_domain,
        )

        return await crawler.crawl(normalized_request)
