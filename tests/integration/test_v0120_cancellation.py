"""v0.12.0 task 94 (RF-119, CA-67; spec D5, D6): sale cancellation with an explicit confirmation.

Scripted model, no network, no cost. The Support model may only ask for a cancellation (a request that waits); the
confirmation and the refusal run by code in the next turns, when the Router's `confirmation` label, validated in code,
is an explicit yes or no. Without a yes nothing changes in the account (`sale_cancellations`); a repeated request or
confirmation returns the same request and protocol; every call is audited with the write scope."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

import pytest

from merchant_assistant.agents import cancellation
from merchant_assistant.agents.router import enforce, explicit_answer
from merchant_assistant.api.identity import ROLE_SCOPES, SUPPORT_READ, SUPPORT_WRITE, Principal
from merchant_assistant.api.schemas import MessageRequest
from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import seed
from merchant_assistant.evaluation.runner import run_conversations
from merchant_assistant.evaluation.scripted_policy import handler as default_handler
from merchant_assistant.llm.scripted import ToolPlan
from merchant_assistant.orchestration.state import RouterDecision
from merchant_assistant.scenarios import as_case, catalog
from merchant_assistant.testing import DEFAULT_CLOCK, offline_orchestrator
from merchant_assistant.tools.base import CustomerContext, ToolEnv
from merchant_assistant.tools.registry import AGENT_TOOLS, TOOLS, execute, model_tool_schemas

ROOT = Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "tests" / "scenarios" / "cancellation.jsonl"
ASK = "Quero cancelar a venda de débito de ontem."
STATUS = "Qual o status do cancelamento da venda de débito de ontem?"
DEBIT_SALE = "sale_1988_0001"  # yesterday's debit sale of cliente1988 (seed): R$ 150,00 on 2026-10-25
AMOUNT, SALE_DATE = "R$ 150,00", "2026-10-25"
READ_ONLY = Principal("merchant:cliente1988", "merchant", "cliente1988", (SUPPORT_READ,))  # a token from before v0.12.0


@pytest.fixture
def orchestrator(settings):
    orch, _ = offline_orchestrator(settings, with_index=False)
    try:
        yield orch
    finally:
        orch.close()


def say(orch, message: str, conversation_id: str | None = None, principal: Principal | None = None):
    request_id = f"req_t94_{uuid.uuid4().hex[:10]}"
    response = orch.handle(
        MessageRequest(message=message, user_id="cliente1988", conversation_id=conversation_id),
        request_id,
        principal=principal,
    )
    return response, orch.trace(request_id)


def rows(settings, sql: str, *args) -> list[dict]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


def requests(settings) -> list[dict]:
    return rows(settings, "SELECT * FROM sale_cancellation_requests ORDER BY created_at, rowid")


def account(settings) -> list[dict]:
    """The account state the cancellation changes: the sale cancellations of the merchant."""
    return rows(settings, "SELECT * FROM sale_cancellations WHERE customer_id='cliente1988' ORDER BY transaction_id")


def write_audit(settings) -> list[tuple]:
    return [
        (r["tool"], r["scope"], r["outcome"], r["resource_id"], r["principal_id"])
        for r in rows(settings, "SELECT * FROM audit_events WHERE scope = ? ORDER BY id", SUPPORT_WRITE)
    ]


def pending(settings, orch) -> tuple[str, dict, list[dict]]:
    """Turn 1 of every flow: the request waits; returns (conversation, its row, the account before any answer)."""
    before = account(settings)
    response, trace = say(orch, ASK)
    assert "request_sale_cancellation" in trace["detail"]["tools"]
    [row] = requests(settings)
    assert row["state"] == "pending_confirmation" and row["sale_id"] == DEBIT_SALE and row["amount"] == 15000
    assert row["sale_date"] == SALE_DATE and row["protocol"] is None
    assert row["conversation_id"] == response.conversation_id
    assert AMOUNT in response.answer and "25/10/2026" in response.answer and '"sim"' in response.answer
    assert not cancellation.promises_execution(response.answer)
    assert account(settings) == before  # nothing changed yet
    return response.conversation_id, row, before


# --- CA-67: the journey of three turns -------------------------------------------------------------------------------


@pytest.mark.parametrize("replan", ["on", "off"])  # CA-67 holds with the replanning and in its ablation (task 93)
def test_ca67_journey_asks_confirms_and_reads_the_protocol_back(settings, replan):
    settings.replan = replan
    orchestrator, _ = offline_orchestrator(settings, with_index=False)
    before = account(settings)
    try:
        [result] = run_conversations(orchestrator, JOURNEY)
        conn = orchestrator.traces._conn()
        try:
            steps = {r["step"] for r in conn.execute("SELECT DISTINCT step FROM steps")}
        finally:
            conn.close()
    finally:
        orchestrator.close()
    assert ("replan" in steps) == (replan == "on") and "confirmation" in steps
    assert result["id"] == "V0120-CANCEL-CONFIRM" and len(result["turns"]) == 3
    assert result["passed"], [t for t in result["turns"] if not t["passed"]]
    first, second, third = result["turns"]
    [row] = requests(settings)
    assert row["state"] == "confirmed" and row["protocol"].startswith("CAN-") and row["confirmed_at"]
    assert AMOUNT in first["answer"] and not cancellation.promises_execution(first["answer"])
    assert row["protocol"] in second["answer"] and AMOUNT in second["answer"]
    assert row["protocol"] in third["answer"]  # the lookup reads it from the confirmed request
    after = account(settings)
    assert [r for r in after if r not in before] == [
        {
            "transaction_id": DEBIT_SALE,
            "customer_id": "cliente1988",
            "status": "requested",
            "requested_at": "2026-10-26T10:00:00-03:00",
            "processed_at": None,
            "reason_code": "merchant_confirmed",
        }
    ]
    principal = "merchant:cliente1988"
    assert write_audit(settings) == [
        ("request_sale_cancellation", SUPPORT_WRITE, "ok", DEBIT_SALE, principal),
        ("confirm_sale_cancellation", SUPPORT_WRITE, "ok", row["request_id"], principal),
    ]
    facts = {(f["kind"], f["value"]) for f in rows(settings, "SELECT kind, value FROM conversation_facts")}
    assert {("protocol", row["protocol"]), ("amount", AMOUNT), ("date", SALE_DATE)} <= facts
    assert ("status", f"{row['request_id']}: confirmed") in facts  # the latest status of the request only
    assert ("status", f"{row['request_id']}: pending_confirmation") not in facts


def test_the_journey_file_carries_the_labels_of_each_turn_and_the_catalog_its_messages():
    [case] = [json.loads(line) for line in JOURNEY.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert case["id"] == "V0120-CANCEL-CONFIRM" and len(case["turns"]) == 3
    assert [t["expected_tools"] for t in case["turns"]] == [
        ["request_sale_cancellation"], ["confirm_sale_cancellation"], ["get_sale_cancellation_context"]
    ]
    assert [t["expected_cancellation_state"] for t in case["turns"]] == [
        "pending_confirmation", "confirmed", "confirmed"
    ]
    item = catalog(ROOT / "data")["scenarios"]["SC-CANCEL-CONFIRM"]
    assert item["conversation_case"] == case["id"] and item["source_case"] is None
    assert [item["message"], *item["follow_up_messages"]] == [t["message"] for t in case["turns"]]
    effective = as_case(item, "cliente1988")
    assert effective.expected_tools == ["request_sale_cancellation"] and effective.must_include_amounts == [15000]
    first = case["turns"][0]
    assert effective.accepted_routes == first["accepted_routes"]
    assert effective.expected_status == first["expected_status"]


def test_each_turn_of_the_journey_runs_the_tool_its_label_names(settings, orchestrator):
    [case] = [json.loads(line) for line in JOURNEY.read_text(encoding="utf-8").splitlines() if line.strip()]
    conversation_id = None
    for turn in case["turns"]:
        response, trace = say(orchestrator, turn["message"], conversation_id)
        conversation_id = response.conversation_id
        assert set(turn["expected_tools"]) <= set(trace["detail"]["tools"]), turn["message"]
        assert requests(settings)[-1]["state"] == turn["expected_cancellation_state"]


# --- no, silence, "yes, but", repetition ------------------------------------------------------------------------------


def test_an_explicit_no_declines_and_leaves_the_account_intact(settings, orchestrator):
    conversation_id, row, before = pending(settings, orchestrator)
    response, trace = say(orchestrator, "Não, pode deixar.", conversation_id)
    assert trace["detail"]["tools"] == ["decline_sale_cancellation"] and response.route == "support"
    assert requests(settings)[0]["state"] == "declined" and requests(settings)[0]["protocol"] is None
    assert account(settings) == before
    assert "nada foi cancelado" in response.answer and AMOUNT in response.answer
    response, trace = say(orchestrator, "Sim", conversation_id)  # nothing waits any more: a later yes does nothing
    assert "confirm_sale_cancellation" not in trace["detail"]["tools"] and account(settings) == before
    assert [a[0] for a in write_audit(settings)] == ["request_sale_cancellation", "decline_sale_cancellation"]


def test_two_turns_without_an_answer_expire_the_request_and_nothing_changes(settings, orchestrator):
    conversation_id, row, before = pending(settings, orchestrator)
    response, _ = say(orchestrator, "Ok, obrigado pela ajuda", conversation_id)
    assert requests(settings)[0]["state"] == "pending_confirmation" and requests(settings)[0]["turns_waited"] == 1
    assert '"sim"' in response.answer and AMOUNT in response.answer  # the reply asks again
    response, _ = say(orchestrator, "Como funciona o Pix?", conversation_id)
    assert requests(settings)[0]["state"] == "expired" and requests(settings)[0]["turns_waited"] == 2
    assert "expirou" in response.answer and not cancellation.promises_execution(response.answer)
    response, trace = say(orchestrator, "Sim", conversation_id)  # too late
    assert "confirm_sale_cancellation" not in trace["detail"]["tools"]
    assert requests(settings)[0]["state"] == "expired" and account(settings) == before
    principal = "merchant:cliente1988"
    assert write_audit(settings) == [  # each turn without an answer, the expiry included, through the registry
        ("request_sale_cancellation", SUPPORT_WRITE, "ok", DEBIT_SALE, principal),
        ("count_unanswered_cancellation_turn", SUPPORT_WRITE, "ok", row["request_id"], principal),
        ("count_unanswered_cancellation_turn", SUPPORT_WRITE, "ok", row["request_id"], principal),
    ]
    facts = {(f["kind"], f["value"]) for f in rows(settings, "SELECT kind, value FROM conversation_facts")}
    assert ("status", f"{row['request_id']}: expired") in facts


def test_yes_but_is_other_and_executes_nothing(settings, orchestrator):
    conversation_id, row, before = pending(settings, orchestrator)
    response, trace = say(orchestrator, "Sim, mas antes me diga quando cai o dinheiro da venda.", conversation_id)
    router = next(s for s in trace["steps"] if s["step"] == "router")
    # the model said yes; the code did not
    assert router["detail"]["confirmation"] == {"model": "yes", "validated": "other"}
    assert "confirm_sale_cancellation" not in trace["detail"]["tools"]
    assert requests(settings)[0]["state"] == "pending_confirmation" and account(settings) == before
    assert '"sim"' in response.answer  # still waiting: asked again


def test_a_repeated_request_and_a_repeated_yes_return_the_same_request_and_protocol(settings, orchestrator):
    conversation_id, row, before = pending(settings, orchestrator)
    say(orchestrator, ASK, conversation_id)  # asked again while waiting: the same request, waiting from now
    assert [r["request_id"] for r in requests(settings)] == [row["request_id"]]
    say(orchestrator, "Sim", conversation_id)
    [confirmed] = requests(settings)
    conn = connect(settings.db_path)
    try:
        env = ToolEnv(conn, FixedClock(DEFAULT_CLOCK), CustomerContext.for_principal(
            Principal.merchant("cliente1988"), "cliente1988", True), conversation_id=conversation_id)
        again = execute("confirm_sale_cancellation", {"request_id": row["request_id"]}, env)
        asked = execute("request_sale_cancellation", {"sale_id": DEBIT_SALE}, env)
    finally:
        conn.close()
    assert again.ok and again.data["protocol"] == confirmed["protocol"] and again.data["repeated"] is True
    assert asked.ok and asked.data["request_id"] == row["request_id"]
    assert asked.data["protocol"] == confirmed["protocol"]
    new = [r for r in account(settings) if r not in before]
    assert [r["transaction_id"] for r in new] == [DEBIT_SALE]  # one cancellation, however many times
    assert len(requests(settings)) == 1


# --- ownership and scope ---------------------------------------------------------------------------------------------


@pytest.fixture
def seeded(settings):
    conn = connect(settings.db_path)
    seed(conn, FixedClock(DEFAULT_CLOCK))
    conn.close()
    return settings


def tool_env(
    settings, principal: Principal, conversation_id: str | None = "conv_t94"
) -> tuple[sqlite3.Connection, ToolEnv]:
    conn = connect(settings.db_path)
    context = CustomerContext.for_principal(principal, principal.customer_id, True)
    return conn, ToolEnv(conn, FixedClock(DEFAULT_CLOCK), context, conversation_id=conversation_id)


def test_a_sale_of_another_merchant_is_refused_and_audited(seeded):
    settings = seeded
    conn, env = tool_env(settings, Principal.merchant("cliente1988"))
    try:
        outcome = execute("request_sale_cancellation", {"sale_id": "sale_002_0002"}, env, agent="customer_support")
        audit = conn.execute("SELECT tool, scope, outcome, resource_id FROM audit_events").fetchall()
        assert conn.execute("SELECT COUNT(*) FROM sale_cancellation_requests").fetchone()[0] == 0
    finally:
        conn.close()
    assert not outcome.ok and outcome.error["code"] == "FORBIDDEN_RESOURCE"
    assert [tuple(a) for a in audit] == [("request_sale_cancellation", SUPPORT_WRITE, "forbidden", "sale_002_0002")]


def test_a_request_of_another_merchant_cannot_be_confirmed(seeded):
    settings = seeded
    conn, env = tool_env(settings, Principal.merchant("cliente_demo_002"))
    try:
        mine = execute("request_sale_cancellation", {"sale_id": "sale_002_0002"}, env)
        other_conn, other = tool_env(settings, Principal.merchant("cliente1988"))
        try:
            refused = execute("confirm_sale_cancellation", {"request_id": mine.data["request_id"]}, other)
        finally:
            other_conn.close()
        state = conn.execute("SELECT state FROM sale_cancellation_requests").fetchone()[0]
    finally:
        conn.close()
    assert mine.ok and refused.error["code"] == "FORBIDDEN_RESOURCE" and state == "pending_confirmation"


def test_in_a_conversation_a_sale_of_another_merchant_leaves_nothing_waiting(settings):
    def handler(call):
        if call.spec.agent == "customer_support":
            return ToolPlan(
                [("request_sale_cancellation", {"sale_id": "sale_002_0002"})],
                final=lambda r: {"points": ["I can only access your own records."], "needs_selection": False,
                                 "missing": [], "escalate": False, "escalation_reason": None},
            )
        return default_handler(call)

    orch, _ = offline_orchestrator(settings, handler=handler, with_index=False)
    try:
        before = rows(settings, "SELECT * FROM sale_cancellations ORDER BY transaction_id")
        response, trace = say(orch, ASK)
    finally:
        orch.close()
    assert requests(settings) == []
    assert rows(settings, "SELECT * FROM sale_cancellations ORDER BY transaction_id") == before
    assert write_audit(settings) == [
        ("request_sale_cancellation", SUPPORT_WRITE, "forbidden", "sale_002_0002", "merchant:cliente1988")
    ]
    assert not cancellation.promises_execution(response.answer) and "R$ 45,00" not in response.answer


def test_without_the_write_scope_nothing_is_requested_or_confirmed(settings, orchestrator):
    assert SUPPORT_WRITE in ROLE_SCOPES["merchant"]
    assert all(SUPPORT_WRITE not in ROLE_SCOPES[r] for r in ("demo", "operator", "service", "admin"))
    before = account(settings)
    response, trace = say(orchestrator, ASK, principal=READ_ONLY)
    assert requests(settings) == [] and account(settings) == before
    assert ("request_sale_cancellation", SUPPORT_WRITE, "forbidden_scope", DEBIT_SALE, "merchant:cliente1988") in (
        write_audit(settings)
    )  # the refusal keeps the sale it tried
    assert not cancellation.promises_execution(response.answer)

    conversation_id, row, before = pending(settings, orchestrator)  # asked by the merchant itself
    response, trace = say(orchestrator, "Sim", conversation_id, principal=READ_ONLY)  # answered with an old token
    assert trace["detail"]["tools"] == ["confirm_sale_cancellation"]
    assert requests(settings)[0]["state"] == "pending_confirmation" and account(settings) == before
    assert write_audit(settings)[-1] == (
        "confirm_sale_cancellation", SUPPORT_WRITE, "forbidden_scope", row["request_id"], "merchant:cliente1988"
    )
    assert "nada foi alterado" in response.answer


def test_confirm_and_decline_are_never_offered_to_a_model_and_the_mcp_stays_read_only():
    offered = {s["name"] for s in model_tool_schemas("customer_support")}
    assert "request_sale_cancellation" in offered
    assert not offered & {"confirm_sale_cancellation", "decline_sale_cancellation"}
    assert {TOOLS[n].scope for n in ("request_sale_cancellation", "confirm_sale_cancellation",
                                     "decline_sale_cancellation")} == {SUPPORT_WRITE}
    assert all(TOOLS[n].scope == SUPPORT_READ for n in AGENT_TOOLS["mcp"])
    assert set(AGENT_TOOLS["customer_support"]) - set(AGENT_TOOLS["mcp"]) == {"request_sale_cancellation"}
    schema = next(s for s in model_tool_schemas("customer_support") if s["name"] == "request_sale_cancellation")
    assert set(schema["parameters"]["properties"]) == {"sale_id"}  # no customer field


def test_a_model_that_asks_to_confirm_is_refused_by_the_allowlist(seeded):
    settings = seeded
    conn, env = tool_env(settings, Principal.merchant("cliente1988"))
    try:
        asked = execute("request_sale_cancellation", {"sale_id": DEBIT_SALE}, env, agent="customer_support")
        refused = execute("confirm_sale_cancellation", {"request_id": asked.data["request_id"]}, env,
                          agent="customer_support")
        state = conn.execute("SELECT state FROM sale_cancellation_requests").fetchone()[0]
    finally:
        conn.close()
    assert refused.error["code"] == "INVALID_ARGUMENT" and "not allowed" in refused.error["message"]
    assert state == "pending_confirmation"


def test_a_request_needs_a_conversation_and_a_sale_already_cancelled_is_refused(seeded):
    settings = seeded
    conn, env = tool_env(settings, Principal.merchant("cliente1988"), conversation_id=None)
    try:
        without = execute("request_sale_cancellation", {"sale_id": DEBIT_SALE}, env)
        env.conversation_id = "conv_t94"
        cancelled = execute("request_sale_cancellation", {"sale_id": "sale_1988_0002"}, env)  # seed: requested
    finally:
        conn.close()
    assert without.error["code"] == "INVALID_ARGUMENT" and cancelled.error["code"] == "INVALID_ARGUMENT"


def test_a_newer_request_in_the_conversation_expires_the_older_one(seeded):
    settings = seeded
    conn, env = tool_env(settings, Principal.merchant("cliente1988"))
    try:
        first = execute("request_sale_cancellation", {"sale_id": DEBIT_SALE}, env)
        second = execute("request_sale_cancellation", {"sale_id": "sale_1988_0003"}, env)
        states = dict(conn.execute("SELECT sale_id, state FROM sale_cancellation_requests").fetchall())
    finally:
        conn.close()
    assert first.ok and second.ok
    assert states == {DEBIT_SALE: "expired", "sale_1988_0003": "pending_confirmation"}


# --- the reply never promises the cancellation before the yes -------------------------------------------------------


def test_a_reply_that_says_the_sale_was_cancelled_before_the_yes_is_replaced(settings):
    def handler(call):
        if call.spec.agent == "personality" and "pending_confirmation" in json.dumps(call.spec.context):
            return {"answer": f"Pronto, cancelei a venda de {AMOUNT}."}
        return default_handler(call)

    orch, _ = offline_orchestrator(settings, handler=handler, with_index=False)
    try:
        response, trace = say(orch, ASK)
    finally:
        orch.close()
    guard = next(s for s in trace["steps"] if s["step"] == "output_guard")
    assert guard["detail"]["cancellation_request_from_code"] is True  # the request turn is code only
    assert "cancelei" not in response.answer and '"sim"' in response.answer
    assert not cancellation.promises_execution(response.answer)


@pytest.mark.parametrize(
    "draft",
    [
        "Pronto, venda cancelada!",
        "Se precisar de algo, estou aqui; a venda foi cancelada.",
        f"Cancelei a venda de {AMOUNT}, se precisar de mais algo é só chamar.",
    ],
)
def test_the_reproductions_of_the_review_are_replaced_by_the_guard(settings, draft):
    def handler(call):
        if call.spec.agent == "personality" and "pending_confirmation" in json.dumps(call.spec.context):
            return {"answer": draft}
        return default_handler(call)

    orch, _ = offline_orchestrator(settings, handler=handler, with_index=False)
    try:
        response, trace = say(orch, ASK)
    finally:
        orch.close()
    guard = next(s for s in trace["steps"] if s["step"] == "output_guard")
    assert guard["detail"]["cancellation_request_from_code"] is True  # the request turn is code only
    assert draft not in response.answer and not cancellation.promises_execution(response.answer)
    assert response.answer == pending_line()
    assert requests(settings)[0]["state"] == "pending_confirmation"


@pytest.mark.parametrize(
    "draft",
    [
        f"Pronto, cancelei a venda de {AMOUNT}.",
        "Pronto, venda cancelada!",
        "Se precisar de algo, estou aqui; a venda foi cancelada.",
        f"Cancelei a venda de {AMOUNT}, se precisar de mais algo é só chamar.",
    ],
)
def test_a_promise_in_a_later_turn_while_the_request_waits_is_replaced(settings, draft):
    """the request turn is code only, so the promise guard is checked in the next turn."""
    later = "Ok, obrigado pela ajuda"

    def handler(call):
        if call.spec.agent == "personality" and call.spec.context.get("message") == later:
            return {"answer": draft}
        return default_handler(call)

    orch, _ = offline_orchestrator(settings, handler=handler, with_index=False)
    try:
        response, _ = say(orch, ASK)
        response, trace = say(orch, later, response.conversation_id)  # a turn without an answer
    finally:
        orch.close()
    guard = next(s for s in trace["steps"] if s["step"] == "output_guard")
    assert guard["detail"]["cancellation_promise"] is True
    assert draft not in response.answer and not cancellation.promises_execution(response.answer)
    assert pending_line() in response.answer
    [row] = requests(settings)
    assert row["state"] == "pending_confirmation" and row["turns_waited"] == 1


def pending_line(language: str = "pt") -> str:
    return cancellation.LINES["pending_confirmation"][language].format(amount=AMOUNT, date="25/10/2026")


def test_while_the_request_waits_the_fixed_line_is_always_added(settings):
    # amount and "assim" (it holds "sim") in the reply: round 1 looked for the word by substring and added nothing
    draft = f"A venda de {AMOUNT} de 25/10/2026 está pronta; assim que puder, me diga o que prefere."

    def handler(call):
        if call.spec.agent == "personality" and "pending_confirmation" in json.dumps(call.spec.context):
            return {"answer": draft}
        return default_handler(call)

    orch, _ = offline_orchestrator(settings, handler=handler, with_index=False)
    try:
        response, _ = say(orch, ASK)
        again, _ = say(orch, "Ok, obrigado pela ajuda", response.conversation_id)  # a turn without an answer
    finally:
        orch.close()
    assert response.answer == pending_line()  # in the request turn, only the fixed line
    assert again.answer == f"{draft}\n{pending_line()}"  # a later turn: the model's text, then the line once


@pytest.mark.parametrize(
    ("text", "promises"),
    [
        ("A venda foi cancelada.", True),
        ("Cancelei a venda de R$ 150,00.", True),
        ("A venda de R$ 150,00 será cancelada.", True),
        ("Your sale has been cancelled.", True),
        ("I'll cancel it now.", True),
        ("Nada foi cancelado ainda.", False),
        ("A venda será cancelada só se você responder sim.", False),
        ("Nothing has been cancelled yet.", False),
        ("I will cancel it only after you reply yes.", False),
        ("O cancelamento foi solicitado.", False),
        # review of round 1: words the patterns missed, a qualifier in another clause, a comma between clauses
        ("Pronto, venda cancelada!", True),
        ("Cancelada com sucesso.", True),
        ("Seu pedido foi cancelado", True),
        ("Se precisar de algo, estou aqui; a venda foi cancelada.", True),
        ("Cancelei a venda, se precisar de mais algo é só chamar.", True),
        ("Não se preocupe, a venda foi cancelada.", True),
        ("When you need it, I’ll cancel it.", True),  # curly apostrophe
        ("Sale cancelled successfully.", True),
        ("A venda de R$ 1.500,00 não será cancelada sem o seu sim.", False),  # a number is not a clause boundary
        ("O pedido de cancelamento espera a sua resposta; nada foi cancelado.", False),
        ("Para confirmar o cancelamento, responda sim.", False),
        ("Cancelamento: aguardando sua confirmação.", False),
    ],
)
def test_promises_of_execution_are_recognised(text, promises):
    assert cancellation.promises_execution(text) is promises


def test_the_fixed_lines_never_promise_and_carry_amount_date_and_protocol():
    for status, by_language in cancellation.LINES.items():
        for language, line in by_language.items():
            assert not cancellation.promises_execution(line), (status, language)
    event = {"status": "confirmed", "sale": {"amount": {"display": AMOUNT}, "sale_date": SALE_DATE},
             "protocol": "CAN-20261026-ABC123"}
    assert cancellation.view(event, "pt")["message"] == (
        "O cancelamento da venda de R$ 150,00 de 25/10/2026 foi solicitado. Protocolo: CAN-20261026-ABC123."
    )
    assert "October 25, 2026" in cancellation.view(event, "en")["message"]


# --- Router: confirmation validated in code (router.v7) -------------------------------------------------------------


@pytest.mark.parametrize(
    ("message", "answer"),
    [
        ("Sim", "yes"),
        ("sim, pode cancelar", "yes"),
        ("Yes, cancel it please", "yes"),
        ("ok, confirmo!", "yes"),
        ("Não", "no"),
        ("não, obrigado", "no"),
        ("No, keep it", "no"),
        ("Sim, mas antes me diga o saldo", None),
        ("yes but first tell me the fee", None),
        ("sim?", None),
        ("sim, não", None),
        ("ok", None),
        ("Quero cancelar a venda de débito de ontem.", None),
    ],
)
def test_explicit_answers(message, answer):
    assert explicit_answer(message) == answer


def decision(confirmation: str, safety: str = "none", route: str = "clarify") -> RouterDecision:
    return RouterDecision(
        route=route, language="pt", topic=None, intents=["x"], safety=safety,
        clarification_question="?" if route == "clarify" else None, case_signal="none", confirmation=confirmation,
    )


def test_enforce_keeps_a_yes_or_no_only_with_a_waiting_request_a_safe_message_and_the_same_answer():
    yes = enforce(decision("yes"), message="Sim", pending_cancellation=True)
    assert (yes.confirmation, yes.route, yes.topic, yes.clarification_question) == ("yes", "support", "cancellation",
                                                                                  None)
    assert enforce(decision("no"), message="Não", pending_cancellation=True).confirmation == "no"
    assert enforce(decision("yes"), message="Sim").confirmation == "other"  # nothing waits
    assert enforce(decision("yes"), message="Não", pending_cancellation=True).confirmation == "other"  # disagree
    assert enforce(decision("other"), message="Sim", pending_cancellation=True).confirmation == "other"  # never added
    unsafe = enforce(decision("yes", safety="injection"), message="Sim", pending_cancellation=True)
    assert (unsafe.confirmation, unsafe.route) == ("other", "out_of_scope")
    assert RouterDecision.model_validate({k: v for k, v in decision("yes").model_dump().items()
                                          if k != "confirmation"}).confirmation == "other"


def test_the_router_reads_the_waiting_request_only_while_it_waits(settings, orchestrator):
    conversation_id, row, _ = pending(settings, orchestrator)
    first_router = [c for c in orchestrator.llm.calls if c.spec.agent == "router"][0]
    assert "Sale cancellation waiting" not in first_router.spec.input
    say(orchestrator, "Sim", conversation_id)
    last_router = [c for c in orchestrator.llm.calls if c.spec.agent == "router"][-1]
    assert f"Sale cancellation waiting for the merchant's yes or no: sale of {AMOUNT} on {SALE_DATE}" in (
        last_router.spec.input
    )
    assert "confirmation:" in last_router.spec.instructions  # router.v7


def test_router_v7_and_support_v9_are_new_files_and_the_old_ones_stay():
    prompts = ROOT / "prompts"
    for old, new in (("router.v6.md", "router.v7.md"), ("support.v8.md", "support.v9.md")):
        assert (prompts / old).exists() and (prompts / new).exists()
    router_v7 = (prompts / "router.v7.md").read_text(encoding="utf-8")
    support_v9 = (prompts / "support.v9.md").read_text(encoding="utf-8")
    assert "version: 7" in router_v7 and "confirmation" in router_v7 and "sim, mas" in router_v7
    assert "version: 9" in support_v9 and "request_sale_cancellation" in support_v9
    assert "confirmation" not in (prompts / "router.v6.md").read_text(encoding="utf-8")
    assert "request_sale_cancellation" not in (prompts / "support.v8.md").read_text(encoding="utf-8")


def test_the_router_comparison_reads_the_same_waiting_request(settings, orchestrator):
    from types import SimpleNamespace

    from merchant_assistant.api import v1
    from merchant_assistant.data.clock import SystemClock

    conversation_id, row, _ = pending(settings, orchestrator)
    conn = connect(settings.db_path)
    try:
        history, state, _ = v1._read_conversation(conn, conversation_id, "cliente1988", SystemClock(settings.timezone))
    finally:
        conn.close()
    assert state["cancellation"]["request_id"] == row["request_id"]
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)))
    spec = v1._router_spec(request, "Sim", history, state)
    assert f"Sale cancellation waiting for the merchant's yes or no: sale of {AMOUNT} on {SALE_DATE}" in spec.input
    assert spec.context["pending_cancellation"]["request_id"] == row["request_id"]


# --- round 2 of the review: the counter, the refused resource, the race and the merchant filter ----------------------


def test_without_the_write_scope_a_turn_without_an_answer_leaves_the_request_waiting(settings, orchestrator):
    conversation_id, row, before = pending(settings, orchestrator)
    for message in ("Ok, obrigado pela ajuda", "Como funciona o Pix?"):  # two turns: enough to expire it
        _, trace = say(orchestrator, message, conversation_id, principal=READ_ONLY)
        assert "count_unanswered_cancellation_turn" in trace["detail"]["tools"]
    [waiting] = requests(settings)
    assert waiting["state"] == "pending_confirmation" and waiting["turns_waited"] == 0
    refused = ("count_unanswered_cancellation_turn", SUPPORT_WRITE, "forbidden_scope", row["request_id"],
               "merchant:cliente1988")
    assert write_audit(settings)[-2:] == [refused, refused]
    response, _ = say(orchestrator, "Sim", conversation_id)  # the merchant's own session still confirms it
    assert requests(settings)[0]["state"] == "confirmed" and requests(settings)[0]["protocol"] in response.answer


def test_a_call_refused_by_scope_is_audited_with_the_resource_it_tried(seeded):
    conn, env = tool_env(seeded, READ_ONLY)
    try:
        for name, args in (
            ("request_sale_cancellation", {"sale_id": DEBIT_SALE}),
            ("confirm_sale_cancellation", {"request_id": "scr_tried"}),
            ("decline_sale_cancellation", {"request_id": "scr_tried"}),
            ("count_unanswered_cancellation_turn", {"request_id": "scr_tried"}),
            ("confirm_sale_cancellation", {"request_id": 42}),  # not a string: no resource kept
        ):
            assert execute(name, args, env).error["code"] == "FORBIDDEN_SCOPE"
        audit = [tuple(r) for r in conn.execute("SELECT tool, outcome, resource_id FROM audit_events ORDER BY id")]
    finally:
        conn.close()
    assert audit == [
        ("request_sale_cancellation", "forbidden_scope", DEBIT_SALE),
        ("confirm_sale_cancellation", "forbidden_scope", "scr_tried"),
        ("decline_sale_cancellation", "forbidden_scope", "scr_tried"),
        ("count_unanswered_cancellation_turn", "forbidden_scope", "scr_tried"),
        ("confirm_sale_cancellation", "forbidden_scope", None),
    ]


def test_the_counter_is_never_offered_to_a_model():
    assert TOOLS["count_unanswered_cancellation_turn"].scope == SUPPORT_WRITE
    assert all("count_unanswered_cancellation_turn" not in tools for tools in AGENT_TOOLS.values())


def test_two_requests_for_the_same_sale_at_once_return_one_request(seeded, monkeypatch):
    from types import SimpleNamespace

    from merchant_assistant.tools import domain

    # the first request stops after reading that nothing is active and before writing its row; round 1 let the second
    # one read the same and both inserted (IntegrityError on the active index)
    inside, calls = threading.Event(), []

    def slow_uuid4():
        calls.append(1)
        if len(calls) == 1:
            inside.set()
            time.sleep(0.5)
        return uuid.uuid4()

    monkeypatch.setattr(domain, "uuid", SimpleNamespace(uuid4=slow_uuid4))
    results: dict[str, object] = {}

    def ask(key: str) -> None:
        conn, env = tool_env(seeded, Principal.merchant("cliente1988"))
        try:
            results[key] = execute("request_sale_cancellation", {"sale_id": DEBIT_SALE}, env)
        except Exception as exc:  # noqa: BLE001 - the failure is what the test reports
            results[key] = exc
        finally:
            conn.close()

    first = threading.Thread(target=ask, args=("first",))
    first.start()
    assert inside.wait(5)
    second = threading.Thread(target=ask, args=("second",))
    second.start()
    first.join(10)
    second.join(10)
    one, two = results["first"], results["second"]
    assert getattr(one, "ok", False) and getattr(two, "ok", False), results
    assert one.data["request_id"] == two.data["request_id"] and two.data["repeated"] is True
    assert len(requests(seeded)) == 1 and len(calls) == 1


def test_the_waiting_request_is_read_only_for_its_own_merchant(seeded):
    from merchant_assistant.tools.domain import pending_sale_cancellation

    conn, env = tool_env(seeded, Principal.merchant("cliente_demo_002"))  # conversation conv_t94
    try:
        theirs = execute("request_sale_cancellation", {"sale_id": "sale_002_0002"}, env)
        assert theirs.ok
        assert pending_sale_cancellation(conn, "conv_t94", "cliente1988") is None
        assert pending_sale_cancellation(conn, "conv_t94", "cliente_demo_002")["request_id"] == (
            theirs.data["request_id"]
        )
    finally:
        conn.close()


# --- pre-QA corrections of the version review ------------------------------------------------------------------------


def test_a_yes_labelled_resolved_confirms_without_feedback_or_moving_the_case(settings):  # P3-3
    def handler(call):
        answer = default_handler(call)
        if call.spec.agent == "router" and call.spec.context.get("pending_cancellation"):
            answer = {**answer, "case_signal": "resolved"}  # the model also reads the yes as a resolution
        return answer

    orch, _ = offline_orchestrator(settings, handler=handler, with_index=False)
    try:
        conversation_id, row, _ = pending(settings, orch)
        conn = sqlite3.connect(settings.db_path)
        try:  # an attempt still waiting for the merchant's feedback
            conn.execute(
                "INSERT INTO case_attempts (conversation_id, cycle, step, result, created_at, updated_at) "
                "VALUES (?, 1, 'Reinicie a maquininha.', 'pending', '2026-10-26', '2026-10-26')",
                (conversation_id,),
            )
            conn.commit()
        finally:
            conn.close()
        [case_before] = rows(settings, "SELECT state, resolution_evidence FROM conversations")
        response, trace = say(orch, "Sim", conversation_id)
    finally:
        orch.close()
    [confirmed] = requests(settings)
    assert confirmed["state"] == "confirmed" and confirmed["protocol"] in response.answer
    assert response.route == "support" and trace["detail"]["tools"] == ["confirm_sale_cancellation"]
    [attempt] = rows(settings, "SELECT result, evidence FROM case_attempts")
    assert attempt == {"result": "pending", "evidence": None}  # no feedback recorded
    assert case_before == {"state": "awaiting_customer", "resolution_evidence": None}
    assert rows(settings, "SELECT state, resolution_evidence FROM conversations") == [case_before]  # case not moved
    assert enforce(
        decision("yes").model_copy(update={"case_signal": "resolved"}), message="Sim", pending_cancellation=True
    ).case_signal == "none"
    assert enforce(  # without a validated answer the model's signal stays
        decision("other").model_copy(update={"case_signal": "resolved"}), message="Sim", pending_cancellation=True
    ).case_signal == "resolved"


def jev_system(
    offline, settings, confirmation: str = "yes", choices: dict | None = None, handler=None, with_index: bool = False
):
    """`POST /v1/messages` with `router_mechanism: "jev"`: the TypeSafe adapter on a stub transport (no network).
    `choices` replaces the stub's answers (e.g. `{"route": "clarify"}`); `handler` replaces the scripted model's."""
    from merchant_assistant.llm.jev import JEV_MODEL, JevRouter
    from merchant_assistant.testing import merchant_headers

    client, orchestrator, llm = offline(with_index=with_index, **({"handler": handler} if handler else {}))
    payloads: list[dict] = []

    def transport(payload):
        payloads.append(payload)
        answers = {
            "route": {"choice": "support"},
            "language": {"choice": "pt"},
            "topic": {"choice": "cancellation"},
            "safety": {"choice": "none"},
            "case_signal": {"choice": "none"},
        }
        if "confirmation" in payload["questions"]:
            answers["confirmation"] = {"choice": confirmation}
        answers |= {question: {"choice": choice} for question, choice in (choices or {}).items()}
        return {"model": JEV_MODEL, "answers": answers, "usage": {"input_tokens": 12, "output_tokens": 5}}

    orchestrator.llm_factory = lambda provider, model: (
        JevRouter("synthetic-key", transport=transport) if provider == "typesafe" else llm
    )
    headers = merchant_headers(client)

    def send(
        message: str, conversation_id: str | None = None, mechanism: str = "jev", comparison_id: str | None = None
    ) -> dict:
        body = {"message": message, "profile_id": "reference", "profile_version": 1, "router_mechanism": mechanism}
        body |= {"conversation_id": conversation_id, "comparison_id": comparison_id}
        sent = client.post("/v1/messages", headers=headers, json=body)
        assert sent.status_code == 200, sent.json()
        return sent.json()

    def run(request_id: str) -> dict:
        return client.get(f"/v1/runs/{request_id}", headers=headers).json()

    def compare(message: str, conversation_id: str | None, mechanism: str) -> dict:
        body = {"message": message, "conversation_id": conversation_id, "profile_id": "reference",
                "profile_version": 1, "selected_mechanism": mechanism}
        compared = client.post("/v1/router/compare", headers=headers, json=body)
        assert compared.status_code == 201, compared.json()
        return compared.json()

    send.compare = compare
    send.trace = orchestrator.trace
    return send, payloads, llm, run


def test_with_jev_a_yes_to_a_waiting_request_confirms_it(offline, settings):  # P2-1
    send, payloads, llm, run = jev_system(offline, settings)
    first = send(ASK)
    [row] = requests(settings)
    assert row["state"] == "pending_confirmation" and "confirmation" not in payloads[0]["questions"]
    conversation_id = first["message"]["conversation_id"]
    second = send("Sim", conversation_id)
    assert set(payloads[1]["questions"]["confirmation"]["criteria"]) == {"yes", "no", "other"}
    [confirmed] = requests(settings)
    assert confirmed["state"] == "confirmed" and confirmed["protocol"] in second["message"]["answer"]
    assert not [call for call in llm.calls if call.spec.agent == "router"]
    steps = [step["step"] for step in run(second["message"]["request_id"])["steps"]]
    assert steps[steps.index("router") + 1] == "confirmation"  # the step `/v1/runs` lists (api-v1, v0.12.0)


def test_with_jev_a_yes_label_on_a_message_that_is_not_an_answer_is_other(offline, settings):  # P2-1
    send, payloads, _, _ = jev_system(offline, settings, confirmation="yes")
    first = send(ASK)
    send("Sim, mas antes me diga quando cai o dinheiro", first["message"]["conversation_id"])
    assert "confirmation" in payloads[1]["questions"]
    [waiting] = requests(settings)
    assert waiting["state"] == "pending_confirmation" and waiting["protocol"] is None


def resolved_on_the_answer(call):
    """The scripted model, except that the Router also reads the merchant's answer as a resolution of the case."""
    answer = default_handler(call)
    if call.spec.agent == "router" and call.spec.context.get("pending_cancellation"):
        answer = {**answer, "case_signal": "resolved"}
    return answer


@pytest.mark.parametrize("mechanism", ["llm", "jev"])
def test_a_yes_through_the_router_comparison_confirms_the_waiting_request(offline, settings, mechanism):  # P2-A
    # both Routers say `resolved` (P3-2 of the version review): the validated yes is what drops the case signal
    send, payloads, _, _ = jev_system(
        offline, settings, choices={"case_signal": "resolved"}, handler=resolved_on_the_answer
    )
    conversation_id = send(ASK, mechanism=mechanism)["message"]["conversation_id"]
    compared = send.compare("Sim", conversation_id, mechanism)
    assert {m: d["decision"]["confirmation"] for m, d in compared["decisions"].items()} == {"llm": "yes", "jev": "yes"}
    assert {d["decision"]["case_signal"] for d in compared["decisions"].values()} == {"none"}
    answer = send("Sim", conversation_id, mechanism, compared["comparison_id"])["message"]["answer"]
    [confirmed] = requests(settings)
    assert confirmed["state"] == "confirmed" and confirmed["protocol"] in answer


def test_without_a_waiting_request_the_router_comparison_is_unchanged(offline, settings):  # P2-A
    send, _, _, _ = jev_system(offline, settings)
    compared = send.compare("Sim", None, "llm")
    assert {result["decision"]["confirmation"] for result in compared["decisions"].values()} == {"other"}
    assert compared["decisions"]["llm"]["decision"]["topic"] != "cancellation"  # a bare yes with nothing waiting
    assert send.compare(ASK, None, "jev")["decisions"]["jev"]["decision"] == {
        "route": "support", "language": "pt", "topic": "cancellation", "intents": [], "safety": "none",
        "clarification_question": None, "case_signal": "none", "confirmation": "other",
    }
    assert requests(settings) == []


# --- closing of v0.12.0 (task 96): the router comparison applies and traces the same rules --------------------------


def clarifying_router(call):
    """The scripted model, except that the Router asks to clarify (the contract termination of task 76)."""
    answer = default_handler(call)
    if call.spec.agent == "router":
        answer = {**answer, "route": "clarify", "topic": None, "clarification_question": "Pode explicar melhor?"}
    return answer


@pytest.mark.parametrize("mechanism", ["llm", "jev"])
def test_through_the_comparison_the_contract_termination_rule_is_in_the_trace(offline, settings, mechanism):
    send, _, _, _ = jev_system(offline, settings, choices={"route": "clarify"}, handler=clarifying_router)
    message = "Quero encerrar meu contrato."
    compared = send.compare(message, None, mechanism)
    assert {m: d["decision"]["route"] for m, d in compared["decisions"].items()} == {
        "llm": "human_handoff", "jev": "human_handoff"
    }
    assert all("model_decision" not in d for d in compared["decisions"].values())  # stored, not returned
    sent = send(message, None, mechanism, compared["comparison_id"])["message"]
    assert sent["route"] == "human_handoff"
    [router_step] = [step for step in send.trace(sent["request_id"])["steps"] if step["step"] == "router"]
    assert router_step["detail"]["rule"] == "contract_termination"


@pytest.mark.parametrize("mechanism", ["llm", "jev"])
def test_through_the_comparison_a_yes_label_on_a_yes_but_is_other_and_the_request_waits(offline, settings, mechanism):
    send, _, _, _ = jev_system(offline, settings, confirmation="yes")
    conversation_id = send(ASK, mechanism=mechanism)["message"]["conversation_id"]
    message = "Sim, mas antes me diga quando cai o dinheiro"
    compared = send.compare(message, conversation_id, mechanism)
    assert {m: d["decision"]["confirmation"] for m, d in compared["decisions"].items()} == {
        "llm": "other", "jev": "other"
    }
    sent = send(message, conversation_id, mechanism, compared["comparison_id"])["message"]
    [waiting] = requests(settings)
    assert waiting["state"] == "pending_confirmation" and waiting["protocol"] is None
    [router_step] = [step for step in send.trace(sent["request_id"])["steps"] if step["step"] == "router"]
    assert router_step["detail"]["confirmation"] == {"model": "yes", "validated": "other"}


def support_on_resolution(call):
    """The scripted model, except that the Router keeps an isolated "Deu certo" with Support (signal `resolved`)."""
    answer = default_handler(call)
    if call.spec.agent == "router" and call.spec.context["message"] == "Deu certo":
        answer = {**answer, "route": "support", "topic": "device", "case_signal": "resolved"}
    return answer


def test_through_the_comparison_the_isolated_resolution_rule_reads_the_case_state(offline, settings):
    from merchant_assistant.api.schemas import CHALLENGE_EXAMPLES

    send, _, _, _ = jev_system(
        offline, settings, choices={"route": "support", "topic": "device", "case_signal": "resolved"},
        handler=support_on_resolution, with_index=True,
    )
    first = send(CHALLENGE_EXAMPLES[4], mechanism="llm")["message"]  # a device step: the case awaits the merchant
    assert first["resolution"]["state"] == "awaiting_customer"
    compared = send.compare("Deu certo", first["conversation_id"], "llm")
    assert {m: d["decision"]["route"] for m, d in compared["decisions"].items()} == {
        "llm": "acknowledgement", "jev": "acknowledgement"
    }
    done = send("Deu certo", first["conversation_id"], "llm", compared["comparison_id"])["message"]
    assert done["route"] == "acknowledgement"
    assert done["resolution"] == {"state": "resolved", "evidence": "customer_confirmed"}


def test_through_the_comparison_a_yes_label_with_nothing_waiting_is_other(offline, settings):
    def labelling_yes(call):
        answer = default_handler(call)
        return {**answer, "confirmation": "yes"} if call.spec.agent == "router" else answer

    send, _, _, _ = jev_system(offline, settings, handler=labelling_yes)
    compared = send.compare("Sim", None, "llm")
    assert compared["decisions"]["llm"]["decision"]["confirmation"] == "other"  # nothing waits in this conversation
