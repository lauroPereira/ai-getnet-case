"""Personality: writes the final reply in a consistent voice from the agents' structured contributions.

It cannot change facts: the output guard checks amounts, dates and percentages against the request evidence.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from merchant_assistant.agents.common import LANGUAGE_NAME, policy, prompt
from merchant_assistant.data.clock import today
from merchant_assistant.guardrails.output import drop_unsupported_sentences, unsupported
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded, RunContext
from merchant_assistant.orchestration.state import GraphState, PersonalityOutput

RECOVERABLE = (LLMError, ValidationError, LimitExceeded, BudgetExceeded)

HANDOFF_LINE = {
    "pt": "Encaminhei seu caso para um atendente (simulação desta demonstração). Protocolo: {protocol}.",
    "en": "I've handed your case to a human agent (simulated in this demo). Protocol: {protocol}.",
}


def final_status(state: GraphState) -> str:
    return state.status or "answered"


def contributions(state: GraphState, language: str) -> dict:
    data: dict = {"status": final_status(state), "language": language}
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
            "simulated": True,
            "message": HANDOFF_LINE[language].format(protocol=state.escalation.protocol),
        }
    return data


def deterministic_answer(state: GraphState, language: str) -> str:
    """Fallback used when the model is unavailable or its text fails the output guard."""
    parts: list[str] = []
    if state.policy:
        parts.append(state.policy)
    if state.knowledge:
        parts += state.knowledge.points or (
            [policy("no_evidence", language)] if state.knowledge.mode != "web" else [policy("unavailable", language)]
        )
    if state.support:
        parts += state.support.points
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
    return texts


def run(state: GraphState, ctx: RunContext) -> dict:
    language = state.decision.language if state.decision else "en"
    status = final_status(state)
    agents = [*state.agents, "personality"]
    data = contributions(state, language)
    p = prompt(ctx, "personality")
    ctx.step_notes["prompt"] = p.ref
    spec = CallSpec(
        agent="personality",
        instructions=p.render(
            language_name=LANGUAGE_NAME[language],
            status=status,
            today=today(ctx.clock).isoformat(),
            contributions=json.dumps(data, ensure_ascii=False, indent=1),
        ),
        input="Write the final reply to the merchant.",
        effort="none",
        max_output_tokens=600,
        context={"contributions": data, "status": status, "language": language},
    )
    try:
        draft = ctx.llm.parse(spec, PersonalityOutput, ctx).value.answer.strip()
        source = "personality"
    except RECOVERABLE as exc:
        ctx.step_notes["error"] = str(exc)
        draft, source = deterministic_answer(state, language), "fallback"
    if state.escalation and state.escalation.protocol not in draft:
        draft = f"{draft}\n{HANDOFF_LINE[language].format(protocol=state.escalation.protocol)}"
    ctx.step_notes["source"] = source
    return {"draft_answer": draft, "status": status, "agents": agents}


def run_output_guard(state: GraphState, ctx: RunContext) -> dict:
    language = state.decision.language if state.decision else "en"
    answer = state.draft_answer or deterministic_answer(state, language)
    ev = evidence(state, ctx)
    ref = today(ctx.clock)
    violations = unsupported(answer, ev, ref)
    ctx.step_notes["violations"] = [f"{v.kind}:{v.value}" for v in violations]
    if violations:
        fallback = deterministic_answer(state, language)
        if not unsupported(fallback, ev, ref):
            answer = fallback
        else:
            answer = drop_unsupported_sentences(answer, ev, ref) or policy("unavailable", language)
    return {"answer": answer, "output_violations": [f"{v.kind}:{v.value}" for v in violations]}
