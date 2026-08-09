import pytest

from ai_web_research_agent.domain.research import (
    ExtractionField,
    ResearchRequest,
)
from ai_web_research_agent.infrastructure.llm import MockLLMProvider
from ai_web_research_agent.services.research import (
    ResearchError,
    extract_from_url,
)


def make_request() -> ResearchRequest:
    return ResearchRequest(
        goal="Find product details",
        source_url="https://example.com/product",
        fields=[
            ExtractionField(name="product_name", description="Product name"),
            ExtractionField(name="price", description="Price"),
        ],
    )


@pytest.mark.asyncio
async def test_extract_from_url_returns_record(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/product",
        status_code=200,
        headers={"content-type": "text/html"},
        text="<html><body><h1>Laptop</h1><p>Only $999</p></body></html>",
    )

    provider = MockLLMProvider(responses=['{"product_name": "Laptop", "price": "$999"}'])

    record = await extract_from_url(
        make_request(),
        llm_provider=provider,
    )

    assert record.fields == {
        "product_name": "Laptop",
        "price": "$999",
    }
    assert record.missing_fields == []
    assert record.confidence == 1.0


@pytest.mark.asyncio
async def test_extract_from_url_raises_on_http_error(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/product",
        status_code=404,
    )

    with pytest.raises(ResearchError):
        await extract_from_url(
            make_request(),
            llm_provider=MockLLMProvider(),
        )


@pytest.mark.asyncio
async def test_extract_from_url_raises_on_non_html(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/product",
        status_code=200,
        headers={"content-type": "image/png"},
        text="not html",
    )

    with pytest.raises(ResearchError):
        await extract_from_url(
            make_request(),
            llm_provider=MockLLMProvider(),
        )


@pytest.mark.asyncio
async def test_extract_from_url_raises_on_invalid_llm_output(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/product",
        status_code=200,
        headers={"content-type": "text/html"},
        text="<html><body><p>content</p></body></html>",
    )

    provider = MockLLMProvider(responses=["{invalid json"])

    with pytest.raises(ResearchError):
        await extract_from_url(
            make_request(),
            llm_provider=provider,
        )
