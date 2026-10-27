"""Retrieval evaluation: hit rate (Recall@k with any-relevant-doc) and MRR over a labeled question set."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from merchant_assistant.rag.index import KnowledgeIndex


@dataclass
class RetrievalCase:
    id: str
    case: str
    language: str
    question: str
    expected_docs: list[str]


def load_cases(path: Path) -> list[RetrievalCase]:
    return [RetrievalCase(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _relevant(payload: dict, expected: list[str]) -> bool:
    haystack = f"{payload.get('doc_id', '')} {payload.get('url') or ''}"
    return any(e in haystack for e in expected)


def evaluate(index: KnowledgeIndex, cases: list[RetrievalCase], k: int = 6) -> dict:
    rows = []
    for case in cases:
        hits = index.search(case.question, k=k)
        rank = next((i + 1 for i, h in enumerate(hits) if _relevant(h.payload, case.expected_docs)), None)
        rows.append(
            {
                "id": case.id,
                "language": case.language,
                "rank": rank,
                "top": [h.payload.get("doc_id") for h in hits[:3]],
                "top_score": round(hits[0].score, 3) if hits else None,
            }
        )

    def summary(selected: list[dict]) -> dict:
        n = len(selected)
        return {
            "n": n,
            "recall_at_k": round(sum(r["rank"] is not None for r in selected) / n, 3) if n else None,
            "mrr": round(sum(1 / r["rank"] for r in selected if r["rank"]) / n, 3) if n else None,
        }

    return {
        "k": k,
        "overall": summary(rows),
        "by_language": {lang: summary([r for r in rows if r["language"] == lang]) for lang in ("en", "pt")},
        "cases": rows,
    }
