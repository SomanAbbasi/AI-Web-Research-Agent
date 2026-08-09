import pytest

from ai_web_research_agent.domain.crawling import (
    CrawlRequest,
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
from ai_web_research_agent.services.crawler import Crawler


@pytest.mark.asyncio
async def test_crawler_discovers_pages(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/robots.txt",
        status_code=200,
        text="""
        User-agent: *
        Allow: /
        """,
    )

    httpx_mock.add_response(
        url="https://example.com/",
        status_code=200,
        headers={
            "content-type": "text/html"
        },
        text="""
        <html>
            <head>
                <title>Home</title>
            </head>
            <body>
                <h1>Home</h1>
                <a href="/about">About</a>
            </body>
        </html>
        """,
    )

    httpx_mock.add_response(
        url="https://example.com/about",
        status_code=200,
        headers={
            "content-type": "text/html"
        },
        text="""
        <html>
            <head>
                <title>About</title>
            </head>
            <body>
                <p>About page</p>
            </body>
        </html>
        """,
    )

    async with HTTPClient() as client:
        robots = RobotsPolicy(
            http_client=client,
            user_agent="AIWebResearchAgent/0.1",
        )

        crawler = Crawler(
            http_client=client,
            robots_policy=robots,
            html_parser=HTMLParser(),
        )

        results = await crawler.crawl(
            CrawlRequest(
                start_url="https://example.com",
                max_depth=1,
                max_pages=2,
            )
        )

    assert len(results) == 2

    assert results[0].status == CrawlStatus.SUCCESS
    assert results[0].page is not None
    assert results[0].page.title == "Home"

    assert results[1].status == CrawlStatus.SUCCESS
    assert results[1].page is not None
    assert results[1].page.title == "About"


@pytest.mark.asyncio
async def test_crawler_respects_max_pages(
    httpx_mock,
):
    httpx_mock.add_response(
        url="https://example.com/robots.txt",
        status_code=200,
        text="""
        User-agent: *
        Allow: /
        """,
    )

    httpx_mock.add_response(
        url="https://example.com/",
        status_code=200,
        headers={
            "content-type": "text/html"
        },
        text="""
        <a href="/one">One</a>
        <a href="/two">Two</a>
        """,
    )

    async with HTTPClient() as client:
        robots = RobotsPolicy(
            http_client=client,
            user_agent="AIWebResearchAgent/0.1",
        )

        crawler = Crawler(
            http_client=client,
            robots_policy=robots,
            html_parser=HTMLParser(),
        )

        results = await crawler.crawl(
            CrawlRequest(
                start_url="https://example.com",
                max_depth=5,
                max_pages=1,
            )
        )

    assert len(results) == 1