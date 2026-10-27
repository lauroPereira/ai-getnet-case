"""Router Agent: entry point that decides which specialists handle the message."""

from __future__ import annotations

from pydantic import ValidationError

from merchant_assistant.agents.common import format_history, guess_language, policy, prompt
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded, RunContext
from merchant_assistant.orchestration.state import GraphState, RouterDecision

SUPPORT_ROUTES = {"support", "knowledge_and_support", "human_handoff"}


def enforce(decision: RouterDecision, *, new_conversation: bool = False) -> RouterDecision:
    """Deterministic rules applied after the model decision."""
    data = decision.model_dump()
    if new_conversation:  # there is no previous reply to react to
        data["case_signal"] = "none"
        if data["route"] == "acknowledgement":
            data["route"] = "clarify"
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
    spec = CallSpec(
        agent="router",
        instructions=p.render(),
        input=(
            f"Conversation so far (oldest first):\n{format_history(state.history)}\n\n"
            f"Current case: state={state.case.get('state', 'in_progress')}, topic={state.case.get('topic')}\n\n"
            f"Merchant message:\n<<<\n{state.message}\n>>>"
        ),
        effort="none",
        max_output_tokens=300,
        context={
            "message": state.message,
            "findings": state.guard_findings,
            "history": state.history,
            "case": state.case,
        },
    )
    errors = list(state.errors)
    try:
        result = ctx.router_override or ctx.llm_for("router").parse(spec, RouterDecision, ctx).value
        decision = enforce(result, new_conversation=not state.history)
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
