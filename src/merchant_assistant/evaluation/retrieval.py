"""Retrieval evaluation: Recall@k (any relevant passage), MRR and nDCG@k over a labeled question set, with the mean
time per query. Two splits (task 81, D8): `dev` (`retrieval.jsonl`, labels by document, used while developing) and
`holdout_v090` (`retrieval_holdout_v090.jsonl`, labels by chunk with grades, sealed by sha256 and measured last).

v0.11.0 (task 90, D7): a fourth configuration, `hybrid@36`, the fusion the reranker reads cut to k without a model, so
`hybrid+rerank - hybrid@36` is the reranker's own gain; and the BM25 floor (`--bm25-min-score`), measured as a
configuration of its own."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.rag.index import CONTROL_MODE, KnowledgeIndex
from merchant_assistant.rag.rerank import RERANK_CANDIDATES

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
PROJECT_SCENARIOS = SCENARIOS  # the versioned sets; tests point SCENARIOS at synthetic ones
SPLITS = {"dev": "retrieval.jsonl", "holdout_v090": "retrieval_holdout_v090.jsonl"}
SEALED_SPLITS = frozenset({"holdout_v090"})
CONFIGURATIONS = ("dense", "hybrid", CONTROL_MODE, "hybrid+rerank")
METRICS = ("recall_at_k", "mrr", "ndcg_at_k")


class SealError(ValueError):
    """The holdout file does not match the sha256 recorded next to it (or the seal is missing)."""


@dataclass
class RetrievalCase:
    id: str
    language: str
    question: str
    case: str = ""
    category: str = ""
    expected_docs: list[str] = field(default_factory=list)  # dev: any of these documents answers
    relevant_chunks: dict[str, int] = field(default_factory=dict)  # holdout: chunk_id -> grade (2 correct, 1 also)

    def gains(self, hits) -> list[int]:
        """Gain of each returned hit. Chunk labels: the grade. Document labels ("any of these"): 1 for the first
        relevant hit only, so the ideal ranking is that one hit at rank 1."""
        if self.relevant_chunks:
            return [self.relevant_chunks.get(h.chunk_id, 0) for h in hits]
        first = next((i for i, h in enumerate(hits) if _relevant(h.payload, self.expected_docs)), None)
        return [1 if i == first else 0 for i in range(len(hits))]

    def ideal(self) -> list[int]:
        return sorted(self.relevant_chunks.values(), reverse=True) if self.relevant_chunks else [1]


def load_cases(path: Path) -> list[RetrievalCase]:
    return [RetrievalCase(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def seal_digest(path: Path) -> str:
    """sha256 of the UTF-8 content with line breaks normalized to LF (as `holdout_v080`)."""
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_seal(path: Path) -> str:
    seal = path.with_suffix(".sha256")
    if not seal.is_file():
        raise SealError(f"{path.name}: seal {seal.name} not found")
    recorded = seal.read_text(encoding="utf-8").split()
    digest = seal_digest(path)
    if not recorded or recorded[0] != digest:
        raise SealError(f"{path.name}: content does not match the sealed sha256 (holdout changed after sealing)")
    return digest


def split_cases(split: str, scenarios: Path | None = None) -> tuple[list[RetrievalCase], str | None]:
    """The cases of a split and, for a sealed split, its checked sha256 (refused when the seal does not match)."""
    if split not in SPLITS:
        raise ValueError(f"Unknown retrieval split: {split!r}")
    path = (scenarios or SCENARIOS) / SPLITS[split]
    digest = check_seal(path) if split in SEALED_SPLITS else None
    return load_cases(path), digest


def _relevant(payload: dict, expected: list[str]) -> bool:
    haystack = f"{payload.get('doc_id', '')} {payload.get('url') or ''}"
    return any(e in haystack for e in expected)


def dcg(gains: list[float]) -> float:
    """Linear gain discounted by log2 of the position plus one (rank 1 counts in full)."""
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(gains: list[float], ideal: list[float], k: int = 6) -> float:
    best = dcg(sorted(ideal, reverse=True)[:k])
    return dcg(list(gains[:k])) / best if best else 0.0


def evaluate(
    index: KnowledgeIndex,
    cases: list[RetrievalCase],
    k: int = 6,
    mode: str | None = None,
    *,
    reranker=None,
    meter=None,
) -> dict:
    rows = []
    floor = 0.0 if (mode or index.mode) == "dense" else index.bm25_min_score
    for case in cases:
        notes: dict = {}
        extra = {"reranker": reranker, "meter": meter, "notes": notes} if reranker is not None else {}
        if floor > 0:  # task 90: the index writes the BM25-only hits its floor dropped
            extra["notes"] = notes
        started = time.perf_counter()
        hits = index.search(case.question, k=k, mode=mode, **extra)[:k]
        elapsed_ms = (time.perf_counter() - started) * 1000
        gains = case.gains(hits)
        row = {
            "id": case.id,
            "language": case.language,
            "rank": next((i + 1 for i, g in enumerate(gains) if g > 0), None),
            "ndcg": round(ndcg_at_k(gains, case.ideal(), k), 3),
            "ms": round(elapsed_ms, 1),
            "top": [h.payload.get("doc_id") for h in hits[:3]],
            "origins": [h.origin for h in hits[:3]],
            "top_score": round(hits[0].score, 3) if hits else None,
        }
        if case.category:
            row["category"] = case.category
        if reranker is not None:
            row["rerank"] = notes.get("rerank", {}).get("status")
        if floor > 0:  # task 90: how many BM25-only hits the floor dropped before the fusion of this query
            row["bm25_dropped"] = len(notes.get("bm25_dropped", []))
        rows.append(row)

    def summary(selected: list[dict]) -> dict:
        n = len(selected)
        if not n:
            return {"n": 0, "recall_at_k": None, "mrr": None, "ndcg_at_k": None, "mean_ms": None}
        return {
            "n": n,
            "recall_at_k": round(sum(r["rank"] is not None for r in selected) / n, 3),
            "mrr": round(sum(1 / r["rank"] for r in selected if r["rank"]) / n, 3),
            "ndcg_at_k": round(sum(r["ndcg"] for r in selected) / n, 3),
            "mean_ms": round(sum(r["ms"] for r in selected) / n, 1),
        }

    report = {
        "k": k,
        "overall": summary(rows),
        "by_language": {lang: summary([r for r in rows if r["language"] == lang]) for lang in ("en", "pt")},
        "cases": rows,
    }
    categories = sorted({r["category"] for r in rows if "category" in r})
    if categories:
        report["by_category"] = {c: summary([r for r in rows if r.get("category") == c]) for c in categories}
    if reranker is not None:
        report["rerank_failures"] = sum(r["rerank"] == "failed" for r in rows)
    report["bm25_min_score"] = floor
    if floor > 0:
        report["bm25_dropped"] = sum(r["bm25_dropped"] for r in rows)
    return report


# --- accumulated report: one row per split and configuration, and the D7 suggestion ------------------------------


def configuration(mode: str, rerank: bool, bm25_min_score: float = 0.0) -> str:
    """The row of the table: the mode (or `hybrid+rerank`) and, when the BM25 floor is on, the floor."""
    name = "hybrid+rerank" if rerank else mode
    return f"{name} bm25>={bm25_min_score:g}" if bm25_min_score > 0 else name


def _base(config: str) -> str:
    return config.split(" ")[0]


def record_run(previous: dict | None, run: dict) -> dict:
    """Adds one `eval-retrieval` run to the report of earlier runs (same embeddings and k). A configuration measured
    again replaces its row and counts the run, so a holdout seen before shows as "já visto"."""
    report = previous or {"embedding_model": run["embedding_model"], "k": run["k"], "results": {}}
    if (report["embedding_model"], report["k"]) != (run["embedding_model"], run["k"]):
        raise ValueError(
            f"the report has embeddings {report['embedding_model']} and k={report['k']}; this run has "
            f"{run['embedding_model']} and k={run['k']}: use another --out"
        )
    split, config = run["split"], configuration(run["mode"], run["rerank"], run.get("bm25_min_score", 0.0))
    earlier = report["results"].get(split, {}).get(config)
    entry = {
        "overall": run["overall"],
        "by_language": run["by_language"],
        "runs": (earlier["runs"] + 1) if earlier else 1,
        "measured_at": run["measured_at"],
    }
    for key in ("by_category", "rerank_failures", "rerank_usage", "holdout", "bm25_min_score", "bm25_dropped"):
        if key in run:
            entry[key] = run[key]
    report["results"].setdefault(split, {})[config] = entry
    return report


def suggest_default(report: dict) -> str:
    """Rule D7, written before measuring: hybrid if its nDCG@k beats dense in dev and in the holdout; the reranker
    only if hybrid+rerank beats its control at the same depth, hybrid@36, in nDCG@k in both (ADR 0020; spec v0.11.0
    D7). A suggestion for the Supervisor, not the decision. The rows with a BM25 floor are not part of the rule."""
    results = report.get("results", {})
    splits = ("dev", "holdout_v090")
    missing = [f"{s}/{c}" for s in splits for c in CONFIGURATIONS if c not in results.get(s, {})]
    if missing:
        return f"indisponível: faltam {', '.join(missing)}"

    def nd(split: str, config: str) -> float:
        return results[split][config]["overall"]["ndcg_at_k"]

    hybrid = all(nd(s, "hybrid") > nd(s, "dense") for s in splits)
    rerank = hybrid and all(nd(s, "hybrid+rerank") > nd(s, CONTROL_MODE) for s in splits)
    numbers = "; ".join(
        f"{s}: " + ", ".join(f"{c} {nd(s, c):.3f}" for c in CONFIGURATIONS) for s in splits
    )
    failures, queries = rerank_failures(report)
    # review P2-2: a query where the reranker failed was answered by the hybrid search, so its number is not the
    # reranker's and the rule cannot suggest it
    suggested = "indisponível" if failures else ("on" if rerank else "off")
    choice = f"RETRIEVAL_MODE={'hybrid' if hybrid else 'dense'}, RERANK={suggested}"
    return f"{choice} (reranker com {failures} falhas em {queries} consultas; nDCG@{report['k']}: {numbers})"


def rerank_failures(report: dict) -> tuple[int, int]:
    """Reranker failures and queries over every split measured with hybrid+rerank."""
    entries = [r["hybrid+rerank"] for r in report.get("results", {}).values() if "hybrid+rerank" in r]
    return sum(e.get("rerank_failures", 0) for e in entries), sum(e["overall"]["n"] for e in entries)


def own_gain(report: dict) -> dict[str, dict[str, float]]:
    """Per split with both rows: `hybrid+rerank - hybrid@36` in Recall@k, MRR and nDCG@k, the reranker's own gain at
    the same fusion depth (rows without a BM25 floor)."""
    gains = {}
    for split in SPLITS:
        rows = report.get("results", {}).get(split, {})
        if "hybrid+rerank" in rows and CONTROL_MODE in rows:
            a, b = rows["hybrid+rerank"]["overall"], rows[CONTROL_MODE]["overall"]
            gains[split] = {m: round(a[m] - b[m], 3) for m in METRICS}
    return gains


def _ordered(rows: dict) -> list[str]:
    """The configurations of a split in table order: the four modes, each followed by its rows with a BM25 floor."""
    order = {c: i for i, c in enumerate(CONFIGURATIONS)}
    return sorted(rows, key=lambda c: (order.get(_base(c), len(order)), rows[c].get("bm25_min_score", 0.0), c))


def render_markdown(report: dict) -> str:
    k = report["k"]
    lines = [
        "# Medição de retrieval (`eval-retrieval`)",
        "",
        f"Embeddings: `{report['embedding_model']}`. k = {k}. Relevância: `dev` por documento (qualquer um dos "
        "rotulados; nDCG com um alvo só), `holdout_v090` por chunk com grau (2 a passagem correta, 1 também "
        "relevante).",
        "",
        f"`hybrid+rerank`: o modelo reordena os {RERANK_CANDIDATES} primeiros de uma fusão de profundidade "
        f"{3 * max(k, RERANK_CANDIDATES)}, contra {3 * k} do `hybrid`; numa consulta em que o reranker falha, a "
        f"resposta é a do `hybrid`. `{CONTROL_MODE}` é o controle: a mesma fusão cortada em k pela ordem do RRF, sem "
        "modelo.",
        "",
        "Piso BM25: hits achados só pelo BM25 com score (sobre o maior score BM25 da consulta) abaixo do piso saem "
        "antes da fusão; `0` é desligado. A coluna Descartados soma esses hits em todas as consultas.",
        "",
        f"| Split | Configuração | Piso BM25 | n | Recall@{k} | MRR | nDCG@{k} | Tempo médio (ms) | Execuções "
        "| Falhas do reranker | Descartados |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for split in SPLITS:
        rows = report["results"].get(split, {})
        for config in _ordered(rows):
            entry = rows[config]
            o = entry["overall"]
            runs = str(entry["runs"]) + (" (holdout já visto)" if split in SEALED_SPLITS and entry["runs"] > 1 else "")
            failed = f"{entry.get('rerank_failures', 0)} de {o['n']}" if _base(config) == "hybrid+rerank" else "—"
            floor = "—" if _base(config) == "dense" else f"{entry.get('bm25_min_score', 0.0):g}"
            dropped = str(entry["bm25_dropped"]) if "bm25_dropped" in entry else "—"
            lines.append(
                f"| {split} | {config} | {floor} | {o['n']} | {o['recall_at_k']:.3f} | {o['mrr']:.3f} "
                f"| {o['ndcg_at_k']:.3f} | {o['mean_ms']:.1f} | {runs} | {failed} | {dropped} |"
            )
    gains = own_gain(report)
    if gains:
        lines += [
            "",
            f"Ganho próprio do reranker (`hybrid+rerank` menos `{CONTROL_MODE}`, mesma profundidade de fusão, sem "
            "piso):",
            "",
            f"| Split | Diferença Recall@{k} | Diferença MRR | Diferença nDCG@{k} |",
            "| --- | --- | --- | --- |",
        ]
        for split, gain in gains.items():
            lines.append(f"| {split} | " + " | ".join(f"{gain[m]:+.3f}" for m in METRICS) + " |")
    holdout = next(
        (e["holdout"] for e in report["results"].get("holdout_v090", {}).values() if "holdout" in e), None
    )
    used = f"usado, lacre `{holdout['sha256'][:12]}…` conferido" if holdout else "não usado"
    lines += ["", f"Holdout de retrieval: {used}."]
    if report["embedding_model"].startswith("hash"):
        lines.append("Embeddings de hash (sem rede): os números são referência do caminho, não prova de qualidade.")
    lines += [
        "",
        f"Modo padrão sugerido (regra D7, a decisão é do Supervisor): {suggest_default(report)}",
        "",
    ]
    return "\n".join(lines)


class CountingMeter:
    """Meter of the reranker calls in `eval-retrieval`: forwards to the budget meter of a paid run (or to nothing,
    offline) and counts calls and tokens for the report."""

    def __init__(self, inner=None) -> None:
        from merchant_assistant.llm.base import NullMeter, Usage

        self.inner, self.calls, self.usage = inner or NullMeter(), 0, Usage()

    def reserve(self, **kwargs):
        reservation = self.inner.reserve(**kwargs)
        self.calls += 1
        return reservation

    def settle(self, reservation, usage) -> None:
        if usage is not None:
            self.usage.add(usage)
        self.inner.settle(reservation, usage)

    def summary(self) -> dict:
        return {
            "calls": self.calls,
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "cost_usd": round(getattr(self.inner, "cost_usd", 0.0), 6),
        }
