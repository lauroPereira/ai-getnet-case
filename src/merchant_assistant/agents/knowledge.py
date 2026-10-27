"""Knowledge Agent: RAG over official content (and demo procedures) plus web search for general questions."""

from __future__ import annotations

from pydantic import ValidationError

from merchant_assistant.agents.common import LANGUAGE_NAME, policy, prompt
from merchant_assistant.data.clock import today
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded, RunContext
from merchant_assistant.orchestration.state import Citation, GraphState, KnowledgeDraft, KnowledgeResult
from merchant_assistant.rag.index import Hit

RECOVERABLE = (LLMError, ValidationError, LimitExceeded, BudgetExceeded)


def _mode(route: str) -> str:
    return {"general_web": "web", "knowledge_and_support": "procedure"}.get(route, "rag")


def _passages(hits: list[Hit]) -> str:
    blocks = []
    for i, h in enumerate(hits, start=1):
        p = h.payload
        kind = "official page" if p.get("source_kind") == "public_official" else "demo procedure"
        origin = p.get("url") or p.get("procedure_id") or p.get("doc_id")
        collected = (p.get("collected_at") or "")[:10]
        header = f"[{i}] ({kind}) {p.get('title')} | {origin}" + (f" | collected {collected}" if collected else "")
        blocks.append(f"{header}\n{p.get('text')}")
    return "\n\n".join(blocks)


def _citations(hits: list[Hit], used: list[int]) -> list[Citation]:
    out, seen = [], set()
    for n in used:
        if not 1 <= n <= len(hits):
            continue
        p = hits[n - 1].payload
        key = p.get("url") or p.get("doc_id")
        if key in seen:
            continue
        seen.add(key)
        out.append(
            Citation(
                title=p.get("title") or key, url=p.get("url"), source_kind=p["source_kind"], chunk_id=p.get("chunk_id")
            )
        )
    return out


def _web(state: GraphState, ctx: RunContext, language: str) -> KnowledgeResult:
    p = prompt(ctx, "knowledge_web")
    ctx.step_notes["prompt"] = p.ref
    spec = CallSpec(
        agent="knowledge",
        instructions=p.render(
            language_name=LANGUAGE_NAME[language], today=today(ctx.clock).isoformat(), timezone=ctx.settings.timezone
        ),
        input=state.message,  # masked message only: no user id or account data goes to the web search
        effort="low",
        max_output_tokens=500,
        context={"mode": "web", "message": state.message},
    )
    try:
        answer = ctx.llm_for("knowledge").web_search(spec, ctx, max_calls=ctx.settings.web_search_max_calls).value
    except RECOVERABLE as exc:
        ctx.step_notes["error"] = str(exc)
        return KnowledgeResult(mode="web", points=[], evidence_sufficient=False, missing=["web_search_unavailable"])
    citations = [
        Citation(title=c.get("title") or c.get("url") or "web", url=c.get("url"), source_kind="web")
        for c in answer.citations
    ]
    return KnowledgeResult(
        mode="web", points=[answer.text], citations=citations, evidence_sufficient=True, evidence_texts=[answer.text]
    )


def run(state: GraphState, ctx: RunContext) -> dict:
    decision = state.decision
    language = decision.language if decision else "en"
    mode = _mode(decision.route if decision else "knowledge")
    agents = [*state.agents, "knowledge"]
    ctx.step_notes["mode"] = mode
    if mode == "web":
        return {"knowledge": _web(state, ctx, language), "agents": agents}

    kinds = ["public_official"] if mode == "rag" else ["public_official", "simulated_internal"]
    try:
        if ctx.index is None:
            raise LLMError("knowledge index not available")
        hits = ctx.index.search(
            state.message,
            k=ctx.settings.retrieval_top_k,
            source_kinds=kinds,
            min_score=ctx.settings.retrieval_min_score,
        )
    except Exception as exc:  # vector store or embedding failure
        ctx.step_notes["error"] = f"retrieval: {exc}"
        result = KnowledgeResult(mode=mode, points=[], evidence_sufficient=False, missing=["knowledge_unavailable"])
        return {"knowledge": result, "agents": agents, "errors": [*state.errors, f"knowledge: {exc}"]}
    ctx.step_notes["hits"] = [{"doc": h.payload.get("doc_id"), "score": round(h.score, 3)} for h in hits]
    if not hits:
        result = KnowledgeResult(
            mode=mode, points=[], evidence_sufficient=False, missing=[policy("no_evidence", language)]
        )
        return {"knowledge": result, "agents": agents}

    p = prompt(ctx, "knowledge_rag" if mode == "rag" else "knowledge_procedure")
    ctx.step_notes["prompt"] = p.ref
    spec = CallSpec(
        agent="knowledge",
        instructions=p.render(language_name=LANGUAGE_NAME[language], passages=_passages(hits)),
        input=f"Merchant question:\n<<<\n{state.message}\n>>>",
        effort="low",
        max_output_tokens=900,
        context={
            "mode": mode,
            "message": state.message,
            "passages": [{"n": i + 1, **h.payload} for i, h in enumerate(hits)],
        },
    )
    try:
        draft = ctx.llm_for("knowledge").parse(spec, KnowledgeDraft, ctx).value
    except RECOVERABLE as exc:
        ctx.step_notes["error"] = str(exc)
        result = KnowledgeResult(mode=mode, points=[], evidence_sufficient=False, missing=["knowledge_unavailable"])
        return {"knowledge": result, "agents": agents, "errors": [*state.errors, f"knowledge: {exc}"]}
    citations = _citations(hits, draft.used_passages)
    used_hits = [hits[n - 1] for n in draft.used_passages if 1 <= n <= len(hits)] or hits
    procedure_id = next((h.payload.get("procedure_id") for h in used_hits if h.payload.get("procedure_id")), None)
    result = KnowledgeResult(
        mode=mode,
        points=draft.points,
        citations=citations,
        evidence_sufficient=draft.evidence_sufficient and bool(citations),
        missing=draft.missing,
        procedure_id=procedure_id,
        evidence_texts=[h.payload.get("text", "") for h in hits],
    )
    return {"knowledge": result, "agents": agents}
