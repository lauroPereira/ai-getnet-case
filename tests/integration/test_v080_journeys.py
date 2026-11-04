"""v0.8.0 task 72b (RF-93, CA-51; spec D15): the business journeys, `router.v6` and the labels.

Scripted model, no network, no cost. What the real model does with `router.v6` and `personality.v5` is measured by the
`v080-qa` campaign; here the prompts are pinned (text and version), the scripted Router follows the same rule, and each
label that changed is checked against the answer the real model gave (copied verbatim from the v0.7.0 campaign in
`docs/evidence/v070-qa-regressao-*.json`) and against the wrong answers the widened label must still reject."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid

import pytest
from pydantic import SecretStr

from merchant_assistant.agents.personality import HANDOFF_LINE
from merchant_assistant.api.schemas import MessageRequest
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation.runner import CHECK_KEYS, _checks, load_cases
from merchant_assistant.evaluation.scripted_policy import CONDITIONS_QUESTION, route_for
from merchant_assistant.llm.prompts import prompt_versions
from merchant_assistant.testing import key_token, offline_orchestrator

PROMPTS = PROJECT_ROOT / "prompts"
CASES = {case.id: case for case in load_cases([PROJECT_ROOT / "tests" / "scenarios" / "business_journeys.jsonl"])}

# The question the real Router sent to `clarify` in the v0.7.0 campaign, and the interrogative variations.
CONDITIONS_EN = "Were different conditions used for yesterday's credit charge?"
CONDITIONS_PT = "A cobrança de crédito de ontem foi feita em condições diferentes?"
CREDIT_CONDITIONS = [  # credit: the synthetic sale whose recorded plan differs from the applicable one
    (CONDITIONS_EN, "en", "conditions differ"),
    ("Was yesterday's credit charge made under different conditions?", "en", "conditions differ"),
    ("Did yesterday's credit sale use a different plan?", "en", "conditions differ"),
    ("Were different pricing conditions applied to yesterday's credit sale?", "en", "conditions differ"),
    ("Were the conditions different on yesterday's credit charge?", "en", "conditions differ"),
    (CONDITIONS_PT, "pt", "condições registradas diferem"),
    ("A venda de crédito de ontem usou um plano diferente?", "pt", "condições registradas diferem"),
    ("Foram aplicadas condições distintas na cobrança de crédito de ontem?", "pt", "condições registradas diferem"),
    ("As condições da venda de crédito de ontem mudaram?", "pt", "condições registradas diferem"),
]
OTHER_PAYMENT_TYPES = [  # the programmed Support looks up the payment type the message names (debit, Pix, else credit)
    ("Did the conditions change on yesterday's debit sale?", "en", "answered", "consistent values"),
    ("Was yesterday's Pix charge made under different conditions?", "en", "handoff", "divergence"),
    ("A venda no débito de ontem usou condições diferentes?", "pt", "answered", "valores coerentes"),
    ("A cobrança no Pix de ontem foi feita em condições diferentes?", "pt", "handoff", "divergência"),
]
# `CONDITIONS_QUESTION` needs four things: a word of difference, the conditions or plan, a charge or sale, a period.
MATCHES_CONDITIONS_RULE = [
    "Did the plan differ on yesterday's credit sale?",  # differ
    "Did the plan change on yesterday's credit sale?",  # change
    "A venda de crédito de ontem mudou de plano?",  # mudou
    "As condições da venda de crédito de ontem mudaram?",  # mudaram
    "A venda de crédito de ontem teve condições distintas?",  # distintas
    "Foram aplicadas condições diferentes na cobrança de ontem?",  # diferentes
    "Was today's credit charge made under a different plan?",  # today
    "Was the latest credit sale charged under different conditions?",  # latest
    "A cobrança de hoje usou outro plano diferente?",  # hoje
]
MISSES_ONE_OF_THE_FOUR = [
    ("Which conditions applied to yesterday's credit sale?", "no word of difference"),
    ("Was yesterday's credit sale different?", "no conditions or plan"),
    ("Were the conditions different yesterday?", "no charge or sale"),
    ("Were different conditions used for the credit sale?", "no period"),
    ("Do the conditions change for sales above R$ 1.000?", "no period (a general question)"),
    ("Can I change my plan?", "no charge or sale, no period"),
]

# Answers the real model gave in the v0.7.0 campaign (verbatim). Each one is correct and was rejected by its label.
REAL_CORRECT = {
    "consistent": (
        "V030-PRICE-CONSISTENT",
        "The fee on your debit sale from November 3, 2026 matches the applicable pricing. The expected and recorded "
        "fee were both R$ 1,94, with a difference of R$ 0,00. From the R$ 150,00 sale, you received R$ 148,06 after "
        "the fee.",
    ),
    "divergence": (
        "V030-PRICE-DIVERGENCE",
        "The comparison for your Pix sale on November 3, 2026 shows a fee discrepancy: the expected fee was R$ 0,00, "
        "but the recorded fee was R$ 0,75. The sale was R$ 80,00, and the recorded net amount was R$ 79,25 instead "
        "of the expected R$ 80,00. This comparison does not issue a correction or refund, so the discrepancy needs "
        "human review. Your case has been handed to a member of our support team, who will reply here. Protocol: "
        "HO-20261104-F8D41C.",
    ),
    "enablement without protocol": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is still pending and has not been activated yet. The request was submitted on "
        "November 2, 2026. Visa appearing as available on your device does not mean account enablement is active.",
    ),
    "enablement with protocol": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is still pending under protocol SIM-BND-1988-001. The device is reported as "
        "available for Visa, but the account configuration has not yet been activated.",
    ),
    "enablement cautious completion date": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is still pending. I don't see an estimated completion date.",
    ),
    "enablement no Mastercard request": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request remains pending. There is no pending Mastercard request.",
    ),
    "enablement uncertain approval": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is currently pending. I cannot confirm whether it will be approved.",
    ),
    "pt conditions": (
        "V030-PT-PRICE-CONDITIONS",
        "Sim. A venda de crédito de 2026-11-03, em 1 parcela, foi registrada no plano demo_legacy, enquanto a "
        "condição de preço aplicável indicava demo_standard.\n\nPara o valor bruto de R$ 1.200,00, foram cobrados "
        "R$ 37,80, com líquido de R$ 1.162,20. Pela condição aplicável, a taxa seria R$ 36,00, com líquido de "
        "R$ 1.164,00.\n\nEssa diferença indica condições distintas, mas não confirma, por si só, um erro na "
        "cobrança. A comparação não realiza correção nem reembolso.",
    ),
    "pt insufficient": (
        "V030-PT-PRICE-INSUFFICIENT",
        "Não foi possível confirmar qual taxa foi cobrada na venda de crédito em 2 parcelas de 02/11/2026, no valor "
        "bruto de R$ 200,00, nem se houve divergência. Não há uma regra de preço aplicável ou uma cobrança "
        "registrada disponível para comparação.",
    ),
}
# Correct real answers from the earlier campaigns (v0.3.0, `docs/evidence/v030-real-*.json`) that the guards added in
# round 2 must not reject: every phrase forbidden below was checked against these.
REAL_CORRECT_V030 = {
    "consistent": (
        "V030-PRICE-CONSISTENT",
        "The debit sale on October 26, 2026 is consistent: the expected and recorded fees are both R$ 1,94, with a "
        "difference of R$ 0,00. The gross amount was R$ 150,00, and the net amount was R$ 148,06.",
    ),
    "divergence": (
        "V030-PRICE-DIVERGENCE",
        "For yesterday, October 26, 2026, the expected Pix fee was R$ 0,00, but R$ 0,75 was charged. For the R$ 80,00 "
        "sale, the recorded net amount was R$ 79,25 instead of R$ 80,00. This confirms a difference between the "
        "pricing rule and the recorded charge; no correction or refund has been made. I’ve handed your case to a "
        "human agent. Protocol: HO-20261027-B9F454.",
    ),
    "enablement with the protocol first": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is still pending and has not been activated. The device checked is available "
        "for Visa. Your existing protocol is SIM-BND-1988-001.",
    ),
    "enablement with the date": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is still pending. It was submitted on October 25, 2026, under protocol "
        "SIM-BND-1988-001. The device is reported as available for Visa, but Visa has not yet been activated in your "
        "account configuration.",
    ),
    "pt conditions, as the conditions differ": (
        "V030-PT-PRICE-CONDITIONS",
        "Sim. A venda de crédito de 26/10/2026 foi registrada no plano demo_legacy, enquanto a regra de comparação "
        "considera demo_standard. A cobrança foi de R$ 37,80; pela regra consultada, seria R$ 36,00. Como as "
        "condições são diferentes, essa diferença não comprova erro na cobrança.",
    ),
    "pt conditions, the comparison shows": (
        "V030-PT-PRICE-CONDITIONS",
        "A venda de crédito de 26/10/2026 foi registrada em 1 parcela, no canal POS e no plano demo_legacy. A regra de "
        "preço consultada se aplica ao plano demo_standard, então a comparação mostra condições diferentes e, por si "
        "só, não confirma erro na cobrança.",
    ),
}

# Wrong answers a widened label must still reject: (case, answer, the check that must fail).
STILL_WRONG = {
    "inconsistent": (
        "V030-PRICE-CONSISTENT",
        "The fee on your debit sale is inconsistent: expected R$ 1,94, but a different fee was recorded.",
        "forbidden_ok",
    ),
    "does not match": (
        "V030-PRICE-CONSISTENT",
        "The recorded fee does not match the applicable pricing; the expected fee was R$ 1,94.",
        "forbidden_ok",
    ),
    "no discrepancy": (
        "V030-PRICE-DIVERGENCE",
        "There is no fee discrepancy on your Pix sale: R$ 0,75 was charged as expected.",
        "forbidden_ok",
    ),
    "enablement approved": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is no longer pending: it has been approved.",
        "forbidden_ok",
    ),
    "enablement unrelated": (
        "V030-ENABLEMENT-PENDING",
        "Your request was received on November 2, 2026.",
        "content_ok",
    ),
    "pt no different conditions": (
        "V030-PT-PRICE-CONDITIONS",
        "Não houve condições distintas nesta cobrança de crédito.",
        "forbidden_ok",
    ),
    "pt same conditions": (
        "V030-PT-PRICE-CONDITIONS",
        "A cobrança de crédito foi feita nas mesmas condições.",
        "forbidden_ok",
    ),
    "pt confirms the fee": (
        "V030-PT-PRICE-INSUFFICIENT",
        "Há uma regra de preço aplicável e a taxa está correta.",
        "forbidden_ok",
    ),
    "pt unrelated": ("V030-PT-PRICE-INSUFFICIENT", "A venda de crédito foi de R$ 200,00.", "content_ok"),
    # round 3 (review P2-1): a negative status must not satisfy the positive status anchor; direct promises still fail
    "enablement: could not find it": (
        "V030-ENABLEMENT-PENDING",
        "I could not find any pending Visa enablement request.",
        "content_ok",
    ),
    "enablement: you have none": (
        "V030-ENABLEMENT-PENDING",
        "You have no pending Visa enablement request.",
        "content_ok",
    ),
    "enablement: not in pending status": (
        "V030-ENABLEMENT-PENDING",
        "The Visa enablement request is not in pending status.",
        "content_ok",
    ),
    "enablement: active, none pending": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement is active. There are no pending requests.",
        "content_ok",
    ),
    "enablement: canceled": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa request has been canceled, nothing pending.",
        "content_ok",
    ),
    "enablement: promised": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is pending, and it will be approved tomorrow.",
        "forbidden_ok",
    ),
    "enablement: rejected": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request was rejected, so it is no more pending.",
        "content_ok",
    ),
    "enablement: cannot see it": (
        "V030-ENABLEMENT-PENDING",
        "I don’t see a pending Visa request on your account.",
        "content_ok",
    ),
    "enablement: completed": (
        "V030-ENABLEMENT-PENDING",
        "The pending Visa enablement request was completed and is already enabled.",
        "content_ok",
    ),
    "enablement: not currently pending": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is not currently pending.",
        "forbidden_ok",
    ),
    "enablement: not still pending": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is not still pending.",
        "forbidden_ok",
    ),
    "enablement: promised within 24 hours": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is pending and should be approved within 24 hours.",
        "forbidden_ok",
    ),
    "enablement: pending but approved": (
        "V030-ENABLEMENT-PENDING",
        "Your Visa enablement request is still pending, but it has been approved.",
        "forbidden_ok",
    ),
    # round 2 (P3): the other widened groups
    "pt conditions: denied": (
        "V030-PT-PRICE-CONDITIONS",
        "Não, não foram usadas condições distintas na cobrança de crédito de ontem.",
        "forbidden_ok",
    ),
    "pt conditions: not found": (
        "V030-PT-PRICE-CONDITIONS",
        "Não encontrei condições distintas nessa cobrança de crédito.",
        "forbidden_ok",
    ),
    "pt conditions: no signs": (
        "V030-PT-PRICE-CONDITIONS",
        "Não há indícios de condições distintas nessa cobrança.",
        "forbidden_ok",
    ),
    "pt conditions: not verified": (
        "V030-PT-PRICE-CONDITIONS",
        "Não foi possível verificar se havia condições distintas nessa cobrança.",
        "forbidden_ok",
    ),
    "pt conditions: the same": (
        "V030-PT-PRICE-CONDITIONS",
        "As condições distintas? Não: foram as mesmas em toda a cobrança.",
        "forbidden_ok",
    ),
    "mismatches": (
        "V030-PRICE-CONSISTENT",
        "The recorded fee mismatches the applicable pricing: the expected fee was R$ 1,94.",
        "forbidden_ok",
    ),
    "mismatch, there was one": (
        "V030-PRICE-CONSISTENT",
        "There was a mismatch with the applicable pricing: R$ 1,94 expected, no difference of R$ 0,00 explains it.",
        "forbidden_ok",
    ),
    "divergence: did not find": (
        "V030-PRICE-DIVERGENCE",
        "I did not find a fee discrepancy on your Pix sale; R$ 0,75 was charged as expected.",
        "forbidden_ok",
    ),
    "divergence: not detected": (
        "V030-PRICE-DIVERGENCE",
        "A fee discrepancy was not detected for your Pix sale (R$ 0,75).",
        "forbidden_ok",
    ),
    "divergence: found none": (
        "V030-PRICE-DIVERGENCE",
        "The check found no fee discrepancy; R$ 0,75 is the expected fee.",
        "forbidden_ok",
    ),
}


def label_checks(case_id: str, answer: str) -> dict:
    """The runner's checks on `answer`, with route, status, tools, language and sources as the label expects."""
    case = CASES[case_id]
    body = {
        "answer": answer,
        "route": case.accepted_routes[0],
        "status": case.expected_status,
        "language": case.language,
        "sources": [{"title": "synthetic evidence"}],
    }
    trace = {"steps": [{"step": f"tool:{tool}"} for tool in case.expected_tools], "detail": {"output_violations": []}}
    return _checks(case, body, trace)


def handle(settings, message):
    orchestrator, _ = offline_orchestrator(settings)
    request_id = f"req_t72b_{uuid.uuid4().hex[:12]}"
    body = orchestrator.handle(MessageRequest(message=message, user_id="cliente1988"), request_id).model_dump()
    return body, orchestrator.trace(request_id)


def step(trace, name):
    return next(s for s in trace["steps"] if s["step"] == name)


def tools(trace):
    return [s["step"].removeprefix("tool:") for s in trace["steps"] if s["step"].startswith("tool:")]


# --- prompts: new versions, the previous ones untouched -------------------------------------------------------------


def test_router_v6_teaches_the_interrogative_conditions_question_and_never_clarifies_it():
    raw = (PROMPTS / "router.v6.md").read_text(encoding="utf-8")
    assert raw.startswith("---\nid: router\nversion: 6\n---")
    text = " ".join(raw.split())
    for question in (CONDITIONS_EN, CONDITIONS_PT, "Was yesterday's credit sale charged under a different plan?"):
        assert question in text
    assert "never `knowledge` and never `clarify`" in text
    assert "Never use `clarify` to ask which type of credit sale, how many installments or which sale" in text
    assert "route it to support with topic `pricing`" in text
    assert "A question about Getnet's general rates is still `knowledge`" in text  # the rule does not swallow rates
    # review P3-5: general questions that do not point at the merchant's own charge stay knowledge
    for general in (
        "What are the fees for credit sales?",
        "Can I change my plan?",
        "Do the conditions change for sales above R$ 1.000?",
    ):
        assert general in text
    assert "a general question that does not point at a charge the merchant already had stays `knowledge`" in text
    # what v5 already protected stays
    assert "Continued failure has priority over acknowledgement" in text
    assert 'for example "it is not working" with no subject' in text


def test_router_v5_is_left_as_it_was():
    v5 = (PROMPTS / "router.v5.md").read_text(encoding="utf-8")
    assert v5.startswith("---\nid: router\nversion: 5\n---")
    assert "interrogative" not in v5 and "installment count is optional" not in v5


def test_personality_v5_says_a_human_agent_answers_and_v4_is_left_as_it_was():
    v5 = (PROMPTS / "personality.v5.md").read_text(encoding="utf-8")
    assert v5.startswith("---\nid: personality\nversion: 5\n---")
    text = " ".join(v5.split())
    assert (
        "confirm that the case went to a human agent on the support team, who will reply in this conversation" in text
    )
    assert 'Say that it is a human agent (in Portuguese, "um atendente"), not only "a member of the team"' in text
    assert "Keep the wording of the `handoff.message` contribution" in text
    # the rules around it stay
    assert "Never say a problem is solved unless the case state given below is" in text
    assert "If the contributions include `operator`" in text
    v4 = (PROMPTS / "personality.v4.md").read_text(encoding="utf-8")
    assert v4.startswith("---\nid: personality\nversion: 4\n---")
    assert "went to a member of the\n  support team" in v4 and "went to a human agent" not in v4


def test_the_loader_serves_the_new_router_and_personality_versions():
    versions = prompt_versions(PROMPTS)
    assert int(versions["router"]) >= 6 and int(versions["personality"]) >= 5


def test_the_run_snapshot_names_the_router_prompt_in_force(settings, offline):
    """`api/v1.py` used to write the literal "router.v5" in the snapshot; it follows the loaded prompt now."""
    settings.api_demo_password = SecretStr("synthetic-demo-access-key-t72b")
    client, _, _ = offline()
    headers = {"Authorization": f"Bearer {key_token(client, 'synthetic-demo-access-key-t72b')}"}
    payload = {"message": CONDITIONS_EN, "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm"}
    response = client.post("/v1/messages", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    conn = sqlite3.connect(settings.db_path)
    try:
        snapshot = json.loads(conn.execute("SELECT snapshot FROM run_snapshots").fetchone()[0])
    finally:
        conn.close()
    assert snapshot["prompt_versions"] == {"router": f"router.v{snapshot['prompt_set']['router']}"}
    assert snapshot["prompt_versions"]["router"] != "router.v5"


# --- the Router: the question and its variations never end in clarify -----------------------------------------------


@pytest.mark.parametrize(("message", "language", "expected"), CREDIT_CONDITIONS)
def test_conditions_question_in_any_interrogative_form_is_support_pricing_and_answered(
    settings, message, language, expected
):
    body, trace = handle(settings, message)
    router = step(trace, "router")["detail"]
    assert (router["route"], router["topic"]) == ("support", "pricing")
    assert (body["route"], body["status"], body["language"]) == ("support", "answered", language)
    assert "simulate_pricing" in tools(trace)
    assert expected in body["answer"].lower()
    assert body["sources"]


@pytest.mark.parametrize(("message", "language", "status", "expected"), OTHER_PAYMENT_TYPES)
def test_conditions_question_about_another_payment_type_looks_up_that_payment_type(
    settings, message, language, status, expected
):
    """Debit comes back consistent and Pix comes back as a divergence in the synthetic data; credit differs. The
    answer shows which sale the programmed Support looked up."""
    body, trace = handle(settings, message)
    assert (body["route"], body["language"], body["status"]) == ("support", language, status)
    assert "simulate_pricing" in tools(trace)
    assert expected in body["answer"].lower()


@pytest.mark.parametrize("message", MATCHES_CONDITIONS_RULE)
def test_the_conditions_rule_matches_each_word_of_difference_and_each_period(message):
    assert re.search(CONDITIONS_QUESTION, message, flags=re.IGNORECASE), message
    assert route_for(message) == ("support", "pricing")


@pytest.mark.parametrize(("message", "missing"), MISSES_ONE_OF_THE_FOUR)
def test_the_conditions_rule_needs_all_four_parts(message, missing):
    """Mutants that drop a part of the rule would send these questions to pricing (review P3-6)."""
    assert not re.search(CONDITIONS_QUESTION, message, flags=re.IGNORECASE), (message, missing)
    assert route_for(message)[1] != "pricing", (message, missing)


@pytest.mark.parametrize(
    ("message", "route", "topic"),
    [
        ("Qual a diferença entre a Get Clássica e a Get Smart?", "knowledge", None),
        ("What's the difference between the Get Clássica and the Get Smart plans?", "knowledge", None),
        ("A antecipação de recebíveis está disponível no meu plano?", "knowledge", None),
        ("My plan is different from my friend's. Can I sell by Pix?", "knowledge", None),
        ("it's not working", "clarify", None),
        ("Is the fee on yesterday's debit sale consistent?", "support", "pricing"),
    ],
)
def test_the_conditions_rule_does_not_swallow_other_questions(message, route, topic):
    assert route_for(message) == (route, topic)


@pytest.mark.parametrize(
    "message",
    [
        "What are the fees for credit sales?",
        "Can I change my plan?",
        "Do the conditions change for sales above R$ 1.000?",
        "As condições mudam para vendas acima de R$ 1.000?",
    ],
)
def test_general_fee_and_plan_questions_are_not_pricing_questions_about_a_charge(message):
    """The contrast `router.v6` teaches: no charge of the merchant is pointed at (review P3-5)."""
    assert route_for(message)[1] != "pricing"


# --- labels: correct real answers pass, wrong ones still fail ------------------------------------------------------


@pytest.mark.parametrize("name", list(REAL_CORRECT))
def test_the_real_answers_that_were_correct_now_pass_their_label(name):
    case_id, answer = REAL_CORRECT[name]
    checks = label_checks(case_id, answer)
    assert all(checks[key] for key in CHECK_KEYS), {key: checks[key] for key in CHECK_KEYS}


@pytest.mark.parametrize("name", list(REAL_CORRECT_V030))
def test_the_guards_of_round_2_do_not_reject_the_correct_real_answers_of_v030(name):
    case_id, answer = REAL_CORRECT_V030[name]
    checks = label_checks(case_id, answer)
    assert all(checks[key] for key in CHECK_KEYS), {key: checks[key] for key in CHECK_KEYS}


@pytest.mark.parametrize("name", list(STILL_WRONG))
def test_the_widened_labels_still_reject_the_wrong_answer(name):
    case_id, answer, failing = STILL_WRONG[name]
    assert not label_checks(case_id, answer)[failing]


def test_enablement_label_requires_affirmative_status_with_narrow_guards():
    case = CASES["V030-ENABLEMENT-PENDING"]
    assert case.must_include_any == [
        ["pending"],
        ["visa"],
        ["still pending", "is pending", "remains pending", "currently pending"],
    ]
    assert case.must_not_include == ["not currently pending", "not still pending"]
    assert case.must_not_assert == [
        "will be approved",
        "should be approved",
        "has been approved",
        "was approved",
        "has been enabled",
        "is now enabled",
        "is now active",
        "is already enabled",
        "was rejected",
        "was completed",
        "has been completed",
    ]


def test_the_value_checks_of_the_changed_labels_are_untouched():
    """Amounts, tools, status, route and sources are what protect the merchant: only the wording groups moved."""
    expected = {
        "V030-PRICE-CONSISTENT": ([194], ["simulate_pricing"], "answered", ["support"], True),
        "V030-PRICE-DIVERGENCE": ([75], ["simulate_pricing"], "handoff", ["support"], True),
        "V030-ENABLEMENT-PENDING": ([], ["get_enablement_requests"], "answered", ["support"], True),
        "V030-PT-PRICE-CONDITIONS": ([], ["simulate_pricing"], "answered", ["support"], True),
        "V030-PT-PRICE-INSUFFICIENT": ([], ["simulate_pricing"], "answered", ["support"], True),
    }
    for case_id, (amounts, expected_tools, status, routes, sources) in expected.items():
        case = CASES[case_id]
        assert (case.must_include_amounts, case.expected_tools, case.expected_status) == (
            amounts,
            expected_tools,
            status,
        )
        assert (case.accepted_routes, case.expect_sources) == (routes, sources)
    # the "must not assert" list of the insufficient-evidence cases is exactly the one the v0.7.0 campaign ran with
    assert "a taxa está correta" in CASES["V030-PT-PRICE-INSUFFICIENT"].must_not_assert
    assert "the fee is correct" in CASES["V030-PRICE-INSUFFICIENT"].must_not_assert


# --- V030-CONTRACT-TERMINATION: the prompt changed, the label did not -----------------------------------------------


def test_contract_termination_keeps_asking_for_a_human_and_the_system_line_says_it():
    case = CASES["V030-CONTRACT-TERMINATION"]
    assert case.must_include_any == [["human"]]
    # the wording the real model gave with personality.v4: a person is not named, so the label rejects it
    v4_wording = (
        "Your case has been handed to a member of our support team, who will reply here. Protocol: HO-20261104-0B64BF."
    )
    assert not label_checks(case.id, v4_wording)["content_ok"]
    # the line the system itself writes (and appends when the model leaves it out) names a human agent
    line = HANDOFF_LINE["en"].format(protocol="HO-20261104-0B64BF")
    assert "human agent" in line and label_checks(case.id, line)["content_ok"]
    assert "atendente" in HANDOFF_LINE["pt"]
    assert "human agent" in (PROMPTS / "personality.v5.md").read_text(encoding="utf-8")


def test_the_scripted_regression_still_passes_the_changed_journeys(settings):
    orchestrator, _ = offline_orchestrator(settings)
    changed = [CASES[case_id] for case_id in {c for c, _ in REAL_CORRECT.values()} | {"V030-CONTRACT-TERMINATION"}]
    for case in changed:
        request_id = f"req_t72b_{uuid.uuid4().hex[:12]}"
        body = orchestrator.handle(MessageRequest(message=case.message, user_id=case.user_id), request_id).model_dump()
        checks = _checks(case, body, orchestrator.trace(request_id))
        assert all(checks[key] for key in CHECK_KEYS), (case.id, body["answer"], checks)
