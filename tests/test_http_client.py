import httpx
import pytest

from ai_web_research_agent.infrastructure.http import (
    HTTPClient,
    RetryPolicy,
)


@pytest.mark.asyncio
async def test_http_client_get(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com",
        status_code=200,
        text="<html>Hello</html>",
    )

    async with HTTPClient() as client:
        response = await client.get("https://example.com")

    assert response.status_code == 200
    assert response.text == "<html>Hello</html>"


@pytest.mark.asyncio
async def test_http_client_sends_user_agent(
    httpx_mock,
):
    httpx_mock.add_response(
        url="https://example.com",
        status_code=200,
        text="OK",
    )

    async with HTTPClient(user_agent="TestCrawler/1.0") as client:
        await client.get("https://example.com")

    request = httpx_mock.get_request()

    assert request is not None
    assert request.headers["user-agent"] == "TestCrawler/1.0"


@pytest.mark.asyncio
async def test_http_client_requires_context_manager():
    client = HTTPClient()

    with pytest.raises(RuntimeError):
        await client.get("https://example.com")


@pytest.mark.asyncio
async def test_http_client_retries_on_5xx_then_succeeds(httpx_mock):
    sleeps: list[float] = []

    async def sleeper(seconds: float) -> None:
        sleeps.append(seconds)

    httpx_mock.add_response(
        url="https://example.com",
        status_code=500,
        text="Internal Server Error",
    )
    httpx_mock.add_response(
        url="https://example.com",
        status_code=200,
        text="OK",
    )

    async with HTTPClient(
        retry_policy=RetryPolicy(
            max_attempts=2,
            backoff=0.5,
        ),
        sleeper=sleeper,
    ) as client:
        response = await client.get("https://example.com")

    assert response.status_code == 200
    assert sleeps == [0.5]


@pytest.mark.asyncio
async def test_http_client_returns_5xx_after_retries_exhausted(httpx_mock):
    sleeps: list[float] = []

    async def sleeper(seconds: float) -> None:
        sleeps.append(seconds)

    httpx_mock.add_response(
        url="https://example.com",
        status_code=503,
        text="Unavailable",
    )
    httpx_mock.add_response(
        url="https://example.com",
        status_code=503,
        text="Unavailable",
    )

    async with HTTPClient(
        retry_policy=RetryPolicy(
            max_attempts=2,
            backoff=0.5,
        ),
        sleeper=sleeper,
    ) as client:
        response = await client.get("https://example.com")

    assert response.status_code == 503
    assert len(sleeps) == 1


@pytest.mark.asyncio
async def test_http_client_retries_transport_error_then_succeeds(httpx_mock):
    sleeps: list[float] = []

    async def sleeper(seconds: float) -> None:
        sleeps.append(seconds)

    httpx_mock.add_exception(
        httpx.ConnectError("connection refused"),
        url="https://example.com",
    )
    httpx_mock.add_response(
        url="https://example.com",
        status_code=200,
        text="OK",
    )

    async with HTTPClient(
        retry_policy=RetryPolicy(
            max_attempts=2,
            backoff=0.5,
        ),
        sleeper=sleeper,
    ) as client:
        response = await client.get("https://example.com")

    assert response.status_code == 200
    assert sleeps == [0.5]


@pytest.mark.asyncio
async def test_http_client_re_raises_after_transport_error_retries(httpx_mock):
    sleeps: list[float] = []

    async def sleeper(seconds: float) -> None:
        sleeps.append(seconds)

    httpx_mock.add_exception(
        httpx.ConnectError("connection refused"),
        url="https://example.com",
    )
    httpx_mock.add_exception(
        httpx.ConnectError("connection refused"),
        url="https://example.com",
    )

    async with HTTPClient(
        retry_policy=RetryPolicy(
            max_attempts=2,
            backoff=0.5,
        ),
        sleeper=sleeper,
    ) as client:
        with pytest.raises(httpx.ConnectError):
            await client.get("https://example.com")

    assert len(sleeps) == 1


def test_retry_policy_requires_at_least_one_attempt():
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)


def test_retry_policy_exponential_backoff():
    policy = RetryPolicy(
        max_attempts=3,
        backoff=0.5,
    )

    assert policy.delay_for(1) == 0.5
    assert policy.delay_for(2) == 1.0
    assert policy.delay_for(3) == 2.0
