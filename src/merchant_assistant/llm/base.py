"""Provider-agnostic model interface used by the agents.

Every paid call goes through a `Meter` (per request): it reserves budget and checks limits before the call and
settles the real usage after it. Implementations: OpenAI (real) and Scripted (deterministic tests).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
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
        self, *, agent: str, model: str, est_input_tokens: int, max_output_tokens: int, web_search_calls: int = 0
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


def estimate_tokens(*texts: str) -> int:
    return sum(len(t) for t in texts) // 3 + 50
