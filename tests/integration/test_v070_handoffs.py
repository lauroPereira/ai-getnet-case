"""v0.7.0 task 64: operator queue (RF-80, RF-81, RF-83; spec D6, D7, D9, D10, D14). Escalation opens the case in the
queue; claim and the approve/reply/reject actions are idempotent through one service shared by the API and the CLI,
with real threads over SQLite for the double-resume race. Scripted model, no network, no cost."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import threading

import pytest
from pydantic import SecretStr

from merchant_assistant import handoffs
from merchant_assistant.api.identity import Principal
from merchant_assistant.data.db import connect
from merchant_assistant.testing import merchant_headers, token_headers

HUMAN = "Quero falar com um atendente"


def operator(client, name="op_ana"):
    return token_headers(client, Principal.operator(name))


def open_case(client) -> dict:
    """A merchant asks for a human through POST /messages; returns the response and the queued case."""
    response = client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client))
    assert response.status_code == 200 and response.json()["status"] == "handoff"
    body = response.json()
    cases = client.get("/v1/handoffs", headers=operator(client)).json()["cases"]
    case = next(c for c in cases if c["protocol"] == body["handoff"]["protocol"])
    return {"message": body, "case": case}


def act(client, case_id, headers, action="approve", key="key-0000001", text=None):
    body = {"action": action, "idempotency_key": key} | ({"text": text} if text is not None else {})
    return client.post(f"/v1/handoffs/{case_id}/actions", headers=headers, json=body)


def test_escalated_case_enters_the_queue_open_with_protocol_summary_and_draft(offline, settings):
    client, _, _ = offline()
    opened = open_case(client)
    message, case = opened["message"], opened["case"]
    assert re.fullmatch(r"HO-\d{8}-[0-9A-F]{6}", message["handoff"]["protocol"])  # D7
    assert set(message["handoff"]) == {"protocol", "reason"}  # `simulated` left the public payload
    assert case["queue_state"] == "open" and case["claimed_by"] is None and case["summary"]
    assert case["channel"] == "api" and case["customer_id"] == "cliente1988"
    detail = client.get(f"/v1/handoffs/{case['case_id']}", headers=operator(client)).json()
    assert detail["draft_reply"] and detail["pending_question"] and detail["language"] == "pt"
    assert detail["thread_id"] == message["request_id"]  # D6
    assert [t["role"] for t in detail["transcript"]] == ["merchant", "assistant"]
    assert detail["events"] == [] and detail["deliveries"] == []
    assert detail["case_state"] == "handoff"
    payload = sqlite3.connect(settings.db_path).execute("SELECT payload FROM handoff_cases").fetchone()[0]
    assert "simulated" not in json.loads(payload)
    assert client.get("/v1/handoffs?state=open", headers=operator(client)).json()["cases"]
    assert client.get("/v1/handoffs?state=closed", headers=operator(client)).json()["cases"] == []
    assert client.get("/v1/handoffs?state=bogus", headers=operator(client)).status_code == 422


def test_merchant_admin_and_anonymous_cannot_use_the_queue(offline, settings):
    client, _, llm = offline()
    case_id = open_case(client)["case"]["case_id"]
    calls = len(llm.calls)
    for headers in (merchant_headers(client), token_headers(client, Principal.of("admin", "default", "cliente1988"))):
        for method, path in (
            ("get", "/v1/handoffs"),
            ("get", f"/v1/handoffs/{case_id}"),
            ("post", f"/v1/handoffs/{case_id}/claim"),
        ):
            response = getattr(client, method)(path, headers=headers)
            assert response.status_code == 403 and response.json()["error"]["code"] == "insufficient_scope", path
        assert act(client, case_id, headers).status_code == 403
    assert client.get("/v1/handoffs").status_code == 401
    assert len(llm.calls) == calls
    detail = client.get(f"/v1/handoffs/{case_id}", headers=operator(client)).json()
    assert detail["queue_state"] == "open" and detail["events"] == []


def test_claim_is_idempotent_and_conflicts_with_another_operator(offline):
    client, _, _ = offline()
    case_id = open_case(client)["case"]["case_id"]
    ana, bruno = operator(client, "op_ana"), operator(client, "op_bruno")
    first = client.post(f"/v1/handoffs/{case_id}/claim", headers=ana)
    assert first.status_code == 200 and first.json()["queue_state"] == "claimed"
    assert first.json()["claimed_by"] == "op_ana" and first.json()["replayed"] is False
    again = client.post(f"/v1/handoffs/{case_id}/claim", headers=ana)
    assert again.status_code == 200 and again.json()["replayed"] is True
    for response in (client.post(f"/v1/handoffs/{case_id}/claim", headers=bruno), act(client, case_id, bruno)):
        assert response.status_code == 409 and response.json()["error"]["code"] == "claimed_by_other"
    events = client.get(f"/v1/handoffs/{case_id}", headers=ana).json()["events"]
    assert [e["action"] for e in events] == ["claim"]
    assert client.post("/v1/handoffs/hc_missing/claim", headers=ana).status_code == 404


def test_action_is_idempotent_and_a_second_resume_is_refused(offline, settings):
    client, orchestrator, _ = offline()
    resumed = []
    orchestrator.resume_handoff = lambda case, record: resumed.append((case["case_id"], record["action"]))
    case_id = open_case(client)["case"]["case_id"]
    ana = operator(client)
    first = act(client, case_id, ana, "reply", "key-reply-01", "Your payout was sent today.")
    assert first.status_code == 200
    record = first.json()
    assert record["replayed"] is False and record["queue_state"] == "answered" and record["action"] == "reply"
    replay = act(client, case_id, ana, "reply", "key-reply-01", "Your payout was sent today.")
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    assert replay.json()["event_id"] == record["event_id"]
    second = act(client, case_id, ana, "approve", "key-other-02")
    assert second.status_code == 409 and second.json()["error"]["code"] == "already_resumed"
    assert resumed == [(case_id, "reply")]  # one resume, never for a replay or a refusal
    detail = client.get(f"/v1/handoffs/{case_id}", headers=ana).json()
    assert [e["action"] for e in detail["events"]] == ["claim", "reply"]  # D9: implicit claim
    assert detail["claimed_by"] == "op_ana" and detail["resume_count"] == 1 and detail["answered_at"]
    other_case = open_case(client)["case"]["case_id"]
    reused = act(client, other_case, ana, "reply", "key-reply-01", "x")
    assert reused.status_code == 409 and reused.json()["error"]["code"] == "idempotency_conflict"


def test_action_validation(offline):
    client, _, _ = offline()
    case_id = open_case(client)["case"]["case_id"]
    ana = operator(client)
    missing_text = act(client, case_id, ana, "reject", "key-reject-1")
    assert missing_text.status_code == 422 and missing_text.json()["error"]["code"] == "text_required"
    assert act(client, case_id, ana, "approve", "short").status_code == 422
    assert act(client, case_id, ana, "approve", "bad key with spaces").status_code == 422
    assert act(client, case_id, ana, "escalate", "key-escalate").status_code == 422
    rejected = act(client, case_id, ana, "reject", "key-reject-2", "Check the device status before replying.")
    assert rejected.status_code == 200 and rejected.json()["queue_state"] == "rejected"  # D14


def test_queue_calls_are_audited_with_the_operator(offline, settings):
    client, _, _ = offline()
    case_id = open_case(client)["case"]["case_id"]
    act(client, case_id, operator(client, "op_ana"), "approve", "key-audit-01")
    act(client, case_id, operator(client, "op_bruno"), "approve", "key-audit-02")
    rows = (
        sqlite3.connect(settings.db_path)
        .execute(
            "SELECT tool, outcome, principal_id, scope, customer_id FROM audit_events "
            "WHERE tool LIKE 'handoff.%' ORDER BY id"
        )
        .fetchall()
    )
    assert rows == [
        ("handoff.approve", "ok", "operator:op_ana", "handoff:operate", "cliente1988"),
        ("handoff.approve", "already_resumed", "operator:op_bruno", "handoff:operate", "cliente1988"),
    ]


def test_queue_routes_are_rate_limited(offline, settings, monkeypatch):
    from merchant_assistant.api import identity

    monkeypatch.setattr(identity, "utc_seconds", lambda: 1_800_000_010.0)  # fixed clock: one 60 s window
    settings.rate_limit_per_minute = 1
    client, _, _ = offline()
    case_id = open_case(client)["case"]["case_id"]
    ana = operator(client)
    assert client.post(f"/v1/handoffs/{case_id}/claim", headers=ana).status_code == 200
    limited = act(client, case_id, ana)
    assert limited.status_code == 429 and limited.json()["error"]["code"] == "rate_limited"
    detail = client.get(f"/v1/handoffs/{case_id}", headers=ana).json()  # reads are not limited
    assert detail["queue_state"] == "claimed"


# --- concurrency (CA-48) ------------------------------------------------------------------------------------------


def _race(settings, case_id: str, keys: list[str]) -> list[dict | handoffs.HandoffError]:
    barrier = threading.Barrier(len(keys))
    results: list = [None] * len(keys)

    def worker(index: int, key: str) -> None:
        conn = connect(settings.db_path)
        try:
            barrier.wait()
            results[index] = handoffs.act(conn, case_id, "op_ana", "approve", None, key, actor="operator:op_ana")
        except handoffs.HandoffError as exc:
            results[index] = exc
        finally:
            conn.close()

    threads = [threading.Thread(target=worker, args=(i, key)) for i, key in enumerate(keys)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


@pytest.mark.parametrize("round_", range(3))
def test_concurrent_actions_with_different_keys_resume_once(offline, settings, round_):
    client, _, _ = offline()
    case_id = open_case(client)["case"]["case_id"]
    results = _race(settings, case_id, [f"race-a-{round_}-key", f"race-b-{round_}-key", f"race-c-{round_}-key"])
    records = [r for r in results if isinstance(r, dict)]
    errors = [r for r in results if isinstance(r, handoffs.HandoffError)]
    assert len(records) == 1 and records[0]["replayed"] is False
    assert len(errors) == 2 and {e.code for e in errors} == {"already_resumed"}
    conn = connect(settings.db_path)
    assert conn.execute("SELECT resume_count FROM handoff_cases WHERE case_id=?", (case_id,)).fetchone()[0] == 1
    actions = conn.execute("SELECT COUNT(*) FROM handoff_events WHERE case_id=? AND action='approve'", (case_id,))
    assert actions.fetchone()[0] == 1


def test_concurrent_actions_with_the_same_key_return_the_same_record(offline, settings):
    client, _, _ = offline()
    case_id = open_case(client)["case"]["case_id"]
    results = _race(settings, case_id, ["same-key-0001"] * 3)
    assert all(isinstance(r, dict) for r in results)
    assert len({r["event_id"] for r in results}) == 1
    assert sorted(r["replayed"] for r in results) == [False, True, True]


# --- service: close -----------------------------------------------------------------------------------------------


def test_close_is_idempotent_and_ends_the_queue(offline, settings):
    client, _, _ = offline()
    case_id = open_case(client)["case"]["case_id"]
    conn = connect(settings.db_path)
    closed = handoffs.close(conn, case_id, "op_ana", actor="service:ticketing", on_behalf_of="operator:op_ana")
    assert closed["queue_state"] == "closed" and closed["replayed"] is False
    assert handoffs.close(conn, case_id, "op_ana", actor="operator:op_ana")["replayed"] is True
    with pytest.raises(handoffs.HandoffError) as refused:
        handoffs.act(conn, case_id, "op_ana", "approve", None, "after-close-1", actor="operator:op_ana")
    assert refused.value.code == "case_closed"
    with pytest.raises(handoffs.HandoffError) as other:
        handoffs.claim(conn, case_id, "op_bruno", actor="operator:op_bruno")
    assert other.value.code == "case_closed"
    row = conn.execute(
        "SELECT principal_id, on_behalf_of FROM audit_events WHERE tool='handoff.close' ORDER BY id"
    ).fetchone()
    assert tuple(row) == ("service:ticketing", "operator:op_ana")


# --- CLI ----------------------------------------------------------------------------------------------------------


def test_cli_operator_uses_the_same_service_and_the_token_operator(offline, settings, capsys, monkeypatch):
    from merchant_assistant import cli
    from merchant_assistant.cli import cmd_operator

    client, orchestrator, _ = offline()
    monkeypatch.setattr(cli, "operator_orchestrator", lambda _settings: orchestrator)
    monkeypatch.setattr(orchestrator, "close", lambda: None)  # the test client keeps using it
    case_id = open_case(client)["case"]["case_id"]
    token = client.app.state.identity.issue(Principal.operator("op_bruno"), "merchant-assistant-cli")["access_token"]
    settings.merchant_assistant_token = SecretStr(token)
    assert cmd_operator(settings, argparse.Namespace(operator_command="list", state="open")) == 0
    assert case_id in capsys.readouterr().out
    assert cmd_operator(settings, argparse.Namespace(operator_command="show", case_id=case_id)) == 0
    assert json.loads(capsys.readouterr().out)["case_id"] == case_id
    args = argparse.Namespace(
        operator_command="act", case_id=case_id, action="reply", text="Done.", idempotency_key="cli-key-0001"
    )
    assert cmd_operator(settings, args) == 0
    record = json.loads(capsys.readouterr().out)
    assert (record["operator_id"], record["queue_state"]) == ("op_bruno", "answered")
    assert cmd_operator(settings, args) == 0 and json.loads(capsys.readouterr().out)["replayed"] is True
    api = client.get(f"/v1/handoffs/{case_id}", headers=operator(client)).json()
    assert api["claimed_by"] == "op_bruno"  # the API sees what the CLI did
    settings.merchant_assistant_token = SecretStr(
        client.app.state.identity.issue(Principal.merchant("cliente1988"), "cli")["access_token"]
    )
    with pytest.raises(SystemExit):
        cmd_operator(settings, argparse.Namespace(operator_command="list", state=None))
