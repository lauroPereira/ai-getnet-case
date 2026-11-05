from __future__ import annotations

from pathlib import Path

import pytest

from merchant_assistant.evaluation import evidence
from merchant_assistant.evaluation.runner import Case, _checks, load_cases

BUSINESS_JOURNEYS = Path("tests/scenarios/business_journeys.jsonl")
PROTOCOL = "HO-20261104-A1B2C3"


def _cases() -> dict[str, Case]:
    return {case.id: case for case in load_cases([BUSINESS_JOURNEYS])}


def _scenario_checks(case: Case, answer: str) -> dict:
    body = {
        "answer": answer,
        "route": case.accepted_routes[0],
        "status": case.expected_status,
        "language": case.language,
        "sources": ["synthetic source"] if case.expect_sources else [],
    }
    trace = {
        "steps": [{"step": f"tool:{tool}"} for tool in case.expected_tools],
        "detail": {"output_violations": []},
    }
    return _checks(case, body, trace)


@pytest.mark.parametrize(
    ("scenario_id", "answer"),
    [
        ("V030-PRICE-CONDITIONS", "The comparison is classified as different conditions."),
        ("V030-PRICE-DIVERGENCE", "Yesterday's Pix sale found a discrepancy of R$ 0,75; it needs review."),
        (
            "V030-PRICE-INSUFFICIENT",
            "The records do not show the fee amounts, so I couldn’t confirm whether the expected "
            "and charged fees match.",
        ),
        (
            "V030-PT-PRICE-CONSISTENT",
            "A taxa prevista e a registrada foram ambas de R$ 1,94, portanto estão coerentes.",
        ),
        (
            "V030-PT-PRICE-INSUFFICIENT",
            "Não havia uma taxa prevista disponível nem uma cobrança registrada para comparar.",
        ),
        ("V030-PT-SALE-CANCELLATION", "O cancelamento da venda de ontem consta como solicitado."),
    ],
)
def test_specific_business_journey_equivalences_pass(scenario_id: str, answer: str):
    checks = _scenario_checks(_cases()[scenario_id], answer)
    assert all(checks[key] for key in checks if key != "tools_called")


@pytest.mark.parametrize(
    ("scenario_id", "answer"),
    [
        ("V030-PRICE-CONDITIONS", "The comparison is not classified as different conditions."),
        ("V030-PRICE-DIVERGENCE", "The Pix comparison found no fee discrepancy."),
        ("V030-PRICE-INSUFFICIENT", "There is enough evidence to compare the fee; the fee is correct."),
        (
            "V030-PT-PRICE-CONSISTENT",
            "A taxa prevista e a registrada foram ambas de R$ 1,94, mas não estão coerentes.",
        ),
        ("V030-PT-PRICE-INSUFFICIENT", "A evidência é suficiente para comparar e a taxa está correta."),
        ("V030-PT-SALE-CANCELLATION", "O cancelamento da venda consta como não solicitado."),
    ],
)
def test_contradictory_business_journey_answers_still_fail(scenario_id: str, answer: str):
    checks = _scenario_checks(_cases()[scenario_id], answer)
    assert not checks["content_ok"] or not checks["forbidden_ok"]


def test_a_single_expected_amount_does_not_prove_fee_consistency():
    answer = "A taxa prevista e a registrada foram ambas de valores diferentes; a taxa cobrada é R$ 1,94."
    checks = _scenario_checks(_cases()["V030-PT-PRICE-CONSISTENT"], answer)
    assert not checks["content_ok"]


@pytest.mark.parametrize(
    ("answer", "content_ok"),
    [
        ("Não é verdade que a taxa prevista e a registrada foram ambas de R$ 1,94.", True),
        ("É falso que a taxa prevista e a registrada foram ambas de R$ 1,94.", True),
        ("É mentira que a taxa prevista e a registrada foram ambas de R$ 1,94.", True),
        ("Não é correto dizer que a taxa prevista e a registrada foram ambas de R$ 1,94.", True),
        ("Não é correto afirmar que a taxa prevista e a registrada foram ambas de R$ 1,94.", True),
        ("Não procede que a taxa prevista e a registrada foram ambas de R$ 1,94.", True),
        ("Não procede afirmar que a taxa prevista e a registrada foram ambas de R$ 1,94.", True),
        ("Não é o caso de que a taxa prevista e a registrada foram ambas de R$ 1,94.", True),
        ("A taxa prevista e a registrada não foram ambas de R$ 1,94.", False),
        ("A taxa prevista e a registrada não são ambas de R$ 1,94.", False),
        ("A taxa prevista e a registrada nunca foram ambas de R$ 1,94.", False),
    ],
)
def test_direct_negations_of_fee_equality_are_rejected(answer: str, content_ok: bool):
    checks = _scenario_checks(_cases()["V030-PT-PRICE-CONSISTENT"], answer)
    assert checks["content_ok"] is content_ok
    assert not checks["forbidden_ok"]


@pytest.mark.parametrize(
    ("scenario_id", "answer"),
    [
        ("V030-PRICE-CONDITIONS", "I cannot confirm that."),
        ("V030-PRICE-DIVERGENCE", "I cannot confirm that."),
        ("V030-PRICE-INSUFFICIENT", "I cannot confirm that."),
        ("V030-PT-PRICE-CONSISTENT", "Não consigo confirmar isso."),
        ("V030-PT-PRICE-INSUFFICIENT", "Não consigo confirmar isso."),
        ("V030-PT-SALE-CANCELLATION", "Não consigo confirmar isso."),
    ],
)
def test_generic_answers_do_not_satisfy_the_business_rubric(scenario_id: str, answer: str):
    assert not _scenario_checks(_cases()[scenario_id], answer)["content_ok"]


def test_prohibited_cancellation_claim_still_fails():
    answer = "O cancelamento foi concluído e já foi processado."
    checks = _scenario_checks(_cases()["V030-PT-SALE-CANCELLATION"], answer)
    assert not checks["forbidden_ok"]


def _escalation_step(protocol: str = PROTOCOL, status: str = "ok") -> dict:
    return {
        "step": "escalation",
        "status": status,
        "detail": {"protocol": protocol, "reason": "private reason", "summary": "private summary"},
    }


def test_judge_evidence_uses_only_the_protocol_from_a_successful_handoff_trace():
    reply_protocol = "HO-20991231-FFFFFF"
    body = {
        "status": "handoff",
        "route": "support",
        "answer": f"I handed the case over. Protocol: {reply_protocol}",
    }
    data, _ = evidence.judge_input("Please review this charge.", body, [], [], {"steps": [_escalation_step()]}, {})

    assert data["evidence"] == [{"kind": "trace", "label": "escalation protocol", "text": PROTOCOL}]
    assert reply_protocol not in data["evidence"][0]["text"]


@pytest.mark.parametrize(
    ("status", "steps"),
    [
        ("handoff", []),
        ("answered", [_escalation_step()]),
        ("handoff", [_escalation_step(status="error")]),
        ("handoff", [_escalation_step(protocol="not-a-protocol")]),
        ("handoff", [_escalation_step(), _escalation_step(protocol="HO-20261104-D4E5F6")]),
    ],
)
def test_unverified_handoff_protocol_is_not_added_to_judge_evidence(status: str, steps: list[dict]):
    body = {"status": status, "route": "support", "answer": f"Protocol: {PROTOCOL}"}
    data, _ = evidence.judge_input("Please review this charge.", body, [], [], {"steps": steps}, {})
    assert data["evidence"] == []


def test_handoff_protocol_stays_inside_the_evidence_limit_with_a_long_passage():
    trace = {
        "steps": [
            _escalation_step(),
            {
                "step": "knowledge",
                "status": "ok",
                "detail": {"citations": ["large#0-aaa"], "hits": [{"doc": "large", "chunk_id": "large#0-aaa"}]},
            },
        ]
    }
    body = {"status": "handoff", "route": "support", "answer": "The case was handed over."}
    data, truncation = evidence.judge_input(
        "Please review this charge.", body, [], [], trace, {"large#0-aaa": "x" * 10_000}
    )

    assert truncation["truncated"] and truncation["kept_chars"] <= evidence.EVIDENCE_LIMIT_CHARS
    assert sum(len(item["text"]) for item in data["evidence"]) <= evidence.EVIDENCE_LIMIT_CHARS
    assert any(item["label"] == "escalation protocol" and item["text"] == PROTOCOL for item in data["evidence"])
