"""v0.7.0 task 66 (CA-47, CA-48): signed webhooks between the assistant, the ticketing and the merchant.

Fake receivers in process (httpx.MockTransport); the ticketing events are signed here with the contract's scheme and
sent with a service token. Scripted model, no network, no cost."""

from __future__ import annotations

import json
import sqlite3
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant.api.identity import Principal
from merchant_assistant.api.webhooks import Webhooks, signature, verify_signature
from merchant_assistant.mocks.service import create_mocks_app
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
    assert replied["ticketing.test"] == replied["merchant.test"]  # one event, two receivers
    merchant_request = next(r for r in receivers.requests if r.url.host == "merchant.test")
    assert verify_signature(
        CONVERSATION_SECRET, merchant_request.headers["x-signature"], merchant_request.content, time.time()
    )
    for request in receivers.requests:  # no secret, token or other merchant in the reply either
        raw = request.content.decode()
        assert all(s not in raw for s in (TICKETING_SECRET, ASSISTANT_SECRET, CONVERSATION_SECRET, "Bearer", "eyJ"))
        assert "cliente_demo_002" not in raw and CARD not in raw
    data = replied["merchant.test"]["data"]
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
    client.app.state.webhooks.wait()
    assert [e for e in receivers.events() if e["type"] == "conversation.replied"] == []  # nothing was produced
    orchestrator.resume_handoff = original
    retried = post_event(client, "ticket.action", data, event_id="evt_retry_0001")  # the outbox repeats the event
    assert retried.status_code == 200 and retried.json()["queue_state"] == "answered", retried.text
    client.app.state.webhooks.wait()
    assert len([e for e in receivers.events() if e["type"] == "conversation.replied"]) == 2


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
    assert sorted((r["target"], r["attempt"], r["status"]) for r in replied) == [
        ("merchant", 1, "rejected"),  # a 4xx is final
        ("ticketing", 1, "error"),
        ("ticketing", 2, "error"),
        ("ticketing", 3, "error"),
    ]


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
