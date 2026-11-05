"""Retrieval evaluation: Recall@k (any relevant passage), MRR and nDCG@k over a labeled question set, with the mean
time per query. Two splits (task 81, D8): `dev` (`retrieval.jsonl`, labels by document, used while developing) and
`holdout_v090` (`retrieval_holdout_v090.jsonl`, labels by chunk with grades, sealed by sha256 and measured last)."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.rag.index import KnowledgeIndex

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
SPLITS = {"dev": "retrieval.jsonl", "holdout_v090": "retrieval_holdout_v090.jsonl"}
SEALED_SPLITS = frozenset({"holdout_v090"})
CONFIGURATIONS = ("dense", "hybrid", "hybrid+rerank")


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
    for case in cases:
        notes: dict = {}
        extra = {"reranker": reranker, "meter": meter, "notes": notes} if reranker is not None else {}
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
    return report


# --- accumulated report: one row per split and configuration, and the D7 suggestion ------------------------------


def configuration(mode: str, rerank: bool) -> str:
    return "hybrid+rerank" if rerank else mode


def record_run(previous: dict | None, run: dict) -> dict:
    """Adds one `eval-retrieval` run to the report of earlier runs (same embeddings and k). A configuration measured
    again replaces its row and counts the run, so a holdout seen before shows as "já visto"."""
    report = previous or {"embedding_model": run["embedding_model"], "k": run["k"], "results": {}}
    if (report["embedding_model"], report["k"]) != (run["embedding_model"], run["k"]):
        raise ValueError(
            f"the report has embeddings {report['embedding_model']} and k={report['k']}; this run has "
            f"{run['embedding_model']} and k={run['k']}: use another --out"
        )
    split, config = run["split"], configuration(run["mode"], run["rerank"])
    earlier = report["results"].get(split, {}).get(config)
    entry = {
        "overall": run["overall"],
        "by_language": run["by_language"],
        "runs": (earlier["runs"] + 1) if earlier else 1,
        "measured_at": run["measured_at"],
    }
    for key in ("by_category", "rerank_failures", "rerank_usage", "holdout"):
        if key in run:
            entry[key] = run[key]
    report["results"].setdefault(split, {})[config] = entry
    return report


def suggest_default(report: dict) -> str:
    """Rule D7, written before measuring: hybrid if its nDCG@k beats dense in dev and in the holdout; the reranker
    only if hybrid+rerank beats hybrid in nDCG@k in both. A suggestion for the Supervisor, not the decision."""
    results = report.get("results", {})
    splits = ("dev", "holdout_v090")
    missing = [f"{s}/{c}" for s in splits for c in CONFIGURATIONS if c not in results.get(s, {})]
    if missing:
        return f"indisponível: faltam {', '.join(missing)}"

    def nd(split: str, config: str) -> float:
        return results[split][config]["overall"]["ndcg_at_k"]

    hybrid = all(nd(s, "hybrid") > nd(s, "dense") for s in splits)
    rerank = hybrid and all(nd(s, "hybrid+rerank") > nd(s, "hybrid") for s in splits)
    numbers = "; ".join(
        f"{s}: " + ", ".join(f"{c} {nd(s, c):.3f}" for c in CONFIGURATIONS) for s in splits
    )
    choice = f"RETRIEVAL_MODE={'hybrid' if hybrid else 'dense'}, RERANK={'on' if rerank else 'off'}"
    return f"{choice} (nDCG@{report['k']}: {numbers})"


def render_markdown(report: dict) -> str:
    k = report["k"]
    lines = [
        "# Medição de retrieval (`eval-retrieval`)",
        "",
        f"Embeddings: `{report['embedding_model']}`. k = {k}. Relevância: `dev` por documento (qualquer um dos "
        "rotulados; nDCG com um alvo só), `holdout_v090` por chunk com grau (2 a passagem correta, 1 também "
        "relevante).",
        "",
        f"| Split | Configuração | n | Recall@{k} | MRR | nDCG@{k} | Tempo médio (ms) | Execuções |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for split in SPLITS:
        for config in CONFIGURATIONS:
            entry = report["results"].get(split, {}).get(config)
            if entry is None:
                continue
            o = entry["overall"]
            runs = str(entry["runs"]) + (" (holdout já visto)" if split in SEALED_SPLITS and entry["runs"] > 1 else "")
            lines.append(
                f"| {split} | {config} | {o['n']} | {o['recall_at_k']:.3f} | {o['mrr']:.3f} | {o['ndcg_at_k']:.3f} "
                f"| {o['mean_ms']:.1f} | {runs} |"
            )
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
