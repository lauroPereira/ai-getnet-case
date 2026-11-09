"""Router Agent: entry point that decides which specialists handle the message."""

from __future__ import annotations

import re
import unicodedata

from pydantic import ValidationError

from merchant_assistant.agents.common import (
    format_history,
    guess_language,
    history_coverage_instruction,
    policy,
    prompt,
)
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded, RunContext
from merchant_assistant.orchestration.state import GraphState, RouterDecision

SUPPORT_ROUTES = {"support", "knowledge_and_support", "human_handoff"}

# Full-message matches only: a confirmation with a new question or instruction must still reach its specialist.
_RESOLUTION_CLAUSE = r"(?:deu certo|(?:voltou a |j[aá] )?funcionar|funcionou|it works|it worked|working again)"
_ISOLATED_RESOLUTION = re.compile(
    rf"\s*{_RESOLUTION_CLAUSE}(?:\s*[,;.!]+\s*{_RESOLUTION_CLAUSE})*\s*[.!]*\s*", re.IGNORECASE
)
# Task 76: an explicit request to end the whole contract goes to a human. Full-message matches only, so a message that
# names a service or product ("cancel the Payment Link contract"), asks how, or says anything else stays with the model.
# "Close", "fechar", "finalizar" and "terminar" also mean signing or completing a contract ("fechar contrato com a
# Getnet"), so they count only with a possessive (my/our, meu/nosso).
_TERMINATE_EN = (
    r"(?:please\s*,?\s*)?(?:i(?:\s+(?:want|need|wish|would\s+like)|['’]d\s+like)\s+to\s+)?(?:please\s+)?"
    r"(?:(?:end|terminate|cancel)\s+(?:my|the|our)|close\s+(?:my|our))\s+(?:getnet\s+)?contract(?:\s+with\s+getnet)?"
    r"(?:\s*,?\s*please)?"
)
_TERMINATE_PT = (
    r"(?:por\s+favor\s*,?\s*)?(?:(?:eu\s+)?(?:quero|preciso|desejo|gostaria\s+de)\s+)?"
    r"(?:(?:encerrar|cancelar|rescindir|encerre|cancele|rescinda)\s+(?:o\s+)?(?:meu\s+|nosso\s+)?"
    r"|(?:fechar|terminar|finalizar|feche|termine|finalize)\s+(?:o\s+)?(?:meu|nosso)\s+)"
    r"contrato(?:\s+(?:com\s+a|da|na)\s+getnet)?(?:\s*,?\s*por\s+favor)?"
)
_CONTRACT_TERMINATION = re.compile(rf"\s*(?:{_TERMINATE_EN}|{_TERMINATE_PT})\s*[.!]*\s*", re.IGNORECASE)

# Task 94 (D5): the only answers to a pending sale cancellation that count as explicit. The whole message must be made
# of these phrases (accents ignored, punctuation other than "?" dropped), with at least one of its kind: "sim, mas..."
# or "yes, but first..." has other words, a question mark makes it a question, and yes and no together are neither.
_YES_PHRASES = (
    "sim", "s", "pode cancelar", "pode sim", "pode", "pode seguir", "confirmo", "eu confirmo", "confirmado",
    "confirmar", "cancele", "cancela", "quero cancelar", "isso", "yes", "y", "yeah", "yep", "confirm", "i confirm",
    "confirmed", "go ahead", "cancel it", "do it",
)
_NO_PHRASES = (
    "nao", "n", "nao quero", "nao cancele", "nao cancela", "nao precisa", "nao pode", "deixa", "deixa pra la",
    "pode deixar", "mudei de ideia", "desisto", "manter", "mantenha", "no", "nope", "do not cancel", "dont cancel",
    "don't cancel", "keep it", "never mind", "nevermind",
)
_FILLER_PHRASES = ("por favor", "obrigado", "obrigada", "ok", "please", "thanks", "thank you")


def explicit_answer(message: str) -> str | None:
    """`yes` or `no` when the message only confirms or only refuses; otherwise None."""
    if "?" in message:
        return None
    text = unicodedata.normalize("NFKD", message.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    words = re.sub(r"[,;.!:\-\u2013\u2014]+", " ", text).split()
    phrases = (
        [(p.split(), "yes") for p in _YES_PHRASES]
        + [(p.split(), "no") for p in _NO_PHRASES]
        + [(p.split(), None) for p in _FILLER_PHRASES]
    )
    # every way of reading the words as a sequence of known phrases: reach[i] = the kinds met to cover words[:i]
    reach: list[set[frozenset[str]]] = [set() for _ in range(len(words) + 1)]
    reach[0].add(frozenset())
    for i in range(len(words)):
        for met in reach[i]:
            for phrase, kind in phrases:
                if words[i : i + len(phrase)] == phrase:
                    reach[i + len(phrase)].add(met | {kind} if kind else met)
    answers = {next(iter(met)) for met in reach[len(words)] if len(met) == 1} if words else set()
    return answers.pop() if len(answers) == 1 else None


def enforce(
    decision: RouterDecision,
    *,
    new_conversation: bool = False,
    message: str = "",
    case_state: str = "",
    pending_cancellation: bool = False,
) -> RouterDecision:
    """Deterministic rules applied after the model decision."""
    data = decision.model_dump()
    # Task 94 (D5): a yes or no counts only with a cancellation waiting for it, in a safe message that is nothing but
    # that answer; then it is the cancellation's turn (support, topic cancellation) and not a reaction to the case,
    # so the model's case signal is dropped. Anything else is `other`.
    answer = explicit_answer(message) if pending_cancellation and decision.safety == "none" else None
    if decision.confirmation == "other" or decision.confirmation != answer:
        data["confirmation"] = "other"
    else:
        data |= {"route": "support", "topic": "cancellation", "clarification_question": None, "case_signal": "none"}
    if data["route"] == "acknowledgement" and decision.safety == "none" and "?" in message:
        # a message that asks something is not only a reaction to the previous reply ("Obrigado! Qual era o
        # protocolo?"); the Support answers it, from its tools or from the facts recorded in the conversation.
        data |= {"route": "support", "topic": None, "clarification_question": None}
    if new_conversation:  # there is no previous reply to react to
        data["case_signal"] = "none"
        if data["route"] == "acknowledgement":
            data["route"] = "clarify"
        if decision.safety == "none" and data["route"] != "human_handoff" and _CONTRACT_TERMINATION.fullmatch(message):
            data |= {"route": "human_handoff", "topic": "contract", "clarification_question": None}
    elif (
        case_state == "awaiting_customer"
        and decision.safety == "none"
        and data["case_signal"] == "resolved"
        and decision.route != "human_handoff"
        and _ISOLATED_RESOLUTION.fullmatch(message)
    ):
        data["route"] = "acknowledgement"
    if decision.safety != "none":
        data["route"] = "out_of_scope"
    if data["route"] in SUPPORT_ROUTES and data["topic"] is None:
        data["topic"] = "general"
    if data["route"] not in SUPPORT_ROUTES:
        data["topic"] = None
    if data["route"] == "clarify" and not data["clarification_question"]:
        data["clarification_question"] = policy("clarify", decision.language)
    return RouterDecision.model_validate(data)


def run(state: GraphState, ctx: RunContext) -> dict:
    agents = [*state.agents, "router"]
    p = prompt(ctx, "router")
    pending = state.cancellation
    waiting = (  # task 94: only a turn with a cancellation waiting for an answer shows it (router.v7, `confirmation`)
        f"Sale cancellation waiting for the merchant's yes or no: sale of {pending['amount']} on "
        f"{pending['sale_date']}\n\n"
        if pending
        else ""
    )
    history_block = format_history(state.history, summary=state.summary, incomplete=state.history_incomplete)
    instructions = p.render() + history_coverage_instruction(state.history_incomplete)
    spec = CallSpec(
        agent="router",
        instructions=instructions,
        input=(
            f"Conversation so far (oldest first):\n{history_block}\n\n"
            f"Current case: state={state.case.get('state', 'in_progress')}, topic={state.case.get('topic')}\n\n"
            f"{waiting}"
            f"Merchant message:\n<<<\n{state.message}\n>>>"
        ),
        effort="none",
        max_output_tokens=300,
        context={
            "message": state.message,
            "findings": state.guard_findings,
            "history": state.history,
            "case": state.case,
            "pending_cancellation": pending,
        },
    )
    errors = list(state.errors)
    try:
        result = ctx.router_override or ctx.llm_for("router").parse(spec, RouterDecision, ctx).value
        decision = enforce(
            result,
            new_conversation=not state.history,
            message=state.message,
            case_state=state.case.get("state", ""),
            pending_cancellation=pending is not None,
        )
        if pending is not None:
            ctx.step_notes["confirmation"] = {"model": result.confirmation, "validated": decision.confirmation}
        if decision.route == "human_handoff" and result.route != "human_handoff":
            ctx.step_notes["rule"] = "contract_termination"  # the only rule in `enforce` that makes a handoff
        elif result.route == "acknowledgement" and decision.route == "support":
            ctx.step_notes["rule"] = "question_not_acknowledgement"
    except (LLMError, ValidationError, LimitExceeded, BudgetExceeded) as exc:
        errors.append(f"router: {exc}")
        ctx.step_notes["router_unavailable"] = True
        language = guess_language(state.message)
        decision = RouterDecision(
            route="clarify",
            language=language,
            topic=None,
            intents=["router_unavailable"],
            safety="none",
            clarification_question=policy("unavailable", language),
            case_signal="none",
        )
    ctx.step_notes.update(
        prompt=p.ref,
        route=decision.route,
        language=decision.language,
        topic=decision.topic,
        safety=decision.safety,
        case_signal=decision.case_signal,
        history_turns=len(state.history),
    )
    update: dict = {"decision": decision, "agents": agents, "errors": errors}
    if decision.route == "out_of_scope":
        update |= {"status": "refused", "policy": policy("refused", decision.language)}
    elif decision.route == "clarify":
        update |= {"status": "needs_clarification", "policy": decision.clarification_question}
    return update
