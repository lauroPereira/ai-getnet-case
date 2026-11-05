"""Seal and shape of the v0.9.0 retrieval holdout (D8, RF-95): written from the knowledge corpus before any retrieval
mode was measured on it, sealed in the commit where it was born, and never read by a development test.

The SHA-256 is computed over the UTF-8 content with line breaks normalized to LF (as `holdout_v080`), so a CRLF
checkout still matches and any edit to a case breaks the seal. This file only checks the seal and the labels against
the corpus: no search runs over these questions here."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from merchant_assistant.rag.chunk import chunk_document
from merchant_assistant.rag.documents import load_all

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "tests" / "scenarios"
HOLDOUT = SCENARIOS / "retrieval_holdout_v090.jsonl"
SEAL = SCENARIOS / "retrieval_holdout_v090.sha256"
CATEGORIES = {"product", "fee", "procedure", "exact_term"}


def normalized_digest(raw: bytes) -> str:
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sealed_digest() -> str:
    return SEAL.read_text(encoding="utf-8").split()[0]


def rows() -> list[dict]:
    return [json.loads(line) for line in HOLDOUT.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_seal_matches_content_and_names_the_file():
    assert normalized_digest(HOLDOUT.read_bytes()) == sealed_digest()
    assert SEAL.read_text(encoding="utf-8").split()[1] == HOLDOUT.name


def test_seal_ignores_line_endings_but_not_content():
    raw = HOLDOUT.read_bytes().replace(b"\r\n", b"\n")
    assert normalized_digest(raw.replace(b"\n", b"\r\n")) == sealed_digest()
    tampered = bytearray(raw)
    tampered[10] = ord("x") if tampered[10] != ord("x") else ord("y")
    assert normalized_digest(bytes(tampered)) != sealed_digest()


def test_shape_languages_and_categories():
    cases = rows()
    assert len(cases) >= 20
    assert sum(c["language"] == "pt" for c in cases) * 2 >= len(cases)
    assert {c["language"] for c in cases} == {"pt", "en"}
    assert {c["category"] for c in cases} == CATEGORIES
    for c in cases:
        assert set(c) == {"id", "category", "language", "question", "relevant_chunks"}, c["id"]
        grades = list(c["relevant_chunks"].values())
        # grade 2: the passage carries the whole answer (two chunks may, after the label review of round 2);
        # grade 1: it carries part of it
        assert grades.count(2) >= 1 and set(grades) <= {1, 2}, c["id"]


def test_labels_point_to_chunks_of_the_versioned_corpus():
    chunk_ids = {c.chunk_id for d in load_all(ROOT / "data") for c in chunk_document(d)}
    for c in rows():
        assert set(c["relevant_chunks"]) <= chunk_ids, c["id"]


def test_ids_and_questions_are_new():
    def norm(text: str) -> str:
        return " ".join(text.casefold().split())

    others: list[dict] = []
    for path in sorted(SCENARIOS.glob("*.jsonl")):
        if path != HOLDOUT:
            others += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    seen = {norm(row[key]) for row in others for key in ("message", "question") if key in row}
    cases = rows()
    assert len({c["id"] for c in cases}) == len(cases)
    assert not {c["id"] for c in cases} & {row["id"] for row in others}
    assert not {norm(c["question"]) for c in cases} & seen


def test_no_other_test_reads_the_holdout():
    """Development tests measure the modes on `retrieval.jsonl` or on synthetic sets, never on this file."""
    here = Path(__file__).resolve()
    readers = [
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "tests").rglob("*.py")
        if p.resolve() != here and "retrieval_holdout_v090" in p.read_text(encoding="utf-8")
    ]
    assert readers == []
