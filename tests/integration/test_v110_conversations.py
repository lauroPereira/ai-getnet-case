"""v1.1.0 task 110 (D2, CA-77, RF-131): `GET /v1/conversations` lists the token's merchant's conversations, latest
activity first, without message text, so the interface can resume the last one. Scripted model, no network, no cost."""

from __future__ import annotations

import json

import pytest

from merchant_assistant.api.identity import Principal
from merchant_assistant.conversations import ConversationStore
from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import MAIN_CUSTOMER, OTHER_CUSTOMER
from merchant_assistant.testing import merchant_headers, token_headers

CLOCK = FixedClock("2026-11-10T10:00:00")
HUMAN = "Quero falar com um atendente"
REPLY = "Seu repasse foi enviado hoje às 10:00."
ITEM_KEYS = {
    "conversation_id", "state", "created_at", "updated_at", "handoff_protocol", "pending_operator_reply"
}


def add_conversation(settings, conversation_id, customer, updated_at, *, text="Texto sintético da conversa"):
    """A conversation with one merchant turn, written straight to the app's database."""
    conn = connect(settings.db_path)
    try:
        with conn:
            conn.execute(
                "INSERT INTO conversations (conversation_id, customer_id, state, technical_cycles, created_at, "
                "updated_at) VALUES (?,?,?,?,?,?)",
                (conversation_id, customer, "awaiting_customer", 0, "2026-11-01T08:00:00-03:00", updated_at),
            )
            conn.execute(
                "INSERT INTO messages (conversation_id, request_id, role, text, route, status, tokens, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (conversation_id, "req_synthetic", "merchant", text, "support", None, 5, updated_at),
            )
    finally:
        conn.close()


def listed(client, headers, **params):
    response = client.get("/v1/conversations", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()["conversations"]


def test_only_the_owners_conversations_latest_first_without_text(offline, settings):
    client, _, _ = offline()
    add_conversation(settings, "conv_older0000000001", MAIN_CUSTOMER, "2026-11-02T10:00:00-03:00")
    add_conversation(settings, "conv_newest000000001", MAIN_CUSTOMER, "2026-11-05T10:00:00-03:00",
                     text="Segredo da conversa mais recente")
    add_conversation(settings, "conv_middle000000001", MAIN_CUSTOMER, "2026-11-03T10:00:00-03:00")
    add_conversation(settings, "conv_otherxx00000001", OTHER_CUSTOMER, "2026-11-09T10:00:00-03:00")

    response = client.get("/v1/conversations", headers=merchant_headers(client, MAIN_CUSTOMER))
    assert response.status_code == 200, response.text
    items = response.json()["conversations"]
    assert [i["conversation_id"] for i in items] == [
        "conv_newest000000001", "conv_middle000000001", "conv_older0000000001"
    ]
    assert all(set(i) == ITEM_KEYS for i in items)
    assert items[0] == {
        "conversation_id": "conv_newest000000001", "state": "awaiting_customer",
        "created_at": "2026-11-01T08:00:00-03:00", "updated_at": "2026-11-05T10:00:00-03:00",
        "handoff_protocol": None, "pending_operator_reply": False,
    }
    assert "Segredo" not in response.text and "Texto sintético" not in response.text
    assert OTHER_CUSTOMER not in response.text and "conv_otherxx00000001" not in response.text

    other = listed(client, merchant_headers(client, OTHER_CUSTOMER))
    assert [i["conversation_id"] for i in other] == ["conv_otherxx00000001"]
    assert listed(client, merchant_headers(client, "cliente_sem_conversa")) == []


def test_limit_defaults_to_five_and_accepts_one_to_twenty(offline, settings):
    client, _, _ = offline()
    for n in range(22):
        add_conversation(settings, f"conv_limit{n:010d}", MAIN_CUSTOMER, f"2026-11-01T10:{n:02d}:00-03:00")
    headers = merchant_headers(client, MAIN_CUSTOMER)
    default = listed(client, headers)
    assert [i["conversation_id"] for i in default] == [f"conv_limit{n:010d}" for n in (21, 20, 19, 18, 17)]
    assert len(listed(client, headers, limit=1)) == 1
    assert len(listed(client, headers, limit=20)) == 20


@pytest.mark.parametrize("limit", ["0", "21", "-1", "abc"])
def test_limit_out_of_range_is_422(offline, limit):
    client, _, _ = offline()
    response = client.get(
        "/v1/conversations", headers=merchant_headers(client, MAIN_CUSTOMER), params={"limit": limit}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request" and "limit" in response.json()["error"]["message"]


@pytest.mark.parametrize("principal", [Principal.operator("op_ana"), Principal.of("service", "ticketing")])
def test_operator_and_service_get_403(offline, principal):
    client, _, _ = offline()
    response = client.get("/v1/conversations", headers=token_headers(client, principal))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_scope"
    assert 'error="insufficient_scope"' in response.headers["WWW-Authenticate"]


def test_no_token_is_401(offline):
    client, _, _ = offline()
    assert client.get("/v1/conversations").status_code == 401


def test_demo_and_admin_list_the_demo_merchants_conversations(offline, settings):
    """Same rule as the conversation by id (`acting_merchant`): demo has the merchant of its token; admin acts on the
    demo's synthetic merchant."""
    client, _, _ = offline()
    add_conversation(settings, "conv_demo00000000001", settings.api_demo_customer_id, "2026-11-05T10:00:00-03:00")
    add_conversation(settings, "conv_otherxx00000001", OTHER_CUSTOMER, "2026-11-06T10:00:00-03:00")
    demo = Principal.of("demo", "default", settings.api_demo_customer_id)
    for principal in (demo, Principal.of("admin", "default")):
        items = listed(client, token_headers(client, principal))
        assert [i["conversation_id"] for i in items] == ["conv_demo00000000001"]


def operator(client):
    return token_headers(client, Principal.operator("op_ana"))


def test_protocol_and_pending_reply_follow_the_case_and_the_delivery(offline):
    client, _, _ = offline()
    headers = merchant_headers(client, MAIN_CUSTOMER)
    first = client.post("/messages", json={"message": "Quando recebo minhas vendas?"}, headers=headers).json()
    handoff = client.post("/messages", json={"message": HUMAN}, headers=headers).json()
    assert handoff["status"] == "handoff", handoff
    protocol = handoff["handoff"]["protocol"]

    items = {i["conversation_id"]: i for i in listed(client, headers)}
    assert items[handoff["conversation_id"]]["handoff_protocol"] == protocol
    assert items[first["conversation_id"]]["handoff_protocol"] is None
    assert not any(i["pending_operator_reply"] for i in items.values())

    case = next(c for c in client.get("/v1/handoffs", headers=operator(client)).json()["cases"]
                if c["protocol"] == protocol)
    body = {"action": "reply", "idempotency_key": "key-resume-reply-01", "text": REPLY}
    replied = client.post(f"/v1/handoffs/{case['case_id']}/actions", headers=operator(client), json=body)
    assert replied.status_code == 200, replied.text
    items = {i["conversation_id"]: i for i in listed(client, headers)}
    assert items[handoff["conversation_id"]]["pending_operator_reply"] is True
    assert REPLY not in json.dumps(items)

    # the conversation by id still carries the whole history, the attendant's turn included
    whole = client.get(f"/v1/conversations/{handoff['conversation_id']}", headers=headers).json()
    assert whole["messages"][-1]["via"] == "operator" and whole["messages"][-1]["text"] == REPLY

    delivered = client.post(
        "/messages", json={"message": "Alguma novidade?", "conversation_id": handoff["conversation_id"]},
        headers=headers,
    ).json()
    assert delivered["via"] == "operator"
    items = {i["conversation_id"]: i for i in listed(client, headers)}
    assert items[handoff["conversation_id"]]["pending_operator_reply"] is False


FOLLOW_UP = "E quando cai na conta?"


def send_v1(client, headers, message, conversation_id, **extra):
    body = {"message": message, "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm",
            "conversation_id": conversation_id} | extra
    response = client.post("/v1/messages", headers=headers, json=body)
    assert response.status_code == 200, response.text
    return response.json()["message"]


def add_operator_turn(settings, conversation_id, text, *, delivered=False) -> int:
    """An attendant's turn written straight to the app's database; returns its `message_id`."""
    conn = connect(settings.db_path)
    try:
        with conn:
            message_id = ConversationStore(conn, CLOCK).append(
                conversation_id, "req_resume_synthetic", "assistant", text, "human_reply", "answered",
                via="operator", meta={"action": "reply", "protocol": "HO-20261110-SYN001"},
            )
            if delivered:
                ConversationStore(conn, CLOCK).mark_delivered(message_id)
        return message_id
    finally:
        conn.close()


def pending_ids(settings, conversation_id) -> list[int]:
    conn = connect(settings.db_path)
    try:
        return [r[0] for r in conn.execute(
            "SELECT id FROM messages WHERE conversation_id=? AND via='operator' AND delivered_at IS NULL ORDER BY id",
            (conversation_id,),
        )]
    finally:
        conn.close()


def test_a_displayed_reply_counts_as_delivered_and_the_next_message_is_answered(offline):
    """CA-77: after resuming, the interface sends the `message_id` of the attendant's turn it showed; the merchant's
    next message gets its own answer and the reply is not repeated, neither on screen nor in the history."""
    client, _, _ = offline()
    headers = merchant_headers(client, MAIN_CUSTOMER)
    handoff = client.post("/messages", json={"message": HUMAN}, headers=headers).json()
    conversation_id = handoff["conversation_id"]
    case = next(c for c in client.get("/v1/handoffs", headers=operator(client)).json()["cases"]
                if c["protocol"] == handoff["handoff"]["protocol"])
    body = {"action": "reply", "idempotency_key": "key-resume-shown-01", "text": REPLY}
    replied = client.post(f"/v1/handoffs/{case['case_id']}/actions", headers=operator(client), json=body)
    assert replied.status_code == 200, replied.text

    whole = client.get(f"/v1/conversations/{conversation_id}", headers=headers).json()
    ids = [m["message_id"] for m in whole["messages"]]
    assert all(isinstance(i, int) for i in ids) and ids == sorted(set(ids))  # stable, one per turn, in order
    shown = whole["messages"][-1]
    assert shown["via"] == "operator" and shown["text"] == REPLY

    answered = send_v1(client, headers, FOLLOW_UP, conversation_id, displayed_operator_message_id=shown["message_id"])
    assert answered["route"] != "human_reply" and answered["via"] == "agent" and answered["answer"] != REPLY
    assert answered["conversation_id"] == conversation_id
    assert listed(client, headers)[0]["pending_operator_reply"] is False

    after = client.get(f"/v1/conversations/{conversation_id}", headers=headers).json()["messages"]
    assert [m["text"] for m in after].count(REPLY) == 1
    assert [m["message_id"] for m in after[: len(ids)]] == ids  # the ids already shown do not change
    assert [(m["role"], m["text"]) for m in after[len(ids):]][0] == ("merchant", FOLLOW_UP)
    assert after[-1]["role"] == "assistant" and after[-1]["via"] == "agent"


def test_without_the_field_the_pending_reply_is_delivered_as_before(offline, settings):
    client, _, _ = offline()
    headers = merchant_headers(client, MAIN_CUSTOMER)
    add_conversation(settings, "conv_plain0000000001", MAIN_CUSTOMER, "2026-11-05T10:00:00-03:00")
    add_operator_turn(settings, "conv_plain0000000001", REPLY)
    delivered = send_v1(client, headers, FOLLOW_UP, "conv_plain0000000001")
    assert (delivered["route"], delivered["via"], delivered["answer"]) == ("human_reply", "operator", REPLY)
    assert pending_ids(settings, "conv_plain0000000001") == []


def test_a_newer_reply_than_the_displayed_one_is_still_delivered(offline, settings):
    """Race: the attendant writes again after the interface loaded the history. The shown turn counts as delivered; the
    newer one, never shown, is delivered by this message (D8) and then the next message is answered."""
    client, _, _ = offline()
    headers = merchant_headers(client, MAIN_CUSTOMER)
    add_conversation(settings, "conv_race00000000001", MAIN_CUSTOMER, "2026-11-05T10:00:00-03:00")
    shown = add_operator_turn(settings, "conv_race00000000001", REPLY)
    newer = add_operator_turn(settings, "conv_race00000000001", "Complementando: o valor já foi conciliado.")

    delivered = send_v1(client, headers, FOLLOW_UP, "conv_race00000000001", displayed_operator_message_id=shown)
    assert (delivered["route"], delivered["answer"]) == ("human_reply", "Complementando: o valor já foi conciliado.")
    assert pending_ids(settings, "conv_race00000000001") == []

    # the newer id is already delivered now: sending it again changes nothing and the message is answered
    answered = send_v1(client, headers, "Obrigado", "conv_race00000000001", displayed_operator_message_id=newer)
    assert answered["route"] != "human_reply" and answered["via"] == "agent"


def test_older_undelivered_replies_shown_above_the_displayed_one_also_count_as_delivered(offline, settings):
    client, _, _ = offline()
    headers = merchant_headers(client, MAIN_CUSTOMER)
    add_conversation(settings, "conv_sibling00000001", MAIN_CUSTOMER, "2026-11-04T10:00:00-03:00")
    sibling = add_operator_turn(settings, "conv_sibling00000001", "Resposta de outra conversa.")  # older id
    add_conversation(settings, "conv_two000000000001", MAIN_CUSTOMER, "2026-11-05T10:00:00-03:00")
    add_operator_turn(settings, "conv_two000000000001", "Primeira resposta da atendente.")
    last = add_operator_turn(settings, "conv_two000000000001", REPLY)
    answered = send_v1(client, headers, FOLLOW_UP, "conv_two000000000001", displayed_operator_message_id=last)
    assert answered["route"] != "human_reply" and answered["via"] == "agent"
    assert pending_ids(settings, "conv_two000000000001") == []
    assert pending_ids(settings, "conv_sibling00000001") == [sibling]  # only this conversation's turns


@pytest.mark.parametrize("which", ["merchant_turn", "other_conversation", "other_merchant", "delivered", "unknown"])
def test_an_id_that_is_not_an_undelivered_reply_of_this_conversation_changes_nothing(offline, settings, which):
    client, _, _ = offline()
    headers = merchant_headers(client, MAIN_CUSTOMER)
    add_conversation(settings, "conv_mine00000000001", MAIN_CUSTOMER, "2026-11-05T10:00:00-03:00")
    pending = add_operator_turn(settings, "conv_mine00000000001", REPLY)
    add_conversation(settings, "conv_sibling00000001", MAIN_CUSTOMER, "2026-11-04T10:00:00-03:00")
    add_conversation(settings, "conv_otherxx00000001", OTHER_CUSTOMER, "2026-11-04T10:00:00-03:00")
    elsewhere = {
        "other_conversation": ("conv_sibling00000001", add_operator_turn(settings, "conv_sibling00000001", "Outra.")),
        "other_merchant": ("conv_otherxx00000001", add_operator_turn(settings, "conv_otherxx00000001", "Alheia.")),
    }
    if which == "merchant_turn":  # written after the pending reply, so its id is the larger one
        conn = connect(settings.db_path)
        try:
            with conn:
                displayed = ConversationStore(conn, CLOCK).append(
                    "conv_mine00000000001", "req_synthetic", "merchant", "Oi?", "support", None
                )
        finally:
            conn.close()
    elif which == "delivered":
        displayed = add_operator_turn(settings, "conv_mine00000000001", "Já entregue.", delivered=True)
    elif which == "unknown":
        displayed = 999_999
    else:
        displayed = elsewhere[which][1]

    delivered = send_v1(client, headers, FOLLOW_UP, "conv_mine00000000001", displayed_operator_message_id=displayed)
    assert (delivered["route"], delivered["answer"]) == ("human_reply", REPLY)  # D8, as without the field
    assert pending_ids(settings, "conv_mine00000000001") == []  # delivered by D8, not by the confirmation
    for conversation_id, message_id in elsewhere.values():
        assert pending_ids(settings, conversation_id) == [message_id]  # untouched
    assert pending < displayed or which in ("other_conversation", "other_merchant")


@pytest.mark.parametrize("value", [0, -1, "abc"])
def test_an_invalid_displayed_id_is_422(offline, value):
    client, _, _ = offline()
    response = client.post("/v1/messages", headers=merchant_headers(client, MAIN_CUSTOMER), json={
        "message": FOLLOW_UP, "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm",
        "displayed_operator_message_id": value,
    })
    assert response.status_code == 422 and response.json()["error"]["code"] == "invalid_request"


def test_openapi_documents_the_route_with_bounds_and_an_example(offline):
    client, _, _ = offline()
    spec = client.get("/openapi.json").json()
    route = spec["paths"]["/v1/conversations"]["get"]
    assert route["security"] == [{"SessionBearer": []}]
    assert {"200", "401", "403", "422"} <= set(route["responses"])
    limit = next(p for p in route["parameters"] if p["name"] == "limit")
    assert (limit["in"], limit["schema"]["minimum"], limit["schema"]["maximum"], limit["schema"]["default"]) == (
        "query", 1, 20, 5
    )
    schemas = spec["components"]["schemas"]
    assert set(schemas["ConversationSummary"]["properties"]) == ITEM_KEYS
    example = schemas["ConversationList"]["examples"][0]["conversations"][0]
    assert set(example) == ITEM_KEYS  # no message text: the whole conversation is the route by id
    displayed = schemas["V1MessageRequest"]["properties"]["displayed_operator_message_id"]
    assert "displayed_operator_message_id" not in schemas["V1MessageRequest"].get("required", [])
    assert {"type": "integer", "minimum": 1} in displayed["anyOf"]
