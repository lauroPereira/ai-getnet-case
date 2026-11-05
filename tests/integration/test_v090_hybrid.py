"""Task 80 (v0.9.0, D7): RETRIEVAL_MODE reaches the Knowledge agent through the active version, with fake embeddings."""

import pytest

from merchant_assistant.testing import merchant_headers, offline_orchestrator

QUESTION = "Qual a diferença entre a Get Clássica e a Get Smart?"


def knowledge_hits(orchestrator, request_id):
    return next(s["detail"]["hits"] for s in orchestrator.trace(request_id)["steps"] if s["step"] == "knowledge")


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
def test_knowledge_answers_in_both_modes_with_the_configured_one(settings, mode):
    from fastapi.testclient import TestClient

    from merchant_assistant.api.app import create_app

    configured = settings.model_copy(update={"retrieval_mode": mode})
    orchestrator, _ = offline_orchestrator(configured)
    client = TestClient(create_app(orchestrator, configured))
    response = client.post(
        "/messages",
        json={"message": QUESTION, "user_id": "cliente1988"},
        headers=merchant_headers(client, "cliente1988"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["route"] == "knowledge" and body["status"] == "answered" and body["sources"]
    active, _ = orchestrator.knowledge_base.capture_active()
    assert active.mode == mode  # the per-request index keeps RETRIEVAL_MODE
    hits = knowledge_hits(orchestrator, body["request_id"])
    assert hits and any("maquininhas" in hit["doc"] for hit in hits)
