"""Customer Support Agent: deterministic case prefix (history + healthcheck) and tool-using specialist."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from pydantic import ValidationError

from merchant_assistant.agents.common import LANGUAGE_NAME, format_history, policy, prompt
from merchant_assistant.conversations import MAX_TECHNICAL_CYCLES, PREFIX_TTL
from merchant_assistant.data.clock import today
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded, RunContext
from merchant_assistant.orchestration.state import GraphState, SupportDraft, SupportResult
from merchant_assistant.tools.registry import AGENT_TOOLS, model_tool_schemas

RECOVERABLE = (LLMError, ValidationError, LimitExceeded, BudgetExceeded)


def run_prefix(state: GraphState, ctx: RunContext) -> dict:
    """Opens the support case without any model call. Failures are recorded, never blocking (handoff stays possible)."""
    if not state.customer_known:
        ctx.step_notes["skipped"] = "customer_not_found"
        return {"prefix": {"customer_known": False}}
    topic = (state.decision.topic if state.decision else None) or "general"
    cache = state.prefix_cache or {}
    if cache.get("data") and cache.get("topic") == topic and cache.get("at"):
        age = ctx.clock.now() - datetime.fromisoformat(cache["at"])
        if age <= PREFIX_TTL:  # same case, same topic, still fresh: no new queries
            ctx.step_notes.update(topic=topic, reused=True, age_s=int(age.total_seconds()))
            return {"prefix": {**cache["data"], "reused": True}}
    history = ctx.run_tool("get_complaint_history", {"topic": topic}, agent=None)
    health = ctx.run_tool("run_customer_healthcheck", {"topic": topic}, agent=None)
    prefix = {
        "customer_known": True,
        "topic": topic,
        "history": history.data if history.ok else {"error": history.error},
        "healthcheck": health.data if health.ok else {"error": health.error},
    }
    ctx.step_notes.update(topic=topic, history_ok=history.ok, healthcheck_ok=health.ok, reused=False)
    return {"prefix": prefix}


def _attempts_summary(attempts: list[dict]) -> str:
    if not attempts:
        return "- None yet."
    lines = [f"- cycle {a['cycle']}: {a['step']} -> {a['result']}" for a in attempts]
    return "\n".join(lines)


def _prefix_summary(prefix: dict) -> str:
    history = prefix.get("history", {})
    health = prefix.get("healthcheck", {})
    lines = []
    if "error" in history:
        lines.append(f"- Support history unavailable ({history['error']['code']}).")
    else:
        for case in history.get("cases", [])[:3]:
            tried = "; ".join(f"{a['step']} -> {a['result']}" for a in case.get("attempts", []))
            lines.append(
                f"- Previous case {case['status']} ({case['topic']}): {case['summary']} Tried: {tried or 'n/a'}"
            )
        if not history.get("cases"):
            lines.append("- No previous support cases for this topic.")
    if "error" in health:
        lines.append(f"- Healthcheck unavailable ({health['error']['code']}).")
    else:
        for c in health.get("checks", []):
            lines.append(f"- Check {c['check']}: {c['status']} ({c['note']})")
    return "\n".join(lines)


def run(state: GraphState, ctx: RunContext) -> dict:
    decision = state.decision
    language = decision.language if decision else "en"
    agents = [*state.agents, "customer_support"]
    if not state.customer_known:
        result = SupportResult(
            points=[policy("account_not_found", language)],
            needs_selection=False,
            missing=[],
            escalate=False,
            escalation_reason=None,
        )
        return {"support": result, "agents": agents, "status": "answered"}

    cycles = int(state.case.get("technical_cycles", 0))
    signal = decision.case_signal if decision else "none"
    if signal == "still_failing" and state.case.get("state") == "handoff":
        ctx.step_notes.update(already_handed_off=True)
        result = SupportResult(
            points=[], needs_selection=False, missing=[], escalate=True, escalation_reason="already_with_human"
        )
        return {"support": result, "agents": agents}
    if signal == "still_failing" and cycles >= MAX_TECHNICAL_CYCLES:
        ctx.step_notes.update(cycles=cycles, limit_reached=True)
        result = SupportResult(
            points=[], needs_selection=False, missing=[], escalate=True, escalation_reason="technical_cycles_exhausted"
        )
        return {"support": result, "agents": agents}

    now = ctx.clock.now()
    d0 = today(ctx.clock)
    procedure = ""
    if state.knowledge and state.knowledge.points:
        procedure = "\n".join(f"- {p}" for p in state.knowledge.points)
    p = prompt(ctx, "support")
    ctx.step_notes["prompt"] = p.ref
    spec = CallSpec(
        agent="customer_support",
        instructions=p.render(
            now=now.isoformat(timespec="minutes"),
            timezone=ctx.settings.timezone,
            today=d0.isoformat(),
            yesterday=(d0 - timedelta(days=1)).isoformat(),
            prefix=_prefix_summary(state.prefix) or "- Nothing.",
            procedure=procedure or "- None.",
            language_name=LANGUAGE_NAME[language],
            history=format_history(state.history, limit=8),
            case_status=state.case.get("state", "in_progress"),
            case_signal=signal,
            attempts=_attempts_summary(state.case.get("attempts", [])),
        ),
        input=f"Merchant message:\n<<<\n{state.message}\n>>>",
        effort="low",
        max_output_tokens=1200,
        context={
            "message": state.message,
            "topic": decision.topic if decision else None,
            "procedure": procedure,
            "today": d0.isoformat(),
            "case_signal": signal,
            "attempts": state.case.get("attempts", []),
        },
    )
    before = len(ctx.outcomes)
    try:
        draft = ctx.llm_for("support").run_tools(
            spec,
            SupportDraft,
            ctx,
            tools=model_tool_schemas("customer_support"),
            call_tool=ctx.tool_caller("customer_support"),
            max_tool_calls=max(ctx.settings.max_tool_calls - ctx.tool_calls, 0),
        ).value
    except RECOVERABLE as exc:
        ctx.step_notes["error"] = str(exc)
        result = SupportResult(
            points=[],
            needs_selection=False,
            missing=[],
            escalate=True,
            escalation_reason=f"support_unavailable: {type(exc).__name__}",
        )
        return {"support": result, "agents": agents, "errors": [*state.errors, f"support: {exc}"]}
    specialist = set(AGENT_TOOLS["customer_support"])
    used = [o for o in ctx.outcomes[before:] if o.name in specialist]
    result = SupportResult(**draft.model_dump(), tools_used=[o.name for o in used])
    ctx.step_notes.update(
        tools=[o.name for o in used],
        failed=[o.name for o in used if not o.ok],
        escalate=result.escalate,
        steps_given=result.steps_given,
        cycles_before=cycles,
    )
    update: dict = {"support": result, "agents": agents}
    if not result.escalate:
        clarify = result.needs_selection or (result.missing and not result.points)
        update["status"] = "needs_clarification" if clarify else "answered"
    return update


def outcomes_for_case(ctx: RunContext) -> list[dict]:
    """Compact record of every tool call in this request, for the handoff package."""
    return [
        {
            "tool": o.name,
            "arguments": o.arguments,
            "ok": o.ok,
            "error": o.error,
            "result_excerpt": json.dumps(o.data, ensure_ascii=False, default=str)[:600] if o.ok else None,
        }
        for o in ctx.outcomes
    ]
