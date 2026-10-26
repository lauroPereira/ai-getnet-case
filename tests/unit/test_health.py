from fastapi.testclient import TestClient

from merchant_assistant.api.app import create_app


def test_health_ok(settings):
    client = TestClient(create_app(settings=settings))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"].startswith("req_")


def test_ready_reports_unconfigured_orchestrator(settings):
    client = TestClient(create_app(settings=settings))
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["ready"] is False
