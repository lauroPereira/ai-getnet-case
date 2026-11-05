"""Task 78: offline re-evaluation of archived real answers for the six CA-51 journeys rejected only by wording.

The archived runs are read only; the rubric is the runner's own `_checks`, the function that produced `content_ok`
and `passed` in the campaign. No model, network or ledger is involved.
"""

from __future__ import annotations

import json

import pytest

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation.runner import CHECK_KEYS, Case, _checks, load_cases

EVIDENCE = PROJECT_ROOT / "docs" / "evidence"
JOURNEYS = PROJECT_ROOT / "tests" / "scenarios" / "business_journeys.jsonl"
ARCHIVES = ("v080-all-r3.json", "v080-healthy-r4.json", "v080-healthy-r5.json")

# The ten r5 answers QA marked as correct-but-rejected by content_ok alone (task 78).
R5_FALSE_NEGATIVES = {
    "req_eval531ac9146987": "V030-PRICE-DIVERGENCE",
    "req_evalb84c1106aea3": "V030-PRICE-DIVERGENCE",
    "req_eval9a0b07470114": "V030-PRICE-DIVERGENCE",
    "req_eval64b06f9b7f24": "V030-PRICE-CONDITIONS",
    "req_eval45e5804e758a": "V030-PT-PRICE-CONDITIONS",
    "req_eval3180af09b4e0": "V030-PRICE-INSUFFICIENT",
    "req_evalb8354030edbd": "V030-PRICE-INSUFFICIENT",
    "req_evalaf77a604682c": "V030-PT-PRICE-INSUFFICIENT",
    "req_eval025b4ed82d6f": "V030-PT-PRICE-INSUFFICIENT",
    "req_eval932e426373de": "V030-SALE-CANCELLATION",
}
# r4 answers that failed before task 78 and must keep failing: the dated journeys ran with an invalid environment
# (the sales of "yesterday" did not exist; QA r4/r5), so the new forms must not accept their "no sale found" answers,
# and CONTRACT-TERMINATION rep. 1 is the routing defect of task 76.
R4_INVALID_ENVIRONMENT_BY_JOURNEY = {
    "V030-PRICE-CONSISTENT": ("req_eval3a9ff9e7f6f1", "req_evalf2fa735fe491", "req_evald33968d3b97f"),
    "V030-PRICE-CONDITIONS": ("req_eval96bad0059232", "req_eval728020fd0838", "req_evalbf4272972688"),
    "V030-PRICE-DIVERGENCE": ("req_eval9527e981f2a7", "req_eval19c76e4906e6", "req_evaldec0aaa9fe58"),
    "V030-SALE-CANCELLATION": ("req_evalc5e4e9aa92d8", "req_eval3795e92d75c6", "req_eval33249c0e4b19"),
    "V030-CONTRACT-TERMINATION": ("req_eval35a095aa8794",),
    "V030-PT-PRICE-CONSISTENT": ("req_eval5cc371e819f7", "req_eval53aa5d93f500", "req_eval9106866e3524"),
    "V030-PT-PRICE-CONDITIONS": ("req_eval2f96df74b3df", "req_eval7c9593e5cf35", "req_evalc8e9ccda0638"),
    "V030-PT-PRICE-DIVERGENCE": ("req_evale2fee9200167", "req_eval65c3501509c7", "req_eval9a688ad14ac0"),
    "V030-PT-SALE-CANCELLATION": ("req_evalde36098ee067", "req_evala65f86ad4484", "req_evalfc5851d4fbfb"),
}
R4_INVALID_ENVIRONMENT = {rid for ids in R4_INVALID_ENVIRONMENT_BY_JOURNEY.values() for rid in ids}


def _cases() -> dict[str, Case]:
    return {case.id: case for case in load_cases([JOURNEYS])}


def _archived(name: str) -> list[dict]:
    ids = _cases().keys()
    rows = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))["cases"]
    return [row for row in rows if row["id"] in ids]


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


def _passed(case: Case, row: dict, answer: str | None = None) -> bool:
    checks = _recheck(case, row, answer)
    return all(checks[key] for key in CHECK_KEYS)


def _r5_row(request_id: str) -> dict:
    return next(row for row in _archived("v080-healthy-r5.json") if row["request_id"] == request_id)


# --- (a) the ten r5 false negatives ---------------------------------------------------------------------------------


@pytest.mark.parametrize(("request_id", "case_id"), sorted(R5_FALSE_NEGATIVES.items()))
def test_the_ten_r5_false_negatives_now_pass_every_deterministic_check(request_id: str, case_id: str):
    row = _r5_row(request_id)
    assert row["id"] == case_id and row["content_ok"] is False and row["passed"] is False  # archived verdict
    assert all(row[key] for key in CHECK_KEYS if key != "content_ok")  # only content_ok failed in the campaign
    checks = _recheck(_cases()[case_id], row)
    assert all(checks[key] for key in CHECK_KEYS), (request_id, checks)


# --- (b) no archived answer of the 13 journeys regresses -------------------------------------------------------------


@pytest.mark.parametrize("archive", ARCHIVES)
def test_every_archived_journey_answer_passes_except_the_invalid_r4_environment(archive: str):
    cases = _cases()
    rows = _archived(archive)
    assert len(rows) == {"v080-all-r3.json": 39, "v080-healthy-r4.json": 39, "v080-healthy-r5.json": 33}[archive]
    for row in rows:
        if row["request_id"] in R4_INVALID_ENVIRONMENT:
            assert row["request_id"] in R4_INVALID_ENVIRONMENT_BY_JOURNEY[row["id"]] and not row["passed"]
        expected = row["request_id"] not in R4_INVALID_ENVIRONMENT
        assert _passed(cases[row["id"]], row) is expected, (archive, row["request_id"])


def test_every_answer_the_campaign_passed_still_passes():
    cases = _cases()
    archived_passes = [row for archive in ARCHIVES for row in _archived(archive) if row["passed"]]
    assert len(archived_passes) == 63
    for row in archived_passes:
        assert _passed(cases[row["id"]], row), row["request_id"]


def test_the_new_forms_do_not_accept_the_invalid_r4_cancellation_answers():
    case = _cases()["V030-SALE-CANCELLATION"]
    rows = [row for row in _archived("v080-healthy-r4.json") if row["id"] == case.id]
    assert len(rows) == 3
    for row in rows:  # "No cancellation records were found ..."
        checks = _recheck(case, row)
        assert not checks["content_ok"] and not checks["forbidden_ok"], row["request_id"]


# --- (c) contradictions are rejected (EN and PT) ---------------------------------------------------------------------

CONTRADICTIONS = {
    "V030-PRICE-DIVERGENCE": [
        "There is no divergence.",
        "There is no difference.",
        "The comparison found no difference.",
        "The comparison has not found a difference.",
        f"The comparison didn{chr(0x2019)}t find a difference.",
        "The comparison does not show a difference.",
        "The fee matched the pricing rule.",
        "The recorded charge matches the pricing rule.",
        "The recorded charge is the same.",
        "The fee is correct.",
        "The fee was charged correctly.",
    ],
    "V030-PRICE-CONDITIONS": [
        "The conditions were the same.",
        "The charge used the same pricing plan.",
        "The same plan was used.",
        "The plans are the same.",
        "The conditions did not differ.",
        "The charge did not use different pricing plans.",
        "There is no difference in pricing conditions.",
        "The plans were not different.",
        "The fee is correct.",
        "The fee is incorrect.",
        "The fee is wrong.",
    ],
    "V030-PT-PRICE-CONDITIONS": [
        "As condições são iguais.",
        "Foram usadas as mesmas condições.",
        "A cobrança usou o mesmo plano.",
        "Não há diferença entre as condições.",
        "Nenhuma diferença entre as condições foi encontrada.",
        "Os planos são iguais.",
        "A taxa está correta.",
        "A taxa está incorreta.",
        "A taxa cobrada está errada.",
        "A cobrança está incorreta.",
    ],
    "V030-PRICE-INSUFFICIENT": [
        "There is sufficient evidence to compare the fee.",
        "There is enough evidence to compare the fee.",
        "The fee is correct.",
        "The fee is incorrect.",
        "The fee was charged incorrectly.",
        "There is a fee divergence.",
    ],
    "V030-PT-PRICE-INSUFFICIENT": [
        "As evidências são suficientes para comparar a taxa.",
        "A evidência é suficiente para comparar.",
        "A taxa está correta.",
        "A taxa está incorreta.",
        "Não há divergência na taxa.",
    ],
    "V030-SALE-CANCELLATION": [
        "The cancellation has been processed.",
        "The cancellation was completed.",
        "Yesterday's sale has been cancelled.",
        "The sale was canceled.",
        "The request was rejected.",
        "The cancellation is marked as completed.",
        "There is no request to cancel yesterday's sale.",
        "No cancellation records were found.",
        "The sale cancellation was not requested.",
        "The cancellation is not marked as requested.",
    ],
}


@pytest.mark.parametrize(
    ("request_id", "contradiction"),
    [
        (request_id, contradiction)
        for request_id, case_id in sorted(R5_FALSE_NEGATIVES.items())
        for contradiction in CONTRADICTIONS[case_id]
    ],
)
def test_contradiction_appended_to_an_accepted_answer_is_rejected(request_id: str, contradiction: str):
    row = _r5_row(request_id)
    checks = _recheck(_cases()[row["id"]], row, f"{row['answer']} {contradiction}")
    assert checks["content_ok"]  # the accepted wording is still there
    assert not checks["forbidden_ok"], (request_id, contradiction)


@pytest.mark.parametrize(
    ("case_id", "contradiction"),
    [(case_id, text) for case_id, texts in CONTRADICTIONS.items() for text in texts],
)
def test_contradiction_alone_fails_the_rubric(case_id: str, contradiction: str):
    row = next(row for row in _archived("v080-healthy-r5.json") if row["id"] == case_id)
    checks = _recheck(_cases()[case_id], row, contradiction)
    assert not checks["forbidden_ok"], (case_id, contradiction)
    assert not all(checks[key] for key in CHECK_KEYS)


# Each new acceptance form, negated or reversed, is rejected even when the form itself is still in the text.
NEGATED_NEW_FORMS = {
    "V030-PRICE-DIVERGENCE": [
        "The comparison has not found a difference.",
        f"We haven{chr(0x2019)}t found a difference.",
        "The rule doesn't show a difference.",
        "The rule shows a fee of R$ 0,75, but the recorded charge is R$ 0,75 too: the recorded charge is the same.",
    ],
    "V030-PRICE-CONDITIONS": ["The charge didn't use different pricing plans."],
    "V030-PT-PRICE-CONDITIONS": ["Não há diferença entre as condições.", "Sem diferença entre as condições."],
    "V030-SALE-CANCELLATION": [
        "There is no request to cancel, so it has not been processed.",
        f"I couldn{chr(0x2019)}t find a request to cancel, so it has not been processed.",
        "Your request to cancel has not been processed because the cancellation was rejected.",
    ],
}


@pytest.mark.parametrize(
    ("case_id", "answer"),
    [(case_id, text) for case_id, texts in NEGATED_NEW_FORMS.items() for text in texts],
)
def test_a_negated_new_form_is_rejected(case_id: str, answer: str):
    row = next(row for row in _archived("v080-healthy-r5.json") if row["id"] == case_id)
    assert not _passed(_cases()[case_id], row, answer), answer


def test_request_to_cancel_alone_is_not_enough_for_the_cancellation_journey():
    # "requested" alone is still accepted (as before); "request to cancel" needs "not (been) processed" with it.
    case = _cases()["V030-SALE-CANCELLATION"]
    row = _r5_row("req_eval932e426373de")
    assert not _recheck(case, row, "Your request to cancel yesterday's sale has been received.")["content_ok"]
    assert _recheck(case, row, "Your request to cancel yesterday's sale has not been processed yet.")["content_ok"]
    assert _recheck(case, row, "Yesterday's sale cancellation is marked as requested.")["content_ok"]


# --- (d) CA-51 recomputed offline on the r5 composition --------------------------------------------------------------


def test_ca51_recomputed_on_the_r5_composition_reaches_at_least_12_of_13_in_every_repetition():
    cases = _cases()
    assert len(cases) == 13
    r5 = _archived("v080-healthy-r5.json")
    r4_enablement = [row for row in _archived("v080-healthy-r4.json") if "ENABLEMENT-PENDING" in row["id"]]
    composition = r5 + r4_enablement
    assert {row["id"] for row in composition} == set(cases)
    for repetition in (1, 2, 3):
        rows = [row for row in composition if row["repetition"] == repetition]
        assert len(rows) == 13
        approved = sum(_passed(cases[row["id"]], row) for row in rows)
        archived = sum(row["passed"] for row in rows)
        assert archived == {1: 11, 2: 8, 3: 10}[repetition]  # the campaign verdict (QA r5)
        assert approved == 13, (repetition, approved)
