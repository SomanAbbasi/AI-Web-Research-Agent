import pytest
from fastapi.testclient import TestClient

from ai_web_research_agent.app import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def create_session(
    client: TestClient,
    goal: str = "research the market",
) -> dict:
    response = client.post(
        "/research/sessions",
        json={"goal": goal},
    )

    assert response.status_code == 201

    return response.json()


def test_create_session(client):
    body = create_session(client)

    assert body["goal"] == "research the market"
    assert body["status"] == "running"
    assert body["id"]
    assert body["created_at"]


def test_list_sessions(client):
    created = create_session(client)

    response = client.get("/research/sessions")

    assert response.status_code == 200

    bodies = response.json()

    assert any(session["id"] == created["id"] for session in bodies)


def test_get_session(client):
    created = create_session(client)

    response = client.get(f"/research/sessions/{created['id']}")

    assert response.status_code == 200
    assert response.json()["goal"] == "research the market"


def test_get_session_not_found(client):
    response = client.get("/research/sessions/missing")

    assert response.status_code == 404


def test_list_records_empty_session(client):
    created = create_session(client)

    response = client.get(f"/research/sessions/{created['id']}/records")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 0
    assert body["records"] == []


def test_report_returns_empty_json_for_session_without_records(client):
    created = create_session(client)

    response = client.get(f"/research/sessions/{created['id']}/report")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.text == "[]"


def test_report_not_found(client):
    response = client.get("/research/sessions/missing/report")

    assert response.status_code == 404


def test_report_rejects_unknown_format(client):
    created = create_session(client)

    response = client.get(
        f"/research/sessions/{created['id']}/report",
        params={"format": "pdf"},
    )

    assert response.status_code == 422
