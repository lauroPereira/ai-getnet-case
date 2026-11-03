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
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from merchant_assistant.config import Settings
from merchant_assistant.data.db import connect
from merchant_assistant.data.webhook_outbox import enqueue

SIGNATURE_TOLERANCE_S = 300
TICKETING, MERCHANT = "ticketing", "merchant"
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
        if key == "t" and value.isascii() and value.isdecimal() and len(value) <= 20:
            timestamp = int(value)
        elif key == "v1" and len(value) == 64 and all(c in "0123456789abcdef" for c in value):
            candidates.append(value)
    if timestamp is None or not candidates or abs(now - timestamp) > tolerance_s:
        return False
    expected = signature(secret, body, timestamp).split("v1=", 1)[1]
    return any(hmac.compare_digest(expected, candidate) for candidate in candidates)


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
        self._active: set[tuple[str, str]] = set()
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
        self._wake()

    def conversation_replied(self, case: dict, record: dict, result: dict | None) -> None:
        """After a successful resume: the reply produced for the operator's action, to the ticket and the merchant."""
        self._wake()

    def handoff_closed(self, case: dict) -> None:
        self._wake()

    def recover_handoff_closed(self) -> None:
        """Recover new durable intentions and unfinished closing events written before migration 0010."""
        conn = connect(self.settings.db_path)
        try:
            cases = conn.execute(
                "SELECT DISTINCT c.* FROM handoff_cases c JOIN webhook_inbox i ON i.case_id=c.case_id "
                "WHERE c.queue_state='closed' AND i.event='ticket.solved' AND i.status_code IN (0,200) "
                "AND NOT EXISTS (SELECT 1 FROM webhook_deliveries d WHERE d.case_id=c.case_id "
                "AND d.event='handoff.closed' AND d.target='ticketing' AND d.status='delivered') "
                "AND NOT EXISTS (SELECT 1 FROM webhook_outbox o WHERE o.case_id=c.case_id "
                "AND o.event='handoff.closed')"
            ).fetchall()
            for case in cases:
                enqueue(conn, "handoff.closed", {
                    "case_id": case["case_id"], "protocol": case["protocol"], "closed_at": case["closed_at"],
                    "closed_by": case["closed_by"],
                }, case["case_id"])
        finally:
            conn.close()
        self.dispatch_pending()

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

    def _wake(self) -> None:
        try:
            self.dispatch_pending()
        except Exception:
            log.exception("could not start webhook delivery")

    def dispatch_pending(self) -> None:
        conn = connect(self.settings.db_path)
        try:
            pending = conn.execute(
                "SELECT o.event_id, o.target, o.body FROM webhook_outbox o WHERE o.status='pending' "
                "AND NOT EXISTS (SELECT 1 FROM webhook_outbox prior WHERE prior.case_id=o.case_id "
                "AND prior.target=o.target AND prior.rowid<o.rowid AND prior.status!='delivered') "
                "ORDER BY o.rowid"
            ).fetchall()
        finally:
            conn.close()
        for row in pending:
            name = row["target"]
            url, secret = self._target(name)
            if not url or not secret:
                continue
            key = (row["event_id"], name)
            with self._lock:
                if key in self._active or len(self._active) >= 16:
                    continue
                self._active.add(key)
                event = json.loads(row["body"])
                thread = threading.Thread(
                    target=self._deliver, args=(event, row["body"].encode("utf-8"), name, url, secret),
                    name=f"webhook-{name}", daemon=True,
                )
                self._threads.add(thread)
            thread.start()

    def _deliver(self, event: dict, body: bytes, name: str, url: str, secret: str) -> None:
        key = (event["id"], name)
        stripe = int.from_bytes(hashlib.sha256(f"{event['id']}:{name}".encode()).digest()[:8], "big") % 64
        lock = None
        schedule_more = False
        try:
            lock = sqlite3.connect(
                f"{self.settings.db_path}.delivery-lock-{stripe:02d}", timeout=5, isolation_level=None
            )
            while True:
                try:
                    lock.execute("BEGIN IMMEDIATE")
                    break
                except sqlite3.OperationalError as exc:
                    if "locked" not in str(exc).lower():
                        raise
            schedule_more = True
            waits = self.settings.webhook_waits
            with httpx.Client(transport=self.transport, timeout=self.settings.webhook_timeout_s) as client:
                while True:
                    conn = connect(self.settings.db_path)
                    try:
                        conn.execute("BEGIN IMMEDIATE")
                        row = conn.execute(
                            "SELECT attempts,status FROM webhook_outbox WHERE event_id=? AND target=?", key
                        ).fetchone()
                        if row is None or row["status"] != "pending":
                            conn.execute("COMMIT")
                            return
                        attempt = row["attempts"] + 1
                        if attempt > self.settings.webhook_max_attempts:
                            conn.execute("UPDATE webhook_outbox SET status='failed' WHERE event_id=? AND target=?", key)
                            conn.execute("COMMIT")
                            return
                        conn.execute(
                            "UPDATE webhook_outbox SET attempts=? WHERE event_id=? AND target=?", (attempt, *key)
                        )
                        data = event["data"]
                        conn.execute(
                            "INSERT INTO webhook_deliveries (delivery_id,event,target,case_id,conversation_id,attempt,"
                            "status,response_code,created_at,event_id,error) "
                            "VALUES (?,?,?,?,?,?,'error',NULL,?,?,'interrupted')",
                            (f"dlv_{uuid.uuid4().hex[:20]}", event["type"], name, data.get("case_id"),
                             data.get("conversation_id"), attempt, _now_iso(), event["id"]),
                        )
                        conn.execute("COMMIT")
                    finally:
                        conn.close()
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
            schedule_more = False
            log.exception("webhook delivery failed", extra={"event": {"id": event.get("id"), "target": name}})
        finally:
            if lock is not None:
                lock.close()
            with self._lock:
                self._active.discard(key)
            # Pick up intentions that arrived while the bounded set of delivery workers was full.
            if schedule_more:
                self._wake()
            with self._lock:
                self._threads.discard(threading.current_thread())

    def _record(self, event: dict, target: str, attempt: int, status: str, code: int | None, error: str | None):
        conn = connect(self.settings.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE webhook_deliveries SET status=?,response_code=?,error=? "
                "WHERE event_id=? AND target=? AND attempt=?",
                (status, code, error, event["id"], target, attempt),
            )
            final = status if status != "error" else (
                "failed" if attempt >= self.settings.webhook_max_attempts else "pending"
            )
            conn.execute(
                "UPDATE webhook_outbox SET status=? WHERE event_id=? AND target=?", (final, event["id"], target)
            )
            conn.execute("COMMIT")
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
