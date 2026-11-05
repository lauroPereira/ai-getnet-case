"""Anthropic Messages API implementation, for the campaign judge only (spec v0.9.0 D3).

`parse` sends `system` = instructions and one user message = input, asks for structured output with
`output_config.format` (the JSON schema of the Pydantic model, made strict by the SDK's `transform_schema`: every
property required, no additional properties) and leaves `thinking` and `output_config.effort` out, so the model runs
with its defaults. A `refusal` or `max_tokens` stop is an `LLMError`, never a score. Tools and web search are not
offered: the judge only parses."""

from __future__ import annotations

from typing import Any

from merchant_assistant.llm.base import (
    CallSpec,
    LLMError,
    LLMResult,
    Meter,
    T,
    ToolCaller,
    Usage,
    WebAnswer,
    estimate_tokens,
)

NOT_SUPPORTED = "not supported for the judge in v0.9.0"
# A judgement with adaptive thinking can write up to 2 000 tokens; 30 s (the OpenAI adapter's bound, sized for the
# agents) cuts it short. A request deadline, when the meter has one, still wins.
CALL_TIMEOUT_S = 120.0
FAILED_STOPS = {"refusal", "max_tokens", "model_context_window_exceeded"}


def _call_timeout(meter: Meter | None) -> float:
    remaining = getattr(meter, "remaining_seconds", None)
    if remaining is None:
        return CALL_TIMEOUT_S
    return max(3.0, min(CALL_TIMEOUT_S, remaining() - 2.0))


def output_format(schema: type[T]) -> dict:
    from anthropic import transform_schema

    return {"type": "json_schema", "schema": transform_schema(schema)}


def _usage(response: Any) -> Usage:
    """Anthropic reports the uncached input, the cache reads and the cache writes apart; `Usage.input_tokens` is their
    sum, as for OpenAI, with the two cached parts kept so `pricing.cost` prices each at its rate."""
    u = response.usage
    read = getattr(u, "cache_read_input_tokens", None) or 0
    written = getattr(u, "cache_creation_input_tokens", None) or 0
    return Usage(
        input_tokens=(u.input_tokens or 0) + read + written,
        output_tokens=u.output_tokens or 0,
        cached_tokens=read,
        cache_creation_tokens=written,
    )


class AnthropicLLM:
    def __init__(self, client: Any, model: str) -> None:
        self.client, self.model = client, model

    def parse(self, spec: CallSpec, schema: type[T], meter: Meter) -> LLMResult[T]:
        reservation = meter.reserve(
            agent=spec.agent,
            model=self.model,
            est_input_tokens=estimate_tokens(spec.instructions, spec.input),
            max_output_tokens=spec.max_output_tokens,
            effective_parameters={"max_output_tokens": spec.max_output_tokens},
        )
        try:
            response = self.client.messages.create(
                model=self.model,
                system=spec.instructions,
                messages=[{"role": "user", "content": spec.input}],
                max_tokens=spec.max_output_tokens,
                output_config={"format": output_format(schema)},
                timeout=_call_timeout(meter),
            )
        except Exception as exc:  # provider errors become LLMError; usage unknown -> settle as reserved
            meter.settle(reservation, None)
            raise LLMError(f"{spec.agent}: {type(exc).__name__}: {exc}") from exc
        usage = _usage(response)
        meter.settle(reservation, usage)
        stop = getattr(response, "stop_reason", None)
        if stop in FAILED_STOPS:
            raise LLMError(f"{spec.agent}: no structured output (stop_reason={stop})")
        text = "".join(
            getattr(block, "text", "") for block in response.content if getattr(block, "type", "") == "text"
        )
        if not text.strip():
            raise LLMError(f"{spec.agent}: no structured output (stop_reason={stop}, empty text)")
        try:
            value = schema.model_validate_json(text)
        except ValueError as exc:  # pydantic.ValidationError is a ValueError
            raise LLMError(f"{spec.agent}: structured output does not match the schema: {exc}") from exc
        return LLMResult(value, usage, getattr(response, "model", None) or self.model)

    def run_tools(
        self,
        spec: CallSpec,
        schema: type[T],
        meter: Meter,
        *,
        tools: list[dict],
        call_tool: ToolCaller,
        max_tool_calls: int,
    ) -> LLMResult[T]:
        raise LLMError(f"{spec.agent}: tool calls are {NOT_SUPPORTED}")

    def web_search(self, spec: CallSpec, meter: Meter, *, max_calls: int = 1) -> LLMResult[WebAnswer]:
        raise LLMError(f"{spec.agent}: web search is {NOT_SUPPORTED}")
