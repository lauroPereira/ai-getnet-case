"""The challenge's literal payload (`message` + `user_id`, no token) must get a 401 that says how to obtain a token:
`POST /v1/auth/token` with the password grant and the demo users of `.env.example`. No model call is made."""

from __future__ import annotations


def test_messages_without_token_explains_how_to_get_one(offline):
    client, _, llm = offline()

    payload = {"message": "When will the money from yesterday's sales be deposited?", "user_id": "cliente1988"}
    response = client.post("/messages", json=payload)

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "token_required"
    assert "POST /v1/auth/token" in error["message"]
    assert "grant_type=password" in error["message"]
    assert ".env.example" in error["message"]
    assert "Authorization: Bearer" in error["message"]
    assert response.headers["WWW-Authenticate"] == 'Bearer realm="merchant-assistant"'
    assert llm.calls == []


def test_v1_routes_without_token_give_the_same_hint(offline):
    client, _, _ = offline()

    response = client.get("/v1/profiles")

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "token_required"
    assert "POST /v1/auth/token" in error["message"]
