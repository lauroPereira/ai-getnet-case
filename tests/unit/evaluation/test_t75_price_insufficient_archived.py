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


# --- Round 2 (review P2-75): honest caveats are not contradictions ---------------------------------------------------

RSQUO = "’"  # typographic apostrophe, as the model often writes it
HONEST_CAVEATS = {
    "V030-PRICE-INSUFFICIENT": [
        f"There is no recorded charge, so I couldn{RSQUO}t confirm whether the fee was charged correctly.",
        "This does not mean the fee is incorrect.",
        f"This doesn{RSQUO}t mean that the fee is wrong.",
        "The comparison does not establish that the fee is incorrect.",
        "There is no indication that the fee is incorrect.",
        f"I can{RSQUO}t tell whether the fee is wrong.",
        "I cannot tell whether there is a fee discrepancy.",
        "If the fee is incorrect, I can hand this off to an attendant.",
    ],
    "V030-PT-PRICE-INSUFFICIENT": [
        "Isso não significa que a taxa está incorreta.",
        "Sem regra aplicável, não é possível afirmar que há divergência na taxa.",
        "Não há como saber se a taxa está correta.",
        "Não é possível confirmar se a taxa cobrada está correta.",
        "Não é possível confirmar que a taxa está correta.",
        "Não há indicação de que a taxa está errada.",
        "Não sabemos se a taxa cobrada está incorreta.",
    ],
}
QUALIFIED_THEN_CLAIMED = {
    "V030-PRICE-INSUFFICIENT": [
        f"I couldn{RSQUO}t find the rule. The fee is wrong.",
        "This does not mean anything, the fee is correct.",
        "Pricing did not show any problem and the fee is correct.",
        "There is no indication of a problem and the fee is correct.",
        "This does not mean the fee is incorrect — the fee is correct.",
        "If anything, the fee is correct.",
    ],
    "V030-PT-PRICE-INSUFFICIENT": [
        "Isso não significa nada e a taxa está correta.",
        "Não há indício de erro e a taxa está correta.",
        "Isso não significa que a taxa está incorreta; a taxa está correta.",
        "Não há como saber, mas a taxa está errada.",
    ],
}


@pytest.mark.parametrize(
    ("request_id", "caveat"),
    [(request_id, caveat) for request_id, case_id in R4_FALSE_NEGATIVES.items() for caveat in HONEST_CAVEATS[case_id]],
)
def test_honest_caveat_appended_to_an_accepted_answer_passes_every_check(request_id: str, caveat: str):
    row = {row["request_id"]: row for row in _archived("v080-healthy-r4.json")}[request_id]
    checks = _recheck(_cases()[row["id"]], row, f"{row['answer']} {caveat}")
    assert all(checks[key] for key in CHECK_KEYS), (request_id, caveat, checks)


@pytest.mark.parametrize(
    ("case_id", "caveat"),
    [(case_id, text) for case_id, texts in HONEST_CAVEATS.items() for text in texts],
)
def test_honest_caveat_alone_is_not_a_forbidden_assertion(case_id: str, caveat: str):
    row = next(row for row in _archived("v080-healthy-r4.json") if row["id"] == case_id)
    assert _recheck(_cases()[case_id], row, caveat)["forbidden_ok"], caveat


@pytest.mark.parametrize(
    ("case_id", "answer"),
    [(case_id, text) for case_id, texts in QUALIFIED_THEN_CLAIMED.items() for text in texts],
)
def test_a_qualifier_does_not_cover_a_later_claim(case_id: str, answer: str):
    row = next(row for row in _archived("v080-healthy-r4.json") if row["id"] == case_id)
    assert not _recheck(_cases()[case_id], row, answer)["forbidden_ok"], answer


@pytest.mark.parametrize(
    ("case_id", "contradiction"),
    [(case_id, text.replace("'", RSQUO)) for case_id, texts in CONTRADICTIONS.items() for text in texts],
)
def test_contradictions_are_still_rejected_after_apostrophe_normalization(case_id: str, contradiction: str):
    row = next(row for row in _archived("v080-healthy-r4.json") if row["id"] == case_id)
    assert not _recheck(_cases()[case_id], row, contradiction)["forbidden_ok"], contradiction


def test_a_typographic_apostrophe_matches_the_straight_one_in_every_label_kind():
    case = _cases()["V030-PRICE-INSUFFICIENT"]
    row = next(row for row in _archived("v080-healthy-r4.json") if row["id"] == case.id)
    # "couldn't compare its fee" is a must_include_any form written with a straight apostrophe
    assert _recheck(case, row, f"I couldn{RSQUO}t compare its fee.")["content_ok"]
    banned = Case(**{**case.__dict__, "must_not_include": ["merchant's id"]})
    assert not _recheck(banned, row, f"There is insufficient evidence. The merchant{RSQUO}s ID is 1.")["forbidden_ok"]


# --- Round 3 (review P3-R2a, P3-R2b): adjacency of the new forms, dash boundary, "don't know whether" ----------------

LSQUO, MODIFIER_APOSTROPHE, EM_DASH, EN_DASH = "‘", "ʼ", "—", "–"
# The five reproductions of P3-R2a and their siblings: a qualifier that is not directly followed by the assertion
# does not cover a claim joined later in the same clause by "and/e/porque/senão que".
QUALIFIER_NOT_ADJACENT = {
    "V030-PRICE-INSUFFICIENT": [
        "It is not possible to establish that there was a problem and the fee is correct.",
        "It is unclear whether you saw it and the fee is correct.",
        f"I don{RSQUO}t know whether you saw it and the fee is correct.",
        "The system does not know whether you saw it and the fee is correct.",
        "I can't say that there was a problem and the fee is correct.",
        "I am not sure that there was a problem and the fee is correct.",
    ],
    "V030-PT-PRICE-INSUFFICIENT": [
        "Não é possível afirmar que houve erro e a taxa está correta.",
        "Não posso afirmar outra coisa senão que a taxa está correta.",
        "Não podemos dizer que houve falha porque a taxa está correta.",
        "Não posso dizer que houve falha porque a taxa está correta.",
        "Não sabemos se você viu e a taxa está correta.",
    ],
}
# Honest caveats in the forms of round 2, with the three apostrophes, still accepted with adjacency.
HONEST_CAVEATS_ADJACENT = {
    "V030-PRICE-INSUFFICIENT": [
        f"I don{RSQUO}t know whether the fee is correct.",
        f"I don{LSQUO}t know whether the fee is correct.",
        f"The system doesn{MODIFIER_APOSTROPHE}t know whether the fee is correct.",
        "We do not know if the fee is wrong.",
        "It is unclear whether the fee is correct.",
        "It is unclear if the fee is incorrect.",
        "It is not possible to establish that the fee is correct.",
        "There is no way to know whether the fee was charged correctly.",
        f"I wasn{RSQUO}t able to verify that the fee is correct.",
        f"I can{LSQUO}t say that the fee is correct.",
        f"This doesn{MODIFIER_APOSTROPHE}t establish that the fee is wrong.",
        "There is no evidence that the fee is correct.",
        "I am not sure that the fee is correct.",
    ],
    "V030-PT-PRICE-INSUFFICIENT": [
        "Não é possível afirmar que a taxa está correta.",
        "Não podemos afirmar que a taxa está correta.",
        "Não posso dizer que a taxa está correta.",
        "Não posso afirmar se a taxa está correta.",
        "Não há como saber se a taxa está correta.",
        "Não se sabe se a taxa está incorreta.",
        "Não temos certeza se a taxa cobrada está correta.",
        "Isso não significa que a taxa está errada.",
        "Não há evidência de que a taxa está correta.",
    ],
}
# A dash (U+2013, U+2014) ends the clause, so a doubt form with its window does not reach a claim after it.
CLAIM_AFTER_A_DASH = {
    "V030-PRICE-INSUFFICIENT": [
        f"I cannot confirm whether the rule applies {EM_DASH} the fee is correct.",
        f"I am not sure whether the rule applies {EN_DASH} the fee is wrong.",
    ],
    "V030-PT-PRICE-INSUFFICIENT": [
        f"Não sei se a regra se aplica {EN_DASH} a taxa está correta.",
        f"Não consigo confirmar se a regra vale {EM_DASH} a taxa está errada.",
    ],
}


def _row(case_id: str) -> dict:
    return next(row for row in _archived("v080-healthy-r4.json") if row["id"] == case_id)


@pytest.mark.parametrize(
    ("case_id", "answer"),
    [(case_id, text) for case_id, texts in QUALIFIER_NOT_ADJACENT.items() for text in texts]
    + [(case_id, text) for case_id, texts in CLAIM_AFTER_A_DASH.items() for text in texts],
)
def test_a_qualifier_not_directly_before_the_claim_does_not_cover_it(case_id: str, answer: str):
    assert not _recheck(_cases()[case_id], _row(case_id), answer)["forbidden_ok"], answer


@pytest.mark.parametrize(
    ("case_id", "caveat"),
    [(case_id, text) for case_id, texts in HONEST_CAVEATS_ADJACENT.items() for text in texts],
)
def test_an_honest_caveat_directly_before_the_assertion_is_still_accepted(case_id: str, caveat: str):
    assert _recheck(_cases()[case_id], _row(case_id), caveat)["forbidden_ok"], caveat


def test_the_dash_is_what_ends_the_clause_in_the_dash_probes():
    case_id = "V030-PRICE-INSUFFICIENT"
    for text in CLAIM_AFTER_A_DASH[case_id]:
        # without the dash the claim falls inside the pre-v0.8.0 doubt window (a known limit), so the dash is what
        # rejects the probes above
        joined = text.replace(f" {EM_DASH} ", " and ").replace(f" {EN_DASH} ", " and ")
        assert _recheck(_cases()[case_id], _row(case_id), joined)["forbidden_ok"], joined
