import httpx
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
        headers={"content-type": "text/html"},
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
        headers={"content-type": "text/html"},
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
        headers={"content-type": "text/html"},
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


def register_home_page(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://example.com/robots.txt",
        status_code=200,
        text="""
        User-agent: *
        Allow: /
        """,
    )


@pytest.mark.asyncio
async def test_crawler_marks_http_error_as_failed(httpx_mock):
    register_home_page(httpx_mock)

    for _ in range(3):
        httpx_mock.add_response(
            url="https://example.com/",
            status_code=500,
            text="Internal Server Error",
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

        results = await crawler.crawl(CrawlRequest(start_url="https://example.com"))

    assert len(results) == 1
    assert results[0].status == CrawlStatus.FAILED
    assert results[0].error == "HTTP 500"


@pytest.mark.asyncio
async def test_crawler_marks_network_error_as_failed(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/robots.txt",
        status_code=200,
        text="User-agent: *\nAllow: /",
    )

    for _ in range(3):
        httpx_mock.add_exception(
            httpx.ConnectError("connection refused"),
            url="https://example.com/",
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

        results = await crawler.crawl(CrawlRequest(start_url="https://example.com"))

    assert len(results) == 1
    assert results[0].status == CrawlStatus.FAILED
    assert results[0].error == "connection refused"


@pytest.mark.asyncio
async def test_crawler_skips_robots_disallowed(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/robots.txt",
        status_code=200,
        text="User-agent: *\nDisallow: /",
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

        results = await crawler.crawl(CrawlRequest(start_url="https://example.com"))

    assert len(results) == 1
    assert results[0].status == CrawlStatus.SKIPPED
    assert results[0].error == "Blocked by robots.txt"


@pytest.mark.asyncio
async def test_crawler_skips_outside_allowed_domain(httpx_mock):
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
                allowed_domain="other.org",
            )
        )

    assert len(results) == 1
    assert results[0].status == CrawlStatus.SKIPPED
    assert results[0].error == "Outside allowed domain"


@pytest.mark.asyncio
async def test_crawler_skips_non_html_content(httpx_mock):
    register_home_page(httpx_mock)

    httpx_mock.add_response(
        url="https://example.com/image.png",
        status_code=200,
        headers={"content-type": "image/png"},
        text="not html",
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
                start_url="https://example.com/image.png",
                max_pages=1,
            )
        )

    assert len(results) == 1
    assert results[0].status == CrawlStatus.SKIPPED
    assert results[0].error == "Not an HTML document"


@pytest.mark.asyncio
async def test_crawler_respects_depth_limit(httpx_mock):
    register_home_page(httpx_mock)

    httpx_mock.add_response(
        url="https://example.com/",
        status_code=200,
        headers={"content-type": "text/html"},
        text='<a href="/about">About</a>',
    )
    httpx_mock.add_response(
        url="https://example.com/about",
        status_code=200,
        headers={"content-type": "text/html"},
        text='<a href="/contact">Contact</a>',
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
                max_pages=10,
            )
        )

    assert [r.url for r in results] == [
        "https://example.com/",
        "https://example.com/about",
    ]


@pytest.mark.asyncio
async def test_crawler_deduplicates_links(httpx_mock):
    register_home_page(httpx_mock)

    httpx_mock.add_response(
        url="https://example.com/",
        status_code=200,
        headers={"content-type": "text/html"},
        text='<a href="/about">About</a><a href="/about">About again</a>',
    )
    httpx_mock.add_response(
        url="https://example.com/about",
        status_code=200,
        headers={"content-type": "text/html"},
        text="About page",
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
                max_pages=10,
            )
        )

    assert len(results) == 2


@pytest.mark.asyncio
async def test_crawler_does_not_follow_external_links(httpx_mock):
    register_home_page(httpx_mock)

    httpx_mock.add_response(
        url="https://example.com/",
        status_code=200,
        headers={"content-type": "text/html"},
        text=('<a href="/about">About</a><a href="https://other.org/page">External</a>'),
    )
    httpx_mock.add_response(
        url="https://example.com/about",
        status_code=200,
        headers={"content-type": "text/html"},
        text="About page",
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
                max_pages=10,
            )
        )

    assert [r.url for r in results] == [
        "https://example.com/",
        "https://example.com/about",
    ]
