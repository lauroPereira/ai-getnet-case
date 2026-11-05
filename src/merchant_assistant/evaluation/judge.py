"""The campaign judge (spec v0.8.0 D9, D11): rubric `judge.v3`, an evaluator that is not the agent, and its record.

The judge scores a reply against the evidence the system had (`evidence.py`) on four 1-5 criteria with a short reason
each, and gives a boolean verdict for a claim the evidence does not support. Provider and model are configured
(JUDGE_PROVIDER, JUDGE_MODEL), differ from the agent's and are written into every judgement. A judge equal to the
agent, without its key, without a price or paired with a provider that does not sell the model is refused before any
call: the paid evaluation never swaps judges on its own. The /v1 on-demand evaluator has its own settings
(EVALUATOR_*) and is not touched by these."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

from merchant_assistant.guardrails.input import mask_sensitive
from merchant_assistant.llm import pricing
from merchant_assistant.llm.base import LLM, CallSpec, Meter, NullMeter
from merchant_assistant.llm.prompts import Prompt, load_prompt
from merchant_assistant.profiles import digest

CRITERIA = ("groundedness", "factual_correctness", "relevance", "usefulness")
RUBRIC = "judge"
RUBRIC_VERSION = "3"
MAX_OUTPUT_TOKENS = 400  # four reasons of at most 25 words and the scores take about 220; this is also the reservation
CAMPAIGN_PRINCIPAL = "cli:eval"
MAX_ERROR_CHARS = 160  # a provider error is stored as its class and a short masked message, never as the raw body
AGENT_PROVIDER = "openai"  # the system under evaluation is built with the OpenAI client (main.build_orchestrator)
JUDGE_PROVIDERS = ("openai", "deepseek", "anthropic")  # providers that can return the structured judgement
# v0.9.0 D1: a Claude judge runs with its default (adaptive) thinking, which counts against max_tokens; 400 would cut
# the judgement short. The other judges keep 400.
MAX_OUTPUT_TOKENS_BY_PROVIDER = {"anthropic": 2000}


class JudgeRefused(RuntimeError):
    """The configured judge cannot be used. Raised before any model call; nothing was spent."""


@dataclass(frozen=True)
class JudgeSetup:
    """Validated local judge configuration, prepared before a spending guard or provider client is created."""

    agent: tuple[str, str]
    provider: str
    model: str
    prompt: Prompt
    independence: str


class JudgeScoreV3(BaseModel):
    groundedness: int = Field(description="1-5: every fact in the reply is supported by the evidence.")
    groundedness_reason: str = Field(description="One short sentence (at most 25 words).")
    factual_correctness: int = Field(description="1-5: the reply agrees with the evidence and is consistent.")
    factual_correctness_reason: str = Field(description="One short sentence (at most 25 words).")
    relevance: int = Field(description="1-5: the reply addresses what the merchant asked.")
    relevance_reason: str = Field(description="One short sentence (at most 25 words).")
    usefulness: int = Field(description="1-5: the merchant can act on the reply; clear, polite, right language.")
    usefulness_reason: str = Field(description="One short sentence (at most 25 words).")
    unsupported_claim: bool = Field(description="True when the reply asserts something the evidence does not support.")

    @field_validator(*CRITERIA)
    @classmethod
    def _scale(cls, value: int) -> int:
        if not 1 <= value <= 5:  # checked here, not in the schema: strict structured outputs reject numeric bounds
            raise ValueError("a score must be between 1 and 5")
        return value


def short_error(exc: Exception) -> str:
    """Class and a short message, masked and on one line: a provider error can echo parts of the request."""
    message = " ".join(mask_sensitive(str(exc))[0].split())
    if len(message) > MAX_ERROR_CHARS:
        message = message[: MAX_ERROR_CHARS - 3] + "..."
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def max_output_tokens_for(provider: str) -> int:
    return MAX_OUTPUT_TOKENS_BY_PROVIDER.get(provider, MAX_OUTPUT_TOKENS)


def judge_spec_v3(prompt: Prompt, data: dict, max_output_tokens: int = MAX_OUTPUT_TOKENS) -> CallSpec:
    return CallSpec(
        agent="judge",
        instructions=prompt.render(),
        effort="none",
        max_output_tokens=max_output_tokens,
        input=json.dumps(data, ensure_ascii=False),
    )


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Judge:
    """A judge bound to its model, prompt and spending meter. `evaluate` never raises: a failure is a judgement of its
    own (state `failed`), so one bad call does not stop a campaign."""

    llm: LLM
    provider: str
    model: str
    prompt: Prompt
    meter: Meter
    independence: str
    max_output_tokens: int = MAX_OUTPUT_TOKENS

    def config(self) -> dict:
        parameters: dict = {"max_output_tokens": self.max_output_tokens, "effort": "none"}
        if self.provider == "anthropic":  # D3: thinking and effort are left to the model's defaults
            parameters = {"max_output_tokens": self.max_output_tokens, "effort": "default", "thinking": "default"}
        return {
            "provider": self.provider,
            "model": self.model,
            "rubric": RUBRIC,
            "rubric_version": self.prompt.version,
            "prompt": self.prompt.ref,
            "independence": self.independence,
            "parameters": parameters,
        }

    def evaluate(self, data: dict, *, repetition: int = 1) -> dict:
        record = {
            "evaluation_id": f"eval_{uuid.uuid4().hex[:20]}",
            "rubric_version": self.prompt.version,
            "repetition": repetition,
            "provider": self.provider,
            "model": self.model,
        }
        spent_before = getattr(self.meter, "cost_usd", 0.0)
        try:
            spec = judge_spec_v3(self.prompt, data, self.max_output_tokens)
            result = self.llm.parse(spec, JudgeScoreV3, self.meter)
        except Exception as exc:  # provider, validation or budget failure: recorded, never raised
            return record | {
                "state": "failed",
                "model_used": self.model,
                "scores": {},
                "reasons": {},
                "unsupported_claim": None,
                "cost_usd": round(getattr(self.meter, "cost_usd", 0.0) - spent_before, 8),
                "error": short_error(exc),
            }
        score = result.value
        return record | {
            "state": "completed",
            "model_used": result.model,
            "scores": {criterion: getattr(score, criterion) for criterion in CRITERIA},
            "reasons": {criterion: getattr(score, f"{criterion}_reason") for criterion in CRITERIA},
            "unsupported_claim": score.unsupported_claim,
            "cost_usd": round(getattr(self.meter, "cost_usd", 0.0) - spent_before, 8),
            "error": None,
        }


# --- independence ---------------------------------------------------------------------------------------------------


def check_independence(agent: tuple[str, str], judge: tuple[str, str]) -> str:
    """How the judge differs from the agent: `different_provider` or `same_provider_different_model`. The judge and the
    agent as the same provider and model is the one combination RF-90 forbids."""
    if agent == judge:
        raise JudgeRefused(
            f"The judge {judge[0]}/{judge[1]} is the same model as the agent. A model grading its own replies is not "
            "an independent evaluation: set JUDGE_PROVIDER and JUDGE_MODEL to another model. "
            "No call was made."
        )
    return "different_provider" if agent[0] != judge[0] else "same_provider_different_model"


def _has_key(settings, provider: str) -> bool:
    if provider == "openai":
        return settings.has_openai
    key = settings.anthropic_api_key if provider == "anthropic" else settings.deepseek_api_key
    return bool(key and key.get_secret_value())


def default_factory(settings) -> Callable[[str, str], LLM]:
    """The model clients the project already has (OpenAI, DeepSeek and, for the judge only, Anthropic)."""
    from merchant_assistant.main import model_factory

    return model_factory(settings)


def validate_judge(settings, *, agent: tuple[str, str]) -> JudgeSetup:
    """Validate provider, price, independence, key and prompt without constructing a provider client."""
    provider, model = settings.judge_provider, settings.judge_model
    if provider not in JUDGE_PROVIDERS:
        raise JudgeRefused(
            f"Provider {provider} cannot be the judge (supported: {', '.join(JUDGE_PROVIDERS)}). "
            "Check JUDGE_PROVIDER. No call was made."
        )
    try:
        price = pricing.model_price(model)
        priced_for = price.get("provider")
    except pricing.PriceUnknown:
        raise JudgeRefused(
            f"No price is registered for the judge model {model}, and a call without a price cannot be budgeted. "
            "No call was made."
        ) from None
    if priced_for != provider:  # the pair must exist: a label cannot make a model independent
        raise JudgeRefused(
            f"The model {model} is registered for the provider {priced_for}, not {provider}: JUDGE_PROVIDER and "
            "JUDGE_MODEL must name a pair that exists. No call was made."
        )
    if not price.get("output_per_mtok"):  # an embedding or router model has no output price: it writes no judgement
        raise JudgeRefused(
            f"The model {model} has no output price in prices.json: it does not generate text and cannot be the judge. "
            "No call was made."
        )
    independence = check_independence(agent, (provider, model))
    if not _has_key(settings, provider):
        raise JudgeRefused(
            f"The judge {provider}/{model} needs {provider.upper()}_API_KEY and it is not configured. The paid "
            "evaluation does not switch to another judge on its own: set the key or choose another JUDGE_*. "
            "No call was made."
        )
    prompt = load_prompt(settings.prompts_dir, RUBRIC, RUBRIC_VERSION)
    return JudgeSetup(agent, provider, model, prompt, independence)


def resolve_judge(
    settings,
    *,
    agent: tuple[str, str],
    meter: Meter | None = None,
    factory: Callable[[str, str], LLM] | None = None,
    validated: JudgeSetup | None = None,
) -> Judge:
    """Build a judge after validation; its spending meter can be bound after the run guard exists."""
    setup = validated or validate_judge(settings, agent=agent)
    if (
        setup.agent != agent
        or setup.provider != settings.judge_provider
        or setup.model != settings.judge_model
    ):
        raise JudgeRefused("The judge configuration changed after validation. No call was made.")
    try:
        llm = (factory or default_factory(settings))(setup.provider, setup.model)
    except RuntimeError as exc:
        raise JudgeRefused(
            f"The judge {setup.provider}/{setup.model} is not available: {exc}. No call was made."
        ) from exc
    return Judge(
        llm,
        setup.provider,
        setup.model,
        setup.prompt,
        meter or NullMeter(),
        setup.independence,
        max_output_tokens_for(setup.provider),
    )


# --- persistence ----------------------------------------------------------------------------------------------------


def save_evaluation(conn, *, request_id: str, judge: Judge, record: dict, data: dict) -> None:
    """Writes one judgement into `run_evaluations` (the columns 0011 added hold the queryable parts; `result` holds
    the whole judgement). Campaign judgements belong to the principal `cli:eval`, so no API session ever lists them."""
    completed = record["state"] == "completed"
    # `result` carries everything the columns of 0011 hold (scores, verdict, repetition), so a rollback and a new
    # upgrade rebuild them from it.
    result = {"repetition": record["repetition"]}
    if completed:
        result |= {
            **record["scores"],
            **{f"{criterion}_reason": text for criterion, text in record["reasons"].items()},
            "unsupported_claim": record["unsupported_claim"],
        }
    evaluator = judge.config() | {"model_used": record["model_used"]}
    conn.execute(
        "INSERT INTO run_evaluations (evaluation_id,request_id,principal_id,method,rubric,rubric_version,evaluator,"
        "config_digest,result,evidence,critical_failures,cost_usd,state,error,created_at,scores,repetition,"
        "unsupported_claim) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            record["evaluation_id"],
            request_id,
            CAMPAIGN_PRINCIPAL,
            "model",
            RUBRIC,
            record["rubric_version"],
            json.dumps(evaluator, sort_keys=True),
            digest(
                {
                    "request_id": request_id,
                    "rubric_version": record["rubric_version"],
                    "evaluator": judge.config(),
                    "repetition": record["repetition"],
                }
            ),
            json.dumps(result, sort_keys=True, ensure_ascii=False),
            json.dumps(data, sort_keys=True, ensure_ascii=False),
            json.dumps(
                [{"code": "unsupported_claim", "check": "judge"}] if record["unsupported_claim"] else [], sort_keys=True
            ),
            record["cost_usd"],
            record["state"],
            record["error"],
            _now(),
            json.dumps(record["scores"], sort_keys=True) if completed else None,
            record["repetition"],
            None if record["unsupported_claim"] is None else int(record["unsupported_claim"]),
        ),
    )
