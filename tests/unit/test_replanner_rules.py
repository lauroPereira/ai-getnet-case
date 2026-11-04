"""v0.8.0 task 69 (RF-86, RF-87; spec D4 to D6): the replanner's rules are pure functions of what was observed, each
with a name, and the guards that come after them. No graph, no model."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from merchant_assistant.agents import replanner
from merchant_assistant.agents.replanner import Chosen, Observed, allowed_next, apply_rules
from merchant_assistant.config import Settings


def seen(**kwargs) -> Observed:
    base = {"just_ran": "knowledge", "ran": ("knowledge",), "route": "knowledge", "hops": 0, "pending": (),
            "customer_known": True, "knowledge_mode": "rag", "evidence_sufficient": True}
    return Observed(**(base | kwargs))


def after_support(**kwargs) -> Observed:
    base = {"just_ran": "support", "ran": ("support",), "route": "support", "knowledge_mode": None,
            "evidence_sufficient": None, "support_points": True}
    return seen(**(base | kwargs))


def only(o: Observed) -> replanner.Match:
    [match] = apply_rules(o)
    return match


# --- one test per rule: the case is clear, so no model is needed ---------------------------------------------------


@pytest.mark.parametrize(
    ("name", "observed", "next_step", "review"),
    [
        ("complete", seen(), "finish", "complete"),
        ("complete", seen(evidence_sufficient=True, knowledge_gap=("a detail the pages skip",)), "finish", "complete"),
        ("complete", after_support(), "finish", "complete"),
        ("plan_pending", seen(route="knowledge_and_support", knowledge_mode="procedure", pending=("support",)),
         "support", "incomplete"),
        ("plan_pending", seen(controlled_answer=True, pending=("support",), route="knowledge_and_support"),
         "support", "incomplete"),
        ("evidence_insufficient_web", seen(evidence_sufficient=False, knowledge_gap=("not in passages",)),
         "web", "incomplete"),
        ("account_dependent_question", seen(account_dependent=True), "support", "incomplete"),
        ("procedure_gap", after_support(how_to=True), "knowledge", "incomplete"),
        ("tool_failure_no_alternative",
         after_support(support_points=False, failed_tools=("get_device_status:TIMEOUT",)), "escalate", "incomplete"),
        ("support_asked_for_human", after_support(support_escalate=True), "escalate", "incomplete"),
        ("selection_pending", after_support(support_needs_selection=True), "clarify", "incomplete"),
        ("specialist_failed", seen(controlled_answer=True), "finish", "incomplete"),
        ("gap_declared", seen(just_ran="web", ran=("knowledge", "web"), evidence_sufficient=False), "finish",
         "incomplete"),
        ("gap_declared", seen(evidence_sufficient=False, knowledge_unavailable=True, knowledge_gap=("x",)), "finish",
         "incomplete"),
        ("gap_declared", after_support(support_points=False), "finish", "incomplete"),
        ("gap_declared", after_support(support_missing=("which device",)), "finish", "incomplete"),
        ("gap_declared", after_support(failed_tools=("get_payout_status:UNAVAILABLE",)), "finish", "incomplete"),
    ],
)
def test_each_rule_settles_its_case_alone(name, observed, next_step, review):
    match = only(observed)
    assert (match.rule, match.next, match.review) == (name, next_step, review)
    assert match.reason


def test_gap_declared_names_what_could_not_be_confirmed():
    match = only(after_support(support_points=False, failed_tools=("get_payout_status:UNAVAILABLE",)))
    assert match.rule == "tool_failure_no_alternative"  # a down tool and nothing else to try is for a human
    match = only(after_support(support_missing=("which device",), failed_tools=("get_payout_status:UNAVAILABLE",)))
    assert match.rule == "gap_declared" and "which device" in match.gap and len(match.gap) == 2


def test_a_planned_step_is_not_a_change_of_plan():
    planned = only(seen(route="knowledge_and_support", knowledge_mode="procedure", pending=("support",)))
    assert planned.planned is True
    assert only(seen(evidence_sufficient=False)).planned is False


def test_a_down_service_is_not_the_same_as_nothing_found():
    """Only UNAVAILABLE and TIMEOUT count as an outage; the web is not tried for an unavailable index either."""
    assert only(seen(evidence_sufficient=False, knowledge_unavailable=True)).rule == "gap_declared"
    assert only(seen(evidence_sufficient=False)).rule == "evidence_insufficient_web"


def test_a_specialist_never_chosen_twice_by_the_rules():
    after_web = seen(just_ran="web", ran=("knowledge", "web"), evidence_sufficient=False)
    assert all(match.next != "web" for match in apply_rules(after_web))
    answered_by_support = after_support(account_dependent=True, ran=("knowledge", "support"), just_ran="support")
    assert all(match.next != "support" for match in apply_rules(answered_by_support))
    already_in_knowledge = after_support(how_to=True, ran=("support", "knowledge"))
    assert all(match.next != "knowledge" for match in apply_rules(already_in_knowledge))


def test_an_unknown_merchant_is_not_sent_to_support():
    o = seen(account_dependent=True, customer_known=False)
    assert only(o).rule == "complete" and "support" not in allowed_next(o)


# --- when the model is needed: no rule applies, or two disagree ----------------------------------------------


def test_two_rules_that_disagree_go_to_the_model():
    escalate_and_ask = after_support(support_escalate=True, support_needs_selection=True)
    assert {m.next for m in apply_rules(escalate_and_ask)} == {"escalate", "clarify"}
    product_for_my_plan = seen(evidence_sufficient=False, account_dependent=True)
    assert {m.next for m in apply_rules(product_for_my_plan)} == {"support", "web"}


def test_no_rule_applies_to_a_failure_next_to_a_how_to():
    o = after_support(how_to=True, failed_tools=("get_payout_status:TIMEOUT",))
    assert apply_rules(o) == []


def test_allowed_steps_exclude_the_specialists_that_already_ran():
    assert allowed_next(seen()) == ["web", "support", "escalate", "clarify", "finish"]
    assert allowed_next(seen(ran=("knowledge", "web", "support"))) == ["escalate", "clarify", "finish"]


# --- the guards (D5, D6, request limits) ---------------------------------------------------------------------


def ctx(**settings):
    return SimpleNamespace(
        settings=Settings(_env_file=None, **settings), model_calls=2, cost_usd=0.0, remaining_seconds=lambda: 10.0
    )


def wants(next_step, **kwargs):
    return Chosen(next_step, "incomplete", "because", "model", **kwargs)


def test_guard_refuses_a_specialist_that_already_ran():
    out = replanner._guard(wants("knowledge"), seen(), ctx())
    assert (out.next, out.origin, out.review) == ("finish", "rule:no_repeat", "incomplete")
    assert out.notes["refused"] == "knowledge" and out.gap


def test_guard_stops_at_the_hop_budget_and_exempts_the_initial_plan_and_escalation():
    full = seen(hops=3)
    assert replanner._guard(wants("web"), full, ctx()).origin == "rule:hop_budget"
    assert replanner._guard(wants("web"), seen(hops=2), ctx()).next == "web"
    assert replanner._guard(wants("support", planned=True), full, ctx()).next == "support"
    assert replanner._guard(wants("escalate"), full, ctx()).next == "escalate"
    assert replanner._guard(wants("clarify"), full, ctx()).next == "clarify"
    assert replanner._guard(wants("web"), seen(hops=0), ctx(max_plan_hops=0)).origin == "rule:hop_budget"


def test_guard_respects_the_requests_own_limits():
    assert replanner._guard(wants("web"), seen(), ctx(max_model_calls=3)).origin == "rule:request_limits"
    assert replanner._guard(wants("web"), seen(), ctx(max_model_calls=4)).next == "web"  # one more call plus the reply
    spent = ctx()
    spent.cost_usd = spent.settings.max_request_cost_usd
    assert replanner._guard(wants("web"), seen(), spent).origin == "rule:request_limits"
    late = ctx()
    late.remaining_seconds = lambda: 0.0
    assert replanner._guard(wants("web"), seen(), late).origin == "rule:request_limits"


def test_guard_does_not_send_an_unknown_merchant_to_support_by_model_choice():
    out = replanner._guard(wants("support"), seen(customer_known=False), ctx())
    assert out.origin == "rule:unknown_merchant" and out.next == "finish"


def test_the_account_and_how_to_markers_are_specific():
    for text in ("Qual a taxa no meu plano?", "Is it in my plan?", "Posso mudar meu contrato?", "my account limit"):
        assert replanner.ACCOUNT_MESSAGE.search(text), text
    for text in ("Preciso de conta bancária para receber minhas vendas via Pix?", "Do I need a bank account?",
                 "Minha maquininha não conecta"):
        assert not replanner.ACCOUNT_MESSAGE.search(text), text
    for text in ("e como faço para antecipar?", "What should I do?", "how do I get it", "o que eu faço"):
        assert replanner.HOW_TO.search(text), text
    for text in ("Como funciona a antecipação?", "How does it work?"):
        assert not replanner.HOW_TO.search(text), text


def test_the_gap_marker_needs_the_merchants_own_data_not_any_mention_of_an_account():
    mentions = ("merchant's contracted plan", "your own rates", "seu plano contratado", "plano contratado do lojista")
    for text in mentions:
        assert replanner.ACCOUNT_GAP.search(text), text
    others = ("not in passages", "bank account requirements", "contract terms of the Get Smart", "plano Get Smart")
    for text in others:
        assert not replanner.ACCOUNT_GAP.search(text), text
