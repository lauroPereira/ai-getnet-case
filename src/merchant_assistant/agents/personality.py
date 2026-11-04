"""Personality: writes the final reply in a consistent voice from the agents' structured contributions.

It cannot change facts: the output guard checks amounts, dates and percentages against the request evidence.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from merchant_assistant.agents.common import LANGUAGE_NAME, format_history, policy, prompt
from merchant_assistant.cases import Turn, next_state
from merchant_assistant.data.clock import today
from merchant_assistant.guardrails.output import drop_unsupported_sentences, unsupported
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded, RunContext
from merchant_assistant.orchestration.state import GraphState, PersonalityOutput

RECOVERABLE = (LLMError, ValidationError, LimitExceeded, BudgetExceeded)

HANDOFF_LINE = {
    "pt": "Encaminhei seu caso para um atendente da nossa equipe, que vai responder por aqui. Protocolo: {protocol}.",
    "en": "I've handed your case to a human agent on our support team, who will reply here. Protocol: {protocol}.",
}


def final_status(state: GraphState) -> str:
    return state.status or "answered"


def operator_text(state: GraphState) -> str | None:
    """The human agent's reply (approved draft or own text); None for `reject` or outside a resumed flow."""
    if state.operator and state.operator.get("action") in ("approve", "reply"):
        return (state.operator.get("text") or "").strip() or None
    return None


def contributions(state: GraphState, language: str) -> dict:
    data: dict = {"status": final_status(state), "language": language}
    if state.operator:  # resumed by a human agent: only the operator's reply or the re-run support speaks
        data["operator"] = {"action": state.operator.get("action"), "from_operator": True}
        if text := operator_text(state):
            data["operator"]["text"] = text
        if state.support and state.operator.get("action") == "reject":
            data["support"] = {
                "points": state.support.points,
                "missing": state.support.missing,
                "needs_selection": state.support.needs_selection,
            }
        return data
    if state.policy:
        data["policy_text"] = state.policy
    if state.knowledge:
        k = state.knowledge
        data["knowledge"] = {
            "mode": k.mode,
            "points": k.points,
            "evidence_sufficient": k.evidence_sufficient,
            "missing": k.missing,
            "sources": [c.title for c in k.citations],
        }
        if not k.evidence_sufficient and not k.points:
            data["knowledge"]["note"] = (
                policy("no_evidence", language) if k.mode != "web" else policy("unavailable", language)
            )
    if state.support:
        data["support"] = {
            "points": state.support.points,
            "missing": state.support.missing,
            "needs_selection": state.support.needs_selection,
        }
    if state.escalation:
        data["handoff"] = {
            "protocol": state.escalation.protocol,
            "message": HANDOFF_LINE[language].format(protocol=state.escalation.protocol),
        }
    if gap := state.plan.get("gap"):  # the replanner ran out of ways to confirm this: say so, without guessing
        data["unconfirmed"] = gap
    return data


def deterministic_answer(state: GraphState, language: str, case_state: str | None = None) -> str:
    """Fallback used when the model is unavailable or its text fails the output guard."""
    if state.operator:
        text = operator_text(state)
        points = state.support.points if state.support and not text else []
        return text or "\n".join(points) or policy("unavailable", language)
    if state.decision and state.decision.route == "acknowledgement":
        return policy("ack_resolved" if case_state == "resolved" else "ack", language)
    parts: list[str] = []
    if state.policy:
        parts.append(state.policy)
    already_says_missing = False
    if state.knowledge and state.knowledge.mode != "procedure":  # procedure points are guidance for the support agent
        parts += state.knowledge.points or (
            [policy("no_evidence", language)] if state.knowledge.mode != "web" else [policy("unavailable", language)]
        )
        already_says_missing = not state.knowledge.points
    if state.support:
        parts += state.support.points
    if state.plan.get("gap") and not already_says_missing:  # the replanner declared something it could not confirm
        parts.append(policy("unconfirmed", language))
    if state.escalation:
        parts.append(HANDOFF_LINE[language].format(protocol=state.escalation.protocol))
    return "\n".join(p for p in parts if p) or policy("unavailable", language)


def evidence(state: GraphState, ctx: RunContext) -> list[str]:
    texts = [state.message, state.policy or ""]
    texts += [json.dumps(o.data, ensure_ascii=False, default=str) for o in ctx.outcomes if o.ok]
    if state.knowledge:
        texts += state.knowledge.evidence_texts
    if state.escalation:
        texts.append(state.escalation.protocol)
    if text := operator_text(state):  # the human agent's text is valid evidence for the output guard
        texts.append(text)
    return texts


def run(state: GraphState, ctx: RunContext) -> dict:
    language = state.decision.language if state.decision else "en"
    status = final_status(state)
    agents = [*state.agents, "personality"]
    signal = state.decision.case_signal if state.decision else "none"
    tool_verified = bool(state.support and state.support.issue_verified_by_tool)
    case_state, evidence = next_state(
        state.case.get("state", "in_progress"),
        state.case.get("evidence"),
        Turn(status, signal, tool_verified, via_operator=state.operator is not None),
    )
    case_next = {"state": case_state, "evidence": evidence}
    data = contributions(state, language)
    data |= {
        "route": state.decision.route if state.decision else None,
        "case_signal": signal,
        "case_state_after_reply": case_state,
    }
    p = prompt(ctx, "personality")
    ctx.step_notes["prompt"] = p.ref
    spec = CallSpec(
        agent="personality",
        instructions=p.render(
            language_name=LANGUAGE_NAME[language],
            status=status,
            today=today(ctx.clock).isoformat(),
            contributions=json.dumps(data, ensure_ascii=False, indent=1),
            history=format_history(state.history, limit=4),
            case_state=case_state,
        ),
        input="Write the final reply to the merchant.",
        effort="none",
        max_output_tokens=600,
        context={"contributions": data, "status": status, "language": language},
    )
    try:
        draft = ctx.llm_for("personality").parse(spec, PersonalityOutput, ctx).value.answer.strip()
        source = "personality"
    except RECOVERABLE as exc:
        ctx.step_notes["error"] = str(exc)
        draft, source = deterministic_answer(state, language, case_state), "fallback"
    if state.escalation and not state.operator and state.escalation.protocol not in draft:
        draft = f"{draft}\n{HANDOFF_LINE[language].format(protocol=state.escalation.protocol)}"
    ctx.step_notes.update(source=source, case_state=case_state, evidence=evidence)
    return {"draft_answer": draft, "status": status, "agents": agents, "case_next": case_next}


def run_output_guard(state: GraphState, ctx: RunContext) -> dict:
    language = state.decision.language if state.decision else "en"
    answer = state.draft_answer or deterministic_answer(state, language, state.case_next.get("state"))
    ev = evidence(state, ctx)
    ref = today(ctx.clock)
    violations = unsupported(answer, ev, ref)
    ctx.step_notes["violations"] = [f"{v.kind}:{v.value}" for v in violations]
    if violations:
        fallback = deterministic_answer(state, language, state.case_next.get("state"))
        if not unsupported(fallback, ev, ref):
            answer = fallback
        else:
            answer = drop_unsupported_sentences(answer, ev, ref) or policy("unavailable", language)
    return {"answer": answer, "output_violations": [f"{v.kind}:{v.value}" for v in violations]}
