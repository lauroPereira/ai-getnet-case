"""v0.7.0 task 66 (CA-47, CA-48) against the real ticketing service of task 66b, both in process.

The assistant, the ticketing (`merchant_assistant.ticketing`, unchanged) and the synthetic merchant receiver (`mocks`)
talk only over HTTP through a test transport that routes by host. The operator works the ticket on the ticketing API
with the JWT the assistant issues; the ticketing calls the assistant with its client-credentials token. Scripted
model, no network, no cost."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant.api.identity import Principal
from merchant_assistant.api.webhooks import Webhooks
from merchant_assistant.mocks.service import create_mocks_app
from merchant_assistant.testing import TEST_TICKETING_SECRET, AppTransport, merchant_headers, token_headers
from merchant_assistant.ticketing.config import TicketingSettings
from merchant_assistant.ticketing.service import create_app as create_ticketing_app

ASSISTANT, TICKETING, MERCHANT = "assistant.test", "ticketing.test", "merchant.test"
TICKETING_SECRET = "it-ticketing-webhook-secret"
ASSISTANT_SECRET = "it-assistant-webhook-secret"
CONVERSATION_SECRET = "it-conversation-webhook-secret"
HUMAN = "Quero falar com um atendente"


@pytest.fixture
def system(offline, settings, tmp_path):
    settings.ticketing_webhook_url = f"http://{TICKETING}/webhooks/assistant"
    settings.ticketing_webhook_secret = SecretStr(TICKETING_SECRET)
    settings.conversation_webhook_url = f"http://{MERCHANT}/merchant/events"
    settings.conversation_webhook_secret = SecretStr(CONVERSATION_SECRET)
    settings.assistant_webhook_secret = SecretStr(ASSISTANT_SECRET)
    assistant, orchestrator, _ = offline()
    ticketing_settings = TicketingSettings(
        db_path=tmp_path / "ticketing" / "ticketing.sqlite3",
        assistant_url=f"http://{ASSISTANT}",
        assistant_issuer=settings.jwt_issuer,
        assistant_jwks_url=f"http://{ASSISTANT}/.well-known/jwks.json",
        inbound_secret=TICKETING_SECRET,
        outbound_secret=ASSISTANT_SECRET,
        client_secret=TEST_TICKETING_SECRET,
        outbox_poll_s=0,  # no background loop in the test
    )
    apps: dict[str, TestClient] = {ASSISTANT: assistant}
    ticketing = TestClient(create_ticketing_app(ticketing_settings, client=httpx.Client(transport=AppTransport(apps))))
    merchant = TestClient(create_mocks_app(conversation_secret=CONVERSATION_SECRET))
    apps |= {TICKETING: ticketing, MERCHANT: merchant}
    webhooks = Webhooks(settings, transport=AppTransport(apps), sleep=lambda _s: None)
    assistant.app.state.webhooks = webhooks
    return assistant, ticketing, merchant, webhooks


def operator(assistant, name="op_ana"):
    """The operator's JWT issued by the assistant (audiences merchant-assistant and ticketing)."""
    return token_headers(assistant, Principal.operator(name))


def test_ticketing_preserves_refusal_when_first_assistant_response_is_lost(system):
    assistant, ticketing, _, webhooks = system
    sent = assistant.post("/messages", json={"message": HUMAN}, headers=merchant_headers(assistant))
    assert sent.status_code == 200
    assert webhooks.wait()
    ana, bruno = operator(assistant), operator(assistant, "op_bruno")
    [ticket] = ticketing.get("/tickets", headers=ana).json()["tickets"]
    ticket_id = ticket["ticket_id"]
    assert ticketing.post(f"/tickets/{ticket_id}/assign", headers=ana).status_code == 200
    transport = ticketing.app.state.dispatcher.client._transport
    original = transport.handle_request
    dropped = []

    def lose_first_response(request):
        response = original(request)
        if request.headers.get("x-webhook-event") == "ticket.assigned" and response.status_code == 409 and not dropped:
            dropped.append(1)
            raise httpx.ReadTimeout("response lost", request=request)
        return response

    transport.handle_request = lose_first_response
    first = ticketing.post(f"/tickets/{ticket_id}/assign", headers=bruno)
    assert first.status_code == 202 and first.json()["delivery"]["status"] == "pending"
    time.sleep(1.1)  # default first retry delay, without changing the outbox timestamps
    retried = ticketing.app.state.dispatcher.deliver(first.json()["delivery"]["event_id"])
    assert retried.status == "rejected" and retried.http_status == 409
    assert retried.response["error"]["code"] == "claimed_by_other"
    detail = ticketing.get(f"/tickets/{ticket_id}", headers=ana).json()
    assert detail["status"] == "open" and detail["assignee"] == "op_ana"


def test_ticketing_retries_action_after_actual_process_dies_without_aging_timestamp(system):
    assistant, ticketing, merchant, webhooks = system
    sent = assistant.post("/messages", json={"message": HUMAN}, headers=merchant_headers(assistant))
    assert sent.status_code == 200 and webhooks.wait()
    ana = operator(assistant)
    [ticket] = ticketing.get("/tickets", headers=ana).json()["tickets"]
    case_id, ticket_id = ticket["case_id"], ticket["ticket_id"]
    key = "crash-ticketing-action"
    script = (
        "import os, sys; from merchant_assistant.data.db import connect; "
        "from merchant_assistant.handoffs import act; conn=connect(sys.argv[1]); "
        "act(conn,sys.argv[2],'op_ana','approve',None,sys.argv[3],actor='service:ticketing',"
        "on_behalf_of='operator:op_ana',resume=lambda *_: os._exit(31))"
    )
    db_path = assistant.app.state.settings.db_path
    process = subprocess.run([sys.executable, "-c", script, str(db_path), case_id, key], check=False, timeout=20)
    assert process.returncode == 31
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT resume_status FROM handoff_cases WHERE case_id=?", (case_id,)).fetchone() == (
            "pending",
        )
    response = ticketing.post(
        f"/tickets/{ticket_id}/actions", headers=ana,
        json={"action": "approve", "text": "", "idempotency_key": key},
    )
    assert response.status_code == 200, response.text
    assert response.json()["delivery"]["assistant"]["queue_state"] == "answered"
    assert webhooks.wait()
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT resume_count, resume_status FROM handoff_cases WHERE case_id=?", (case_id,))\
            .fetchone() == (1, "done")
        assert conn.execute("SELECT COUNT(*) FROM messages WHERE via='operator'").fetchone()[0] == 1
    assert len(merchant.get("/merchant/events").json()["events"]) == 1


@pytest.mark.parametrize("action", ["approve", "reply", "reject"])
def test_case_becomes_a_ticket_worked_on_the_ticketing_and_closed(system, action):
    assistant, ticketing, merchant, webhooks = system
    ana = operator(assistant)
    sent = assistant.post("/messages", json={"message": HUMAN}, headers=merchant_headers(assistant))
    assert sent.status_code == 200 and sent.json()["status"] == "handoff", sent.text
    conversation_id, protocol = sent.json()["conversation_id"], sent.json()["handoff"]["protocol"]
    webhooks.wait()

    # handoff.created -> ticket `new`
    [new] = ticketing.get("/tickets", params={"status": "new"}, headers=ana).json()["tickets"]
    assert new["protocol"] == protocol and new["customer_id"] == "cliente1988" and new["draft_reply"]
    ticket_id, case_id = new["ticket_id"], new["case_id"]

    # assign -> ticket.assigned -> claimed in the assistant, ticket `open`
    assigned = ticketing.post(f"/tickets/{ticket_id}/assign", headers=ana)
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["delivery"]["assistant"]["status"] == "accepted"
    assert assigned.json()["ticket"]["status"] == "open" and assigned.json()["ticket"]["assignee"] == "op_ana"
    case = assistant.get(f"/v1/handoffs/{case_id}", headers=ana).json()
    assert (case["queue_state"], case["claimed_by"], case["ticket_id"]) == ("claimed", "op_ana", ticket_id)
    bruno = ticketing.post(f"/tickets/{ticket_id}/assign", headers=operator(assistant, "op_bruno"))
    assert bruno.status_code == 409 and bruno.json()["error"]["code"] == "claimed_by_other"  # passed through

    # action -> ticket.action -> resume -> conversation.replied to the ticket and the merchant, ticket `pending`
    text = {"approve": "", "reply": "Seu repasse cai amanhã.", "reject": "Verifique a maquininha."}[action]
    body = {"action": action, "text": text, "idempotency_key": f"it-{action}-0001"}
    acted = ticketing.post(f"/tickets/{ticket_id}/actions", headers=ana, json=body)
    assert acted.status_code == 200, acted.text
    answer = acted.json()["delivery"]["assistant"]
    expected_queue = "rejected" if action == "reject" else "answered"
    assert answer["status"] == "accepted" and answer["queue_state"] == expected_queue
    webhooks.wait()
    detail = ticketing.get(f"/tickets/{ticket_id}", headers=ana).json()
    assert detail["status"] == "pending" and detail["reply_text"] and detail["reply_delivered_at"]
    if action == "reply":
        assert text in detail["reply_text"]
    [to_merchant] = merchant.get("/merchant/events", params={"conversation_id": conversation_id}).json()["events"]
    assert to_merchant["type"] == "conversation.replied" and to_merchant["data"]["reply_text"] == detail["reply_text"]
    assert to_merchant["data"]["via"] == "operator" and to_merchant["data"]["action"] == action
    assert "operator_id" not in to_merchant["data"]  # D29; the ticket keeps who acted

    # the same act again: the ticketing replays its record; the assistant is not resumed twice (CA-48)
    again = ticketing.post(f"/tickets/{ticket_id}/actions", headers=ana, json=body)
    assert again.status_code == 200 and again.json()["delivery"]["replayed"] is True
    other = ticketing.post(f"/tickets/{ticket_id}/actions", headers=ana, json=body | {"idempotency_key": "it-other-01"})
    assert other.status_code == 409 and other.json()["error"]["code"] == "already_resumed"

    # the merchant's next message brings the operator's turn (D8), recorded apart from the webhook (D24)
    thanks = {"message": "Obrigado", "conversation_id": conversation_id}
    following = assistant.post("/messages", json=thanks, headers=merchant_headers(assistant))
    assert following.json()["route"] == "human_reply" and following.json()["answer"] == detail["reply_text"]

    # solve -> ticket.solved -> case closed -> handoff.closed back to the ticket
    solved = ticketing.post(f"/tickets/{ticket_id}/solve", headers=ana)
    assert solved.status_code == 200 and solved.json()["ticket"]["status"] == "solved", solved.text
    webhooks.wait()
    detail = ticketing.get(f"/tickets/{ticket_id}", headers=ana).json()
    assert detail["closed_by"] == "op_ana" and detail["closed_at"]
    case = assistant.get(f"/v1/handoffs/{case_id}", headers=ana).json()
    assert case["queue_state"] == "closed" and case["closed_at"]

    # deliveries recorded on both sides
    received = [d["event_type"] for d in detail["deliveries"]["received"]]
    assert received == ["handoff.created", "conversation.replied", "handoff.closed"]
    sent_events = [(d["event_type"], d["status"]) for d in detail["deliveries"]["sent"]]
    assert ("ticket.assigned", "delivered") in sent_events and ("ticket.solved", "delivered") in sent_events
    assert ("ticket.action", "delivered") in sent_events
    ours = sorted((d["event"], d["target"], d["status"]) for d in case["deliveries"])
    assert ours == [
        ("conversation.replied", "merchant", "delivered"),
        ("conversation.replied", "ticketing", "delivered"),
        ("handoff.closed", "ticketing", "delivered"),
        ("handoff.created", "ticketing", "delivered"),
    ]
