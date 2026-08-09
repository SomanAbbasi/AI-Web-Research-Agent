import json

import pytest

from ai_web_research_agent.domain.research import (
    ExtractionField,
    ResearchRequest,
)
from ai_web_research_agent.infrastructure.llm import MockLLMProvider
from ai_web_research_agent.services.extraction import (
    ExtractionError,
    ExtractionService,
)

FIELDS = [
    ExtractionField(name="product_name", description="Product name"),
    ExtractionField(name="price", description="Price in USD"),
    ExtractionField(name="rating", description="Average rating"),
]


def make_request() -> ResearchRequest:
    return ResearchRequest(
        goal="Find product details",
        source_url="https://example.com/product",
        fields=FIELDS,
    )


def make_service(responses: list[str]) -> ExtractionService:
    return ExtractionService(
        llm_provider=MockLLMProvider(responses=responses),
    )


@pytest.mark.asyncio
async def test_extract_valid_response():
    service = make_service(['{"product_name": "Laptop", "price": "$999", "rating": "4.5"}'])

    record = await service.extract(
        make_request(),
        "page text",
    )

    assert record.fields == {
        "product_name": "Laptop",
        "price": "$999",
        "rating": "4.5",
    }
    assert record.missing_fields == []
    assert record.confidence == 1.0
    assert record.source_url == "https://example.com/product"


@pytest.mark.asyncio
async def test_extract_coerces_non_string_values():
    service = make_service(['{"product_name": "Laptop", "price": 999, "rating": 4.5}'])

    record = await service.extract(
        make_request(),
        "page text",
    )

    assert record.fields["price"] == "999"
    assert record.fields["rating"] == "4.5"


@pytest.mark.asyncio
async def test_extract_marks_missing_fields():
    service = make_service(['{"product_name": "Laptop"}'])

    record = await service.extract(
        make_request(),
        "page text",
    )

    assert record.fields == {"product_name": "Laptop"}
    assert record.missing_fields == ["price", "rating"]
    assert record.confidence == pytest.approx(1 / 3)


@pytest.mark.asyncio
async def test_extract_ignores_extra_keys():
    service = make_service(
        ['{"product_name": "Laptop", "price": "$999", "rating": "4.5", "evil": "x"}']
    )

    record = await service.extract(
        make_request(),
        "page text",
    )

    assert "evil" not in record.fields


@pytest.mark.asyncio
async def test_extract_handles_code_fence():
    service = make_service(
        ['```json\n{"product_name": "Laptop", "price": "$999", "rating": "4.5"}\n```']
    )

    record = await service.extract(
        make_request(),
        "page text",
    )

    assert record.fields["product_name"] == "Laptop"


@pytest.mark.asyncio
async def test_extract_rejects_malformed_json():
    service = make_service(["not json at all"])

    with pytest.raises(ExtractionError):
        await service.extract(
            make_request(),
            "page text",
        )


@pytest.mark.asyncio
async def test_extract_rejects_non_object_json():
    service = make_service(["[1, 2, 3]"])

    with pytest.raises(ExtractionError):
        await service.extract(
            make_request(),
            "page text",
        )


@pytest.mark.asyncio
async def test_extract_no_fields_returns_no_confidence():
    service = make_service(["{}"])

    request = ResearchRequest(
        goal="Anything",
        source_url="https://example.com",
        fields=[],
    )

    record = await service.extract(request, "page text")

    assert record.fields == {}
    assert record.missing_fields == []
    assert record.confidence is None


@pytest.mark.asyncio
async def test_mock_provider_echoes_empty_fields():
    provider = MockLLMProvider()

    output = await provider.generate_json(
        "Requested fields:\n- product_name: Product name\n- price: Price"
    )

    assert json.loads(output) == {
        "product_name": "",
        "price": "",
    }


def test_build_llm_provider_factory():
    from ai_web_research_agent.config.settings import Settings
    from ai_web_research_agent.infrastructure.llm import build_llm_provider

    settings = Settings(
        llm_provider="mock",
    )

    provider = build_llm_provider(settings)

    assert isinstance(provider, MockLLMProvider)

    openai_settings = Settings(
        llm_provider="openai",
        llm_api_key=None,
    )

    with pytest.raises(ValueError):
        build_llm_provider(openai_settings)

    unknown_settings = Settings(
        llm_provider="anthropic",
    )

    with pytest.raises(ValueError):
        build_llm_provider(unknown_settings)
