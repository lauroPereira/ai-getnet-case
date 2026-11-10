"""Optional OTLP export of the request traces (spec v0.13.0, D6, CA-72; task 101).

Each saved trace becomes one `turn` span with one child span per recorded step (node, tool call, operator reply),
carrying the step's own start, duration and status. The spans are built after the fact from what `TraceStore` saves,
so the attendance code does not change and a failed export never touches a reply.

Off by default: with `OTEL_EXPORTER_OTLP_ENDPOINT` empty this module imports nothing from `opentelemetry`; with an
endpoint but without the `[otel]` extra (SDK and OTLP/HTTP exporter) it logs one warning and exports nothing. The
provider is private to the assistant (never the global one), so only these spans leave the process, and they go
through a `BatchSpanProcessor` with a bounded queue and a short export timeout: an unreachable collector costs a
background thread, never the turn.

Every attribute comes from a closed set defined in the code (route, status, step, step status, agent, replan
origin, provider), and the span names too: no message text, merchant, operator, request or conversation id, token or
error text reaches a span."""

from __future__ import annotations

import logging
import os
import socket
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from merchant_assistant.observability.metrics import AGENTS, ORIGINS, ROUTES, STATUSES, _closed, _provider
from merchant_assistant.tools.registry import TOOLS

log = logging.getLogger("merchant_assistant.otel")

SERVICE_NAME = "merchant-assistant"
EXPORT_TIMEOUT_SECONDS = 2  # per OTLP request, retries included
SCHEDULE_DELAY_MILLIS = 2000
MAX_QUEUE_SIZE = 2048  # spans waiting for export; beyond it the processor drops instead of blocking

# Closed vocabularies. tests/integration/test_v0130_otel.py checks the node names against both graphs, so a new node
# left out of here fails the suite instead of becoming `other`.
NODE_STEPS = frozenset(
    {
        "input_guard", "router", "confirmation", "knowledge", "web", "support_prefix", "support", "replan",
        "escalation", "personality", "output_guard", "human_review", "human_reply", "summary",
    }
)  # fmt: skip
STEPS = NODE_STEPS | {f"tool:{name}" for name in (*TOOLS, "other")}  # a model may ask for an unregistered tool
STEP_STATUSES = frozenset({"ok", "error", "exception", "interrupted"})
TOOL_AGENTS = AGENTS | {"host"}  # a tool call made by the graph itself is recorded with agent "host"
ATTRIBUTES = {  # attribute key -> the closed set its values come from (with `other` for anything outside it)
    "assistant.route": ROUTES,
    "assistant.status": STATUSES,
    "assistant.step": STEPS,
    "assistant.step.status": STEP_STATUSES,
    "assistant.agent": TOOL_AGENTS,
    "assistant.replan.origin": ORIGINS,
    "assistant.providers": None,  # sequence of `metrics._provider` values: the providers of the price table
}


@dataclass
class SpanPlan:
    name: str
    start_ns: int
    end_ns: int
    status: str  # ok | error | unset
    attributes: dict[str, str | tuple[str, ...]]
    children: list[SpanPlan] = field(default_factory=list)


EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _ns(iso: str) -> int:
    return (datetime.fromisoformat(iso) - EPOCH) // timedelta(microseconds=1) * 1000


def _providers(usage: object) -> tuple[str, ...]:
    models = usage.get("models", []) if isinstance(usage, dict) else []
    return tuple(sorted({_provider(m) for m in models if isinstance(m, str)}))


def _step_name(step: object) -> str:
    if isinstance(step, str) and step.startswith("tool:"):
        return f"tool:{_closed(step[len('tool:') :], frozenset(TOOLS))}"
    return _closed(step, NODE_STEPS)


def span_plan(recorder: object, summary: dict) -> SpanPlan:
    """The spans of one saved trace: pure, so the closed attributes are tested without the SDK."""
    detail = summary.get("detail") if isinstance(summary.get("detail"), dict) else {}
    usage = detail.get("models_by_agent") if isinstance(detail.get("models_by_agent"), dict) else {}
    children: list[SpanPlan] = []
    for step in recorder.steps:  # type: ignore[attr-defined]
        name = _step_name(step.step)
        status = _closed(step.status, STEP_STATUSES)
        attributes: dict[str, str | tuple[str, ...]] = {"assistant.step": name, "assistant.step.status": status}
        if name.startswith("tool:"):
            attributes["assistant.agent"] = _closed(step.detail.get("agent"), TOOL_AGENTS)
        elif name in AGENTS:
            attributes["assistant.agent"] = name
            if providers := _providers(usage.get(name)):
                attributes["assistant.providers"] = providers
        if name == "replan":
            attributes["assistant.replan.origin"] = _closed(step.detail.get("origin"), ORIGINS)
        start = _ns(step.started_at)
        children.append(
            SpanPlan(
                name=name,
                start_ns=start,
                end_ns=start + int(step.duration_ms) * 1_000_000,
                status="ok" if status == "ok" else "error" if status in ("error", "exception") else "unset",
                attributes=attributes,
            )
        )
    # the duration is the one TraceStore.save stored (read once there); the step start is recorded to the
    # millisecond, so the turn spans its children whatever the rounding
    duration_ms = recorder.duration_ms if recorder.duration_ms is not None else recorder.elapsed_ms  # type: ignore[attr-defined]
    start = min([recorder.started_ns, *(c.start_ns for c in children)])  # type: ignore[attr-defined]
    end = max([recorder.started_ns + duration_ms * 1_000_000, *(c.end_ns for c in children)])  # type: ignore[attr-defined]
    turn: dict[str, str | tuple[str, ...]] = {
        "assistant.route": _closed(summary.get("route"), ROUTES),
        "assistant.status": _closed(summary.get("status"), STATUSES),
    }
    if providers := tuple(sorted({p for usage_of in usage.values() for p in _providers(usage_of)})):
        turn["assistant.providers"] = providers
    failed = any(c.attributes["assistant.step.status"] == "exception" for c in children)
    return SpanPlan("turn", start, end, "error" if failed else "ok", turn, children)


class OtelExporter:
    """Writes the spans of a saved trace through an OpenTelemetry tracer. `in_context(span)` makes a span the parent of
    the next ones, `status(code)` builds the span status and `root()` is an empty context (a turn is always a root
    span, whatever the HTTP layer has as current). Never raises."""

    def __init__(
        self,
        tracer: object,
        *,
        in_context: Callable[[object], object],
        status: Callable[[str], object],
        root: Callable[[], object],
        provider: object | None = None,
    ) -> None:
        self.tracer, self.in_context, self.status, self.root, self.provider = tracer, in_context, status, root, provider

    def __call__(self, recorder: object, summary: dict) -> None:
        try:
            self._emit(span_plan(recorder, summary), self.root())
        except Exception:  # telemetry must never break a reply
            log.warning("otel: span export failed", exc_info=True)

    def _emit(self, plan: SpanPlan, context: object) -> None:
        span = self.tracer.start_span(  # type: ignore[attr-defined]
            plan.name, context=context, attributes=plan.attributes, start_time=plan.start_ns
        )
        try:
            parent = self.in_context(span)
            for child in plan.children:
                self._emit(child, parent)
        finally:
            span.set_status(self.status(plan.status))
            span.end(end_time=plan.end_ns)


def traces_endpoint(base: str) -> str:
    """`OTEL_EXPORTER_OTLP_ENDPOINT` is the collector's base URL; the OTLP/HTTP traces path is appended once."""
    base = base.strip().rstrip("/")
    return base if base.endswith("/v1/traces") else f"{base}/v1/traces"


def instance_id() -> str:
    """`service.instance.id` of the OTLP resource: host and pid, one per API worker (the exporter is built in each)."""
    return f"{socket.gethostname()}:{os.getpid()}"


def exporter_from_settings(settings: object) -> OtelExporter | None:
    """The span exporter when an endpoint is configured and the `[otel]` extra is installed; None otherwise."""
    endpoint = (getattr(settings, "otel_exporter_otlp_endpoint", "") or "").strip()
    if not endpoint:
        return None
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        log.warning("otel: OTEL_EXPORTER_OTLP_ENDPOINT is set but the [otel] extra is not installed; no span is sent")
        return None
    from opentelemetry import trace
    from opentelemetry.context import Context

    from merchant_assistant import __version__

    resource = Resource.create(
        {"service.name": SERVICE_NAME, "service.version": __version__, "service.instance.id": instance_id()}
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=traces_endpoint(endpoint), timeout=EXPORT_TIMEOUT_SECONDS),
            max_queue_size=MAX_QUEUE_SIZE,
            schedule_delay_millis=SCHEDULE_DELAY_MILLIS,
            export_timeout_millis=EXPORT_TIMEOUT_SECONDS * 1000,
        )
    )
    codes = {"ok": trace.StatusCode.OK, "error": trace.StatusCode.ERROR, "unset": trace.StatusCode.UNSET}
    log.info("otel: exporting spans over OTLP/HTTP")
    return OtelExporter(
        provider.get_tracer("merchant_assistant", __version__),
        in_context=trace.set_span_in_context,
        status=lambda code: trace.Status(codes[code]),
        root=Context,
        provider=provider,
    )
