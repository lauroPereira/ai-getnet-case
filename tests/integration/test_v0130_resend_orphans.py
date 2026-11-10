"""v0.13.0 task 99 (spec D4, D5; CA-71): exhausted webhook deliveries are resent, by an operator or once at startup,
and a case opened by a turn that stopped before telling the ticketing is announced at the next startup. Also the
pieces of D4 that one process can show: no lock in memory around a case, and WAL on the database.

Fake receivers in process (httpx.MockTransport), scripted model, no network, no cost. The two-process tests are in
`test_v0130_workers.py`."""

from __future__ import annotations

import json
import sqlite3
import threading

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant import handoffs
from merchant_assistant.api.identity import Principal
from merchant_assistant.api.webhooks import Webhooks
from merchant_assistant.data.db import connect
from merchant_assistant.data.webhook_outbox import RESEND_AFTER_SECONDS, webhook_targets
from merchant_assistant.mocks.service import create_mocks_app
from merchant_assistant.orchestration import graph
from merchant_assistant.testing import TEST_TICKETING_SECRET, AppTransport, merchant_headers, token_headers
from merchant_assistant.ticketing.config import TicketingSettings
from merchant_assistant.ticketing.service import create_app as create_ticketing_app

TICKETING_URL = "http://ticketing.test/webhooks/assistant"
MERCHANT_URL = "http://merchant.test/merchant/events"
HUMAN = "Quero falar com um atendente"
LONG_AGO = "2026-01-01T00:00:00+00:00"


class Receivers:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.down: set[str] = set()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.host in self.down:
            raise httpx.ConnectError("receiver down", request=request)
        return httpx.Response(200, json={"status": "received"})

    def events(self, host: str | None = None) -> list[dict]:
        return [json.loads(r.content) for r in self.requests if host in (None, r.url.host)]


@pytest.fixture
def wired(offline, settings):
    def make():
        settings.ticketing_webhook_url = TICKETING_URL
        settings.ticketing_webhook_secret = SecretStr("test-ticketing-webhook-secret")
        settings.conversation_webhook_url = MERCHANT_URL
        settings.conversation_webhook_secret = SecretStr("test-conversation-webhook-secret")
        client, orchestrator, _ = offline()
        receivers, waits = Receivers(), []
        client.app.state.webhooks = Webhooks(settings, transport=httpx.MockTransport(receivers), sleep=waits.append)
        return client, receivers

    return make


def rows(client, query, args=()):
    conn = sqlite3.connect(client.app.state.settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(query, args)]
    finally:
        conn.close()


def change(client, query, args=()):
    conn = sqlite3.connect(client.app.state.settings.db_path)
    try:
        conn.execute(query, args)
        conn.commit()
    finally:
        conn.close()


def operator(client) -> dict:
    return token_headers(client, Principal.operator("op_ana"))


def exhausted_case(client, receivers) -> str:
    """A handoff whose `handoff.created` ran out of attempts (ticketing down), with the ticketing back up after."""
    receivers.down = {"ticketing.test"}
    response = client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client))
    assert response.status_code == 200 and response.json()["status"] == "handoff"
    assert client.app.state.webhooks.wait()
    assert rows(client, "SELECT status,attempts,resend_count FROM webhook_outbox") == [
        {"status": "exhausted", "attempts": 3, "resend_count": 0}
    ]
    receivers.down = set()
    receivers.requests.clear()
    return rows(client, "SELECT case_id FROM handoff_cases")[0]["case_id"]


# --- resend by an operator ------------------------------------------------------------------------------------------


def test_each_attempt_shows_the_intention_of_its_own_event_and_target(wired, settings):
    settings.telegram_webhook_url = "http://telegram.test/webhooks/assistant"
    settings.telegram_webhook_secret = SecretStr("test-telegram-webhook-secret")
    client, receivers = wired()
    receivers.down = {"ticketing.test"}  # the same handoff.created: exhausted at the ticketing, delivered to Telegram
    response = client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client))
    assert response.status_code == 200 and response.json()["status"] == "handoff"
    assert client.app.state.webhooks.wait()
    case_id = rows(client, "SELECT case_id FROM handoff_cases")[0]["case_id"]
    change(  # an attempt recorded with no intention behind it (before the outbox existed)
        client,
        "INSERT INTO webhook_deliveries (delivery_id,event,target,case_id,conversation_id,attempt,status,"
        "response_code,created_at,event_id,error) VALUES ('dlv_legacy','handoff.created','ticketing',?,NULL,1,"
        "'error',NULL,?,'evt_legacy',NULL)",
        (case_id, LONG_AGO),
    )
    deliveries = client.get(f"/v1/handoffs/{case_id}", headers=operator(client)).json()["deliveries"]
    seen = sorted(((d["target"], d["status"], d["intent_status"], d["resend_count"]) for d in deliveries), key=repr)
    assert seen == sorted(
        [("ticketing", "error", None, None)]
        + [("ticketing", "error", "exhausted", 0)] * 3
        + [("telegram", "delivered", "delivered", 0)],
        key=repr,
    )
    assert len({d["event_id"] for d in deliveries if d["event_id"] != "evt_legacy"}) == 1  # one event, two targets


def test_an_operator_resends_an_exhausted_delivery(wired):
    client, receivers = wired()
    case_id = exhausted_case(client, receivers)
    detail = client.get(f"/v1/handoffs/{case_id}", headers=operator(client)).json()
    delivery_id = detail["deliveries"][-1]["delivery_id"]
    assert [d["status"] for d in detail["deliveries"]] == ["error"] * 3
    # each attempt carries the state of its intention: the operator sees what can be resent
    assert [(d["intent_status"], d["resend_count"]) for d in detail["deliveries"]] == [("exhausted", 0)] * 3

    resent = client.post(f"/v1/webhooks/deliveries/{delivery_id}/resend", headers=operator(client))
    assert resent.status_code == 202, resent.text
    body = resent.json()
    assert body == {
        "delivery_id": delivery_id,
        "event_id": body["event_id"],
        "target": "ticketing",
        "case_id": case_id,
        "status": "pending",
        "resend_count": 1,
    }
    assert client.app.state.webhooks.wait()
    assert [event["type"] for event in receivers.events()] == ["handoff.created"]
    assert rows(client, "SELECT status,attempts,resend_count FROM webhook_outbox") == [
        {"status": "delivered", "attempts": 4, "resend_count": 1}
    ]
    attempts = rows(client, "SELECT attempt,status FROM webhook_deliveries ORDER BY attempt")
    assert attempts == [{"attempt": n, "status": "error"} for n in (1, 2, 3)] + [{"attempt": 4, "status": "delivered"}]
    after = client.get(f"/v1/handoffs/{case_id}", headers=operator(client)).json()["deliveries"]
    assert [(d["status"], d["intent_status"], d["resend_count"]) for d in after] == [
        ("error", "delivered", 1), ("error", "delivered", 1), ("error", "delivered", 1), ("delivered", "delivered", 1)
    ]  # fmt: skip

    again = client.post(f"/v1/webhooks/deliveries/{delivery_id}/resend", headers=operator(client))
    assert again.status_code == 409 and again.json()["error"]["code"] == "delivery_not_exhausted"
    missing = client.post("/v1/webhooks/deliveries/dlv_missing/resend", headers=operator(client))
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "delivery_not_found"
    audit = rows(client, "SELECT outcome,resource_id,principal_id FROM audit_events WHERE tool='webhook.resend'")
    assert audit == [
        {"outcome": "ok", "resource_id": case_id, "principal_id": "operator:op_ana"},
        {"outcome": "delivery_not_exhausted", "resource_id": None, "principal_id": "operator:op_ana"},
        {"outcome": "delivery_not_found", "resource_id": None, "principal_id": "operator:op_ana"},
    ]


def test_resend_needs_an_operator_with_handoff_operate(wired):
    client, receivers = wired()
    case_id = exhausted_case(client, receivers)
    delivery_id = rows(client, "SELECT delivery_id FROM webhook_deliveries LIMIT 1")[0]["delivery_id"]
    for headers in (merchant_headers(client), token_headers(client, Principal.of("service", "ticketing"))):
        refused = client.post(f"/v1/webhooks/deliveries/{delivery_id}/resend", headers=headers)
        assert refused.status_code == 403 and refused.json()["error"]["code"] == "insufficient_scope"
    assert client.post(f"/v1/webhooks/deliveries/{delivery_id}/resend").status_code == 401
    outbox = rows(client, "SELECT status,resend_count FROM webhook_outbox")
    assert outbox == [{"status": "exhausted", "resend_count": 0}]
    assert receivers.requests == [] and case_id


def test_each_resend_allows_another_round_of_attempts(wired):
    client, receivers = wired()
    exhausted_case(client, receivers)
    receivers.down = {"ticketing.test"}  # still down after the resend
    delivery_id = rows(client, "SELECT delivery_id FROM webhook_deliveries LIMIT 1")[0]["delivery_id"]
    assert client.post(f"/v1/webhooks/deliveries/{delivery_id}/resend", headers=operator(client)).status_code == 202
    assert client.app.state.webhooks.wait()
    assert rows(client, "SELECT status,attempts,resend_count FROM webhook_outbox") == [
        {"status": "exhausted", "attempts": 6, "resend_count": 1}
    ]
    assert [r["attempt"] for r in rows(client, "SELECT attempt FROM webhook_deliveries ORDER BY attempt")] == [
        1, 2, 3, 4, 5, 6
    ]


def outbox(client) -> list[tuple[str, str, str]]:
    found = rows(client, "SELECT event,target,status FROM webhook_outbox ORDER BY rowid")
    return [(r["event"], r["target"], r["status"]) for r in found]


def first_delivery(client, event: str) -> str:
    return rows(client, "SELECT delivery_id FROM webhook_deliveries WHERE event=? LIMIT 1", (event,))[0]["delivery_id"]


def test_the_reply_waits_for_an_exhausted_creation_and_follows_its_resend(wired):
    client, receivers = wired()
    case_id = exhausted_case(client, receivers)
    acted = client.post(
        f"/v1/handoffs/{case_id}/actions",
        headers=operator(client),
        json={"action": "approve", "idempotency_key": "resend-reply-01"},
    )
    assert acted.status_code == 200, acted.text
    assert client.app.state.webhooks.wait()
    # The merchant has no creation to wait for; the ticketing does: its copy of the reply waits.
    assert [(e["type"], r.url.host) for e, r in zip(receivers.events(), receivers.requests, strict=True)] == [
        ("conversation.replied", "merchant.test")
    ]
    assert outbox(client) == [
        ("handoff.created", "ticketing", "exhausted"),
        ("conversation.replied", "ticketing", "pending"),
        ("conversation.replied", "merchant", "delivered"),
    ]
    receivers.requests.clear()
    resent = client.post(
        f"/v1/webhooks/deliveries/{first_delivery(client, 'handoff.created')}/resend", headers=operator(client)
    )
    assert resent.status_code == 202, resent.text
    assert client.app.state.webhooks.wait()
    assert [e["type"] for e in receivers.events("ticketing.test")] == ["handoff.created", "conversation.replied"]
    assert {status for _, _, status in outbox(client)} == {"delivered"}


def test_an_exhausted_creation_never_holds_back_another_case(wired):
    client, receivers = wired()
    exhausted_case(client, receivers)
    other = client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client))  # a new conversation
    assert other.status_code == 200 and other.json()["status"] == "handoff", other.text
    assert client.app.state.webhooks.wait()
    [created] = receivers.events("ticketing.test")
    assert created["type"] == "handoff.created" and created["data"]["protocol"] == other.json()["handoff"]["protocol"]
    assert [status for event, _, status in outbox(client) if event == "handoff.created"] == ["exhausted", "delivered"]


def test_a_resend_to_a_destination_without_url_or_secret_is_refused(wired):
    client, receivers = wired()
    exhausted_case(client, receivers)
    settings = client.app.state.settings
    delivery_id = first_delivery(client, "handoff.created")
    for url, secret in ((None, SecretStr("test-ticketing-webhook-secret")), (TICKETING_URL, SecretStr(" "))):
        settings.ticketing_webhook_url, settings.ticketing_webhook_secret = url, secret
        refused = client.post(f"/v1/webhooks/deliveries/{delivery_id}/resend", headers=operator(client))
        assert refused.status_code == 409, refused.text
        assert refused.json()["error"]["code"] == "delivery_target_not_configured"
    assert rows(client, "SELECT status,resend_count FROM webhook_outbox") == [
        {"status": "exhausted", "resend_count": 0}
    ]
    assert receivers.requests == []
    settings.ticketing_webhook_url = TICKETING_URL
    settings.ticketing_webhook_secret = SecretStr("test-ticketing-webhook-secret")
    assert client.post(f"/v1/webhooks/deliveries/{delivery_id}/resend", headers=operator(client)).status_code == 202
    assert client.app.state.webhooks.wait()
    assert rows(client, "SELECT status FROM webhook_outbox") == [{"status": "delivered"}]


def test_resend_is_rate_limited_per_operator(wired):
    client, receivers = wired()
    exhausted_case(client, receivers)
    client.app.state.settings.rate_limit_per_minute = 2
    headers = operator(client)
    codes = [client.post("/v1/webhooks/deliveries/dlv_missing/resend", headers=headers).status_code for _ in range(3)]
    assert codes == [404, 404, 429]
    limited = client.post("/v1/webhooks/deliveries/dlv_missing/resend", headers=headers)
    assert limited.json()["error"]["code"] == "rate_limited" and int(limited.headers["Retry-After"]) > 0
    assert rows(client, "SELECT status,resend_count FROM webhook_outbox") == [
        {"status": "exhausted", "resend_count": 0}
    ]


# --- the order against the real ticketing --------------------------------------------------------------------------


ASSISTANT, TICKETING, MERCHANT = "assistant.test", "ticketing.test", "merchant.test"


@pytest.fixture
def system(offline, settings, tmp_path):
    """The assistant, the real ticketing service and the synthetic merchant receiver, in process, over HTTP through a
    transport that routes by host; the ticketing can be taken down."""
    settings.ticketing_webhook_url = TICKETING_URL
    settings.ticketing_webhook_secret = SecretStr("it-ticketing-webhook-secret")
    settings.conversation_webhook_url = MERCHANT_URL
    settings.conversation_webhook_secret = SecretStr("it-conversation-webhook-secret")
    settings.assistant_webhook_secret = SecretStr("it-assistant-webhook-secret")
    assistant, _, _ = offline()
    ticketing_settings = TicketingSettings(
        db_path=tmp_path / "ticketing" / "ticketing.sqlite3",
        assistant_url=f"http://{ASSISTANT}",
        assistant_issuer=settings.jwt_issuer,
        assistant_jwks_url=f"http://{ASSISTANT}/.well-known/jwks.json",
        inbound_secret="it-ticketing-webhook-secret",
        outbound_secret="it-assistant-webhook-secret",
        client_secret=TEST_TICKETING_SECRET,
        outbox_poll_s=0,
    )
    apps: dict[str, TestClient] = {ASSISTANT: assistant}
    ticketing = TestClient(create_ticketing_app(ticketing_settings, client=httpx.Client(transport=AppTransport(apps))))
    merchant = TestClient(create_mocks_app(conversation_secret="it-conversation-webhook-secret"))
    apps |= {TICKETING: ticketing, MERCHANT: merchant}
    down: set[str] = set()

    class Routed(AppTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            if request.url.host in down:
                raise httpx.ConnectError("ticketing down", request=request)
            return super().handle_request(request)

    assistant.app.state.webhooks = Webhooks(settings, transport=Routed(apps), sleep=lambda _s: None)
    return assistant, ticketing, down


@pytest.mark.parametrize("later", ["conversation.replied", "handoff.closed"])
def test_with_the_real_ticketing_a_later_event_waits_for_the_resent_creation(system, later):
    assistant, ticketing, down = system
    webhooks, settings = assistant.app.state.webhooks, assistant.app.state.settings
    down.add(TICKETING)
    opened = assistant.post("/messages", json={"message": HUMAN}, headers=merchant_headers(assistant))
    assert opened.status_code == 200 and opened.json()["status"] == "handoff" and webhooks.wait()
    down.clear()  # the ticketing is back, but nobody resent the creation yet
    case_id = rows(assistant, "SELECT case_id FROM handoff_cases")[0]["case_id"]
    ana = operator(assistant)
    if later == "conversation.replied":
        acted = assistant.post(
            f"/v1/handoffs/{case_id}/actions",
            headers=ana,
            json={"action": "approve", "idempotency_key": "real-ticketing-reply-01"},
        )
        assert acted.status_code == 200, acted.text
    else:
        conn = connect(settings.db_path)
        try:
            handoffs.close(conn, case_id, "op_ana", actor="operator:op_ana", targets=webhook_targets(settings))
        finally:
            conn.close()
        webhooks.handoff_closed({"case_id": case_id})
    assert webhooks.wait()
    waiting = [("handoff.created", "ticketing", "exhausted"), (later, "ticketing", "pending")]
    if later == "conversation.replied":
        waiting.append((later, "merchant", "delivered"))
    assert outbox(assistant) == waiting  # nothing reached the ticketing ahead of its ticket
    assert rows(assistant, "SELECT * FROM webhook_deliveries WHERE event=? AND target='ticketing'", (later,)) == []
    assert ticketing.get("/tickets", headers=ana).json()["tickets"] == []

    created = first_delivery(assistant, "handoff.created")
    resent = assistant.post(f"/v1/webhooks/deliveries/{created}/resend", headers=ana)
    assert resent.status_code == 202, resent.text
    assert webhooks.wait()
    assert {status for _, _, status in outbox(assistant)} == {"delivered"}
    [ticket] = ticketing.get("/tickets", headers=ana).json()["tickets"]
    detail = ticketing.get(f"/tickets/{ticket['ticket_id']}", headers=ana).json()
    assert [d["event_type"] for d in detail["deliveries"]["received"]] == ["handoff.created", later]
    if later == "conversation.replied":
        assert detail["reply_text"] and detail["reply_delivered_at"]
    else:
        assert detail["closed_at"] and detail["closed_by"] == "op_ana"
    refused = rows(assistant, "SELECT * FROM webhook_deliveries WHERE status='rejected'")
    assert refused == []  # no 404 ticket_not_found on the way


# --- resend at startup ------------------------------------------------------------------------------------------------


def test_startup_resends_once_what_was_exhausted_more_than_an_hour_ago(wired):
    client, receivers = wired()
    exhausted_case(client, receivers)
    assert RESEND_AFTER_SECONDS == 3600
    with TestClient(client.app):  # exhausted a moment ago: left alone
        assert client.app.state.webhooks.wait()
    assert receivers.requests == []
    assert rows(client, "SELECT status FROM webhook_outbox") == [{"status": "exhausted"}]

    change(client, "UPDATE webhook_deliveries SET created_at=?", (LONG_AGO,))
    receivers.down = {"ticketing.test"}
    with TestClient(client.app):  # the startup queues it again, once; the receiver is still down
        assert client.app.state.webhooks.wait()
    assert rows(client, "SELECT status,attempts,resend_count FROM webhook_outbox") == [
        {"status": "exhausted", "attempts": 6, "resend_count": 1}
    ]
    change(client, "UPDATE webhook_deliveries SET created_at=?", (LONG_AGO,))
    receivers.down = set()
    receivers.requests.clear()
    with TestClient(client.app):  # already sent again once: an operator decides now
        assert client.app.state.webhooks.wait()
    assert receivers.requests == []
    outbox = rows(client, "SELECT status,resend_count FROM webhook_outbox")
    assert outbox == [{"status": "exhausted", "resend_count": 1}]


def test_startup_resend_delivers_when_the_receiver_is_back(wired):
    client, receivers = wired()
    exhausted_case(client, receivers)
    change(client, "UPDATE webhook_deliveries SET created_at=?", (LONG_AGO,))
    with TestClient(client.app):
        assert client.app.state.webhooks.wait()
    assert [event["type"] for event in receivers.events()] == ["handoff.created"]
    assert rows(client, "SELECT status,attempts,resend_count FROM webhook_outbox") == [
        {"status": "delivered", "attempts": 4, "resend_count": 1}
    ]


# --- orphan case at startup -------------------------------------------------------------------------------------------


def test_a_case_opened_by_a_turn_that_stopped_is_announced_at_startup(wired, monkeypatch):
    client, receivers = wired()
    real = graph.enqueue

    def stopped(conn, kind, data, key, *targets):  # the turn stops between opening the case and queueing it
        if kind == "handoff.created":
            raise RuntimeError("process stopped")
        return real(conn, kind, data, key, *targets)

    monkeypatch.setattr(graph, "enqueue", stopped)
    with pytest.raises(RuntimeError, match="process stopped"):
        client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client))
    monkeypatch.undo()
    [case] = rows(client, "SELECT case_id, protocol, queue_state, thread_id FROM handoff_cases")
    assert case["queue_state"] == "open" and rows(client, "SELECT * FROM webhook_outbox") == []
    assert client.app.state.orchestrator.flow_saved(case["thread_id"])  # the turn saved the flow before stopping

    with TestClient(client.app):  # the startup recreates the intention and delivers it
        assert client.app.state.webhooks.wait()
    [created] = receivers.events()
    assert created["type"] == "handoff.created" and created["data"]["case_id"] == case["case_id"]
    assert created["data"]["protocol"] == case["protocol"] and created["data"]["summary"]
    assert created["id"] == rows(client, "SELECT event_id FROM webhook_outbox")[0]["event_id"]
    assert rows(client, "SELECT event,status FROM webhook_outbox") == [
        {"event": "handoff.created", "status": "delivered"}
    ]
    with TestClient(client.app):  # a second startup (the other worker) queues nothing more
        assert client.app.state.webhooks.wait()
    assert len(receivers.requests) == 1


def test_a_case_whose_flow_was_never_saved_is_not_announced_and_the_resend_completes_it(wired, monkeypatch):
    client, _ = wired()

    def stopped(*args, **kwargs):  # the turn stops after writing the case and before saving its flow
        raise RuntimeError("process stopped")

    monkeypatch.setattr(client.app.state.orchestrator, "_suspend", stopped)
    with pytest.raises(RuntimeError, match="process stopped"):
        client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client))
    monkeypatch.undo()
    [case] = rows(client, "SELECT * FROM handoff_cases")
    assert case["queue_state"] == "open" and case["thread_id"] and case["resume_status"] is None

    restarted, receivers = wired()  # a new process over the same runtime
    orchestrator = restarted.app.state.orchestrator
    with TestClient(restarted.app):  # its startup finds nothing an operator could resume: no announcement
        assert restarted.app.state.webhooks.wait()
        assert not orchestrator.flow_saved(case["thread_id"])
        assert receivers.requests == [] and rows(restarted, "SELECT * FROM webhook_outbox") == []

        again = restarted.post(  # the merchant sends the same message again: the original case is completed
            "/messages",
            json={"message": HUMAN, "conversation_id": case["conversation_id"]},
            headers=merchant_headers(restarted),
        )
        assert again.status_code == 200 and again.json()["handoff"]["protocol"] == case["protocol"], again.text
        assert restarted.app.state.webhooks.wait()
        assert orchestrator.flow_saved(case["thread_id"])
        [created] = receivers.events("ticketing.test")
        assert created["type"] == "handoff.created" and created["data"]["case_id"] == case["case_id"]
        acted = restarted.post(
            f"/v1/handoffs/{case['case_id']}/actions",
            headers=operator(restarted),
            json={"action": "approve", "idempotency_key": "orphan-unsaved-01"},
        )
        assert acted.status_code == 200 and acted.json()["queue_state"] == "answered", acted.text
        assert restarted.app.state.webhooks.wait()
    assert len(rows(restarted, "SELECT * FROM handoff_cases")) == 1


def add_case(conn, case_id, *, created_at="2026-10-26T10:00:00-03:00", channel="api", ticket_id=None, state="open",
             thread_id="req_thread"):
    conn.execute(
        "INSERT INTO handoff_cases (case_id, protocol, customer_id, idempotency_key, reason, payload, created_at, "
        "conversation_id, queue_state, channel, thread_id, ticket_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (case_id, f"HO-{case_id}", "cliente1988", f"key-{case_id}", "human_requested",
         json.dumps({"summary": "s", "pending_question": "q", "draft_reply": "d", "language": "pt-BR"}),
         created_at, None, state, channel, thread_id, ticket_id),
    )


def test_recover_orphans_picks_only_cases_no_ticketing_knows(settings):
    conn = connect(settings.db_path)
    try:
        add_case(conn, "hc_orphan")
        add_case(conn, "hc_young", created_at="2026-11-07T11:59:30+00:00")
        add_case(conn, "hc_ticketed", ticket_id="tkt_1")
        add_case(conn, "hc_claimed", state="claimed")
        add_case(conn, "hc_cli", channel="in_process")
        add_case(conn, "hc_old", thread_id=None)  # opened before v0.7.0: no saved flow, never announced
        add_case(conn, "hc_unsaved", thread_id="req_unsaved")  # its turn stopped before the flow was saved
        add_case(conn, "hc_assigned")
        conn.execute(
            "INSERT INTO webhook_inbox (event_id, source, event, case_id, status_code, response, received_at) "
            "VALUES ('evt_in','ticketing','ticket.assigned','hc_assigned',200,'{}','t')"
        )
        from datetime import UTC, datetime

        now = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
        checked: list[str] = []

        def saved(thread_id: str) -> bool:
            checked.append(thread_id)
            return thread_id != "req_unsaved"

        assert handoffs.recover_orphans(conn, set(), saved, now=now) == []  # no destination: nothing to send
        assert handoffs.recover_orphans(conn, {"merchant"}, saved, now=now) == []  # the merchant gets no creation
        assert handoffs.recover_orphans(conn, {"ticketing", "merchant"}, saved, now=now) == ["hc_orphan"]
        assert sorted(checked) == ["req_thread", "req_unsaved"]  # only cases past every other filter are looked up
        [intention] = conn.execute("SELECT event, target, case_id, body FROM webhook_outbox").fetchall()
        assert tuple(intention)[:3] == ("handoff.created", "ticketing", "hc_orphan")
        assert json.loads(intention["body"])["data"]["pending_question"] == "q"
        assert handoffs.recover_orphans(conn, {"ticketing"}, saved, now=now) == []  # it has its intention now
        later = datetime(2026, 11, 7, 12, 5, tzinfo=UTC)  # the young case is past the grace period now
        assert handoffs.recover_orphans(conn, {"ticketing"}, saved, now=later) == ["hc_young"]
    finally:
        conn.close()


# --- D4 inside one process -----------------------------------------------------------------------------------------


def test_actions_on_a_case_are_serialized_by_sqlite_without_a_lock_in_memory(wired, monkeypatch):
    client, receivers = wired()
    response = client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client))
    assert client.app.state.webhooks.wait()
    case_id = rows(client, "SELECT case_id FROM handoff_cases WHERE thread_id=?", (response.json()["request_id"],))
    case_id = case_id[0]["case_id"]
    assert not hasattr(handoffs, "_CASE_LOCKS")
    real_connect = sqlite3.connect

    def quick_lock(path, *args, **kwargs):  # the lock files wait 5 s by default: shorten it for the test
        return real_connect(path, *args, **(kwargs | {"timeout": 0.2} if ".case-lock-" in str(path) else kwargs))

    monkeypatch.setattr(sqlite3, "connect", quick_lock)
    held, release = threading.Event(), threading.Event()

    def hold() -> None:  # another thread of this process is acting on the case
        conn = connect(client.app.state.settings.db_path)
        try:
            with handoffs._case_lock(conn, case_id):
                held.set()
                release.wait(timeout=30)
        finally:
            conn.close()

    other = threading.Thread(target=hold, daemon=True)
    other.start()
    conn = connect(client.app.state.settings.db_path)
    try:
        assert held.wait(timeout=30)
        with pytest.raises(handoffs.HandoffError) as busy:
            handoffs.act(conn, case_id, "op_ana", "approve", None, "lock-thread-key-1", actor="service:ticketing")
        assert (busy.value.status, busy.value.code) == (503, "resume_failed")
        release.set()
        other.join(timeout=30)
        done = handoffs.act(conn, case_id, "op_ana", "approve", None, "lock-thread-key-1", actor="service:ticketing")
        assert done["queue_state"] == "answered"
    finally:
        release.set()
        conn.close()


def test_the_database_opens_in_wal_mode(settings):
    conn = connect(settings.db_path)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        conn.close()
    raw = sqlite3.connect(settings.db_path)  # the mode is kept in the file
    try:
        assert raw.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        raw.close()
    memory = connect(":memory:")
    try:
        assert memory.execute("PRAGMA journal_mode").fetchone()[0] == "memory"
    finally:
        memory.close()
