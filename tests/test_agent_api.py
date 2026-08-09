from urllib.parse import quote_plus

import pytest
from fastapi.testclient import TestClient

from ai_web_research_agent.app import app

EMPTY_SEARCH = "<html><body></body></html>"

SOURCE_HTML = "<html><head><title>Laptop</title></head><body><p>Laptop costs $999</p></body></html>"

SEARCH_URL = "https://html.duckduckgo.com/html/?q=" + quote_plus("Find laptop price name price")


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_run_agent_endpoint(client, httpx_mock):
    httpx_mock.add_response(
        url=SEARCH_URL,
        status_code=200,
        headers={"content-type": "text/html"},
        text=EMPTY_SEARCH,
    )
    httpx_mock.add_response(
        url=SEARCH_URL,
        status_code=200,
        headers={"content-type": "text/html"},
        text=EMPTY_SEARCH,
    )
    httpx_mock.add_response(
        url="https://a.com/1",
        status_code=200,
        headers={"content-type": "text/html"},
        text=SOURCE_HTML,
    )

    response = client.post(
        "/research/agent",
        json={
            "goal": "Find laptop price",
            "fields": [
                {"name": "name", "description": "Product name"},
                {"name": "price", "description": "Price"},
            ],
            "max_retries": 1,
            "candidate_urls": ["https://a.com/1"],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "completed"
    assert body["goal"] == "Find laptop price"
    assert body["session_id"]
    assert body["sources_used"] == ["https://a.com/1"]
    assert "summary" in body
    assert "steps" in body


def test_run_agent_validates_request(client):
    response = client.post(
        "/research/agent",
        json={
            "goal": "",
            "fields": [],
        },
    )

    assert response.status_code == 422
