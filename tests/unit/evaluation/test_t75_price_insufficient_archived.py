"""Task 75: offline re-evaluation of archived real answers for the PRICE-INSUFFICIENT journeys (EN and PT).

The archived runs are read only; the rubric is the runner's own `_checks`, the function that produced `content_ok`
in the campaign. No model, network or ledger is involved.
"""

from __future__ import annotations

import json

import pytest

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation.runner import CHECK_KEYS, Case, _checks, load_cases

EVIDENCE = PROJECT_ROOT / "docs" / "evidence"
JOURNEYS = PROJECT_ROOT / "tests" / "scenarios" / "business_journeys.jsonl"
IDS = ("V030-PRICE-INSUFFICIENT", "V030-PT-PRICE-INSUFFICIENT")
# The four answers QA r4 marked as correct-but-rejected (task 75).
R4_FALSE_NEGATIVES = {
    "req_evalbccfe360ff22": "V030-PRICE-INSUFFICIENT",
    "req_evaldf38c4d80b5e": "V030-PRICE-INSUFFICIENT",
    "req_evale8ee4429374a": "V030-PT-PRICE-INSUFFICIENT",
    "req_eval51b2a1d763e0": "V030-PT-PRICE-INSUFFICIENT",
}


def _cases() -> dict[str, Case]:
    return {case.id: case for case in load_cases([JOURNEYS])}


def _archived(name: str) -> list[dict]:
    rows = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))["cases"]
    return [row for row in rows if row["id"] in IDS]


def _recheck(case: Case, row: dict, answer: str | None = None) -> dict:
    body = {
        "answer": row["answer"] if answer is None else answer,
        "route": row["route"],
        "status": row["status"],
        "language": row["language"],
        "sources": row["sources"],
    }
    trace = {
        "steps": [{"step": f"tool:{tool}"} for tool in row["tools_called"]],
        "detail": {"output_violations": row["violations"]},
    }
    return _checks(case, body, trace)


def test_the_four_r4_false_negatives_now_pass_every_deterministic_check():
    cases = _cases()
    rows = {row["request_id"]: row for row in _archived("v080-healthy-r4.json")}
    for request_id, case_id in R4_FALSE_NEGATIVES.items():
        row = rows[request_id]
        assert row["id"] == case_id and row["content_ok"] is False  # archived verdict before the label fix
        checks = _recheck(cases[case_id], row)
        assert all(checks[key] for key in CHECK_KEYS), (request_id, checks)


@pytest.mark.parametrize("archive", ["v080-healthy-r4.json", "v080-all-r3.json"])
def test_no_archived_r3_or_r4_answer_for_these_journeys_regresses(archive: str):
    cases = _cases()
    rows = _archived(archive)
    assert len(rows) == 6
    for row in rows:
        checks = _recheck(cases[row["id"]], row)
        assert all(checks[key] for key in CHECK_KEYS), (row["request_id"], checks)


CONTRADICTIONS = {
    "V030-PRICE-INSUFFICIENT": [
        "The fee is correct.",
        "The fee is incorrect.",
        "The fee is wrong.",
        "The fee was confirmed.",
        "The fee was charged correctly.",
        "The fee diverges from the pricing rule.",
        "There is a fee discrepancy.",
        "There is a fee divergence.",
    ],
    "V030-PT-PRICE-INSUFFICIENT": [
        "A taxa está correta.",
        "A taxa está incorreta.",
        "A taxa está errada.",
        "A taxa foi confirmada.",
        "A taxa cobrada está correta.",
        "A taxa cobrada está incorreta.",
        "A taxa diverge da regra.",
        "Há divergência na taxa.",
        "Não há divergência na taxa.",
    ],
}


@pytest.mark.parametrize(
    ("request_id", "contradiction"),
    [
        (request_id, contradiction)
        for request_id, case_id in R4_FALSE_NEGATIVES.items()
        for contradiction in CONTRADICTIONS[case_id]
    ],
)
def test_contradiction_appended_to_an_accepted_answer_is_rejected(request_id: str, contradiction: str):
    row = {row["request_id"]: row for row in _archived("v080-healthy-r4.json")}[request_id]
    case = _cases()[row["id"]]
    checks = _recheck(case, row, f"{row['answer']} {contradiction}")
    assert checks["content_ok"]  # the accepted wording is still there
    assert not checks["forbidden_ok"], (request_id, contradiction)


@pytest.mark.parametrize(
    ("case_id", "contradiction"),
    [(case_id, text) for case_id, texts in CONTRADICTIONS.items() for text in texts],
)
def test_contradiction_alone_fails_the_rubric(case_id: str, contradiction: str):
    row = next(row for row in _archived("v080-healthy-r4.json") if row["id"] == case_id)
    checks = _recheck(_cases()[case_id], row, contradiction)
    assert not checks["content_ok"] and not checks["forbidden_ok"], checks
