"""The campaign judge (spec v0.8.0 D9, D11): rubric `judge.v3`, an evaluator that is not the agent, and its record.

The judge scores a reply against the evidence the system had (`evidence.py`) on four 1-5 criteria with a short reason
each, and gives a boolean verdict for a claim the evidence does not support. Provider and model are configured
(EVALUATOR_PROVIDER, EVALUATOR_MODEL), differ from the agent's and are written into every judgement. A judge equal to
the agent, without its key or without a price is refused before any call: the paid evaluation never swaps judges on
its own."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

from merchant_assistant.llm import pricing
from merchant_assistant.llm.base import LLM, CallSpec, Meter, NullMeter
from merchant_assistant.llm.prompts import Prompt, load_prompt
from merchant_assistant.profiles import digest

CRITERIA = ("groundedness", "factual_correctness", "relevance", "usefulness")
RUBRIC = "judge"
RUBRIC_VERSION = "3"
MAX_OUTPUT_TOKENS = 600
CAMPAIGN_PRINCIPAL = "cli:eval"
AGENT_PROVIDER = "openai"  # the system under evaluation is built with the OpenAI client (main.build_orchestrator)
JUDGE_PROVIDERS = ("openai", "deepseek")  # providers that can return the structured judgement


class JudgeRefused(RuntimeError):
    """The configured judge cannot be used. Raised before any model call; nothing was spent."""


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


def judge_spec_v3(prompt: Prompt, data: dict) -> CallSpec:
    return CallSpec(
        agent="judge",
        instructions=prompt.render(),
        effort="none",
        max_output_tokens=MAX_OUTPUT_TOKENS,
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

    def config(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "rubric": RUBRIC,
            "rubric_version": self.prompt.version,
            "prompt": self.prompt.ref,
            "independence": self.independence,
            "parameters": {"max_output_tokens": MAX_OUTPUT_TOKENS, "effort": "none"},
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
            result = self.llm.parse(judge_spec_v3(self.prompt, data), JudgeScoreV3, self.meter)
        except Exception as exc:  # provider, validation or budget failure: recorded, never raised
            return record | {
                "state": "failed",
                "model_used": self.model,
                "scores": {},
                "reasons": {},
                "unsupported_claim": None,
                "cost_usd": round(getattr(self.meter, "cost_usd", 0.0) - spent_before, 8),
                "error": f"{type(exc).__name__}: {exc}",
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
            "an independent evaluation: set EVALUATOR_PROVIDER and EVALUATOR_MODEL to another model. "
            "No call was made."
        )
    return "different_provider" if agent[0] != judge[0] else "same_provider_different_model"


def _has_key(settings, provider: str) -> bool:
    if provider == "openai":
        return settings.has_openai
    key = settings.deepseek_api_key
    return bool(key and key.get_secret_value())


def default_factory(settings) -> Callable[[str, str], LLM]:
    """The provider clients the project already has (OpenAI and, for the model profiles, DeepSeek)."""
    from merchant_assistant.llm.openai_llm import OpenAILLM
    from merchant_assistant.main import deepseek_client, openai_client

    def factory(provider: str, model: str) -> LLM:
        if provider == "openai":
            return OpenAILLM(openai_client(settings), model)
        if provider == "deepseek":
            return OpenAILLM(deepseek_client(settings), model)
        raise RuntimeError(f"provider {provider} is not available")

    return factory


def resolve_judge(
    settings,
    *,
    agent: tuple[str, str],
    meter: Meter | None = None,
    factory: Callable[[str, str], LLM] | None = None,
) -> Judge:
    """The configured judge, or a refusal. Every check runs before the client is built, so a refusal costs nothing.
    The spending meter can be bound afterwards (`judge.meter = ...`), once the budget guard of the run exists."""
    provider, model = settings.evaluator_provider, settings.evaluator_model
    if provider not in JUDGE_PROVIDERS:
        raise JudgeRefused(
            f"Provider {provider} cannot be the judge (supported: {', '.join(JUDGE_PROVIDERS)}). "
            "Check EVALUATOR_PROVIDER. No call was made."
        )
    independence = check_independence(agent, (provider, model))
    if not _has_key(settings, provider):
        raise JudgeRefused(
            f"The judge {provider}/{model} needs {provider.upper()}_API_KEY and it is not configured. The paid "
            "evaluation does not switch to another judge on its own: set the key or choose another EVALUATOR_*. "
            "No call was made."
        )
    try:
        pricing.model_price(model)
    except pricing.PriceUnknown:
        raise JudgeRefused(
            f"No price is registered for the judge model {model}, and a call without a price cannot be budgeted. "
            "No call was made."
        ) from None
    prompt = load_prompt(settings.prompts_dir, RUBRIC, RUBRIC_VERSION)
    try:
        llm = (factory or default_factory(settings))(provider, model)
    except RuntimeError as exc:
        raise JudgeRefused(f"The judge {provider}/{model} is not available: {exc}. No call was made.") from exc
    return Judge(llm, provider, model, prompt, meter or NullMeter(), independence)


# --- persistence ----------------------------------------------------------------------------------------------------


def save_evaluation(conn, *, request_id: str, judge: Judge, record: dict, data: dict) -> None:
    """Writes one judgement into `run_evaluations` (the columns 0011 added hold the queryable parts; `result` holds
    the whole judgement). Campaign judgements belong to the principal `cli:eval`, so no API session ever lists them."""
    completed = record["state"] == "completed"
    result = (
        {
            **record["scores"],
            **{f"{criterion}_reason": text for criterion, text in record["reasons"].items()},
            "unsupported_claim": record["unsupported_claim"],
        }
        if completed
        else {}
    )
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
