"""v0.8.0 task 68b (observation O-8 of the v0.7.0 QA): the case keeps the `ticket_id` of the ticket that works it.

The real ticketing service (`merchant_assistant.ticketing`) and the assistant talk in process over HTTP; the operator
works the ticket on the ticketing API. Scripted model, no network, no cost."""

from __future__ import annotations

import json
import sqlite3
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant.api.identity import Principal
from merchant_assistant.api.webhooks import Webhooks, signature
from merchant_assistant.mocks.service import create_mocks_app
from merchant_assistant.testing import TEST_TICKETING_SECRET, AppTransport, merchant_headers, token_headers
from merchant_assistant.ticketing.config import TicketingSettings
from merchant_assistant.ticketing.service import create_app as create_ticketing_app

ASSISTANT, TICKETING, MERCHANT = "assistant.test", "ticketing.test", "merchant.test"
TICKETING_SECRET, ASSISTANT_SECRET, CONVERSATION_SECRET = "t68b-ticketing", "t68b-assistant", "t68b-conversation"
HUMAN = "Quero falar com um atendente"
EVENTS_PATH = "/v1/integrations/ticketing/events"


@pytest.fixture
def system(offline, settings, tmp_path):
    settings.ticketing_webhook_url = f"http://{TICKETING}/webhooks/assistant"
    settings.ticketing_webhook_secret = SecretStr(TICKETING_SECRET)
    settings.conversation_webhook_url = f"http://{MERCHANT}/merchant/events"
    settings.conversation_webhook_secret = SecretStr(CONVERSATION_SECRET)
    settings.assistant_webhook_secret = SecretStr(ASSISTANT_SECRET)
    assistant, _, _ = offline()
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
    return assistant, ticketing, webhooks


def operator(assistant, name="op_ana"):
    return token_headers(assistant, Principal.operator(name))


def new_ticket(assistant, ticketing, webhooks) -> dict:
    """A merchant asks for a human: the assistant opens the case and the ticketing opens the ticket."""
    sent = assistant.post("/messages", json={"message": HUMAN}, headers=merchant_headers(assistant))
    assert sent.status_code == 200 and sent.json()["status"] == "handoff", sent.text
    assert webhooks.wait()
    [ticket] = ticketing.get("/tickets", params={"status": "new"}, headers=operator(assistant)).json()["tickets"]
    return ticket


def ticket_ids(assistant, case_id) -> tuple[str | None, str | None]:
    """The case as the operator reads it: in the queue (`GET /v1/handoffs`) and in the detail."""
    headers = operator(assistant)
    listed = [c for c in assistant.get("/v1/handoffs", headers=headers).json()["cases"] if c["case_id"] == case_id]
    detail = assistant.get(f"/v1/handoffs/{case_id}", headers=headers).json()
    assert len(listed) == 1
    return listed[0]["ticket_id"], detail["ticket_id"]


def stored_ticket_id(assistant, case_id) -> str | None:
    conn = sqlite3.connect(assistant.app.state.settings.db_path)
    try:
        return conn.execute("SELECT ticket_id FROM handoff_cases WHERE case_id=?", (case_id,)).fetchone()[0]
    finally:
        conn.close()


def first_event(ticketing, assistant, ticket_id, kind):
    """The operator's first act on the ticket: `assigned`, `action` (reply) or `solved`."""
    ana = operator(assistant)
    if kind == "assigned":
        return ticketing.post(f"/tickets/{ticket_id}/assign", headers=ana)
    if kind == "action":
        body = {"action": "reply", "text": "Seu repasse cai amanhã.", "idempotency_key": "t68b-reply-0001"}
        return ticketing.post(f"/tickets/{ticket_id}/actions", headers=ana, json=body)
    return ticketing.post(f"/tickets/{ticket_id}/solve", headers=ana)


@pytest.mark.parametrize("kind", ["assigned", "action", "solved"])
def test_ticket_id_is_in_the_queue_and_in_the_detail_after_the_first_accepted_event(system, kind):
    assistant, ticketing, webhooks = system
    ticket = new_ticket(assistant, ticketing, webhooks)
    case_id, ticket_id = ticket["case_id"], ticket["ticket_id"]
    assert ticket_ids(assistant, case_id) == (None, None)  # no event accepted yet: nothing to record

    response = first_event(ticketing, assistant, ticket_id, kind)
    assert response.status_code == 200, response.text
    assert response.json()["delivery"]["assistant"]["status"] == "accepted"
    webhooks.wait()
    assert ticket_ids(assistant, case_id) == (ticket_id, ticket_id)
    assert stored_ticket_id(assistant, case_id) == ticket_id


def test_the_ticket_id_follows_the_whole_cycle_and_the_first_one_wins(system):
    assistant, ticketing, webhooks = system
    ticket = new_ticket(assistant, ticketing, webhooks)
    case_id, ticket_id = ticket["case_id"], ticket["ticket_id"]
    ana = operator(assistant)
    assert ticketing.post(f"/tickets/{ticket_id}/assign", headers=ana).status_code == 200
    body = {"action": "approve", "text": "", "idempotency_key": "t68b-approve-01"}
    assert ticketing.post(f"/tickets/{ticket_id}/actions", headers=ana, json=body).status_code == 200
    assert ticketing.post(f"/tickets/{ticket_id}/solve", headers=ana).status_code == 200
    webhooks.wait()
    assert ticket_ids(assistant, case_id) == (ticket_id, ticket_id)
    assert assistant.get(f"/v1/handoffs/{case_id}", headers=ana).json()["queue_state"] == "closed"


def signed_event(event_type: str, data: dict) -> tuple[bytes, dict]:
    event = {"id": f"evt_t68b_{time.time_ns()}", "type": event_type, "created_at": "2026-11-04T12:00:00Z"}
    body = json.dumps(event | {"data": data}).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Id": event["id"],
        "X-Webhook-Event": event_type,
        "X-Signature": signature(ASSISTANT_SECRET, body, int(time.time())),
    }
    return body, headers


def post_event(assistant, event_type, case_id, operator_id, ticket_id="tkt_t68b"):
    data = {"ticket_id": ticket_id, "case_id": case_id, "operator_id": operator_id}
    body, headers = signed_event(event_type, data)
    auth = token_headers(assistant, Principal.of("service", "ticketing"))
    return assistant.post(EVENTS_PATH, content=body, headers=headers | auth)


def test_a_refused_event_does_not_record_the_ticket_id(system):
    assistant, ticketing, webhooks = system
    ticket = new_ticket(assistant, ticketing, webhooks)
    case_id = ticket["case_id"]
    ana, bruno = "op_ana", "op_bruno"

    # refused before any change: unknown operator and missing fields
    unknown = post_event(assistant, "ticket.assigned", case_id, "op_nobody")
    assert unknown.status_code == 422 and unknown.json()["error"]["code"] == "unknown_operator"
    body, headers = signed_event("ticket.assigned", {"case_id": case_id, "operator_id": ana})  # no ticket_id
    auth = token_headers(assistant, Principal.of("service", "ticketing"))
    assert assistant.post(EVENTS_PATH, content=body, headers=headers | auth).status_code == 400
    assert stored_ticket_id(assistant, case_id) is None

    # the case belongs to Bruno (claimed on the assistant): the ticketing's event for Ana is a 409 and writes nothing
    claimed = assistant.post(f"/v1/handoffs/{case_id}/claim", headers=operator(assistant, bruno))
    assert claimed.status_code == 200
    refused = post_event(assistant, "ticket.assigned", case_id, ana, "tkt_ana")
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "claimed_by_other"
    assert stored_ticket_id(assistant, case_id) is None

    # Bruno holds the case, so his event is accepted (as an idempotent claim) and records his ticket; a later accepted
    # event of another ticket does not overwrite it
    accepted = post_event(assistant, "ticket.assigned", case_id, bruno, "tkt_bruno")
    assert accepted.status_code == 200 and accepted.json()["status"] == "replayed"
    assert ticket_ids(assistant, case_id) == ("tkt_bruno", "tkt_bruno")
    again = post_event(assistant, "ticket.solved", case_id, bruno, "tkt_other")
    assert again.status_code == 200
    assert stored_ticket_id(assistant, case_id) == "tkt_bruno"
