import httpx
import pytest

from ai_web_research_agent.infrastructure.http import HTTPClient
from ai_web_research_agent.infrastructure.robots import (
    RobotsPolicy,
    RobotsRule,
)


def parse_robots(content: str) -> dict[str, list[RobotsRule]]:
    policy = RobotsPolicy(
        http_client=HTTPClient(),
        user_agent="AIWebResearchAgent/0.1",
    )

    return policy._parse(content)


def test_parse_simple_disallow():
    groups = parse_robots("User-agent: *\nDisallow: /private")

    assert len(groups["*"]) == 1
    assert groups["*"][0].path == "/private"
    assert groups["*"][0].allow is False


def test_parse_ignores_directives_before_user_agent():
    groups = parse_robots("Disallow: /\nUser-agent: *\nAllow: /")

    assert groups["*"][0].path == "/"


def test_parse_empty_disallow_ignored():
    groups = parse_robots("User-agent: *\nDisallow:")

    assert groups == {}


def test_parse_multiple_user_agents_form_one_group():
    groups = parse_robots("User-agent: bot-a\nUser-agent: bot-b\nDisallow: /x")

    assert len(groups["bot-a"]) == 1
    assert len(groups["bot-b"]) == 1


@pytest.mark.asyncio
async def test_specific_user_agent_takes_precedence(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/robots.txt",
        status_code=200,
        text="""
        User-agent: *
        Allow: /

        User-agent: AIWebResearchAgent
        Disallow: /private
        """,
    )

    async with HTTPClient() as client:
        policy = RobotsPolicy(
            http_client=client,
            user_agent="AIWebResearchAgent/0.1",
        )

        assert await policy.can_fetch("https://example.com/private/secret") is False
        assert await policy.can_fetch("https://example.com/public") is True


@pytest.mark.asyncio
async def test_most_specific_rule_wins(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/robots.txt",
        status_code=200,
        text="""
        User-agent: *
        Disallow: /private
        Allow: /private/public
        """,
    )

    async with HTTPClient() as client:
        policy = RobotsPolicy(
            http_client=client,
            user_agent="AIWebResearchAgent/0.1",
        )

        assert await policy.can_fetch("https://example.com/private/public") is True
        assert await policy.can_fetch("https://example.com/private/other") is False


@pytest.mark.asyncio
async def test_allow_wins_tie(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/robots.txt",
        status_code=200,
        text="User-agent: *\nDisallow: /x\nAllow: /x",
    )

    async with HTTPClient() as client:
        policy = RobotsPolicy(
            http_client=client,
            user_agent="AIWebResearchAgent/0.1",
        )

        assert await policy.can_fetch("https://example.com/x") is True


@pytest.mark.asyncio
async def test_unmatched_user_agent_allows(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/robots.txt",
        status_code=200,
        text="User-agent: SomeOtherBot\nDisallow: /",
    )

    async with HTTPClient() as client:
        policy = RobotsPolicy(
            http_client=client,
            user_agent="AIWebResearchAgent/0.1",
        )

        assert await policy.can_fetch("https://example.com/anything") is True


@pytest.mark.asyncio
async def test_missing_robots_file_allows(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/robots.txt",
        status_code=404,
    )

    async with HTTPClient() as client:
        policy = RobotsPolicy(
            http_client=client,
            user_agent="AIWebResearchAgent/0.1",
        )

        assert await policy.can_fetch("https://example.com/page") is True


@pytest.mark.asyncio
async def test_robots_fetch_failure_fails_open(httpx_mock):
    for _ in range(3):
        httpx_mock.add_exception(
            httpx.ConnectError("connection refused"),
            url="https://example.com/robots.txt",
        )

    async with HTTPClient() as client:
        policy = RobotsPolicy(
            http_client=client,
            user_agent="AIWebResearchAgent/0.1",
        )

        assert await policy.can_fetch("https://example.com/page") is True
