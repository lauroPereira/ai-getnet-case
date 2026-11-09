"""Regression coverage for cancellation status, confirmation, and long-conversation answers.

The tests use deterministic model responses and seeded synthetic sales without network calls.
"""

from __future__ import annotations

import sqlite3
import uuid

import pytest

from merchant_assistant.agents import cancellation
from merchant_assistant.agents.personality import courtesy_only, run_output_guard
from merchant_assistant.agents.router import enforce
from merchant_assistant.api.identity import Principal
from merchant_assistant.api.schemas import MessageRequest
from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.evaluation.scripted_policy import cancellation_filters
from merchant_assistant.evaluation.scripted_policy import handler as default_handler
from merchant_assistant.llm.scripted import ToolPlan
from merchant_assistant.orchestration.state import GraphState, KnowledgeResult, RouterDecision, SupportResult
from merchant_assistant.testing import merchant_headers, offline_orchestrator, token_headers
from merchant_assistant.tools.base import CustomerContext, ToolEnv
from merchant_assistant.tools.registry import ToolOutcome, execute

QA_DAY = "2026-11-07T10:00:00"
CLOCK = FixedClock(QA_DAY)
PROTOCOL = "SIM-BND-1988-001"  # the pending Visa enablement request of cliente1988 (seed)
CREDIT = "R$ 1.200,00"  # yesterday's credit sale, which already has a `requested` cancellation (seed)
PREFIX_TOOLS = {"get_complaint_history", "run_customer_healthcheck"}  # case opening of the support route, no model
COURTESY = "Por nada! Se precisar de mais alguma ajuda, estou à disposição."
SUPPORT_FIELDS = {
    "needs_selection": False,
    "missing": [],
    "escalate": False,
    "escalation_reason": None,
    "steps_given": [],
    "issue_verified_by_tool": False,
}


class Script:
    """The default scripted model, with per-message Router decisions, Support plans and Personality text."""

    def __init__(self, router=None, support=None, personality=None):
        self.router, self.support, self.personality = router or {}, support or {}, personality or {}
        self.personality_calls: dict[str, object] = {}

    def __call__(self, call):
        agent, message = call.spec.agent, call.spec.context.get("message")
        if agent == "router" and message in self.router:
            return {**default_handler(call), **self.router[message]}
        if agent == "customer_support" and message in self.support:
            plan = self.support[message]
            return plan() if callable(plan) else plan
        if agent == "personality" and message in self.personality:
            self.personality_calls[message] = call
            return {"answer": self.personality[message]}
        return default_handler(call)


def support_plan(calls: list[tuple[str, dict]], *points: str, escalate: bool = False) -> ToolPlan:
    reason = "data_conflict" if escalate else None
    return ToolPlan(
        calls,
        final=lambda _results: {
            **SUPPORT_FIELDS,
            "points": list(points),
            "escalate": escalate,
            "escalation_reason": reason,
        },
    )


@pytest.fixture
def make(settings):
    made = []

    def build(script: Script | None = None, **kwargs):
        orch, llm = offline_orchestrator(settings, handler=script or default_handler, clock=CLOCK, **kwargs)
        made.append(orch)
        return orch, llm

    yield build
    for orch in made:
        orch.close()


def say(orch, message: str, conversation_id: str | None = None):
    request_id = f"req_qa1_{uuid.uuid4().hex[:10]}"
    response = orch.handle(
        MessageRequest(message=message, user_id="cliente1988", conversation_id=conversation_id), request_id
    )
    return response, orch.trace(request_id)


def step(trace: dict, name: str) -> dict:
    return next(s for s in trace["steps"] if s["step"] == name)["detail"]


def rows(settings, sql: str, *args) -> list[dict]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


def account(settings) -> list[dict]:
    return rows(settings, "SELECT * FROM sale_cancellations WHERE customer_id='cliente1988' ORDER BY transaction_id")


def requests(settings) -> list[dict]:
    return rows(settings, "SELECT * FROM sale_cancellation_requests ORDER BY created_at, rowid")


# --- Cancellation status belongs to the sale asked about ----------------------------------------------------------


def test_the_lookup_identifies_each_sale_and_filters_to_the_one_named(settings, make):
    make()  # initializes the seeded sales
    conn = connect(settings.db_path)
    try:
        context = CustomerContext.for_principal(Principal.merchant("cliente1988"), "cliente1988", True)
        env = ToolEnv(conn, CLOCK, context)
        everything = execute("get_sale_cancellation_context", {"period": "yesterday"}, env).data
        parcelled = execute(
            "get_sale_cancellation_context", {"payment_type": "credit", "installments": 2}, env
        ).data
        link = execute("get_sale_cancellation_context", {"channel": "payment_link"}, env).data
        dated = execute("get_sale_cancellation_context", {"sale_date": "2026-11-01"}, env).data
    finally:
        conn.close()
    by_id = {s["sale_id"]: s for s in everything["sales"]}
    assert everything["selection"] is None and set(by_id) == {"sale_1988_0001", "sale_1988_0002", "sale_1988_0003"}
    assert by_id["sale_1988_0001"]["payment_type"] == "debit" and by_id["sale_1988_0001"]["cancellation"] is None
    assert by_id["sale_1988_0002"]["cancellation"]["status"] == "requested"
    assert by_id["sale_1988_0002"]["gross_amount"]["display"] == CREDIT
    assert [c["sale"]["payment_type"] for c in everything["cancellations"]] == ["credit"]  # each record, its sale
    [sale] = parcelled["sales"]  # not in the receivables schedule, found here (case 2)
    assert parcelled["selection"] == {"payment_type": "credit", "installments": 2}
    assert (sale["sale_id"], sale["sale_date"], sale["channel"]) == ("sale_1988_0005", "2026-11-05", "payment_link")
    assert sale["gross_amount"]["display"] == "R$ 200,00" and sale["cancellation"] is None
    assert parcelled["cancellations"] == []
    assert [s["sale_id"] for s in link["sales"]] == ["sale_1988_0004", "sale_1988_0005"]
    assert [s["sale_id"] for s in dated["sales"]] == ["sale_1988_0004"] and dated["date_from"] == "2026-11-01"


def test_case_1_the_debit_sale_waiting_in_another_conversation_has_no_cancellation(settings, make):
    status = "Qual o status do cancelamento da venda de débito de ontem?"
    observed = "O cancelamento da venda de débito de ontem, 06/11/2026, está com status solicitado."
    script = Script(
        support={status: lambda: support_plan(
            [("get_sale_cancellation_context", {"period": "yesterday", "payment_type": "debit"})], observed
        )},
        personality={status: observed},
    )
    orch, _ = make(script)
    say(orch, "Quero cancelar a venda de débito de ontem.")  # pending in another conversation, no yes
    [pending] = requests(settings)
    assert pending["sale_id"] == "sale_1988_0001" and pending["state"] == "pending_confirmation"
    before = account(settings)

    response, trace = say(orch, status)  # a new conversation
    assert "solicitado" not in response.answer and not cancellation.claims_status(response.answer)
    assert (
        "A venda de débito de R$ 150,00 de 06/11/2026 não tem cancelamento registrado. Há um pedido de cancelamento "
        "dela esperando a sua resposta, e nada foi cancelado."
    ) in response.answer
    assert step(trace, "output_guard")["cancellation_status_from_code"] is True
    assert observed not in response.answer
    assert account(settings) == before


def test_case_2_the_parcelled_sale_is_found_by_the_lookup_and_asked_for(settings, make):
    orch, _ = make()  # the scripted Support follows support.v10: it filters the lookup by what the merchant named
    before = account(settings)
    response, trace = say(orch, "Quero cancelar a venda de crédito parcelada em 2 vezes.")
    [row] = requests(settings)
    assert row["sale_id"] == "sale_1988_0005" and row["amount"] == 20000 and row["state"] == "pending_confirmation"
    assert "R$ 200,00" in response.answer and "05/11/2026" in response.answer and CREDIT not in response.answer
    assert '"sim"' in response.answer and not cancellation.promises_execution(response.answer)
    assert "não tem cancelamento registrado" not in response.answer  # the sale asked for has the request's line only
    assert trace["detail"]["tools"][-2:] == ["get_sale_cancellation_context", "request_sale_cancellation"]
    assert step(trace, "tool:get_sale_cancellation_context")["arguments"] == {
        "period": "last_7_days", "payment_type": "credit", "installments": 2
    }
    assert account(settings) == before


def test_cases_2_and_3_a_refused_request_and_the_status_never_describe_another_sale(settings, make):
    ask = "Quero cancelar a venda de crédito parcelada em 2 vezes."
    status = "Qual o status do cancelamento da venda de crédito parcelada em 2 vezes?"
    found = (
        "Encontrei uma venda no crédito em 2 vezes, de 06/11/2026, no valor bruto de R$ 1.200,00, que já tem um "
        "pedido de cancelamento registrado."
    )
    later = "A venda de crédito parcelada em 2 vezes continua com o cancelamento solicitado em 06/11/2026."
    script = Script(
        support={
            ask: lambda: support_plan(  # as observed: the schedule, then the credit sale of yesterday
                [
                    ("get_receivables_schedule", {"period": "yesterday"}),
                    ("request_sale_cancellation", {"sale_id": "sale_1988_0002"}),
                ],
                found,
            ),
            status: lambda: support_plan(
                [("get_sale_cancellation_context", {"payment_type": "credit", "installments": 2})], later
            ),
        },
        personality={ask: found, status: later},
    )
    orch, _ = make(script)
    before = account(settings)
    response, trace = say(orch, ask)
    assert requests(settings) == [] and account(settings) == before  # refused by the tool (already cancelled)
    assert response.answer == cancellation.LINES["not_requested"]["pt"]  # nothing about any sale
    assert CREDIT not in response.answer and "06/11/2026" not in response.answer
    assert step(trace, "output_guard")["cancellation_fixed_reply"] == "not_requested"

    response, trace = say(orch, status, response.conversation_id)
    assert "solicitado" not in response.answer and CREDIT not in response.answer
    assert response.answer == NO_PARCELLED
    assert account(settings) == before


def test_case_4_a_yes_after_the_request_expired_says_it_expired(settings, make):
    ask = "Quero cancelar a venda do link de pagamento de R$ 500,00."
    observed = (
        "Recebi sua confirmação. O pedido de cancelamento da venda de R$ 500,00 de 01/11/2026 está registrado como "
        "solicitado."
    )
    script = Script(
        router={"Sim": {"route": "support", "topic": "cancellation"}},  # nothing waits: the Router's own route
        support={
            ask: lambda: support_plan(
                [
                    ("get_sale_cancellation_context", {"channel": "payment_link"}),
                    ("request_sale_cancellation", {"sale_id": "sale_1988_0004"}),
                ],
                "Venda de R$ 500,00 em 01/11/2026 (link de pagamento).",
            ),
            "Sim": lambda: support_plan([("get_sale_cancellation_context", {"channel": "payment_link"})], observed),
        },
        personality={"Sim": observed},
    )
    orch, _ = make(script)
    before = account(settings)
    response, _ = say(orch, ask)
    conversation_id = response.conversation_id
    say(orch, "Ok, obrigado pela ajuda", conversation_id)
    response, _ = say(orch, "Como funciona o Pix?", conversation_id)  # the second turn without an answer
    assert requests(settings)[0]["state"] == "expired" and "expirou" in response.answer

    expired = (
        "O pedido de cancelamento da venda de R$ 500,00 de 01/11/2026 expirou sem confirmação, e nada foi cancelado."
    )
    line = cancellation.LINES["expired"]["pt"].format(amount="R$ 500,00", date="01/11/2026")
    response, trace = say(orch, "Sim", conversation_id)
    assert response.answer == line and expired in line  # the fixed line is the whole reply
    assert step(trace, "output_guard")["cancellation_fixed_reply"] == "closed"
    assert "confirm_sale_cancellation" not in trace["detail"]["tools"]
    response, _ = say(orch, "Sim", conversation_id)  # a second yes right after: the same answer
    assert response.answer == line
    assert requests(settings)[0]["state"] == "expired" and account(settings) == before

    say(orch, "Quanto vendi ontem?", conversation_id)  # another subject, then a bare yes: still that request (P3-5)
    response, _ = say(orch, "Sim", conversation_id)
    assert response.answer == line and account(settings) == before


def test_a_yes_after_a_no_says_the_request_was_declined(settings, make):
    orch, _ = make()
    before = account(settings)
    response, _ = say(orch, "Quero cancelar a venda Pix de ontem.")
    conversation_id = response.conversation_id
    say(orch, "Não", conversation_id)
    response, trace = say(orch, "Sim", conversation_id)
    assert "confirm_sale_cancellation" not in trace["detail"]["tools"]
    assert "O pedido de cancelamento da venda de R$ 80,00 de 06/11/2026 foi recusado, e nada foi cancelado." in (
        response.answer
    )
    assert requests(settings)[0]["state"] == "declined" and account(settings) == before


def test_case_5_the_pix_sale_declined_has_no_cancellation_and_the_case_is_still_announced(settings, make):
    status = "Qual o status do cancelamento da venda Pix de ontem?"
    observed = (
        "Encontrei duas solicitações de cancelamento, ambas com status requested, e não sei qual é a da venda Pix."
    )
    script = Script(
        support={status: lambda: support_plan(
            [("get_sale_cancellation_context", {"period": "yesterday", "payment_type": "pix"})], observed, escalate=True
        )},
        personality={status: observed},
    )
    orch, _ = make(script)
    before = account(settings)
    response, _ = say(orch, "Quero cancelar a venda Pix de ontem.")
    conversation_id = response.conversation_id
    say(orch, "Não", conversation_id)
    response, trace = say(orch, status, conversation_id)
    assert "requested" not in response.answer and not cancellation.claims_status(response.answer)
    assert (
        "A venda Pix de R$ 80,00 de 06/11/2026 não tem cancelamento registrado. O último pedido de cancelamento dela "
        "foi recusado, e nada foi cancelado."
    ) in response.answer
    assert response.handoff is not None and response.handoff.protocol in response.answer  # the case it opened
    assert account(settings) == before


REQUESTED_CREDIT = (
    "O cancelamento da venda de crédito de R$ 1.200,00 de 06/11/2026 está com status solicitado e ainda não foi "
    "processado."
)
NO_DEBIT = "A venda de débito de R$ 150,00 de 06/11/2026 não tem cancelamento registrado."
NO_PIX = "A venda Pix de R$ 80,00 de 06/11/2026 não tem cancelamento registrado."
NO_LINK_500 = "A venda de crédito de R$ 500,00 de 01/11/2026 não tem cancelamento registrado."
NO_PARCELLED = "A venda de crédito em 2 parcelas de R$ 200,00 de 05/11/2026 não tem cancelamento registrado."


def status_probe(make, message: str, arguments: dict, observed: str):
    """The Support looks up status with `arguments`; the scripted Personality returns `observed`."""
    script = Script(
        router={message: {"route": "support", "topic": "cancellation", "language": "pt"}},
        support={message: lambda: support_plan([("get_sale_cancellation_context", arguments)], observed)},
        personality={message: observed},
    )
    orch, _ = make(script)
    return orch


def test_the_real_requested_status_of_the_credit_sale_still_reaches_the_merchant(settings, make):
    orch, _ = make()
    response, trace = say(orch, "Qual o status do cancelamento da venda de crédito de ontem?")
    assert response.answer == REQUESTED_CREDIT and step(trace, "output_guard")["cancellation_status_from_code"]


def test_probe_b_the_amount_names_the_sale_and_without_it_every_candidate_is_listed(settings, make):
    message = "Qual o status do cancelamento da venda de R$ 500,00?"
    observed = "O cancelamento da venda de R$ 500,00 está solicitado."
    orch = status_probe(make, message, {"amount": 50000}, observed)
    response, trace = say(orch, message)
    assert response.answer == NO_LINK_500
    assert step(trace, "tool:get_sale_cancellation_context")["arguments"] == {"amount": 50000}

    orch = status_probe(make, message, {"period": "last_7_days"}, observed)  # the model left the amount out
    response, _ = say(orch, message)
    assert observed not in response.answer and response.answer.startswith("Encontrei 5 vendas com essas condições.")
    assert NO_LINK_500 in response.answer and REQUESTED_CREDIT in response.answer and NO_PIX in response.answer


def test_probe_a_two_cancellations_in_the_period_and_the_pix_sale_asked(settings, make):
    message = "Qual o status do cancelamento da venda Pix?"
    observed = "O cancelamento da venda Pix está com status solicitado."
    orch = status_probe(make, message, {"period": "yesterday"}, observed)
    response, _ = say(orch, "Quero cancelar a venda de débito de ontem.")
    say(orch, "Sim", response.conversation_id)  # a second cancellation in the period: the debit sale
    response, _ = say(orch, message)
    lines = response.answer.split("\n")
    assert observed not in lines
    assert lines[0] == "Encontrei 3 vendas com essas condições. O status de cancelamento de cada uma:"
    assert lines[2] == REQUESTED_CREDIT and lines[3] == NO_PIX
    assert lines[1].startswith(
        "O cancelamento da venda de débito de R$ 150,00 de 06/11/2026 está com status solicitado"
    ) and "Protocolo: CAN-" in lines[1]


def test_probe_c_a_mixed_selection_lists_both_sales_with_their_own_status(settings, make):
    message = "Qual o status do cancelamento da venda de crédito?"
    observed = "A venda de crédito continua com o cancelamento solicitado."
    orch = status_probe(make, message, {"payment_type": "credit"}, observed)
    response, _ = say(orch, message)
    assert response.answer.split("\n") == [
        "Encontrei 3 vendas com essas condições. O status de cancelamento de cada uma:",
        NO_LINK_500,
        NO_PARCELLED,
        REQUESTED_CREDIT,
    ]


@pytest.mark.parametrize(
    "observed",
    [
        "Estornamos a venda de débito de ontem.",
        "O cancelamento da venda de débito está pendente.",
        "O pedido foi aberto e está na fila.",
        "O cancelamento foi processado.",
        "O pedido foi aceito e encaminhado.",
        "Já pedi o cancelamento da venda de débito.",
        "The cancellation is pending.",
        "It was submitted and the sale was refunded.",
    ],
)
def test_paraphrases_of_a_cancellation_never_reach_the_merchant(settings, make, observed):
    message = "Qual o status do cancelamento da venda de débito de ontem?"
    orch = status_probe(make, message, {"period": "yesterday", "payment_type": "debit"}, observed)
    response, _ = say(orch, message)
    assert response.answer == NO_DEBIT and observed not in response.answer
    assert cancellation.claims_status(observed)  # and the word list, kept as an extra defense, knows it


def test_the_latest_request_and_the_closed_request_are_read_for_this_merchant_only(settings, make):
    orch, _ = make()
    response, _ = say(orch, "Quero cancelar a venda Pix de ontem.")
    conversation_id = response.conversation_id
    say(orch, "Não", conversation_id)
    conn = connect(settings.db_path)
    try:  # a later row of another merchant, in the same conversation and for the same sale
        conn.execute(
            "INSERT INTO sale_cancellation_requests (request_id, customer_id, sale_id, amount, sale_date, state, "
            "created_at, idempotency_key, conversation_id, turns_waited, updated_at) "
            "VALUES ('scr_other', 'cliente_demo_002', 'sale_1988_0003', 8000, '2026-11-06', 'pending_confirmation', "
            "'2026-11-07T23:00:00-03:00', 'other', ?, 0, '2026-11-07T23:00:00-03:00')",
            (conversation_id,),
        )
        conn.commit()
        assert cancellation.closed_request(conn, conversation_id, "cliente1988", "Sim")["status"] == "declined"
        context = CustomerContext.for_principal(Principal.merchant("cliente1988"), "cliente1988", True)
        data = execute("get_sale_cancellation_context", {"payment_type": "pix"}, ToolEnv(conn, CLOCK, context)).data
    finally:
        conn.close()
    assert data["sales"][0]["cancellation_request"]["state"] == "declined"
    response, _ = say(orch, "Sim", conversation_id)
    assert "foi recusado, e nada foi cancelado" in response.answer


@pytest.mark.parametrize(
    "text",
    [
        "O cancelamento da venda de débito de ontem, 06/11/2026, está com status solicitado.",
        "A venda continua com o cancelamento solicitado em 06/11/2026.",
        "Recebi sua confirmação. O pedido está registrado como solicitado.",
        "Encontrei duas solicitações de cancelamento, ambas com status requested.",
        "O cancelamento está em andamento.",
        "Pronto, venda cancelada!",
    ],
)
def test_statements_of_a_cancellation_in_progress_are_claims(text):
    assert cancellation.claims_status(text)


@pytest.mark.parametrize("key", ["expired", "declined_late", "not_requested", "not_requested_scope"])
def test_the_fixed_lines_are_not_claims(key):
    for language in ("pt", "en"):
        line = cancellation.LINES[key][language].format(amount="R$ 80,00", date="06/11/2026", protocol=None)
        assert not cancellation.claims_status(line), line
        assert not cancellation.claims_status(cancellation.STATUS_LINES["no_sale"][language])
    for note in cancellation._REQUEST_NOTE.values():
        sale = cancellation.STATUS_LINES["none"]["pt"].format(sale="Pix de R$ 80,00 de 06/11/2026")
        assert not cancellation.claims_status(sale + note["pt"]) and not cancellation.claims_status(note["en"])


def test_the_english_status_line_names_the_sale_in_order():
    sale = {"payment_type": "credit", "installments": 2, "sale_date": "2026-11-05",
            "gross_amount": {"display": "R$ 200,00"}, "cancellation": None, "cancellation_request": None}
    assert cancellation._sale_status(sale, "en") == (
        "The credit sale in 2 installments of R$ 200,00 on November 5, 2026 has no cancellation recorded."
    )
    assert cancellation._sale_status({**sale, "installments": 1, "payment_type": "pix"}, "en").startswith(
        "The Pix sale of R$ 200,00 on November 5, 2026"
    )



# --- Closed cancellation requests and human handoff ----------------------------------------------------------------

DECLINED_PIX = cancellation.LINES["declined_late"]["pt"].format(amount="R$ 80,00", date="06/11/2026")
PENDING_PIX = cancellation.LINES["pending_confirmation"]["pt"].format(amount="R$ 80,00", date="06/11/2026")


def test_an_operator_reply_after_a_yes_to_a_closed_request_reaches_the_merchant(settings, offline):
    """The closed request's fixed line never replaces a human reply."""
    client, orchestrator, _ = offline(
        handler=Script(router={"Sim": {"route": "human_handoff", "topic": None, "language": "pt"}}), clock=CLOCK
    )
    headers = merchant_headers(client)
    sent = client.post("/messages", json={"message": "Quero cancelar a venda Pix de ontem."}, headers=headers).json()
    conversation_id = sent["conversation_id"]
    client.post("/messages", json={"message": "Não", "conversation_id": conversation_id}, headers=headers)
    handed = client.post("/messages", json={"message": "Sim", "conversation_id": conversation_id}, headers=headers)
    body = handed.json()
    assert body["status"] == "handoff" and DECLINED_PIX in body["answer"]
    assert body["handoff"]["protocol"] in body["answer"]
    saved = orchestrator.review_graph().get_state({"configurable": {"thread_id": body["request_id"]}}).values
    assert saved and saved.get("cancellation_event") is None  # the closed request's event stays out of the resume
    operator = token_headers(client, Principal.operator("op_ana"))
    case = next(c for c in client.get("/v1/handoffs", headers=operator).json()["cases"]
                if c["protocol"] == body["handoff"]["protocol"])
    text = "Conferi aqui: a venda Pix segue ativa e nada foi cancelado."
    acted = client.post(f"/v1/handoffs/{case['case_id']}/actions", headers=operator,
                        json={"action": "reply", "idempotency_key": "key-qa-r3-operator", "text": text})
    assert acted.status_code == 200, acted.text
    last = client.get(f"/v1/conversations/{conversation_id}", headers=headers).json()["messages"][-1]
    assert last["via"] == "operator" and last["text"] == text
    assert account(settings) == [r for r in account(settings) if r["transaction_id"] != "sale_1988_0003"]


def test_the_status_beside_another_subject_asks_for_that_question_separately(settings, make):
    """A status lookup and a separate sales question keep their own answers."""
    message = "Qual o status do cancelamento da venda Pix de ontem e quanto vou receber da venda de crédito?"
    said = ["A venda Pix tem cancelamento solicitado.", "Da venda de crédito você recebe R$ 1.162,20."]
    script = Script(
        router={message: {"route": "support", "topic": "cancellation", "language": "pt"}},
        support={message: lambda: support_plan(
            [("get_sale_cancellation_context", {"period": "yesterday", "payment_type": "pix"}),
             ("get_receivables_schedule", {"period": "yesterday"})],
            *said,
        )},
        personality={message: " ".join(said)},
    )
    orch, _ = make(script)
    response, _ = say(orch, message)
    assert response.answer.split("\n") == [NO_PIX, cancellation.STATUS_LINES["rest"]["pt"]]  # no text of the model


def test_a_request_and_a_status_in_the_same_turn_both_come_from_code(settings, make):
    """The looked-up sale gets its status line; the requested sale gets its confirmation line."""
    message = "Qual o status do cancelamento da venda de débito de ontem? E quero cancelar a venda Pix de ontem."
    said = ["A venda de débito está com cancelamento solicitado.", "Pedi o cancelamento da venda Pix."]
    script = Script(
        router={message: {"route": "support", "topic": "cancellation", "language": "pt"}},
        support={message: lambda: support_plan(
            [("get_sale_cancellation_context", {"period": "yesterday", "payment_type": "debit"}),
             ("request_sale_cancellation", {"sale_id": "sale_1988_0003"})],
            *said,
        )},
        personality={message: " ".join(said)},
    )
    orch, _ = make(script)
    before = account(settings)
    response, _ = say(orch, message)
    assert response.answer.split("\n") == [NO_DEBIT, PENDING_PIX]
    [row] = requests(settings)
    assert row["sale_id"] == "sale_1988_0003" and row["state"] == "pending_confirmation"
    assert account(settings) == before


def test_after_other_subjects_a_bare_yes_still_meets_the_closed_request_and_a_bare_no_does_not(settings, make):
    """Only an affirmative answer confirms later; an immediate negative keeps the fixed line."""
    orch, _ = make()
    response, _ = say(orch, "Quero cancelar a venda Pix de ontem.")
    conversation_id = response.conversation_id
    say(orch, "Não", conversation_id)
    response, _ = say(orch, "Não, obrigado", conversation_id)  # the turn right after the refusal
    assert response.answer == DECLINED_PIX

    say(orch, "Como funciona o Pix?", conversation_id)
    say(orch, "O que é a Get Smart?", conversation_id)
    response, trace = say(orch, "Não, obrigado", conversation_id)
    assert DECLINED_PIX not in response.answer and "cancellation_fixed_reply" not in step(trace, "output_guard")
    response, _ = say(orch, "Sim, obrigado", conversation_id)
    assert response.answer == DECLINED_PIX


def test_a_no_answered_with_a_paraphrase_gets_the_fixed_line(settings, make):
    """A negative answer uses the fixed line instead of a paraphrase claiming completion."""
    orch, _ = make(Script(personality={"Não": "Combinado, o cancelamento foi registrado e a venda foi estornada."}))
    response, _ = say(orch, "Quero cancelar a venda Pix de ontem.")
    response, trace = say(orch, "Não", response.conversation_id)
    assert "estornada" not in response.answer and "registrado" not in response.answer
    assert cancellation.LINES["declined"]["pt"].format(amount="R$ 80,00", date="06/11/2026") in response.answer
    assert step(trace, "output_guard")["cancellation_promise"] is True


LINK_ASK = "Quero cancelar a venda do link de pagamento de R$ 500,00."
EXPIRED_LINK = cancellation.LINES["expired"]["pt"].format(amount="R$ 500,00", date="01/11/2026")


def link_request_plan():
    return support_plan(
        [("get_sale_cancellation_context", {"channel": "payment_link", "amount": 50000}),
         ("request_sale_cancellation", {"sale_id": "sale_1988_0004"})],
        "Venda de R$ 500,00 em 01/11/2026.",
    )


def test_the_turn_that_expires_the_request_keeps_its_answer_and_adds_the_line(settings, make):
    """When a request expires, the answer to another question in the same turn survives."""
    payout = "Meu repasse de ontem foi enviado?"
    said = "Seu repasse de ontem foi enviado e processado."
    script = Script(
        router={payout: {"route": "support", "topic": "receivables", "language": "pt"}},
        support={LINK_ASK: link_request_plan},
        personality={payout: said},
    )
    orch, _ = make(script)
    response, _ = say(orch, LINK_ASK)
    say(orch, "Ok, obrigado pela ajuda", response.conversation_id)
    response, trace = say(orch, payout, response.conversation_id)
    assert requests(settings)[0]["state"] == "expired"
    assert response.answer == f"{said}\n{EXPIRED_LINK}"
    assert "cancellation_promise" not in step(trace, "output_guard")


def _escalation_draft(text):
    def handler(call):
        if call.spec.agent == "escalation":
            return {"summary": "Lojista pediu atendimento.", "pending_question": "Responder.", "draft_reply": text}
        return Script(support={LINK_ASK: link_request_plan})(call)

    return handler


@pytest.mark.parametrize(
    ("action", "text"),
    [
        ("reply", "Ola! Seu atendimento foi registrado e a segunda via da maquininha foi enviada hoje."),
        ("approve", "Seu atendimento foi registrado e a segunda via da maquininha foi enviada hoje."),
    ],
)
def test_a_human_agents_text_is_delivered_untouched_after_the_request_expired(settings, offline, action, text):
    """An operator reply or approved draft is delivered unchanged after request expiration."""
    client, _, _ = offline(handler=_escalation_draft(text if action == "approve" else "Rascunho."), clock=CLOCK)
    headers = merchant_headers(client)
    sent = client.post("/messages", json={"message": LINK_ASK}, headers=headers).json()
    conversation_id = sent["conversation_id"]
    for message in ("Ok, obrigado pela ajuda", "Quero falar com um atendente humano agora."):
        body = client.post("/messages", json={"message": message, "conversation_id": conversation_id},
                           headers=headers).json()
    assert body["status"] == "handoff" and requests(settings)[0]["state"] == "expired"
    operator = token_headers(client, Principal.operator("op_ana"))
    case = next(c for c in client.get("/v1/handoffs", headers=operator).json()["cases"]
                if c["protocol"] == body["handoff"]["protocol"])
    action_body = {"action": action, "idempotency_key": f"key-qa-r4-{action}"} | ({"text": text} if action == "reply"
                                                                                  else {})
    acted = client.post(f"/v1/handoffs/{case['case_id']}/actions", headers=operator, json=action_body)
    assert acted.status_code == 200, acted.text
    last = client.get(f"/v1/conversations/{conversation_id}", headers=headers).json()["messages"][-1]
    assert last["via"] == "operator" and last["text"] == text


def test_the_sentence_about_the_rest_needs_points_and_another_tool_that_answered(settings, make):
    """Approval note: a failed tool, or another tool with no point written, does not bring the fixed sentence."""
    message = "Qual o status do cancelamento da venda Pix de ontem?"
    pix = ("get_sale_cancellation_context", {"period": "yesterday", "payment_type": "pix"})
    schedule = ("get_receivables_schedule", {"period": "yesterday"})
    plans = iter([
        lambda: support_plan([schedule, pix], "A venda Pix está com cancelamento solicitado."),  # schedule fails
        lambda: ToolPlan(
            [pix, schedule], final=lambda _r: {**SUPPORT_FIELDS, "points": [], "missing": ["Qual venda?"]}
        ),
    ])
    script = Script(router={message: {"route": "support", "topic": "cancellation", "language": "pt"}},
                    support={message: lambda: next(plans)()})
    orch, _ = make(script)
    orch.faults.update(get_receivables_schedule="UNAVAILABLE")
    response, trace = say(orch, message)
    assert step(trace, "tool:get_receivables_schedule")["error"] and response.answer == NO_PIX
    orch.faults.clear()
    response, trace = say(orch, message)
    assert not step(trace, "tool:get_receivables_schedule")["error"]
    assert response.answer.split("\n") == [NO_PIX, "Qual venda?"]


def test_two_lookups_and_a_request_in_one_turn_give_each_sale_its_own_line(settings, make):
    """Each looked-up sale gets one status line, except the sale requested for cancellation."""
    message = "Qual o status do cancelamento da venda de débito de ontem? E quero cancelar a venda Pix de ontem."
    script = Script(
        router={message: {"route": "support", "topic": "cancellation", "language": "pt"}},
        support={message: lambda: support_plan(
            [("get_sale_cancellation_context", {"period": "yesterday", "payment_type": "debit"}),
             ("get_sale_cancellation_context", {"period": "yesterday", "payment_type": "pix"}),
             ("request_sale_cancellation", {"sale_id": "sale_1988_0003"})],
            "A venda de débito está com cancelamento solicitado.",
        )},
        personality={message: "A venda de débito está com cancelamento solicitado."},
    )
    orch, _ = make(script)
    response, _ = say(orch, message)
    assert response.answer.split("\n") == [NO_DEBIT, PENDING_PIX]


def test_an_operators_reject_reruns_support_and_the_status_comes_from_code(settings, offline):
    """A rejection without operator text reruns Support and retains the code-derived status."""
    def handler(call):
        if call.spec.agent == "customer_support" and call.spec.context.get("operator_instruction"):
            return support_plan([("get_sale_cancellation_context", {"period": "yesterday", "payment_type": "pix"})],
                                "A venda Pix está com cancelamento solicitado.")
        return default_handler(call)

    client, _, _ = offline(handler=handler, clock=CLOCK)
    headers = merchant_headers(client)
    body = client.post("/messages", json={"message": "Quero falar com um atendente"}, headers=headers).json()
    operator = token_headers(client, Principal.operator("op_ana"))
    case = next(c for c in client.get("/v1/handoffs", headers=operator).json()["cases"]
                if c["protocol"] == body["handoff"]["protocol"])
    acted = client.post(f"/v1/handoffs/{case['case_id']}/actions", headers=operator, json={
        "action": "reject", "idempotency_key": "key-qa-r4-reject",
        "text": "Consulte de novo o status da venda Pix de ontem antes de responder.",
    })
    assert acted.status_code == 200, acted.text
    last = client.get(f"/v1/conversations/{body['conversation_id']}", headers=headers).json()["messages"][-1]
    assert last["via"] == "operator" and last["text"] == NO_PIX


def test_the_guard_never_replaces_an_operator_reply_with_the_closed_requests_line():
    """The output guard leaves a resumed turn's human reply intact."""
    closed = {"request_id": "scr_x", "status": "declined", "late": True, "protocol": None,
              "sale": {"sale_id": "sale_1988_0003", "sale_date": "2026-11-06", "amount": {"display": "R$ 80,00"}}}
    text = "Conferi aqui: a venda Pix segue ativa."
    state = GraphState(
        request_id="req_x", conversation_id="conv_x", user_id="cliente1988", customer_known=True, message="Sim",
        decision=RouterDecision(route="human_handoff", language="pt", topic=None, intents=[], safety="none",
                                clarification_question=None, case_signal="none"),
        operator={"action": "reply", "text": text}, draft_answer=text, cancellation_event=closed,
    )
    assert run_output_guard(state, _context())["answer"].startswith(text)
    # an operator's "reject" reruns Support, which may look the status up: the human turn is still not replaced
    lookup = ToolOutcome("get_sale_cancellation_context", {}, True, {"sales": [_sale(80)]})
    assert run_output_guard(state, _context(lookup))["answer"].startswith(text)


def _sale(n: int, status: str | None = None) -> dict:
    return {
        "sale_id": f"sale_{n}", "sale_date": "2026-11-06", "payment_type": "debit", "installments": 1,
        "channel": "pos", "gross_amount": {"display": f"R$ {n},00"},
        "cancellation": {"status": status} if status else None, "cancellation_request": None,
    }


def _context(*outcomes):
    from types import SimpleNamespace

    return SimpleNamespace(outcomes=list(outcomes), step_notes={}, clock=CLOCK)


def test_the_block_lists_eight_sales_and_counts_the_rest():
    lookup = ToolOutcome("get_sale_cancellation_context", {}, True, {"sales": [_sale(n) for n in range(10, 20)]})
    lines = cancellation.status_block(_context(lookup), "pt").split("\n")
    assert lines[0] == "Encontrei 10 vendas com essas condições. O status de cancelamento de cada uma:"
    assert len(lines) == 1 + cancellation.STATUS_LIMIT + 1 and lines[8].startswith("A venda de débito de R$ 17,00")
    assert lines[-1] == cancellation.STATUS_LINES["more"]["pt"].format(n=2)


def test_the_block_keeps_the_official_points_and_what_support_still_asks():
    lookup = ToolOutcome("get_sale_cancellation_context", {}, True, {"sales": [_sale(80)]})
    state = GraphState(
        request_id="req_x", conversation_id="conv_x", user_id="cliente1988", customer_known=True,
        message="Qual o status do cancelamento?",
        decision=RouterDecision(route="knowledge_and_support", language="pt", topic="cancellation", intents=[],
                                safety="none", clarification_question=None, case_signal="none"),
        knowledge=KnowledgeResult(mode="rag", points=["O cancelamento segue a política oficial."],
                                  evidence_sufficient=True),
        support=SupportResult(points=["O cancelamento está solicitado.", "Sua maquininha está online."],
                              needs_selection=False, missing=["Qual é a data da venda?"], escalate=False,
                              escalation_reason=None,
                              tools_used=["get_sale_cancellation_context", "get_device_status"],
                              tools_ok=["get_sale_cancellation_context", "get_device_status"]),
        draft_answer="O cancelamento está solicitado.",
    )
    answer = run_output_guard(state, _context(lookup))["answer"]
    assert answer.split("\n") == [
        "O cancelamento segue a política oficial.",
        "A venda de débito de R$ 80,00 de 06/11/2026 não tem cancelamento registrado.",
        "Qual é a data da venda?",
        cancellation.STATUS_LINES["rest"]["pt"],
    ]


@pytest.mark.parametrize(
    ("status", "pt", "en"),
    [
        ("rejected", "foi recusado, e a venda não foi cancelada.", "was rejected, and the sale was not cancelled."),
        ("unknown", "Não consegui confirmar a situação do cancelamento", "I couldn't confirm the state of the"),
        ("weird_status", "Não consegui confirmar a situação do cancelamento", "I couldn't confirm the state of the"),
    ],
)
def test_other_statuses_are_written_in_words_never_raw(status, pt, en):
    line_pt, line_en = (cancellation._sale_status(_sale(80, status), language) for language in ("pt", "en"))
    assert pt in line_pt and en in line_en and status not in line_pt
    assert status == "rejected" or status not in line_en  # "was rejected" is English, not the raw value


# --- Confirmation line appears once across quote variants ---------------------------------------------------------


@pytest.mark.parametrize("quotes", [("“", "”"), ('"', '"')])
def test_the_confirmation_line_is_not_repeated_after_curly_or_straight_quotes(settings, make, quotes):
    ask = "Quero cancelar a venda Pix de ontem."
    left, right = quotes
    model = (
        f"Para confirmar o cancelamento da venda de R$ 80,00 de 06/11/2026, responda {left}sim{right}. Para manter a "
        f"venda, responda {left}não{right}. Nada foi cancelado ainda."
    )
    orch, _ = make(Script(personality={ask: model}))
    response, _ = say(orch, ask)
    line = cancellation.LINES["pending_confirmation"]["pt"].format(amount="R$ 80,00", date="06/11/2026")
    assert cancellation.normalized(response.answer).count(cancellation.normalized(line)) == 1
    assert response.answer == line  # a request turn gives the fixed line alone


@pytest.mark.parametrize(
    "variant",
    ["\u2018sim\u2019", "\u00absim\u00bb", "\u201esim\u201c", "'sim'", "*\"sim\"*", "_\"sim\"_", "**\u201csim\u201d**"],
)
def test_every_quote_mark_and_emphasis_counts_as_the_same_line(variant):
    line = 'Para confirmar, responda "sim". Nada foi cancelado ainda.'
    draft = f"Para confirmar, responda {variant}. Nada foi cancelado ainda."
    assert cancellation.contains_line(draft, line), draft


QA_R2_REQUESTS = [  # scripted request variants that must resolve to the fixed confirmation line
    ("Quero cancelar a venda de débito de ontem.", "sale_1988_0001", "R$ 150,00", "06/11/2026",
     "Para confirmar o cancelamento da venda de R$ 150,00 de ontem (06/11/2026), responda “sim”. Para manter a "
     "venda, responda “não”. Nada foi cancelado ainda."),
    ("Quero cancelar a venda de débito de ontem.", "sale_1988_0001", "R$ 150,00", "06/11/2026",
     "Registrei a solicitação para cancelar a venda de débito de R$ 150,00, de 06/11/2026. Nada foi cancelado ainda. "
     "Para confirmar o cancelamento, responda “sim”."),
    ("Quero cancelar a venda de crédito parcelada em 2 vezes.", "sale_1988_0005", "R$ 200,00", "05/11/2026",
     "Encontrei a venda de crédito parcelada em 2 vezes, de 05/11/2026, no valor de R$ 200,00. Ela ainda não foi "
     "cancelada. Para confirmar o cancelamento, responda “sim”."),
    ("Quero cancelar a venda do link de pagamento de R$ 500,00.", "sale_1988_0004", "R$ 500,00", "01/11/2026",
     "Encontrei a venda do link de pagamento de R$ 500,00. Registrei o pedido, mas nada foi cancelado ainda. Para "
     "confirmar o cancelamento, responda “sim”."),
    ("Quero cancelar a venda do link de pagamento de R$ 500,00.", "sale_1988_0004", "R$ 500,00", "01/11/2026",
     "Registrei a solicitação. Responda “sim” para confirmar o cancelamento ou “não” para manter a venda."),
    ("Quero cancelar a venda Pix de ontem.", "sale_1988_0003", "R$ 80,00", "06/11/2026",
     "Registrei o pedido para cancelar a venda Pix de R$ 80,00. Para confirmar o cancelamento, responda “sim”."),
    ("Quero cancelar a venda Pix de ontem.", "sale_1988_0003", "R$ 80,00", "06/11/2026",
     "A venda Pix de R$ 80,00, de 06/11/2026, ainda não foi cancelada. Há uma solicitação aguardando sua confirmação. "
     "Para confirmar o cancelamento, responda “sim”."),
    ("Sim", "sale_1988_0001", "R$ 150,00", "06/11/2026",
     "Encontrei a venda de débito de R$ 150,00, de 06/11/2026. Para confirmar o cancelamento, responda exatamente "
     "“sim” em uma mensagem separada. Nada foi cancelado ainda."),
]


@pytest.mark.parametrize(("message", "sale_id", "amount", "day", "model"), QA_R2_REQUESTS)
def test_a_request_asks_for_the_yes_once_whatever_the_model_wrote(settings, make, message, sale_id, amount, day, model):
    """A turn that leaves a request waiting answers with the fixed line alone."""
    arguments = cancellation_filters(message) if message != "Sim" else {"period": "yesterday", "payment_type": "debit"}
    lookup = ("get_sale_cancellation_context", arguments)  # as support.v10 asks
    plan = lambda: support_plan([lookup, ("request_sale_cancellation", {"sale_id": sale_id})], model)  # noqa: E731
    router = {message: {"route": "support", "topic": "cancellation", "language": "pt"}}
    orch, _ = make(Script(router=router, support={message: plan}, personality={message: model}))
    response, trace = say(orch, message)
    line = cancellation.LINES["pending_confirmation"]["pt"].format(amount=amount, date=day)
    assert response.answer == line and model not in response.answer
    assert step(trace, "output_guard")["cancellation_request_from_code"] is True
    assert requests(settings)[0]["state"] == "pending_confirmation"


def test_a_reply_without_the_line_still_gets_it():
    view = {"status": "pending_confirmation", "message": 'Responda "sim".', "protocol": None}
    from merchant_assistant.agents.personality import _with_cancellation_line

    assert _with_cancellation_line("Encontrei a venda.", view) == 'Encontrei a venda.\nResponda "sim".'
    assert _with_cancellation_line("Encontrei a venda. Responda “sim”.", view).count("sim") == 1


# --- Questions remain answerable after a long run of courtesies ---------------------------------------------------

TURN_2 = "Qual o status da habilitação Visa e quanto vendi ontem?"
GET_TAP = "O que é a Get Tap?"
LAST = "Qual era o protocolo e o valor da venda de crédito que você me passou no começo?"
TURN_26 = (
    "Obrigado! Antes de encerrar, só me lembra: qual foi o protocolo e o valor da venda de crédito que você me disse "
    "lá no começo da nossa conversa?"
)
TURN_27 = (
    "Só pra eu anotar: qual foi o protocolo e o valor da venda de crédito que você me passou no começo da conversa?"
)
PRODUCT_QUESTIONS = (
    "Como funciona o Pix?",
    "Como funciona a antecipação?",
    "O que é a Get Smart?",
    "Como funciona o link de pagamento?",
    "A maquininha aceita aproximação?",
    "O que é a Get Clássica?",
    "Como uso o Pix na maquininha?",
    "A antecipação tem custo?",
    "O link de pagamento aceita parcelado?",
    "Como recebo pelo WhatsApp?",
)
VALUE_TOOLS = [("get_enablement_requests", {"scheme": "visa"}), ("get_receivables_schedule", {"period": "yesterday"})]


def qa_message(n: int) -> str:
    """Builds a long conversation with an early lookup, intervening product questions, and later follow-ups."""
    if n == 1:
        return "Olá"
    if n == 2:
        return TURN_2
    if n <= 24:
        if n % 2 == 0:
            return "Obrigado!"
        return GET_TAP if n == 17 else PRODUCT_QUESTIONS[(n - 3) // 2 - (n > 17)]
    return {25: LAST, 26: TURN_26, 27: TURN_27}[n]


def from_register(results=None):
    """A Support that answers from the facts recorded earlier in the conversation, as its prompt allows; the values are
    read from the facts block of its own instructions."""

    def plan(call):
        import re

        facts = re.findall(r"^- (\w+): (.+?) \(from [a-z_]+\)$", call.spec.instructions, re.M)
        protocol = next(v for k, v in facts if k == "protocol" and v.startswith("SIM-BND"))
        amount = next(v for k, v in facts if k == "amount" and v == CREDIT)
        said = f"O protocolo é {protocol} e a venda de crédito foi de {amount}."
        return support_plan(results or [], said)

    return plan


class QAScript(Script):
    def __init__(self):
        cite = "O protocolo da habilitação Visa é SIM-BND-1988-001 e a venda de crédito foi de R$ 1.200,00."
        super().__init__(
            router={
                TURN_2: {"route": "support", "topic": "enablement"},
                GET_TAP: {"route": "knowledge", "topic": None},
                LAST: {"route": "support", "topic": "enablement"},
                TURN_26: {"route": "acknowledgement", "topic": None, "case_signal": "thanks_only"},
                TURN_27: {"route": "acknowledgement", "topic": None, "case_signal": "none"},
            },
            support={
                TURN_2: lambda: support_plan(VALUE_TOOLS, "A habilitação Visa está pendente."),
                LAST: lambda: support_plan(VALUE_TOOLS, cite),  # tools verify the earlier values again
            },
            personality={  # courtesy reply after the product questions
                GET_TAP: "Por nada! Fico à disposição se precisar de mais alguma ajuda.",
                TURN_26: COURTESY,
                TURN_27: COURTESY,
            },
        )

    def __call__(self, call):
        message = call.spec.context.get("message")
        if call.spec.agent == "customer_support" and message == TURN_26:  # the register, no tool
            return from_register()(call)
        if call.spec.agent == "customer_support" and message == TURN_27:  # the tools fail: the register answers
            return from_register(VALUE_TOOLS)(call)
        return super().__call__(call)


def test_turns_17_26_and_27_of_the_long_conversation_answer_from_knowledge_and_the_register(settings, make):
    script = QAScript()
    orch, _ = make(script)
    conversation_id, turns = None, {}
    for n in range(1, 28):
        if n == 27:  # the value tools are unavailable in this turn
            orch.faults.update(get_enablement_requests="UNAVAILABLE", get_receivables_schedule="UNAVAILABLE")
        response, trace = say(orch, qa_message(n), conversation_id)
        conversation_id = response.conversation_id
        turns[n] = (response, trace)

    # turn 17: the Knowledge answer, not the thanks the Personality wrote
    response, trace = turns[17]
    assert step(trace, "router")["route"] == "knowledge" and "Por nada" not in response.answer
    assert not courtesy_only(response.answer) and step(trace, "output_guard")["courtesy_only"] is True
    assert GET_TAP in script.personality_calls[GET_TAP].spec.instructions  # personality.v7 reads the message
    assert step(trace, "personality")["prompt"] == "personality@7"

    # turn 25: the values are verified by tools in this turn
    response, trace = turns[25]
    assert PROTOCOL in response.answer and CREDIT in response.answer
    assert {"get_enablement_requests", "get_receivables_schedule"} <= set(trace["detail"]["tools"])

    # turns 26 and 27: labelled `acknowledgement`, answered by the Support from the register
    for n in (26, 27):
        response, trace = turns[n]
        router = step(trace, "router")
        assert router["route"] == "support" and router["rule"] == "question_not_acknowledgement", n
        assert PROTOCOL in response.answer and CREDIT in response.answer, n
        assert "Por nada" not in response.answer and trace["detail"]["output_violations"] == [], n
        assert step(trace, "output_guard")["courtesy_only"] is True, n
        assert qa_message(n) in script.personality_calls[qa_message(n)].spec.instructions, n
    assert not {"get_enablement_requests", "get_receivables_schedule"} & set(turns[26][1]["detail"]["tools"])
    assert set(turns[26][1]["detail"]["tools"]) <= PREFIX_TOOLS
    failed = [s for s in turns[27][1]["steps"] if s["step"].startswith("tool:get_") and s["detail"]["error"]]
    assert {s["step"] for s in failed} == {"tool:get_enablement_requests", "tool:get_receivables_schedule"}
    # the facts the guard accepted were recorded by turn 2 (and 25), never by the failed turn
    facts = rows(settings, "SELECT kind, value, source_tool FROM conversation_facts WHERE conversation_id=?",
                 conversation_id)
    assert ("protocol", PROTOCOL, "get_enablement_requests") in {(f["kind"], f["value"], f["source_tool"])
                                                                 for f in facts}


def test_a_thanks_is_still_an_acknowledgement_and_a_question_is_not():
    def decision(route: str, safety: str = "none") -> RouterDecision:
        return RouterDecision(
            route=route, language="pt", topic=None, intents=[], safety=safety, clarification_question=None,
            case_signal="thanks_only",
        )

    assert enforce(decision("acknowledgement"), message="Obrigado!").route == "acknowledgement"
    asked = enforce(decision("acknowledgement"), message=TURN_26)
    assert (asked.route, asked.topic) == ("support", "general")
    assert enforce(decision("acknowledgement", "unsafe"), message="Obrigado?").route == "out_of_scope"
    assert enforce(decision("knowledge"), message=GET_TAP).route == "knowledge"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (COURTESY, True),
        ("Por nada! Fico à disposição se precisar de mais alguma ajuda.", True),
        ("You're welcome! Let me know if you need anything else.", True),
        ("De nada, fico feliz em ajudar!", True),
        ("Por nada, até mais!", True),
        ("Disponha! Tenha um ótimo dia!", True),
        ("Por nada! Quer saber mais alguma coisa?", True),
        ("Obrigado você! Estou aqui para ajudar.", True),
        ("A Get Tap transforma o celular em maquininha. Se precisar, estou aqui.", False),
        (f"O protocolo é {PROTOCOL}. Por nada!", False),
        ("", False),
    ],
)
def test_a_reply_made_only_of_courtesies_is_recognized(text, expected):
    assert courtesy_only(text) is expected


# --- A sales question remains on the normal support-answer path ----------------------------------------------------

SALES = "Quanto vendi ontem?"
SALES_SAID = "Ontem você teve três vendas: débito de R$ 150,00, crédito de R$ 1.200,00 e Pix de R$ 80,00."
STATUS_OF_YESTERDAY = [
    "Encontrei 3 vendas com essas condições. O status de cancelamento de cada uma:", NO_DEBIT, REQUESTED_CREDIT, NO_PIX
]


def sales_script(said: str = SALES_SAID) -> Script:
    """Routes a sales question to Support and looks up yesterday's cancellation status."""
    return Script(
        router={SALES: {"route": "support", "topic": "receivables", "language": "pt"}},
        support={SALES: lambda: support_plan([("get_sale_cancellation_context", {"period": "yesterday"})], said)},
        personality={SALES: said},
    )


def test_a_sales_question_that_looked_the_status_up_is_answered_by_the_normal_flow(settings, make):
    script = sales_script()
    orch, _ = make(script)
    response, trace = say(orch, SALES)
    assert "get_sale_cancellation_context" in trace["detail"]["tools"]
    assert response.answer == SALES_SAID  # the model's reply, without the block written by code
    assert "cancellation_status_from_code" not in step(trace, "output_guard")
    assert "cancellation_status" not in script.personality_calls[SALES].spec.context["contributions"]


def test_the_output_guard_still_checks_the_sales_reply(settings, make):
    invented = "Ontem você vendeu R$ 9.999,00."
    orch, _ = make(sales_script(invented))
    response, trace = say(orch, SALES)
    assert "R$ 9.999,00" not in response.answer and step(trace, "output_guard")["violations"]
    assert "cancellation_status_from_code" not in step(trace, "output_guard")


def test_the_same_lookup_for_a_status_question_keeps_the_block(settings, make):
    message = "Qual o status do cancelamento da venda de ontem?"
    orch = status_probe(make, message, {"period": "yesterday"}, "As vendas de ontem estão com cancelamento solicitado.")
    response, trace = say(orch, message)
    assert response.answer.split("\n") == STATUS_OF_YESTERDAY
    assert step(trace, "output_guard")["cancellation_status_from_code"] is True


def test_after_a_request_closed_in_the_conversation_the_sales_question_gets_the_block(settings, make):
    orch, _ = make(sales_script())
    response, _ = say(orch, "Quero cancelar a venda Pix de ontem.")
    conversation_id = response.conversation_id
    say(orch, "Não", conversation_id)
    say(orch, "Como funciona o Pix?", conversation_id)
    assert requests(settings)[0]["state"] == "declined"
    response, trace = say(orch, SALES, conversation_id)
    assert SALES_SAID not in response.answer and step(trace, "output_guard")["cancellation_status_from_code"] is True
    assert response.answer.split("\n")[:3] == STATUS_OF_YESTERDAY[:3]
    assert response.answer.split("\n")[3].startswith(NO_PIX + " O último pedido de cancelamento dela foi recusado")


def test_with_a_request_waiting_the_sales_question_gets_the_block(settings, make):
    orch, _ = make(sales_script())
    response, _ = say(orch, "Quero cancelar a venda Pix de ontem.")
    response, trace = say(orch, SALES, response.conversation_id)
    assert requests(settings)[0]["state"] == "pending_confirmation"
    assert SALES_SAID not in response.answer and step(trace, "output_guard")["cancellation_status_from_code"] is True
    assert response.answer.startswith(STATUS_OF_YESTERDAY[0]) and PENDING_PIX in response.answer


def test_a_request_in_the_turn_makes_it_about_a_cancellation_whatever_the_topic(settings, make):
    message = "Quero cancelar a venda Pix de ontem."
    script = Script(
        router={message: {"route": "support", "topic": "general", "language": "pt"}},
        support={message: lambda: support_plan(
            [("get_sale_cancellation_context", {"period": "yesterday"}),
             ("request_sale_cancellation", {"sale_id": "sale_1988_0003"})],
            "Pedi o cancelamento da venda Pix.",
        )},
    )
    orch, _ = make(script)
    response, _ = say(orch, message)
    assert response.answer.split("\n") == [
        "Encontrei 2 vendas com essas condições. O status de cancelamento de cada uma:",
        NO_DEBIT,
        REQUESTED_CREDIT,
        PENDING_PIX,
    ]


# --- Cancellation mentions require matching status evidence --------------------------------------------------------

PIX_STATUS = "Qual o status do cancelamento da venda Pix de ontem?"
PIX_SAID = "A venda Pix está com cancelamento solicitado."
PIX_CLAIM = "A venda Pix está com status solicitado e em análise."  # a claim with no mention of a cancellation
PIX_LOOKUP = ("get_sale_cancellation_context", {"period": "yesterday", "payment_type": "pix"})


def pix_status_script(message: str, router: dict) -> Script:
    return Script(
        router={message: {"language": "pt", **router}},
        support={message: lambda: support_plan([PIX_LOOKUP], PIX_CLAIM)},
        personality={message: PIX_CLAIM},
    )


@pytest.mark.parametrize("topic", ["receivables", "general", "pricing"])
def test_s1_a_status_question_with_another_topic_gets_the_status_from_code(settings, make, topic):
    orch, _ = make(pix_status_script(PIX_STATUS, {"route": "support", "topic": topic}))
    response, trace = say(orch, PIX_STATUS)
    assert step(trace, "router")["topic"] == topic
    assert response.answer == NO_PIX and step(trace, "output_guard")["cancellation_status_from_code"] is True


def test_s2_a_status_question_routed_to_knowledge_and_support_gets_the_status_from_code(settings, make):
    orch, _ = make(pix_status_script(PIX_STATUS, {"route": "knowledge_and_support", "topic": "general"}))
    response, trace = say(orch, PIX_STATUS)
    assert step(trace, "router")["route"] == "knowledge_and_support"
    assert NO_PIX in response.answer.split("\n") and PIX_CLAIM not in response.answer
    assert step(trace, "output_guard")["cancellation_status_from_code"] is True


def test_s3_a_request_waiting_in_another_conversation_and_a_status_question_with_another_topic(settings, make):
    status = "Qual o status do cancelamento da venda de débito de ontem?"
    said = "A venda de débito de ontem está com status solicitado."
    script = Script(
        router={status: {"route": "support", "topic": "general", "language": "pt"}},
        support={status: lambda: support_plan(
            [("get_sale_cancellation_context", {"period": "yesterday", "payment_type": "debit"})], said
        )},
        personality={status: said},
    )
    orch, _ = make(script)
    say(orch, "Quero cancelar a venda de débito de ontem.")  # waiting in another conversation
    response, trace = say(orch, status)  # a new conversation
    assert response.answer == (
        f"{NO_DEBIT} Há um pedido de cancelamento dela esperando a sua resposta, e nada foi cancelado."
    )
    assert step(trace, "output_guard")["cancellation_status_from_code"] is True


def test_s4_a_thanks_with_a_status_question_made_general_by_96a_gets_the_status_from_code(settings, make):
    message = "Obrigado! E o cancelamento da venda Pix de ontem, como ficou?"
    orch, _ = make(pix_status_script(message, {"route": "acknowledgement", "topic": None}))
    response, _ = say(orch, "Como funciona o Pix?")
    response, trace = say(orch, message, response.conversation_id)
    router = step(trace, "router")
    assert (router["rule"], router["route"], router["topic"]) == ("question_not_acknowledgement", "support", "general")
    assert response.answer == NO_PIX and step(trace, "output_guard")["cancellation_status_from_code"] is True


def test_s5_a_sales_reply_that_speaks_of_a_cancellation_gets_the_status_from_code(settings, make):
    script = sales_script()
    script.personality[SALES] = f"{SALES_SAID} {PIX_SAID}"  # the model adds a status the code did not write
    orch, _ = make(script)
    response, trace = say(orch, SALES)
    assert response.answer.split("\n") == STATUS_OF_YESTERDAY and PIX_SAID not in response.answer
    assert step(trace, "output_guard")["cancellation_status_from_code"] is True


@pytest.mark.parametrize(
    ("text", "mentions"),
    [
        ("Qual o status do CANCELAMENTO?", True),
        ("A venda foi estornada.", True),
        ("Cancelaram a venda?", True),
        ("The sale was refunded.", True),
        ("Houve um chargeback.", True),
        ("Cancellation status?", True),
        ("Pedi o estôrno da venda.", True),  # an accent inside the word
        ("Quanto vendi ontem?", False),
        (SALES_SAID, False),
        ("Recancelar", False),
    ],
)
def test_a_mention_of_a_cancellation_is_recognised(text, mentions):
    assert cancellation.mentions_cancellation(text) is mentions


def _insert_request(conn, request_id: str, customer_id: str, conversation_id: str) -> None:
    conn.execute(
        "INSERT INTO sale_cancellation_requests (request_id, customer_id, sale_id, amount, sale_date, state, "
        "created_at, idempotency_key, conversation_id, turns_waited, updated_at) "
        "VALUES (?, ?, 'sale_1988_0003', 8000, '2026-11-06', 'pending_confirmation', "
        "'2026-11-07T09:00:00-03:00', ?, ?, 0, '2026-11-07T09:00:00-03:00')",
        (request_id, customer_id, request_id, conversation_id),
    )
    conn.commit()


def test_a_request_of_another_merchant_in_the_conversation_is_not_a_cancellation_turn(settings, make):
    orch, _ = make(sales_script())
    response, _ = say(orch, "Como funciona o Pix?")
    conversation_id = response.conversation_id
    conn = connect(settings.db_path)
    try:
        _insert_request(conn, "scr_other_merchant", "cliente_demo_002", conversation_id)
        assert cancellation.requested_in_conversation(conn, conversation_id, "cliente_demo_002")
        assert not cancellation.requested_in_conversation(conn, conversation_id, "cliente1988")
    finally:
        conn.close()
    response, trace = say(orch, SALES, conversation_id)
    assert response.answer == SALES_SAID and "cancellation_status_from_code" not in step(trace, "output_guard")


def test_a_request_in_another_conversation_is_not_a_cancellation_turn(settings, make):
    orch, _ = make(sales_script())
    response, _ = say(orch, "Como funciona o Pix?")
    conversation_id = response.conversation_id
    other, _ = say(orch, "Quero cancelar a venda Pix de ontem.")  # another conversation
    conn = connect(settings.db_path)
    try:
        assert cancellation.requested_in_conversation(conn, other.conversation_id, "cliente1988")
        assert not cancellation.requested_in_conversation(conn, conversation_id, "cliente1988")
    finally:
        conn.close()
    response, trace = say(orch, SALES, conversation_id)
    assert response.answer == SALES_SAID and "cancellation_status_from_code" not in step(trace, "output_guard")
    response, _ = say(orch, SALES)  # and in a new conversation
    assert response.answer == SALES_SAID


PENDING_EVENT = {"status": "pending_confirmation", "protocol": None,
                 "sale": {"sale_id": "sale_80", "sale_date": "2026-11-06", "amount": {"display": "R$ 80,00"}}}


@pytest.mark.parametrize(
    ("extra", "block"),
    [
        ({}, False),
        ({"topic": "cancellation"}, True),
        ({"cancellation_in_conversation": True}, True),
        ({"cancellation_event": PENDING_EVENT}, True),
        ({"operator": {"action": "reject", "text": "Consulte de novo."}}, True),
        ({"message": PIX_STATUS}, True),
    ],
)
def test_each_reason_for_a_cancellation_turn_holds_without_a_mention(extra, block):
    """Neither the message nor the model's text mentions a cancellation: only the other reasons bring the block."""
    said = "Tudo certo com a venda Pix."
    lookup = ToolOutcome("get_sale_cancellation_context", {}, True, {"sales": [_sale(80)]})
    state = GraphState(
        request_id="req_x", conversation_id="conv_x", user_id="cliente1988", customer_known=True,
        message=extra.get("message", "E a venda Pix de ontem, como ficou?"),
        decision=RouterDecision(route="support", language="pt", topic=extra.get("topic", "general"), intents=[],
                                safety="none", clarification_question=None, case_signal="none"),
        support=SupportResult(points=[said], needs_selection=False, missing=[], escalate=False,
                              escalation_reason=None, tools_used=["get_sale_cancellation_context"],
                              tools_ok=["get_sale_cancellation_context"]),
        draft_answer=said,
        **{k: v for k, v in extra.items() if k not in ("topic", "message")},
    )
    answer = run_output_guard(state, _context(lookup))["answer"]
    line = "A venda de débito de R$ 80,00 de 06/11/2026 não tem cancelamento registrado."
    assert (line in answer.split("\n")) is block and (said in answer) is not block


# --- Cancellation status lines require evidence from the relevant sale --------------------------------------------


def test_only_the_supports_points_speak_of_a_cancellation_and_the_block_replaces_the_reply(settings, make):
    script = sales_script()
    script.support[SALES] = lambda: support_plan(
        [("get_sale_cancellation_context", {"period": "yesterday"})],
        SALES_SAID,
        "A venda de crédito tem cancelamento solicitado.",
    )
    orch, _ = make(script)  # the draft speaks of sales only
    response, trace = say(orch, SALES)
    assert response.answer.split("\n") == STATUS_OF_YESTERDAY
    assert step(trace, "output_guard")["cancellation_status_from_code"] is True


ASK_SALE = cancellation.STATUS_LINES["ask_sale"]["pt"]


def no_lookup_script(message: str, said: str) -> Script:
    return Script(
        support={message: lambda: ToolPlan([], final=lambda _r: {**SUPPORT_FIELDS, "points": []})},
        personality={message: said},
    )


def test_a_status_the_model_states_without_a_lookup_becomes_the_question_for_the_sale(settings, make):
    orch, _ = make(no_lookup_script(PIX_STATUS, "A venda Pix está com status solicitado."))
    response, trace = say(orch, PIX_STATUS)
    assert "get_sale_cancellation_context" not in trace["detail"]["tools"]
    assert response.answer == ASK_SALE and step(trace, "output_guard")["cancellation_status_unchecked"] is True


def test_a_cancellation_turn_without_a_lookup_and_without_a_status_follows_the_normal_flow(settings, make):
    said = "Me diga qual venda você quer consultar: tipo, valor ou data."
    orch, _ = make(no_lookup_script(PIX_STATUS, said))
    response, trace = say(orch, PIX_STATUS)
    assert response.answer == said and "cancellation_status_unchecked" not in step(trace, "output_guard")


def test_a_status_word_outside_a_cancellation_turn_follows_the_normal_flow(settings, make):
    payout = "Meu repasse de ontem foi enviado?"
    said = "Seu repasse de ontem foi enviado e processado."
    script = no_lookup_script(payout, said)
    script.router[payout] = {"route": "support", "topic": "receivables", "language": "pt"}
    orch, _ = make(script)
    response, trace = say(orch, payout)
    assert response.answer == said and "cancellation_status_unchecked" not in step(trace, "output_guard")


def test_a_human_agents_status_is_never_replaced_by_the_question_for_the_sale():
    text = "A venda Pix está com status solicitado."
    state = GraphState(
        request_id="req_x", conversation_id="conv_x", user_id="cliente1988", customer_known=True,
        message=PIX_STATUS,
        decision=RouterDecision(route="support", language="pt", topic="cancellation", intents=[], safety="none",
                                clarification_question=None, case_signal="none"),
        operator={"action": "reply", "text": text}, draft_answer=text,
    )
    assert run_output_guard(state, _context())["answer"].startswith(text)


def test_after_a_request_a_payout_reply_without_a_lookup_follows_the_normal_flow(settings, make):
    """The question for the sale needs the current question about a cancellation, not a request earlier on."""
    payout = "Meu repasse de ontem foi enviado?"
    said = "Seu repasse foi enviado e processado."
    script = no_lookup_script(payout, said)
    script.router[payout] = {"route": "support", "topic": "receivables", "language": "pt"}
    orch, _ = make(script)
    response, _ = say(orch, "Quero cancelar a venda Pix de ontem.")
    conversation_id = response.conversation_id
    say(orch, "Não", conversation_id)
    assert requests(settings)[0]["state"] == "declined"
    response, trace = say(orch, payout, conversation_id)
    assert "get_sale_cancellation_context" not in trace["detail"]["tools"]
    assert response.answer == said and "cancellation_status_unchecked" not in step(trace, "output_guard")


# --- Procedure questions keep their normal answer ------------------------------------------------------------------

PROCEDURES = {
    "Como faço o estorno de uma venda direto na maquininha?": (
        "Na maquininha, acesse o menu Estorno, escolha a venda e confirme com a senha. O valor é devolvido ao cliente "
        "e o estorno é processado pela adquirente."
    ),
    "Como cancelar uma venda no débito?": (
        "Para cancelar uma venda no débito, acesse o menu Cancelamento. Depois de solicitado, o cancelamento é "
        "processado e o valor é estornado ao cliente."
    ),
    "Como cancelo uma venda de débito?": (
        "Você cancela pela maquininha ou pelo app: escolha a venda e confirme. O valor estornado volta ao cliente."
    ),
    "How do I refund a sale on the terminal?": (
        "On the terminal, open Menu > Refund, pick the sale and confirm. The amount is refunded to the customer and "
        "the refund is processed by the acquirer."
    ),
}


@pytest.mark.parametrize("route", [("knowledge", None), ("support", "cancellation")])
@pytest.mark.parametrize("message", list(PROCEDURES))
def test_a_question_of_procedure_keeps_its_answer(settings, make, message, route):
    said = PROCEDURES[message]
    script = no_lookup_script(message, said)
    script.router[message] = {"route": route[0], "topic": route[1], "language": "en" if "How" in message else "pt"}
    orch, _ = make(script)
    response, trace = say(orch, message)
    assert said in response.answer and "cancellation_status_unchecked" not in step(trace, "output_guard")
    assert cancellation.claims_status(said)  # the wide word list would have taken it for a status


def test_an_official_answer_is_never_replaced_even_when_it_reads_like_a_state():
    """The answer of the Knowledge (route `knowledge`) is kept even if a sentence of it reads like a sale's state."""
    said = "Feito isso, a venda está cancelada e o valor volta ao cliente."
    assert cancellation.states_sale_status(said)
    state = GraphState(
        request_id="req_x", conversation_id="conv_x", user_id="cliente1988", customer_known=True,
        message="Como cancelo uma venda de débito?",
        decision=RouterDecision(route="knowledge", language="pt", topic=None, intents=[], safety="none",
                                clarification_question=None, case_signal="none"),
        draft_answer=said,
    )
    assert run_output_guard(state, _context())["answer"] == said
    with_points = state.model_copy(update={
        "decision": state.decision.model_copy(update={"route": "knowledge_and_support", "topic": "cancellation"}),
        "knowledge": KnowledgeResult(mode="rag", points=["Cancele pela maquininha."], evidence_sufficient=True),
    })
    assert run_output_guard(with_points, _context())["answer"] == said
    without = state.model_copy(update={
        "decision": state.decision.model_copy(update={"route": "support", "topic": "cancellation"}),
    })
    assert run_output_guard(without, _context())["answer"] == ASK_SALE


@pytest.mark.parametrize(
    ("text", "states"),
    [
        ("A venda Pix está com status solicitado.", True),
        ("O cancelamento da venda de débito de ontem está com status solicitado.", True),
        ("Seu pedido de cancelamento foi aprovado.", True),
        ("The cancellation of the Pix sale was approved.", True),
        ("Your sale is pending.", True),
        ("The sale was cancelled.", True),
        ("The cancellation is under review.", True),
        ("The cancellation has been completed.", True),
        ("The cancellation request remains pending.", True),
        ("The Pix sale was cancelled.", True),  # up to three words before the noun
        ("The debit sale is pending.", True),
        ("The cancellation is now in progress.", True),
        ("The sale is currently pending.", True),
        ("Your sale is cancelled.", True),  # "is" + a participle that closes the clause
        ("The cancellation is approved.", True),
        ("The cancellation is processed the same day.", False),
        ("The cancellation is approved by the issuer.", False),
        ("The sale is not cancelled.", False),
        ("The cancellation is processed within one business day.", False),  # "is" + participle: a procedure
        ("The sale is cancelled and the amount goes back to the customer.", False),
        ("The cancellation is requested in the app and approved by the acquirer.", False),
        ("A venda Pix não está cancelada.", False),
        ("Seu repasse foi enviado e processado.", False),
        *((said, False) for said in PROCEDURES.values()),
    ],
)
def test_the_state_of_a_specific_sale_is_recognised_and_a_procedure_is_not(text, states):
    assert cancellation.states_sale_status(text) is states


def test_a_cancellation_question_with_an_event_in_the_turn_gets_the_line_of_96b(settings, make):
    """When a request changes state in the turn, the fixed status line is used."""
    orch, _ = make(Script(personality={"Não": "A venda Pix está com status solicitado."}))
    response, _ = say(orch, "Quero cancelar a venda Pix de ontem.")
    response, trace = say(orch, "Não", response.conversation_id)
    assert cancellation.LINES["declined"]["pt"].format(amount="R$ 80,00", date="06/11/2026") in response.answer
    assert ASK_SALE not in response.answer and "cancellation_status_unchecked" not in step(trace, "output_guard")
    assert step(trace, "output_guard")["cancellation_promise"] is True


def test_a_procedure_in_the_passive_voice_keeps_its_answer_without_the_knowledge():
    """Route support, topic cancellation, no Knowledge in the turn (with "How do I", the Replanner would add it and
    its points would protect the answer): only the narrow detector decides, and "is processed" is a procedure."""
    said = "Open Sales in the app, pick the sale and tap Cancel. The cancellation is processed the same day."
    state = GraphState(
        request_id="req_x", conversation_id="conv_x", user_id="cliente1988", customer_known=True,
        message="How do I cancel a debit sale?",
        decision=RouterDecision(route="support", language="en", topic="cancellation", intents=[], safety="none",
                                clarification_question=None, case_signal="none"),
        support=SupportResult(points=[said], needs_selection=False, missing=[], escalate=False,
                              escalation_reason=None, tools_used=[], tools_ok=[]),
        draft_answer=said,
    )
    ctx = _context()
    assert run_output_guard(state, ctx)["answer"] == said and "cancellation_status_unchecked" not in ctx.step_notes
    stated = state.model_copy(update={"draft_answer": "The cancellation of the debit sale was approved."})
    assert run_output_guard(stated, _context())["answer"] == cancellation.STATUS_LINES["ask_sale"]["en"]
