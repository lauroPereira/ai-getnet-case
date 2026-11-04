"""v0.7.0 task 64, round 2 (review of 2026-11-03; spec D19 widened, D22, D23): no simulation text for the merchant or
the operator, the CLI uses the single resume point, queue reads and gate refusals are audited, a reused key with
another text is a conflict, token attempts are limited per address across accounts, and the service validates the
idempotency key on its own. Scripted model, no network, no cost."""

from __future__ import annotations

import argparse
import json
import sqlite3

import pytest
from pydantic import SecretStr

from merchant_assistant import handoffs
from merchant_assistant.api import identity
from merchant_assistant.api.identity import Principal
from merchant_assistant.data.db import connect
from merchant_assistant.testing import merchant_headers, token_headers

HUMAN = "Quero falar com um atendente humano, por favor"


def operator(client, name="op_ana"):
    return token_headers(client, Principal.operator(name))


def hand_off(client) -> dict:
    message = client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client)).json()
    assert message["status"] == "handoff"
    case = client.get("/v1/handoffs", headers=operator(client)).json()["cases"][0]
    return {"message": message, "case": case}


def audit(settings, tool_prefix="handoff."):
    rows = sqlite3.connect(settings.db_path).execute(
        "SELECT tool, outcome, principal_id, scope, resource_id FROM audit_events WHERE tool LIKE ? ORDER BY id",
        (f"{tool_prefix}%",),
    )
    return [tuple(r) for r in rows]


def test_no_simulation_text_for_the_merchant_or_the_operator(offline):
    client, _, _ = offline()
    opened = hand_off(client)
    detail = client.get(f"/v1/handoffs/{opened['case']['case_id']}", headers=operator(client)).json()
    texts = [opened["message"]["answer"], *(t["text"] for t in detail["transcript"])]
    for text in texts:
        assert "simula" not in text.lower(), text
    payload = json.dumps(detail, ensure_ascii=False).lower()
    assert '"simulated"' not in payload


def test_cli_act_uses_the_single_resume_point(offline, settings, capsys, monkeypatch):
    from merchant_assistant import cli

    client, orchestrator, _ = offline()
    case = hand_off(client)["case"]
    calls = []
    real = orchestrator.resume_handoff
    monkeypatch.setattr(orchestrator, "resume_handoff", lambda c, r: calls.append(r["event_id"]) or real(c, r))
    monkeypatch.setattr(orchestrator, "close", lambda: None)
    monkeypatch.setattr(cli, "operator_orchestrator", lambda _settings: orchestrator)
    token = client.app.state.identity.issue(Principal.operator("op_ana"), "merchant-assistant-cli")["access_token"]
    settings.merchant_assistant_token = SecretStr(token)
    args = argparse.Namespace(
        operator_command="act", case_id=case["case_id"], action="reply", text="Resolvido.", idempotency_key="cli-r2-001"
    )
    assert cli.cmd_operator(settings, args) == 0
    record = json.loads(capsys.readouterr().out)
    assert len(calls) == 1 and record["resume_status"] == "done"
    turns = client.get(f"/v1/conversations/{case['conversation_id']}", headers=merchant_headers(client)).json()
    assert turns["messages"][-1]["via"] == "operator" and turns["messages"][-1]["text"] == "Resolvido."


def test_queue_reads_and_gate_refusals_are_audited(offline, settings):
    client, _, _ = offline()
    case_id = hand_off(client)["case"]["case_id"]  # one audited list read by op_ana
    client.get(f"/v1/handoffs/{case_id}", headers=operator(client))
    client.get("/v1/handoffs/hc_missing", headers=operator(client))
    merchant = merchant_headers(client)
    client.get("/v1/handoffs", headers=merchant)
    client.get(f"/v1/handoffs/{case_id}", headers=merchant)
    client.post(f"/v1/handoffs/{case_id}/claim", headers=merchant)
    client.post(
        f"/v1/handoffs/{case_id}/actions",
        headers=merchant,
        json={"action": "approve", "idempotency_key": "merchant-try-1"},
    )
    assert audit(settings) == [
        ("handoff.list", "ok", "operator:op_ana", "handoff:operate", None),
        ("handoff.read", "ok", "operator:op_ana", "handoff:operate", case_id),
        ("handoff.read", "case_not_found", "operator:op_ana", "handoff:operate", "hc_missing"),
        ("handoff.list", "insufficient_scope", "merchant:cliente1988", "handoff:operate", None),
        ("handoff.read", "insufficient_scope", "merchant:cliente1988", "handoff:operate", case_id),
        ("handoff.claim", "insufficient_scope", "merchant:cliente1988", "handoff:operate", case_id),
        ("handoff.approve", "insufficient_scope", "merchant:cliente1988", "handoff:operate", case_id),
    ]


def test_same_key_with_another_text_is_a_conflict(offline, settings):
    client, _, _ = offline()
    case_id = hand_off(client)["case"]["case_id"]
    body = {"action": "reply", "text": "Primeiro texto.", "idempotency_key": "key-d22-0001"}
    url = f"/v1/handoffs/{case_id}/actions"
    assert client.post(url, headers=operator(client), json=body).status_code == 200
    changed = client.post(url, headers=operator(client), json=body | {"text": "Outro texto."})
    assert changed.status_code == 409 and changed.json()["error"]["code"] == "idempotency_conflict"
    same = client.post(url, headers=operator(client), json=body)
    assert same.status_code == 200 and same.json()["replayed"] is True and same.json()["text"] == "Primeiro texto."
    texts = [t["text"] for t in client.get(f"/v1/handoffs/{case_id}", headers=operator(client)).json()["events"]]
    assert texts.count("Primeiro texto.") == 1 and "Outro texto." not in texts


def test_token_attempts_are_limited_per_address_across_accounts(offline, settings, monkeypatch):
    monkeypatch.setattr(identity, "utc_seconds", lambda: 1_800_000_010.0)
    settings.auth_attempts_per_ip_per_minute = 3
    client, _, _ = offline()
    users = ["cliente1988", "cliente_demo_002", "op_ana"]
    for user in users:  # one attempt per account: the per-account limit is never reached
        response = client.post("/v1/auth/token", data={"grant_type": "password", "username": user, "password": "x"})
        assert response.status_code == 400
    sprayed = client.post("/v1/auth/token", data={"grant_type": "password", "username": "op_bruno", "password": "x"})
    assert sprayed.status_code == 429 and sprayed.json()["error"] == "rate_limited"
    assert int(sprayed.headers["retry-after"]) >= 1


@pytest.mark.parametrize("key", ["", "short-7", "a" * 81, "has space1", "acentuação1", "semi;colon1"])
def test_service_validates_the_idempotency_key(offline, settings, key):
    client, _, _ = offline()
    case_id = hand_off(client)["case"]["case_id"]
    conn = connect(settings.db_path)
    with pytest.raises(handoffs.HandoffError) as refused:
        handoffs.act(conn, case_id, "op_ana", "approve", None, key, actor="operator:op_ana")
    assert refused.value.code == "invalid_idempotency_key"
    assert conn.execute("SELECT COUNT(*) FROM handoff_events").fetchone()[0] == 0


@pytest.mark.parametrize("key", ["eight-ch", "a" * 80, "UPPER_lower-123"])
def test_service_accepts_keys_at_the_limits(offline, settings, key):
    client, _, _ = offline()
    case_id = hand_off(client)["case"]["case_id"]
    record = handoffs.act(connect(settings.db_path), case_id, "op_ana", "approve", None, key, actor="operator:op_ana")
    assert record["idempotency_key"] == key
