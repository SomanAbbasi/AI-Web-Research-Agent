import logging
import re

from ai_web_research_agent.domain.fetching import (
    FetchedPage,
    PageFetcher,
)

logger = logging.getLogger(__name__)

_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript|template)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_TAGS_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def visible_text_length(html: str) -> int:
    """Estimate the amount of human-readable text in an HTML document."""
    without_embedded = _SCRIPT_STYLE_RE.sub(" ", html)
    without_tags = _TAGS_RE.sub(" ", without_embedded)
    text = _WHITESPACE_RE.sub(" ", without_tags).strip()

    return len(text)


def is_page_complete(
    html: str,
    min_text_length: int = 200,
) -> bool:
    """Heuristic for whether a page rendered useful content over HTTP.

    A page with very little visible text was likely rendered by
    JavaScript and is a candidate for browser rendering.
    """
    return visible_text_length(html) >= min_text_length


class HybridPageFetcher:
    """Fetches over HTTP first and falls back to a browser when needed.

    Plain HTTP stays the default because it is faster and cheaper. When the
    HTTP response looks incomplete and a browser fetcher is available, the
    page is re-rendered. If the browser fails, the HTTP content is returned
    rather than failing the whole crawl.
    """

    def __init__(
        self,
        http_fetcher: PageFetcher,
        browser_fetcher: PageFetcher | None = None,
        min_text_length: int = 200,
    ) -> None:
        self._http_fetcher = http_fetcher
        self._browser_fetcher = browser_fetcher
        self._min_text_length = min_text_length

    async def fetch(self, url: str) -> FetchedPage:
        page = await self._http_fetcher.fetch(url)

        if not self._should_render(page):
            return page

        if self._browser_fetcher is None:
            return page

        logger.info("HTTP content looks incomplete, rendering %s in browser", url)

        try:
            return await self._browser_fetcher.fetch(url)
        except Exception:
            logger.exception("Browser rendering failed for %s", url)

            return page

    def _should_render(self, page: FetchedPage) -> bool:
        return not is_page_complete(
            page.html,
            min_text_length=self._min_text_length,
        )
