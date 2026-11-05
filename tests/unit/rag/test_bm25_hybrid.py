"""Task 80 (v0.9.0, D7): BM25 + RRF hybrid retrieval, persisted by corpus hash; dense stays the default."""

import json
from types import SimpleNamespace

import pytest

from merchant_assistant import cli
from merchant_assistant.config import PROJECT_ROOT, Settings
from merchant_assistant.evaluation.retrieval import evaluate, load_cases
from merchant_assistant.rag import bm25
from merchant_assistant.rag.chunk import Chunk, chunk_document
from merchant_assistant.rag.documents import load_all
from merchant_assistant.rag.embed import HashEmbedder
from merchant_assistant.rag.index import RRF_K, Hit, KnowledgeIndex, open_qdrant, rrf

CASES = load_cases(PROJECT_ROOT / "tests" / "scenarios" / "retrieval.jsonl")
EXACT = [c for c in CASES if c.case == "EXACT-TERM"]


def corpus():
    return [c for d in load_all(Settings(_env_file=None).data_dir) for c in chunk_document(d)]


@pytest.fixture(scope="module")
def index():
    idx = KnowledgeIndex(open_qdrant(":memory:", PROJECT_ROOT), "t80", HashEmbedder())
    idx.rebuild(corpus())
    return idx


def chunk(cid: str, text: str, kind: str = "public_official") -> Chunk:
    return Chunk(cid, cid.split("#")[0], 0, text, cid, None, kind, {})


# --- tokenization -----------------------------------------------------------------------------------------------


def test_tokenize_folds_accents_drops_stopwords_and_keeps_codes():
    assert bm25.tokenize("Qual a taxa MDR da maquininha?") == ["taxa", "mdr", "maquininha"]
    assert bm25.tokenize("Erro E-1023 na antecipação") == ["erro", "e-1023", "antecipacao"]
    assert bm25.tokenize("ADQ 4-91; cartão pré-pago") == ["adq", "4-91", "cartao", "pre", "pago"]
    assert bm25.tokenize("What is the fee of the card?") == ["fee", "card"]


# --- dense equivalence ------------------------------------------------------------------------------------------


def reference_dense(idx: KnowledgeIndex, query: str, k: int, source_kinds=None, min_score: float = 0.0):
    """The v0.8.0 search, verbatim: one Qdrant query, Hit(score, payload)."""
    from qdrant_client import models

    vector = idx.embedder.embed([query])[0]
    query_filter = None
    if source_kinds:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="source_kind", match=models.MatchAny(any=source_kinds))]
        )
    result = idx.client.query_points(
        idx.collection, query=vector, limit=k, query_filter=query_filter, with_payload=True
    )
    return [Hit(p.score, dict(p.payload or {})) for p in result.points if p.score >= min_score]


@pytest.mark.parametrize(
    ("k", "kinds", "min_score"), [(6, None, 0.0), (3, ["public_official"], 0.05), (6, None, 0.3)]
)
def test_dense_default_and_explicit_dense_equal_the_previous_search(index, k, kinds, min_score):
    def same(actual: list[Hit], expected: list[Hit]) -> bool:
        # The in-memory Qdrant varies in the last float digits between identical queries: scores are compared
        # approximately, order, payloads and origin exactly.
        return [(h.payload, h.origin) for h in actual] == [(h.payload, h.origin) for h in expected] and [
            h.score for h in actual
        ] == pytest.approx([h.score for h in expected], rel=1e-6)

    for case in CASES:
        expected = reference_dense(index, case.question, k, kinds, min_score)
        assert same(index.search(case.question, k=k, source_kinds=kinds, min_score=min_score), expected)
        assert same(index.search(case.question, k=k, source_kinds=kinds, min_score=min_score, mode="dense"), expected)
        assert all(hit.origin == "dense" for hit in expected)


def test_mode_comes_from_the_index_and_unknown_modes_are_refused(index):
    hybrid = KnowledgeIndex(index.client, index.collection, index.embedder, mode="hybrid")
    question = EXACT[0].question
    assert hybrid.search(question) == index.search(question, mode="hybrid") != index.search(question)
    with pytest.raises(ValueError):
        index.search(question, mode="sparse")
    with pytest.raises(ValueError):
        KnowledgeIndex(index.client, index.collection, index.embedder, mode="sparse")


def test_retrieval_mode_setting_defaults_to_dense():
    assert Settings(_env_file=None).retrieval_mode == "dense"
    assert Settings(_env_file=None, retrieval_mode="hybrid").retrieval_mode == "hybrid"
    with pytest.raises(ValueError):
        Settings(_env_file=None, retrieval_mode="sparse")


# --- fusion -----------------------------------------------------------------------------------------------------


def hit(cid: str, score: float = 0.5) -> Hit:
    return Hit(score, {"chunk_id": cid})


def test_rrf_scores_origins_and_dense_tie_break():
    fused = rrf([hit("a"), hit("b")], [(9.0, {"chunk_id": "b"}), (5.0, {"chunk_id": "c"})], k=3)
    assert [(h.chunk_id, h.origin) for h in fused] == [("b", "both"), ("a", "dense"), ("c", "bm25")]
    assert fused[0].score == pytest.approx(1 / (RRF_K + 2) + 1 / (RRF_K + 1))
    assert fused[1].score == pytest.approx(1 / (RRF_K + 1))
    # Same fused score: the dense ranking decides.
    swapped = rrf([hit("a"), hit("b")], [(9.0, {"chunk_id": "b"}), (5.0, {"chunk_id": "a"})], k=2)
    assert [h.chunk_id for h in swapped] == ["a", "b"]
    alone = rrf([hit("a")], [(9.0, {"chunk_id": "z"})], k=2)
    assert [(h.chunk_id, h.origin) for h in alone] == [("a", "dense"), ("z", "bm25")]


def test_hybrid_keeps_the_source_filter_and_k(index):
    hits = index.search("Get Smart taxas", k=4, source_kinds=["simulated_internal"], mode="hybrid")
    assert 0 < len(hits) <= 4
    assert {h.payload["source_kind"] for h in hits} == {"simulated_internal"}


# --- exact terms the dense search misses ------------------------------------------------------------------------


def test_hybrid_finds_the_exact_term_questions_dense_misses(index):
    assert len(EXACT) >= 3
    dense, hybrid = evaluate(index, EXACT, k=6, mode="dense"), evaluate(index, EXACT, k=6, mode="hybrid")
    assert sum(row["rank"] is None for row in dense["cases"]) >= 3  # hashing embedder: reference, not proof
    assert all(row["rank"] for row in hybrid["cases"])
    assert hybrid["overall"]["mrr"] > dense["overall"]["mrr"]


# --- persistence by corpus hash ---------------------------------------------------------------------------------


def test_bm25_is_rebuilt_only_when_the_corpus_hash_changes(tmp_path):
    records = [chunk("d1#0", "Taxa MDR do débito").payload(), chunk("d2#0", "Erro E-1023 na venda").payload()]
    first, built = bm25.load_or_build(records, tmp_path)
    assert built and bm25.bm25_path(tmp_path, first.corpus_hash).exists()
    again, built = bm25.load_or_build(list(reversed(records)), tmp_path)  # same corpus, other order: loaded
    assert not built and again.corpus_hash == first.corpus_hash
    assert [p["chunk_id"] for _, p in again.search("e-1023", k=2)] == ["d2#0"]
    changed = [*records, chunk("d3#0", "Antecipação de recebíveis").payload()]
    other, built = bm25.load_or_build(changed, tmp_path)
    assert built and other.corpus_hash != first.corpus_hash
    assert sorted(p.name for p in tmp_path.glob("bm25-*.pkl")) == sorted(
        f"bm25-{h}.pkl" for h in (first.corpus_hash, other.corpus_hash)
    )


def test_index_persists_bm25_next_to_the_manifest_and_reloads_it(tmp_path, monkeypatch):
    chunks = [chunk("d1#0", "Taxa MDR do débito na Get Smart"), chunk("d2#0", "Erro E-1023 ao vender no crédito")]
    first = KnowledgeIndex(open_qdrant(":memory:", tmp_path), "c", HashEmbedder(), bm25_dir=tmp_path)
    manifest = first.rebuild(chunks, tmp_path / "index_manifest.json")
    assert manifest["retrieval_modes"] == ["dense", "hybrid"]
    stored = json.loads((tmp_path / "index_manifest.json").read_text(encoding="utf-8"))
    assert stored["bm25_corpus_hash"] == manifest["bm25_corpus_hash"]
    assert first.search("E-1023", k=1, mode="hybrid")[0].chunk_id == "d2#0"
    assert bm25.bm25_path(tmp_path, manifest["bm25_corpus_hash"]).exists()

    def no_build(records):
        raise AssertionError("BM25 rebuilt for an unchanged corpus")

    monkeypatch.setattr(bm25.Bm25Index, "build", staticmethod(no_build))
    second = KnowledgeIndex(open_qdrant(":memory:", tmp_path), "c", HashEmbedder(), bm25_dir=tmp_path)
    second.rebuild(chunks)
    assert second.search("E-1023", k=1, mode="hybrid")[0].chunk_id == "d2#0"  # loaded from the file


def test_replacing_a_collection_drops_its_cached_bm25(tmp_path):
    idx = KnowledgeIndex(open_qdrant(":memory:", tmp_path), "c", HashEmbedder())
    idx.rebuild([chunk("d1#0", "Taxa MDR do débito"), chunk("d2#0", "Erro E-1023 na venda")])
    assert idx.search("E-1023", k=2, mode="hybrid")[0].chunk_id == "d2#0"
    idx.rebuild([chunk("d1#0", "Taxa MDR do débito"), chunk("d3#0", "Erro E-1023 no Pix")], replace_existing=True)
    assert "d2#0" not in [h.chunk_id for h in idx.search("E-1023", k=2, mode="hybrid")]


# --- CLI --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
def test_eval_retrieval_reports_mode_and_bm25_hash_without_network(tmp_path, capsys, mode):
    settings = Settings(_env_file=None, openai_api_key=None, runtime_dir=tmp_path / "runtime")
    assert cli.cmd_eval_retrieval(settings, SimpleNamespace(fake=True, k=6, mode=mode)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == mode and len(report["bm25_corpus_hash"]) == 64
    assert report["overall"]["n"] == len(CASES)
    assert not list((tmp_path / "runtime").glob("bm25-*.pkl"))  # in memory, like the evaluation Qdrant


def test_eval_retrieval_command_line_takes_mode(tmp_path, capsys, monkeypatch):
    settings = Settings(_env_file=None, openai_api_key=None, runtime_dir=tmp_path / "runtime")
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    assert cli.main(["eval-retrieval", "--fake", "--mode", "hybrid"]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "hybrid"
