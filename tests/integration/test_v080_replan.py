"""v0.8.0 task 69 (RF-86 to RF-88, CA-49; spec D1 to D8, D16): the `replan` step after each specialist.

Scripted model, no network, no cost. Rules settle the clear cases; the model is asked only when none applies or two
disagree. The route of the answer stays the Router's initial plan; the executed path is in `agents` and in the trace."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

import pytest

from merchant_assistant.agents import replanner
from merchant_assistant.agents.common import policy
from merchant_assistant.api.schemas import MessageRequest
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation.runner import _checks, load_cases
from merchant_assistant.evaluation.scripted_policy import handler as default_handler
from merchant_assistant.llm.base import LLMError
from merchant_assistant.llm.scripted import ToolPlan
from merchant_assistant.orchestration.graph import build_review_graph
from merchant_assistant.testing import merchant_headers

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
REPLAN_CASES = {case.id: case for case in load_cases([SCENARIOS / "replan.jsonl"])}
FOUR_FILES = ("challenge_examples", "core_cases", "business_journeys")
SIMPLE = "What's the difference between the Get Clássica and the Get Smart?"
UNKNOWN_PRODUCT = "A maquininha Get XYZ aceita pagamento por aproximação?"
FAULTS = {"REPLAN-TOOL-DOWN": {"simulate_pricing": "UNAVAILABLE"}}


def handle(orchestrator, message, user_id="cliente1988"):
    request_id = f"req_t69_{uuid.uuid4().hex[:12]}"
    response = orchestrator.handle(MessageRequest(message=message, user_id=user_id), request_id)
    return response.model_dump(), orchestrator.trace(request_id)


def replan_steps(trace) -> list[dict]:
    return [s["detail"] | {"status": s["status"]} for s in trace["steps"] if s["step"] == "replan"]


def decisions(trace) -> list[tuple]:
    return [(s["next"], s["origin"], s["hops"], s["review"]) for s in replan_steps(trace)]


def ledger_agents(orchestrator, trace) -> list[str]:
    conn = sqlite3.connect(orchestrator.budget.path)
    try:
        rows = conn.execute("SELECT agent FROM ledger WHERE request_id=? ORDER BY id", (trace["request_id"],))
        return [r[0] for r in rows]
    finally:
        conn.close()


def with_handlers(**by_agent):
    """The scripted policy, with some agents answered differently: `by_agent[name](call)` or NotImplemented."""

    def handler(call):
        replacement = by_agent.get(call.spec.agent)
        if replacement is not None and (answer := replacement(call)) is not NotImplemented:
            return answer
        return default_handler(call)

    return handler


def replan_calls(llm) -> list:
    return [c for c in llm.calls if c.spec.agent == "replan"]


# --- clear cases: rules only ---------------------------------------------------------------------------------


def test_simple_question_is_closed_by_rule_without_an_extra_call(offline):
    client, orchestrator, llm = offline()
    body, trace = handle(orchestrator, SIMPLE)
    assert body["route"] == "knowledge" and body["agents"] == ["router", "knowledge", "personality"]
    [step] = replan_steps(trace)
    assert (step["next"], step["origin"], step["review"], step["hops"]) == ("finish", "rule:complete", "complete", 0)
    assert step["reason"] and step["observed"]["just_ran"] == "knowledge" and step["observed"]["evidence_sufficient"]
    assert replan_calls(llm) == [] and trace["model_calls"] == 3
    assert ledger_agents(orchestrator, trace) == ["router", "knowledge", "personality"]  # ledger: nothing extra
    assert trace["detail"]["plan_hops"] == 0


@pytest.mark.parametrize(
    ("case_id", "agents", "expected"),
    [
        (
            "REPLAN-WEB",
            ["router", "knowledge", "web", "personality"],
            [("web", "rule:evidence_insufficient_web", 1, "incomplete"), ("finish", "rule:complete", 1, "complete")],
        ),
        (
            "REPLAN-PROCEDURE",
            ["router", "customer_support", "knowledge", "personality"],
            [("knowledge", "rule:procedure_gap", 1, "incomplete"), ("finish", "rule:complete", 1, "complete")],
        ),
        (
            "REPLAN-TOOL-DOWN",
            ["router", "customer_support", "escalation", "personality"],
            [("escalate", "rule:tool_failure_no_alternative", 1, "incomplete")],
        ),
        (
            "REPLAN-ACCOUNT",
            ["router", "knowledge", "customer_support", "personality"],
            [
                ("support", "rule:account_dependent_question", 1, "incomplete"),
                ("finish", "rule:complete", 1, "complete"),
            ],
        ),
    ],
)
def test_the_four_scenarios_of_rf88_pass_with_the_scripted_model_and_show_their_decisions(
    offline, case_id, agents, expected
):
    case = REPLAN_CASES[case_id]
    client, orchestrator, llm = offline(faults=FAULTS.get(case_id))
    body, trace = handle(orchestrator, case.message)
    checks = _checks(case, body, trace)
    assert all(checks[k] for k in ("route_ok", "status_ok", "tools_ok", "amounts_ok", "content_ok", "forbidden_ok",
                                   "sources_ok", "grounded_ok")), (case_id, checks, body["answer"])
    assert body["route"] in case.accepted_routes  # D16: the route is the Router's initial plan
    assert body["agents"] == agents  # the executed path, in order
    assert decisions(trace) == expected
    for step in replan_steps(trace):
        assert {"next", "reason", "review", "hops", "origin", "observed"} <= set(step)  # D7
    assert replan_calls(llm) == []  # every one of them is a clear case
    assert trace["detail"]["plan_hops"] == expected[-1][2]
    assert ledger_agents(orchestrator, trace).count("replan") == 0


def test_tool_down_scenario_leaves_a_case_in_the_queue_without_inventing_data(offline, settings):
    case = REPLAN_CASES["REPLAN-TOOL-DOWN"]
    client, orchestrator, _ = offline(faults=FAULTS["REPLAN-TOOL-DOWN"])
    body, trace = handle(orchestrator, case.message)
    assert body["status"] == "handoff" and body["handoff"]["protocol"].startswith("HO-")
    assert body["handoff"]["reason"] == "tool_error:UNAVAILABLE"
    conn = sqlite3.connect(settings.db_path)
    assert conn.execute("SELECT queue_state, reason FROM handoff_cases").fetchall() == [
        ("open", "tool_error:UNAVAILABLE")
    ]
    assert trace["detail"]["plan_hops"] == 1


def test_the_second_specialist_of_the_routers_plan_is_not_a_change_of_plan(offline):
    client, orchestrator, llm = offline()
    body, trace = handle(orchestrator, "My card machine won't connect to the internet, what should I do?")
    assert body["route"] == "knowledge_and_support"
    assert body["agents"] == ["router", "knowledge", "customer_support", "personality"]
    assert decisions(trace) == [
        ("support", "rule:plan_pending", 0, "incomplete"), ("finish", "rule:complete", 0, "complete")
    ]
    assert replan_calls(llm) == []


def test_no_clear_case_of_the_forty_or_the_four_scenarios_asks_the_model(offline):
    client, orchestrator, llm = offline()
    cases = load_cases([SCENARIOS / f"{name}.jsonl" for name in FOUR_FILES])
    assert len(cases) == 40
    for case in cases:
        body, trace = handle(orchestrator, case.message)
        assert body["route"] in case.accepted_routes, case.id
        assert all(s["origin"].startswith("rule:") for s in replan_steps(trace)), case.id
        assert len(replan_steps(trace)) <= 3 and trace["detail"]["plan_hops"] <= 3, case.id
    assert replan_calls(llm) == []


# --- the model is for the ambiguity --------------------------------------------------------------------------


def test_the_model_is_called_only_when_rules_disagree_or_none_applies(offline):
    client, orchestrator, llm = offline()
    message = "A Get XYZ aceita pagamento por aproximação no meu plano?"  # not in the pages, and depends on the plan
    body, trace = handle(orchestrator, message)
    first, second = replan_steps(trace)
    assert (first["next"], first["origin"], first["candidates"]) == ("support", "model", ["support", "web"])
    assert (second["next"], second["origin"], second["candidates"]) == ("finish", "model", [])  # no rule applies
    assert len(replan_calls(llm)) == 2
    assert ledger_agents(orchestrator, trace).count("replan") == 2
    assert body["agents"] == ["router", "knowledge", "customer_support", "personality"]
    spec = replan_calls(llm)[0].spec
    assert spec.agent == "replan" and spec.effort == "none" and spec.max_output_tokens <= 80
    assert "replan@2" in [s["detail"].get("prompt") for s in trace["steps"] if s["step"] == "replan"]


def test_the_planner_unavailable_ends_with_what_was_collected(offline):
    handler = with_handlers(replan=lambda call: LLMError("planner down"))
    client, orchestrator, llm = offline(handler=handler)
    body, trace = handle(orchestrator, "A Get XYZ aceita pagamento por aproximação no meu plano?")
    [step] = replan_steps(trace)
    assert (step["next"], step["origin"], step["status"]) == ("finish", "rule:planner_unavailable", "error")
    assert body["status"] == "answered" and body["answer"].strip()


def test_two_rules_that_disagree_ask_the_model_and_a_human_wins_in_the_scripted_policy(offline):
    both = {"points": ["A", "B"], "needs_selection": True, "missing": [], "escalate": True,
            "escalation_reason": "needs_a_person", "steps_given": [], "issue_verified_by_tool": False}
    client, orchestrator, llm = offline(handler=with_handlers(customer_support=lambda call: both))
    body, trace = handle(orchestrator, "Quando vai cair o dinheiro das vendas de ontem?")
    [step] = replan_steps(trace)
    assert (step["next"], step["origin"], step["candidates"]) == ("escalate", "model", ["clarify", "escalate"])
    assert body["status"] == "handoff" and len(replan_calls(llm)) == 1


def test_a_selection_pending_asks_the_merchant_by_rule(offline):
    selection = {"points": ["Maquininha A", "Maquininha B"], "needs_selection": True, "missing": [],
                 "escalate": False, "escalation_reason": None, "steps_given": [], "issue_verified_by_tool": False}
    client, orchestrator, llm = offline(handler=with_handlers(customer_support=lambda call: selection))
    body, trace = handle(orchestrator, "Quando vai cair o dinheiro das vendas de ontem?")
    assert decisions(trace) == [("clarify", "rule:selection_pending", 0, "incomplete")]
    assert body["status"] == "needs_clarification" and "Maquininha A" in body["answer"]
    assert replan_calls(llm) == []


def test_the_model_can_ask_a_question_and_then_the_answer_is_a_clarification(offline, monkeypatch):
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])
    ask = {"next": "clarify", "review": "incomplete", "reason": "which product?"}
    client, orchestrator, llm = offline(handler=with_handlers(replan=lambda call: ask))
    body, trace = handle(orchestrator, SIMPLE)
    assert body["status"] == "needs_clarification" and body["answer"].strip()
    assert decisions(trace) == [("clarify", "model", 0, "incomplete")]


def test_the_tool_failure_reason_is_recorded_even_if_support_did_not_escalate(offline):
    calm = {"points": [], "needs_selection": False, "missing": [], "escalate": False, "escalation_reason": None,
            "steps_given": [], "issue_verified_by_tool": False}
    plan = lambda call: ToolPlan([("get_receivables_schedule", {"period": "yesterday"})], final=lambda results: calm)  # noqa: E731
    client, orchestrator, llm = offline(
        faults={"get_receivables_schedule": "TIMEOUT"}, handler=with_handlers(customer_support=plan)
    )
    body, trace = handle(orchestrator, "Quando vai cair o dinheiro das vendas de ontem?")
    assert body["status"] == "handoff" and body["handoff"]["reason"] == "tool_error:TIMEOUT"
    assert decisions(trace) == [("escalate", "rule:tool_failure_no_alternative", 1, "incomplete")]


# --- the loop cannot happen ----------------------------------------------------------------------------------


def stubborn():
    """Specialists that never resolve anything: no passages cover it, the web is down, support finds nothing."""
    nothing = {"points": [], "needs_selection": False, "missing": [], "escalate": False, "escalation_reason": None,
               "steps_given": [], "issue_verified_by_tool": False}

    def knowledge(call):
        if call.kind == "web":
            return LLMError("web search unavailable")
        return {"points": [], "used_passages": [], "evidence_sufficient": False, "missing": ["not covered"]}

    return with_handlers(knowledge=knowledge, customer_support=lambda call: nothing)


def specialists_in(body) -> list[str]:
    return [a for a in body["agents"] if a in ("knowledge", "web", "customer_support")]


def test_forced_loop_specialists_that_never_resolve_end_without_repeating_any(offline):
    client, orchestrator, llm = offline(handler=stubborn())
    message = "Quando vai cair o dinheiro das vendas de ontem e como faço para antecipar esse valor?"
    body, trace = handle(orchestrator, message)
    assert body["agents"] == ["router", "customer_support", "knowledge", "web", "personality"]
    assert decisions(trace) == [
        ("knowledge", "rule:procedure_gap", 1, "incomplete"),
        ("web", "rule:evidence_insufficient_web", 2, "incomplete"),
        ("finish", "rule:gap_declared", 2, "incomplete"),
    ]
    assert len(set(specialists_in(body))) == len(specialists_in(body))  # none twice
    assert replan_calls(llm) == []
    contributions = [c.spec.context["contributions"] for c in llm.calls if c.spec.agent == "personality"][0]
    assert contributions["unconfirmed"], "the reply must be told what could not be confirmed"
    assert body["status"] == "answered" and body["answer"].strip()


def test_forced_loop_a_planner_that_always_wants_more_ends_in_three_changes_of_plan(offline, monkeypatch):
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])  # every decision goes to the model
    script = iter(["web", "support", "escalate"])
    answer = lambda call: {"next": next(script), "review": "incomplete", "reason": "more"}  # noqa: E731
    client, orchestrator, llm = offline(handler=with_handlers(replan=answer))
    body, trace = handle(orchestrator, SIMPLE)
    assert body["agents"] == ["router", "knowledge", "web", "customer_support", "escalation", "personality"]
    assert [d[0] for d in decisions(trace)] == ["web", "support", "escalate"]
    assert [d[2] for d in decisions(trace)] == [1, 2, 3] and trace["detail"]["plan_hops"] == 3
    assert body["status"] == "handoff" and len(set(specialists_in(body))) == 3


@pytest.mark.parametrize("wanted", ["knowledge", "web", "support"])
def test_a_specialist_the_planner_asks_for_twice_is_refused(offline, monkeypatch, wanted):
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])
    asks = iter(["web", wanted, wanted, wanted])
    answer = lambda call: {"next": next(asks), "review": "incomplete", "reason": "again"}  # noqa: E731
    client, orchestrator, llm = offline(handler=with_handlers(replan=answer))
    body, trace = handle(orchestrator, SIMPLE)
    assert len(set(specialists_in(body))) == len(specialists_in(body))
    assert len(replan_steps(trace)) <= 4 and trace["detail"]["plan_hops"] <= 3
    assert body["agents"][-1] == "personality" and body["answer"].strip()
    refused = [s for s in replan_steps(trace) if s["origin"] == "rule:no_repeat"]
    assert refused and refused[0]["next"] == "finish" and refused[0]["refused"] in ("knowledge", "web", "support")


EURO = "What's the euro exchange rate today?"
ASKS_FOR_THE_PAGES_AGAIN = [
    (["knowledge", "knowledge", "knowledge"], ["router", "knowledge", "personality"],
     [("finish", "rule:no_repeat", 0, "incomplete")]),
    (["web", "knowledge"], ["router", "knowledge", "personality"], [("finish", "rule:no_repeat", 0, "incomplete")]),
    (["support", "knowledge", "knowledge", "escalate"], ["router", "knowledge", "customer_support", "personality"],
     [("support", "model", 1, "incomplete"), ("finish", "rule:no_repeat", 1, "incomplete")]),
    (["support", "escalate"], ["router", "knowledge", "customer_support", "escalation", "personality"],
     [("support", "model", 1, "incomplete"), ("escalate", "model", 2, "incomplete")]),
]


@pytest.mark.parametrize(("script", "agents", "expected"), ASKS_FOR_THE_PAGES_AGAIN)
def test_on_the_general_web_route_the_search_runs_once_whatever_the_planner_asks(
    offline, monkeypatch, script, agents, expected
):
    """Review P2-1: there the `knowledge` node is the web search, so `knowledge` is not a new specialist."""
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])
    asks = iter([*script, "finish"])
    answer = lambda call: {"next": next(asks), "review": "incomplete", "reason": "again"}  # noqa: E731
    client, orchestrator, llm = offline(handler=with_handlers(replan=answer))
    body, trace = handle(orchestrator, EURO)
    assert body["route"] == "general_web" and body["agents"] == agents
    assert len([c for c in llm.calls if c.kind == "web"]) == 1  # one search, never overwritten
    assert decisions(trace) == expected
    assert trace["detail"]["plan_hops"] <= 3


def test_a_finish_the_model_calls_incomplete_declares_its_reason_as_the_gap(offline, monkeypatch):
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])
    reason = "the fee for 12 installments could not be confirmed"
    incomplete = {"next": "finish", "review": "incomplete", "reason": reason}
    client, orchestrator, llm = offline(handler=with_handlers(replan=lambda call: incomplete))
    body, trace = handle(orchestrator, SIMPLE)
    assert decisions(trace) == [("finish", "model", 0, "incomplete")]
    contributions = [c.spec.context["contributions"] for c in llm.calls if c.spec.agent == "personality"][0]
    assert contributions["unconfirmed"] == [reason]


def test_a_finish_the_model_calls_complete_declares_no_gap(offline, monkeypatch):
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])
    complete = {"next": "finish", "review": "complete", "reason": "the pages answer it"}
    client, orchestrator, llm = offline(handler=with_handlers(replan=lambda call: complete))
    body, trace = handle(orchestrator, SIMPLE)
    contributions = [c.spec.context["contributions"] for c in llm.calls if c.spec.agent == "personality"][0]
    assert "unconfirmed" not in contributions


def test_the_labels_need_what_each_replanned_step_brings(offline):
    """The web scenario needs the page the search found (or the plain admission), the procedure one needs the official
    how-to next to the account figures, and the tool scenario needs the tool to have been tried and to have failed."""
    web = REPLAN_CASES["REPLAN-WEB"]
    client, orchestrator, llm = offline()
    body, trace = handle(orchestrator, web.message)
    assert "NFC" in body["answer"] and {"web"} <= {s["type"] for s in body["sources"]}
    assert _checks(web, body, trace)["content_ok"]
    assert not _checks(web, body | {"answer": "A Get XYZ é ótima, aceita tudo."}, trace)["content_ok"]  # invented

    procedure = REPLAN_CASES["REPLAN-PROCEDURE"]
    body, trace = handle(orchestrator, procedure.message)
    assert {"official", "tool"} <= {s["type"] for s in body["sources"]}
    assert "aplicativo" in body["answer"].lower()
    support_only = body | {"answer": "O crédito de 14806 e 116220 ainda não foi confirmado."}
    assert not _checks(procedure, support_only, trace)["content_ok"]  # the account part alone does not satisfy it

    tool_down = REPLAN_CASES["REPLAN-TOOL-DOWN"]
    assert tool_down.expected_tools == ["simulate_pricing"]
    asked_for_a_person = _checks(tool_down, body | {"status": "handoff"}, {"steps": [], "detail": {}})
    assert not asked_for_a_person["tools_ok"]  # a handoff without the attempted lookup is another scenario


BUDGETS = [(0, ["router", "knowledge", "personality"]), (1, ["router", "knowledge", "web", "personality"])]


@pytest.mark.parametrize(("budget", "path"), BUDGETS)
def test_the_budget_of_changes_of_plan_is_a_setting_and_ends_with_the_gap_declared(
    offline, settings, monkeypatch, budget, path
):
    settings.max_plan_hops = budget
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])
    asks = iter(["web", "support"])
    answer = lambda call: {"next": next(asks), "review": "incomplete", "reason": "more"}  # noqa: E731
    client, orchestrator, llm = offline(handler=with_handlers(replan=answer))
    body, trace = handle(orchestrator, SIMPLE)
    assert body["agents"] == path
    last = replan_steps(trace)[-1]
    assert (last["next"], last["origin"]) == ("finish", "rule:hop_budget")
    assert trace["detail"]["plan_hops"] == budget
    contributions = [c.spec.context["contributions"] for c in llm.calls if c.spec.agent == "personality"][0]
    assert contributions["unconfirmed"]


def test_the_requests_call_limit_still_holds(offline, settings):
    settings.max_model_calls = 3
    client, orchestrator, llm = offline()
    body, trace = handle(orchestrator, UNKNOWN_PRODUCT)  # would go to the web, but router + knowledge + reply = 3
    assert body["agents"] == ["router", "knowledge", "personality"] and trace["model_calls"] == 3
    assert decisions(trace) == [("finish", "rule:request_limits", 0, "incomplete")]


def test_an_account_question_from_an_unknown_merchant_stays_with_knowledge(offline):
    client, orchestrator, llm = offline()
    body, trace = handle(orchestrator, "A antecipação de recebíveis está disponível no meu plano?", "someone_else")
    assert body["agents"] == ["router", "knowledge", "personality"]
    assert decisions(trace) == [("finish", "rule:complete", 0, "complete")]


def test_a_failing_node_never_loops_the_replanner(offline, monkeypatch):
    from merchant_assistant.agents import support

    def boom(state, ctx):
        raise RuntimeError("support exploded")

    monkeypatch.setattr(support, "run", boom)
    client, orchestrator, llm = offline()
    body, trace = handle(orchestrator, "Quando vai cair o dinheiro das vendas de ontem?")
    assert body["agents"] == ["router", "personality"] and body["answer"].strip()
    assert decisions(trace) == [("finish", "rule:specialist_failed", 0, "incomplete")]


# --- trace, API and catalog ----------------------------------------------------------------------------------


def test_the_run_endpoint_shows_each_decision_with_its_origin(offline):
    client, orchestrator, _ = offline()
    headers = merchant_headers(client)
    item = next(s for s in client.get("/v1/scenarios", headers=headers).json()["scenarios"] if
                s["scenario_id"] == "SC-REPLAN-WEB")
    sent = client.post(
        "/v1/messages", headers=headers,
        json={"message": item["message"], "profile_id": "reference", "profile_version": 1,
              "router_mechanism": "llm", "scenario_id": "SC-REPLAN-WEB"},
    )
    assert sent.status_code == 200, sent.text
    run = client.get(f"/v1/runs/{sent.json()['message']['request_id']}", headers=headers).json()
    assert run["route"] == "knowledge"  # the initial plan (D16)
    assert sent.json()["message"]["agents"] == ["router", "knowledge", "web", "personality"]
    steps = [s for s in run["steps"] if s["step"] == "replan"]
    assert [(s["next"], s["origin"], s["hops"], s["review"]) for s in steps] == [
        ("web", "rule:evidence_insufficient_web", 1, "incomplete"), ("finish", "rule:complete", 1, "complete")]
    assert all(s["reason"] and s["observed"]["route"] == "knowledge" for s in steps)
    other = next(s for s in run["steps"] if s["step"] == "knowledge")
    assert "next" not in other and "origin" not in other  # the new fields belong to the replan step only
    assert run["checks"]["origin"] == "scenario:SC-REPLAN-WEB"
    assert run["checks"]["passed"] == run["checks"]["total"] and run["checks"]["critical_failures"] == []


def test_catalog_scenarios_carry_the_message_and_labels_of_replan_jsonl():
    from merchant_assistant.scenarios import LABEL_FIELDS, as_case, catalog

    scenarios = catalog(PROJECT_ROOT / "data")["scenarios"]
    pairs = {"SC-REPLAN-WEB": "REPLAN-WEB", "SC-REPLAN-PROCEDURE": "REPLAN-PROCEDURE",
             "SC-REPLAN-TOOL-DOWN": "REPLAN-TOOL-DOWN", "SC-REPLAN-ACCOUNT": "REPLAN-ACCOUNT"}
    assert set(REPLAN_CASES) == set(pairs.values()) and all(c.split == "dev" for c in REPLAN_CASES.values())
    for scenario_id, case_id in pairs.items():
        item, case = scenarios[scenario_id], REPLAN_CASES[case_id]
        effective = as_case(item, "cliente1988")
        assert item["journey"] == "replan" and effective.message == case.message and effective.language == case.language
        for field in LABEL_FIELDS:
            assert getattr(effective, field) == getattr(case, field), (scenario_id, field)
    assert scenarios["SC-REPLAN-TOOL-DOWN"]["precondition"]  # the only one that needs the pricing service down


def test_replan_jsonl_has_exactly_the_four_rf88_cases_in_the_runner_format():
    lines = [json.loads(x) for x in Path(SCENARIOS / "replan.jsonl").read_text(encoding="utf-8").splitlines() if x]
    assert [x["id"] for x in lines] == ["REPLAN-WEB", "REPLAN-PROCEDURE", "REPLAN-TOOL-DOWN", "REPLAN-ACCOUNT"]


def test_the_review_graph_that_resumes_a_handed_off_case_has_no_replanning():
    nodes = set(build_review_graph(None).get_graph().nodes)
    assert {"human_review", "support", "personality", "output_guard"} <= nodes
    assert not nodes & {"replan", "web", "knowledge", "escalation"}  # D3: support -> personality, as in v0.7.0


# --- task 72b, review of task 69, round 2 (P3): the declared gap, from the planner to the text ---------------------

REASON = "the fee for 12 installments could not be confirmed"
SIMPLE_PT = "Qual a diferença entre a Get Clássica e a Get Smart?"


def model_decides(*answers, **extra):
    """Rules off by the caller; the planner answers with `answers` in order, then closes with a complete finish."""
    queue = iter(answers)
    closing = {"next": "finish", "review": "complete", "reason": "the results answer it"}
    return with_handlers(replan=lambda call: next(queue, closing), **extra)


def personality_call(llm):
    return next(c for c in llm.calls if c.spec.agent == "personality")


@pytest.mark.parametrize("wanted", ["clarify", "escalate", "web", "support"])
def test_only_a_finish_declares_the_models_reason_as_the_gap(offline, monkeypatch, wanted):
    """Mutant A08: `clarify` (and the others) with an incomplete review must not turn the reason into the gap."""
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])
    incomplete = {"next": wanted, "review": "incomplete", "reason": REASON}
    client, orchestrator, llm = offline(handler=model_decides(incomplete))
    body, trace = handle(orchestrator, SIMPLE)
    assert replan_steps(trace)[0]["next"] == wanted and body["answer"].strip()
    assert "unconfirmed" not in personality_call(llm).spec.context["contributions"]


@pytest.mark.parametrize("reason", ["", "   ", "\n\t "])
def test_an_empty_reason_on_an_incomplete_finish_is_not_declared_as_an_empty_gap(offline, monkeypatch, reason):
    """Mutant A09: nothing to say is not a gap; the Personality is not told to confirm an empty string."""
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])
    incomplete = {"next": "finish", "review": "incomplete", "reason": reason}
    client, orchestrator, llm = offline(handler=model_decides(incomplete))
    body, trace = handle(orchestrator, SIMPLE)
    assert decisions(trace) == [("finish", "model", 0, "incomplete")]
    assert "unconfirmed" not in personality_call(llm).spec.context["contributions"]
    assert body["answer"].strip()


def test_the_gap_is_in_what_the_personality_reads_and_its_prompt_says_to_state_it(offline, monkeypatch):
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])
    incomplete = {"next": "finish", "review": "incomplete", "reason": REASON}
    client, orchestrator, llm = offline(handler=model_decides(incomplete))
    handle(orchestrator, SIMPLE)
    instructions = personality_call(llm).spec.instructions
    assert '"unconfirmed"' in instructions and REASON in instructions
    prompt = " ".join((PROJECT_ROOT / "prompts" / "personality.v5.md").read_text(encoding="utf-8").split())
    assert "If the contributions include `unconfirmed`" in prompt
    assert "tell the merchant plainly, in their language, what you could not confirm" in prompt
    assert "never fill it in with a guess and never present it as confirmed" in prompt


@pytest.mark.parametrize(("message", "language"), [(SIMPLE, "en"), (SIMPLE_PT, "pt")])
def test_the_fallback_answer_says_what_could_not_be_confirmed(offline, monkeypatch, message, language):
    """The Personality is down, so the deterministic fallback writes the reply: it must still carry the gap."""
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])
    incomplete = {"next": "finish", "review": "incomplete", "reason": REASON}
    down = lambda call: LLMError("personality down")  # noqa: E731
    client, orchestrator, llm = offline(handler=model_decides(incomplete, personality=down))
    body, trace = handle(orchestrator, message)
    assert body["language"] == language and body["status"] == "answered"
    assert body["answer"].endswith(policy("unconfirmed", language))
    assert len(body["answer"]) > len(policy("unconfirmed", language))  # the confirmed part comes first


def test_the_fallback_does_not_say_it_twice_when_the_knowledge_part_already_says_nothing_was_found(offline):
    base = stubborn()
    handler = lambda call: LLMError("personality down") if call.spec.agent == "personality" else base(call)  # noqa: E731
    client, orchestrator, llm = offline(handler=handler)
    body, trace = handle(orchestrator, UNKNOWN_PRODUCT)
    assert decisions(trace)[-1][:2] == ("finish", "rule:gap_declared")
    assert policy("unconfirmed", "pt") not in body["answer"]
    assert body["answer"].strip() and "\n" not in body["answer"]


def test_the_fallback_is_unchanged_when_nothing_was_declared(offline):
    down = lambda call: LLMError("personality down")  # noqa: E731
    client, orchestrator, llm = offline(handler=with_handlers(personality=down))
    body, trace = handle(orchestrator, SIMPLE)
    assert decisions(trace) == [("finish", "rule:complete", 0, "complete")]
    assert policy("unconfirmed", "en") not in body["answer"] and body["answer"].strip()


def test_replan_v2_tells_the_planner_its_reason_may_reach_the_merchant_and_v1_is_left_alone():
    from merchant_assistant.orchestration.state import ReplanDecision

    v2 = " ".join((PROJECT_ROOT / "prompts" / "replan.v2.md").read_text(encoding="utf-8").split())
    assert v2.startswith("--- id: replan version: 2 ---")
    assert 'With `finish` and review "incomplete" it is also what the reply tells the merchant' in v2
    assert "could not be confirmed, so write that missing fact in plain words" in v2
    v1 = " ".join((PROJECT_ROOT / "prompts" / "replan.v1.md").read_text(encoding="utf-8").split())
    assert v1.startswith("--- id: replan version: 1 ---") and "for the trace. Keep the whole answer short." in v1
    description = ReplanDecision.model_json_schema()["properties"]["reason"]["description"]
    assert "for the trace" in description and "could not be confirmed" in description


# --- task 72b, review of task 69, round 2 (P3): REPLAN-WEB accepts honest admissions, not an invented yes -----------

HONEST_WEB_ANSWERS = [
    "Não encontrei informações sobre a Get XYZ nas fontes que consultei.",
    "Não consegui encontrar informações confiáveis sobre a Get XYZ.",
    "Não foi possível confirmar se a Get XYZ aceita pagamento por aproximação.",
    "Não foi possível encontrar essa informação em fontes confiáveis.",
    "Não há informações públicas sobre esse modelo, então não posso confirmar.",
    "Uma página de terceiros diz que a Get XYZ aceita pagamento por aproximação (NFC), mas não é uma fonte oficial.",
    # review P3-4: admissions the first list missed
    "Não consegui verificar se a Get XYZ aceita pagamento por aproximação.",
    "Não identifiquei informações sobre esse modelo.",
    "Não achei nada sobre a Get XYZ.",
    "Não foi possível verificar essa informação.",
    "Não sei dizer se a Get XYZ aceita pagamento por aproximação.",
    "Não posso afirmar que a Get XYZ aceita pagamento por aproximação.",
    "Não existe informação pública sobre a Get XYZ.",
    "Não consigo confirmar se esse modelo tem pagamento por aproximação.",
    # an honest answer may repeat the question, NFC included, behind an expression of doubt
    "Não foi possível confirmar se a Get XYZ aceita NFC.",
    "Não sei se a Get XYZ tem NFC.",
]
INVENTED_WEB_ANSWERS = [
    "Sim, a Get XYZ aceita pagamento por aproximação.",
    "Sim, aceita NFC e carteiras digitais.",
    "A Get XYZ aceita NFC.",
    "A Get XYZ tem NFC e é compatível com Apple Pay.",
    "A Get XYZ é ótima, aceita tudo.",
    "Não encontrei fontes oficiais, mas sim, a Get XYZ aceita pagamento por aproximação.",
    "Não consegui confirmar na página oficial, mas sim, aceita pagamento por aproximação.",
    "Não localizei a página oficial, porém a Get XYZ possui NFC.",
    # review P3-4: the invention that comes after the caveat
    "Não encontrei fonte oficial, mas a Get XYZ aceita pagamento por aproximação.",
    "Não consegui verificar, porém a Get XYZ possui NFC.",
    "Não tenho certeza, no entanto, a Get XYZ aceita pagamento por aproximação.",
    "Não achei a página oficial, contudo a Get XYZ tem NFC.",
    "Não sei dizer, mas aceita pagamento por aproximação.",
]


def web_label_checks(answer):
    case = REPLAN_CASES["REPLAN-WEB"]
    body = {"answer": answer, "route": "knowledge", "status": "answered", "language": "pt", "sources": []}
    return _checks(case, body, {"steps": [], "detail": {}})


@pytest.mark.parametrize("answer", HONEST_WEB_ANSWERS)
def test_the_web_label_accepts_an_honest_admission_or_a_claim_named_as_third_party(answer):
    checks = web_label_checks(answer)
    assert checks["content_ok"] and checks["forbidden_ok"], answer


@pytest.mark.parametrize("answer", INVENTED_WEB_ANSWERS)
def test_the_web_label_rejects_an_invented_yes_for_the_fictional_product(answer):
    checks = web_label_checks(answer)
    assert not (checks["content_ok"] and checks["forbidden_ok"]), answer


def test_nfc_alone_no_longer_satisfies_the_web_label():
    assert not web_label_checks("A maquininha tem NFC.")["content_ok"]


# --- task 72b, round 2 (review P3-6): the fallback with the Support part present ----------------------------------


def test_the_fallback_keeps_the_support_points_before_the_declared_gap(offline, monkeypatch):
    monkeypatch.setattr(replanner, "apply_rules", lambda o: [])
    incomplete = {"next": "finish", "review": "incomplete", "reason": REASON}
    down = lambda call: LLMError("personality down")  # noqa: E731
    client, orchestrator, llm = offline(handler=model_decides(incomplete, personality=down))
    body, trace = handle(orchestrator, "Quando vai cair o dinheiro das vendas de ontem?")
    sentence = policy("unconfirmed", "pt")
    assert body["route"] == "support" and "customer_support" in body["agents"]
    assert body["answer"].endswith(sentence) and body["answer"].count(sentence) == 1
    assert "crédito" in body["answer"][: -len(sentence)]  # the account figures come first, then the gap
