"""`judge.v3` (spec v0.8.0 D9): four 1-5 criteria with a reason each and the unsupported-claim verdict, over the masked
evidence, limited to 6 000 characters with the cut on record. Offline: the judge is the scripted stand-in."""

from __future__ import annotations

import json

import pytest

from merchant_assistant.api.identity import Principal
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.data.db import connect
from merchant_assistant.evaluation import evidence
from merchant_assistant.evaluation.judge import CRITERIA, JudgeScoreV3
from merchant_assistant.evaluation.scripted_judge import handler, scripted_judge
from merchant_assistant.llm.base import NullMeter
from merchant_assistant.llm.prompts import load_prompt
from merchant_assistant.llm.scripted import ScriptedLLM
from merchant_assistant.testing import offline_orchestrator
from merchant_assistant.tools import registry
from merchant_assistant.tools.base import CustomerContext, ToolEnv
from merchant_assistant.tools.registry import ToolOutcome, execute

PROMPTS = PROJECT_ROOT / "prompts"
BODY = {"status": "answered", "route": "support", "answer": "O valor líquido é R$ 120,00, com pagamento em 2 dias."}


def tool(name="get_receivables_schedule", data=None, ok=True):
    error = None if ok else {"code": "X"}
    return ToolOutcome(name, {"period": "yesterday"}, ok, data=data if ok else None, error=error)


def data_for(outcomes, reply=None, trace=None, message="Quanto vou receber ontem de recebíveis?"):
    body = BODY | ({"answer": reply} if reply else {})
    data, _ = evidence.judge_input(message, body, ["Receivables (your account)"], outcomes, trace or {"steps": []}, {})
    return data


# --- the rubric files -----------------------------------------------------------------------------------------------


def test_v3_is_the_latest_and_v2_stays_loadable():
    latest, old = load_prompt(PROMPTS, "judge"), load_prompt(PROMPTS, "judge", "2")
    assert (latest.id, latest.version) == ("judge", "3") and (old.id, old.version) == ("judge", "2")
    text = " ".join(latest.template.split())
    assert all(criterion in text for criterion in CRITERIA) and "unsupported_claim" in text
    assert "answers_question" in old.template and "answers_question" not in latest.template
    with pytest.raises(FileNotFoundError):
        load_prompt(PROMPTS, "judge", "9")


# --- the judgement --------------------------------------------------------------------------------------------------


def test_judge_v3_returns_four_scores_with_reasons_and_the_verdict():
    judge = scripted_judge(PROMPTS, NullMeter())
    record = judge.evaluate(data_for([tool(data={"net_amount": {"display": "R$ 120,00"}})]))
    assert record["state"] == "completed" and record["error"] is None
    assert set(record["scores"]) == set(CRITERIA) and set(record["reasons"]) == set(CRITERIA)
    assert all(1 <= score <= 5 for score in record["scores"].values())
    assert all(isinstance(reason, str) and reason for reason in record["reasons"].values())
    assert record["unsupported_claim"] is False
    assert (record["provider"], record["model"], record["rubric_version"]) == ("scripted", "scripted-judge-v3", "3")
    assert record["repetition"] == 1 and record["evaluation_id"].startswith("eval_")


def test_an_amount_the_evidence_does_not_contain_turns_the_verdict_on():
    judge = scripted_judge(PROMPTS, NullMeter())
    supported = judge.evaluate(data_for([tool(data={"net_amount": {"display": "R$ 120,00"}})]))
    invented = judge.evaluate(data_for([tool(data={"net_amount": {"display": "R$ 90,00"}})]))
    assert supported["unsupported_claim"] is False and invented["unsupported_claim"] is True
    assert invented["scores"]["groundedness"] < supported["scores"]["groundedness"]
    assert invented["scores"]["factual_correctness"] < supported["scores"]["factual_correctness"]


def test_the_judge_receives_the_evidence_content_and_the_truncation_record():
    llm = ScriptedLLM(handler, model="scripted-judge-v3")
    judge = scripted_judge(PROMPTS, NullMeter(), llm)
    judge.evaluate(data_for([tool(data={"net_amount": {"display": "R$ 120,00"}})]))
    (call,) = llm.calls
    sent = json.loads(call.spec.input)
    assert call.spec.agent == "judge" and call.spec.instructions == load_prompt(PROMPTS, "judge", "3").render()
    assert sent["evidence"][0]["kind"] == "tool_result" and "R$ 120,00" in sent["evidence"][0]["text"]
    assert sent["evidence_truncation"]["truncated"] is False and sent["reply"] == BODY["answer"]
    assert call.schema is JudgeScoreV3


def test_a_score_outside_the_scale_is_a_failed_judgement_not_an_invented_one():
    def bad(call):
        return handler(call) | {"relevance": 6}

    judge = scripted_judge(PROMPTS, NullMeter(), ScriptedLLM(bad, model="scripted-judge-v3"))
    record = judge.evaluate(data_for([]))
    assert record["state"] == "failed" and record["scores"] == {} and record["unsupported_claim"] is None
    assert "between 1 and 5" in record["error"]


def test_a_provider_error_is_recorded_and_does_not_stop_the_campaign():
    judge = scripted_judge(PROMPTS, NullMeter(), ScriptedLLM(lambda call: RuntimeError("provider down")))
    record = judge.evaluate(data_for([]))
    assert record["state"] == "failed" and record["error"] == "RuntimeError: provider down"


# --- the evidence ---------------------------------------------------------------------------------------------------


def test_long_evidence_is_cut_to_the_limit_and_the_cut_is_recorded():
    items = [
        {"kind": "tool_result", "label": "get_payout_status", "text": "t" * 100},
        {"kind": "passage", "label": "doc", "text": "p" * 10_000},
    ]
    kept, record = evidence.fit_items(items)
    assert record == {
        "limit_chars": 6000,
        "original_chars": 10_100,
        "kept_chars": 6000,
        "items": 2,
        "items_cut": 1,
        "truncated": True,
    }
    assert kept[0]["text"] == "t" * 100  # the short item is never pushed out by the long one
    assert len(kept[1]["text"]) == 5900 and kept[1]["text"].endswith(evidence.CUT_MARK) and kept[1]["cut"] is True
    assert sum(len(item["text"]) for item in kept) <= evidence.EVIDENCE_LIMIT_CHARS


def test_long_items_share_the_limit_equally_and_nothing_is_dropped():
    items = [{"kind": "passage", "label": str(n), "text": "x" * 5000} for n in range(3)]
    kept, record = evidence.fit_items(items)
    assert [len(item["text"]) for item in kept] == [2000, 2000, 2000]
    assert (record["original_chars"], record["kept_chars"], record["items_cut"], record["truncated"]) == (
        15_000,
        6000,
        3,
        True,
    )


def test_evidence_within_the_limit_is_left_alone_and_says_so():
    items = [{"kind": "passage", "label": "doc", "text": "short text"}]
    kept, record = evidence.fit_items(items)
    assert kept == items and record["truncated"] is False and record["items_cut"] == 0
    assert record["kept_chars"] == record["original_chars"] == 10


def test_the_judge_input_carries_the_truncation_of_the_evidence_it_cut():
    big = tool(data={"rows": ["R$ 1,00 " * 40] * 40})
    data = data_for([big])
    assert data["evidence_truncation"]["truncated"] is True
    assert data["evidence_truncation"]["original_chars"] > 6000 and data["evidence_truncation"]["kept_chars"] <= 6000
    assert sum(len(item["text"]) for item in data["evidence"]) <= 6000


def test_evidence_is_masked_before_it_reaches_the_judge():
    secret = tool(data={"note": "card 4111 1111 1111 1111 and CPF 123.456.789-09 and mail ana@example.com"})
    text = data_for([secret])["evidence"][0]["text"]
    assert "4111" not in text and "123.456.789-09" not in text and "ana@example.com" not in text
    assert "[card number removed]" in text and "[CPF removed]" in text and "[e-mail removed]" in text


def test_a_failed_tool_call_is_evidence_too():
    data = data_for([tool(ok=False)])
    assert data["evidence"][0]["kind"] == "tool_result" and '"error"' in data["evidence"][0]["text"]


def test_cited_passages_come_from_the_corpus_with_the_trace_excerpt_as_fallback():
    hits = [
        {"doc": "doc", "chunk_id": "doc#0-aaa", "excerpt": "excerpt zero"},
        {"doc": "doc", "chunk_id": "doc#1-bbb", "excerpt": "excerpt one"},
        {"doc": "doc", "chunk_id": "doc#2-ccc", "excerpt": "retrieved but not cited"},
    ]
    trace = {"steps": [{"step": "knowledge", "detail": {"citations": ["doc#0-aaa", "doc#1-bbb"], "hits": hits}}]}
    items, notes = evidence.passage_items(trace, {"doc#0-aaa": "the full text of chunk zero"})
    assert [(i["kind"], i["text"]) for i in items] == [
        ("passage", "the full text of chunk zero"),
        ("passage", "excerpt one"),
    ]
    assert notes == []
    no_citation = {"steps": [{"step": "knowledge", "detail": {"hits": hits[2:]}}]}
    assert [i["text"] for i in evidence.passage_items(no_citation, {})[0]] == ["retrieved but not cited"]


def test_a_web_answer_tells_the_judge_its_text_is_not_recorded():
    trace = {"steps": [{"step": "knowledge", "detail": {"mode": "web"}}]}
    items, notes = evidence.passage_items(trace, {})
    assert items == [] and notes == [evidence.WEB_NOTE]
    data, _ = evidence.judge_input("Previsão do tempo?", BODY, [], [], trace, {})
    assert data["evidence_notes"] == [evidence.WEB_NOTE] and data["evidence"] == []


def test_tool_results_are_recorded_during_a_case_and_the_observer_is_removed_after(settings):
    orchestrator, _ = offline_orchestrator(settings)
    conn = connect(settings.db_path)
    customer = CustomerContext.for_principal(Principal.merchant("cliente1988"), "cliente1988", True)
    env = ToolEnv(conn, orchestrator.clock, customer, mock_services=orchestrator.mock_services)
    with evidence.record_tool_results() as outcomes:
        assert registry.OUTCOME_OBSERVERS
        execute("get_device_status", {}, env)
    assert [o.name for o in outcomes] == ["get_device_status"] and outcomes[0].ok
    assert registry.OUTCOME_OBSERVERS == []
    execute("get_device_status", {}, env)
    assert len(outcomes) == 1  # a call outside the block is not recorded
    with pytest.raises(RuntimeError), evidence.record_tool_results():
        raise RuntimeError("the case failed")
    assert registry.OUTCOME_OBSERVERS == []
    conn.close()
