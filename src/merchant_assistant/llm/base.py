"""Provider-agnostic model interface used by the agents.

Every paid call goes through a `Meter` (per request): it reserves budget and checks limits before the call and
settles the real usage after it. Implementations: OpenAI (real) and Scripted (deterministic tests).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any, Generic, Literal, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
Effort = Literal["none", "low", "medium", "high"]


class LLMError(Exception):
    """The provider failed or returned an unusable answer."""


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    web_search_calls: int = 0

    def add(self, other: Usage) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cached_tokens += other.cached_tokens
        self.web_search_calls += other.web_search_calls


@dataclass
class LLMResult(Generic[T]):
    value: T
    usage: Usage
    model: str


class WebAnswer(BaseModel):
    text: str
    citations: list[dict] = []


class Meter(Protocol):
    def reserve(
        self,
        *,
        agent: str,
        model: str,
        est_input_tokens: int,
        max_output_tokens: int,
        web_search_calls: int = 0,
        effective_parameters: dict[str, int] | None = None,
    ) -> Any: ...

    def settle(self, reservation: Any, usage: Usage) -> None: ...


class NullMeter:
    def reserve(self, **_: Any) -> None:
        return None

    def settle(self, reservation: Any, usage: Usage) -> None:
        return None


ToolCaller = Callable[[str, dict], str]


@dataclass
class CallSpec:
    """What an agent asks of the model. `context` carries structured data for scripted tests; real providers
    only see `instructions` and `input`."""

    agent: str
    instructions: str
    input: str
    effort: Effort = "none"
    max_output_tokens: int = 800
    context: dict = field(default_factory=dict)


class LLM(Protocol):
    model: str

    def parse(self, spec: CallSpec, schema: type[T], meter: Meter) -> LLMResult[T]: ...

    def run_tools(
        self,
        spec: CallSpec,
        schema: type[T],
        meter: Meter,
        *,
        tools: list[dict],
        call_tool: ToolCaller,
        max_tool_calls: int,
    ) -> LLMResult[T]: ...

    def web_search(self, spec: CallSpec, meter: Meter, *, max_calls: int = 1) -> LLMResult[WebAnswer]: ...


class OutputTokenLimitLLM:
    """Apply a profile's output cap before metering and forwarding a model call."""

    def __init__(self, llm: LLM, max_output_tokens: int) -> None:
        self._llm = llm
        self.model = llm.model
        self.max_output_tokens = max_output_tokens
        self.effective_parameters = {"max_output_tokens": max_output_tokens}

    def _bounded(self, spec: CallSpec) -> CallSpec:
        return replace(spec, max_output_tokens=min(spec.max_output_tokens, self.max_output_tokens))

    def effective_parameters_for(self, spec: CallSpec) -> dict[str, int]:
        return {"max_output_tokens": min(spec.max_output_tokens, self.max_output_tokens)}

    def _meter(self, meter: Meter, spec: CallSpec) -> Meter:
        parameters = {"max_output_tokens": spec.max_output_tokens}

        class EffectiveParameterMeter:
            def reserve(self, **kwargs: Any) -> Any:
                kwargs["effective_parameters"] = parameters
                return meter.reserve(**kwargs)

            def settle(self, reservation: Any, usage: Usage | None) -> None:
                meter.settle(reservation, usage)

            def __getattr__(self, name: str) -> Any:
                return getattr(meter, name)

        return EffectiveParameterMeter()

    def parse(self, spec: CallSpec, schema: type[T], meter: Meter) -> LLMResult[T]:
        bounded = self._bounded(spec)
        return self._llm.parse(bounded, schema, self._meter(meter, bounded))

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
        bounded = self._bounded(spec)
        return self._llm.run_tools(
            bounded,
            schema,
            self._meter(meter, bounded),
            tools=tools,
            call_tool=call_tool,
            max_tool_calls=max_tool_calls,
        )

    def web_search(self, spec: CallSpec, meter: Meter, *, max_calls: int = 1) -> LLMResult[WebAnswer]:
        bounded = self._bounded(spec)
        return self._llm.web_search(bounded, self._meter(meter, bounded), max_calls=max_calls)


def estimate_tokens(*texts: str) -> int:
    return sum(len(t) for t in texts) // 3 + 50
