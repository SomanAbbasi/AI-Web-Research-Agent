from fastapi.testclient import TestClient

from ai_web_research_agent.app import app

client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "healthy"


def test_version():
    response = client.get("/version")

    assert response.status_code == 200
