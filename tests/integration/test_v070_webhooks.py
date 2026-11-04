"""v0.7.0 task 66 (CA-47, CA-48): signed webhooks between the assistant, the ticketing and the merchant.

Fake receivers in process (httpx.MockTransport); the ticketing events are signed here with the contract's scheme and
sent with a service token. Scripted model, no network, no cost."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant import handoffs
from merchant_assistant.api import integrations
from merchant_assistant.api.identity import Principal
from merchant_assistant.api.webhooks import Webhooks, signature, verify_signature
from merchant_assistant.mocks.service import create_mocks_app
from merchant_assistant.orchestration import graph
from merchant_assistant.testing import TEST_TICKETING_SECRET, AppTransport, merchant_headers, token_headers

TICKETING_URL = "http://ticketing.test/webhooks/assistant"
MERCHANT_URL = "http://merchant.test/merchant/events"
TICKETING_SECRET = "test-ticketing-webhook-secret"
ASSISTANT_SECRET = "test-assistant-webhook-secret"
CONVERSATION_SECRET = "test-conversation-webhook-secret"
CARD = "4111 1111 1111 1111"
HUMAN = "Quero falar com um atendente"
EVENTS_PATH = "/v1/integrations/ticketing/events"


class Receivers:
    """Fake ticketing and merchant endpoints: records every request and answers with a programmable status."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.status: dict[str, int] = {}
        self.down: set[str] = set()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        self.requests.append(request)
        if host in self.down:
            raise httpx.ConnectError("receiver down", request=request)
        return httpx.Response(self.status.get(host, 200), json={"status": "received"})

    def events(self, host: str | None = None) -> list[dict]:
        return [json.loads(r.content) for r in self.requests if host in (None, r.url.host)]


@pytest.fixture
def wired(offline, settings):
    """(client, orchestrator, receivers, waits): the assistant with both webhook targets on fake receivers."""

    def make(**kwargs):
        settings.ticketing_webhook_url = TICKETING_URL
        settings.ticketing_webhook_secret = SecretStr(TICKETING_SECRET)
        settings.conversation_webhook_url = MERCHANT_URL
        settings.conversation_webhook_secret = SecretStr(CONVERSATION_SECRET)
        settings.assistant_webhook_secret = SecretStr(ASSISTANT_SECRET)
        client, orchestrator, _ = offline(**kwargs)
        receivers, waits = Receivers(), []
        client.app.state.webhooks = Webhooks(settings, transport=httpx.MockTransport(receivers), sleep=waits.append)
        return client, orchestrator, receivers, waits

    return make


def hand_off(client, customer="cliente1988") -> dict:
    headers = merchant_headers(client, customer)
    first = client.post("/messages", json={"message": f"Meu cartão {CARD} foi recusado"}, headers=headers)
    assert first.status_code == 200, first.text
    body = {"message": HUMAN, "conversation_id": first.json()["conversation_id"]}
    response = client.post("/messages", json=body, headers=headers)
    assert response.status_code == 200 and response.json()["status"] == "handoff", response.text
    conn = sqlite3.connect(client.app.state.settings.db_path)
    conn.row_factory = sqlite3.Row
    case = conn.execute("SELECT * FROM handoff_cases WHERE thread_id=?", (response.json()["request_id"],)).fetchone()
    conn.close()
    client.app.state.webhooks.wait()
    return {"message": response.json(), "case_id": case["case_id"], "protocol": case["protocol"]}


def service(client) -> dict[str, str]:
    return token_headers(client, Principal.of("service", "ticketing"))


def signed(event_type: str, data: dict, *, secret=ASSISTANT_SECRET, event_id=None, skew=0) -> tuple[bytes, dict]:
    event = {"id": event_id or f"evt_{time.time_ns()}", "type": event_type, "created_at": "2026-11-03T12:00:00Z"}
    body = json.dumps(event | {"data": data}).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Id": event["id"],
        "X-Webhook-Event": event_type,
        "X-Signature": signature(secret, body, int(time.time()) + skew),  # skew: seconds away from now
    }
    return body, headers


def post_event(client, event_type, data, *, headers=None, **kwargs):
    body, signed_headers = signed(event_type, data, **kwargs)
    auth = service(client) if headers is None else headers
    return client.post(EVENTS_PATH, content=body, headers=signed_headers | auth)


def ticket(case_id, operator="op_ana", **extra) -> dict:
    return {"ticket_id": "tkt_000000000001", "case_id": case_id, "operator_id": operator} | extra


def rows(client, query, args=()):
    conn = sqlite3.connect(client.app.state.settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(query, args)]
    finally:
        conn.close()


def case_snapshot(client, case_id):
    case = rows(client, "SELECT * FROM handoff_cases WHERE case_id=?", (case_id,))[0]
    events = rows(client, "SELECT event_id FROM handoff_events WHERE case_id=?", (case_id,))
    return {k: case[k] for k in ("queue_state", "claimed_by", "resume_count", "closed_at", "ticket_id")}, len(events)


# --- outgoing: handoff.created --------------------------------------------------------------------------------------


def test_handoff_created_reaches_the_ticketing_signed_and_masked(wired):
    client, _, receivers, _ = wired()
    other = hand_off(client, "cliente_demo_002")  # another merchant's case must never leak into the first one's body
    receivers.requests.clear()
    opened = hand_off(client)
    [request] = receivers.requests
    assert request.url == TICKETING_URL
    assert request.headers["x-webhook-event"] == "handoff.created"
    assert verify_signature(TICKETING_SECRET, request.headers["x-signature"], request.content, time.time())
    assert not verify_signature(CONVERSATION_SECRET, request.headers["x-signature"], request.content, time.time())
    event = json.loads(request.content)
    assert request.headers["x-webhook-id"] == event["id"] and event["id"].startswith("evt_")
    data = event["data"]
    expected = {"case_id", "protocol", "conversation_id", "customer_id", "language", "reason", "summary"}
    assert expected | {"pending_question", "draft_reply", "transcript"} == set(data)
    assert data["case_id"] == opened["case_id"] and data["protocol"] == opened["protocol"]
    assert data["customer_id"] == "cliente1988" and data["draft_reply"]
    assert 0 < len(data["transcript"]) <= 10 and {"role", "text", "at"} == set(data["transcript"][0])
    text = request.content.decode()
    assert CARD not in text and "[card number removed]" in text  # masked body
    for secret in (TICKETING_SECRET, ASSISTANT_SECRET, CONVERSATION_SECRET, TEST_TICKETING_SECRET):
        assert secret not in text
    assert "Bearer" not in text and "eyJ" not in text  # no token
    assert "cliente_demo_002" not in text and other["case_id"] not in text and other["protocol"] not in text
    detail = client.get(
        f"/v1/handoffs/{opened['case_id']}", headers=token_headers(client, Principal.operator("op_ana"))
    )
    [delivery] = detail.json()["deliveries"]
    assert (delivery["event"], delivery["target"], delivery["attempt"], delivery["status"]) == (
        "handoff.created",
        "ticketing",
        1,
        "delivered",
    )
    assert delivery["event_id"] == event["id"] and delivery["response_code"] == 200


def test_turn_without_handoff_sends_nothing_and_empty_urls_send_nothing(wired, settings):
    client, _, receivers, _ = wired()
    reply = client.post("/messages", json={"message": "Olá"}, headers=merchant_headers(client))
    assert reply.status_code == 200 and reply.json()["status"] != "handoff"
    client.app.state.webhooks.wait()
    assert receivers.requests == []
    settings.ticketing_webhook_url = ""  # also what `KEY=` in .env means
    settings.conversation_webhook_url = None
    hand_off(client)
    assert receivers.requests == [] and rows(client, "SELECT * FROM webhook_deliveries") == []


# --- incoming events and the reply (CA-47) ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ["approve", "reply", "reject"])
def test_ticketing_events_resume_reply_and_close(wired, action):
    client, _, receivers, _ = wired()
    opened = hand_off(client)
    case_id = opened["case_id"]
    receivers.requests.clear()
    assigned = post_event(client, "ticket.assigned", ticket(case_id))
    assert assigned.status_code == 200, assigned.text
    assert assigned.json() == {"status": "accepted", "case_state": "handoff", "queue_state": "claimed"}
    text = {"approve": "", "reply": "Seu repasse cai amanhã.", "reject": "Verifique a maquininha."}[action]
    acted = post_event(client, "ticket.action", ticket(case_id, action=action, text=text, idempotency_key="tkt-key-01"))
    assert acted.status_code == 200, acted.text
    expected_queue = "rejected" if action == "reject" else "answered"
    assert acted.json()["status"] == "accepted" and acted.json()["queue_state"] == expected_queue
    assert acted.json()["case_state"] != "handoff"
    client.app.state.webhooks.wait()
    replied = {r.url.host: json.loads(r.content) for r in receivers.requests}
    assert set(replied) == {"ticketing.test", "merchant.test"}
    to_ticketing, to_merchant = replied["ticketing.test"], replied["merchant.test"]
    assert to_ticketing["id"] == to_merchant["id"] and to_ticketing["type"] == to_merchant["type"]  # one event
    assert to_ticketing["data"]["operator_id"] == "op_ana" and "operator_id" not in to_merchant["data"]  # D29
    assert {k: v for k, v in to_ticketing["data"].items() if k != "operator_id"} == to_merchant["data"]
    ticketing_request = next(r for r in receivers.requests if r.url.host == "ticketing.test")
    assert verify_signature(  # two bodies, each signed with the secret of its direction
        TICKETING_SECRET, ticketing_request.headers["x-signature"], ticketing_request.content, time.time()
    )
    assert b"op_ana" not in next(r for r in receivers.requests if r.url.host == "merchant.test").content
    merchant_request = next(r for r in receivers.requests if r.url.host == "merchant.test")
    assert verify_signature(
        CONVERSATION_SECRET, merchant_request.headers["x-signature"], merchant_request.content, time.time()
    )
    for request in receivers.requests:  # no secret, token or other merchant in the reply either
        raw = request.content.decode()
        assert all(s not in raw for s in (TICKETING_SECRET, ASSISTANT_SECRET, CONVERSATION_SECRET, "Bearer", "eyJ"))
        assert "cliente_demo_002" not in raw and CARD not in raw
    data = replied["ticketing.test"]["data"]
    assert replied["merchant.test"]["type"] == "conversation.replied"
    assert (data["case_id"], data["action"], data["operator_id"], data["via"]) == (
        case_id,
        action,
        "op_ana",
        "operator",
    )
    assert data["reply_text"] and data["request_id"].startswith("req_resume_") and data["delivered_at"]
    if action == "reply":
        assert text in data["reply_text"]
    conversation = client.get(
        f"/v1/conversations/{opened['message']['conversation_id']}", headers=merchant_headers(client)
    ).json()
    assert [d["status"] for d in conversation["webhook_deliveries"]] == ["delivered"]
    operator_turn = rows(client, "SELECT delivered_at FROM messages WHERE via='operator'")
    assert operator_turn == [{"delivered_at": None}]  # D24: the webhook does not mark the turn as delivered
    receivers.requests.clear()
    solved = post_event(client, "ticket.solved", ticket(case_id))
    assert solved.status_code == 200 and solved.json()["queue_state"] == "closed", solved.text
    client.app.state.webhooks.wait()
    [closed] = receivers.events()
    assert closed["type"] == "handoff.closed" and receivers.requests[0].url.host == "ticketing.test"
    assert closed["data"]["case_id"] == case_id and closed["data"]["closed_by"] == "op_ana"
    assert closed["data"]["closed_at"] and closed["data"]["protocol"] == opened["protocol"]
    assert case_snapshot(client, case_id)[0]["ticket_id"] == "tkt_000000000001"
    audit = rows(
        client,
        "SELECT tool, outcome, principal_id, on_behalf_of FROM audit_events "
        "WHERE resource_id=? AND tool LIKE 'handoff.%'",
        (case_id,),
    )
    acting = [a for a in audit if a["tool"] in ("handoff.claim", f"handoff.{action}", "handoff.close")]
    assert len(acting) == 3
    assert all(a["principal_id"] == "service:ticketing" and a["on_behalf_of"] == "operator:op_ana" for a in acting)


def test_case_detail_shows_deliveries_of_every_event(wired):
    client, _, _, _ = wired()
    opened = hand_off(client)
    post_event(
        client, "ticket.action", ticket(opened["case_id"], action="approve", text="", idempotency_key="tkt-key-02")
    )
    post_event(client, "ticket.solved", ticket(opened["case_id"]))
    client.app.state.webhooks.wait()
    detail = client.get(
        f"/v1/handoffs/{opened['case_id']}", headers=token_headers(client, Principal.operator("op_ana"))
    )
    seen = sorted((d["event"], d["target"]) for d in detail.json()["deliveries"])
    assert seen == [
        ("conversation.replied", "merchant"),
        ("conversation.replied", "ticketing"),
        ("handoff.closed", "ticketing"),
        ("handoff.created", "ticketing"),
    ]


# --- idempotency (CA-48) ------------------------------------------------------------------------------------------


def test_repeated_event_id_or_key_has_no_new_effect_and_a_second_resume_conflicts(wired):
    client, orchestrator, receivers, _ = wired()
    case_id = hand_off(client)["case_id"]
    calls = []
    original = orchestrator.resume_handoff
    orchestrator.resume_handoff = lambda case, record: calls.append(record) or original(case, record)
    data = ticket(case_id, action="reply", text="Pode ficar tranquilo.", idempotency_key="tkt-key-03")
    first = post_event(client, "ticket.action", data, event_id="evt_same_0001")
    assert first.status_code == 200 and first.json()["status"] == "accepted"
    before = case_snapshot(client, case_id)
    again = post_event(client, "ticket.action", data, event_id="evt_same_0001")
    assert again.status_code == 200 and again.json()["status"] == "replayed"
    same_key = post_event(client, "ticket.action", data, event_id="evt_other_0002")
    assert same_key.status_code == 200 and same_key.json()["status"] == "replayed"
    other_key = post_event(client, "ticket.action", data | {"idempotency_key": "tkt-key-04"})
    assert other_key.status_code == 409 and other_key.json()["error"]["code"] == "already_resumed"
    changed_text = post_event(client, "ticket.action", data | {"text": "Outro texto"})
    assert changed_text.status_code == 409 and changed_text.json()["error"]["code"] == "idempotency_conflict"
    assert case_snapshot(client, case_id) == before and len(calls) == 1
    client.app.state.webhooks.wait()
    assert len([e for e in receivers.events() if e["type"] == "conversation.replied"]) == 2  # one per receiver
    bruno = post_event(client, "ticket.assigned", ticket(case_id, "op_bruno"))
    assert bruno.status_code == 409 and bruno.json()["error"]["code"] == "claimed_by_other"


def test_failed_resume_is_503_and_the_ticketing_retry_of_the_same_event_resumes(wired):
    client, orchestrator, receivers, _ = wired()
    case_id = hand_off(client)["case_id"]
    original = orchestrator.resume_handoff

    def broken(case, record):
        raise RuntimeError("model down")

    orchestrator.resume_handoff = broken
    data = ticket(case_id, action="approve", text="", idempotency_key="tkt-key-05")
    failed = post_event(client, "ticket.action", data, event_id="evt_retry_0001")
    assert failed.status_code == 503 and failed.json()["error"]["code"] == "resume_failed"
    assert rows(client, "SELECT status_code FROM webhook_inbox WHERE event_id=?", ("evt_retry_0001",)) == [
        {"status_code": 0}
    ]
    changed = post_event(client, "ticket.action", data | {"case_id": "other"}, event_id="evt_retry_0001")
    assert changed.status_code == 503 and changed.json()["error"]["code"] == "resume_failed"
    client.app.state.webhooks.wait()
    assert [e for e in receivers.events() if e["type"] == "conversation.replied"] == []  # nothing was produced
    orchestrator.resume_handoff = original
    retried = post_event(client, "ticket.action", data, event_id="evt_retry_0001")  # the outbox repeats the event
    assert retried.status_code == 200 and retried.json()["queue_state"] == "answered", retried.text
    client.app.state.webhooks.wait()
    assert len([e for e in receivers.events() if e["type"] == "conversation.replied"]) == 2


def test_concurrent_same_event_id_for_different_cases_has_one_effect(wired, monkeypatch):
    client, _, _, _ = wired()
    cases = [hand_off(client, customer)["case_id"] for customer in ("cliente1988", "cliente_demo_002")]
    headers = service(client)
    entered, second_connected, release = Event(), Event(), Event()
    original_apply, original_db = integrations._apply, integrations._db
    calls = []

    def apply(*args):
        calls.append(args[2]["data"]["case_id"])
        entered.set()
        assert release.wait(10)
        return original_apply(*args)

    def db(request):
        conn = original_db(request)
        if entered.is_set():
            second_connected.set()
        return conn

    monkeypatch.setattr(integrations, "_apply", apply)
    monkeypatch.setattr(integrations, "_db", db)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(post_event, client, "ticket.assigned", ticket(cases[0]),
                            headers=headers, event_id="evt_concurrent")
        assert entered.wait(10)
        second = pool.submit(post_event, client, "ticket.assigned", ticket(cases[1]),
                             headers=headers, event_id="evt_concurrent")
        assert second_connected.wait(10)
        release.set()
        responses = [first.result(timeout=10), second.result(timeout=10)]
    assert [r.status_code for r in responses] == [200, 200]
    assert [r.json()["status"] for r in responses] == ["accepted", "replayed"]
    assert calls == [cases[0]]
    assert [case_snapshot(client, case)[0]["queue_state"] for case in cases] == ["claimed", "open"]
    assert len(rows(client, "SELECT * FROM webhook_inbox WHERE event_id='evt_concurrent'")) == 1
    audits = rows(client, "SELECT * FROM audit_events WHERE tool='handoff.claim' AND resource_id IN (?,?)", cases)
    assert len(audits) == 1


def test_interrupted_event_retries_only_its_original_case(wired, monkeypatch):
    client, _, _, _ = wired()
    cases = [hand_off(client, customer)["case_id"] for customer in ("cliente1988", "cliente_demo_002")]
    original = integrations._apply

    def interrupted(*args):
        original(*args)
        raise RuntimeError("interrupted after claim")

    monkeypatch.setattr(integrations, "_apply", interrupted)
    with pytest.raises(RuntimeError, match="interrupted after claim"):
        post_event(client, "ticket.assigned", ticket(cases[0]), event_id="evt_interrupted")
    monkeypatch.setattr(integrations, "_apply", original)
    changed = post_event(client, "ticket.assigned", ticket(cases[1]), event_id="evt_interrupted")
    assert changed.status_code == 503 and changed.json()["error"]["code"] == "resume_failed"
    retried = post_event(client, "ticket.assigned", ticket(cases[0]), event_id="evt_interrupted")
    assert retried.status_code == 200 and retried.json()["status"] == "replayed"
    assert [case_snapshot(client, case)[0]["queue_state"] for case in cases] == ["claimed", "open"]


@pytest.mark.parametrize("operator_name,code,status", [("op_ghost", "unknown_operator", 422),
                                                        ("op_bruno", "claimed_by_other", 409)])
def test_repeated_final_refusal_returns_original_error_without_new_effect_or_audit(wired, operator_name, code, status):
    client, _, _, _ = wired()
    case_id = hand_off(client)["case_id"]
    if status == 409:
        assert post_event(client, "ticket.assigned", ticket(case_id)).status_code == 200
    before = case_snapshot(client, case_id)
    rejected = post_event(client, "ticket.assigned", ticket(case_id, operator_name), event_id="evt_refused")
    assert rejected.status_code == status and rejected.json()["error"]["code"] == code
    audits = rows(client, "SELECT * FROM audit_events WHERE resource_id=?", (case_id,))
    duplicate = post_event(client, "ticket.assigned", ticket(case_id), event_id="evt_refused")
    assert duplicate.status_code == status and duplicate.json() == rejected.json()
    assert case_snapshot(client, case_id) == before
    assert rows(client, "SELECT * FROM audit_events WHERE resource_id=?", (case_id,)) == audits


def test_event_lock_paths_are_bounded_and_cannot_escape_runtime(tmp_path):
    paths = {integrations._lock_path(tmp_path / "db.sqlite3", f"../../event-{n}") for n in range(3000)}
    assert len(paths) <= integrations.LOCK_STRIPES
    assert all(path.startswith(str(tmp_path / "db.sqlite3.webhook-lock-")) for path in paths)


def test_same_action_key_in_distinct_events_does_not_resume_concurrently(wired, monkeypatch):
    client, orchestrator, _, _ = wired()
    case_id = hand_off(client)["case_id"]
    headers = service(client)
    entered, second_connected, release = Event(), Event(), Event()
    calls = []
    original = orchestrator.resume_handoff

    def resume(case, record):
        calls.append(record["event_id"])
        entered.set()
        assert release.wait(10)
        return original(case, record)

    orchestrator.resume_handoff = resume
    original_db = integrations._db

    def db(request):
        conn = original_db(request)
        if entered.is_set():
            second_connected.set()
        return conn

    monkeypatch.setattr(integrations, "_db", db)
    data = ticket(case_id, action="approve", text="", idempotency_key="same-action-key")
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(post_event, client, "ticket.action", data, headers=headers, event_id="evt_action_1")
        try:
            assert entered.wait(10)
            second = pool.submit(post_event, client, "ticket.action", data, headers=headers, event_id="evt_action_2")
            assert second_connected.wait(10)
        finally:
            release.set()
        responses = [first.result(timeout=10), second.result(timeout=10)]
    assert [response.status_code for response in responses] == [200, 200]
    assert len(calls) == 1


def test_distinct_event_ids_do_not_wait_for_each_other(wired, monkeypatch):
    client, _, _, _ = wired()
    cases = [hand_off(client, customer)["case_id"] for customer in ("cliente1988", "cliente_demo_002")]
    headers = service(client)
    entered, release = Event(), Event()
    original = integrations._apply

    def apply(*args):
        if args[2]["id"] == "evt_slow":
            entered.set()
            assert release.wait(10)
        return original(*args)

    monkeypatch.setattr(integrations, "_apply", apply)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            post_event, client, "ticket.assigned", ticket(cases[0]), headers=headers, event_id="evt_slow"
        )
        try:
            assert entered.wait(10)
            second = pool.submit(post_event, client, "ticket.assigned", ticket(cases[1]),
                                 headers=headers, event_id="evt_fast")
            assert second.result(timeout=4).json()["status"] == "accepted"
        finally:
            release.set()
        assert first.result(timeout=10).json()["status"] == "accepted"


def test_interrupted_process_releases_event_lock_and_reservation_can_resume(wired):
    client, _, _, _ = wired()
    case_id = hand_off(client)["case_id"]
    body, headers = signed("ticket.assigned", ticket(case_id), event_id="evt_crashed")
    event = json.loads(body)
    conn = sqlite3.connect(client.app.state.settings.db_path, isolation_level=None)
    try:
        integrations._reserve(conn, event)
    finally:
        conn.close()
    lock_path = integrations._lock_path(client.app.state.settings.db_path, event["id"])
    script = (
        "import sqlite3, sys; "
        "conn = sqlite3.connect(sys.argv[1], isolation_level=None); "
        "conn.execute('BEGIN IMMEDIATE'); print('locked', flush=True); sys.stdin.read()"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", script, lock_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    try:
        assert process.stdout.readline().strip() == "locked"
        process.kill()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        process.stdin.close()
        process.stdout.close()
    response = client.post(EVENTS_PATH, content=body, headers=headers | service(client))
    assert response.status_code == 200 and response.json()["status"] == "accepted"
    assert case_snapshot(client, case_id)[0]["queue_state"] == "claimed"


def test_closed_intent_survives_process_death_before_emit(wired):
    client, _, receivers, _ = wired()
    case_id = hand_off(client)["case_id"]
    assert post_event(client, "ticket.assigned", ticket(case_id)).status_code == 200
    body, headers = signed("ticket.solved", ticket(case_id), event_id="evt_crashed_close")
    conn = sqlite3.connect(client.app.state.settings.db_path, isolation_level=None)
    try:
        integrations._reserve(conn, json.loads(body))
    finally:
        conn.close()
    script = (
        "import os, sys; from merchant_assistant.data.db import connect; "
        "from merchant_assistant.handoffs import close; conn=connect(sys.argv[1]); "
        "close(conn,sys.argv[2],'op_ana',actor='service:ticketing',on_behalf_of='operator:op_ana'); os._exit(23)"
    )
    process = subprocess.run([sys.executable, "-c", script, str(client.app.state.settings.db_path), case_id],
                             check=False, timeout=20)
    assert process.returncode == 23
    assert case_snapshot(client, case_id)[0]["queue_state"] == "closed"
    receivers.requests.clear()
    client.app.state.webhooks.recover_pending_intents()
    client.app.state.webhooks.wait()
    [closed] = receivers.events()
    assert closed["type"] == "handoff.closed" and closed["data"]["case_id"] == case_id
    retried = client.post(EVENTS_PATH, content=body, headers=headers | service(client))
    assert retried.status_code == 200 and retried.json()["status"] == "replayed"
    client.app.state.webhooks.wait()
    assert [e["id"] for e in receivers.events()] == [closed["id"]]


def test_closed_delivery_retries_with_same_id_after_ack_is_lost(wired, monkeypatch):
    client, _, receivers, _ = wired()
    case_id = hand_off(client)["case_id"]
    assert post_event(client, "ticket.assigned", ticket(case_id)).status_code == 200
    webhooks = client.app.state.webhooks
    original = webhooks._record
    failed = []

    def lose_ack(event, *args):
        if event["type"] == "handoff.closed" and not failed:
            failed.append(event["id"])
            raise RuntimeError("delivery acknowledgement lost")
        return original(event, *args)

    monkeypatch.setattr(webhooks, "_record", lose_ack)
    receivers.requests.clear()
    assert post_event(client, "ticket.solved", ticket(case_id)).status_code == 200
    assert webhooks.wait()
    webhooks.recover_pending_intents()
    assert webhooks.wait()
    events = receivers.events()
    assert len(events) == 2 and events[0] == events[1]
    assert len({event["id"] for event in events}) == 1


def _child_settings_script() -> str:
    # both receivers configured: a destination without a URL gets no intention
    return (
        "import os, sys; from pathlib import Path; from pydantic import SecretStr; "
        "from merchant_assistant.config import Settings; "
        "from merchant_assistant.testing import offline_orchestrator, passwords_setting, TEST_USER_PASSWORDS, "
        "TEST_TICKETING_SECRET; "
        "settings=Settings(_env_file=None,runtime_dir=Path(sys.argv[1]),jwt_private_key_path=Path(sys.argv[2]),"
        "demo_mode=True,budget_limit_usd=1.0,qdrant_url=':memory:',retrieval_min_score=0.05,"
        "ticketing_webhook_url='http://ticketing.test/webhooks/assistant',"
        "conversation_webhook_url='http://merchant.test/merchant/events',"
        "demo_user_passwords=SecretStr(passwords_setting(TEST_USER_PASSWORDS)),"
        "ticketing_client_secret=SecretStr(TEST_TICKETING_SECRET),password_hash_iterations=1000); "
        "orchestrator,_=offline_orchestrator(settings); "
    )


def test_created_outbox_survives_process_death_before_delivery(wired, settings):
    client, _, receivers, _ = wired()
    script = _child_settings_script() + (
        "from fastapi.testclient import TestClient; from merchant_assistant.api.app import create_app; "
        "from merchant_assistant.testing import merchant_headers; app=create_app(orchestrator,settings); "
        "app.state.webhooks.handoff_created_for=lambda *_: os._exit(71); client=TestClient(app); "
        "client.post('/messages',json={'message':'Quero falar com um atendente'},headers=merchant_headers(client))"
    )
    process = subprocess.run(
        [sys.executable, "-c", script, str(settings.runtime_path), str(settings.jwt_private_key_path)],
        check=False, timeout=30,
    )
    assert process.returncode == 71
    assert rows(client, "SELECT status FROM webhook_outbox WHERE event='handoff.created'") == [{"status": "pending"}]
    client.app.state.webhooks.recover_pending_intents()
    assert client.app.state.webhooks.wait()
    [created] = receivers.events()
    assert created["type"] == "handoff.created"
    assert rows(client, "SELECT status FROM webhook_outbox WHERE event='handoff.created'") == [{"status": "delivered"}]


def test_attempt_count_survives_process_death_during_delivery(wired, settings, monkeypatch):
    client, _, receivers, _ = wired()
    monkeypatch.setattr(client.app.state.webhooks, "handoff_created_for", lambda *_: None)
    response = client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client))
    assert response.status_code == 200
    script = _child_settings_script() + (
        "import httpx; from merchant_assistant.api.webhooks import Webhooks; "
        "settings.ticketing_webhook_url='http://ticketing.test/webhooks/assistant'; "
        "settings.ticketing_webhook_secret=SecretStr('test-ticketing-webhook-secret'); "
        "transport=httpx.MockTransport(lambda request: os._exit(73)); "
        "hooks=Webhooks(settings,transport=transport); hooks.dispatch_pending(); hooks.wait()"
    )
    process = subprocess.run(
        [sys.executable, "-c", script, str(settings.runtime_path), str(settings.jwt_private_key_path)],
        check=False, timeout=30,
    )
    assert process.returncode == 73
    assert rows(client, "SELECT status,attempts FROM webhook_outbox WHERE event='handoff.created'") == [
        {"status": "pending", "attempts": 1}
    ]
    client.app.state.webhooks.recover_pending_intents()
    assert client.app.state.webhooks.wait()
    assert rows(client, "SELECT status,attempts FROM webhook_outbox WHERE event='handoff.created'") == [
        {"status": "delivered", "attempts": 2}
    ]
    assert len(receivers.events()) == 1


def test_reply_outbox_survives_process_death_before_delivery(wired, settings):
    client, _, receivers, _ = wired()
    case_id = hand_off(client)["case_id"]
    key = "crash-reply-outbox"
    script = _child_settings_script() + (
        "from merchant_assistant.data.db import connect; from merchant_assistant.handoffs import act; "
        "conn=connect(settings.db_path); "
        "def_resume=lambda case,record: (orchestrator.resume_handoff(case,record),os._exit(72)); "
        "act(conn,sys.argv[3],'op_ana','approve',None,sys.argv[4],actor='service:ticketing',resume=def_resume)"
    )
    process = subprocess.run(
        [sys.executable, "-c", script, str(settings.runtime_path), str(settings.jwt_private_key_path), case_id, key],
        check=False, timeout=30,
    )
    assert process.returncode == 72
    pending = rows(client, "SELECT target,status FROM webhook_outbox WHERE event='conversation.replied'")
    assert sorted((item["target"], item["status"]) for item in pending) == [
        ("merchant", "pending"), ("ticketing", "pending")
    ]
    receivers.requests.clear()
    client.app.state.webhooks.recover_pending_intents()
    assert client.app.state.webhooks.wait()
    assert len([event for event in receivers.events() if event["type"] == "conversation.replied"]) == 2
    replay = post_event(client, "ticket.action", ticket(case_id, action="approve", text="", idempotency_key=key))
    assert replay.status_code == 200
    assert client.app.state.webhooks.wait()
    assert len([event for event in receivers.events() if event["type"] == "conversation.replied"]) == 2


@pytest.mark.parametrize("event_type", ["handoff.created", "conversation.replied", "handoff.closed"])
def test_domain_change_rolls_back_if_outbox_cannot_be_written(wired, monkeypatch, event_type):
    client, _, _, _ = wired()
    target = handoffs if event_type == "handoff.closed" else graph
    original = target.enqueue

    def fail(conn, kind, data, key, *targets):
        if kind == event_type:
            raise RuntimeError("outbox unavailable")
        return original(conn, kind, data, key, *targets)

    if event_type == "handoff.created":
        monkeypatch.setattr(target, "enqueue", fail)
        with pytest.raises(RuntimeError, match="outbox unavailable"):
            client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client))
        assert rows(client, "SELECT * FROM messages WHERE status='handoff'") == []
    else:
        case_id = hand_off(client)["case_id"]
        monkeypatch.setattr(target, "enqueue", fail)
        if event_type == "conversation.replied":
            data = ticket(case_id, action="approve", text="", idempotency_key="outbox-failure")
            response = post_event(client, "ticket.action", data, event_id="evt_outbox_failure")
            assert response.status_code == 503
            assert rows(client, "SELECT * FROM messages WHERE via='operator'") == []
        else:
            with pytest.raises(RuntimeError, match="outbox unavailable"):
                post_event(client, "ticket.solved", ticket(case_id), event_id="evt_outbox_failure")
            assert case_snapshot(client, case_id)[0]["queue_state"] == "open"
    assert rows(client, "SELECT * FROM webhook_outbox WHERE event=?", (event_type,)) == []


def test_busy_event_is_retryable_and_untrusted_id_is_not_a_path(wired):
    client, _, _, _ = wired()
    case_id = hand_off(client)["case_id"]
    event_id = "../../arbitrary-id"
    lock_path = integrations._lock_path(client.app.state.settings.db_path, event_id)
    lock = sqlite3.connect(lock_path, isolation_level=None)
    try:
        lock.execute("BEGIN IMMEDIATE")
        blocked = post_event(client, "ticket.assigned", ticket(case_id), event_id=event_id)
        assert blocked.status_code == 503 and blocked.json()["error"]["code"] == "resume_failed"
        assert case_snapshot(client, case_id)[0]["queue_state"] == "open"
        assert rows(client, "SELECT * FROM webhook_inbox WHERE event_id=?", (event_id,)) == []
    finally:
        lock.close()
    retried = post_event(client, "ticket.assigned", ticket(case_id), event_id=event_id)
    assert retried.status_code == 200 and retried.json()["status"] == "accepted"


def test_interrupted_action_is_retried_without_waiting(wired, monkeypatch):
    client, _, _, _ = wired()
    case_id = hand_off(client)["case_id"]
    data = ticket(case_id, action="approve", text="", idempotency_key="crash-action-01")
    original = handoffs._resume

    def crash(*args):
        raise RuntimeError("stopped before resume")

    monkeypatch.setattr(handoffs, "_resume", crash)
    with pytest.raises(RuntimeError, match="stopped before resume"):
        post_event(client, "ticket.action", data, event_id="evt_crashed_action")
    monkeypatch.setattr(handoffs, "_resume", original)
    retried = post_event(client, "ticket.action", data, event_id="evt_crashed_action")
    assert retried.status_code == 200 and retried.json()["queue_state"] == "answered"
    assert case_snapshot(client, case_id)[0]["resume_count"] == 1


# --- refusals --------------------------------------------------------------------------------------------------------


def test_bad_signature_window_token_or_scope_change_nothing(wired, settings):
    client, _, _, _ = wired()
    case_id = hand_off(client)["case_id"]
    before = case_snapshot(client, case_id)
    data = ticket(case_id)
    attempts = [
        (post_event(client, "ticket.assigned", data, secret="wrong-secret"), 401, "invalid_signature"),
        (post_event(client, "ticket.assigned", data, secret=TICKETING_SECRET), 401, "invalid_signature"),
        (post_event(client, "ticket.assigned", data, skew=-310), 401, "invalid_signature"),
        (post_event(client, "ticket.assigned", data, skew=310), 401, "invalid_signature"),
        (post_event(client, "ticket.assigned", data, headers={}), 401, "token_required"),
        (post_event(client, "ticket.assigned", data, headers={"Authorization": "Bearer x.y.z"}), 401, "invalid_token"),
        (
            post_event(client, "ticket.assigned", data, headers=token_headers(client, Principal.operator("op_ana"))),
            403,
            "insufficient_scope",
        ),
        (post_event(client, "ticket.assigned", data, headers=merchant_headers(client)), 403, "insufficient_scope"),
    ]
    for index, (response, status, code) in enumerate(attempts):
        assert response.status_code == status and response.json()["error"]["code"] == code, (index, response.text)
    body, headers = signed("ticket.assigned", data)
    tampered = client.post(EVENTS_PATH, content=body.replace(b"op_ana", b"op_bru"), headers=headers | service(client))
    assert tampered.status_code == 401
    assert case_snapshot(client, case_id) == before
    assert rows(client, "SELECT * FROM webhook_inbox") == []
    settings.assistant_webhook_secret = None
    unconfigured = post_event(client, "ticket.assigned", data)
    assert unconfigured.status_code == 503 and unconfigured.json()["error"]["code"] == "webhook_not_configured"
    assert case_snapshot(client, case_id) == before


@pytest.mark.parametrize("invalid", ["t=²,v1=00", "t=999999999999999999999999,v1=00", "t={now},v1=é"])
def test_malformed_signature_returns_401_without_effect(wired, invalid):
    client, _, _, _ = wired()
    case_id = hand_off(client)["case_id"]
    before = case_snapshot(client, case_id)
    body, headers = signed("ticket.assigned", ticket(case_id))
    headers["X-Signature"] = invalid.format(now=int(time.time())).encode("latin-1")
    response = client.post(EVENTS_PATH, content=body, headers=headers | service(client))
    assert response.status_code == 401 and response.json()["error"]["code"] == "invalid_signature"
    assert case_snapshot(client, case_id) == before
    assert rows(client, "SELECT * FROM webhook_inbox") == []


def test_unknown_operator_case_event_and_payload(wired):
    client, _, _, _ = wired()
    case_id = hand_off(client)["case_id"]
    before = case_snapshot(client, case_id)
    unknown = post_event(client, "ticket.assigned", ticket(case_id, "op_ghost"))
    assert unknown.status_code == 422 and unknown.json()["error"]["code"] == "unknown_operator"
    missing = post_event(client, "ticket.assigned", ticket("hc_missing"))
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "case_not_found"
    event = post_event(client, "ticket.reopened", ticket(case_id))
    assert event.status_code == 422 and event.json()["error"]["code"] == "unknown_event"
    bad = post_event(client, "ticket.assigned", {"case_id": case_id})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "invalid_payload"
    key = post_event(client, "ticket.action", ticket(case_id, action="approve", idempotency_key="short"))
    assert key.status_code == 422 and key.json()["error"]["code"] == "invalid_idempotency_key"
    assert case_snapshot(client, case_id) == before
    audit = rows(client, "SELECT outcome, principal_id FROM audit_events WHERE outcome='unknown_operator'")
    assert audit == [{"outcome": "unknown_operator", "principal_id": "service:ticketing"}]


# --- receivers that fail ---------------------------------------------------------------------------------------------


def test_receiver_down_gets_three_recorded_attempts_without_breaking_the_request(wired):
    client, _, receivers, waits = wired()
    receivers.down = {"ticketing.test"}
    opened = hand_off(client)  # the merchant's request answers normally
    assert opened["message"]["status"] == "handoff"
    attempts = rows(client, "SELECT attempt, status, error, response_code FROM webhook_deliveries ORDER BY attempt")
    assert attempts == [
        {"attempt": n, "status": "error", "error": "ConnectError", "response_code": None} for n in (1, 2, 3)
    ]
    assert waits == [1.0, 2.0]
    receivers.down, receivers.status = set(), {"ticketing.test": 503, "merchant.test": 404}
    acted = post_event(
        client, "ticket.action", ticket(opened["case_id"], action="approve", idempotency_key="tkt-key-06")
    )
    assert acted.status_code == 200
    client.app.state.webhooks.wait()
    replied = rows(
        client,
        "SELECT target, attempt, status, response_code FROM webhook_deliveries WHERE event='conversation.replied'",
    )
    assert [(r["target"], r["attempt"], r["status"]) for r in replied] == [("merchant", 1, "rejected")]
    pending = rows(client, "SELECT status,attempts FROM webhook_outbox WHERE event='conversation.replied' "
                           "AND target='ticketing'")
    assert pending == [{"status": "pending", "attempts": 0}]  # the failed creation must be resolved first


def test_reply_gets_three_attempts_after_ticket_creation(wired):
    client, _, receivers, _ = wired()
    case_id = hand_off(client)["case_id"]
    receivers.status = {"ticketing.test": 503}
    assert post_event(client, "ticket.action", ticket(case_id, action="approve", idempotency_key="retry-reply-01"))\
        .status_code == 200
    assert client.app.state.webhooks.wait()
    attempts = rows(client, "SELECT attempt,status FROM webhook_deliveries "
                            "WHERE event='conversation.replied' AND target='ticketing' ORDER BY attempt")
    assert attempts == [{"attempt": n, "status": "error"} for n in (1, 2, 3)]
    assert rows(client, "SELECT status,attempts FROM webhook_outbox WHERE event='conversation.replied' "
                        "AND target='ticketing'") == [{"status": "failed", "attempts": 3}]
    client.app.state.webhooks.recover_pending_intents()
    assert client.app.state.webhooks.wait()
    assert len(rows(client, "SELECT * FROM webhook_deliveries WHERE event='conversation.replied' "
                            "AND target='ticketing'")) == 3


def test_signature_window_is_300_seconds():
    body = b'{"id":"evt_1"}'
    now = time.time()
    assert verify_signature("s", signature("s", body, int(now) - 299), body, now)
    assert not verify_signature("s", signature("s", body, int(now) - 301), body, now)
    assert not verify_signature("", signature("", body, int(now)), body, now)
    assert not verify_signature("s", "t=abc,v1=00", body, now)
    assert not verify_signature("s", None, body, now)


# --- the merchant receiver in `mocks` ---------------------------------------------------------------------------------


def test_mocks_merchant_receiver_checks_the_signature_and_ignores_repeated_ids():
    client = TestClient(create_mocks_app(conversation_secret=CONVERSATION_SECRET))
    data = {"case_id": "hc_1", "conversation_id": "conv_a", "reply_text": "Olá"}
    body, headers = signed("conversation.replied", data, secret=CONVERSATION_SECRET, event_id="evt_m_1")
    assert client.post("/merchant/events", content=body, headers=headers).json() == {"status": "received"}
    assert client.post("/merchant/events", content=body, headers=headers).json() == {"status": "duplicate"}
    _, wrong = signed("conversation.replied", data, secret="other", event_id="evt_m_1")
    assert client.post("/merchant/events", content=body, headers=wrong).status_code == 401
    stale_body, stale = signed("conversation.replied", data, secret=CONVERSATION_SECRET, skew=-400)
    assert client.post("/merchant/events", content=stale_body, headers=stale).status_code == 401
    other_body, other = signed("conversation.replied", data | {"conversation_id": "conv_b"}, secret=CONVERSATION_SECRET)
    assert client.post("/merchant/events", content=other_body, headers=other).status_code == 200
    listed = client.get("/merchant/events", params={"conversation_id": "conv_a"}).json()["events"]
    assert [e["id"] for e in listed] == ["evt_m_1"]
    assert len(client.get("/merchant/events").json()["events"]) == 2
    unconfigured = TestClient(create_mocks_app(conversation_secret=""))
    assert unconfigured.post("/merchant/events", content=body, headers=headers).status_code == 503


def test_assistant_delivers_to_the_mocks_merchant_receiver(wired, settings):
    """The real `mocks` receiver behind the assistant's own transport: the signature of one side checks on the other."""
    client, _, _, _ = wired()
    mocks = TestClient(create_mocks_app(conversation_secret=CONVERSATION_SECRET))
    settings.ticketing_webhook_url = None
    transport = AppTransport({"merchant.test": mocks})
    client.app.state.webhooks = Webhooks(settings, transport=transport, sleep=lambda _s: None)
    opened = hand_off(client)
    post_event(client, "ticket.action", ticket(opened["case_id"], action="approve", idempotency_key="tkt-key-07"))
    client.app.state.webhooks.wait()
    events = mocks.get("/merchant/events").json()["events"]
    assert [e["type"] for e in events] == ["conversation.replied"]
    assert events[0]["data"]["conversation_id"] == opened["message"]["conversation_id"]
    delivered = rows(client, "SELECT target, status, response_code FROM webhook_deliveries WHERE target='merchant'")
    assert delivered == [{"target": "merchant", "status": "delivered", "response_code": 200}]


# --- a case opened by a turn that stopped before it finished (review round 4, P2-1) ---------------------------------


def only_case(client) -> dict:
    [case] = rows(client, "SELECT * FROM handoff_cases")
    return case


def has_flow(orchestrator, case) -> bool:
    return bool(orchestrator.review_graph().get_state({"configurable": {"thread_id": case["thread_id"]}}).values)


def complete_by_sending_again(client, orchestrator, receivers, case) -> None:
    """The merchant sends the same message again: the turn completes the case and the operator can act on it."""
    receivers.requests.clear()
    body = {"message": HUMAN, "conversation_id": case["conversation_id"]}
    again = client.post("/messages", json=body, headers=merchant_headers(client))
    assert again.status_code == 200 and again.json()["status"] == "handoff", again.text
    assert again.json()["handoff"]["protocol"] == case["protocol"]
    assert client.app.state.webhooks.wait()
    after = only_case(client)  # still the one case, now with its flow saved and its intention delivered once
    assert after["case_id"] == case["case_id"] and after["resume_status"] is None and has_flow(orchestrator, after)
    [created] = receivers.events()
    assert created["type"] == "handoff.created" and created["data"]["case_id"] == case["case_id"]
    assert created["data"]["protocol"] == case["protocol"]
    assert rows(client, "SELECT status,attempts FROM webhook_outbox") == [{"status": "delivered", "attempts": 1}]
    assert len(rows(client, "SELECT * FROM messages WHERE role='assistant'")) == 1
    third = client.post("/messages", json=body, headers=merchant_headers(client))  # nothing is queued twice
    assert third.status_code == 200 and client.app.state.webhooks.wait()
    assert len(receivers.events()) == 1 and len(rows(client, "SELECT * FROM webhook_outbox")) == 1
    assert post_event(client, "ticket.assigned", ticket(case["case_id"])).status_code == 200
    data = ticket(case["case_id"], action="approve", text="", idempotency_key="after-interrupted-turn")
    acted = post_event(client, "ticket.action", data)
    assert acted.status_code == 200 and acted.json()["status"] == "accepted", acted.text  # not 503 checkpoint_missing
    assert client.app.state.webhooks.wait()


@pytest.mark.parametrize("dies", ["before_checkpoint", "after_checkpoint"])
def test_case_of_a_turn_that_died_is_completed_when_the_message_is_sent_again(wired, settings, dies):
    client, orchestrator, receivers, _ = wired()
    script = _child_settings_script() + (
        "from fastapi.testclient import TestClient; from merchant_assistant.api.app import create_app; "
        "from merchant_assistant.testing import merchant_headers; app=create_app(orchestrator,settings); "
        "real=orchestrator._suspend; "
        "orchestrator._suspend=(lambda *a,**k: os._exit(74)) if sys.argv[3]=='before_checkpoint' "
        "else (lambda *a,**k: (real(*a,**k), os._exit(74))); "
        "client=TestClient(app); "
        "client.post('/messages',json={'message':'Quero falar com um atendente'},headers=merchant_headers(client))"
    )
    process = subprocess.run(
        [sys.executable, "-c", script, str(settings.runtime_path), str(settings.jwt_private_key_path), dies],
        check=False, timeout=60,
    )
    assert process.returncode == 74
    case = only_case(client)  # written by the escalation, before the end-of-turn transaction that never ran
    assert case["queue_state"] == "open" and case["resume_status"] is None and case["thread_id"]
    assert rows(client, "SELECT * FROM webhook_outbox") == [] and rows(client, "SELECT * FROM messages") == []
    assert has_flow(orchestrator, case) == (dies == "after_checkpoint")
    complete_by_sending_again(client, orchestrator, receivers, case)


def test_case_of_a_turn_whose_outbox_write_failed_is_completed_when_the_message_is_sent_again(wired, monkeypatch):
    client, orchestrator, receivers, _ = wired()
    original, failing = graph.enqueue, [True]

    def flaky(conn, kind, data, key, *targets):
        if kind == "handoff.created" and failing:
            raise RuntimeError("outbox unavailable")
        return original(conn, kind, data, key, *targets)

    monkeypatch.setattr(graph, "enqueue", flaky)
    with pytest.raises(RuntimeError, match="outbox unavailable"):
        client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client))
    case = only_case(client)  # the turn was rolled back, the case written before it was not
    assert case["queue_state"] == "open" and has_flow(orchestrator, case)
    assert rows(client, "SELECT * FROM webhook_outbox") == [] and rows(client, "SELECT * FROM messages") == []
    failing.clear()
    complete_by_sending_again(client, orchestrator, receivers, case)


def test_case_without_a_url_to_send_to_is_not_queued_late_or_twice(wired, settings):
    client, orchestrator, receivers, _ = wired()
    settings.ticketing_webhook_url = None
    opened = hand_off(client)
    assert rows(client, "SELECT * FROM webhook_outbox") == []
    again = client.post(
        "/messages",
        json={"message": HUMAN, "conversation_id": opened["message"]["conversation_id"]},
        headers=merchant_headers(client),
    )
    assert again.status_code == 200 and client.app.state.webhooks.wait()
    assert rows(client, "SELECT * FROM webhook_outbox") == [] and receivers.events() == []
    assert has_flow(orchestrator, only_case(client))


# --- destinations, startup and exclusion between processes (review round 4, P3) -------------------------------------


def test_destination_without_a_url_receives_no_intention(wired, settings):
    client, _, receivers, _ = wired()
    settings.ticketing_webhook_url = None  # the merchant receiver stays configured
    case_id = hand_off(client)["case_id"]
    assert rows(client, "SELECT * FROM webhook_outbox") == []
    assert post_event(client, "ticket.assigned", ticket(case_id)).status_code == 200
    data = ticket(case_id, action="approve", text="", idempotency_key="no-ticketing-url")
    assert post_event(client, "ticket.action", data).status_code == 200
    assert post_event(client, "ticket.solved", ticket(case_id)).status_code == 200
    assert client.app.state.webhooks.wait()
    assert rows(client, "SELECT event,target,status FROM webhook_outbox") == [
        {"event": "conversation.replied", "target": "merchant", "status": "delivered"}
    ]
    assert [request.url.host for request in receivers.requests] == ["merchant.test"]


def test_failing_recovery_does_not_keep_the_api_from_starting(offline, monkeypatch, caplog):
    client, _, _ = offline()
    calls = []

    def broken():
        calls.append(1)
        raise RuntimeError("outbox unreadable")

    monkeypatch.setattr(client.app.state.webhooks, "recover_pending_intents", broken)
    with TestClient(client.app) as started:  # runs the lifespan
        assert started.get("/health").status_code == 200
    assert calls == [1] and "could not recover the pending webhook intentions" in caplog.text


def _hold(script: str, *args: str) -> subprocess.Popen:
    process = subprocess.Popen(
        [sys.executable, "-c", script, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    assert process.stdout.readline().strip() == "locked"
    return process


def _release(process: subprocess.Popen) -> None:
    process.stdin.close()
    process.wait(timeout=20)
    process.stdout.close()


HOLD_CASE_LOCK = (
    "import sys\n"
    "from merchant_assistant.data.db import connect\n"
    "from merchant_assistant.handoffs import _case_lock\n"
    "conn = connect(sys.argv[1])\n"
    "with _case_lock(conn, sys.argv[2]):\n"
    "    print('locked', flush=True)\n"
    "    sys.stdin.read()\n"
)
HOLD_DELIVERY_LOCKS = (
    "import sqlite3, sys\n"
    "held = []\n"
    "for stripe in range(64):\n"
    "    lock = sqlite3.connect(f'{sys.argv[1]}.delivery-lock-{stripe:02d}', isolation_level=None)\n"
    "    lock.execute('BEGIN IMMEDIATE')\n"
    "    held.append(lock)\n"
    "print('locked', flush=True)\n"
    "sys.stdin.read()\n"
)


def test_action_on_a_case_waits_for_another_process_holding_the_case(wired, settings, monkeypatch):
    from merchant_assistant.data.db import connect

    client, _, _, _ = wired()
    case_id = hand_off(client)["case_id"]
    real_connect = sqlite3.connect

    def quick_lock(path, *args, **kwargs):  # the lock files wait 5 s by default: shorten it for the test
        return real_connect(path, *args, **(kwargs | {"timeout": 0.2} if ".case-lock-" in str(path) else kwargs))

    monkeypatch.setattr(sqlite3, "connect", quick_lock)
    other = _hold(HOLD_CASE_LOCK, str(settings.db_path), case_id)
    conn = connect(settings.db_path)
    try:
        with pytest.raises(handoffs.HandoffError) as busy:
            handoffs.act(conn, case_id, "op_ana", "approve", None, "case-lock-key-1", actor="service:ticketing")
        assert (busy.value.status, busy.value.code) == (503, "resume_failed")
        assert case_snapshot(client, case_id) == (
            {"queue_state": "open", "claimed_by": None, "resume_count": 0, "closed_at": None, "ticket_id": None}, 0
        )
        _release(other)
        done = handoffs.act(conn, case_id, "op_ana", "approve", None, "case-lock-key-1", actor="service:ticketing")
        assert done["queue_state"] == "answered" and done["replayed"] is False
    finally:
        conn.close()
        if other.poll() is None:
            other.kill()


def test_delivery_waits_for_another_process_delivering_the_same_event(wired, settings, monkeypatch):
    client, _, receivers, _ = wired()
    webhooks = client.app.state.webhooks
    monkeypatch.setattr(webhooks, "handoff_created_for", lambda *_: None)  # queue it, deliver it by hand below
    assert client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client)).status_code == 200
    assert rows(client, "SELECT status,attempts FROM webhook_outbox") == [{"status": "pending", "attempts": 0}]
    other = _hold(HOLD_DELIVERY_LOCKS, str(settings.db_path))
    try:
        webhooks.dispatch_pending()
        time.sleep(1.0)  # long enough for an unguarded delivery to have reached the receiver
        assert receivers.requests == []
        assert rows(client, "SELECT status,attempts FROM webhook_outbox") == [{"status": "pending", "attempts": 0}]
        _release(other)
        assert webhooks.wait(timeout=30)
    finally:
        if other.poll() is None:
            other.kill()
    assert [event["type"] for event in receivers.events()] == ["handoff.created"]
    assert rows(client, "SELECT status,attempts FROM webhook_outbox") == [{"status": "delivered", "attempts": 1}]
