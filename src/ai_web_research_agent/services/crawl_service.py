from ai_web_research_agent.config.settings import get_settings
from ai_web_research_agent.domain.crawling import (
    CrawlRequest,
    CrawlResult,
)
from ai_web_research_agent.infrastructure.html_parser import (
    HTMLParser,
)
from ai_web_research_agent.infrastructure.http import (
    HTTPClient,
)
from ai_web_research_agent.infrastructure.robots import (
    RobotsPolicy,
)
from ai_web_research_agent.services.crawler import (
    Crawler,
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
    ) as http_client:
        robots_policy = RobotsPolicy(
            http_client=http_client,
            user_agent=settings.user_agent,
        )

        parser = HTMLParser()

        crawler = Crawler(
            http_client=http_client,
            robots_policy=robots_policy,
            html_parser=parser,
        )

        normalized_request = CrawlRequest(
            start_url=normalize_url(request.start_url),
            max_depth=request.max_depth,
            max_pages=request.max_pages,
            allowed_domain=request.allowed_domain,
        )

        return await crawler.crawl(normalized_request)
