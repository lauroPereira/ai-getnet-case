"""Task 90 (spec v0.11.0 D7, CA-63): the reranker's control `hybrid@36` and the floor for hits only BM25 found.

Hashing embeddings and the in-memory Qdrant over the versioned corpus; questions from the development set and the
synthetic scenarios, never the retrieval holdout. No model call (the reranker here is programmed)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from merchant_assistant.config import PROJECT_ROOT, Settings
from merchant_assistant.evaluation.retrieval import load_cases
from merchant_assistant.llm.base import NullMeter
from merchant_assistant.llm.prompts import load_prompt
from merchant_assistant.llm.scripted import ScriptedLLM
from merchant_assistant.rag.chunk import chunk_document
from merchant_assistant.rag.documents import load_all
from merchant_assistant.rag.embed import HashEmbedder
from merchant_assistant.rag.index import (
    CONTROL_MODE,
    CONTROL_WIDTH,
    RETRIEVAL_MODES,
    SEARCH_MODES,
    Hit,
    KnowledgeIndex,
    bm25_floor,
    open_qdrant,
    rrf,
)
from merchant_assistant.rag.rerank import RERANK_CANDIDATES, Reranker

QUESTIONS = [c.question for c in load_cases(PROJECT_ROOT / "tests" / "scenarios" / "retrieval.jsonl")] + [
    "Apareceu ADQ 4-91 na maquininha, o que faço?",
    "Como cancelar uma venda no débito?",
    "How much is the monthly rent of the Get Mini?",
    "Quanto custa a Get Clássica por mês?",
]
FLOOR = 0.5


def corpus():
    return [c for d in load_all(PROJECT_ROOT / "data") for c in chunk_document(d)]


@pytest.fixture(scope="module")
def index():
    idx = KnowledgeIndex(open_qdrant(":memory:", PROJECT_ROOT), "t90", HashEmbedder())
    idx.rebuild(corpus())
    return idx


def shown(hits: list[Hit]) -> list[tuple]:
    return [(h.chunk_id, round(h.score, 9), h.origin) for h in hits]


# --- hybrid@36 -----------------------------------------------------------------------------------------------------


def test_the_control_is_a_search_mode_at_the_reranker_depth_not_a_service_mode():
    assert CONTROL_MODE == "hybrid@36" and CONTROL_WIDTH == RERANK_CANDIDATES and 3 * CONTROL_WIDTH == 36
    assert CONTROL_MODE in SEARCH_MODES and CONTROL_MODE not in RETRIEVAL_MODES
    with pytest.raises(ValueError):
        KnowledgeIndex(None, "x", HashEmbedder(), mode=CONTROL_MODE)


@pytest.mark.parametrize("k", [12, 36])
def test_hybrid_at_36_equals_hybrid_when_k_reaches_the_reranker_width(index, k):
    for question in QUESTIONS:
        assert shown(index.search(question, k=k, mode=CONTROL_MODE)) == shown(
            index.search(question, k=k, mode="hybrid")
        ), question


def test_hybrid_at_36_is_the_top_k_of_the_fusion_the_reranker_reads(index):
    """At k = 6 it is the first 6 of the fusion of width 12 (depth 36), what an order-keeping reranker returns, and
    the depth alone already differs from `hybrid` (depth 18) on some questions."""

    class Identity:
        candidates = RERANK_CANDIDATES

        def reorder(self, query, hits, meter, notes=None):
            return list(hits)

    differ = 0
    for question in QUESTIONS:
        control = index.search(question, k=6, mode=CONTROL_MODE, min_score=0.3)
        assert shown(control) == shown(index.search(question, k=12, mode="hybrid", min_score=0.3)[:6]), question
        kept = index.search(question, k=6, mode="hybrid", min_score=0.3, reranker=Identity(), meter=NullMeter())
        assert shown(control) == shown(kept), question
        differ += shown(control) != shown(index.search(question, k=6, mode="hybrid", min_score=0.3))
    assert differ >= 1


def test_hybrid_at_36_differs_from_the_programmed_reranker(index):
    from merchant_assistant.evaluation.scripted_policy import handler

    reranker = Reranker(ScriptedLLM(handler), load_prompt(PROJECT_ROOT / "prompts", "rerank"))
    differ = 0
    for question in QUESTIONS:
        notes: dict = {}
        reranked = index.search(question, k=6, mode="hybrid", reranker=reranker, meter=NullMeter(), notes=notes)
        assert notes["rerank"]["status"] == "ok", question
        differ += shown(reranked) != shown(index.search(question, k=6, mode=CONTROL_MODE))
    assert differ >= 1  # the control has no model: what the reranker changes shows up against it


def test_hybrid_at_36_takes_no_reranker(index):
    with pytest.raises(ValueError, match="without a model"):
        index.search(QUESTIONS[0], mode=CONTROL_MODE, reranker=object(), meter=NullMeter())


# --- the BM25 floor ------------------------------------------------------------------------------------------------


def hit(cid: str) -> Hit:
    return Hit(0.5, {"chunk_id": cid})


def bm(score: float, cid: str) -> tuple[float, dict]:
    return score, {"chunk_id": cid}


def test_floor_drops_only_bm25_only_hits_below_it_on_the_normalized_score():
    dense = [hit("a"), hit("b")]
    lexical = [bm(10.0, "a"), bm(8.0, "c"), bm(2.0, "d"), bm(1.0, "b"), bm(4.9, "e")]
    kept, dropped = bm25_floor(dense, lexical, FLOOR)
    # c: 0.8 kept; d: 0.2 dropped; b: 0.1 but the dense list found it, kept; e: 0.49 dropped
    assert [p["chunk_id"] for _, p in kept] == ["a", "c", "b"] and dropped == ["d", "e"]
    assert bm25_floor(dense, lexical, 0.0) == (lexical, [])
    assert bm25_floor(dense, [], FLOOR) == ([], [])
    assert bm25_floor([], [bm(0.0, "x")], FLOOR) == ([], ["x"])  # no positive BM25 score: nothing to normalize on
    assert bm25_floor([], [bm(3.0, "x")], 1.0) == ([bm(3.0, "x")], [])  # the best hit is 1, never below 1


def test_search_with_the_floor_drops_before_the_fusion_and_notes_what_it_dropped(index):
    dropped_any = 0
    for question in QUESTIONS:
        notes: dict = {}
        floored = index.search(question, k=6, mode="hybrid", bm25_min_score=FLOOR, notes=notes)
        dense = {h.chunk_id for h in index.search(question, k=18, mode="dense")}
        scores = {str(p["chunk_id"]): s for s, p in index.bm25_index().search(question, k=18)}
        best = max(scores.values(), default=0.0)
        dropped = notes["bm25_dropped"]
        assert not dense & set(dropped), question  # a hit the dense list found is never dropped
        assert all(scores[c] / best < FLOOR for c in dropped), question
        assert not {h.chunk_id for h in floored} & set(dropped), question
        expected_dropped = [c for c, s in scores.items() if c not in dense and s / best < FLOOR]
        assert dropped == expected_dropped, question
        dropped_any += bool(dropped)
    assert dropped_any >= 1  # not vacuous on this corpus


def test_the_floor_changes_what_the_fusion_reads(index):
    # review P2-2 (M06): the floored search is the fusion of the dense list with the floored BM25 list, not with the
    # whole one; computing the dropped ids while fusing the unfiltered list must fail here
    changed = 0
    for question in QUESTIONS:
        dense = index.search(question, k=18, mode="dense")
        lexical = index.bm25_index().search(question, k=18)
        floored = index.search(question, k=6, mode="hybrid", bm25_min_score=FLOOR)
        assert shown(floored) == shown(rrf(dense, bm25_floor(dense, lexical, FLOOR)[0], 6)), question
        changed += shown(floored) != shown(index.search(question, k=6, mode="hybrid", bm25_min_score=0.0))
    assert changed >= 1  # the floor moves the top 6 of at least one question

def test_floor_off_is_the_v090_search_and_writes_nothing(index):
    for question in QUESTIONS[:6]:
        notes: dict = {}
        assert shown(index.search(question, mode="hybrid", notes=notes)) == shown(index.search(question, mode="hybrid"))
        assert shown(index.search(question, mode="hybrid", bm25_min_score=0.0)) == shown(
            index.search(question, mode="hybrid")
        )
        assert "bm25_dropped" not in notes


def test_the_index_floor_is_the_default_and_reaches_the_control_and_the_reranker_fusion(index):
    floored = KnowledgeIndex(index.client, index.collection, index.embedder, mode="hybrid", bm25_min_score=FLOOR)
    def dropped(question: str) -> list[str]:
        notes: dict = {}
        index.search(question, mode="hybrid", bm25_min_score=FLOOR, notes=notes)
        return notes["bm25_dropped"]

    question = next(q for q in QUESTIONS if dropped(q))
    by_arg: dict = {}
    by_index: dict = {}
    assert shown(floored.search(question, notes=by_index)) == shown(
        index.search(question, mode="hybrid", bm25_min_score=FLOOR, notes=by_arg)
    )
    assert by_index == by_arg and "bm25_dropped" in by_index
    control: dict = {}
    floored.search(question, mode=CONTROL_MODE, notes=control)
    assert "bm25_dropped" in control
    assert shown(floored.search(question, bm25_min_score=0.0)) == shown(index.search(question, mode="hybrid"))

    from merchant_assistant.evaluation.scripted_policy import handler

    noted: dict = {}
    reranker = Reranker(ScriptedLLM(handler), load_prompt(PROJECT_ROOT / "prompts", "rerank"))
    floored.search(question, reranker=reranker, meter=NullMeter(), notes=noted)
    assert noted["rerank"]["status"] == "ok" and "bm25_dropped" in noted


def test_floor_setting_is_off_by_default_and_a_fraction():
    assert Settings(_env_file=None).retrieval_bm25_min_score == 0.0
    assert Settings(_env_file=None, retrieval_bm25_min_score=0.25).retrieval_bm25_min_score == 0.25
    for wrong in (-0.1, 1.5, float("nan")):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, retrieval_bm25_min_score=wrong)
