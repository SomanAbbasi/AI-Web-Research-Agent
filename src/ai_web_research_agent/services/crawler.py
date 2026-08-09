from urllib.parse import urlparse

import httpx

from ai_web_research_agent.domain.crawling import (
    CrawlRequest,
    CrawlResult,
    CrawlStatus,
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
        http_client: HTTPClient,
        robots_policy: RobotsPolicy,
        html_parser: HTMLParser,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._http_client = http_client
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

                response = await self._http_client.get(url)

                if response.status_code >= 400:
                    results.append(
                        CrawlResult(
                            url=url,
                            status=CrawlStatus.FAILED,
                            error=f"HTTP {response.status_code}",
                        )
                    )

                    continue

                content_type = response.headers.get(
                    "content-type",
                    "",
                ).lower()

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
                    url=str(response.url),
                    status_code=response.status_code,
                    html=response.text,
                )

                results.append(
                    CrawlResult(
                        url=str(response.url),
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
