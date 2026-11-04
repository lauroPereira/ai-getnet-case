"""Agent orchestration: LangGraph state graph with typed state and direct calls between nodes.

input_guard -> router -> {knowledge | support_prefix -> [knowledge] -> support | escalation} -> personality
-> output_guard. Every node is traced; recoverable failures are handled inside the agents.

Human review (ADR 0018, v0.7.0): when Escalation opens a case, the state at the end of the handed-off turn enters the
review graph, compiled with a SQLite checkpointer, and stops in `human_review` with `interrupt()` under
thread = the escalating request (D6). An operator's action resumes that thread with `Command(resume=...)`:
approve/reply -> personality -> output_guard; reject -> support (operator instruction, one cycle) -> personality ->
output_guard. The attendance graph has no checkpointer, so a turn without a handoff never touches checkpoints.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from merchant_assistant.agents import escalation, knowledge, personality, router, support
from merchant_assistant.agents.common import guess_language, policy
from merchant_assistant.api.identity import Principal
from merchant_assistant.api.schemas import Handoff, MessageRequest, MessageResponse, Resolution, Source
from merchant_assistant.config import Settings
from merchant_assistant.conversations import Conversation, ConversationStore
from merchant_assistant.data.clock import Clock
from merchant_assistant.data.db import connect
from merchant_assistant.data.webhook_outbox import TARGETS, enqueue, webhook_targets
from merchant_assistant.guardrails.input import check_input
from merchant_assistant.handoffs import transcript
from merchant_assistant.llm.base import LLM, OutputTokenLimitLLM
from merchant_assistant.observability.traces import TraceRecorder, TraceStore
from merchant_assistant.orchestration.budget import BudgetGuard, CombinedBudgetGuard
from merchant_assistant.orchestration.run import RunContext
from merchant_assistant.orchestration.state import (
    Citation,
    EscalationResult,
    GraphState,
    KnowledgeResult,
    RouterDecision,
    SupportResult,
)
from merchant_assistant.rag.index import KnowledgeIndex
from merchant_assistant.tools.base import CustomerContext, ToolEnv

log = logging.getLogger("merchant_assistant.orchestrator")

NodeFn = Callable[[GraphState, RunContext], dict]

TOOL_TITLES = {
    "get_receivables_schedule": "Receivables schedule (your account)",
    "get_payout_status": "Payout status (your account)",
    "get_device_status": "Card machine status (your account)",
    "find_authorization_events": "Card authorization events (your account)",
    "get_contract_snapshot": "Contracted products (your account)",
    "simulate_pricing": "Synthetic pricing and independent charge comparison",
    "get_fee_breakdown": "Recorded fee breakdown (synthetic charge service)",
    "get_enablement_requests": "Card-scheme enablement requests (your account)",
    "get_sale_cancellation_context": "Sale cancellation status (your account)",
}


def input_guard(state: GraphState, ctx: RunContext) -> dict:
    result = check_input(state.message)
    ctx.step_notes.update(findings=result.findings, blocked=result.blocked)
    update: dict = {"message": result.masked, "guard_findings": result.findings, "guard_blocked": result.blocked}
    if result.blocked:
        language = guess_language(result.masked)
        update |= {
            "decision": RouterDecision(
                route="out_of_scope",
                language=language,
                topic=None,
                intents=["blocked_by_input_guard"],
                safety="injection",
                clarification_question=None,
                case_signal="none",
            ),
            "status": "refused",
            "policy": policy("refused", language),
        }
    return update


def _traced(name: str, fn: NodeFn):
    def node(state: GraphState, config: RunnableConfig) -> dict:
        ctx: RunContext = config["configurable"]["ctx"]
        ctx.step_notes = {}
        step, t0 = ctx.trace.start(name)
        try:
            update = fn(state, ctx)
            ctx.trace.finish(step, t0, "error" if "error" in ctx.step_notes else "ok", **ctx.step_notes)
            return update
        except Exception as exc:  # unexpected: keep the request alive with a controlled answer
            log.exception("node failed", extra={"event": {"request_id": ctx.request_id, "node": name}})
            ctx.trace.finish(step, t0, "exception", error=f"{type(exc).__name__}: {exc}", **ctx.step_notes)
            language = state.decision.language if state.decision else guess_language(state.message)
            return {
                "errors": [*state.errors, f"{name}: {type(exc).__name__}"],
                "policy": state.policy or policy("unavailable", language),
            }

    return node


def _after_guard(s: GraphState) -> str:
    return "personality" if s.guard_blocked else "router"


def _after_router(s: GraphState) -> str:
    route = s.decision.route
    if route in ("knowledge", "general_web"):
        return "knowledge"
    if route in ("support", "knowledge_and_support", "human_handoff"):
        return "support_prefix"
    return "personality"


def _after_prefix(s: GraphState) -> str:
    route = s.decision.route
    if route == "human_handoff":
        return "escalation"
    return "knowledge" if route == "knowledge_and_support" else "support"


def _after_knowledge(s: GraphState) -> str:
    return "support" if s.decision.route == "knowledge_and_support" else "personality"


def _after_support(s: GraphState) -> str:
    return "escalation" if s.support and s.support.escalate else "personality"


def build_graph():
    g = StateGraph(GraphState)
    for name, fn in [
        ("input_guard", input_guard),
        ("router", router.run),
        ("knowledge", knowledge.run),
        ("support_prefix", support.run_prefix),
        ("support", support.run),
        ("escalation", escalation.run),
        ("personality", personality.run),
        ("output_guard", personality.run_output_guard),
    ]:
        g.add_node(name, _traced(name, fn))
    g.add_edge(START, "input_guard")
    g.add_conditional_edges("input_guard", _after_guard, ["router", "personality"])
    g.add_conditional_edges("router", _after_router, ["knowledge", "support_prefix", "personality"])
    g.add_conditional_edges("support_prefix", _after_prefix, ["knowledge", "support", "escalation"])
    g.add_conditional_edges("knowledge", _after_knowledge, ["support", "personality"])
    g.add_conditional_edges("support", _after_support, ["escalation", "personality"])
    g.add_edge("escalation", "personality")
    g.add_edge("personality", "output_guard")
    g.add_edge("output_guard", END)
    return g.compile()


# Types stored in checkpoints: registered explicitly (unregistered types will be refused by langgraph).
CHECKPOINT_TYPES = [
    (cls.__module__, cls.__name__)
    for cls in (GraphState, RouterDecision, KnowledgeResult, Citation, SupportResult, EscalationResult)
]


class ResumeError(Exception):
    """The operator's action was recorded but the flow could not be resumed (the case stays recoverable)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def human_review(state: GraphState, config: RunnableConfig) -> dict:
    """Stops the flow until an operator acts (interrupt); on resume, takes the action as the new contribution."""
    escalation = state.escalation
    value = interrupt(
        {
            "case_id": escalation.case_id if escalation else None,
            "protocol": escalation.protocol if escalation else None,
            "summary": escalation.summary if escalation else None,
            "pending_question": escalation.pending_question if escalation else None,
            "draft_reply": escalation.draft_reply if escalation else None,
        }
    )
    ctx: RunContext = config["configurable"]["ctx"]
    ctx.trace.event("human_review", action=value.get("action"), operator_id=value.get("operator_id"))
    return {
        "operator": dict(value),
        "status": "answered",
        "case": {**state.case, "state": state.case_next.get("state", "handoff")},
        "support": None,
        "policy": None,
        "draft_answer": None,
        "answer": None,
        "agents": ["human_review"],
        "errors": [],
        "output_violations": [],
    }


def _after_review(s: GraphState) -> str:
    return "support" if (s.operator or {}).get("action") == "reject" else "personality"


def build_review_graph(checkpointer):
    g = StateGraph(GraphState)
    g.add_node("human_review", human_review)  # not wrapped: interrupt() must reach LangGraph
    for name, fn in [
        ("support", support.run),
        ("personality", personality.run),
        ("output_guard", personality.run_output_guard),
    ]:
        g.add_node(name, _traced(name, fn))
    g.add_edge(START, "human_review")
    g.add_conditional_edges("human_review", _after_review, ["support", "personality"])
    g.add_edge("support", "personality")  # never back to escalation in the same cycle (D14)
    g.add_edge("personality", "output_guard")
    g.add_edge("output_guard", END)
    return g.compile(checkpointer=checkpointer)


def _sources(state: GraphState, ctx: RunContext) -> list[Source]:
    out: list[Source] = []
    if state.knowledge:
        kind_map = {"public_official": "official", "simulated_internal": "demo_procedure", "web": "web"}
        out += [Source(type=kind_map[c.source_kind], title=c.title, url=c.url) for c in state.knowledge.citations]
    seen = set()
    for o in ctx.outcomes:
        if o.ok and o.name in TOOL_TITLES and o.name not in seen:
            seen.add(o.name)
            out.append(Source(type="tool", title=TOOL_TITLES[o.name], observed_at=(o.data or {}).get("observed_at")))
    return out


class Orchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        llm: LLM,
        index: KnowledgeIndex | None,
        clock: Clock,
        budget: BudgetGuard | CombinedBudgetGuard,
        traces: TraceStore,
        faults: dict[str, str] | None = None,
        mock_services: object | None = None,
        llm_factory: Callable[[str, str], LLM] | None = None,
        knowledge_base=None,
    ) -> None:
        self.settings, self.llm, self.index, self.clock = settings, llm, index, clock
        self.knowledge_base = knowledge_base
        self.budget, self.traces, self.faults = budget, traces, faults or {}
        self.mock_services = mock_services
        self.llm_factory = llm_factory
        self.graph = build_graph()
        self._review_graph = None  # opened on the first handoff: turns without one never touch checkpoints
        self._checkpoint_conn: sqlite3.Connection | None = None
        self._review_lock = threading.Lock()

    def review_graph(self):
        with self._review_lock:
            if self._review_graph is None:
                path = self.settings.checkpoint_db_path
                path.parent.mkdir(parents=True, exist_ok=True)
                self._checkpoint_conn = sqlite3.connect(str(path), check_same_thread=False)
                serde = JsonPlusSerializer(allowed_msgpack_modules=CHECKPOINT_TYPES)
                self._review_graph = build_review_graph(SqliteSaver(self._checkpoint_conn, serde=serde))
            return self._review_graph

    def _suspend(self, final: GraphState, ctx: RunContext, thread_id: str | None = None) -> None:
        """Saves the handed-off flow at `human_review` (interrupt) under thread = request id (D6). `thread_id` is the
        case's own thread when a later turn completes a flow that the escalating request did not get to save."""
        thread_id = thread_id or final.request_id
        step, t0 = ctx.trace.start("human_review")
        try:
            self.review_graph().invoke(final, config={"configurable": {"thread_id": thread_id, "ctx": ctx}})
            ctx.trace.finish(step, t0, "interrupted", thread_id=thread_id)
        except Exception as exc:  # the reply to the merchant never fails because of the checkpoint
            log.exception("suspend failed", extra={"event": {"request_id": final.request_id}})
            ctx.trace.finish(step, t0, "error", error=f"{type(exc).__name__}: {exc}")
            self._mark_checkpoint_failed(final, exc)

    def _mark_checkpoint_failed(self, final: GraphState, exc: Exception) -> None:
        """D28: the case shows from the start that its flow was not saved (an action gets `503 checkpoint_missing`)."""
        try:
            conn = connect(self.settings.db_path)
            try:
                conn.execute(
                    "UPDATE handoff_cases SET resume_status='checkpoint_failed', resume_error=? WHERE case_id=?",
                    (f"checkpoint_failed:{type(exc).__name__}", final.escalation.case_id),
                )
            finally:
                conn.close()
        except Exception:
            log.exception("checkpoint failure not recorded", extra={"event": {"request_id": final.request_id}})

    def handle(
        self,
        request: MessageRequest,
        request_id: str,
        *,
        agent_models: dict[str, dict] | None = None,
        router_llm: LLM | None = None,
        router_decision: RouterDecision | None = None,
        db_path=None,
        knowledge: tuple[KnowledgeIndex | None, str | None] | None = None,
        trace_tags: dict | None = None,
        principal: Principal | None = None,
        channel: str = "in_process",
    ) -> MessageResponse:
        """`db_path` isolates domain effects (a comparison uses a temporary copy of the synthetic database),
        `knowledge` pins an already captured knowledge-base version and `trace_tags` mark the trace.
        `principal` is the authenticated caller (HTTP routes always pass it); in-process callers (CLI `ask`, offline
        evaluation) run as the merchant of `request.user_id`."""
        if request.user_id is None:
            raise ValueError("the merchant of the request must be set by the server")
        principal = principal or Principal.merchant(request.user_id)
        if knowledge is not None:
            captured_index, knowledge_version_id = knowledge
        else:
            captured_index, knowledge_version_id = (
                self.knowledge_base.capture_active() if self.knowledge_base else (self.index, None)
            )
        conn = connect(db_path or self.settings.db_path)
        try:
            store = ConversationStore(conn, self.clock)
            conv = store.open(request.conversation_id, request.user_id)  # raises ConversationNotFound
            pending = None if conv.created else store.pending_operator_turn(conv.conversation_id)
            if pending is not None:  # D8: a human reply waiting for this conversation is delivered first
                return self._deliver(store, conv, pending, request, request_id, principal, trace_tags)
            history = [] if conv.created else store.history(conv.conversation_id)
            known = conn.execute("SELECT 1 FROM customers WHERE customer_id = ?", (request.user_id,)).fetchone()
            env = ToolEnv(
                conn,
                self.clock,
                CustomerContext.for_principal(principal, request.user_id, known is not None),
                dict(self.faults),
                self.mock_services,
            )
            ctx = RunContext(
                request_id=request_id,
                settings=self.settings,
                llm=self.llm,
                index=captured_index,
                budget=self.budget,
                trace=TraceRecorder(request_id),
                tools=env,
                clock=self.clock,
                knowledge_version_id=knowledge_version_id,
                agent_llms={
                    name: (
                        router_llm if name == "router" and router_llm is not None else self._profile_llm(name, config)
                    )
                    for name, config in (agent_models or {}).items()
                },
                router_override=router_decision,
                channel=channel,
            )
            initial = GraphState(
                request_id=request_id,
                conversation_id=conv.conversation_id,
                user_id=request.user_id,
                customer_known=known is not None,
                message=request.message,
                history=history,
                case=conv.case_view(),
                prefix_cache={"topic": conv.prefix_topic, "at": conv.prefix_at, "data": conv.prefix}
                if conv.prefix
                else None,
            )
            final = GraphState.model_validate(
                self.graph.invoke(initial, config={"configurable": {"ctx": ctx}, "recursion_limit": 30})
            )
            announce = False  # does this turn queue `handoff.created` together with its messages?
            if final.escalation and db_path is None:  # isolated comparison runs never leave a case to resume
                if final.escalation.created:
                    self._suspend(final, ctx)
                    announce = channel in ("api", "web")
                else:
                    announce = self._complete_interrupted_handoff(conn, final, ctx, channel)
            if announce:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    self._persist(store, conv, final)
                    case = conn.execute("SELECT * FROM handoff_cases WHERE case_id=?", (final.escalation.case_id,))\
                        .fetchone()
                    payload = json.loads(case["payload"] or "{}")
                    enqueue(conn, "handoff.created", {
                        "case_id": case["case_id"], "protocol": case["protocol"],
                        "conversation_id": case["conversation_id"], "customer_id": case["customer_id"],
                        "language": payload.get("language"), "reason": case["reason"],
                        "summary": payload.get("summary"), "pending_question": payload.get("pending_question"),
                        "draft_reply": payload.get("draft_reply"), "transcript": transcript(conn, conv.conversation_id),
                    }, case["case_id"], webhook_targets(self.settings))
                    conn.execute("COMMIT")
                except BaseException:
                    conn.execute("ROLLBACK")
                    raise
            else:
                self._persist(store, conv, final)
            response = self._response(final, ctx)
            self._record(final, ctx, response, trace_tags)
            return response
        finally:
            conn.close()

    def _complete_interrupted_handoff(self, conn, final: GraphState, ctx: RunContext, channel: str) -> bool:
        """The case found by this turn (`created=False`) may have been opened by a turn that stopped between writing the
        case and finishing: the flow is not saved, or `handoff.created` was never queued. Saves the flow under the
        case's own thread when it is missing (or marks the failure, D28) and says whether the intention is still to be
        queued with this turn's messages. A case already ticketed, worked on or from before v0.7.0 is left alone."""
        case = conn.execute("SELECT * FROM handoff_cases WHERE case_id=?", (final.escalation.case_id,)).fetchone()
        if case is None or not case["thread_id"] or case["queue_state"] != "open" or case["ticket_id"]:
            return False
        if case["resume_status"] is None and not self._has_checkpoint(case["thread_id"]):
            self._suspend(final, ctx, thread_id=case["thread_id"])
        if channel not in ("api", "web"):
            return False
        queued = {
            row[0]
            for row in conn.execute(
                "SELECT target FROM webhook_outbox WHERE event='handoff.created' AND case_id=?", (case["case_id"],)
            )
        }
        return bool((webhook_targets(self.settings) & set(TARGETS["handoff.created"])) - queued)

    def _has_checkpoint(self, thread_id: str) -> bool:
        try:
            return bool(self.review_graph().get_state({"configurable": {"thread_id": thread_id}}).values)
        except Exception:  # unknown is not missing: only a checkpoint known to be absent is rebuilt
            log.exception("checkpoint lookup failed", extra={"event": {"thread_id": thread_id}})
            return True

    def _deliver(self, store, conv, pending: dict, request, request_id: str, principal, trace_tags) -> MessageResponse:
        """D8: records the merchant's message and returns the operator's reply (route human_reply), no model call."""
        meta = pending["meta"]
        language = meta.get("language") or guess_language(request.message)
        store.append(
            conv.conversation_id, request_id, "merchant", check_input(request.message).masked, "human_reply", None
        )
        store.mark_delivered(pending["id"])
        recorder = TraceRecorder(request_id)
        recorder.event("human_reply", protocol=meta.get("protocol"), action=meta.get("action"))
        response = MessageResponse(
            answer=pending["text"],
            status="answered",
            route="human_reply",
            via="operator",
            agents=["operator"],
            language=language,
            request_id=request_id,
            conversation_id=conv.conversation_id,
            resolution=Resolution(state=conv.state, evidence=conv.resolution_evidence),
        )
        summary = {
            "user_id": request.user_id,
            "route": "human_reply",
            "status": "answered",
            "language": language,
            "errors": [],
            "model_calls": 0,
            "tool_calls": 0,
            "cost_usd": 0.0,
            "detail": {
                "agents": ["operator"],
                "conversation_id": conv.conversation_id,
                "principal_id": principal.principal_id,
                "protocol": meta.get("protocol"),
                **(trace_tags or {}),
            },
        }
        try:
            self.traces.save(recorder, summary)
        except Exception:  # traces must never break a reply
            log.exception("trace save failed")
        return response

    def resume_handoff(self, case: dict, record: dict) -> dict:
        """Single resume point for an operator's action (called by `handoffs.act` after its commit): resumes the
        interrupted thread, writes the reply as an operator turn and moves the case (D14). Retrying after a failure is
        safe: an interrupted thread is resumed, a half-run one continues, and a turn is written only once."""
        thread_id = case.get("thread_id")
        if not thread_id:
            raise ResumeError("not_resumable", "This case has no saved flow to resume.")
        payload = json.loads(case.get("payload") or "{}")
        action = record["action"]
        text = payload.get("draft_reply") if action == "approve" else record.get("text")
        request_id = f"req_resume_{uuid.uuid4().hex[:16]}"
        conn = connect(self.settings.db_path)
        try:
            store = ConversationStore(conn, self.clock)
            conv = store.open(case["conversation_id"], case["customer_id"])
            known = conn.execute("SELECT 1 FROM customers WHERE customer_id = ?", (case["customer_id"],)).fetchone()
            operator = Principal.operator(record["operator_id"])
            env = ToolEnv(  # D4: the operator's principal acting for the merchant of the case, read from the case
                conn,
                self.clock,
                CustomerContext.for_principal(
                    operator, case["customer_id"], known is not None, authorized_customer_id=case["customer_id"]
                ),
                dict(self.faults),
                self.mock_services,
            )
            captured_index, knowledge_version_id = (
                self.knowledge_base.capture_active() if self.knowledge_base else (self.index, None)
            )
            ctx = RunContext(
                request_id=request_id,
                settings=self.settings,
                llm=self.llm,
                index=captured_index,
                budget=self.budget,
                trace=TraceRecorder(request_id),
                tools=env,
                clock=self.clock,
                knowledge_version_id=knowledge_version_id,
                channel=case.get("channel") or "in_process",
            )
            graph = self.review_graph()
            config = {"configurable": {"thread_id": thread_id, "ctx": ctx}, "recursion_limit": 30}
            snapshot = graph.get_state(config)
            if not snapshot.values:
                raise ResumeError("checkpoint_missing", "The saved flow of this case was not found.")
            value = {"action": action, "text": text, "operator_id": record["operator_id"], "case_id": case["case_id"]}
            if any(task.interrupts for task in snapshot.tasks):
                out = graph.invoke(Command(resume=value), config=config)
            elif snapshot.next:  # a previous attempt stopped half-way: continue from the last checkpoint
                out = graph.invoke(None, config=config)
            else:
                out = snapshot.values
            final = GraphState.model_validate(out)
            if not final.answer or not final.operator:
                raise ResumeError("resume_incomplete", "The resumed flow ended without a reply.")
            already = conn.execute(
                "SELECT 1 FROM messages WHERE conversation_id=? AND via='operator' AND meta LIKE ?",
                (conv.conversation_id, f'%"event_id": "{record["event_id"]}"%'),
            ).fetchone()
            case_state = final.case_next.get("state", "awaiting_customer")
            if already is None:
                meta = {
                    "action": action,
                    "protocol": case["protocol"],
                    "case_id": case["case_id"],
                    "event_id": record["event_id"],
                    "language": final.decision.language if final.decision else None,
                }
                conn.execute("BEGIN IMMEDIATE")
                try:
                    store.save(
                        conv, state=case_state, topic=conv.topic, technical_cycles=conv.technical_cycles,
                        evidence=final.case_next.get("evidence"),
                    )
                    store.append(
                        conv.conversation_id, request_id, "assistant", final.answer, "human_reply", "answered",
                        via="operator", meta=meta,
                    )
                    enqueue(conn, "conversation.replied", {
                        "case_id": case["case_id"], "protocol": case["protocol"],
                        "conversation_id": case["conversation_id"], "action": action,
                        "operator_id": record["operator_id"], "reply_text": final.answer, "via": "operator",
                        "request_id": request_id,
                        "delivered_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    }, record["event_id"], webhook_targets(self.settings))
                    conn.execute("COMMIT")
                except BaseException:
                    conn.execute("ROLLBACK")
                    raise
            response = MessageResponse(
                answer=final.answer,
                status="answered",
                route="human_reply",
                via="operator",
                agents=final.agents,
                language=final.decision.language if final.decision else "pt",
                sources=_sources(final, ctx),
                request_id=request_id,
                conversation_id=conv.conversation_id,
                resolution=Resolution(state=case_state, evidence=final.case_next.get("evidence")),
            )
            tags = {"purpose": "operator_resume", "resumes": thread_id, "case_id": case["case_id"], "action": action}
            self._record(final.model_copy(update={"request_id": request_id}), ctx, response, tags)
            return {"request_id": request_id, "case_state": case_state, "answer": final.answer}
        finally:
            conn.close()

    def _profile_llm(self, agent: str, config: dict) -> LLM:
        if self.llm_factory is None:
            # Scripted tests remain deterministic for every catalogued profile.
            if (config.get("provider") == "openai" and config.get("model") == self.llm.model) or type(
                self.llm
            ).__name__ == "ScriptedLLM":
                llm = self.llm
            else:
                raise RuntimeError(f"provider {config.get('provider')} is not configured")
        else:
            provider, model = config["provider"], config["model"]
            if provider == "typesafe" and agent != "router":
                raise RuntimeError("TypeSafe is supported only for the router agent")
            llm = self.llm_factory(provider, model)
        parameters = config.get("parameters") or {}
        if parameters:
            if set(parameters) != {"max_output_tokens"} or config.get("provider") not in {"openai", "deepseek"}:
                raise RuntimeError(f"unsupported parameters for {config.get('provider')}:{config.get('model')}")
            llm = OutputTokenLimitLLM(llm, parameters["max_output_tokens"])
        return llm

    def _persist(self, store: ConversationStore, conv: Conversation, state: GraphState) -> None:
        """Stores the turn: feedback on earlier attempts, new attempts, case state, cached prefix and messages."""
        signal = state.decision.case_signal if state.decision else "none"
        if signal == "still_failing":
            store.record_feedback(conv.conversation_id, "failed", "customer_reported")
        elif signal == "resolved":
            store.record_feedback(conv.conversation_id, "worked", "customer_confirmed")
        steps = state.support.steps_given if state.support else []
        cycles = conv.technical_cycles + (1 if steps else 0)
        if steps:
            store.add_attempts(conv.conversation_id, cycles, steps)
        topic = (state.decision.topic if state.decision else None) or conv.topic
        fresh_prefix = state.prefix if state.prefix.get("customer_known") and not state.prefix.get("reused") else None
        store.save(
            conv,
            state=state.case_next.get("state", conv.state),
            topic=topic,
            technical_cycles=cycles,
            evidence=state.case_next.get("evidence"),
            prefix=fresh_prefix,
            prefix_topic=state.prefix.get("topic") if fresh_prefix else None,
        )
        route = state.decision.route if state.decision else None
        store.append(conv.conversation_id, state.request_id, "merchant", state.message, route, None)
        store.append(conv.conversation_id, state.request_id, "assistant", state.answer or "", route, state.status)

    def _response(self, state: GraphState, ctx: RunContext) -> MessageResponse:
        language = state.decision.language if state.decision else guess_language(state.message)
        status = state.status or "answered"
        handoff = None
        if state.escalation:
            handoff = Handoff(protocol=state.escalation.protocol, reason=state.escalation.reason)
        case_state = state.case_next.get("state") or ("handoff" if status == "handoff" else "awaiting_customer")
        return MessageResponse(
            answer=state.answer or policy("unavailable", language),
            status=status,
            route=state.decision.route if state.decision else "clarify",
            agents=state.agents,
            language=language,
            sources=_sources(state, ctx),
            request_id=state.request_id,
            conversation_id=state.conversation_id,
            resolution=Resolution(state=case_state, evidence=state.case_next.get("evidence")),
            handoff=handoff,
        )

    def conversation(self, conversation_id: str) -> dict | None:
        conn = connect(self.settings.db_path)
        try:
            return ConversationStore(conn, self.clock).get(conversation_id)
        finally:
            conn.close()

    def _record(self, state: GraphState, ctx: RunContext, response: MessageResponse, tags: dict | None = None) -> None:
        summary = {
            "user_id": state.user_id,
            "route": response.route,
            "status": response.status,
            "language": response.language,
            "errors": state.errors,
            **ctx.summary(),
            "detail": {
                "agents": state.agents,
                "guard_findings": state.guard_findings,
                "output_violations": state.output_violations,
                "tools": [o.name for o in ctx.outcomes],
                "conversation_id": state.conversation_id,
                "principal_id": ctx.tools.customer.principal_id,
                "models_by_agent": ctx.summary()["usage_by_agent"],
                "effective_parameters_by_agent": ctx.summary()["effective_parameters_by_agent"],
                "cost_estimate_usd": ctx.summary()["cost_estimate_usd"],
                "cost_estimate_basis": ctx.summary()["cost_estimate_basis"],
                "cost_is_estimate": True,
                "knowledge_base_version_id": ctx.knowledge_version_id,
                "knowledge_base_collection": ctx.index.collection if ctx.index else None,
                "citations": [c.chunk_id for c in state.knowledge.citations] if state.knowledge else [],
                **(tags or {}),
            },
        }
        try:
            self.traces.save(ctx.trace, summary)
        except Exception:  # traces must never break a reply
            log.exception("trace save failed")
        log.info(
            "request",
            extra={
                "event": {
                    "request_id": state.request_id,
                    "duration_ms": ctx.trace.elapsed_ms,
                    **{k: v for k, v in summary.items() if k != "detail"},
                }
            },
        )

    def readiness(self) -> dict:
        index_chunks = 0
        db_ok = self.settings.db_path.exists()
        active_version = None
        try:
            # Observe the index of the version that is active now, not the one the runtime started with.
            if self.knowledge_base and db_ok:
                active, version_id = self.knowledge_base.capture_active()
                active_version = {"version_id": version_id, "collection": active.collection if active else None}
            else:
                active = self.index
            index_chunks = active.count() if active else 0
        except Exception as exc:  # pragma: no cover - reported, not raised
            log.warning("index readiness failed: %s", exc)
        return {
            "knowledge_base": active_version,  # the active version and its collection (versions.index is the boot one)
            "ready": bool(index_chunks and db_ok),
            "index_chunks": index_chunks,
            "database": db_ok,
            "model": self.llm.model,
            "budget_remaining_usd": round(self.budget.remaining(), 4),
            "pending_handoffs": self._pending_handoffs(db_ok),
            "checkpoints": self._checkpoint_threads(),
            "versions": self.versions(),
        }

    def _pending_handoffs(self, db_ok: bool) -> int | None:
        if not db_ok:
            return None
        conn = connect(self.settings.db_path)
        try:
            row = conn.execute("SELECT COUNT(*) FROM handoff_cases WHERE queue_state IN ('open','claimed')").fetchone()
            return int(row[0])
        finally:
            conn.close()

    def _checkpoint_threads(self) -> dict:
        """Saved flows waiting for or after an operator (read only here and on resume, never per message)."""
        path = self.settings.checkpoint_db_path
        if not path.exists():
            return {"store": "sqlite", "threads": 0}
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints").fetchone()
            return {"store": "sqlite", "threads": int(row[0])}
        except sqlite3.Error:
            return {"store": "sqlite", "threads": None}
        finally:
            conn.close()

    def versions(self) -> dict:
        """Package, schema, index and prompt versions in use (decision 0006)."""
        from merchant_assistant import __version__
        from merchant_assistant.data.migrations import current_version
        from merchant_assistant.llm.prompts import prompt_versions

        schema = None
        if self.settings.db_path.exists():
            conn = connect(self.settings.db_path)
            try:
                schema = current_version(conn)
            finally:
                conn.close()
        index = None
        manifest_path = self.settings.runtime_path / "index_manifest.json"
        if manifest_path.exists():
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            index = {
                "collection": m.get("collection"),
                "embedding_model": m.get("embedding_model"),
                "corpus": (m.get("corpus_hash") or "")[:12],
                "chunks": m.get("chunks"),
                "built_at": m.get("built_at"),
            }
        return {
            "app": __version__,
            "schema": schema,
            "index": index,
            "prompts": prompt_versions(self.settings.prompts_dir),
        }

    def trace(self, request_id: str) -> dict | None:
        return self.traces.get(request_id)

    def close(self) -> None:
        if self._checkpoint_conn is not None:
            self._checkpoint_conn.close()
        if self.index is not None:
            self.index.client.close()
        if self.mock_services is not None and hasattr(self.mock_services, "close"):
            self.mock_services.close()
