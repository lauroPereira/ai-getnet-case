"""The campaign judge (spec v0.8.0 D9, D11): rubric `judge.v5` by default, an evaluator that is not the agent, and
its record.

The judge scores a reply against the evidence the system had (`evidence.py`) on four 1-5 criteria with a short reason
each, and gives a boolean verdict for a claim the evidence does not support. Provider and model are configured
(JUDGE_PROVIDER, JUDGE_MODEL), differ from the agent's and are written into every judgement. A judge equal to the
agent, without its key, without a price or paired with a provider that does not sell the model is refused before any
call: the paid evaluation never swaps judges on its own. The /v1 on-demand evaluator has its own settings
(EVALUATOR_*) and is not touched by these.

`judge.v5` (spec v0.11.0 D3, task 88) judges claim by claim, in two calls: `judge_claims.v1` lists the claims of the
reply without seeing the evidence (`ClaimList`), then `judge.v5` gives a verdict per claim and the four criteria
(`JudgeScoreV5`). `unsupported_claim` is computed here from the verdicts, never asked of the model. A calibration run
can hand it the claims of the sample instead (`eval --judge-repeat --claims-from`, task 89 round 2): the first call is
skipped, the verdicts answer the sample's numbers and the judgement records where its claims came from."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from merchant_assistant.guardrails.input import mask_sensitive
from merchant_assistant.llm import pricing
from merchant_assistant.llm.base import LLM, CallSpec, Meter, NullMeter
from merchant_assistant.llm.prompts import Prompt, load_prompt
from merchant_assistant.profiles import digest

CRITERIA = ("groundedness", "factual_correctness", "relevance", "usefulness")
RUBRIC = "judge"
RUBRIC_VERSION = "5"  # selected by the v0.11.0 D6(g) rule; v3 and v4 remain explicit options
# v0.10.0 D1: judge.v4 is judge.v3 plus the general claim with no source; the schema (JudgeScoreV3) is the same.
# v0.11.0 D3: judge.v5 judges claim by claim, after the claims prompt (CLAIM_RUBRICS) has listed them.
RUBRIC_VERSIONS = ("3", "4", "5")
CLAIM_RUBRICS = {"5": ("judge_claims", "1")}  # rubric version -> the prompt that lists the claims before it
CLAIM_KINDS = ("fact", "value", "date", "status", "promise", "guidance", "standard")
CLAIM_VERDICTS = ("supported", "partial", "generic", "not_found")
UNSUPPORTED_VERDICTS = frozenset({"generic", "not_found"})  # `partial` does not turn the verdict on
SUPPORT_MAX_CHARS = 200
CLAIMS_INPUT = ("merchant_message", "route", "status", "reply")  # the claims step sees no evidence: it only lists
MAX_OUTPUT_TOKENS = 400  # four reasons of at most 25 words and the scores take about 220; this is also the reservation
# v0.11.0 D3, sized from the longest replies: the personality step writes at most 600 tokens and the replies of the
# v0.10.0 campaign have up to 13 sentences (about 25 claims once compound sentences are split). Listing re-emits the
# reply plus about 15 tokens of JSON per claim (600 + 25 x 15 = 975); a verdict with a 200-character quote takes about
# 70 (25 x 70 = 1 750) beside the four reasons (about 220). Both are also the reservation of each call.
CLAIMS_MAX_OUTPUT_TOKENS = 1200
MAX_OUTPUT_TOKENS_V5 = 2000
CAMPAIGN_PRINCIPAL = "cli:eval"
MAX_ERROR_CHARS = 160  # a provider error is stored as its class and a short masked message, never as the raw body
AGENT_PROVIDER = "openai"  # the system under evaluation is built with the OpenAI client (main.build_orchestrator)
JUDGE_PROVIDERS = ("openai", "deepseek", "anthropic")  # providers that can return the structured judgement
# v0.9.0 D1: a Claude judge runs with its default (adaptive) thinking, which counts against max_tokens; 400 would cut
# the judgement short. The other judges keep 400.
MAX_OUTPUT_TOKENS_BY_PROVIDER = {"anthropic": 2000}
THINKING_MARGIN_BY_PROVIDER = {"anthropic": 1600}  # the same margin over the visible output, for both calls of v5


class JudgeRefused(RuntimeError):
    """The configured judge cannot be used. Raised before any model call; nothing was spent."""


class ClaimMismatch(ValueError):
    """The verdicts of `judge.v5` do not answer exactly the claims it was given: the judgement is invalid."""


def rubric_version(choice: str | None) -> str:
    """The stored version of a rubric named on the command line (`v3`, `v4`, `v5`, or `3`, `4`, `5`); `None` is the
    default."""
    if choice is None:
        return RUBRIC_VERSION
    version = choice[1:] if choice[:1] in ("v", "V") else choice
    if version not in RUBRIC_VERSIONS:
        raise JudgeRefused(
            f"Unknown rubric {choice!r} (available: {', '.join('v' + v for v in RUBRIC_VERSIONS)}). No call was made."
        )
    return version


@dataclass(frozen=True)
class JudgeSetup:
    """Validated local judge configuration, prepared before a spending guard or provider client is created."""

    agent: tuple[str, str]
    provider: str
    model: str
    prompt: Prompt
    independence: str
    claims_prompt: Prompt | None = None  # judge.v5: the prompt of the first call (CLAIM_RUBRICS)


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


# --- judge.v5: claim by claim (spec v0.11.0 D3) ---------------------------------------------------------------------


class Claim(BaseModel):
    n: int = Field(description="Number of the claim: 1, 2, 3, ... in the order of the reply.")
    text: str = Field(description="The claim, short and in the words of the reply.")
    kind: Literal["fact", "value", "date", "status", "promise", "guidance", "standard"] = Field(
        description="What the claim states; standard for handing over, protocol, clarification and courtesy."
    )


class ClaimList(BaseModel):
    claims: list[Claim] = Field(description="Every claim of the reply, numbered; empty when it states nothing.")

    @field_validator("claims")
    @classmethod
    def _numbers(cls, claims: list[Claim]) -> list[Claim]:
        numbers = [claim.n for claim in claims]
        if any(n < 1 for n in numbers) or len(set(numbers)) != len(numbers):
            raise ValueError("the claims must have distinct numbers from 1")
        return claims


class ClaimVerdict(BaseModel):
    n: int = Field(description="Number of the claim this verdict is for.")
    verdict: Literal["supported", "partial", "generic", "not_found"] = Field(
        description="supported, partial, generic (guidance or generalization with no passage; sending the merchant to "
        "a Getnet channel is a next step, not generic) or not_found."
    )
    support: str = Field(description="The passage of the evidence that supports it (at most 200 characters), or ''.")

    @field_validator("support")
    @classmethod
    def _short(cls, value: str) -> str:
        # the quote is for the reader and never enters the verdict: a longer one is cut, not a failed judgement
        return value[:SUPPORT_MAX_CHARS]


class JudgeScoreV5(BaseModel):
    claim_verdicts: list[ClaimVerdict] = Field(description="One verdict for each claim number given, no other.")
    groundedness: int = Field(description="1-5: every fact in the reply is supported by the evidence.")
    groundedness_reason: str = Field(description="One short sentence (at most 25 words).")
    factual_correctness: int = Field(description="1-5: the reply agrees with the evidence and is consistent.")
    factual_correctness_reason: str = Field(description="One short sentence (at most 25 words).")
    relevance: int = Field(description="1-5: the reply addresses what the merchant asked.")
    relevance_reason: str = Field(description="One short sentence (at most 25 words).")
    usefulness: int = Field(description="1-5: the merchant can act on the reply; clear, polite, right language.")
    usefulness_reason: str = Field(description="One short sentence (at most 25 words).")

    @field_validator(*CRITERIA)
    @classmethod
    def _scale(cls, value: int) -> int:
        if not 1 <= value <= 5:  # as in JudgeScoreV3: strict structured outputs reject numeric bounds
            raise ValueError("a score must be between 1 and 5")
        return value


def check_verdicts(claims: list[Claim], verdicts: list[ClaimVerdict]) -> None:
    """Exactly one verdict per claim number: an unknown, a missing or a repeated number makes the judgement invalid;
    nothing is filled in here."""
    expected = {claim.n for claim in claims}
    given = [verdict.n for verdict in verdicts]
    unknown = sorted(set(given) - expected)
    missing = sorted(expected - set(given))
    repeated = sorted({n for n in given if given.count(n) > 1})
    problems = [
        f"{label} claim number(s) {', '.join(map(str, numbers))}"
        for label, numbers in (("unknown", unknown), ("missing", missing), ("repeated", repeated))
        if numbers
    ]
    if problems:
        raise ClaimMismatch("the verdicts do not match the claims: " + "; ".join(problems))


def unsupported_from_claims(claims: list[dict], verdicts: list[dict]) -> bool:
    """D3: true when a claim whose kind is not `standard` is `generic` or `not_found`; `partial` does not count."""
    kinds = {claim["n"]: claim["kind"] for claim in claims}
    return any(v["verdict"] in UNSUPPORTED_VERDICTS and kinds.get(v["n"]) != "standard" for v in verdicts)


def claim_counts(claims: dict) -> dict:
    """How many claims of one judgement got each verdict, and how many are `standard` (never held against it)."""
    counts = dict.fromkeys(CLAIM_VERDICTS, 0)
    for verdict in claims["claim_verdicts"]:
        counts[verdict["verdict"]] += 1
    standard = sum(claim["kind"] == "standard" for claim in claims["claims"])
    return {"claims": len(claims["claims"]), **counts, "standard": standard}


def short_error(exc: Exception) -> str:
    """Class and a short message, masked and on one line: a provider error can echo parts of the request."""
    message = " ".join(mask_sensitive(str(exc))[0].split())
    if len(message) > MAX_ERROR_CHARS:
        message = message[: MAX_ERROR_CHARS - 3] + "..."
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def max_output_tokens_for(provider: str, rubric: str = RUBRIC_VERSION) -> int:
    """The output cap of the judgement call (the second call under judge.v5)."""
    if rubric in CLAIM_RUBRICS:
        return MAX_OUTPUT_TOKENS_V5 + THINKING_MARGIN_BY_PROVIDER.get(provider, 0)
    return MAX_OUTPUT_TOKENS_BY_PROVIDER.get(provider, MAX_OUTPUT_TOKENS)


def claims_max_output_tokens_for(provider: str) -> int:
    """The output cap of the call that lists the claims (judge.v5)."""
    return CLAIMS_MAX_OUTPUT_TOKENS + THINKING_MARGIN_BY_PROVIDER.get(provider, 0)


def judge_spec_v3(prompt: Prompt, data: dict, max_output_tokens: int = MAX_OUTPUT_TOKENS) -> CallSpec:
    return CallSpec(
        agent="judge",
        instructions=prompt.render(),
        effort="none",
        max_output_tokens=max_output_tokens,
        input=json.dumps(data, ensure_ascii=False),
    )


def tokens(usage) -> dict | None:
    """The tokens of one judgement (spec v0.9.0, task 79 round 2): the input is the whole input, of which the cache
    reads and the cache writes are parts; the output includes the thinking. `None` when the provider's usage is unknown
    (a network failure: the reservation stands as the cost)."""
    if usage is None:
        return None
    return {
        "input_tokens": usage.input_tokens,
        "cache_read_tokens": usage.cached_tokens,
        "cache_creation_tokens": usage.cache_creation_tokens,
        "output_tokens": usage.output_tokens,
    }


TOKEN_KEYS = ("input_tokens", "cache_read_tokens", "cache_creation_tokens", "output_tokens")


def add_tokens(first: dict | None, second: dict | None) -> dict | None:
    """The tokens of the two calls of a judge.v5 judgement: the sum of the parts the provider reported (`None` only
    when neither was)."""
    known = [usage for usage in (first, second) if usage]
    if not known:
        return None
    return {key: sum(int(usage.get(key) or 0) for usage in known) for key in TOKEN_KEYS}


def judge_usage(records: list[dict]) -> dict | None:
    """Tokens of the judgements that recorded them (spec v0.9.0, task 79 round 2): total and mean per judgement. A
    failed judgement the provider billed counts; one whose usage is unknown (network failure) does not."""
    known = [record["usage"] for record in records if record.get("usage")]
    if not known:
        return None
    total = {key: sum(int(usage.get(key) or 0) for usage in known) for key in TOKEN_KEYS}
    return {
        "judgements": len(known),
        "total": total,
        "mean": {key: round(value / len(known), 1) for key, value in total.items()},
    }


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
    claims_prompt: Prompt | None = None  # judge.v5 (spec v0.11.0 D3): the first call lists the claims
    claims_max_output_tokens: int = CLAIMS_MAX_OUTPUT_TOKENS

    def config(self) -> dict:
        parameters: dict = {"max_output_tokens": self.max_output_tokens, "effort": "none"}
        if self.provider == "anthropic":  # D3: thinking and effort are left to the model's defaults
            parameters = {"max_output_tokens": self.max_output_tokens, "effort": "default", "thinking": "default"}
        config = {
            "provider": self.provider,
            "model": self.model,
            "rubric": RUBRIC,
            "rubric_version": self.prompt.version,
            "prompt": self.prompt.ref,
            "independence": self.independence,
            "parameters": parameters,
        }
        if self.claims_prompt is not None:  # both prompts of a judge.v5 judgement are on record (v0.11.0 D3)
            config["claims_prompt"] = self.claims_prompt.ref
            config["parameters"] = parameters | {"claims_max_output_tokens": self.claims_max_output_tokens}
        return config

    def _failed(self, record: dict, spent_before: float, exc: Exception, usage: dict | None) -> dict:
        return record | {
            "state": "failed",
            "model_used": self.model,
            "scores": {},
            "reasons": {},
            "unsupported_claim": None,
            "cost_usd": round(getattr(self.meter, "cost_usd", 0.0) - spent_before, 8),
            "usage": usage,  # a refusal or a cut answer was billed all the same
            "error": short_error(exc),
        }

    def evaluate(
        self, data: dict, *, repetition: int = 1, claims: list[dict] | None = None, claims_origin: str | None = None
    ) -> dict:
        """One judgement. `claims` (judge.v5 only, `eval --claims-from`) is the list of a calibration sample: it is
        judged as given, without the call that lists the claims, and `claims_origin` is recorded with it."""
        if claims is not None and self.claims_prompt is None:
            raise ValueError("claims can be given only to a judge.v5 judge (--rubric v5)")
        record = {
            "evaluation_id": f"eval_{uuid.uuid4().hex[:20]}",
            "rubric_version": self.prompt.version,
            "repetition": repetition,
            "provider": self.provider,
            "model": self.model,
        }
        spent_before = getattr(self.meter, "cost_usd", 0.0)
        if self.claims_prompt is not None:
            return self._evaluate_claims(data, record, spent_before, claims, claims_origin)
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
                "usage": tokens(getattr(exc, "usage", None)),  # a refusal or a cut answer was billed all the same
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
            "usage": tokens(result.usage),
            "error": None,
        }

    def _evaluate_claims(
        self, data: dict, record: dict, spent_before: float, given: list[dict] | None = None, origin: str | None = None
    ) -> dict:
        """judge.v5: list the claims (without the evidence), then judge each one against the evidence; the verdict is
        computed from the list. A failure of either call, or verdicts that do not answer exactly the claims listed, is
        a failed judgement that keeps the tokens of every call that was billed. With `given` (the claims of a
        calibration sample) the listing call is not made."""
        record = record | {"claims": None}
        if given is not None:
            try:
                listed = ClaimList(claims=given).claims
            except Exception as exc:  # a malformed list: a failed judgement, and no call was made
                return self._failed(record, spent_before, exc, None)
            used = None
        else:
            listing = {key: data.get(key) for key in CLAIMS_INPUT}
            try:
                spec = judge_spec_v3(self.claims_prompt, listing, self.claims_max_output_tokens)
                first = self.llm.parse(spec, ClaimList, self.meter)
            except Exception as exc:  # recorded, never raised, as in `evaluate`
                return self._failed(record, spent_before, exc, tokens(getattr(exc, "usage", None)))
            used = tokens(first.usage)
            listed = first.value.claims
        claims = [claim.model_dump() for claim in sorted(listed, key=lambda claim: claim.n)]
        try:
            spec = judge_spec_v3(self.prompt, data | {"claims": claims}, self.max_output_tokens)
            second = self.llm.parse(spec, JudgeScoreV5, self.meter)
        except Exception as exc:
            return self._failed(record, spent_before, exc, add_tokens(used, tokens(getattr(exc, "usage", None))))
        used = add_tokens(used, tokens(second.usage))
        score = second.value
        try:
            check_verdicts(listed, score.claim_verdicts)
        except ClaimMismatch as exc:
            return self._failed(record, spent_before, exc, used)
        verdicts = [verdict.model_dump() for verdict in sorted(score.claim_verdicts, key=lambda verdict: verdict.n)]
        found = {"claims": claims, "claim_verdicts": verdicts}
        if given is not None:  # where the claims came from, kept with them (the column `claims` and `result`)
            found["origin"] = origin or "amostra:"
        return record | {
            "state": "completed",
            "model_used": second.model,
            "scores": {criterion: getattr(score, criterion) for criterion in CRITERIA},
            "reasons": {criterion: getattr(score, f"{criterion}_reason") for criterion in CRITERIA},
            "unsupported_claim": unsupported_from_claims(claims, verdicts),
            "claims": found,
            "cost_usd": round(getattr(self.meter, "cost_usd", 0.0) - spent_before, 8),
            "usage": used,
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


def validate_judge(settings, *, agent: tuple[str, str], rubric: str | None = None) -> JudgeSetup:
    """Validate provider, price, independence, key and prompt without constructing a provider client. `rubric` picks
    the prompt (`judge.v5` by default; `judge.v3` and `judge.v4` remain available when explicitly named). `judge.v5`
    also loads the claim-list prompt, spec v0.11.0 D3."""
    version = rubric_version(rubric)
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
    prompt = load_prompt(settings.prompts_dir, RUBRIC, version)
    claims_prompt = load_prompt(settings.prompts_dir, *CLAIM_RUBRICS[version]) if version in CLAIM_RUBRICS else None
    return JudgeSetup(agent, provider, model, prompt, independence, claims_prompt)


def resolve_judge(
    settings,
    *,
    agent: tuple[str, str],
    meter: Meter | None = None,
    factory: Callable[[str, str], LLM] | None = None,
    validated: JudgeSetup | None = None,
    rubric: str | None = None,
) -> Judge:
    """Build a judge after validation; its spending meter can be bound after the run guard exists."""
    setup = validated or validate_judge(settings, agent=agent, rubric=rubric)
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
        max_output_tokens_for(setup.provider, setup.prompt.version),
        claims_prompt=setup.claims_prompt,
        claims_max_output_tokens=claims_max_output_tokens_for(setup.provider),
    )


# --- persistence ----------------------------------------------------------------------------------------------------


def save_evaluation(
    conn, *, request_id: str, judge: Judge, record: dict, data: dict, run: str | None = None
) -> None:
    """Writes one judgement into `run_evaluations` (the columns 0011 added hold the queryable parts; `result` holds
    the whole judgement). Campaign judgements belong to the principal `cli:eval`, so no API session ever lists them.
    `run` is the name of the execution that wrote it (the report name of `eval`, spec v0.9.0 D1), kept in `evaluator`
    so a comparison can tell the probe from the repetitions; `result` also keeps the judgement's tokens. No column is
    added for either. A completed judge.v5 judgement also writes its claims and their verdicts into the column `claims`
    (0013) and into `result`, so a rollback of 0013 loses nothing (spec v0.11.0 D3)."""
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
    claims = record.get("claims") if completed else None
    if claims:
        result["claims"] = claims
    if record.get("usage"):
        result["usage"] = record["usage"]
    evaluator = judge.config() | {"model_used": record["model_used"]} | ({"run": run} if run else {})
    conn.execute(
        "INSERT INTO run_evaluations (evaluation_id,request_id,principal_id,method,rubric,rubric_version,evaluator,"
        "config_digest,result,evidence,critical_failures,cost_usd,state,error,created_at,scores,repetition,"
        "unsupported_claim,claims) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
            json.dumps(claims, sort_keys=True, ensure_ascii=False) if claims else None,
        ),
    )
