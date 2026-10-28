"""Agent orchestration: LangGraph state graph with typed state and direct calls between nodes.

input_guard -> router -> {knowledge | support_prefix -> [knowledge] -> support | escalation} -> personality
-> output_guard. Every node is traced; recoverable failures are handled inside the agents.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from merchant_assistant.agents import escalation, knowledge, personality, router, support
from merchant_assistant.agents.common import guess_language, policy
from merchant_assistant.api.schemas import Handoff, MessageRequest, MessageResponse, Resolution, Source
from merchant_assistant.config import Settings
from merchant_assistant.conversations import Conversation, ConversationStore
from merchant_assistant.data.clock import Clock
from merchant_assistant.data.db import connect
from merchant_assistant.guardrails.input import check_input
from merchant_assistant.llm.base import LLM, OutputTokenLimitLLM
from merchant_assistant.observability.traces import TraceRecorder, TraceStore
from merchant_assistant.orchestration.budget import BudgetGuard, CombinedBudgetGuard
from merchant_assistant.orchestration.run import RunContext
from merchant_assistant.orchestration.state import GraphState, RouterDecision
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
    ) -> MessageResponse:
        """`db_path` isolates domain effects (a comparison uses a temporary copy of the synthetic database),
        `knowledge` pins an already captured knowledge-base version and `trace_tags` mark the trace."""
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
            history = [] if conv.created else store.history(conv.conversation_id)
            known = conn.execute("SELECT 1 FROM customers WHERE customer_id = ?", (request.user_id,)).fetchone()
            env = ToolEnv(
                conn,
                self.clock,
                CustomerContext(request.user_id, known is not None),
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
            self._persist(store, conv, final)
            response = self._response(final, ctx)
            self._record(final, ctx, response, trace_tags)
            return response
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
            "versions": self.versions(),
        }

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
        if self.index is not None:
            self.index.client.close()
        if self.mock_services is not None and hasattr(self.mock_services, "close"):
            self.mock_services.close()
