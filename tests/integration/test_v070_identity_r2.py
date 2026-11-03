"""v0.7.0 task 63, round 2 (review of 2026-11-03; spec D18 widened, D20, D21): .env.example works as copied, no
issuer override in the example, MCP re-verifies the token on every call, every paid merchant action is limited,
admin has no merchant of its own, workbench routes refuse operators and services, unexpected tool errors are
audited. Scripted model, no network, no cost."""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import sqlite3

import anyio
import pytest
from fastapi.testclient import TestClient
from mcp import Client

from merchant_assistant.api import identity
from merchant_assistant.api.app import create_app
from merchant_assistant.api.identity import Identity, Principal
from merchant_assistant.config import PROJECT_ROOT, Settings
from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import seed
from merchant_assistant.testing import merchant_headers, token_headers
from merchant_assistant.tools import registry
from merchant_assistant.tools.base import CustomerContext, ToolEnv

CLOCK = FixedClock("2026-10-26T10:00:00")
ADMIN = Principal.of("admin", "default")
DEMO = Principal.of("demo", "default", "cliente1988")


def example_lines() -> dict[str, str]:
    lines = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    return dict(line.split("=", 1) for line in lines if line and not line.startswith("#") and "=" in line)


# --- P1-1 and P2-1: the documented `cp .env.example .env` -----------------------------------------------------------


def test_env_example_as_copied_issues_and_verifies_tokens(tmp_path):
    settings = Settings(
        _env_file=PROJECT_ROOT / ".env.example",
        runtime_dir=tmp_path / "runtime",
        password_hash_iterations=1_000,  # only the hashing cost differs from the file
    )
    assert settings.jwt_private_key_path is None and settings.jwt_jwks_url is None  # `KEY=` means unset
    client = TestClient(create_app(settings=settings))
    jwks = client.get("/.well-known/jwks.json")
    assert jwks.status_code == 200 and jwks.json()["keys"]
    token = client.post(
        "/v1/auth/token",
        data={"grant_type": "password", "username": "cliente1988", "password": "cliente1988-fictitious"},
    )
    assert token.status_code == 200, token.text
    headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
    assert client.get("/v1/profiles", headers=headers).status_code == 200
    assert (tmp_path / "runtime" / "jwt" / "signing_key.pem").exists()


def test_empty_paths_and_urls_mean_unset():
    settings = Settings(_env_file=None, jwt_private_key_path="", runtime_dir=" ", checkpoints_path="", jwt_jwks_url="")
    assert (settings.jwt_private_key_path, settings.runtime_dir, settings.checkpoints_path, settings.jwt_jwks_url) == (
        None,
        None,
        None,
        None,
    )


def test_issuer_is_not_overridden_by_the_example():
    assert "JWT_ISSUER" not in example_lines()  # an active value would override the compose default
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "JWT_ISSUER: ${JWT_ISSUER:-http://api:8000}" in compose
    assert Settings(_env_file=PROJECT_ROOT / ".env.example").jwt_issuer == "http://127.0.0.1:8000"


# --- P2-2: MCP re-verifies the token on every call --------------------------------------------------------------------


def test_mcp_refuses_calls_after_the_token_is_revoked(settings):
    from merchant_assistant.mcp_server import build_server, env_factory_for, principal_for_token
    from merchant_assistant.mocks.clients import in_process_client

    conn = connect(settings.db_path)
    seed(conn, CLOCK)
    issuer = Identity(settings)
    token = issuer.issue(Principal.merchant("cliente1988"), "merchant-assistant-cli")["access_token"]
    principal = principal_for_token(issuer, conn, token)
    server = build_server(
        env_factory_for(settings.db_path, principal, CLOCK, in_process_client()),
        authorize=lambda c: principal_for_token(issuer, c, token),
    )

    async def call():
        async with Client(server) as client:
            return await client.call_tool("get_device_status", {})

    assert anyio.run(call).is_error is False
    issuer.revoke(conn, issuer.decode(token))
    refused = anyio.run(call)
    assert refused.is_error and json.loads(refused.content[0].text)["error"]["code"] == "INVALID_TOKEN"
    rows = conn.execute("SELECT tool, outcome, principal_id FROM audit_events ORDER BY id").fetchall()
    assert [tuple(r) for r in rows] == [
        ("get_device_status", "ok", "merchant:cliente1988"),
        ("get_device_status", "invalid_token", "merchant:cliente1988"),
    ]


# --- P2-3 / D18 widened: every paid merchant action is limited -------------------------------------------------------


def test_router_compare_counts_in_the_per_token_action_limit(offline, settings):
    settings.demo_session_message_limit = 1
    client, _, _ = offline()
    headers = merchant_headers(client)
    body = {"message": "Olá", "profile_id": "reference", "profile_version": 1, "selected_mechanism": "llm"}
    assert client.post("/v1/router/compare", headers=headers, json=body).status_code == 201
    second = client.post("/v1/router/compare", headers=headers, json=body)
    assert second.status_code == 429 and second.json()["error"]["code"] == "demo_message_limit_reached"


def test_paid_routes_pass_the_rate_limit(offline, settings, monkeypatch):
    monkeypatch.setattr(identity, "utc_seconds", lambda: 1_800_000_010.0)  # one fixed 60 s window
    settings.rate_limit_per_minute = 1
    client, _, _ = offline()
    paid = [
        (
            "/v1/router/compare",
            {"message": "Olá", "profile_id": "reference", "profile_version": 1, "selected_mechanism": "llm"},
        ),
        (
            "/v1/runs/req_unknown/evaluations",
            {"confirmed": True, "max_cost_usd": 0.01, "expected_estimate_digest": "x"},
        ),
        (
            "/v1/comparisons",
            {
                "profiles": [
                    {"profile_id": "reference", "profile_version": 1},
                    {"profile_id": "hybrid", "profile_version": 1},
                ],
                "scenario_ids": ["x"],
                "confirmed": True,
                "max_cost_usd": 0.01,
                "expected_estimate_digest": "x",
            },
        ),
    ]
    for index, (path, body) in enumerate(paid):
        headers = merchant_headers(client, ["cliente1988", "cliente_demo_002", "someone_else"][index])  # own window
        client.post(path, headers=headers, json=body)
        limited = client.post(path, headers=headers, json=body)
        assert limited.status_code == 429 and limited.json()["error"]["code"] == "rate_limited", path


# --- D20: admin has no merchant of its own -------------------------------------------------------------------------


def test_admin_uses_the_demo_merchant_only_in_v1_messages(offline, settings):
    client, _, _ = offline()
    admin = token_headers(client, ADMIN)
    claims = client.app.state.identity.decode(admin["Authorization"][7:])
    assert "customer_id" not in claims
    refused = client.post("/messages", headers=admin, json={"message": "Olá"})
    assert refused.status_code == 403 and refused.json()["error"]["code"] == "insufficient_scope"
    message = refused.json()["error"]["message"]
    assert "merchant and demo" in message and "operator" not in message.lower() and "admin" not in message.lower()
    body = {"message": "Olá", "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm"}
    sent = client.post("/v1/messages", headers=admin, json=body)
    assert sent.status_code == 200, sent.text
    owner = sqlite3.connect(settings.db_path).execute(
        "SELECT customer_id FROM conversations WHERE conversation_id=?", (sent.json()["message"]["conversation_id"],)
    )
    assert owner.fetchone()[0] == settings.api_demo_customer_id
    conversation_id = sent.json()["message"]["conversation_id"]
    assert client.get(f"/v1/conversations/{conversation_id}", headers=admin).status_code == 403


# --- D21: least privilege on the workbench routes ------------------------------------------------------------------


@pytest.mark.parametrize("principal", [Principal.operator("op_ana"), Principal.of("service", "ticketing")])
def test_workbench_routes_refuse_operators_and_services(offline, principal):
    client, _, llm = offline()
    headers = token_headers(client, principal)
    gets = [
        "/v1/profiles",
        "/v1/kb/documents",
        "/v1/kb/documents/x",
        "/v1/kb/versions",
        "/v1/kb/versions/x",
        "/v1/catalog/models",
        "/v1/scenarios",
        "/v1/runs/req_x",
        "/v1/comparisons/cmp_x",
    ]
    for path in gets:
        response = client.get(path, headers=headers)
        assert response.status_code == 403 and response.json()["error"]["code"] == "insufficient_scope", path
    merchant = merchant_headers(client)
    assert all(client.get(p, headers=merchant).status_code == 200 for p in ("/v1/profiles", "/v1/scenarios"))
    assert llm.calls == []


# --- P3-3: unexpected tool errors are audited -----------------------------------------------------------------------


def test_unexpected_tool_exception_is_audited_as_error(settings, monkeypatch):
    conn = connect(settings.db_path)
    seed(conn, CLOCK)

    def broken(env, args):
        raise RuntimeError("boom")

    spec = registry.TOOLS["get_device_status"]
    monkeypatch.setitem(registry.TOOLS, "get_device_status", dataclasses.replace(spec, fn=broken))
    env = ToolEnv(conn, CLOCK, CustomerContext.for_principal(Principal.merchant("cliente1988"), "cliente1988", True))
    with pytest.raises(RuntimeError):
        registry.execute("get_device_status", {}, env)
    row = conn.execute("SELECT tool, scope, outcome, principal_id FROM audit_events").fetchone()
    assert tuple(row) == ("get_device_status", "support:read", "error", "merchant:cliente1988")


# --- P3-5: the synthetic v0.4.0 script uses the v0.7.0 credentials -------------------------------------------------


def test_synthetic_v040_script_logs_in_with_passwords(tmp_path):
    path = PROJECT_ROOT / "tools" / "scripts" / "run_synthetic_v040_api.py"
    spec = importlib.util.spec_from_file_location("run_synthetic_v040_api", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.CACHE.resolve() not in tmp_path.resolve().parents:
        pytest.skip("the script only writes under .pytest_cache (run with the project's --basetemp)")
    client = TestClient(module.build(tmp_path / "v040"))
    for user, password in (("demo", "v040-synthetic-demo-password"), ("admin", "v040-synthetic-admin-password")):
        token = client.post("/v1/auth/token", data={"grant_type": "password", "username": user, "password": password})
        assert token.status_code == 200, (user, token.text)
