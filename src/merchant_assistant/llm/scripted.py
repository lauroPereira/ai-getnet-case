"""Deterministic model for tests: a handler decides each answer from the call spec (including `context`).

It runs the same metering, tool execution and validation paths as the real provider, at zero cost.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from merchant_assistant.llm.base import CallSpec, LLMError, LLMResult, Meter, T, ToolCaller, Usage, WebAnswer


@dataclass
class ScriptedCall:
    kind: str  # parse | tools | web
    spec: CallSpec
    schema: type[BaseModel] | None = None


@dataclass
class ToolPlan:
    """Tool calls to execute, then `final(results)` builds the structured answer from the tool outputs."""

    calls: list[tuple[str, dict]]
    final: Callable[[list[str]], Any]
    follow_up: Callable[[list[str]], list[tuple[str, dict]]] | None = None


@dataclass
class ScriptedLLM:
    handler: Callable[[ScriptedCall], Any]
    model: str = "scripted-v1"
    calls: list[ScriptedCall] = field(default_factory=list)

    def _usage(self, spec: CallSpec) -> Usage:
        return Usage(input_tokens=(len(spec.instructions) + len(spec.input)) // 4, output_tokens=60)

    def _answer(self, call: ScriptedCall) -> Any:
        self.calls.append(call)
        answer = self.handler(call)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def parse(self, spec: CallSpec, schema: type[T], meter: Meter) -> LLMResult[T]:
        reservation = meter.reserve(
            agent=spec.agent, model=self.model, est_input_tokens=100, max_output_tokens=spec.max_output_tokens
        )
        try:
            raw = self._answer(ScriptedCall("parse", spec, schema))
        except LLMError:
            meter.settle(reservation, None)
            raise
        usage = self._usage(spec)
        meter.settle(reservation, usage)
        return LLMResult(schema.model_validate(raw), usage, self.model)

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
        reservation = meter.reserve(
            agent=spec.agent, model=self.model, est_input_tokens=100, max_output_tokens=spec.max_output_tokens
        )
        plan = self._answer(ScriptedCall("tools", spec, schema))
        meter.settle(reservation, self._usage(spec))
        if not isinstance(plan, ToolPlan):
            return LLMResult(schema.model_validate(plan), self._usage(spec), self.model)
        allowed = {t["name"] for t in tools}
        results: list[str] = []
        pending = list(plan.calls)
        while pending:
            for name, args in pending:
                if name not in allowed:
                    raise LLMError(f"scripted plan used a tool not offered: {name}")
                if len(results) >= max_tool_calls:
                    results.append('{"error": {"code": "LIMIT_REACHED", "message": "Tool limit reached."}}')
                    continue
                results.append(call_tool(name, args))
            pending = plan.follow_up(results) if plan.follow_up else []
            plan.follow_up = None
            if pending:
                reservation = meter.reserve(
                    agent=spec.agent, model=self.model, est_input_tokens=100, max_output_tokens=spec.max_output_tokens
                )
                meter.settle(reservation, self._usage(spec))
        return LLMResult(schema.model_validate(plan.final(results)), self._usage(spec), self.model)

    def web_search(self, spec: CallSpec, meter: Meter, *, max_calls: int = 1) -> LLMResult[WebAnswer]:
        reservation = meter.reserve(
            agent=spec.agent,
            model=self.model,
            est_input_tokens=100,
            max_output_tokens=spec.max_output_tokens,
            web_search_calls=max_calls,
        )
        try:
            raw = self._answer(ScriptedCall("web", spec))
        except LLMError:
            meter.settle(reservation, None)
            raise
        usage = Usage(100, 60, 0, 1)
        meter.settle(reservation, usage)
        return LLMResult(WebAnswer.model_validate(raw), usage, self.model)
