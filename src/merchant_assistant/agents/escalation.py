"""Escalation Agent (fourth agent): prepares and persists the human handoff, idempotently, and puts the case in the
operator queue (`open`, protocol `HO-AAAAMMDD-XXXXXX`, checkpoint thread = the request that escalated)."""

from __future__ import annotations

import hashlib
import json
import uuid

from pydantic import ValidationError

from merchant_assistant.agents.common import guess_language, policy, prompt
from merchant_assistant.agents.support import outcomes_for_case
from merchant_assistant.data.clock import today
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded, RunContext
from merchant_assistant.orchestration.state import EscalationDraft, EscalationResult, GraphState
from merchant_assistant.tools.base import access_error, write_audit

HANDOFF_CREATE = "handoff:create"
CASE_WRITE = "handoff_case.create"  # audit name of the case write

RECOVERABLE = (LLMError, ValidationError, LimitExceeded, BudgetExceeded)


def _reason(state: GraphState) -> str:
    if state.decision and state.decision.route == "human_handoff":
        return "customer_request"
    if state.support and state.support.escalation_reason:
        return state.support.escalation_reason
    return "needs_human"


DRAFT_OPENING = {
    "pt": "Olá! Sou da equipe de atendimento da Getnet e analisei o seu caso.",
    "en": "Hello! I'm from the Getnet support team and I've reviewed your case.",
}
DRAFT_CLOSING = {
    "pt": "Se precisar de algo mais, é só responder por aqui.",
    "en": "If you need anything else, just reply here.",
}


def draft_reply(state: GraphState, language: str) -> str:
    """Deterministic draft for the operator from the agents' contributions (D15 fallback; `escalation.v2` writes a
    model draft from task 65). Never promises anything the contributions do not say."""
    language = language if language in DRAFT_OPENING else "pt"
    points = [*(state.support.points if state.support else []), *(state.knowledge.points if state.knowledge else [])]
    body = " ".join(str(point).strip() for point in points[:3] if str(point).strip())
    return " ".join(part for part in (DRAFT_OPENING[language], body, DRAFT_CLOSING[language]) if part)


def run(state: GraphState, ctx: RunContext) -> dict:
    agents = [*state.agents, "escalation"]
    reason = _reason(state)
    key = hashlib.sha256(f"{state.conversation_id}|{state.message}|{reason}".encode()).hexdigest()
    conn = ctx.tools.conn
    existing = conn.execute("SELECT * FROM handoff_cases WHERE idempotency_key = ?", (key,)).fetchone()
    if existing is None and state.case.get("state") == "handoff":  # already with a human: one case per conversation
        existing = conn.execute(
            "SELECT * FROM handoff_cases WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1",
            (state.conversation_id,),
        ).fetchone()
    if existing is not None:
        payload = json.loads(existing["payload"])
        result = EscalationResult(
            case_id=existing["case_id"],
            protocol=existing["protocol"],
            reason=existing["reason"],
            summary=payload["summary"],
            pending_question=payload["pending_question"],
            created=False,
        )
        ctx.step_notes.update(protocol=result.protocol, created=False)
        return {"escalation": result, "agents": agents, "status": "handoff"}

    if denied := access_error(ctx.tools.customer, HANDOFF_CREATE):  # checked before the case is written
        write_audit(ctx.tools, CASE_WRITE, HANDOFF_CREATE, denied.code.lower())
        ctx.step_notes["error"] = denied.code
        language = state.decision.language if state.decision else guess_language(state.message)
        return {
            "agents": agents,
            "errors": [*state.errors, f"escalation: {denied.code}"],
            "policy": state.policy or policy("unavailable", language),
        }

    case = {
        "merchant_message": state.message,
        "intents": state.decision.intents if state.decision else [],
        "checks_at_case_opening": state.prefix,
        "queries": outcomes_for_case(ctx),
        "support_findings": state.support.points if state.support else [],
        "knowledge_points": state.knowledge.points if state.knowledge else [],
        "troubleshooting_attempts": state.case.get("attempts", []),
        "conversation": state.history[-8:],
    }
    p = prompt(ctx, "escalation")
    ctx.step_notes["prompt"] = p.ref
    spec = CallSpec(
        agent="escalation",
        instructions=p.render(reason=reason, case=json.dumps(case, ensure_ascii=False, default=str)[:6000]),
        input="Write the handover.",
        effort="none",
        max_output_tokens=400,
        context={"reason": reason, "case": case},
    )
    try:
        draft = ctx.llm_for("escalation").parse(spec, EscalationDraft, ctx).value
    except RECOVERABLE as exc:
        ctx.step_notes["error"] = str(exc)
        draft = EscalationDraft(
            summary=f'Lojista solicitou ajuda: "{state.message[:200]}". Motivo: {reason}.',
            pending_question="Analisar a solicitação e retornar ao lojista.",
        )
    protocol = f"HO-{today(ctx.clock):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    language = state.decision.language if state.decision else guess_language(state.message)
    case_id = f"hc_{uuid.uuid4().hex[:16]}"
    payload = {
        **case,
        "summary": draft.summary,
        "pending_question": draft.pending_question,
        "draft_reply": draft_reply(state, language),
        "language": language,
        "reason": reason,
    }
    conn.execute(
        "INSERT INTO handoff_cases (case_id, protocol, customer_id, idempotency_key, reason, payload, created_at, "
        "conversation_id, queue_state, channel, thread_id) VALUES (?,?,?,?,?,?,?,?,'open',?,?)",
        (
            case_id,
            protocol,
            state.user_id,
            key,
            reason,
            json.dumps(payload, ensure_ascii=False, default=str),
            ctx.clock.now().isoformat(timespec="seconds"),
            state.conversation_id,
            ctx.channel,
            ctx.request_id,  # D6: the checkpoint thread is the request that escalated
        ),
    )
    write_audit(ctx.tools, CASE_WRITE, HANDOFF_CREATE, "ok", case_id)
    result = EscalationResult(
        case_id=case_id,
        protocol=protocol,
        reason=reason,
        summary=draft.summary,
        pending_question=draft.pending_question,
        created=True,
    )
    ctx.step_notes.update(protocol=protocol, created=True, reason=reason)
    return {"escalation": result, "agents": agents, "status": "handoff"}
