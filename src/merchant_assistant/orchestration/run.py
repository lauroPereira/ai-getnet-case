"""Per-request run context: dependencies, limits, budget metering, tool execution and trace."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from merchant_assistant.config import Settings
from merchant_assistant.data.clock import Clock
from merchant_assistant.llm import pricing
from merchant_assistant.llm.base import LLM, Usage
from merchant_assistant.observability.traces import TraceRecorder
from merchant_assistant.orchestration.budget import BudgetExceeded, BudgetGuard
from merchant_assistant.rag.index import KnowledgeIndex
from merchant_assistant.tools.base import ToolEnv
from merchant_assistant.tools.registry import ToolOutcome, execute


class LimitExceeded(Exception):
    def __init__(self, kind: str) -> None:
        super().__init__(f"request limit reached: {kind}")
        self.kind = kind


@dataclass
class Reservation:
    ledger_id: int
    agent: str
    model: str
    amount: float


@dataclass
class RunContext:
    request_id: str
    settings: Settings
    llm: LLM
    index: KnowledgeIndex | None
    budget: BudgetGuard
    trace: TraceRecorder
    tools: ToolEnv
    clock: Clock
    model_calls: int = 0
    tool_calls: int = 0
    cost_usd: float = 0.0
    outcomes: list[ToolOutcome] = field(default_factory=list)
    usage_by_agent: dict[str, dict] = field(default_factory=dict)
    step_notes: dict[str, Any] = field(default_factory=dict)
    started: float = field(default_factory=time.perf_counter)

    # --- limits ---------------------------------------------------------------------------------------------------

    def check_time(self) -> None:
        if time.perf_counter() - self.started > self.settings.max_request_seconds:
            raise LimitExceeded("time")

    def remaining_seconds(self) -> float:
        return self.settings.max_request_seconds - (time.perf_counter() - self.started)

    # --- Meter protocol -------------------------------------------------------------------------------------------

    def reserve(
        self, *, agent: str, model: str, est_input_tokens: int, max_output_tokens: int, web_search_calls: int = 0
    ) -> Reservation:
        self.check_time()
        if self.model_calls >= self.settings.max_model_calls:
            raise LimitExceeded("model_calls")
        amount = pricing.estimate(model, est_input_tokens, max_output_tokens, web_search_calls)
        if self.cost_usd + amount > self.settings.max_request_cost_usd:
            raise BudgetExceeded("request", amount, self.settings.max_request_cost_usd - self.cost_usd)
        ledger_id = self.budget.reserve(request_id=self.request_id, agent=agent, model=model, amount=amount)
        self.model_calls += 1
        return Reservation(ledger_id, agent, model, amount)

    def settle(self, reservation: Reservation | None, usage: Usage | None) -> None:
        if reservation is None:
            return
        actual = pricing.cost(reservation.model, usage) if usage else None
        self.budget.settle(reservation.ledger_id, actual)
        spent = reservation.amount if actual is None else actual
        self.cost_usd += spent
        agg = self.usage_by_agent.setdefault(
            reservation.agent,
            {"calls": 0, "input_tokens": 0, "output_tokens": 0, "web_search_calls": 0, "cost_usd": 0.0},
        )
        agg["calls"] += 1
        agg["cost_usd"] = round(agg["cost_usd"] + spent, 8)
        if usage:
            agg["input_tokens"] += usage.input_tokens
            agg["output_tokens"] += usage.output_tokens
            agg["web_search_calls"] += usage.web_search_calls

    # --- tools ----------------------------------------------------------------------------------------------------

    def run_tool(self, name: str, args: dict, *, agent: str | None) -> ToolOutcome:
        if self.tool_calls >= self.settings.max_tool_calls:
            outcome = ToolOutcome(name, args, False, error={"code": "LIMIT_REACHED", "message": "Tool limit reached."})
        else:
            self.check_time()
            self.tool_calls += 1
            step, t0 = self.trace.start(f"tool:{name}")
            outcome = execute(name, args, self.tools, agent=agent)
            self.trace.finish(
                step, t0, "ok" if outcome.ok else "error", arguments=args, error=outcome.error, agent=agent or "host"
            )
        self.outcomes.append(outcome)
        return outcome

    def tool_caller(self, agent: str):
        def call(name: str, args: dict) -> str:
            return self.run_tool(name, args, agent=agent).for_model()

        return call

    def summary(self) -> dict[str, Any]:
        return {
            "model_calls": self.model_calls,
            "tool_calls": self.tool_calls,
            "cost_usd": round(self.cost_usd, 8),
            "usage_by_agent": self.usage_by_agent,
        }
