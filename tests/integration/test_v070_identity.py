"""v0.7.0 task 63 (CA-46, spec version 2): JWT issued by the assistant (token, revoke, JWKS, discovery), token
required on /messages, merchant from the principal, identity_mismatch, operator and service boundaries, own-merchant
reads on /v1 and demo routes, one audit row per tool call, rate limit before any model call, MCP by token and the
smoke with a token. Scripted model, keys generated in the tests, no network, no cost."""

from __future__ import annotations

import logging
import sqlite3

import jwt
import pytest
from fastapi.testclient import TestClient

from merchant_assistant.api import identity
from merchant_assistant.api.app import create_app
from merchant_assistant.api.identity import Principal
from merchant_assistant.api.schemas import CHALLENGE_EXAMPLES, MessageRequest
from merchant_assistant.testing import (
    TEST_TICKETING_SECRET,
    TEST_USER_PASSWORDS,
    merchant_headers,
    password_headers,
    token_headers,
)

DEVICE = CHALLENGE_EXAMPLES[4]
DEMO = Principal.of("demo", "default", "cliente1988")
ADMIN = Principal.of("admin", "default", "cliente1988")


def token_request(client, **form):
    return client.post("/v1/auth/token", data=form)


def post(client, message, headers, **extra):
    return client.post("/messages", json={"message": message, **extra}, headers=headers)


def operator_headers(client, operator="op_ana"):
    return token_headers(client, Principal.operator(operator))


def audit(settings):
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM audit_events ORDER BY id")]
    finally:
        conn.close()


def tool_steps(orchestrator, request_id):
    return [s for s in orchestrator.trace(request_id)["steps"] if s["step"].startswith("tool:")]


# --- issuer ------------------------------------------------------------------------------------------------------


def test_password_grant_issues_tokens_per_principal(offline, settings, caplog):
    client, _, _ = offline()
    with caplog.at_level(logging.DEBUG):
        merchant = token_request(
            client, grant_type="password", username="cliente_demo_002", password=TEST_USER_PASSWORDS["cliente_demo_002"]
        )
    assert merchant.status_code == 200 and merchant.headers["cache-control"] == "no-store"
    body = merchant.json()
    assert set(body) == {"access_token", "token_type", "expires_in", "scope"}
    assert body["token_type"] == "Bearer" and body["expires_in"] == 3600
    assert set(body["scope"].split()) == {"support:read", "handoff:create", "conversation:read"}
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert (claims["sub"], claims["customer_id"], claims["client_id"]) == (
        "merchant:cliente_demo_002",
        "cliente_demo_002",
        "merchant-assistant-web",
    )
    logs = "\n".join(r.getMessage() for r in caplog.records)
    assert TEST_USER_PASSWORDS["cliente_demo_002"] not in logs and body["access_token"] not in logs
    operator = token_request(
        client, grant_type="password", username="op_bruno", password=TEST_USER_PASSWORDS["op_bruno"]
    )
    assert set(operator.json()["scope"].split()) == {"handoff:operate", "support:read"}
    assert "handoff:operate" not in body["scope"]
    stored = sqlite3.connect(settings.db_path).execute(
        "SELECT role, customer_id, scopes FROM api_principals WHERE principal_id='operator:op_bruno'"
    )
    assert stored.fetchone() == ("operator", None, '["handoff:operate", "support:read"]')


def test_token_endpoint_errors_follow_rfc6749_and_do_not_say_which_field_failed(offline):
    client, _, _ = offline()
    wrong_password = token_request(client, grant_type="password", username="cliente1988", password="nope")
    unknown_user = token_request(client, grant_type="password", username="nobody", password="nope")
    for response in (wrong_password, unknown_user):
        assert response.status_code == 400 and response.json()["error"] == "invalid_grant"
        assert set(response.json()) == {"error", "error_description"}  # RFC 6749 §5.2, not the project envelope
        assert response.headers["cache-control"] == "no-store"
    assert wrong_password.json() == unknown_user.json()
    unknown_client = token_request(
        client, grant_type="password", username="cliente1988", password="x", client_id="rogue-app"
    )
    assert unknown_client.status_code == 401 and unknown_client.json()["error"] == "invalid_client"
    assert unknown_client.headers["www-authenticate"].startswith("Basic")
    grant = token_request(client, grant_type="authorization_code", code="x")
    assert grant.status_code == 400 and grant.json()["error"] == "unsupported_grant_type"
    for incomplete in ({}, {"grant_type": "password", "username": "cliente1988"}):
        response = token_request(client, **incomplete)
        assert response.status_code == 400 and response.json()["error"] == "invalid_request"


def test_token_attempts_are_limited_per_account_and_address(offline, settings, monkeypatch):
    monkeypatch.setattr(identity, "utc_seconds", lambda: 1_800_000_010.0)  # fixed clock: one 60 s window
    settings.auth_attempts_per_minute = 2
    client, _, _ = offline()
    for _ in range(2):
        assert token_request(client, grant_type="password", username="op_ana", password="wrong").status_code == 400
    blocked = token_request(
        client, grant_type="password", username="op_ana", password=TEST_USER_PASSWORDS["op_ana"]
    )  # even the right password: the attempt is counted before any hashing
    assert blocked.status_code == 429 and blocked.json()["error"] == "rate_limited"
    assert 1 <= int(blocked.headers["retry-after"]) <= 60
    other_user = token_request(
        client, grant_type="password", username="op_bruno", password=TEST_USER_PASSWORDS["op_bruno"]
    )
    assert other_user.status_code == 200
    for _ in range(2):
        token_request(client, grant_type="client_credentials", client_id="ticketing-demo", client_secret="wrong")
    refused = token_request(
        client, grant_type="client_credentials", client_id="ticketing-demo", client_secret=TEST_TICKETING_SECRET
    )
    assert refused.status_code == 429


def test_client_credentials_for_the_ticketing_service(offline):
    client, _, llm = offline()
    issued = token_request(
        client, grant_type="client_credentials", client_id="ticketing-demo", client_secret=TEST_TICKETING_SECRET
    )
    assert issued.status_code == 200 and issued.json()["expires_in"] == 600
    assert issued.json()["scope"] == "handoff:integrate"
    claims = jwt.decode(issued.json()["access_token"], options={"verify_signature": False})
    assert (claims["sub"], claims["role"], claims["client_id"]) == ("service:ticketing", "service", "ticketing-demo")
    assert "customer_id" not in claims
    basic = client.post(
        "/v1/auth/token", data={"grant_type": "client_credentials"}, auth=("ticketing-demo", TEST_TICKETING_SECRET)
    )
    assert basic.status_code == 200
    refused = token_request(
        client, grant_type="client_credentials", client_id="ticketing-demo", client_secret="wrong-secret"
    )
    assert refused.status_code == 401 and refused.json()["error"] == "invalid_client"
    unknown = token_request(client, grant_type="client_credentials", client_id="rogue", client_secret="x")
    assert unknown.status_code == 401 and unknown.json()["error"] == "invalid_client"
    service = {"Authorization": f"Bearer {issued.json()['access_token']}"}
    assert post(client, DEVICE, service).status_code == 403
    assert llm.calls == []


def test_published_jwks_validates_the_issued_token_independently(offline):
    client, _, _ = offline()
    discovery = client.get("/.well-known/openid-configuration").json()
    assert discovery["issuer"] == "http://127.0.0.1:8000"
    assert discovery["jwks_uri"] == "http://127.0.0.1:8000/.well-known/jwks.json"
    assert discovery["token_endpoint"].endswith("/v1/auth/token")
    assert set(discovery["grant_types_supported"]) == {"password", "client_credentials"}
    assert "handoff:integrate" in discovery["scopes_supported"]
    jwks = client.get("/.well-known/jwks.json").json()
    assert all("d" not in key and "p" not in key for key in jwks["keys"])  # public parts only
    token = password_headers(client, "op_ana", TEST_USER_PASSWORDS["op_ana"])["Authorization"][7:]
    keys = jwt.PyJWKSet.from_dict(jwks)
    signing = next(k for k in keys.keys if k.key_id == jwt.get_unverified_header(token)["kid"])
    claims = jwt.decode(token, signing.key, algorithms=["RS256"], audience="ticketing", issuer=discovery["issuer"])
    assert claims["sub"] == "operator:op_ana" and claims["scope"] == "handoff:operate support:read"


def test_revoked_token_is_refused(offline):
    client, _, _ = offline()
    headers = merchant_headers(client)
    assert client.get("/v1/profiles", headers=headers).status_code == 200
    assert client.post("/v1/auth/revoke", headers=headers).status_code == 200
    assert client.get("/v1/profiles", headers=headers).status_code == 401
    assert post(client, DEVICE, headers).status_code == 401


# --- POST /messages -----------------------------------------------------------------------------------------------


def test_messages_without_a_valid_token_is_401(offline):
    client, _, llm = offline()
    expired = client.app.state.identity.issue(Principal.merchant("cliente1988"), "t", now=1_000_000_000)
    for headers in (
        {},
        {"Authorization": "Bearer not-a-token"},
        {"Authorization": "Basic abc"},
        {"Authorization": f"Bearer {expired['access_token']}"},
    ):
        response = post(client, DEVICE, headers, user_id="cliente1988")
        assert response.status_code == 401
        assert response.json()["error"]["code"] in {"token_required", "invalid_token"}
        assert response.headers["www-authenticate"].startswith("Bearer")
    assert llm.calls == []


def test_merchant_comes_from_the_principal_and_mismatch_is_403(offline, settings):
    client, orchestrator, llm = offline()
    headers = merchant_headers(client, "cliente_demo_002")
    mismatch = post(client, DEVICE, headers, user_id="cliente1988")
    assert mismatch.status_code == 403 and mismatch.json()["error"]["code"] == "identity_mismatch"
    assert llm.calls == []
    without_user = post(client, CHALLENGE_EXAMPLES[2], headers)
    assert without_user.status_code == 200
    assert orchestrator.trace(without_user.json()["request_id"])["user_id"] == "cliente_demo_002"
    same_user = post(client, CHALLENGE_EXAMPLES[2], headers, user_id="cliente_demo_002")
    assert same_user.status_code == 200
    conversation = sqlite3.connect(settings.db_path).execute(
        "SELECT customer_id FROM conversations WHERE conversation_id=?", (same_user.json()["conversation_id"],)
    )
    assert conversation.fetchone()[0] == "cliente_demo_002"


def test_operator_session_cannot_send_messages_and_merchant_has_no_operate_scope(offline):
    client, _, llm = offline()
    headers = operator_headers(client)
    refused = post(client, DEVICE, headers)
    assert refused.status_code == 403 and refused.json()["error"]["code"] == "insufficient_scope"
    assert 'error="insufficient_scope"' in refused.headers["www-authenticate"]
    v1 = client.post(
        "/v1/messages",
        headers=headers,
        json={"message": DEVICE, "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm"},
    )
    assert v1.status_code == 403
    assert llm.calls == []
    assert "handoff:operate" not in Principal.merchant("cliente1988").scopes


def test_merchant_sees_the_demo_profiles_and_shares_the_action_limit(offline, settings):
    settings.demo_session_message_limit = 1
    client, _, _ = offline()
    admin = token_headers(client, ADMIN)
    agents = next(p["agents"] for p in client.get("/v1/profiles", headers=admin).json()["profiles"])
    created = client.post(
        "/v1/profiles", headers=admin, json={"name": "Internal only", "agents": agents, "demo_allowed": False}
    ).json()
    published = client.post(
        f"/v1/profiles/{created['profile_id']}/publish", headers=admin, json={"expected_version": 1}
    )
    assert published.status_code == 200
    merchant = merchant_headers(client)
    visible = {p["profile_id"] for p in client.get("/v1/profiles", headers=merchant).json()["profiles"]}
    demo_visible = {
        p["profile_id"] for p in client.get("/v1/profiles", headers=token_headers(client, DEMO)).json()["profiles"]
    }
    assert visible == demo_visible and created["profile_id"] not in visible  # D18
    body = {"message": "Olá", "profile_id": created["profile_id"], "profile_version": 1, "router_mechanism": "llm"}
    assert client.post("/v1/messages", headers=merchant, json=body).status_code == 404
    body |= {"profile_id": "reference"}
    assert client.post("/v1/messages", headers=merchant, json=body).status_code == 200
    limited = client.post("/v1/messages", headers=merchant, json=body)
    assert limited.status_code == 429 and limited.json()["error"]["code"] == "demo_message_limit_reached"
    fresh = token_headers(client, Principal.merchant("cliente1988"))  # the limit is per token
    assert client.post("/v1/messages", headers=fresh, json=body).status_code == 200


# --- reads of another merchant ------------------------------------------------------------------------------------


def test_merchant_b_never_reads_conversation_or_trace_of_merchant_a(offline, settings):
    client, _, _ = offline()
    a, b = merchant_headers(client, "cliente1988"), merchant_headers(client, "cliente_demo_002")
    sent = post(client, DEVICE, a).json()
    conversation_id, request_id = sent["conversation_id"], sent["request_id"]

    assert client.get(f"/conversations/{conversation_id}", headers=a).status_code == 200
    assert client.get(f"/traces/{request_id}", headers=a).status_code == 200
    assert client.get(f"/v1/conversations/{conversation_id}", headers=a).status_code == 200
    for path in (f"/conversations/{conversation_id}", f"/traces/{request_id}", f"/v1/conversations/{conversation_id}"):
        response = client.get(path, headers=b)
        assert response.status_code == 404, path
        assert "cliente1988" not in response.text
        assert client.get(path).status_code == 401, path
    # B cannot continue A's conversation either.
    assert post(client, "oi", b, conversation_id=conversation_id).status_code == 404

    admin = token_headers(client, ADMIN)
    assert client.get(f"/conversations/{conversation_id}", headers=admin).status_code == 200
    assert client.get(f"/traces/{request_id}", headers=admin).status_code == 200


def test_merchant_b_never_reads_the_v1_run_of_merchant_a(offline):
    client, _, _ = offline()
    a, b = merchant_headers(client, "cliente1988"), merchant_headers(client, "cliente_demo_002")
    sent = client.post(
        "/v1/messages",
        headers=a,
        json={"message": DEVICE, "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm"},
    )
    assert sent.status_code == 200, sent.text
    request_id = sent.json()["message"]["request_id"]
    assert client.get(f"/v1/runs/{request_id}", headers=a).status_code == 200
    assert client.get(f"/v1/runs/{request_id}", headers=b).status_code == 404
    assert client.get(f"/traces/{request_id}", headers=b).status_code == 404


def test_operator_reads_only_conversations_with_a_handoff_case(offline):
    client, _, _ = offline()
    a = merchant_headers(client, "cliente1988")
    plain = post(client, CHALLENGE_EXAMPLES[2], a).json()
    handed = post(client, "Quero falar com um atendente", a).json()
    assert handed["status"] == "handoff"
    operator = operator_headers(client)
    assert client.get(f"/conversations/{plain['conversation_id']}", headers=operator).status_code == 404
    assert client.get(f"/traces/{plain['request_id']}", headers=operator).status_code == 404
    assert client.get(f"/conversations/{handed['conversation_id']}", headers=operator).status_code == 200
    assert client.get(f"/traces/{handed['request_id']}", headers=operator).status_code == 200


# --- audit of every tool call -------------------------------------------------------------------------------------


def test_n_tool_calls_leave_n_audit_rows_with_principal_scope_and_result(offline, settings):
    client, orchestrator, _ = offline()
    headers = merchant_headers(client, "cliente1988")
    request_ids = [
        post(client, message, headers).json()["request_id"]
        for message in (DEVICE, CHALLENGE_EXAMPLES[2], "What is the payout status of receivable rcv_002_0001?")
    ]
    calls = sum(orchestrator.trace(rid)["tool_calls"] for rid in request_ids)
    rows = audit(settings)
    assert calls >= 5 and len(rows) == calls
    assert {r["principal_id"] for r in rows} == {"merchant:cliente1988"}
    assert {r["customer_id"] for r in rows} == {"cliente1988"}
    assert {r["scope"] for r in rows} == {"support:read"}
    assert [r["tool"] for r in rows] == [
        s["step"].removeprefix("tool:") for rid in request_ids for s in tool_steps(orchestrator, rid)
    ]
    assert {r["outcome"] for r in rows} == {"ok", "forbidden"}
    assert all(r["outcome"] in {"ok", "forbidden"} for r in rows)


@pytest.mark.parametrize(
    ("principal", "expected"),
    [
        (Principal("merchant:cliente1988", "merchant", "cliente1988", ("handoff:create",)), "forbidden_scope"),
        (Principal.merchant("cliente_demo_002"), "forbidden_customer"),  # another merchant's principal
    ],
)
def test_refused_tool_calls_are_audited_and_never_run(offline, settings, principal, expected):
    _, orchestrator, _ = offline()
    response = orchestrator.handle(
        MessageRequest(message=DEVICE, user_id="cliente1988"), "req_refused", principal=principal
    )
    trace = orchestrator.trace("req_refused")
    rows = [r for r in audit(settings) if r["tool"] != "handoff_case.create"]  # the case write has its own row
    assert trace["tool_calls"] >= 2 and len(rows) == trace["tool_calls"]
    assert {r["outcome"] for r in rows} == {expected}
    assert {r["principal_id"] for r in rows} == {principal.principal_id}
    assert all(s["status"] == "error" for s in tool_steps(orchestrator, "req_refused"))
    assert "cliente_demo_002" not in response.answer


def test_escalation_checks_handoff_create_before_writing_the_case(offline, settings):
    _, orchestrator, _ = offline()
    no_handoff = Principal("merchant:cliente1988", "merchant", "cliente1988", ("support:read", "conversation:read"))
    response = orchestrator.handle(
        MessageRequest(message="Quero falar com um atendente", user_id="cliente1988"),
        "req_no_case",
        principal=no_handoff,
    )
    conn = sqlite3.connect(settings.db_path)
    assert conn.execute("SELECT COUNT(*) FROM handoff_cases").fetchone()[0] == 0
    assert response.handoff is None
    rows = [r for r in audit(settings) if r["tool"] == "handoff_case.create"]
    assert [(r["scope"], r["outcome"], r["principal_id"]) for r in rows] == [
        ("handoff:create", "forbidden_scope", "merchant:cliente1988")
    ]
    allowed = orchestrator.handle(
        MessageRequest(message="Quero falar com um atendente", user_id="cliente1988"),
        "req_case",
        principal=Principal.merchant("cliente1988"),
    )
    case_rows = [r for r in audit(settings) if r["tool"] == "handoff_case.create" and r["outcome"] == "ok"]
    assert allowed.handoff is not None and len(case_rows) == 1
    assert case_rows[0]["resource_id"] == conn.execute("SELECT case_id FROM handoff_cases").fetchone()[0]


# --- rate limit ---------------------------------------------------------------------------------------------------


def test_rate_limit_returns_429_before_any_model_call(offline, settings, monkeypatch):
    settings.rate_limit_per_minute = 2
    clock = {"now": 1_800_000_000.0}
    monkeypatch.setattr(identity, "utc_seconds", lambda: clock["now"])
    client, _, llm = offline()
    headers = merchant_headers(client)
    assert [post(client, "Olá", headers).status_code for _ in range(2)] == [200, 200]
    calls_before = len(llm.calls)
    limited = post(client, DEVICE, headers)
    assert limited.status_code == 429 and limited.json()["error"]["code"] == "rate_limited"
    assert limited.headers["Retry-After"] == "60"
    assert len(llm.calls) == calls_before
    assert post(client, "Olá", merchant_headers(client, "cliente_demo_002")).status_code == 200  # per principal
    demo = token_headers(client, DEMO)
    body = {"message": "Olá", "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm"}
    assert [client.post("/v1/messages", headers=demo, json=body).status_code for _ in range(3)] == [200, 200, 429]
    clock["now"] += 60
    assert post(client, "Olá", headers).status_code == 200


# --- MCP, startup and smoke ---------------------------------------------------------------------------------------


def test_mcp_derives_the_merchant_from_the_token_and_refuses_others(settings):
    from merchant_assistant.data.db import connect
    from merchant_assistant.mcp_server import AccessRefused, env_factory_for, principal_for_token

    issuer = identity.Identity(settings)
    conn = connect(settings.db_path)
    try:
        token = issuer.issue(Principal.merchant("cliente_demo_002"), "merchant-assistant-cli")["access_token"]
        principal = principal_for_token(issuer, conn, token)
        assert (principal.principal_id, principal.customer_id) == ("merchant:cliente_demo_002", "cliente_demo_002")
        refused = [
            issuer.issue(Principal.operator("op_ana"), "cli")["access_token"],
            issuer.issue(Principal.of("service", "ticketing"), "ticketing-demo")["access_token"],
            "not-a-token",
            None,
        ]
        for bad in refused:
            with pytest.raises(AccessRefused):
                principal_for_token(issuer, conn, bad)
    finally:
        conn.close()
    env = env_factory_for(settings.db_path, principal, None)()
    try:
        assert env.customer.customer_id == "cliente_demo_002"
        assert env.customer.principal_id == "merchant:cliente_demo_002"
    finally:
        env.conn.close()
    with pytest.raises(ValueError):
        env_factory_for(settings.db_path, Principal.operator("op_ana"), None)


def test_mcp_cli_has_no_customer_option():
    from merchant_assistant import cli

    with pytest.raises(SystemExit):
        cli.main(["mcp", "--customer", "cliente1988"])


def test_example_values_log_a_warning_at_startup(settings, caplog):
    from pydantic import SecretStr

    settings.ticketing_client_secret = SecretStr("ticketing-demo-secret-fictitious")
    with caplog.at_level(logging.WARNING, logger="merchant_assistant.api"):
        create_app(settings=settings)
    messages = [r.getMessage() for r in caplog.records]
    assert any("example credentials" in m and "client:ticketing-demo" in m for m in messages)
    assert not any("ticketing-demo-secret-fictitious" in m for m in messages)


def test_smoke_gets_its_token_and_passes(offline, capsys):
    from merchant_assistant.cli import run_smoke

    client, _, _ = offline()
    assert run_smoke(client, "cliente1988", TEST_USER_PASSWORDS["cliente1988"]) == 0
    out = capsys.readouterr().out
    assert "token for cliente1988" in out and out.count("200 ") == len(CHALLENGE_EXAMPLES)
    assert run_smoke(client, "cliente1988", "wrong-password") == len(CHALLENGE_EXAMPLES)


def test_placeholder_app_also_requires_a_token(settings):
    client = TestClient(create_app(settings=settings))
    assert client.post("/messages", json={"message": "hi"}).status_code == 401
    assert post(client, "hi", merchant_headers(client)).status_code == 200
