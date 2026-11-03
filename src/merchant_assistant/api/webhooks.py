"""Signed webhooks of the assistant (task 66; spec v0.7.0 "Contrato entre os times / Webhooks", D11, D24; ADR 0018).

Envelope `{"id": "evt_…", "type", "created_at", "data"}`; headers `X-Webhook-Id`, `X-Webhook-Event` and
`X-Signature: t=<unix>,v1=<hex>` with `v1 = HMAC-SHA256(secret, "<t>.<raw body>")`; one secret per direction.
Outgoing events (`handoff.created`, `conversation.replied`, `handoff.closed`) are built in the request with masked
text and sent by a short thread outside it: up to `WEBHOOK_MAX_ATTEMPTS` attempts (network error, timeout, 5xx or
429 are retried; another 4xx is final), each attempt recorded in `webhook_deliveries`. The merchant's copy of
`conversation.replied` omits `operator_id` (D29): one event id, a body per receiver, each signed with its secret.
An empty URL sends nothing; a receiver that is down never raises in the merchant's or the operator's request."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from merchant_assistant.config import Settings
from merchant_assistant.data.db import connect
from merchant_assistant.guardrails.input import check_input
from merchant_assistant.handoffs import transcript

SIGNATURE_TOLERANCE_S = 300
TICKETING, MERCHANT = "ticketing", "merchant"
TARGETS: dict[str, tuple[str, ...]] = {
    "handoff.created": (TICKETING,),
    "conversation.replied": (TICKETING, MERCHANT),
    "handoff.closed": (TICKETING,),
}
HIDDEN_FROM: dict[str, tuple[str, ...]] = {MERCHANT: ("operator_id",)}  # D29: the merchant's copy omits the operator
log = logging.getLogger("merchant_assistant.webhooks")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def signature(secret: str, body: bytes, timestamp: int) -> str:
    digest = hmac.new(secret.encode("utf-8"), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def verify_signature(
    secret: str, header: str | None, body: bytes, now: float, tolerance_s: int = SIGNATURE_TOLERANCE_S
) -> bool:
    """True only for a matching `v1` and a `t` within the tolerance window."""
    if not secret or not header:
        return False
    timestamp, candidates = None, []
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t" and value.isdigit():
            timestamp = int(value)
        elif key == "v1" and value:
            candidates.append(value)
    if timestamp is None or not candidates or abs(now - timestamp) > tolerance_s:
        return False
    expected = signature(secret, body, timestamp).split("v1=", 1)[1]
    return any(hmac.compare_digest(expected, candidate) for candidate in candidates)


def envelope(event_type: str, data: dict) -> dict:
    return {"id": f"evt_{uuid.uuid4().hex}", "type": event_type, "created_at": _now_iso(), "data": data}


def _mask(text) -> str | None:
    return check_input(text).masked if isinstance(text, str) and text else text


def _secret(value) -> str:
    return value.get_secret_value().strip() if value else ""


class Webhooks:
    """Builds, signs and delivers the assistant's outgoing events. `transport` replaces the network in tests."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.settings, self.transport, self.sleep, self.clock = settings, transport, sleep, clock
        self._threads: set[threading.Thread] = set()
        self._lock = threading.Lock()

    # --- targets ------------------------------------------------------------------------------------------------

    def _target(self, name: str) -> tuple[str | None, str]:
        s = self.settings
        if name == TICKETING:
            return s.ticketing_webhook_url, _secret(s.ticketing_webhook_secret)
        return s.conversation_webhook_url, _secret(s.conversation_webhook_secret)

    # --- events -------------------------------------------------------------------------------------------------

    def handoff_created_for(self, request_id: str) -> None:
        """After a turn answered with `status=handoff`: the case opened by this request (thread = request id, D6)."""
        self._safely(self._handoff_created, request_id)

    def _handoff_created(self, request_id: str) -> None:
        conn = connect(self.settings.db_path)
        try:
            case = conn.execute("SELECT * FROM handoff_cases WHERE thread_id=?", (request_id,)).fetchone()
            if case is None:
                return
            payload = json.loads(case["payload"] or "{}")
            data = {
                "case_id": case["case_id"],
                "protocol": case["protocol"],
                "conversation_id": case["conversation_id"],
                "customer_id": case["customer_id"],
                "language": payload.get("language"),
                "reason": _mask(case["reason"]),
                "summary": _mask(payload.get("summary")),
                "pending_question": _mask(payload.get("pending_question")),
                "draft_reply": _mask(payload.get("draft_reply")),
                "transcript": transcript(conn, case["conversation_id"]),  # last 10 turns, masked by the input guard
            }
        finally:
            conn.close()
        self.emit("handoff.created", data)

    def conversation_replied(self, case: dict, record: dict, result: dict | None) -> None:
        """After a successful resume: the reply produced for the operator's action, to the ticket and the merchant."""

        def build() -> None:
            data = {
                "case_id": case["case_id"],
                "protocol": case["protocol"],
                "conversation_id": case["conversation_id"],
                "action": record["action"],
                "operator_id": record["operator_id"],
                "reply_text": _mask((result or {}).get("answer")),
                "via": "operator",
                "request_id": (result or {}).get("request_id"),
                "delivered_at": _now_iso(),
            }
            self.emit("conversation.replied", data)

        self._safely(build)

    def handoff_closed(self, case: dict) -> None:
        data = {
            "case_id": case["case_id"],
            "protocol": case["protocol"],
            "closed_at": case.get("closed_at"),
            "closed_by": case.get("closed_by"),
        }
        self._safely(self.emit, "handoff.closed", data)

    def resume_point(self, resume: Callable[[dict, dict], dict] | None) -> Callable[[dict, dict], dict] | None:
        """Wraps the single resume point: a successful resume emits `conversation.replied` (a failed one does not)."""
        if resume is None:
            return None

        def run(case: dict, record: dict) -> dict:
            result = resume(case, record)
            self.conversation_replied(case, record, result if isinstance(result, dict) else None)
            return result

        return run

    # --- delivery -----------------------------------------------------------------------------------------------

    def emit(self, event_type: str, data: dict) -> dict | None:
        """Starts one delivery thread per configured target. Returns the envelope, or None when nothing is sent."""
        targets = []
        for name in TARGETS[event_type]:
            url, secret = self._target(name)
            if not url:
                continue
            if not secret:
                log.warning("webhook target without secret", extra={"event": {"target": name, "type": event_type}})
                continue
            targets.append((name, url, secret))
        if not targets:
            return None
        event = envelope(event_type, data)
        for name, url, secret in targets:
            copy = event | {"data": {k: v for k, v in data.items() if k not in HIDDEN_FROM.get(name, ())}}
            body = json.dumps(copy, ensure_ascii=False, separators=(",", ":")).encode("utf-8")  # signed per target
            thread = threading.Thread(
                target=self._deliver, args=(copy, body, name, url, secret), name=f"webhook-{name}", daemon=True
            )
            with self._lock:
                self._threads.add(thread)
            thread.start()
        return event

    def _deliver(self, event: dict, body: bytes, name: str, url: str, secret: str) -> None:
        try:
            waits = self.settings.webhook_waits
            with httpx.Client(transport=self.transport, timeout=self.settings.webhook_timeout_s) as client:
                for attempt in range(1, self.settings.webhook_max_attempts + 1):
                    headers = {
                        "Content-Type": "application/json",
                        "X-Webhook-Id": event["id"],
                        "X-Webhook-Event": event["type"],
                        "X-Signature": signature(secret, body, int(self.clock())),
                    }
                    code, error = None, None
                    try:
                        code = client.post(url, content=body, headers=headers).status_code
                    except httpx.HTTPError as exc:
                        error = type(exc).__name__
                    if code is not None and 200 <= code < 300:
                        status = "delivered"
                    elif code is not None and code < 500 and code not in (408, 429):
                        status = "rejected"  # the receiver refused this event: repeating it changes nothing
                    else:
                        status = "error"
                    self._record(event, name, attempt, status, code, error)
                    if status != "error":
                        return
                    if attempt < self.settings.webhook_max_attempts:
                        self.sleep(waits[min(attempt - 1, len(waits) - 1)])
        except Exception:  # a delivery thread never takes anything down with it
            log.exception("webhook delivery failed", extra={"event": {"id": event.get("id"), "target": name}})
        finally:
            with self._lock:
                self._threads.discard(threading.current_thread())

    def _record(self, event: dict, target: str, attempt: int, status: str, code: int | None, error: str | None):
        data = event["data"]
        conn = connect(self.settings.db_path)
        try:
            conn.execute(
                "INSERT INTO webhook_deliveries (delivery_id, event, target, case_id, conversation_id, attempt, "
                "status, response_code, created_at, event_id, error) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    f"dlv_{uuid.uuid4().hex[:20]}",
                    event["type"],
                    target,
                    data.get("case_id"),
                    data.get("conversation_id"),
                    attempt,
                    status,
                    code,
                    _now_iso(),
                    event["id"],
                    error,
                ),
            )
        finally:
            conn.close()

    def wait(self, timeout: float = 30.0) -> bool:
        """Joins the delivery threads still running (tests, CLI). True when none is left."""
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                pending = list(self._threads)
            if not pending:
                return True
            for thread in pending:
                thread.join(max(0.0, deadline - time.monotonic()))
            if time.monotonic() >= deadline:
                with self._lock:
                    return not self._threads

    def _safely(self, fn, *args) -> None:
        try:
            fn(*args)
        except Exception:  # building an event never breaks the request that triggered it
            log.exception("webhook event not built")
