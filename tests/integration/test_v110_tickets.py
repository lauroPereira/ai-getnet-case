"""v1.1.0 task 109 (D1, CA-76, RF-130): the merchant reads their human support tickets (`get_handoff_cases`) in any
conversation: protocol, queue state and the attendant's reply. Scripted model, no network, no cost."""

from __future__ import annotations

import json
import sqlite3

import pytest

from merchant_assistant import handoffs
from merchant_assistant.api.identity import SUPPORT_READ, Principal
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.conversations import ConversationStore
from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import MAIN_CUSTOMER, OTHER_CUSTOMER, seed
from merchant_assistant.evaluation.scripted_policy import route_for, ticket_filter
from merchant_assistant.guardrails.output import unsupported
from merchant_assistant.llm.prompts import load_prompt, prompt_versions
from merchant_assistant.testing import merchant_headers, token_headers
from merchant_assistant.tools.base import CustomerContext, ToolEnv
from merchant_assistant.tools.domain import HANDOFF_CASES_LIMIT
from merchant_assistant.tools.registry import AGENT_TOOLS, TOOLS, execute, model_tool_schemas

PROMPTS = PROJECT_ROOT / "prompts"
CLOCK = FixedClock("2026-10-26T10:00:00")
HUMAN = "Quero falar com um atendente"
REPLY = "Seu estorno de R$ 150,00 foi aprovado e cai na conta em 12/11."
ANY_TICKET = "Tenho algum ticket aberto?"
# The scripted model guesses the language from common words (the real Router decides it): this one reads as Portuguese.
ANY_TICKET_PT = "Tenho algum ticket aberto com vocês?"


# --- the tool over the seeded database ----------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "db.sqlite3")
    seed(c, CLOCK)
    return c


def env(conn, customer=MAIN_CUSTOMER):
    return ToolEnv(conn, CLOCK, CustomerContext.for_principal(Principal.merchant(customer), customer, True))


def add_case(conn, protocol, *, customer=MAIN_CUSTOMER, created_at="2026-10-26T09:00:00", **columns) -> str:
    case_id = f"hc_{protocol[-6:].lower()}"
    conversation_id = ConversationStore(conn, CLOCK).open(f"conv_{case_id}", customer).conversation_id
    conn.execute(
        "INSERT INTO handoff_cases (case_id, protocol, customer_id, idempotency_key, reason, payload, created_at, "
        "conversation_id, queue_state, claimed_by, claimed_at, answered_at, closed_at, closed_by) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            case_id, protocol, customer, f"key-{case_id}", "customer_request", "{}", created_at, conversation_id,
            columns.get("state", "open"), columns.get("claimed_by"), columns.get("claimed_at"),
            columns.get("answered_at"), columns.get("closed_at"), columns.get("closed_by"),
        ),
    )
    return case_id


def add_operator_turn(conn, case_id, text, protocol):
    conn.execute(
        "INSERT INTO messages (conversation_id, request_id, role, text, route, status, tokens, created_at, via, meta) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (f"conv_{case_id}", "req_x", "assistant", text, "human_reply", "answered", 10, "2026-10-26T09:30:00",
         "operator", json.dumps({"action": "reply", "case_id": case_id, "protocol": protocol})),
    )


def test_the_tool_is_a_support_specialist_read_with_no_customer_field_and_also_over_mcp():
    spec = TOOLS["get_handoff_cases"]
    assert spec.scope == SUPPORT_READ and spec.phase == "specialist"
    assert "get_handoff_cases" in AGENT_TOOLS["customer_support"] and "get_handoff_cases" in AGENT_TOOLS["mcp"]
    schema = next(s for s in model_tool_schemas("customer_support") if s["name"] == "get_handoff_cases")
    assert set(schema["parameters"]["properties"]) == {"protocol"}
    assert schema["parameters"]["additionalProperties"] is False and not schema["parameters"].get("required")
    assert "customer" not in json.dumps(schema["parameters"]).lower()


def test_states_dates_and_reply_of_each_case_newest_first_without_operator_id(conn):
    add_case(conn, "HO-20261020-AAAA01", created_at="2026-10-20T08:00:00")
    claimed = add_case(conn, "HO-20261021-BBBB02", created_at="2026-10-21T08:00:00", state="claimed",
                       claimed_by="op_ana", claimed_at="2026-10-21T08:05:00")
    answered = add_case(conn, "HO-20261022-CCCC03", created_at="2026-10-22T08:00:00", state="answered",
                        claimed_by="op_ana", claimed_at="2026-10-22T08:05:00", answered_at="2026-10-22T08:10:00")
    add_operator_turn(conn, answered, REPLY, "HO-20261022-CCCC03")
    add_case(conn, "HO-20261023-DDDD04", created_at="2026-10-23T08:00:00", state="closed", claimed_by="op_bia",
             claimed_at="2026-10-23T08:05:00", answered_at="2026-10-23T08:10:00", closed_at="2026-10-23T09:00:00",
             closed_by="op_bia")
    out = execute("get_handoff_cases", {}, env(conn))
    assert out.ok, out.error
    cases = out.data["cases"]
    assert [c["protocol"] for c in cases] == [
        "HO-20261023-DDDD04", "HO-20261022-CCCC03", "HO-20261021-BBBB02", "HO-20261020-AAAA01"
    ]
    assert [c["state"] for c in cases] == ["closed", "answered", "claimed", "open"]
    assert set(cases[0]) == {
        "protocol", "state", "reason", "opened_at", "claimed_at", "answered_at", "closed_at", "operator_reply"
    }
    assert cases[0]["closed_at"] == "2026-10-23T09:00:00" and cases[2]["claimed_at"] == "2026-10-21T08:05:00"
    assert cases[1]["operator_reply"] == REPLY and cases[1]["answered_at"] == "2026-10-22T08:10:00"
    assert cases[3]["operator_reply"] is None and cases[3]["claimed_at"] is None
    assert out.data["source"] == "HandoffCases" and out.data["observed_at"].startswith("2026-10-26T10:00:00")
    dumped = json.dumps(out.data)
    assert "op_ana" not in dumped and "op_bia" not in dumped and claimed not in dumped and "conv_" not in dumped


def test_each_case_of_one_conversation_gets_only_its_own_reply(conn):
    """Two cases opened in the same conversation, only the first answered: the second never shows the first's reply."""
    answered = add_case(conn, "HO-20261020-AAAA01", created_at="2026-10-20T08:00:00", state="answered")
    waiting = add_case(conn, "HO-20261022-CCCC03", created_at="2026-10-22T08:00:00")
    conn.execute("UPDATE handoff_cases SET conversation_id = ? WHERE case_id = ?", (f"conv_{answered}", waiting))
    add_operator_turn(conn, answered, REPLY, "HO-20261020-AAAA01")
    cases = {c["protocol"]: c for c in execute("get_handoff_cases", {}, env(conn)).data["cases"]}
    assert cases["HO-20261020-AAAA01"]["operator_reply"] == REPLY
    assert cases["HO-20261022-CCCC03"]["operator_reply"] is None


def test_at_most_five_cases(conn):
    for n in range(7):
        add_case(conn, f"HO-202610{10 + n}-EEEE{n:02d}", created_at=f"2026-10-{10 + n}T08:00:00")
    cases = execute("get_handoff_cases", {}, env(conn)).data["cases"]
    assert len(cases) == HANDOFF_CASES_LIMIT == 5
    assert cases[0]["protocol"] == "HO-20261016-EEEE06" and cases[-1]["protocol"] == "HO-20261012-EEEE02"


@pytest.mark.parametrize(
    ("protocol", "expected"),
    [
        ("HO-20261022-CCCC03", ["HO-20261022-CCCC03"]),  # full
        ("ho-20261022-cccc03", ["HO-20261022-CCCC03"]),  # any case
        ("CC03", ["HO-20261022-CCCC03"]),  # the end, 4 characters
        ("cccc03", ["HO-20261022-CCCC03"]),
        ("1022-CCCC03", ["HO-20261022-CCCC03"]),
        ("10220CCCC03", []),  # an end that is not the protocol's
        ("AAAA", []),  # in the protocol but not at its end
        ("FFFF99", []),
    ],
)
def test_filter_by_the_full_protocol_or_its_end(conn, protocol, expected):
    add_case(conn, "HO-20261020-AAAA01", created_at="2026-10-20T08:00:00")
    add_case(conn, "HO-20261022-CCCC03", created_at="2026-10-22T08:00:00")
    out = execute("get_handoff_cases", {"protocol": protocol}, env(conn))
    assert out.ok and [c["protocol"] for c in out.data["cases"]] == expected
    assert out.data["protocol_filter"] == protocol


@pytest.mark.parametrize("protocol", ["C03", "AB-1", "--C03--", "CC 03", "CC03?", "çççç", "", "X" * 33])
def test_a_protocol_shorter_than_four_letters_or_digits_or_with_other_characters_is_an_argument_error(conn, protocol):
    add_case(conn, "HO-20261022-CCCC03")
    out = execute("get_handoff_cases", {"protocol": protocol}, env(conn))
    assert not out.ok and out.error["code"] == "INVALID_ARGUMENT" and out.data is None
    audit = conn.execute("SELECT tool, outcome FROM audit_events").fetchall()
    assert [tuple(r) for r in audit] == [("get_handoff_cases", "invalid_argument")]


def test_an_unknown_argument_is_refused(conn):
    out = execute("get_handoff_cases", {"customer_id": OTHER_CUSTOMER}, env(conn))
    assert not out.ok and out.error["code"] == "INVALID_ARGUMENT"


def test_another_merchant_never_sees_the_case_and_every_call_is_audited(conn):
    mine = add_case(conn, "HO-20261022-CCCC03")
    add_operator_turn(conn, mine, REPLY, "HO-20261022-CCCC03")
    add_case(conn, "HO-20261022-OTHR01", customer=OTHER_CUSTOMER)
    other = env(conn, OTHER_CUSTOMER)
    calls = (({}, ["HO-20261022-OTHR01"]), ({"protocol": "HO-20261022-CCCC03"}, []), ({"protocol": "CC03"}, []))
    for args, seen in calls:
        out = execute("get_handoff_cases", args, other)  # someone else's protocol finds nothing: no data, no hint
        assert out.ok and [c["protocol"] for c in out.data["cases"]] == seen
        assert REPLY not in json.dumps(out.data) and "hc_cccc03" not in json.dumps(out.data)
    assert [c["protocol"] for c in execute("get_handoff_cases", {}, other).data["cases"]] == ["HO-20261022-OTHR01"]
    assert [c["protocol"] for c in execute("get_handoff_cases", {}, env(conn)).data["cases"]] == [
        "HO-20261022-CCCC03"
    ]
    one = execute("get_handoff_cases", {"protocol": "cc03"}, env(conn))
    assert one.ok and one.data["count"] == 1
    rows = conn.execute(
        "SELECT customer_id, tool, resource_id, outcome, principal_id, scope FROM audit_events ORDER BY id"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (OTHER_CUSTOMER, "get_handoff_cases", None, "ok", f"merchant:{OTHER_CUSTOMER}", SUPPORT_READ),
        (OTHER_CUSTOMER, "get_handoff_cases", None, "ok", f"merchant:{OTHER_CUSTOMER}", SUPPORT_READ),
        (OTHER_CUSTOMER, "get_handoff_cases", None, "ok", f"merchant:{OTHER_CUSTOMER}", SUPPORT_READ),
        (OTHER_CUSTOMER, "get_handoff_cases", None, "ok", f"merchant:{OTHER_CUSTOMER}", SUPPORT_READ),
        (MAIN_CUSTOMER, "get_handoff_cases", None, "ok", f"merchant:{MAIN_CUSTOMER}", SUPPORT_READ),
        (MAIN_CUSTOMER, "get_handoff_cases", mine, "ok", f"merchant:{MAIN_CUSTOMER}", SUPPORT_READ),  # the one found
    ]


def test_a_session_without_the_read_scope_is_refused_and_audited(conn):
    add_case(conn, "HO-20261022-CCCC03")
    context = CustomerContext(MAIN_CUSTOMER, True, "svc:x", "service", (), MAIN_CUSTOMER)
    out = execute("get_handoff_cases", {}, ToolEnv(conn, CLOCK, context))
    assert not out.ok and out.error["code"] == "FORBIDDEN_SCOPE" and out.data is None
    row = conn.execute("SELECT tool, outcome, scope FROM audit_events").fetchone()
    assert tuple(row) == ("get_handoff_cases", "forbidden_scope", SUPPORT_READ)


def test_the_reported_values_come_from_the_tool_result_and_pass_the_output_guard(conn):
    answered = add_case(conn, "HO-20261022-CCCC03", state="answered", answered_at="2026-10-22T08:10:00")
    add_operator_turn(conn, answered, REPLY, "HO-20261022-CCCC03")
    out = execute("get_handoff_cases", {}, env(conn))
    answer = f"Ticket HO-20261022-CCCC03: respondido em 2026-10-22. Resposta da atendente: {REPLY}"
    evidence = [json.dumps(out.data, ensure_ascii=False)]
    assert unsupported(answer, [ANY_TICKET, *evidence], CLOCK.now().date()) == []
    # without the tool result the amount and the dates of the reply have no evidence
    kinds = {v.kind for v in unsupported(answer, [ANY_TICKET], CLOCK.now().date())}
    assert kinds == {"amount", "date"}


# --- prompt and Router ---------------------------------------------------------------------------------------------


def test_support_v11_is_a_new_file_in_use_and_keeps_every_rule_of_v10():
    v10 = (PROMPTS / "support.v10.md").read_text(encoding="utf-8")
    v11 = (PROMPTS / "support.v11.md").read_text(encoding="utf-8")
    assert "get_handoff_cases" not in v10 and "version: 10" in v10
    assert load_prompt(PROMPTS, "support").ref == "support@11" and prompt_versions(PROMPTS)["support"] == "11"
    flat = " ".join(v11.split())
    assert "call `get_handoff_cases` before saying there is none" in flat
    assert "in their own words" in flat and "Never state or guess a deadline" in flat
    assert "Asking about an existing ticket is not asking for a person: do not escalate" in flat
    old_rules = " ".join(v10.split("How to work:")[1].split("Write `points`")[0].split())
    assert old_rules in flat  # rules 1 to 14 unchanged
    assert prompt_versions(PROMPTS)["router"] == "7"  # the Router prompt did not need a new version


@pytest.mark.parametrize(
    ("message", "protocol"),
    [
        (ANY_TICKET, None),
        ("Qual o status do ticket que termina em 7F3A?", "7F3A"),
        ("Alguma novidade do chamado HO-20261026-7F3A9C?", "HO-20261026-7F3A9C"),
        ("Do I have any open ticket?", None),
        ("What is the status of the ticket ending in 7f3a?", "7f3a"),
    ],
)
def test_the_scripted_router_sends_ticket_questions_to_support(message, protocol):
    assert route_for(message) == ("support", "general")
    assert ticket_filter(message) == ({"protocol": protocol} if protocol else {})


@pytest.mark.parametrize(
    ("message", "route"),
    [
        (HUMAN, "human_handoff"),
        ("Já pedi habilitação Visa, qual é o protocolo?", "support"),
        ("Quero encerrar meu contrato", "human_handoff"),
    ],
)
def test_requests_for_a_person_and_other_protocols_keep_their_route(message, route):
    assert route_for(message)[0] == route
    if "Visa" in message:
        assert route_for(message)[1] == "enablement"


# --- end to end through the API -------------------------------------------------------------------------------------


def operator(client, name="op_ana"):
    return token_headers(client, Principal.operator(name))


def hand_off(client, customer=MAIN_CUSTOMER) -> dict:
    response = client.post("/messages", json={"message": HUMAN}, headers=merchant_headers(client, customer))
    assert response.status_code == 200 and response.json()["status"] == "handoff", response.text
    protocol = response.json()["handoff"]["protocol"]
    cases = client.get("/v1/handoffs", headers=operator(client)).json()["cases"]
    return next(c for c in cases if c["protocol"] == protocol)


def ask(client, message, customer=MAIN_CUSTOMER) -> dict:
    response = client.post("/messages", json={"message": message}, headers=merchant_headers(client, customer))
    assert response.status_code == 200, response.text
    return response.json()


def test_a_new_conversation_gets_protocol_state_and_reply_of_tickets_opened_in_other_conversations(offline, settings):
    client, orchestrator, llm = offline()
    opened, claimed, answered, closed = (hand_off(client) for _ in range(4))
    assert len({c["conversation_id"] for c in (opened, claimed, answered, closed)}) == 4
    assert client.post(f"/v1/handoffs/{claimed['case_id']}/claim", headers=operator(client)).status_code == 200
    body = {"action": "reply", "idempotency_key": "key-ticket-reply-01", "text": REPLY}
    replied = client.post(f"/v1/handoffs/{answered['case_id']}/actions", headers=operator(client), json=body)
    assert replied.status_code == 200 and replied.json()["queue_state"] == "answered", replied.text
    conn = connect(settings.db_path)
    try:
        handoffs.close(conn, closed["case_id"], "op_ana", actor="op_ana", targets=set())
    finally:
        conn.close()

    first = ask(client, ANY_TICKET_PT)  # a new conversation: no conversation_id
    assert first["conversation_id"] not in {c["conversation_id"] for c in (opened, claimed, answered, closed)}
    assert first["route"] == "support" and first["status"] == "answered" and first["via"] == "agent"
    answer = first["answer"]
    assert f"Ticket {opened['protocol']}: aguardando uma atendente." in answer
    assert f"Ticket {claimed['protocol']}: em atendimento por uma atendente." in answer
    assert f"Ticket {answered['protocol']}: respondido pela atendente." in answer
    assert f"Ticket {closed['protocol']}: encerrado." in answer
    assert f"Resposta da atendente: {REPLY}" in answer  # the attendant's words, amount and date unchanged
    trace = orchestrator.trace(first["request_id"])
    assert trace["detail"]["output_violations"] == []
    assert "tool:get_handoff_cases" in {s["step"] for s in trace["steps"]}
    assert any(s["title"] == "Human support tickets (your account)" for s in first["sources"])
    support_call = next(c for c in reversed(llm.calls) if c.spec.agent == "customer_support")
    assert "get_handoff_cases" in support_call.spec.instructions  # support.v11 is the prompt in force

    end = answered["protocol"][-4:].lower()
    second = ask(client, f"Qual o status do ticket que termina em {end}?")
    assert second["route"] == "support" and second["conversation_id"] != first["conversation_id"]
    assert second["answer"] == (
        f"Ticket {answered['protocol']}: respondido pela atendente.\nResposta da atendente: {REPLY}"
    )

    other = ask(client, ANY_TICKET_PT, customer=OTHER_CUSTOMER)
    assert other["answer"] == "Não encontrei ticket de atendimento humano."
    assert not any(c["protocol"] in other["answer"] for c in (opened, claimed, answered, closed))
    with sqlite3.connect(settings.db_path) as db:
        rows = db.execute(
            "SELECT customer_id, principal_id, scope, outcome, resource_id FROM audit_events "
            "WHERE tool='get_handoff_cases' ORDER BY id"
        ).fetchall()
    assert rows == [
        (MAIN_CUSTOMER, f"merchant:{MAIN_CUSTOMER}", SUPPORT_READ, "ok", None),
        (MAIN_CUSTOMER, f"merchant:{MAIN_CUSTOMER}", SUPPORT_READ, "ok", answered["case_id"]),
        (OTHER_CUSTOMER, f"merchant:{OTHER_CUSTOMER}", SUPPORT_READ, "ok", None),
    ]


def test_an_english_question_about_a_ticket_with_no_ticket_says_so(offline):
    client, _, _ = offline()
    response = ask(client, "Do I have any open ticket?")
    assert response["route"] == "support" and response["answer"] == "I found no human support ticket."
