"""v0.7.0 task 68: the P3 gaps that the review of tasks 63 and 64 (`docs/evidence/v070-reviewer.md`) left for the
closing. P3-A: `merchant-assistant mcp` really wires the per-call token check. P3-B: a tool call refused by the request
limit is audited with the principal. P3-C: `operator_forbidden` stays as a second guard behind `READER`. Scripted
model, no network, no cost."""

from __future__ import annotations

import argparse
import json
import sqlite3

import anyio
import pytest
from mcp import Client
from pydantic import SecretStr

from merchant_assistant import mcp_server
from merchant_assistant.api import v1
from merchant_assistant.api.identity import Identity, Principal
from merchant_assistant.cli import cmd_mcp
from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import seed
from merchant_assistant.testing import merchant_headers, token_headers


def audit_rows(settings) -> list[dict]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM audit_events ORDER BY id")]
    finally:
        conn.close()


# --- P3-A: the MCP command wires `authorize` ------------------------------------------------------------------------


def test_mcp_command_checks_the_token_again_on_every_call(settings, monkeypatch):
    """The server `cmd_mcp` builds refuses, with `INVALID_TOKEN` and an audit row, a call made after its token was
    revoked (the existing test builds the server by hand; this one goes through the command)."""
    conn = connect(settings.db_path)
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    issuer = Identity(settings)
    token = issuer.issue(Principal.merchant("cliente1988"), "merchant-assistant-cli")["access_token"]
    settings.merchant_assistant_token = SecretStr(token)
    served = []
    monkeypatch.setattr(mcp_server, "serve_stdio", served.append)  # no stdio: the test talks to the server in memory
    assert cmd_mcp(settings, argparse.Namespace()) == 0
    [server] = served

    async def call():
        async with Client(server) as client:
            return await client.call_tool("get_device_status", {})

    assert anyio.run(call).is_error is False
    issuer.revoke(conn, issuer.decode(token))
    refused = anyio.run(call)
    assert refused.is_error and json.loads(refused.content[0].text)["error"]["code"] == "INVALID_TOKEN"
    assert [(r["tool"], r["outcome"], r["principal_id"]) for r in audit_rows(settings)] == [
        ("get_device_status", "ok", "merchant:cliente1988"),
        ("get_device_status", "invalid_token", "merchant:cliente1988"),
    ]
    conn.close()


def test_mcp_command_refuses_to_start_without_a_valid_merchant_token(settings, capsys):
    connect(settings.db_path).close()
    assert cmd_mcp(settings, argparse.Namespace()) == 2  # no token at all
    operator = Identity(settings).issue(Principal.operator("op_ana"), "merchant-assistant-cli")["access_token"]
    settings.merchant_assistant_token = SecretStr(operator)
    assert cmd_mcp(settings, argparse.Namespace()) == 2  # an operator has no merchant of its own
    assert capsys.readouterr().err.count("mcp:") == 2


# --- P3-B: the request limit on tool calls is audited -----------------------------------------------------------------


def test_tool_call_refused_by_the_request_limit_is_audited_with_the_principal(offline, settings):
    settings.max_tool_calls = 1  # the Escalation runs two bootstrap tools through the host: the second is refused
    client, orchestrator, _ = offline()
    response = client.post(
        "/messages", json={"message": "Quero falar com um atendente"}, headers=merchant_headers(client)
    )
    assert response.status_code == 200 and response.json()["status"] == "handoff"
    calls = [r for r in audit_rows(settings) if r["tool"] != "handoff_case.create"]
    refused = [r for r in calls if r["outcome"] == "limit_reached"]
    assert len(refused) == 1
    assert refused[0]["principal_id"] == "merchant:cliente1988" and refused[0]["scope"] == "support:read"
    assert refused[0]["customer_id"] == "cliente1988"
    trace = orchestrator.trace(response.json()["request_id"])
    assert trace["tool_calls"] == 1  # the trace counts the calls that ran; the audit also keeps the refusal
    assert len(calls) == trace["tool_calls"] + len(refused) and sum(r["outcome"] == "ok" for r in calls) == 1


# --- P3-C: `operator_forbidden` is a second guard behind READER -------------------------------------------------------


@pytest.mark.parametrize("role,name", [("operator", "op_ana"), ("service", "ticketing")])
@pytest.mark.parametrize(
    "path,body",
    [
        (
            "/v1/messages",
            {"message": "Olá", "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm"},
        ),
        (
            "/v1/router/compare",
            {"message": "Olá", "profile_id": "reference", "profile_version": 1, "selected_mechanism": "llm"},
        ),
    ],
)
def test_operator_and_service_stay_out_of_the_merchant_routes_even_if_reader_roles_widen(
    offline, monkeypatch, role, name, path, body
):
    """`READER` already refuses both roles, which makes `operator_forbidden` redundant today. It stays on purpose:
    were `READER_ROLES` ever widened by mistake, these routes would still refuse them (403, no model call)."""
    client, _, llm = offline()
    monkeypatch.setattr(v1, "READER_ROLES", (*v1.READER_ROLES, role))
    headers = token_headers(client, Principal.of(role, name))
    refused = client.post(path, json=body, headers=headers)
    assert refused.status_code == 403 and refused.json()["error"]["code"] == "insufficient_scope"
    assert refused.json()["error"]["message"] == v1.OPERATOR_FORBIDDEN
    assert llm.calls == []
