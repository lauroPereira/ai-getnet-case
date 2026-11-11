"""v1.1.0 task 113 (D4, CA-79): the operator's own reply reaches the merchant exactly as written, with no Personality
and no rewriting; an approved draft still passes through the Personality; the merchant's webhook copy goes through the
masking of sensitive data. Also: support.v11 describes the ticket state in the merchant's language and lists each
answered ticket with the attendant's reply (CA-76); the access log keeps the path of `/v1/auth/authorize` without its
query.
Scripted model, no network, no cost."""

from __future__ import annotations

import json
import logging
import sqlite3

import httpx
from pydantic import SecretStr
from uvicorn.protocols.utils import get_path_with_query_string

from merchant_assistant.api.identity import Principal
from merchant_assistant.api.webhooks import Webhooks
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import MAIN_CUSTOMER
from merchant_assistant.evaluation.scripted_policy import handler as default_handler
from merchant_assistant.observability import logging as app_logging
from merchant_assistant.testing import merchant_headers, token_headers
from merchant_assistant.tools.base import CustomerContext, ToolEnv
from merchant_assistant.tools.registry import execute

HUMAN = "Quero falar com um atendente"
# Amounts, a percentage and dates no tool returned: only the operator wrote them.
REPLY = "Seu estorno de R$ 150,00 foi aprovado e cai na conta em 12/11. A taxa de 2,5% volta a valer em 01/12."
ADDED = "Os créditos ainda não estão confirmados."
DRAFT = "Nossa equipe analisou o seu caso e vai responder por aqui."  # escalation draft of the scripted model
MERCHANT_WEBHOOK = "http://merchant.test/merchant/events"


def rewriting_handler(call):
    """A Personality that rewrites a human agent's text (adds a sentence the agent never wrote)."""
    if call.spec.agent == "personality" and (call.spec.context["contributions"].get("operator") or {}).get("text"):
        return {"answer": f"{call.spec.context['contributions']['operator']['text']} {ADDED}"}
    return default_handler(call)


def operator(client):
    return token_headers(client, Principal.operator("op_ana"))


def hand_off(client) -> dict:
    response = client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client, MAIN_CUSTOMER))
    assert response.status_code == 200 and response.json()["status"] == "handoff", response.text
    protocol = response.json()["handoff"]["protocol"]
    cases = client.get("/v1/handoffs", headers=operator(client)).json()["cases"]
    return next(c for c in cases if c["protocol"] == protocol)


def act(client, case_id, action, key, text=None):
    body = {"action": action, "idempotency_key": key} | ({"text": text} if text else {})
    response = client.post(f"/v1/handoffs/{case_id}/actions", headers=operator(client), json=body)
    assert response.status_code == 200 and response.json()["resume_status"] == "done", response.text
    return response.json()


def last_operator_turn(client, conversation_id) -> dict:
    response = client.get(f"/v1/conversations/{conversation_id}", headers=merchant_headers(client, MAIN_CUSTOMER))
    assert response.status_code == 200, response.text
    return [t for t in response.json()["messages"] if t.get("via") == "operator"][-1]


def resume_trace(orchestrator, settings, case_id) -> dict:
    with sqlite3.connect(settings.db_path) as db:
        resume_id = db.execute("SELECT resume_request_id FROM handoff_cases WHERE case_id=?", (case_id,)).fetchone()[0]
    return orchestrator.trace(resume_id)


# --- D4: reply as written, approve through the Personality --------------------------------------------------------


def test_the_operators_reply_reaches_the_merchant_exactly_as_written(offline, settings):
    client, orchestrator, llm = offline(handler=rewriting_handler)
    case = hand_off(client)
    calls_before = len(llm.calls)
    record = act(client, case["case_id"], "reply", "key-verbatim-0001", REPLY)
    assert record["queue_state"] == "answered" and record["case_state"] == "awaiting_customer"
    assert len(llm.calls) == calls_before  # no model call at all in the resume: no Personality, no rewriting
    trace = resume_trace(orchestrator, settings, case["case_id"])
    assert [s["step"] for s in trace["steps"]] == ["human_review", "operator_reply"]
    assert trace["detail"]["output_violations"] == []

    turn = last_operator_turn(client, case["conversation_id"])  # GET /v1/conversations/{id}
    assert turn["text"] == REPLY and turn["operator_action"] == "reply" and turn["route"] == "human_reply"

    body = {
        "message": "E aí?", "conversation_id": case["conversation_id"],
        "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm",
    }
    sent = client.post("/v1/messages", json=body, headers=merchant_headers(client, MAIN_CUSTOMER))
    assert sent.status_code == 200, sent.text
    delivered = sent.json()["message"]  # the API's answer to the merchant's next message
    assert delivered["answer"] == REPLY and delivered["via"] == "operator" and delivered["route"] == "human_reply"

    conn = connect(settings.db_path)  # the ticket the merchant reads in any conversation (get_handoff_cases)
    try:
        clock = FixedClock("2026-11-11T10:00:00")
        merchant = CustomerContext.for_principal(Principal.merchant(MAIN_CUSTOMER), MAIN_CUSTOMER, True)
        cases = execute("get_handoff_cases", {}, ToolEnv(conn, clock, merchant)).data["cases"]
        ticket = next(c for c in cases if c["protocol"] == case["protocol"])
    finally:
        conn.close()
    assert ticket["operator_reply"] == REPLY and ADDED not in ticket["operator_reply"]


def test_an_approved_draft_still_passes_through_the_personality(offline, settings):
    client, orchestrator, llm = offline(handler=rewriting_handler)
    case = hand_off(client)
    calls_before = len(llm.calls)
    act(client, case["case_id"], "approve", "key-approve-d4-01")
    assert [c.spec.agent for c in llm.calls[calls_before:]] == ["personality"]
    trace = resume_trace(orchestrator, settings, case["case_id"])
    assert [s["step"] for s in trace["steps"]] == ["human_review", "personality", "output_guard"]
    assert last_operator_turn(client, case["conversation_id"])["text"] == f"{DRAFT} {ADDED}"


# --- the merchant's webhook copy ------------------------------------------------------------------------------------


def _replied_to_merchant(offline, settings, key: str, text: str) -> tuple[dict, dict]:
    """(case, `data` of the `conversation.replied` event the merchant's webhook received) after a `reply`."""
    settings.conversation_webhook_url = MERCHANT_WEBHOOK
    settings.conversation_webhook_secret = SecretStr("test-conversation-webhook-secret")
    client, _, _ = offline(handler=rewriting_handler)
    received: list[httpx.Request] = []

    def receiver(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return httpx.Response(200, json={"status": "received"})

    client.app.state.webhooks = Webhooks(settings, transport=httpx.MockTransport(receiver), sleep=lambda _: None)
    case = hand_off(client)
    act(client, case["case_id"], "reply", key, text)
    client.app.state.webhooks.wait()
    events = [json.loads(r.content) for r in received]
    replied = [e for e in events if e["type"] == "conversation.replied"]
    assert len(replied) == 1, events
    assert last_operator_turn(client, case["conversation_id"])["text"] == text  # the conversation keeps it whole
    return case, replied[0]["data"]


def test_the_merchants_webhook_carries_the_operators_plain_reply_as_written(offline, settings):
    case, data = _replied_to_merchant(offline, settings, "key-webhook-plain-01", REPLY)
    assert data["reply_text"] == REPLY and data["case_id"] == case["case_id"] and data["via"] == "operator"
    assert "operator_id" not in data


def test_the_merchants_webhook_masks_sensitive_data_in_the_operators_reply(offline, settings):
    text = "Para dúvidas, escreva para contato@exemplo.com.br."
    _, data = _replied_to_merchant(offline, settings, "key-webhook-mask-01", text)
    assert data["reply_text"] == "Para dúvidas, escreva para [e-mail removed]"
    assert "contato@exemplo.com.br" not in data["reply_text"]


# --- tickets in the merchant's language, with the attendant's reply -------------------------------------------------


def test_support_v11_describes_the_ticket_state_in_the_merchants_language_never_with_its_code():
    v11 = " ".join((PROJECT_ROOT / "prompts" / "support.v11.md").read_text(encoding="utf-8").split())
    assert (
        "Describe the state in words of $language_name, never with its code (`open`, `claimed`, `answered`, "
        "`rejected`, `closed`)." in v11
    )


def test_support_v11_lists_each_answered_ticket_with_the_attendants_reply_even_when_asked_only_about_open_ones():
    v11 = " ".join((PROJECT_ROOT / "prompts" / "support.v11.md").read_text(encoding="utf-8").split())
    assert (
        "When you list tickets, every ticket with `operator_reply` comes with that reply in the attendant's own "
        "words, never only its protocol; this holds also when the merchant asked only about open tickets." in v11
    )


# --- access log -----------------------------------------------------------------------------------------------------


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


def _access_line(path: str, query: bytes) -> str:
    """An access line written the way uvicorn writes it, through the `uvicorn.access` logger."""
    access = logging.getLogger("uvicorn.access")
    capture, level = _Capture(), access.level
    access.addHandler(capture)
    access.setLevel(logging.INFO)
    try:
        scope = {"path": path, "query_string": query}
        access.info('%s - "%s %s HTTP/%s" %d', "127.0.0.1:5000", "GET", get_path_with_query_string(scope), "1.1", 200)
    finally:
        access.removeHandler(capture)
        access.setLevel(level)
    return capture.lines[-1]


def test_the_access_log_keeps_the_authorize_path_without_its_query():
    merchant_logger = logging.getLogger("merchant_assistant")
    access = logging.getLogger("uvicorn.access")
    saved = (merchant_logger.handlers[:], merchant_logger.level, merchant_logger.propagate, access.filters[:])
    try:
        app_logging.configure_logging("INFO")
        app_logging.configure_logging("INFO")  # once per worker: never a second filter
        assert sum(isinstance(f, app_logging.AuthorizeQueryFilter) for f in access.filters) == 1
        query = b"response_type=code&client_id=merchant-assistant-web&state=st4te-xyz&code_challenge=ch4llenge-abc"
        line = _access_line("/v1/auth/authorize", query)
        assert line == '127.0.0.1:5000 - "GET /v1/auth/authorize HTTP/1.1" 200'
        assert "st4te-xyz" not in line and "ch4llenge-abc" not in line
        assert "?limit=5" in _access_line("/v1/conversations", b"limit=5")  # other paths keep their query
    finally:
        merchant_logger.handlers, merchant_logger.propagate = saved[0], saved[2]
        merchant_logger.setLevel(saved[1])
        access.filters = saved[3]
