"""Prometheus text exposition (format 0.0.4) computed on demand from the traces and the budget ledger (spec v0.10.0,
D4). No Prometheus library: the values come from what the system already stores, read-only, cached for 5 s.

No label carries message text, a request id, a merchant or an operator: routes, statuses, agents and replan origins
come from the code, and a tool label is a registered tool name or `other`."""

from __future__ import annotations

import re
import sqlite3
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from merchant_assistant.llm.pricing import prices
from merchant_assistant.tools.registry import TOOLS

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"
CACHE_SECONDS = 5.0
DURATION_BUCKETS = (1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0)  # seconds; +Inf is added on exposition
_SAFE_LABEL = re.compile(r"^[a-z0-9_:.\-]{1,64}$")


def _label(value: object) -> str:
    """Only short code identifiers become label values; anything else is `other`."""
    text = "unknown" if value is None else str(value)
    return text if _SAFE_LABEL.match(text) else "other"


def _tool(name: str) -> str:
    return name if name in TOOLS else "other"  # a model may ask for an unregistered name: it never becomes a label


def _provider(model: str) -> str:
    if model.startswith("scripted"):
        return "scripted"
    entry = prices()["models"].get(model)
    return _label(entry.get("provider")) if entry else "unknown"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _number(value: float) -> str:
    if value == float("inf"):
        return "+Inf"
    return repr(float(value)) if not float(value).is_integer() else str(int(value))


@contextmanager
def _read_only(path: Path | str) -> Iterator[sqlite3.Connection | None]:
    """A missing database yields nothing (and is never created by a scrape)."""
    if str(path) == ":memory:" or not Path(path).is_file():
        yield None
        return
    conn = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True, timeout=5)
    try:
        yield conn
    finally:
        conn.close()


class Family:
    def __init__(self, name: str, kind: str, help_text: str) -> None:
        self.name, self.kind, self.help = name, kind, help_text
        self.samples: list[tuple[str, dict[str, str], float]] = []

    def add(self, value: float, suffix: str = "", **labels: str) -> None:
        self.samples.append((self.name + suffix, labels, value))

    def render(self) -> list[str]:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} {self.kind}"]
        for name, labels, value in self.samples:
            body = ",".join(f'{k}="{_escape(v)}"' for k, v in labels.items())
            lines.append(f"{name}{{{body}}} {_number(value)}" if body else f"{name} {_number(value)}")
        return lines


def _trace_families(path: Path | str) -> list[Family]:
    requests = Family("requests_total", "counter", "Assistant requests by route and status, from the traces.")
    model_calls = Family("model_calls_total", "counter", "Settled model calls by agent, from the traces.")
    tool_calls = Family("tool_calls_total", "counter", "Tool calls by tool and outcome (ok or error).")
    tool_failures = Family("tool_failures_total", "counter", "Tool calls that ended in error, by tool.")
    handoffs = Family("handoffs_total", "counter", "Requests that ended in a human handoff.")
    replans = Family("replan_total", "counter", "Replanner decisions by origin (rule:<name> or model).")
    duration = Family("request_duration_seconds", "histogram", "Request duration in seconds, from the traces.")
    tools: dict[tuple[str, str], int] = {}
    failures: dict[str, int] = {}
    buckets = [0] * len(DURATION_BUCKETS)
    count, total_seconds, handoff_count = 0, 0.0, 0
    with _read_only(path) as conn:
        if conn is not None:
            agg: dict[tuple[str, str], int] = {}
            for route, status, n in conn.execute("SELECT route, status, COUNT(*) FROM requests GROUP BY 1, 2"):
                key = (_label(route), _label(status))
                agg[key] = agg.get(key, 0) + n
                handoff_count += n if status == "handoff" else 0
            for (route, status), n in sorted(agg.items()):
                requests.add(n, route=route, status=status)
            calls: dict[str, int] = {}
            for agent, n in conn.execute(
                "SELECT j.key, SUM(COALESCE(json_extract(j.value, '$.calls'), 0)) FROM requests, "
                "json_each(CASE WHEN json_valid(requests.detail) THEN requests.detail ELSE '{}' END, "
                "'$.models_by_agent') AS j GROUP BY 1"
            ):
                calls[_label(agent)] = calls.get(_label(agent), 0) + int(n or 0)
            for agent, n in sorted(calls.items()):
                model_calls.add(n, agent=agent)
            for step, status, n in conn.execute(
                "SELECT step, status, COUNT(*) FROM steps WHERE step LIKE 'tool:%' GROUP BY 1, 2"
            ):
                tool, outcome = _tool(step[len("tool:") :]), "ok" if status == "ok" else "error"
                tools[(tool, outcome)] = tools.get((tool, outcome), 0) + n
                if outcome == "error":
                    failures[tool] = failures.get(tool, 0) + n
            origins: dict[str, int] = {}
            for origin, n in conn.execute(
                "SELECT CASE WHEN json_valid(detail) THEN json_extract(detail, '$.origin') END, COUNT(*) "
                "FROM steps WHERE step = 'replan' GROUP BY 1"
            ):
                origins[_label(origin)] = origins.get(_label(origin), 0) + n
            for origin, n in sorted(origins.items()):
                replans.add(n, origin=origin)
            for (duration_ms,) in conn.execute("SELECT COALESCE(duration_ms, 0) FROM requests"):
                seconds = duration_ms / 1000
                count, total_seconds = count + 1, total_seconds + seconds
                for i, bound in enumerate(DURATION_BUCKETS):
                    buckets[i] += seconds <= bound
    for (tool, outcome), n in sorted(tools.items()):
        tool_calls.add(n, tool=tool, outcome=outcome)
    for tool, n in sorted(failures.items()):
        tool_failures.add(n, tool=tool)
    handoffs.add(handoff_count)
    for bound, n in zip(DURATION_BUCKETS, buckets, strict=True):
        duration.add(n, "_bucket", le=_number(bound))
    duration.add(count, "_bucket", le="+Inf")
    duration.add(round(total_seconds, 3), "_sum")
    duration.add(count, "_count")
    return [requests, model_calls, tool_calls, tool_failures, handoffs, replans, duration]


def _ledger_families(path: Path | str, limit_usd: float) -> list[Family]:
    cost = Family("cost_usd_total", "counter", "Settled spend in USD by provider, from the budget ledger.")
    remaining = Family("budget_remaining_usd", "gauge", "Budget left in USD (limit minus settled and reserved).")
    limit = Family("budget_limit_usd", "gauge", "Configured budget limit in USD.")
    by_provider: dict[str, float] = {}
    committed = 0.0
    with _read_only(path) as conn:
        if conn is not None:
            for model, settled, reserved in conn.execute(
                "SELECT model, SUM(CASE WHEN status='settled' THEN actual_usd ELSE 0 END), "
                "SUM(CASE WHEN status='reserved' THEN reserved_usd ELSE 0 END) FROM ledger GROUP BY 1"
            ):
                provider = _provider(model)
                by_provider[provider] = by_provider.get(provider, 0.0) + float(settled or 0)
                committed += float(settled or 0) + float(reserved or 0)
    for provider, usd in sorted(by_provider.items()):
        cost.add(round(usd, 8), provider=provider)
    remaining.add(round(max(limit_usd - committed, 0.0), 8))
    limit.add(limit_usd)
    return [cost, remaining, limit]


def render(traces_path: Path | str, ledger_path: Path | str, limit_usd: float) -> str:
    families = [*_trace_families(traces_path), *_ledger_families(ledger_path, limit_usd)]
    return "\n".join(line for family in families for line in family.render()) + "\n"


class MetricsCollector:
    """Renders the exposition at most once per `CACHE_SECONDS` in this process."""

    def __init__(
        self,
        traces_path: Path | str,
        ledger_path: Path | str,
        limit_usd: float,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.traces_path, self.ledger_path, self.limit_usd, self.clock = traces_path, ledger_path, limit_usd, clock
        self._lock = threading.Lock()
        self._cached: tuple[float, str] | None = None

    def text(self) -> str:
        with self._lock:
            now = self.clock()
            if self._cached is None or now - self._cached[0] >= CACHE_SECONDS:
                self._cached = (now, render(self.traces_path, self.ledger_path, self.limit_usd))
            return self._cached[1]


def collector_for(orchestrator: object, settings: object) -> MetricsCollector:
    """The stores the orchestrator writes to; the runtime defaults when it has none (placeholder)."""
    runtime = settings.runtime_path  # type: ignore[attr-defined]
    traces_path = getattr(getattr(orchestrator, "traces", None), "path", None) or runtime / "traces.sqlite3"
    budget = getattr(orchestrator, "budget", None)
    budget = getattr(budget, "primary", budget)  # a combined guard: the installation ledger
    ledger_path = getattr(budget, "path", None) or runtime / "budget.sqlite3"
    limit = getattr(budget, "limit_usd", None)
    return MetricsCollector(traces_path, ledger_path, settings.budget_limit_usd if limit is None else limit)  # type: ignore[attr-defined]
