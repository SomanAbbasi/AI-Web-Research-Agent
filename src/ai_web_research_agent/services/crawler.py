
from urllib.parse import urlparse

from ai_web_research_agent.domain.crawling import (
    CrawlRequest,
    CrawlResult,
    CrawlStatus,
)
from ai_web_research_agent.infrastructure.html_parser import HTMLParser
from ai_web_research_agent.infrastructure.http import HTTPClient
from ai_web_research_agent.infrastructure.robots import RobotsPolicy
from ai_web_research_agent.services.frontier import URLFrontier
from ai_web_research_agent.services.url_normalizer import normalize_url


class Crawler:
    def __init__(
        self,
        http_client: HTTPClient,
        robots_policy: RobotsPolicy,
        html_parser: HTMLParser,
    ) -> None:
        self._http_client = http_client
        self._robots_policy = robots_policy
        self._html_parser = html_parser

    async def crawl(
        self,
        request: CrawlRequest,
    ) -> list[CrawlResult]:
        frontier = URLFrontier()

        start_url = normalize_url(request.start_url)

        allowed_domain = (
            request.allowed_domain
            or urlparse(start_url).netloc
        )

        frontier.add(start_url, 0)

        results: list[CrawlResult] = []

        while len(frontier) > 0 and len(results) < request.max_pages:
            item = frontier.pop()

            if item is None:
                break

            url, depth = item

            if depth > request.max_depth:
                continue

            parsed = urlparse(url)

            if parsed.netloc != allowed_domain:
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
                response = await self._http_client.get(url)

                content_type = response.headers.get(
                    "content-type",
                    "",
                )

                if response.status_code >= 400:
                    results.append(
                        CrawlResult(
                            url=url,
                            status=CrawlStatus.FAILED,
                            error=f"HTTP {response.status_code}",
                        )
                    )

                    continue

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
                    url=url,
                    status_code=response.status_code,
                    html=response.text,
                )

                results.append(
                    CrawlResult(
                        url=url,
                        status=CrawlStatus.SUCCESS,
                        page=page,
                    )
                )

                if depth < request.max_depth:
                    for link in page.links:
                        try:
                            normalized = normalize_url(link.url)
                        except ValueError:
                            continue

                        if (
                            urlparse(normalized).netloc
                            == allowed_domain
                        ):
                            frontier.add(
                                normalized,
                                depth + 1,
                            )

            except Exception as exc:
                results.append(
                    CrawlResult(
                        url=url,
                        status=CrawlStatus.FAILED,
                        error=str(exc),
                    )
                )

        return results