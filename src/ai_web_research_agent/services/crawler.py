from urllib.parse import urlparse

import httpx

from ai_web_research_agent.domain.crawling import (
    CrawlRequest,
    CrawlResult,
    CrawlStatus,
)
from ai_web_research_agent.domain.fetching import (
    PageFetcher,
)
from ai_web_research_agent.infrastructure.html_parser import (
    HTMLParser,
)
from ai_web_research_agent.infrastructure.robots import (
    RobotsPolicy,
)
from ai_web_research_agent.services.frontier import (
    URLFrontier,
)
from ai_web_research_agent.services.rate_limiter import (
    RateLimiter,
)
from ai_web_research_agent.services.url_normalizer import (
    normalize_url,
)


class Crawler:
    """Coordinates the complete crawling process."""

    def __init__(
        self,
        page_fetcher: PageFetcher,
        robots_policy: RobotsPolicy,
        html_parser: HTMLParser,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._page_fetcher = page_fetcher
        self._robots_policy = robots_policy
        self._html_parser = html_parser
        self._rate_limiter = rate_limiter or RateLimiter()

    async def crawl(
        self,
        request: CrawlRequest,
    ) -> list[CrawlResult]:
        frontier = URLFrontier()

        start_url = normalize_url(request.start_url)

        allowed_domain = request.allowed_domain or urlparse(start_url).netloc

        frontier.add(
            start_url,
            0,
        )

        results: list[CrawlResult] = []

        while len(frontier) > 0 and len(results) < request.max_pages:
            item = frontier.pop()

            if item is None:
                break

            url, depth = item

            if depth > request.max_depth:
                continue

            if not self._is_allowed_domain(
                url,
                allowed_domain,
            ):
                results.append(
                    CrawlResult(
                        url=url,
                        status=CrawlStatus.SKIPPED,
                        error="Outside allowed domain",
                    )
                )

                continue

            allowed = await self._robots_policy.can_fetch(url)

            if not allowed:
                results.append(
                    CrawlResult(
                        url=url,
                        status=CrawlStatus.SKIPPED,
                        error="Blocked by robots.txt",
                    )
                )

                continue

            try:
                host = urlparse(url).netloc

                await self._rate_limiter.wait(host)

                fetched = await self._page_fetcher.fetch(url)

                if fetched.status_code >= 400:
                    results.append(
                        CrawlResult(
                            url=url,
                            status=CrawlStatus.FAILED,
                            error=f"HTTP {fetched.status_code}",
                        )
                    )

                    continue

                content_type = fetched.content_type.lower()

                if "text/html" not in content_type:
                    results.append(
                        CrawlResult(
                            url=url,
                            status=CrawlStatus.SKIPPED,
                            error="Not an HTML document",
                        )
                    )

                    continue

                page = self._html_parser.parse(
                    url=fetched.url,
                    status_code=fetched.status_code,
                    html=fetched.html,
                )

                page.via_browser = fetched.via_browser

                results.append(
                    CrawlResult(
                        url=fetched.url,
                        status=CrawlStatus.SUCCESS,
                        page=page,
                    )
                )

                if depth >= request.max_depth:
                    continue

                for link in page.links:
                    try:
                        normalized = normalize_url(link.url)
                    except ValueError:
                        continue

                    if self._is_allowed_domain(
                        normalized,
                        allowed_domain,
                    ):
                        frontier.add(
                            normalized,
                            depth + 1,
                        )

            except httpx.HTTPError as exc:
                results.append(
                    CrawlResult(
                        url=url,
                        status=CrawlStatus.FAILED,
                        error=str(exc),
                    )
                )

        return results

    @staticmethod
    def _is_allowed_domain(
        url: str,
        allowed_domain: str,
    ) -> bool:
        hostname = urlparse(url).netloc

        return hostname == allowed_domain
