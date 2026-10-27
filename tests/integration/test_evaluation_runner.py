from dataclasses import replace

import pytest

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation.runner import CHECK_KEYS, _checks, load_cases, run, summarize, write_report
from merchant_assistant.llm.prompts import load_prompt
from merchant_assistant.testing import offline_orchestrator

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
BUSINESS_JOURNEYS = SCENARIOS / "business_journeys.jsonl"


def checked_business_case(case_id: str, answer: str) -> dict:
    case = next(case for case in load_cases([BUSINESS_JOURNEYS]) if case.id == case_id)
    body = {
        "answer": answer,
        "route": case.accepted_routes[0],
        "status": case.expected_status,
        "language": case.language,
        "sources": [{"title": "synthetic pricing and charge evidence"}] if case.expect_sources else [],
    }
    trace = {
        "steps": [{"step": f"tool:{tool}"} for tool in case.expected_tools],
        "detail": {"output_violations": []},
    }
    return _checks(case, body, trace)


def test_latest_router_prompt_prioritizes_persistent_failure_after_handoff():
    prompt = load_prompt(PROJECT_ROOT / "prompts", "router")
    assert prompt.version == "5"
    template = " ".join(prompt.template.casefold().split())
    assert "continued failure has priority over acknowledgement" in template
    assert "do not open a new handoff" in template


def test_labeled_scenarios_are_valid():
    cases = load_cases([SCENARIOS / "challenge_examples.jsonl", SCENARIOS / "core_cases.jsonl"])
    assert len(cases) == 27
    assert sum(c.split == "dev" for c in cases) == 10
    assert len({c.id for c in cases}) == 27


def test_runner_scripted_mode_produces_report(settings, tmp_path):
    orchestrator, _ = offline_orchestrator(settings)
    cases = [c for c in load_cases([SCENARIOS / "core_cases.jsonl"]) if c.id in {"UC12", "UC14", "UC16", "UC18"}]
    rows = run(orchestrator, cases)
    assert all(r["route_ok"] and r["status_ok"] for r in rows)
    summary = summarize(rows)
    assert summary["overall"]["n"] == 4 and set(CHECK_KEYS) <= set(summary["overall"])
    md, js = write_report(rows, summary, tmp_path, "test", {"mode": "scripted"})
    assert md.exists() and js.exists()


def test_multi_turn_scenarios_scripted(settings):
    from merchant_assistant.evaluation.runner import run_conversations

    orchestrator, _ = offline_orchestrator(settings)
    rows = run_conversations(orchestrator, SCENARIOS / "followup.jsonl")
    assert len(rows) == 4
    assert all(r["passed"] for r in rows), [(r["id"], [t for t in r["turns"] if not t["passed"]]) for r in rows]


@pytest.mark.parametrize(
    ("case_id", "answer"),
    [
        (
            "V030-PRICE-DIVERGENCE",
            "No divergence was found. The difference is R$ 0.75 and I am handing the case to a human.",
        ),
        (
            "V030-PT-PRICE-DIVERGENCE",
            "Não há divergência. A diferença é R$ 0,75 e encaminhei para análise de um atendente.",
        ),
    ],
)
def test_divergence_checks_reject_negation_with_other_criteria_correct(case_id, answer):
    checks = checked_business_case(case_id, answer)
    assert checks["content_ok"] and checks["amounts_ok"]
    assert checks["route_ok"] and checks["status_ok"] and checks["tools_ok"] and checks["sources_ok"]
    assert checks["grounded_ok"] and not checks["forbidden_ok"]


@pytest.mark.parametrize(
    ("case_id", "answer"),
    [
        (
            "V030-PRICE-DIVERGENCE",
            "A divergence of R$ 0.75 was found. No refund or correction is being made; I referred it for review.",
        ),
        (
            "V030-PT-PRICE-DIVERGENCE",
            "Foi encontrada uma divergência de R$ 0,75. Não haverá reembolso nem correção; encaminhei para revisão.",
        ),
    ],
)
def test_divergence_checks_keep_true_handoff_with_no_refund_or_correction(case_id, answer):
    checks = checked_business_case(case_id, answer)
    assert all(checks[key] for key in CHECK_KEYS), checks


@pytest.mark.parametrize(
    ("case_id", "answer"),
    [
        ("V030-PRICE-INSUFFICIENT", "There is not enough evidence to compare the fee."),
        ("V030-PT-PRICE-INSUFFICIENT", "Não há evidência suficiente para comparar a taxa desta venda."),
    ],
)
def test_insufficient_evidence_checks_accept_clear_negative_formulations(case_id, answer):
    checks = checked_business_case(case_id, answer)
    assert checks["content_ok"] and checks["forbidden_ok"], checks
    assert checks["route_ok"] and checks["status_ok"] and checks["tools_ok"] and checks["sources_ok"]


@pytest.mark.parametrize(
    ("case_id", "answer"),
    [
        ("V030-PRICE-INSUFFICIENT", "There is enough evidence to compare the fee."),
        ("V030-PT-PRICE-INSUFFICIENT", "A evidência é suficiente para comparar a taxa."),
    ],
)
def test_insufficient_evidence_checks_still_reject_positive_sufficiency_claim(case_id, answer):
    checks = checked_business_case(case_id, answer)
    assert not checks["content_ok"] or not checks["forbidden_ok"], checks


@pytest.mark.parametrize(
    ("case_id", "answer"),
    [
        (
            "V030-PRICE-INSUFFICIENT",
            "There is enough evidence to compare the fee. "
            "There is no expected pricing fee or recorded charge to compare.",
        ),
        (
            "V030-PRICE-INSUFFICIENT",
            "The fee is correct. There is no expected pricing fee or recorded charge to compare.",
        ),
        ("V030-PT-PRICE-INSUFFICIENT", "A taxa está correta. Não há taxa esperada para comparar."),
        (
            "V030-PRICE-INSUFFICIENT",
            "There is no data, but the fee is correct. There is no expected pricing fee or recorded charge to compare.",
        ),
        (
            "V030-PT-PRICE-INSUFFICIENT",
            "Não há dados, mas a taxa está correta. Não há taxa esperada para comparar.",
        ),
    ],
)
def test_insufficient_evidence_rejects_assertions_even_with_missing_evidence(case_id, answer):
    checks = checked_business_case(case_id, answer)
    assert checks["content_ok"], checks
    assert not checks["forbidden_ok"], checks
    assert all(checks[key] for key in CHECK_KEYS if key not in {"content_ok", "forbidden_ok"}), checks


@pytest.mark.parametrize(
    ("case_id", "answer"),
    [
        (
            "V030-PRICE-INSUFFICIENT",
            "There is insufficient evidence to compare the fee. I cannot confirm whether the fee is correct.",
        ),
        (
            "V030-PRICE-INSUFFICIENT",
            "The comparison returned insufficient evidence; I am not sure whether the fee is correct.",
        ),
        (
            "V030-PT-PRICE-INSUFFICIENT",
            "Não há evidência suficiente para comparar a taxa; não foi possível confirmar se a taxa está correta.",
        ),
        (
            "V030-PT-PRICE-INSUFFICIENT",
            "Não há evidência suficiente para comparar. Não está claro se a taxa está correta.",
        ),
    ],
)
def test_insufficient_evidence_accepts_scoped_uncertainty(case_id, answer):
    checks = checked_business_case(case_id, answer)
    assert all(checks[key] for key in CHECK_KEYS), checks


def test_literal_privacy_ban_remains_unconditional_inside_negation():
    case = next(case for case in load_cases([BUSINESS_JOURNEYS]) if case.id == "V030-PRICE-INSUFFICIENT")
    case = replace(case, must_not_include=["customer ID 123"])
    body = {
        "answer": "There is insufficient evidence to compare the fee. Do not disclose customer ID 123.",
        "route": case.accepted_routes[0],
        "status": case.expected_status,
        "language": case.language,
        "sources": [{"title": "synthetic pricing and charge evidence"}],
    }
    trace = {"steps": [{"step": f"tool:{tool}"} for tool in case.expected_tools], "detail": {"output_violations": []}}

    checks = _checks(case, body, trace)

    assert checks["content_ok"]
    assert not checks["forbidden_ok"]
    assert all(checks[key] for key in CHECK_KEYS if key != "forbidden_ok"), checks


@pytest.mark.parametrize(
    ("case_id", "valid_answer", "contradictory_answer"),
    [
        (
            "V030-PRICE-CONDITIONS",
            "The expected plan was demo_standard and the recorded plan was demo_legacy, "
            "a difference in pricing conditions.",
            "The expected and recorded pricing conditions were the same.",
        ),
        (
            "V030-PRICE-DIVERGENCE",
            "The difference between the pricing rule and the recorded charge was R$ 0.75. "
            "No refund or correction was made; I handed this off.",
            "No difference between the pricing rule and the recorded charge was found. "
            "The amount is R$ 0.75 and I handed this off.",
        ),
        (
            "V030-PRICE-INSUFFICIENT",
            "The comparison returned insufficient evidence. "
            "There was no expected pricing fee or recorded charge to compare.",
            "The fee was confirmed as correct.",
        ),
        (
            "V030-PT-PRICE-INSUFFICIENT",
            "Não foi possível confirmar se a taxa está correta ou incorreta. "
            "Não há taxa esperada nem cobrança registrada para comparar.",
            "A taxa foi confirmada como correta e há evidência suficiente para comparar.",
        ),
        (
            "V030-PT-SALE-CANCELLATION",
            "O cancelamento da venda está com status “solicitado”. Ainda não há registro de processamento.",
            "O cancelamento da venda foi finalizado.",
        ),
    ],
)
def test_real_r2_phrasings_pass_and_contradictions_fail(case_id, valid_answer, contradictory_answer):
    valid = checked_business_case(case_id, valid_answer)
    contradictory = checked_business_case(case_id, contradictory_answer)
    assert all(valid[key] for key in CHECK_KEYS), valid
    assert not all(contradictory[key] for key in CHECK_KEYS), contradictory


@pytest.mark.parametrize(
    ("case_id", "answer"),
    [
        (
            "V030-PT-PRICE-DIVERGENCE",
            "Foi encontrada uma divergência de R$ 0,75. Não haverá reembolso nem correção; encaminhei para revisão.",
        ),
        (
            "V030-PT-PRICE-DIVERGENCE",
            "Não há divergência. A diferença é R$ 0,75 e encaminhei para análise de um atendente.",
        ),
    ],
)
def test_pt_divergence_accepts_truth_and_rejects_negation(case_id, answer):
    checks = checked_business_case(case_id, answer)
    if answer.startswith("Não há divergência"):
        assert checks["amounts_ok"] and checks["route_ok"] and checks["status_ok"] and checks["sources_ok"]
        assert checks["content_ok"] and not checks["forbidden_ok"]
    else:
        assert all(checks[key] for key in CHECK_KEYS), checks
