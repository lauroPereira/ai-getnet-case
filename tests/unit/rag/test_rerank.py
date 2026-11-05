"""Task 81 (v0.9.0, D7): reranker `rerank.v1` over the first 12 results of the hybrid fusion, programmed model only.

Success, failure (provider, unusable order, budget and request limits) and the output token limit. Development
tests: they never read the retrieval holdout."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.llm.base import LLMError, NullMeter
from merchant_assistant.llm.openai_llm import OpenAILLM
from merchant_assistant.llm.prompts import load_prompt
from merchant_assistant.llm.scripted import ScriptedLLM
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded
from merchant_assistant.rag.chunk import chunk_document
from merchant_assistant.rag.documents import load_all
from merchant_assistant.rag.embed import HashEmbedder
from merchant_assistant.rag.index import Hit, KnowledgeIndex, open_qdrant
from merchant_assistant.rag.rerank import (
    PASSAGE_CHARS,
    RERANK_CANDIDATES,
    RERANK_MAX_OUTPUT_TOKENS,
    Reranker,
)

PROMPT = load_prompt(PROJECT_ROOT / "prompts", "rerank")
QUESTION = "Apareceu ADQ 4-91 na maquininha, o que faço?"


def hits(n: int) -> list[Hit]:
    return [
        Hit(1 / (60 + i), {"chunk_id": f"doc{i}#0", "doc_id": f"doc{i}", "text": f"text {i} " * 200})
        for i in range(1, n + 1)
    ]


class RecordingMeter:
    def __init__(self, fail: Exception | None = None) -> None:
        self.reserved: list[dict] = []
        self.settled: list = []
        self.fail = fail

    def reserve(self, **kwargs):
        if self.fail is not None:
            raise self.fail
        self.reserved.append(kwargs)
        return len(self.reserved)

    def settle(self, reservation, usage) -> None:
        self.settled.append((reservation, usage))


def ordered(*labels: str):
    return lambda call: {"order": list(labels)}


def test_prompt_is_versioned():
    assert (PROMPT.id, PROMPT.version, PROMPT.ref) == ("rerank", "1", "rerank@1")
    assert (PROJECT_ROOT / "prompts" / "rerank.v1.md").is_file()


def test_success_reorders_metered_with_a_small_output_cap():
    llm, meter, notes = ScriptedLLM(ordered("P3", "P1", "P2")), RecordingMeter(), {}
    candidates = hits(3)
    result = Reranker(llm, PROMPT).rerank(QUESTION, candidates, meter, notes)
    assert [h.chunk_id for h in result] == ["doc3#0", "doc1#0", "doc2#0"]
    assert result[0] is candidates[2]  # same hits (fused score and origin kept), new order
    assert notes["rerank"] == {"prompt": "rerank@1", "candidates": 3, "status": "ok", "order": [3, 1, 2]}
    (call,) = llm.calls
    assert call.spec.agent == "rerank" and call.spec.effort == "none"
    assert call.spec.max_output_tokens == RERANK_MAX_OUTPUT_TOKENS <= 200
    assert meter.reserved[0]["agent"] == "rerank" and meter.reserved[0]["max_output_tokens"] == RERANK_MAX_OUTPUT_TOKENS
    assert len(meter.settled) == 1 and meter.settled[0][1] is not None  # usage settled through the Meter
    assert QUESTION in call.spec.input and "[P1]" in call.spec.input and "[P3]" in call.spec.input


def test_input_is_bounded_per_candidate():
    llm = ScriptedLLM(ordered("P1"))
    Reranker(llm, PROMPT).rerank(QUESTION, hits(RERANK_CANDIDATES), NullMeter())
    spec = llm.calls[0].spec
    assert spec.input.count("[P") == RERANK_CANDIDATES == 12
    assert all(len(block.split("\n", 1)[1]) <= PASSAGE_CHARS for block in spec.input.split("\n\n[")[1:])
    assert len(spec.input) < RERANK_CANDIDATES * (PASSAGE_CHARS + 80) + 500


def test_left_out_labels_keep_fusion_order_and_repeats_count_once():
    result = Reranker(ScriptedLLM(ordered("P4", "P2", "P4")), PROMPT).rerank(QUESTION, hits(5), NullMeter())
    assert [h.chunk_id for h in result] == ["doc4#0", "doc2#0", "doc1#0", "doc3#0", "doc5#0"]


@pytest.mark.parametrize(
    "answer",
    [
        LLMError("provider timeout"),
        {"order": ["P1", "P9"]},  # unknown label
        {"order": []},
        {"wrong": "shape"},  # structured output that does not validate
    ],
    ids=["provider", "unknown-label", "empty", "invalid"],
)
def test_failure_keeps_the_fusion_order_and_is_noted(answer):
    notes: dict = {}
    candidates = hits(4)
    result = Reranker(ScriptedLLM(lambda call: answer), PROMPT).rerank(QUESTION, candidates, NullMeter(), notes)
    assert result == candidates
    assert notes["rerank"]["status"] == "failed" and notes["rerank"]["error"]


@pytest.mark.parametrize(
    "exc", [BudgetExceeded("request", 0.01, 0.0), LimitExceeded("model_calls")], ids=["budget", "limit"]
)
def test_meter_refusal_keeps_the_fusion_order(exc):
    notes: dict = {}
    llm = ScriptedLLM(ordered("P2", "P1"))
    result = Reranker(llm, PROMPT).rerank(QUESTION, hits(2), RecordingMeter(fail=exc), notes)
    assert [h.chunk_id for h in result] == ["doc1#0", "doc2#0"]
    assert notes["rerank"]["status"] == "failed" and llm.calls == []


def test_fewer_than_two_candidates_make_no_call():
    llm, notes = ScriptedLLM(ordered("P1")), {}
    assert Reranker(llm, PROMPT).rerank(QUESTION, hits(1), NullMeter(), notes) == hits(1)
    assert notes["rerank"]["status"] == "skipped" and llm.calls == []


class TruncatingResponses:
    """OpenAI Responses stand-in: the answer stops at max_output_tokens, so nothing parses."""

    def __init__(self) -> None:
        self.kwargs: dict = {}

    def parse(self, **kwargs):
        self.kwargs = kwargs
        usage = SimpleNamespace(input_tokens=900, output_tokens=kwargs["max_output_tokens"], input_tokens_details=None)
        return SimpleNamespace(output_parsed=None, status="incomplete", usage=usage, output=[])


def test_output_token_limit_reached_keeps_the_fusion_order():
    responses = TruncatingResponses()
    llm = OpenAILLM(SimpleNamespace(responses=responses), "gpt-6-luna")
    meter, notes = RecordingMeter(), {}
    candidates = hits(3)
    assert Reranker(llm, PROMPT).rerank(QUESTION, candidates, meter, notes) == candidates
    assert responses.kwargs["max_output_tokens"] == RERANK_MAX_OUTPUT_TOKENS
    assert responses.kwargs["model"] == "gpt-6-luna"
    assert notes["rerank"]["status"] == "failed" and "incomplete" in notes["rerank"]["error"]
    assert meter.settled[0][1].output_tokens == RERANK_MAX_OUTPUT_TOKENS  # the truncated call is still paid for


# --- inside KnowledgeIndex.search: after the fusion, over its first 12 ------------------------------------------


@pytest.fixture(scope="module")
def index():
    idx = KnowledgeIndex(open_qdrant(":memory:", PROJECT_ROOT), "rerank_test", HashEmbedder())
    idx.rebuild([c for d in load_all(PROJECT_ROOT / "data") for c in chunk_document(d)])
    return idx


class Reverse:
    candidates = RERANK_CANDIDATES

    def __init__(self) -> None:
        self.seen: list[str] = []

    def rerank(self, query, hits, meter, notes=None):
        self.seen = [h.chunk_id for h in hits]
        return list(reversed(hits))


class Failing(Reverse):
    def rerank(self, query, hits, meter, notes=None):
        self.seen = [h.chunk_id for h in hits]
        return list(hits)


def test_search_reranks_the_first_12_of_the_fusion(index):
    fused12 = [h.chunk_id for h in index.search(QUESTION, k=12, mode="hybrid")]
    reverse = Reverse()
    result = index.search(QUESTION, k=6, mode="hybrid", reranker=reverse, meter=NullMeter())
    assert reverse.seen == fused12 and len(fused12) == 12
    assert [h.chunk_id for h in result] == list(reversed(fused12))[:6]


def test_search_with_a_reranker_that_keeps_the_order_returns_the_fusion_top_k(index):
    fused12 = [h.chunk_id for h in index.search(QUESTION, k=12, mode="hybrid")]
    result = index.search(QUESTION, k=6, mode="hybrid", reranker=Failing(), meter=NullMeter())
    assert [h.chunk_id for h in result] == fused12[:6]


def test_search_with_the_programmed_reranker_writes_the_trace_note(index):
    from merchant_assistant.evaluation.scripted_policy import handler

    notes: dict = {}
    result = index.search(
        QUESTION, mode="hybrid", reranker=Reranker(ScriptedLLM(handler), PROMPT), meter=NullMeter(), notes=notes
    )
    assert len(result) == 6 and notes["rerank"]["status"] == "ok" and notes["rerank"]["candidates"] == 12
    assert sorted(notes["rerank"]["order"]) == list(range(1, 13))


def test_reranker_requires_the_hybrid_mode(index):
    with pytest.raises(ValueError, match="hybrid"):
        index.search(QUESTION, mode="dense", reranker=Reverse(), meter=NullMeter())
