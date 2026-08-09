from urllib.parse import parse_qs, quote_plus, urlparse

from bs4 import BeautifulSoup

from ai_web_research_agent.infrastructure.http import HTTPClient


def parse_search_results(html: str, limit: int) -> list[str]:
    """Extract absolute http(s) result URLs from search engine HTML.

    DuckDuckGo wraps result links in a redirect endpoint with the real URL
    in the ``uddg`` query parameter; plain absolute links are accepted as-is.
    """
    soup = BeautifulSoup(html, "html.parser")

    urls: list[str] = []

    for anchor in soup.select("a[href]"):
        href = anchor.get("href")

        if not isinstance(href, str) or not href:
            continue

        url = _unwrap_redirect(href)

        if not _is_http_url(url):
            continue

        if url not in urls:
            urls.append(url)

        if len(urls) >= limit:
            break

    return urls


class DuckDuckGoDiscoverer:
    """Discovers source URLs using DuckDuckGo's HTML search results."""

    def __init__(
        self,
        timeout: float = 10.0,
        user_agent: str = "AIWebResearchAgent/0.1",
    ) -> None:
        self._timeout = timeout
        self._user_agent = user_agent

    async def discover(self, query: str, limit: int) -> list[str]:
        search_url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)

        async with HTTPClient(
            timeout=self._timeout,
            user_agent=self._user_agent,
        ) as client:
            response = await client.get(search_url)

        if response.status_code >= 400:
            return []

        return parse_search_results(response.text, limit)


def _unwrap_redirect(href: str) -> str:
    """Resolve a search engine redirect wrapper into its target URL."""
    if "/l/?uddg=" not in href:
        return href

    parsed = urlparse(href)
    params = parse_qs(parsed.query)

    targets = params.get("uddg", [])

    if not targets:
        return href

    return targets[0]


def _is_http_url(url: str) -> bool:
    return url.startswith(("http://", "https://"))
