from fastapi.testclient import TestClient

from merchant_assistant.api.app import create_app
from merchant_assistant.api.schemas import CHALLENGE_EXAMPLES, MessageResponse


def client(settings):
    return TestClient(create_app(settings=settings))


def test_valid_request_returns_contract(settings):
    response = client(settings).post("/messages", json={"message": CHALLENGE_EXAMPLES[0], "user_id": "cliente1988"})
    assert response.status_code == 200
    body = MessageResponse.model_validate(response.json())
    assert body.request_id == response.headers["X-Request-ID"]
    assert body.conversation_id.startswith("conv_")


def test_missing_field_returns_documented_error(settings):
    response = client(settings).post("/messages", json={"message": "hi"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert "user_id" in error["message"]
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_rejects_oversized_message_and_bad_user_id(settings):
    c = client(settings)
    assert c.post("/messages", json={"message": "x" * 2001, "user_id": "cliente1988"}).status_code == 422
    assert c.post("/messages", json={"message": "hi", "user_id": "bad id!"}).status_code == 422
    assert c.post("/messages", json={"message": "", "user_id": "cliente1988"}).status_code == 422


def test_rejects_unknown_fields(settings):
    response = client(settings).post("/messages", json={"message": "hi", "user_id": "a", "admin": True})
    assert response.status_code == 422


def test_openapi_lists_challenge_examples(settings):
    spec = client(settings).get("/openapi.json").json()
    examples = spec["components"]["schemas"]["MessageRequest"]["examples"]
    assert len(examples) == 10
    assert all(e["user_id"] == "cliente1988" for e in examples)


def test_traces_endpoint_only_in_demo_mode(settings):
    settings.demo_mode = False
    assert client(settings).get("/traces/req_x").status_code == 404
