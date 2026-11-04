"""The judge is not the agent (spec v0.8.0 D11, RF-90): a judge equal to the agent, without its key, without a price or
from an unsupported provider is refused with a clear message before the client is even built. Offline."""

from __future__ import annotations

import json

import pytest
from pydantic import SecretStr

from merchant_assistant.config import PROJECT_ROOT, Settings
from merchant_assistant.data.db import connect
from merchant_assistant.evaluation import evidence
from merchant_assistant.evaluation.judge import (
    JudgeRefused,
    check_independence,
    resolve_judge,
    save_evaluation,
)
from merchant_assistant.evaluation.scripted_judge import handler, scripted_judge
from merchant_assistant.llm.base import NullMeter
from merchant_assistant.llm.scripted import ScriptedLLM

AGENT = ("openai", "gpt-6-luna")


class Factory:
    """Stands for the provider clients: counts how many were built and hands out a scripted judge model."""

    def __init__(self, error: Exception | None = None):
        self.built, self.error = [], error
        self.llm = ScriptedLLM(handler, model="deepseek-flash")

    def __call__(self, provider, model):
        self.built.append((provider, model))
        if self.error:
            raise self.error
        return self.llm


def configured(**update) -> Settings:
    base = {"_env_file": None, "openai_api_key": None, "deepseek_api_key": None}
    return Settings(**(base | update))


def test_the_default_judge_is_deepseek_flash_and_differs_from_the_default_agent():
    settings = configured()
    assert (settings.evaluator_provider, settings.evaluator_model) == ("deepseek", "deepseek-flash")
    assert (AGENT[0], settings.agent_model) != (settings.evaluator_provider, settings.evaluator_model)


def test_a_configured_independent_judge_is_resolved_without_any_call():
    factory = Factory()
    settings = configured(deepseek_api_key=SecretStr("synthetic-deepseek-key"))
    judge = resolve_judge(settings, agent=AGENT, meter=NullMeter(), factory=factory)
    assert (judge.provider, judge.model, judge.independence) == ("deepseek", "deepseek-flash", "different_provider")
    assert judge.config()["rubric_version"] == "3" and judge.config()["prompt"] == "judge@3"
    assert factory.built == [("deepseek", "deepseek-flash")] and factory.llm.calls == []


def test_a_judge_equal_to_the_agent_is_refused_before_any_client_is_built():
    factory = Factory()
    settings = configured(
        openai_api_key=SecretStr("synthetic-openai-key"), evaluator_provider="openai", evaluator_model="gpt-6-luna"
    )
    with pytest.raises(JudgeRefused) as refused:
        resolve_judge(settings, agent=AGENT, meter=NullMeter(), factory=factory)
    message = str(refused.value)
    assert "openai/gpt-6-luna is the same model as the agent" in message and "EVALUATOR_MODEL" in message
    assert message.endswith("No call was made.") and factory.built == [] and factory.llm.calls == []


def test_a_judge_without_its_provider_key_is_refused_and_never_replaced():
    factory = Factory()
    with pytest.raises(JudgeRefused) as refused:
        resolve_judge(configured(), agent=AGENT, meter=NullMeter(), factory=factory)
    message = str(refused.value)
    assert "DEEPSEEK_API_KEY" in message and "does not switch to another judge" in message
    assert "synthetic" not in message and factory.built == [] and factory.llm.calls == []

    other = configured(evaluator_provider="openai", evaluator_model="another-openai-model")
    with pytest.raises(JudgeRefused, match="OPENAI_API_KEY"):
        resolve_judge(other, agent=AGENT, meter=NullMeter(), factory=factory)
    assert factory.built == []


def test_an_empty_key_counts_as_missing():
    settings = configured(deepseek_api_key=SecretStr(""))
    with pytest.raises(JudgeRefused, match="DEEPSEEK_API_KEY"):
        resolve_judge(settings, agent=AGENT, meter=NullMeter(), factory=Factory())


def test_a_judge_without_a_price_or_from_an_unsupported_provider_is_refused():
    factory = Factory()
    unpriced = configured(deepseek_api_key=SecretStr("synthetic-deepseek-key"), evaluator_model="unpriced-model")
    with pytest.raises(JudgeRefused, match="No price is registered for the judge model unpriced-model"):
        resolve_judge(unpriced, agent=AGENT, meter=NullMeter(), factory=factory)
    router_only = configured(evaluator_provider="typesafe", evaluator_model="jev-1.14.0")
    with pytest.raises(JudgeRefused, match="Provider typesafe cannot be the judge"):
        resolve_judge(router_only, agent=AGENT, meter=NullMeter(), factory=factory)
    assert factory.built == []


def test_a_provider_that_cannot_be_built_is_a_refusal_not_a_crash():
    settings = configured(deepseek_api_key=SecretStr("synthetic-deepseek-key"))
    factory = Factory(RuntimeError("DEEPSEEK_API_KEY is not configured"))
    with pytest.raises(JudgeRefused, match="is not available: DEEPSEEK_API_KEY is not configured"):
        resolve_judge(settings, agent=AGENT, meter=NullMeter(), factory=factory)


def test_the_independence_basis_is_named_and_only_the_identical_pair_is_forbidden():
    assert check_independence(AGENT, ("deepseek", "deepseek-flash")) == "different_provider"
    assert check_independence(AGENT, ("openai", "another-model")) == "same_provider_different_model"
    assert check_independence(("scripted", "scripted-v1"), ("scripted", "scripted-judge-v3")) == (
        "same_provider_different_model"
    )
    with pytest.raises(JudgeRefused):
        check_independence(AGENT, AGENT)


def test_a_judgement_is_stored_with_its_provider_model_and_the_queryable_columns(tmp_path):
    prompts = PROJECT_ROOT / "prompts"
    judge = scripted_judge(prompts, NullMeter())
    broken = scripted_judge(prompts, NullMeter(), ScriptedLLM(lambda call: ValueError("bad")))
    reply = {"status": "answered", "route": "support", "answer": "Você recebe R$ 10,00."}
    data, _ = evidence.judge_input("Quanto vou receber?", reply, [], [], {}, {})
    done = judge.evaluate(data, repetition=2)
    failed = broken.evaluate(data, repetition=3)
    conn = connect(tmp_path / "campaign.sqlite3")
    save_evaluation(conn, request_id="req_eval000001", judge=judge, record=done, data=data)
    save_evaluation(conn, request_id="req_eval000001", judge=judge, record=failed, data=data)

    row = conn.execute("SELECT * FROM run_evaluations WHERE evaluation_id=?", (done["evaluation_id"],)).fetchone()
    kind = (row["principal_id"], row["method"], row["rubric"], row["rubric_version"])
    assert kind == ("cli:eval", "model", "judge", "3")
    assert (row["state"], row["repetition"], row["unsupported_claim"]) == ("completed", 2, 1)  # R$ 10,00 is invented
    evaluator = json.loads(row["evaluator"])
    assert (evaluator["provider"], evaluator["model"], evaluator["model_used"]) == (
        "scripted",
        "scripted-judge-v3",
        "scripted-judge-v3",
    )
    assert json.loads(row["scores"]) == done["scores"]
    result = json.loads(row["result"])
    assert result["unsupported_claim"] is True and result["groundedness_reason"] == done["reasons"]["groundedness"]
    assert json.loads(row["evidence"])["reply"] == "Você recebe R$ 10,00."

    bad = conn.execute("SELECT * FROM run_evaluations WHERE evaluation_id=?", (failed["evaluation_id"],)).fetchone()
    assert (bad["state"], bad["scores"], bad["unsupported_claim"], bad["repetition"]) == ("failed", None, None, 3)
    assert bad["error"] == "ValueError: bad" and json.loads(bad["result"]) == {}
    conn.close()
