from fastapi.testclient import TestClient

from merchant_assistant.api.app import create_app
from merchant_assistant.api.schemas import CHALLENGE_EXAMPLES, MessageResponse
from merchant_assistant.testing import merchant_headers


def client(settings):
    return TestClient(create_app(settings=settings))


def test_valid_request_returns_contract(settings):
    c = client(settings)
    response = c.post("/messages", json={"message": CHALLENGE_EXAMPLES[0]}, headers=merchant_headers(c))
    assert response.status_code == 200
    body = MessageResponse.model_validate(response.json())
    assert body.request_id == response.headers["X-Request-ID"]
    assert body.conversation_id.startswith("conv_")


def test_missing_field_returns_documented_error(settings):
    c = client(settings)
    response = c.post("/messages", json={"user_id": "cliente1988"}, headers=merchant_headers(c))
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert "message" in error["message"]
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_rejects_oversized_message_and_bad_user_id(settings):
    c = client(settings)
    headers = merchant_headers(c)
    assert c.post("/messages", json={"message": "x" * 2001}, headers=headers).status_code == 422
    assert c.post("/messages", json={"message": "hi", "user_id": "bad id!"}, headers=headers).status_code == 422
    assert c.post("/messages", json={"message": ""}, headers=headers).status_code == 422


def test_rejects_unknown_fields(settings):
    c = client(settings)
    response = c.post("/messages", json={"message": "hi", "admin": True}, headers=merchant_headers(c))
    assert response.status_code == 422


def test_openapi_lists_challenge_examples_and_the_session(settings):
    spec = client(settings).get("/openapi.json").json()
    examples = spec["components"]["schemas"]["MessageRequest"]["examples"]
    assert len(examples) == 10
    assert all(set(e) == {"message"} for e in examples)  # the merchant comes from the session
    route = spec["paths"]["/messages"]["post"]
    assert route["security"] == [{"SessionBearer": []}]
    assert "/v1/auth/token" in route["description"] and "Authorization: Bearer" in route["description"]
    assert {"401", "403", "429"} <= set(route["responses"])


def test_traces_endpoint_only_in_demo_mode(settings):
    settings.demo_mode = False
    assert client(settings).get("/traces/req_x").status_code == 404
