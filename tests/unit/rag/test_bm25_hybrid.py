"""Task 80 (v0.9.0, D7): BM25 + RRF hybrid retrieval, persisted by corpus hash; dense stays the default."""

import json
import time
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


# --- round 2 (review P2-1 to P2-3) ------------------------------------------------------------------------------


def test_rrf_uses_k_60_over_ranks_starting_at_1():
    fused = rrf([hit("a"), hit("b")], [(9.0, {"chunk_id": "b"})], k=2)
    assert [h.score for h in fused] == pytest.approx([1 / 62 + 1 / 61, 1 / 61])  # fixed numbers, not RRF_K
    assert RRF_K == 60


class _Lexical:
    def __init__(self, ranking: list[str], calls: list) -> None:
        self.ranking, self.calls = ranking, calls

    def search(self, query, *, k, source_kinds=None):
        self.calls.append(("bm25", k))
        return [(1.0, {"chunk_id": cid}) for cid in self.ranking[:k]]


def test_hybrid_fuses_the_top_3k_of_each_list(monkeypatch):
    """`e` is 5th in the dense list and 3rd in the BM25 list: with k=2 it only wins through both 3k=6 lists."""
    idx = KnowledgeIndex(open_qdrant(":memory:", PROJECT_ROOT), "depth", HashEmbedder())
    calls: list = []

    def dense(query, *, k, source_kinds, min_score):
        calls.append(("dense", k))
        return [hit(cid) for cid in ["a", "b", "c", "d", "e", "f", "g"][:k]]

    monkeypatch.setattr(idx, "_dense", dense)
    monkeypatch.setattr(idx, "bm25_index", lambda: _Lexical(["x", "y", "e", "z"], calls))
    fused = idx.search("q", k=2, mode="hybrid")
    assert sorted(calls) == [("bm25", 6), ("dense", 6)]
    assert [(h.chunk_id, h.origin) for h in fused] == [("e", "both"), ("a", "dense")]
    assert fused[0].score == pytest.approx(1 / 65 + 1 / 63)


def test_min_score_cuts_the_dense_list_only(tmp_path):
    """Rule for ADR 0020 and D7: the cosine threshold does not apply to BM25 or to the fused score."""
    idx = KnowledgeIndex(open_qdrant(":memory:", tmp_path), "ms", HashEmbedder())
    idx.rebuild([chunk("d1#0", "Taxa MDR do débito"), chunk("d2#0", "Erro E-1023 na venda")])
    assert idx.search("E-1023", k=2, min_score=0.99) == []  # dense: nothing above the threshold
    strict = idx.search("E-1023", k=2, min_score=0.99, mode="hybrid")
    assert [(h.chunk_id, h.origin) for h in strict] == [("d2#0", "bm25")]
    assert strict[0].score == pytest.approx(1 / 61)
    loose = idx.search("E-1023", k=2, min_score=0.0, mode="hybrid")
    assert {h.origin for h in loose} & {"dense", "both"}  # without the threshold the dense list takes part


def _recollected(cid: str, url: str, kind: str) -> Chunk:
    return Chunk(cid, cid.split("#")[0], 0, "Erro E-1023 na venda", cid, url, kind, {"collected_at": url})


def test_persisted_bm25_takes_payloads_from_the_current_collection(tmp_path):
    """Same ids and texts, other metadata (recollected snapshot): the file is reused, its metadata is not."""
    client = open_qdrant(":memory:", tmp_path)
    v1 = KnowledgeIndex(client, "v1", HashEmbedder(), bm25_dir=tmp_path)
    v1.rebuild([_recollected("p#0", "https://old.example", "public_official")])
    assert v1.search("E-1023", k=1, mode="hybrid")[0].payload["url"] == "https://old.example"
    v2 = KnowledgeIndex(client, "v2", HashEmbedder(), bm25_dir=tmp_path)
    v2.rebuild([_recollected("p#0", "https://new.example", "simulated_internal")])
    assert len(list(tmp_path.glob("bm25-*.pkl"))) == 1  # same corpus hash: one file for both versions
    assert v2.search("E-1023", mode="hybrid", source_kinds=["public_official"], min_score=0.99) == []
    current = v2.search("E-1023", mode="hybrid", source_kinds=["simulated_internal"], min_score=0.99)
    assert [(h.origin, h.payload["url"], h.payload["source_kind"]) for h in current] == [
        ("bm25", "https://new.example", "simulated_internal")
    ]


def test_the_bm25_file_keeps_ids_and_statistics_only(tmp_path):
    import pickle

    records = [_recollected("p#0", "https://old.example", "public_official").payload()]
    index, _ = bm25.load_or_build(records, tmp_path)
    with bm25.bm25_path(tmp_path, index.corpus_hash).open("rb") as handle:
        state = pickle.load(handle)
    assert set(state) == {"format", "corpus_hash", "chunk_ids", "bm25"} and state["chunk_ids"] == ["p#0"]
    assert b"old.example" not in bm25.bm25_path(tmp_path, index.corpus_hash).read_bytes()


def test_a_round_1_file_with_payloads_is_rebuilt(tmp_path):
    import pickle

    records = [_recollected("p#0", "https://new.example", "public_official").payload()]
    path = bm25.bm25_path(tmp_path, bm25.corpus_hash(records))
    stale = {"corpus_hash": bm25.corpus_hash(records), "payloads": [{**records[0], "url": "https://old.example"}]}
    path.write_bytes(pickle.dumps(stale))
    index, built = bm25.load_or_build(records, tmp_path)
    assert built and index.payloads[0]["url"] == "https://new.example"
    assert not bm25.load_or_build(records, tmp_path)[1]  # rewritten in the current format


def _big_corpus(n: int = 3000) -> list[dict]:
    return [
        chunk(f"d{i}#0", f"Documento {i} sobre taxa MDR, erro E-{1000 + i} e antecipação").payload() for i in range(n)
    ]


def _together(target, n: int = 4) -> tuple[list, list]:
    import threading

    barrier, results, errors = threading.Barrier(n), [], []

    def run():
        barrier.wait()
        try:
            results.append(target())
        except Exception as exc:  # collected for the assertion
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    return results, errors


def test_concurrent_first_builds_of_one_corpus_build_once_and_write_one_file(tmp_path):
    records = _big_corpus()
    results, errors = _together(lambda: bm25.load_or_build(records, tmp_path))
    assert errors == [] and len(results) == 4
    assert sum(built for _, built in results) == 1  # the others wait and load the file
    assert len({index.corpus_hash for index, _ in results}) == 1
    assert [p.name for p in tmp_path.iterdir()] == [f"bm25-{results[0][0].corpus_hash}.pkl"]  # no .tmp left


def test_concurrent_writers_use_their_own_temporary_files(tmp_path):
    """Builders in different processes are not serialized by the in-process lock: their writes must not collide."""
    index = bm25.Bm25Index.build(_big_corpus())
    path = bm25.bm25_path(tmp_path, index.corpus_hash)
    _, errors = _together(lambda: bm25._write(index, path))
    assert errors == []
    assert [p.name for p in tmp_path.iterdir()] == [path.name]
    assert bm25.load_or_build(_big_corpus(), tmp_path)[1] is False


def test_a_failed_write_still_answers_from_memory(tmp_path, monkeypatch):
    def locked(src, dst):
        raise PermissionError(32, "The process cannot access the file")

    monkeypatch.setattr(bm25.os, "replace", locked)
    records = [chunk("d2#0", "Erro E-1023 na venda").payload()]
    index, built = bm25.load_or_build(records, tmp_path)
    assert built and [p["chunk_id"] for _, p in index.search("E-1023", k=1)] == ["d2#0"]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("persisted", [True, False])
def test_concurrent_first_hybrid_searches_build_the_collection_bm25_once(tmp_path, monkeypatch, persisted):
    """The per-collection lock: also without a BM25 directory (evaluation, tests) one search builds, the rest wait."""
    bm25_dir = tmp_path if persisted else None
    idx = KnowledgeIndex(open_qdrant(":memory:", tmp_path), "conc", HashEmbedder(), bm25_dir=bm25_dir)
    idx.rebuild([chunk("d1#0", "Taxa MDR do débito"), chunk("d2#0", "Erro E-1023 na venda")])
    builds: list = []
    original = bm25.Bm25Index.build

    def counted(records):
        builds.append(len(records))
        time.sleep(0.2)  # a slow build: the other searches arrive while it runs
        return original(records)

    monkeypatch.setattr(bm25.Bm25Index, "build", staticmethod(counted))
    results, errors = _together(lambda: idx.search("E-1023", k=1, mode="hybrid")[0].chunk_id)
    assert errors == [] and results == ["d2#0"] * 4
    assert builds == [2]
