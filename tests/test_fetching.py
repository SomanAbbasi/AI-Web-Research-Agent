import pytest

from ai_web_research_agent.domain.fetching import FetchedPage
from ai_web_research_agent.services.fetching import (
    HybridPageFetcher,
    is_page_complete,
    visible_text_length,
)


class FakeFetcher:
    def __init__(
        self,
        page: FetchedPage | None = None,
        error: Exception | None = None,
    ) -> None:
        self._page = page
        self._error = error
        self.calls: list[str] = []

    async def fetch(self, url: str) -> FetchedPage:
        self.calls.append(url)

        if self._error is not None:
            raise self._error

        if self._page is None:
            raise AssertionError("FakeFetcher has no page configured")

        return self._page


def test_visible_text_length_counts_text_not_markup():
    html = "<html><body><p>Hello world</p><script>var x = 1;</script></body></html>"

    assert visible_text_length(html) == 11


def test_visible_text_length_empty():
    assert visible_text_length("<html><body></body></html>") == 0


def test_is_page_complete_rich_page():
    html = f"<html><body>{'<p>word</p>' * 100}</body></html>"

    assert is_page_complete(html, min_text_length=200) is True


def test_is_page_complete_spa_shell():
    html = '<div id="root"></div>'

    assert is_page_complete(html, min_text_length=200) is False


@pytest.mark.asyncio
async def test_hybrid_uses_http_when_content_is_complete():
    http_page = FetchedPage(
        url="https://example.com/",
        status_code=200,
        html="<html><body>" + "<p>word</p>" * 100 + "</body></html>",
    )

    http = FakeFetcher(page=http_page)
    browser = FakeFetcher(page=http_page)

    hybrid = HybridPageFetcher(
        http_fetcher=http,
        browser_fetcher=browser,
    )

    result = await hybrid.fetch("https://example.com/")

    assert result is http_page
    assert http.calls == ["https://example.com/"]
    assert browser.calls == []


@pytest.mark.asyncio
async def test_hybrid_renders_when_content_is_incomplete():
    thin = FetchedPage(
        url="https://example.com/",
        status_code=200,
        html='<div id="root"></div>',
    )
    rendered = FetchedPage(
        url="https://example.com/",
        status_code=200,
        html="<html><body>" + "<p>loaded</p>" * 100 + "</body></html>",
        via_browser=True,
    )

    http = FakeFetcher(page=thin)
    browser = FakeFetcher(page=rendered)

    hybrid = HybridPageFetcher(
        http_fetcher=http,
        browser_fetcher=browser,
    )

    result = await hybrid.fetch("https://example.com/")

    assert result is rendered
    assert result.via_browser is True
    assert browser.calls == ["https://example.com/"]


@pytest.mark.asyncio
async def test_hybrid_falls_back_to_http_when_browser_fails():
    thin = FetchedPage(
        url="https://example.com/",
        status_code=200,
        html='<div id="root"></div>',
    )

    http = FakeFetcher(page=thin)
    browser = FakeFetcher(error=RuntimeError("browser crashed"))

    hybrid = HybridPageFetcher(
        http_fetcher=http,
        browser_fetcher=browser,
    )

    result = await hybrid.fetch("https://example.com/")

    assert result is thin


@pytest.mark.asyncio
async def test_hybrid_without_browser_returns_http():
    thin = FetchedPage(
        url="https://example.com/",
        status_code=200,
        html='<div id="root"></div>',
    )

    http = FakeFetcher(page=thin)

    hybrid = HybridPageFetcher(http_fetcher=http)

    result = await hybrid.fetch("https://example.com/")

    assert result is thin
