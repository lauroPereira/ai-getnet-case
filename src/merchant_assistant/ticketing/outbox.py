"""Delivery of ticket events to the assistant: signed body, service token, recorded attempts and retries."""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from merchant_assistant.ticketing.auth import AuthError, ServiceToken, TransientError
from merchant_assistant.ticketing.config import TicketingSettings
from merchant_assistant.ticketing.signing import signature
from merchant_assistant.ticketing.store import TicketStore, iso

EVENTS_PATH = "/v1/integrations/ticketing/events"


def envelope(event_type: str, data: dict, now: datetime) -> dict:
    return {"id": f"evt_{uuid.uuid4().hex}", "type": event_type, "created_at": iso(now), "data": data}


@dataclass(frozen=True)
class Delivery:
    status: str  # delivered | pending | rejected | failed | in_flight
    event_id: str
    http_status: int | None = None
    response: dict | None = None
    error: str | None = None


class Dispatcher:
    def __init__(
        self,
        settings: TicketingSettings,
        store: TicketStore,
        client: httpx.Client,
        token: ServiceToken,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.settings, self.store, self.client, self.token, self.now = settings, store, client, token, now

    def _post(self, row: dict) -> httpx.Response:
        body = row["body"].encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Id": row["event_id"],
            "X-Webhook-Event": row["event_type"],
            "X-Signature": signature(self.settings.outbound_secret, body, int(self.now().timestamp())),
            "Authorization": f"Bearer {self.token.get()}",
        }
        try:
            return self.client.post(
                f"{self.settings.assistant_url}{EVENTS_PATH}",
                content=body,
                headers=headers,
                timeout=self.settings.request_timeout_s,
            )
        except httpx.HTTPError as exc:
            raise TransientError(f"assistant unreachable: {type(exc).__name__}") from exc

    def _send(self, row: dict) -> httpx.Response:
        response = self._post(row)
        if response.status_code == 401:  # expired or revoked service token: renew once
            self.token.invalidate()
            response = self._post(row)
        if response.status_code >= 500 or response.status_code == 429:
            raise TransientError(f"assistant returned {response.status_code}")
        return response

    def deliver(self, event_id: str) -> Delivery:
        lease = self.settings.request_timeout_s * 3 + 5
        row = self.store.claim(event_id, self.now(), lease)
        if row is None:
            current = self.store.get_outbox(event_id)
            return Delivery(current["status"] if current else "missing", event_id)
        if not self.settings.outbound_secret:
            return self._retry_later(row, "ASSISTANT_WEBHOOK_SECRET is not configured")
        try:
            response = self._send(row)
        except TransientError as exc:
            return self._retry_later(row, str(exc))
        except AuthError as exc:
            self.store.record_attempt(
                event_id,
                self.now(),
                outcome="rejected",
                http_status=exc.status,
                error=exc.code,
                final_status="rejected",
            )
            return Delivery("rejected", event_id, exc.status, {"error": {"code": exc.code, "message": exc.message}})
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text[:500]}
        if 200 <= response.status_code < 300:
            self.store.record_attempt(
                event_id,
                self.now(),
                outcome="delivered",
                http_status=response.status_code,
                response_body=body,
                final_status="delivered",
            )
            return Delivery("delivered", event_id, response.status_code, body)
        self.store.record_attempt(
            event_id,
            self.now(),
            outcome="rejected",
            http_status=response.status_code,
            response_body=body,
            final_status="rejected",
        )
        return Delivery("rejected", event_id, response.status_code, body)

    def _retry_later(self, row: dict, error: str) -> Delivery:
        attempt = row["attempts"] + 1
        now = self.now()
        if attempt >= self.settings.max_attempts:
            self.store.record_attempt(row["event_id"], now, outcome="network_error", error=error, final_status="failed")
            return Delivery("failed", row["event_id"], error=error)
        waits = self.settings.retry_waits_s or (0.0,)
        wait = waits[min(attempt - 1, len(waits) - 1)]
        self.store.record_attempt(
            row["event_id"],
            now,
            outcome="network_error",
            error=error,
            next_attempt_at=now.timestamp() + wait,
            final_status="pending",
        )
        return Delivery("pending", row["event_id"], error=error)

    def dispatch_due(self) -> list[Delivery]:
        return [self.deliver(event_id) for event_id in self.store.due(self.now())]


class OutboxWorker:
    """Background loop that retries pending events while the service runs."""

    def __init__(self, dispatcher: Dispatcher, poll_s: float) -> None:
        self.dispatcher, self.poll_s = dispatcher, poll_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self.poll_s <= 0 or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="ticketing-outbox", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.poll_s):
            try:
                self.dispatcher.dispatch_due()
            except Exception as exc:  # noqa: BLE001 - the loop must survive one bad round
                print(json.dumps({"event": "ticketing_outbox_error", "error": type(exc).__name__}))

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
