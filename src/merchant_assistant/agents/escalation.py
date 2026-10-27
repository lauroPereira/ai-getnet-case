"""Escalation Agent (fourth agent): prepares and persists the simulated human handoff, idempotently."""

from __future__ import annotations

import hashlib
import json
import uuid

from pydantic import ValidationError

from merchant_assistant.agents.common import prompt
from merchant_assistant.agents.support import outcomes_for_case
from merchant_assistant.data.clock import today
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded, RunContext
from merchant_assistant.orchestration.state import EscalationDraft, EscalationResult, GraphState

RECOVERABLE = (LLMError, ValidationError, LimitExceeded, BudgetExceeded)


def _reason(state: GraphState) -> str:
    if state.decision and state.decision.route == "human_handoff":
        return "customer_request"
    if state.support and state.support.escalation_reason:
        return state.support.escalation_reason
    return "needs_human"


def run(state: GraphState, ctx: RunContext) -> dict:
    agents = [*state.agents, "escalation"]
    reason = _reason(state)
    key = hashlib.sha256(f"{state.conversation_id}|{state.message}|{reason}".encode()).hexdigest()
    conn = ctx.tools.conn
    existing = conn.execute("SELECT * FROM handoff_cases WHERE idempotency_key = ?", (key,)).fetchone()
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

    case = {
        "merchant_message": state.message,
        "intents": state.decision.intents if state.decision else [],
        "checks_at_case_opening": state.prefix,
        "queries": outcomes_for_case(ctx),
        "support_findings": state.support.points if state.support else [],
        "knowledge_points": state.knowledge.points if state.knowledge else [],
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
        draft = ctx.llm.parse(spec, EscalationDraft, ctx).value
    except RECOVERABLE as exc:
        ctx.step_notes["error"] = str(exc)
        draft = EscalationDraft(
            summary=f'Lojista solicitou ajuda: "{state.message[:200]}". Motivo: {reason}.',
            pending_question="Analisar a solicitação e retornar ao lojista.",
        )
    protocol = f"SIM-{today(ctx.clock):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    case_id = f"hc_{uuid.uuid4().hex[:16]}"
    payload = {
        **case,
        "summary": draft.summary,
        "pending_question": draft.pending_question,
        "reason": reason,
        "simulated": True,
    }
    conn.execute(
        "INSERT INTO handoff_cases (case_id, protocol, customer_id, idempotency_key, reason, payload, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            case_id,
            protocol,
            state.user_id,
            key,
            reason,
            json.dumps(payload, ensure_ascii=False, default=str),
            ctx.clock.now().isoformat(timespec="seconds"),
        ),
    )
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
