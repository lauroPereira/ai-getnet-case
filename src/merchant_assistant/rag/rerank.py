"""Reranker (v0.9.0, task 81, D7): the agent model reorders the first 12 results of the hybrid fusion.

Prompt `rerank.v1`, structured output with the order of the candidate labels, a small output cap, metered like any
other model call. Any failure is written to the trace notes and never fails the search: the index then answers
exactly as with RERANK=off."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError

from merchant_assistant.llm.base import LLM, CallSpec, LLMError, Meter
from merchant_assistant.llm.prompts import Prompt
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded
from merchant_assistant.rag.index import Hit

RERANK_CANDIDATES = 12
RERANK_MAX_OUTPUT_TOKENS = 150  # 12 short labels in JSON need about 60
PASSAGE_CHARS = 700  # per candidate: bounds the input of one call
RECOVERABLE = (LLMError, ValidationError, LimitExceeded, BudgetExceeded)


class RerankOrder(BaseModel):
    order: list[str] = Field(description="Candidate labels such as P3, most relevant first.")


class RerankRefused(LLMError):
    """The model answered, but with an order that cannot be applied (unknown label or nothing listed)."""


def _label(n: int) -> str:
    return f"P{n}"


@dataclass
class Reranker:
    llm: LLM
    prompt: Prompt
    candidates: int = RERANK_CANDIDATES
    max_output_tokens: int = RERANK_MAX_OUTPUT_TOKENS

    def spec(self, query: str, hits: list[Hit]) -> CallSpec:
        blocks = []
        for i, h in enumerate(hits, start=1):
            title = h.payload.get("title") or h.payload.get("doc_id")
            blocks.append(f"[{_label(i)}] {title}\n{(h.payload.get('text') or '')[:PASSAGE_CHARS]}")
        return CallSpec(
            agent="rerank",
            instructions=self.prompt.render(),
            input=f"Merchant question:\n<<<\n{query}\n>>>\n\nCandidates:\n\n" + "\n\n".join(blocks),
            effort="none",
            max_output_tokens=self.max_output_tokens,
            context={
                "mode": "rerank",
                "query": query,
                "candidates": [
                    {"label": _label(i), "chunk_id": h.chunk_id, "text": h.payload.get("text") or ""}
                    for i, h in enumerate(hits, start=1)
                ],
            },
        )

    def rerank(self, query: str, hits: list[Hit], meter: Meter, notes: dict | None = None) -> list[Hit]:
        """`hits` reordered by the model; on failure the same list, and `notes["rerank"]` says why."""
        reordered = self.reorder(query, hits, meter, notes)
        return list(hits) if reordered is None else reordered

    def reorder(self, query: str, hits: list[Hit], meter: Meter, notes: dict | None = None) -> list[Hit] | None:
        """`hits` reordered by the model, or None when it failed or was skipped (`notes["rerank"]` says why). The
        index uses None to answer exactly as without the reranker (review P2-1 of task 81)."""
        note: dict = {"prompt": self.prompt.ref, "candidates": len(hits)}
        if notes is not None:
            notes["rerank"] = note
        if len(hits) < 2:
            note["status"] = "skipped"
            return None
        try:
            answer = self.llm.parse(self.spec(query, hits), RerankOrder, meter).value
            positions = self._positions(answer.order, len(hits))
        except RECOVERABLE as exc:
            note.update(status="failed", error=f"{type(exc).__name__}: {exc}"[:300])
            return None
        note.update(status="ok", order=[p + 1 for p in positions])  # fusion ranks in the new order
        return [hits[p] for p in positions]

    @staticmethod
    def _positions(order: list[str], n: int) -> list[int]:
        labels = {_label(i): i - 1 for i in range(1, n + 1)}
        unknown = [label for label in order if label.strip() not in labels]
        if unknown or not order:
            raise RerankRefused(f"unusable order: unknown {unknown[:3]}" if unknown else "empty order")
        listed: list[int] = []
        for label in order:
            if labels[label.strip()] not in listed:  # a repeated label counts once
                listed.append(labels[label.strip()])
        return listed + [p for p in range(n) if p not in listed]  # left out: fusion order, after the listed ones
