"""Task 76: an explicit request to end the whole contract goes to a human, even when the model asks to clarify.

Scripted model, no network, no cost. The rule lives in `router.enforce` (after the model decision); `router.v6` is
unchanged.
"""

from __future__ import annotations

import uuid

import pytest

from merchant_assistant.agents import router
from merchant_assistant.api.schemas import MessageRequest
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation.runner import CHECK_KEYS, _checks, load_cases
from merchant_assistant.evaluation.scripted_policy import handler as scripted_handler
from merchant_assistant.orchestration.state import RouterDecision
from merchant_assistant.testing import offline_orchestrator

CLARIFY_EN = "Do you want to end your Getnet contract entirely, or cancel a specific service?"  # QA r4, rep. 1


def decision(route="clarify", topic=None, safety="none", language="en", signal="none"):
    return RouterDecision(
        route=route,
        language=language,
        topic=topic,
        intents=["contract_termination"],
        safety=safety,
        clarification_question=CLARIFY_EN if route == "clarify" else None,
        case_signal=signal,
    )


EXPLICIT = [
    "I want to close my contract.",
    "I want to close my contract",
    "i want to close my contract!",
    "I'd like to terminate my contract.",
    "I would like to end my Getnet contract.",
    "I need to cancel my contract with Getnet.",
    "Please close my contract.",
    "Close my contract, please.",
    "Cancel the contract.",
    "Quero encerrar meu contrato.",
    "quero encerrar o meu contrato",
    "Quero cancelar o contrato.",
    "Gostaria de rescindir meu contrato com a Getnet.",
    "Preciso encerrar o contrato da Getnet.",
    "Por favor, encerre meu contrato.",
    "Cancele meu contrato, por favor.",
    "Encerrar contrato.",
    "I want to close our contract.",
    "Quero fechar meu contrato.",
    "Quero finalizar o nosso contrato com a Getnet.",
]

NOT_EXPLICIT = [
    "Quero cancelar o serviço X.",
    "quero cancelar o serviço de antecipação",
    "Quero cancelar o Link de Pagamento.",
    "Quero encerrar o contrato da maquininha.",
    "Quero cancelar o contrato do Pix.",
    "I want to cancel my Payment Link contract.",
    "I want to close the contract for my card machine.",
    "I want to cancel a service.",
    "I want to cancel.",
    "How do I close my contract?",
    "Can I close my contract?",
    "Quero encerrar meu contrato?",
    "Como encerro meu contrato?",
    "I don't want to close my contract.",
    "Não quero encerrar meu contrato.",
    "I want to close my contract and get a refund for yesterday's sale.",
    "Quero encerrar meu contrato e cancelar a venda de ontem.",
    "What happens if I close my contract?",
    "I want to close my account.",
    # review P2-76: "fechar/finalizar/close the contract" also means signing or completing one
    "Quero fechar contrato com a Getnet.",
    "Gostaria de fechar contrato.",
    "Quero finalizar o contrato.",
    "Preciso fechar o contrato da Getnet.",
    "I want to close the contract.",
    "Close the contract.",
    "Feche o contrato.",
    "Quero terminar o contrato.",
]


@pytest.mark.parametrize("message", EXPLICIT)
@pytest.mark.parametrize("model_route", ["clarify", "support", "knowledge"])
def test_explicit_termination_in_a_new_conversation_goes_to_a_human(message, model_route):
    result = router.enforce(decision(route=model_route), new_conversation=True, message=message)
    assert result.route == "human_handoff"
    assert result.topic == "contract"
    assert result.clarification_question is None
    assert result.case_signal == "none"


@pytest.mark.parametrize("message", NOT_EXPLICIT)
def test_service_specific_ambiguous_or_mixed_messages_keep_the_model_decision(message):
    model = decision()
    assert router.enforce(model, new_conversation=True, message=message) == router.enforce(
        model, new_conversation=True, message=""
    )
    assert router.enforce(model, new_conversation=True, message=message).route == "clarify"
    support = decision(route="support", topic="cancellation")
    assert router.enforce(support, new_conversation=True, message=message).route == "support"


def test_the_rule_needs_a_new_conversation_and_no_safety_flag():
    message = "I want to close my contract."
    assert router.enforce(decision(), message=message, case_state="awaiting_customer").route == "clarify"
    assert router.enforce(decision(), message=message, case_state="handoff").route == "clarify"
    for safety in ("unsafe", "sensitive", "injection"):
        result = router.enforce(decision(safety=safety), new_conversation=True, message=message)
        assert result.route == "out_of_scope" and result.topic is None


def test_a_model_handoff_is_left_as_the_model_chose_it():
    for topic, expected in ((None, "general"), ("general", "general"), ("contract", "contract")):
        result = router.enforce(
            decision(route="human_handoff", topic=topic), new_conversation=True, message="I want to close my contract."
        )
        assert (result.route, result.topic) == ("human_handoff", expected)


# --- programmed regression of the journey, with the Router answering as it did in QA r4 rep. 1 -------------------

CASE = {c.id: c for c in load_cases([PROJECT_ROOT / "tests" / "scenarios" / "business_journeys.jsonl"])}[
    "V030-CONTRACT-TERMINATION"
]


def clarifying_router(call):
    """The scripted policy, except that the Router asks to clarify every message (the r4 failure)."""
    if call.spec.agent == "router":
        language = "pt" if call.spec.context["message"].lower().startswith(("quero", "não")) else "en"
        return decision(language=language).model_dump()
    return scripted_handler(call)


def _ask(orchestrator, message):
    request_id = f"req_t76_{uuid.uuid4().hex[:12]}"
    body = orchestrator.handle(MessageRequest(message=message, user_id=CASE.user_id), request_id).model_dump()
    return body, orchestrator.trace(request_id)


def test_contract_termination_journey_hands_off_in_every_repetition(settings):
    orchestrator, _ = offline_orchestrator(settings, handler=clarifying_router)
    protocols = set()
    for _repetition in range(3):
        body, trace = _ask(orchestrator, CASE.message)
        checks = _checks(CASE, body, trace)
        assert all(checks[key] for key in CHECK_KEYS), (body, checks)
        assert body["route"] == "human_handoff" and body["status"] == "handoff"
        assert "HO-" in body["answer"]
        protocols.add(body["answer"].split("HO-", 1)[1][:15])
        assert _router_step(trace)["detail"]["rule"] == "contract_termination"  # the trace says the rule acted
    assert len(protocols) == 3  # a new conversation, a new handoff case each time


def test_portuguese_termination_hands_off_and_a_service_cancellation_still_clarifies(settings):
    orchestrator, _ = offline_orchestrator(settings, handler=clarifying_router)
    body, _ = _ask(orchestrator, "Quero encerrar meu contrato.")
    assert (body["route"], body["status"]) == ("human_handoff", "handoff")
    assert "HO-" in body["answer"] and "atendente" in body["answer"].lower()
    body, trace = _ask(orchestrator, "Quero cancelar o serviço X.")
    assert (body["route"], body["status"]) == ("clarify", "needs_clarification")
    assert "HO-" not in body["answer"]
    assert "rule" not in _router_step(trace)["detail"]


def _router_step(trace):
    return next(step for step in trace["steps"] if step["step"] == "router")


def test_the_trace_has_no_rule_note_when_the_model_already_handed_off(settings):
    def handing_off_router(call):
        if call.spec.agent == "router":
            return decision(route="human_handoff", topic="contract").model_dump()
        return scripted_handler(call)

    orchestrator, _ = offline_orchestrator(settings, handler=handing_off_router)
    body, trace = _ask(orchestrator, CASE.message)
    assert (body["route"], body["status"]) == ("human_handoff", "handoff")
    assert "rule" not in _router_step(trace)["detail"]


def test_signing_a_contract_keeps_the_model_decision_end_to_end(settings):
    def signup_router(call):
        if call.spec.agent == "router":
            return decision(route="knowledge", language="pt").model_dump()
        return scripted_handler(call)

    orchestrator, _ = offline_orchestrator(settings, handler=signup_router)
    body, trace = _ask(orchestrator, "Quero fechar contrato com a Getnet.")
    assert body["route"] == "knowledge" and body["status"] != "handoff"
    assert "rule" not in _router_step(trace)["detail"]
