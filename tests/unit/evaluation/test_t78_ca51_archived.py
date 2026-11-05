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
    # "requested" alone is still accepted (as before); "request to cancel" needs both "received" and
    # "not (been) processed" with it (review round 1, P2-1).
    case = _cases()["V030-SALE-CANCELLATION"]
    row = _r5_row("req_eval932e426373de")
    assert not _recheck(case, row, "Your request to cancel yesterday's sale has been received.")["content_ok"]
    assert not _recheck(case, row, "Your request to cancel yesterday's sale has not been processed yet.")["content_ok"]
    received_not_processed = "Your request to cancel yesterday's sale has been received, but it has not been processed."
    assert _passed(case, row, received_not_processed)
    assert _recheck(case, row, "Yesterday's sale cancellation is marked as requested.")["content_ok"]


# --- (c2) review round 1 probes (P2-1 to P2-4, P3-1): alone and appended to every accepted answer -------------------

RSQ = chr(0x2019)
REVIEW_PROBES = {
    "V030-SALE-CANCELLATION": [  # P2-1
        "Your request to cancel yesterday's sale was rejected, so it has not been processed.",
        "Your request to cancel yesterday's sale was denied, so it has not been processed.",
        "Your request to cancel yesterday's sale was declined, so it has not been processed.",
        "Your request to cancel yesterday's sale was refused, so it has not been processed.",
        "The status of your request to cancel yesterday's sale is unknown, so it has not been processed.",
        "There isn't a request to cancel yesterday's sale, so it has not been processed.",
        f"There isn{RSQ}t a request to cancel yesterday{RSQ}s sale, so it has not been processed.",
        "There is not a request to cancel yesterday's sale, so it has not been processed.",
        "We have no record of a request to cancel yesterday's sale, so it has not been processed.",
        "Your request to cancel yesterday's sale has been received, but it was rejected and has not been processed.",
        "Your request to cancel yesterday's sale has not been received, so it has not been processed.",
        f"Your request to cancel yesterday{RSQ}s sale wasn{RSQ}t received, so it has not been processed.",
        "Your request to cancel yesterday's sale was not received, so it has not been processed.",
        "Your request to cancel yesterday's sale was not yet received, so it has not been processed.",
        "Your request to cancel yesterday's sale has not yet been received, so it has not been processed.",
        "Your request to cancel yesterday's sale hasn't been received, so it has not been processed.",
        "Your request to cancel yesterday's sale hasn't yet been received, so it has not been processed.",
        "We haven't yet received a request to cancel yesterday's sale, so it has not been processed.",
        "There are no records of a request to cancel yesterday's sale, so it has not been processed.",
        "Your request to cancel has been received; its status is not known and it has not been processed.",
        # P2-5 (review round 2): the bare prohibitions became assertions (see CANCELLATION_STATE_PROBES below).
        "Your request to cancel has been received; its status: unknown. It has not been processed.",
        "Your request to cancel has been received, but its status is unknown and it has not been processed.",
        "Your request to cancel has been received; it shows status unknown and has not been processed.",
        "Your request to cancel has been received; its status remains unknown and it has not been processed.",
        "We have no record of the request to cancel yesterday's sale, so it has been received but not processed.",
        "We have no record of your request to cancel yesterday's sale; it has been received but not processed.",
        "We have no record of any request to cancel yesterday's sale; it has not been processed.",
        "There are no records of the request to cancel yesterday's sale; it has been received but not processed.",
        "There are no records of your request to cancel yesterday's sale; it has been received but not processed.",
        "There are no records of any request to cancel yesterday's sale; it has not been processed.",
        # P3-9 (review round 2): cheap additions.
        "Your request to cancel the sale has been received, but it was not approved and has not been processed.",
        "Your request to cancel the sale has been received, but it wasn't approved and has not been processed.",
        "Your request to cancel the sale has been received, but it was not accepted and has not been processed.",
        f"Your request to cancel yesterday's sale has been received, but it wasn{RSQ}t accepted, so not processed.",
        "Your request to cancel the sale has been received and has not been processed, and it won't be processed.",
        "Your request to cancel the sale has been received; it has not been processed and will not be processed.",
        "Your request to cancel yesterday's sale has been received but has not been processed: it cannot be processed.",
        "Your request to cancel yesterday's sale has been received but has not been processed: it can't be processed.",
    ],
    "V030-PRICE-CONDITIONS": [  # P2-2
        "No different pricing plans were used.",
        "Different pricing plans were not used.",
        "The charge wasn't made under different pricing plans.",
        "The charge was not made under different pricing plans.",
        "There were no different pricing plans.",
        "The charge and expected conditions never used different pricing plans.",
        "The charge and expected conditions have not used different pricing plans.",
        "Different pricing plans weren't used.",
        "Different plans were not used.",
        "Different plans weren't used.",
        "Different conditions were not used.",
        "Different conditions weren't used.",
        # P2-6 (review round 2): contractions of "have not used".
        "The charge and expected conditions haven't used different pricing plans.",
        f"The charge hasn{RSQ}t used different pricing plans.",
        "The charge wouldn't have used different pricing plans.",
        "The charge would not have used different pricing plans.",
        # P3-6 (review round 2): "no different" is bound to the plans and conditions.
        "The charge had no different pricing plans.",
        "There were no different plans.",
        "There were no different conditions.",
        "The plans were no different.",
        "The conditions were no different.",
    ],
    "V030-PT-PRICE-CONDITIONS": [  # P2-3
        "Não encontrei diferença entre as condições.",
        "Não identifiquei diferença entre as condições.",
        "Não vejo diferença entre as condições.",
        "Não constatei diferença entre as condições.",
        "Não foi encontrada diferença entre as condições.",
        "Não há diferença entre as condições.",
        "Não encontrei diferença.",
        "Não foi encontrada diferença.",
        "Não há diferença.",
        "Não encontrei essa diferença entre as condições.",
        "Não há essa diferença entre as condições.",
        "Nenhuma diferença foi encontrada.",
        "A cobrança foi feita sem diferença de condições.",
        "Não houve diferença entre as condições.",
        "Não existe diferença entre as condições.",
        "Não há qualquer diferença entre as condições.",
        "Não foi identificada diferença entre as condições.",
        "Não foi constatada diferença entre as condições.",
        "Não foram encontradas diferenças entre as condições.",
        "Não foram identificadas diferenças entre as condições.",
        "Não houve essa diferença entre as condições.",
        "Não existe essa diferença entre as condições.",
        "Não identifiquei essa diferença entre as condições.",
        "Não vejo essa diferença entre as condições.",
        "Não constatei essa diferença entre as condições.",
        # P3-6 (review round 2): "não há / nenhuma / sem diferença" are bound to the conditions and plans.
        "Não há diferença entre os planos.",
        "Não há diferença nas condições.",
        "Não há diferença de condições.",
        "Nenhuma diferença entre os planos.",
        "Nenhuma diferença nas condições.",
        "Nenhuma diferença de condições foi encontrada.",
        "A cobrança foi feita sem diferença entre as condições.",
        "A cobrança foi feita sem diferença entre os planos.",
        "A cobrança foi feita sem diferença nas condições.",
        "Nenhuma diferença foi identificada.",
    ],
    "V030-PRICE-DIVERGENCE": [  # P2-4 and P3-1
        "The pricing rule shows a fee of R$ 0,75, but the recorded charge is R$ 0,75.",
        "The pricing rule shows a fee of R$ 0,75, but the recorded charge was R$ 0,75.",
        "The rule doesn't show a difference.",
        f"The rule doesn{RSQ}t show a difference.",
        "The comparison didn't show a difference.",
    ],
}
# P2-5 (review round 2): "rejected", "denied", "declined" and "refused" are prohibited only as an asserted state of the
# request; one probe per bound form, each matching that form alone.
CANCELLATION_STATES = ("rejected", "denied", "declined", "refused")
CANCELLATION_STATE_TEMPLATES = (
    "Your request to cancel yesterday's sale has been received, but it has been {state} and has not been processed.",
    "Your request to cancel yesterday's sale has been received, but it had been {state} and has not been processed.",
    "Your request to cancel the sale has been received, but it has already been {state} and has not been processed.",
    "Your request to cancel yesterday's sale has been received, but it was {state} and has not been processed.",
    "Your request to cancel yesterday's sale has been received, but it is {state} and has not been processed.",
    "Your request to cancel yesterday's sale has been received, but it got {state} and has not been processed.",
    "Your request to cancel yesterday's sale has been received and has not been processed. Status: {state}.",
    "Your request to cancel yesterday's sale has been received; it shows status {state} and has not been processed.",
    "Your request to cancel yesterday's sale has been received, is listed as {state}, and has not been processed.",
    "{State}: your request to cancel yesterday's sale has been received but has not been processed.",
)
CANCELLATION_STATE_PROBES = [
    template.format(state=state, State=state.capitalize())
    for state in CANCELLATION_STATES
    for template in CANCELLATION_STATE_TEMPLATES
]
REVIEW_PROBES["V030-SALE-CANCELLATION"] += sorted(set(CANCELLATION_STATE_PROBES))
# P2-7 (review round 3): contracted "has been", "it's", adverbs and the active voice; straight and typographic
# apostrophes (the runner compares both as "'"). One probe per bound form, each matching that form alone.
P2_7_STATE_TEMPLATES = (
    "Your request to cancel yesterday's sale has been received, but it's been {state} and has not been processed.",
    f"Your request to cancel yesterday{RSQ}s sale has been received, but it{RSQ}s been {{state}}, so not processed.",
    "Your request to cancel yesterday's sale has been received, but it's {state} and has not been processed.",
    f"Your request to cancel yesterday{RSQ}s sale has been received, but it{RSQ}s {{state}}, so not processed.",
    "Your request to cancel yesterday's sale has been received, but the request's {state}, so it is not processed.",
    "Your request to cancel yesterday's sale has been received, but the cancellation's {state}; not processed.",
    "Your request to cancel the sale has been received, but the sale's {state} and has not been processed.",
    "Your request to cancel yesterday's sale has been received, but it is now {state} and has not been processed.",
    "Your request to cancel yesterday's sale has been received, but it was later {state} and has not been processed.",
    "Your request to cancel yesterday's sale has been received, but it was then {state} and has not been processed.",
    "Your request to cancel yesterday's sale has been received, but it ended up {state} and has not been processed.",
    "Your request to cancel yesterday's sale has been received, but the bank {state} it, so it has not been processed.",
)
P2_7_PROBES = [template.format(state=state) for state in CANCELLATION_STATES for template in P2_7_STATE_TEMPLATES]
P2_7_PROBES += [
    "Your request to cancel yesterday's sale has been received, but its status is now denied and it is not processed.",
    "The status of your request to cancel is unknown; it has been received but has not been processed.",
    "The status of the sale cancellation is unknown; it was requested and has not been processed.",
    "The status of your request is unknown; it has been received but has not been processed.",
    # "concluído" additions: "has been completed", "is complete" and "been refunded" bound to an auxiliary.
    "Your request to cancel yesterday's sale has been received, and it has been completed.",
    "Your request to cancel yesterday's sale has been received, and the cancellation is complete.",
    "Your request to cancel yesterday's sale has been received; the amount has been refunded.",
    "Your request to cancel yesterday's sale has been received; the amounts have been refunded.",
    "Your request to cancel yesterday's sale has been received; the amount had been refunded.",
    "Your request to cancel yesterday's sale has been received; the amount has already been refunded.",
    f"Your request to cancel yesterday's sale has been received; the amount{RSQ}s been refunded.",
    "Your request to cancel yesterday's sale has been received; the amount was refunded.",
    "Your request to cancel yesterday's sale has been received; the amounts were refunded.",
]
REVIEW_PROBES["V030-SALE-CANCELLATION"] += P2_7_PROBES


@pytest.mark.parametrize(
    ("case_id", "probe"),
    [(case_id, text) for case_id, texts in REVIEW_PROBES.items() for text in texts],
)
def test_review_probe_alone_fails_the_rubric(case_id: str, probe: str):
    row = next(row for row in _archived("v080-healthy-r5.json") if row["id"] == case_id)
    assert not _passed(_cases()[case_id], row, probe), probe


@pytest.mark.parametrize(
    ("request_id", "probe"),
    [
        (request_id, probe)
        for request_id, case_id in sorted(R5_FALSE_NEGATIVES.items())
        for probe in REVIEW_PROBES.get(case_id, [])
    ],
)
def test_review_probe_appended_to_an_accepted_answer_is_rejected(request_id: str, probe: str):
    row = _r5_row(request_id)
    checks = _recheck(_cases()[row["id"]], row, f"{row['answer']} {probe}")
    assert checks["content_ok"]  # the accepted wording is still there
    assert not checks["forbidden_ok"], (request_id, probe)


# Correct pending wordings for the cancellation journey (review round 2, P2-5): the bare "rejected", "declined",
# "unknown" and "no record of" refused them; the bound forms do not.
CORRECT_PENDING_CANCELLATION = [
    "The cancellation of yesterday's sale was requested and has not been processed or rejected yet.",
    "The cancellation of yesterday's sale was requested; there is no record of it being completed.",
    "The sale cancellation was requested and is still pending: it has not been processed or rejected yet.",
    f"The cancellation of yesterday's sale was requested and hasn{RSQ}t been approved or declined yet.",
    "The cancellation of yesterday's sale was requested; it has not been rejected or processed.",
    "The cancellation of yesterday's sale was requested and hasn't been denied or refused.",
    "The cancellation of yesterday's sale was requested; it is unknown when it will be processed.",
    "The cancellation of yesterday's sale was requested; there is no record of a processed date.",
    # Review round 3 (P2-7): the bound forms still accept these.
    "The cancellation of yesterday's sale was requested; there is no record of the request being processed.",
    "The cancellation of yesterday's sale was requested and has neither been approved nor rejected.",
    "The cancellation of yesterday's sale was requested; it is not rejected and has not been processed.",
    "The cancellation of yesterday's sale was requested and has not been processed; we will tell you if it's rejected.",
    f"The cancellation of yesterday{RSQ}s sale was requested and not processed; you will be told if it{RSQ}s denied.",
    "The cancellation of yesterday's sale was requested; its processing date is unknown.",
    "The cancellation of yesterday's sale was requested; it has not been completed or refunded yet.",
    f"The cancellation of yesterday's sale was requested; it is not complete and hasn{RSQ}t been refunded.",
]


@pytest.mark.parametrize(
    ("request_id", "statement"),
    [
        # The negations of P2-2 are bound to "different ...": a correct remark about which plan was not used passes.
        ("req_eval64b06f9b7f24", "The expected conditions were not used for this charge."),
        ("req_eval64b06f9b7f24", "The demo_standard plan was not used for this charge."),
        ("req_eval932e426373de", "No processed date is shown."),
        # P3-6 (review round 2): "no different" and "não há / sem / nenhuma diferença" about other attributes pass.
        ("req_eval64b06f9b7f24", "The installments and channel were no different."),
        ("req_eval45e5804e758a", "Não há diferença no número de parcelas nem no canal."),
        ("req_eval45e5804e758a", "O canal e as parcelas ficaram sem diferença."),
        ("req_eval45e5804e758a", "Nenhuma diferença no número de parcelas."),
        *[("req_eval932e426373de", text) for text in CORRECT_PENDING_CANCELLATION],
    ],
)
def test_correct_statements_near_the_new_prohibitions_still_pass(request_id: str, statement: str):
    row = _r5_row(request_id)
    assert _passed(_cases()[row["id"]], row, f"{row['answer']} {statement}"), statement


@pytest.mark.parametrize("statement", CORRECT_PENDING_CANCELLATION)
def test_a_correct_pending_cancellation_wording_passes_alone(statement: str):
    row = _r5_row("req_eval932e426373de")
    assert _passed(_cases()["V030-SALE-CANCELLATION"], row, statement), statement


# P3-8 (review round 2): the narrowed acceptance forms. A wording with only the old, wider form
# ("different pricing plans", "diferença entre as condições") is no longer accepted.
NARROWING_PROBES = {
    "V030-PRICE-CONDITIONS": ["Different pricing plans were never applied."],
    "V030-PT-PRICE-CONDITIONS": ["Não detectamos diferença entre as condições."],
}


@pytest.mark.parametrize(
    ("case_id", "probe"),
    [(case_id, text) for case_id, texts in NARROWING_PROBES.items() for text in texts],
)
def test_a_wording_with_only_the_old_wider_form_fails(case_id: str, probe: str):
    row = next(row for row in _archived("v080-healthy-r5.json") if row["id"] == case_id)
    assert not _recheck(_cases()[case_id], row, probe)["content_ok"], probe


def test_the_divergence_form_is_bound_to_the_case_amounts():
    # P2-4: "but the recorded charge is R$" alone is no longer a form; only the case's R$ 0,00 x R$ 0,75 divergence.
    case = _cases()["V030-PRICE-DIVERGENCE"]
    row = _r5_row("req_evalb84c1106aea3")
    forms = [form for group in case.must_include_any for form in group]
    assert "but the recorded charge is R$" not in forms and "but the recorded charge was R$" not in forms
    assert _recheck(case, row, "The rule shows R$ 0,00, but the recorded charge is R$ 0,75.")["content_ok"]
    assert not _recheck(case, row, "The rule shows R$ 0,50, but the recorded charge is R$ 0,75.")["content_ok"]


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
