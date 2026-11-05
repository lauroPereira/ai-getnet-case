"""Task 81 (v0.9.0, CA-52): nDCG@k with fixed numbers, the seal check, the accumulated report and the D7 line.

Synthetic data only: these tests never read the retrieval holdout."""

from __future__ import annotations

import math

import pytest

from merchant_assistant.evaluation import retrieval
from merchant_assistant.evaluation.retrieval import (
    RetrievalCase,
    SealError,
    check_seal,
    dcg,
    evaluate,
    ndcg_at_k,
    record_run,
    render_markdown,
    seal_digest,
    suggest_default,
)
from merchant_assistant.rag.index import Hit

# --- nDCG@k: fixed numbers ---------------------------------------------------------------------------------------


def test_dcg_uses_linear_gain_and_log2_discount():
    assert dcg([1]) == 1.0
    assert dcg([0, 1]) == pytest.approx(1 / math.log2(3))
    assert dcg([2, 1]) == pytest.approx(2 + 1 / math.log2(3))  # 2.63093


def test_perfect_ranking_is_one():
    assert ndcg_at_k([2, 1, 0, 0, 0, 0], [2, 1]) == 1.0
    assert ndcg_at_k([1, 0, 0], [1]) == 1.0


def test_inverted_and_late_rankings_have_known_values():
    assert ndcg_at_k([1, 2], [2, 1]) == pytest.approx(0.859719, abs=1e-6)  # (1 + 2/log2 3) / (2 + 1/log2 3)
    assert ndcg_at_k([0, 0, 0, 0, 0, 1], [1]) == pytest.approx(1 / math.log2(7)) == pytest.approx(0.356207, abs=1e-6)
    assert ndcg_at_k([0, 1], [1]) == pytest.approx(0.630930, abs=1e-6)


def test_cut_at_k_and_no_relevant():
    assert ndcg_at_k([0, 0, 0, 0, 0, 0, 1], [1], k=6) == 0.0  # rank 7 is outside @6
    assert ndcg_at_k([0, 0], [2, 1]) == 0.0
    assert ndcg_at_k([1], []) == 0.0


def test_gains_by_chunk_grade_and_by_first_relevant_document():
    hits = [Hit(0.9, {"chunk_id": f"d{i}#0", "doc_id": f"pub:d{i}"}) for i in range(1, 5)]
    graded = RetrievalCase("h", "pt", "q", relevant_chunks={"d3#0": 2, "d1#0": 1})
    assert graded.gains(hits) == [1, 0, 2, 0] and graded.ideal() == [2, 1]
    by_doc = RetrievalCase("d", "en", "q", expected_docs=["d2", "d4"])
    assert by_doc.gains(hits) == [0, 1, 0, 0] and by_doc.ideal() == [1]  # "any of these": one target


class FixedIndex:
    def __init__(self, ranking: dict[str, list[str]]) -> None:
        self.ranking, self.calls = ranking, []

    def search(self, query, *, k, mode=None, **extra):
        self.calls.append((query, k, mode, sorted(extra)))
        return [Hit(0.5, {"chunk_id": c, "doc_id": c.split("#")[0]}) for c in self.ranking[query]]


def test_evaluate_reports_recall_mrr_ndcg_and_time():
    index = FixedIndex({"q1": ["a#0", "b#0"], "q2": ["x#0", "y#0", "b#0"], "q3": ["x#0"]})
    cases = [
        RetrievalCase("1", "pt", "q1", category="fee", relevant_chunks={"a#0": 2}),
        RetrievalCase("2", "en", "q2", category="fee", relevant_chunks={"b#0": 2, "y#0": 1}),
        RetrievalCase("3", "pt", "q3", category="product", relevant_chunks={"a#0": 2}),
    ]
    report = evaluate(index, cases, k=6, mode="hybrid")
    o = report["overall"]
    assert (o["n"], o["recall_at_k"], o["mrr"]) == (3, 0.667, 0.5)  # ranks 1, 2, none
    # nDCG: 1; (1/log2 3 + 2/log2 4) / (2 + 1/log2 3) = 0.6199; 0
    assert [r["ndcg"] for r in report["cases"]] == [1.0, 0.62, 0.0]
    assert o["ndcg_at_k"] == 0.54 and o["mean_ms"] is not None
    assert set(report["by_category"]) == {"fee", "product"} and report["by_category"]["fee"]["n"] == 2
    assert all(call[2] == "hybrid" and call[3] == [] for call in index.calls)  # no reranker arguments when off


def test_evaluate_passes_the_reranker_and_counts_its_failures():
    class NotingIndex(FixedIndex):
        def search(self, query, *, k, mode=None, **extra):
            extra["notes"]["rerank"] = {"status": "failed" if query == "q2" else "ok"}
            return super().search(query, k=k, mode=mode, **extra)

    index = NotingIndex({"q1": ["a#0"], "q2": ["a#0"]})
    cases = [RetrievalCase("1", "pt", "q1", expected_docs=["a"]), RetrievalCase("2", "en", "q2", expected_docs=["a"])]
    report = evaluate(index, cases, mode="hybrid", reranker=object(), meter=object())
    assert [r["rerank"] for r in report["cases"]] == ["ok", "failed"] and report["rerank_failures"] == 1
    assert index.calls[0][3] == ["meter", "notes", "reranker"]


# --- seal --------------------------------------------------------------------------------------------------------


def sealed(tmp_path, text: str, name: str = "set.jsonl"):
    path = tmp_path / name
    path.write_bytes(text.encode("utf-8"))
    path.with_suffix(".sha256").write_text(f"{seal_digest(path)}  {name}\n", encoding="utf-8")
    return path


def test_seal_accepts_crlf_and_refuses_edits_or_a_missing_seal(tmp_path):
    path = sealed(tmp_path, '{"id": "a"}\n{"id": "b"}\n')
    assert check_seal(path) == seal_digest(path)
    path.write_bytes(b'{"id": "a"}\r\n{"id": "b"}\r\n')
    assert check_seal(path)
    path.write_bytes(b'{"id": "a"}\n{"id": "c"}\n')
    with pytest.raises(SealError, match="does not match"):
        check_seal(path)
    path.with_suffix(".sha256").unlink()
    with pytest.raises(SealError, match="not found"):
        check_seal(path)


def test_only_the_holdout_split_is_sealed(tmp_path, monkeypatch):
    line = '{"id": "s1", "language": "pt", "question": "q", "relevant_chunks": {"a#0": 2}}\n'
    sealed(tmp_path, line, retrieval.SPLITS["holdout_v090"])
    (tmp_path / retrieval.SPLITS["dev"]).write_text(
        '{"id": "d1", "case": "UC", "language": "en", "question": "q", "expected_docs": ["a"]}\n', encoding="utf-8"
    )
    monkeypatch.setattr(retrieval, "SCENARIOS", tmp_path)
    cases, digest = retrieval.split_cases("holdout_v090")
    assert [c.id for c in cases] == ["s1"] and digest == seal_digest(tmp_path / retrieval.SPLITS["holdout_v090"])
    assert retrieval.split_cases("dev")[1] is None
    with pytest.raises(ValueError):
        retrieval.split_cases("holdout")


# --- accumulated report and the D7 suggestion -----------------------------------------------------------------------


def run(split: str, mode: str, rerank: bool, ndcg: float, model: str = "text-embedding-3-small", **extra) -> dict:
    overall = {"n": 20, "recall_at_k": 0.9, "mrr": 0.7, "ndcg_at_k": ndcg, "mean_ms": 12.5}
    return {"split": split, "mode": mode, "rerank": rerank, "k": 6, "embedding_model": model, "overall": overall,
            "by_language": {}, "measured_at": "2026-11-05T12:00:00+00:00", **extra}


def table(dev: tuple[float, float, float], holdout: tuple[float, float, float], failures: dict | None = None) -> dict:
    report = None
    for split, values in (("dev", dev), ("holdout_v090", holdout)):
        for (mode, rerank), value in zip((("dense", False), ("hybrid", False), ("hybrid", True)), values, strict=True):
            extra = {"rerank_failures": (failures or {}).get(split, 0)} if rerank else {}
            report = record_run(report, run(split, mode, rerank, value, **extra))
    return report


@pytest.mark.parametrize(
    ("dev", "holdout", "expected"),
    [
        ((0.5, 0.6, 0.7), (0.5, 0.6, 0.7), "RETRIEVAL_MODE=hybrid, RERANK=on"),
        ((0.5, 0.6, 0.7), (0.5, 0.6, 0.6), "RETRIEVAL_MODE=hybrid, RERANK=off"),  # rerank does not improve holdout
        ((0.5, 0.6, 0.5), (0.5, 0.6, 0.7), "RETRIEVAL_MODE=hybrid, RERANK=off"),  # nor dev
        ((0.5, 0.6, 0.7), (0.6, 0.6, 0.7), "RETRIEVAL_MODE=dense, RERANK=off"),  # hybrid not confirmed in holdout
        ((0.6, 0.5, 0.9), (0.5, 0.6, 0.9), "RETRIEVAL_MODE=dense, RERANK=off"),  # hybrid worse in dev
    ],
)
def test_d7_suggestion(dev, holdout, expected):
    line = suggest_default(table(dev, holdout))
    assert line.startswith(expected + " (reranker com 0 falhas em 40 consultas; nDCG@6: dev: dense ")


@pytest.mark.parametrize("failures", [{"dev": 1}, {"holdout_v090": 3}])
def test_reranker_failures_make_its_suggestion_unavailable_and_show_in_the_table(failures):
    """Review P2-2: a failed query was answered by the hybrid search, so the hybrid+rerank number is not the
    reranker's; the hybrid suggestion still follows its own rule."""
    report = table((0.5, 0.6, 0.7), (0.5, 0.6, 0.7), failures)
    (split, count), = failures.items()
    line = suggest_default(report)
    assert line.startswith(f"RETRIEVAL_MODE=hybrid, RERANK=indisponível (reranker com {count} falhas em 40 consultas")
    text = render_markdown(report)
    assert f"| {split} | hybrid+rerank | 20 | 0.900 | 0.700 | 0.700 | 12.5 | 1 | {count} de 20 |" in text
    assert "| dev | hybrid | 20 | 0.900 | 0.700 | 0.600 | 12.5 | 1 | — |" in text
    assert f"Modo padrão sugerido (regra D7, a decisão é do Supervisor): {line}" in text


def test_markdown_states_the_fusion_depth_of_the_reranker():
    text = render_markdown(table((0.5, 0.6, 0.7), (0.5, 0.6, 0.7)))
    assert "reordena os 12 primeiros de uma fusão de profundidade 36, contra 18 do `hybrid`" in text
    assert "| dev | hybrid+rerank | 20 | 0.900 | 0.700 | 0.700 | 12.5 | 1 | 0 de 20 |" in text


def test_suggestion_waits_for_every_split_and_configuration():
    report = record_run(None, run("dev", "dense", False, 0.5))
    report = record_run(report, run("dev", "hybrid", True, 0.6))
    assert suggest_default(report) == "indisponível: faltam dev/hybrid, holdout_v090/dense, holdout_v090/hybrid, " \
        "holdout_v090/hybrid+rerank"


def test_record_run_counts_repeats_and_refuses_other_embeddings():
    holdout = {"split": "holdout_v090", "sha256": "f" * 64, "seal": "ok", "used": True}
    report = record_run(None, run("holdout_v090", "dense", False, 0.4, holdout=holdout))
    report = record_run(report, run("holdout_v090", "dense", False, 0.5, holdout=holdout))
    entry = report["results"]["holdout_v090"]["dense"]
    assert entry["runs"] == 2 and entry["overall"]["ndcg_at_k"] == 0.5 and entry["holdout"] == holdout
    text = render_markdown(report)
    assert "| holdout_v090 | dense | 20 | 0.900 | 0.700 | 0.500 | 12.5 | 2 (holdout já visto) | — |" in text
    assert "Holdout de retrieval: usado, lacre `ffffffffffff…` conferido." in text
    assert "Modo padrão sugerido (regra D7, a decisão é do Supervisor): indisponível" in text
    with pytest.raises(ValueError, match="another --out"):
        record_run(report, run("dev", "dense", False, 0.5, model="hash-embedder-v1"))


def test_markdown_flags_hash_embeddings_and_an_unused_holdout():
    text = render_markdown(record_run(None, run("dev", "hybrid", True, 0.6, model="hash-embedder-v1")))
    assert "| dev | hybrid+rerank | 20 |" in text and "Holdout de retrieval: não usado." in text
    assert "Embeddings de hash (sem rede)" in text
