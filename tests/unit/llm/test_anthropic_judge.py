"""v0.9.0 task 79 (spec D3, D4): the Anthropic adapter for the campaign judge, its prices with cache and the judge
validation. The provider is programmed (the real SDK client over an in-memory transport): no network, no cost."""

from __future__ import annotations

import json

import pytest
from pydantic import SecretStr

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation import judge as judge_module
from merchant_assistant.evaluation.judge import Judge, JudgeRefused, JudgeScoreV3, judge_spec_v3
from merchant_assistant.llm import pricing
from merchant_assistant.llm.anthropic_llm import NOT_SUPPORTED, AnthropicLLM
from merchant_assistant.llm.base import CallSpec, LLMError, Usage
from merchant_assistant.llm.prompts import load_prompt
from merchant_assistant.llm.scripted_anthropic import FIXED_JUDGEMENT, ScriptedAnthropic, judging, message

MODEL = "claude-opus-5-5"
AGENT = ("openai", "gpt-6-luna")


class RecordingMeter:
    def __init__(self) -> None:
        self.reserved: list[dict] = []
        self.settled: list[Usage | None] = []
        self.cost_usd = 0.0

    def reserve(self, **kwargs):
        self.reserved.append(kwargs)
        return len(self.reserved)

    def settle(self, reservation, usage):
        self.settled.append(usage)
        if usage is not None:
            self.cost_usd += pricing.cost(MODEL, usage)


def spec(max_output_tokens: int = 2000) -> CallSpec:
    data = {"merchant_message": "Qual o prazo?", "reply": "Dois dias úteis.", "evidence": []}
    prompt = load_prompt(PROJECT_ROOT / "prompts", "judge", "3")
    return judge_spec_v3(prompt, data, max_output_tokens)


def test_parse_sends_the_structured_output_contract_and_returns_the_judgement():
    provider = ScriptedAnthropic(judging(cache_read=1000, cache_creation=500))
    meter = RecordingMeter()
    result = AnthropicLLM(provider.client, MODEL).parse(spec(), JudgeScoreV3, meter)
    assert result.value.model_dump() == FIXED_JUDGEMENT and result.model == MODEL
    body = provider.requests[0]
    assert body["model"] == MODEL and body["max_tokens"] == 2000
    assert body["system"] == spec().instructions
    assert body["messages"] == [{"role": "user", "content": spec().input}]
    assert "thinking" not in body and "effort" not in body["output_config"]  # D3: the model's defaults
    schema = body["output_config"]["format"]
    assert schema["type"] == "json_schema"
    strict = schema["schema"]
    assert strict["additionalProperties"] is False and sorted(strict["required"]) == sorted(JudgeScoreV3.model_fields)
    assert all(strict["properties"][c]["type"] == "integer" for c in judge_module.CRITERIA)
    assert strict["properties"]["unsupported_claim"]["type"] == "boolean"
    # input_tokens is the whole input: 3000 uncached + 1000 read + 500 written; each part priced at its rate
    assert result.usage == Usage(4500, 500, 1000, 0, 500)
    assert meter.reserved[0]["max_output_tokens"] == 2000 and meter.settled == [result.usage]


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_a_refusal_or_a_cut_answer_is_an_error_never_a_score(stop):
    text = "" if stop == "refusal" else '{"groundedness": 4, "groundedness_reason": "cut'
    provider = ScriptedAnthropic(lambda body: message(text, stop_reason=stop))
    meter = RecordingMeter()
    with pytest.raises(LLMError, match=f"stop_reason={stop}"):
        AnthropicLLM(provider.client, MODEL).parse(spec(), JudgeScoreV3, meter)
    assert meter.settled == [Usage(3000, 500, 0, 0, 0)]  # what the provider billed is still settled


def test_a_network_failure_settles_the_reservation_and_is_an_error():
    provider = ScriptedAnthropic(lambda body: OSError("connection reset"))
    meter = RecordingMeter()
    with pytest.raises(LLMError, match="APIConnectionError"):
        AnthropicLLM(provider.client, MODEL).parse(spec(), JudgeScoreV3, meter)
    assert meter.settled == [None]  # usage unknown: the reservation stands


def test_an_answer_outside_the_schema_or_the_scale_is_an_error():
    out_of_scale = dict(FIXED_JUDGEMENT, groundedness=7)
    for text in ("not json", json.dumps(out_of_scale)):
        provider = ScriptedAnthropic(lambda body, text=text: message(text))
        with pytest.raises(LLMError, match="does not match the schema"):
            AnthropicLLM(provider.client, MODEL).parse(spec(), JudgeScoreV3, RecordingMeter())


def test_tools_and_web_search_are_not_offered_to_the_judge():
    llm = AnthropicLLM(ScriptedAnthropic(judging()).client, MODEL)
    with pytest.raises(LLMError, match=NOT_SUPPORTED):
        llm.run_tools(spec(), JudgeScoreV3, RecordingMeter(), tools=[], call_tool=lambda n, a: "", max_tool_calls=1)
    with pytest.raises(LLMError, match=NOT_SUPPORTED):
        llm.web_search(spec(), RecordingMeter())


def test_claude_prices_cover_cache_reads_and_cache_writes():
    opus = pricing.model_price(MODEL)
    assert (opus["provider"], opus["input_per_mtok"], opus["output_per_mtok"]) == ("anthropic", 4.00, 20.00)
    assert opus["cached_input_per_mtok"] == 0.20 and opus["cache_creation_input_per_mtok"] == 5.00
    assert pricing.model_price("claude-sonnet-5-5")["output_per_mtok"] == 10.00
    assert pricing.model_price("claude-haiku-5-5")["input_per_mtok"] == 0.10
    # 3000 uncached x 4 + 1000 read x 0.20 + 500 written x 5 + 500 output x 20, per million
    assert pricing.cost(MODEL, Usage(4500, 500, 1000, 0, 500)) == pytest.approx(0.0247)
    # without an explicit write price, Anthropic writes cost 1.25x the input and the others the input price
    assert pricing.cache_creation_price({"provider": "anthropic", "input_per_mtok": 2.0}) == 2.5
    assert pricing.cache_creation_price({"provider": "openai", "input_per_mtok": 0.1}) == 0.1
    openai = (800 * 0.10 + 200 * 0.01 + 100 * 0.5) / 1e6  # OpenAI usage is unchanged: no cache-write part
    assert pricing.cost("gpt-6-luna", Usage(1000, 100, 200)) == pytest.approx(openai)


def judge_settings(settings, **overrides):
    values = {"judge_provider": "anthropic", "judge_model": MODEL, "anthropic_api_key": SecretStr("test-key")}
    return settings.model_copy(update=values | overrides)


def test_a_claude_judge_is_independent_of_the_openai_agent_and_needs_its_own_key(settings):
    setup = judge_module.validate_judge(judge_settings(settings), agent=AGENT)
    assert (setup.provider, setup.model, setup.independence) == ("anthropic", MODEL, "different_provider")
    with pytest.raises(JudgeRefused, match="ANTHROPIC_API_KEY"):
        judge_module.validate_judge(judge_settings(settings, anthropic_api_key=None), agent=AGENT)
    with pytest.raises(JudgeRefused, match="registered for the provider deepseek"):
        judge_module.validate_judge(judge_settings(settings, judge_model="deepseek-flash"), agent=AGENT)
    with pytest.raises(JudgeRefused, match="registered for the provider anthropic"):
        judge_module.validate_judge(judge_settings(settings, judge_provider="deepseek"), agent=AGENT)


def test_the_factory_builds_the_adapter_only_with_the_key_and_calls_nothing(settings):
    from merchant_assistant.main import model_factory

    llm = model_factory(judge_settings(settings))("anthropic", MODEL)
    assert isinstance(llm, AnthropicLLM) and llm.model == MODEL
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        model_factory(judge_settings(settings, anthropic_api_key=None))("anthropic", MODEL)


def test_the_claude_judge_has_room_for_thinking_and_a_refusal_is_a_failed_judgement(settings):
    provider = ScriptedAnthropic(lambda body: message("", stop_reason="refusal"))
    judge = judge_module.resolve_judge(
        judge_settings(settings), agent=AGENT, factory=lambda p, m: AnthropicLLM(provider.client, m)
    )
    assert isinstance(judge, Judge) and judge.max_output_tokens == 2000
    assert judge.config()["parameters"] == {"max_output_tokens": 2000, "effort": "default", "thinking": "default"}
    record = judge.evaluate({"merchant_message": "Oi", "reply": "Olá", "evidence": []})
    assert provider.requests[0]["max_tokens"] == 2000
    assert record["state"] == "failed" and record["scores"] == {} and record["unsupported_claim"] is None
    assert "refusal" in record["error"]
    # the other judges keep the v0.8.0 parameters
    assert judge_module.max_output_tokens_for("deepseek") == judge_module.MAX_OUTPUT_TOKENS == 400
