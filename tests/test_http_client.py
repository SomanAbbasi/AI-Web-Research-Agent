import pytest

from ai_web_research_agent.infrastructure.http import HTTPClient


@pytest.mark.asyncio
async def test_http_client_get(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com",
        status_code=200,
        text="<html>Hello</html>",
    )

    async with HTTPClient() as client:
        response = await client.get(
            "https://example.com"
        )

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

    async with HTTPClient(
        user_agent="TestCrawler/1.0"
    ) as client:
        await client.get(
            "https://example.com"
        )

    request = httpx_mock.get_request()

    assert request is not None
    assert (
        request.headers["user-agent"]
        == "TestCrawler/1.0"
    )


@pytest.mark.asyncio
async def test_http_client_requires_context_manager():
    client = HTTPClient()

    with pytest.raises(RuntimeError):
        await client.get(
            "https://example.com"
        )