"""HTTP API of the demo ticketing service.

Run with `uvicorn merchant_assistant.ticketing.service:app --port 8002`. The assistant sends `handoff.created`,
`conversation.replied` and `handoff.closed` to `POST /webhooks/assistant`; operators (JWT issued by the assistant)
work the ticket through `/tickets`, and every act is delivered to the assistant as a signed event. The assistant's
answer decides the ticket status."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Annotated, Literal

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from merchant_assistant.ticketing.auth import AuthError, Operator, OperatorVerifier, ServiceToken
from merchant_assistant.ticketing.config import TicketingSettings
from merchant_assistant.ticketing.outbox import Delivery, Dispatcher, OutboxWorker, envelope
from merchant_assistant.ticketing.signing import verify
from merchant_assistant.ticketing.store import STATUSES, TicketStore

INBOUND_EVENTS = {"handoff.created", "conversation.replied", "handoff.closed"}
PASS_THROUGH = {404, 409, 422}
LOCAL_DELIVERY_ERRORS = {
    "assistant_malformed_response",
    "service_token_malformed",
    "delivery_error",
}  # assistant errors the screen receives with the same code and body


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["approve", "reply", "reject"]
    text: str = Field(default="", max_length=4000)
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")


REQUEST_ID: ContextVar[str] = ContextVar("ticketing_request_id", default="req_unknown")


def _error(status: int, code: str, message: str, **extra) -> JSONResponse:
    """Same envelope and Bearer challenge as the assistant: {"error": {"code", "message", "request_id"}}."""
    headers = {"X-Request-Id": REQUEST_ID.get()}
    if status == 401:  # RFC 6750 3.1: no error code when the request carries no credential
        headers["WWW-Authenticate"] = "Bearer" if code == "token_required" else f'Bearer error="{code}"'
    elif status == 403:
        headers["WWW-Authenticate"] = f'Bearer error="{code}", scope="handoff:operate"'
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "request_id": REQUEST_ID.get(), **extra}},
        headers=headers,
    )


def current_operator(request: Request) -> Operator:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthError(401, "token_required", "A Bearer token issued by the assistant is required.")
    return request.app.state.verifier.verify(token.strip())


OperatorDep = Annotated[Operator, Depends(current_operator)]


def create_app(
    settings: TicketingSettings | None = None,
    *,
    client: httpx.Client | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FastAPI:
    settings = settings or TicketingSettings.from_env()
    client = client or httpx.Client()
    store = TicketStore(settings.db_path)
    verifier = OperatorVerifier(settings, client)
    dispatcher = Dispatcher(settings, store, client, ServiceToken(settings, client), now)
    worker = OutboxWorker(dispatcher, settings.outbox_poll_s)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        worker.start()
        yield
        worker.stop()

    app = FastAPI(title="Demo Ticketing Service", version="1.0.0", lifespan=lifespan)
    app.state.settings, app.state.store, app.state.dispatcher = settings, store, dispatcher
    app.state.verifier = verifier

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        REQUEST_ID.set(f"req_{uuid.uuid4().hex[:16]}")
        return await call_next(request)

    @app.exception_handler(AuthError)
    async def auth_error(_request: Request, exc: AuthError) -> JSONResponse:
        return _error(exc.status, exc.code, exc.message)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # --- assistant -> ticketing ---------------------------------------------------------------------------------

    @app.post("/webhooks/assistant")
    async def receive(request: Request):
        if not settings.inbound_secret:
            return _error(503, "webhook_not_configured", "TICKETING_WEBHOOK_SECRET is not configured.")
        raw = await request.body()
        if not verify(
            settings.inbound_secret,
            request.headers.get("x-signature"),
            raw,
            time.time(),
            settings.signature_tolerance_s,
        ):
            return _error(401, "invalid_signature", "Invalid or expired webhook signature.")
        try:
            event = json.loads(raw)
            valid = (
                isinstance(event, dict)
                and isinstance(event.get("id"), str)
                and isinstance(event.get("type"), str)
                and isinstance(event.get("data"), dict)
                and request.headers.get("x-webhook-id", event["id"]) == event["id"]
            )
        except ValueError:
            valid = False
        if not valid:
            return _error(400, "invalid_payload", "Expected the webhook envelope {id, type, created_at, data}.")
        if event["type"] not in INBOUND_EVENTS:
            return _error(422, "unknown_event", f"Event {event['type']} is not handled by the ticketing service.")
        if not isinstance(event["data"].get("case_id"), str) or not event["data"]["case_id"]:
            return _error(400, "invalid_payload", "data.case_id is required.")
        result = store.receive(event, now())
        if result["result"] == "unknown_case":
            return _error(404, "ticket_not_found", "No ticket exists for this case yet.")
        status = "duplicate" if result["result"] == "duplicate" else "received"
        return {"status": status, "ticket_id": result.get("ticket_id")}

    # --- operator API -------------------------------------------------------------------------------------------

    @app.get("/tickets")
    def list_tickets(_op: OperatorDep, status: str | None = None):
        if status is not None and status not in STATUSES:
            return _error(422, "invalid_status", f"status must be one of {', '.join(STATUSES)}.")
        return {"tickets": store.list_tickets(status)}

    @app.get("/tickets/{ticket_id}")
    def get_ticket(ticket_id: str, _op: OperatorDep):
        ticket = store.detail(ticket_id)
        return ticket if ticket else _error(404, "ticket_not_found", "Unknown ticket.")

    def respond(ticket_id: str, delivery: Delivery, *, replayed: bool = False):
        info = {"status": delivery.status, "event_id": delivery.event_id, "replayed": replayed}
        if delivery.status == "delivered":
            return {"ticket": store.get(ticket_id), "delivery": {**info, "assistant": delivery.response}}
        if delivery.status == "rejected":
            if delivery.http_status in PASS_THROUGH:
                return JSONResponse(status_code=delivery.http_status, content=delivery.response)
            own = ((delivery.response or {}).get("error") or {}).get("code")
            if own in LOCAL_DELIVERY_ERRORS:
                return _error(502, own, delivery.response["error"]["message"], event_id=delivery.event_id)
            return _error(
                502,
                "assistant_rejected",
                "The assistant refused the service request.",
                upstream_status=delivery.http_status,
                event_id=delivery.event_id,
            )
        # pending, failed or another worker in flight: the screen shows "envio pendente"
        return JSONResponse(
            status_code=202, content={"ticket": store.get(ticket_id), "delivery": {**info, "error": delivery.error}}
        )

    def stored(row: dict) -> Delivery:
        body = json.loads(row["response_body"]) if row.get("response_body") else None
        return Delivery(row["status"], row["event_id"], row.get("response_status"), body)

    def act(ticket_id: str, op: Operator, event_type: str, extra: dict, key: str | None = None):
        ticket = store.get(ticket_id)
        if ticket is None:
            return _error(404, "ticket_not_found", "Unknown ticket.")
        signed = extra | {"operator_id": op.operator_id}  # the same key from another operator is not a replay
        fingerprint = hashlib.sha256(json.dumps(signed, sort_keys=True).encode()).hexdigest() if key else None
        data = {"ticket_id": ticket_id, "case_id": ticket["case_id"], "operator_id": op.operator_id, **extra}
        outcome, row = store.enqueue(
            ticket_id,
            envelope(event_type, data, now()),
            op.operator_id,
            now(),
            idempotency_key=key,
            fingerprint=fingerprint,
        )
        if outcome == "not_found":
            return _error(404, "ticket_not_found", "Unknown ticket.")
        if outcome == "solved":
            return _error(409, "ticket_solved", "The ticket is already solved.")
        if outcome == "busy":
            return _error(
                409, "delivery_pending", "A previous act of this ticket is still being sent.", event_id=row["event_id"]
            )
        if outcome == "mismatch":
            return _error(409, "idempotency_key_reused", "This idempotency_key was used for a different act.")
        if outcome == "existing":
            if row["status"] == "failed" and store.retry_failed(row["event_id"], now()):
                return respond(ticket_id, dispatcher.deliver(row["event_id"]), replayed=True)
            return respond(ticket_id, stored(row), replayed=True)
        return respond(ticket_id, dispatcher.deliver(row["event_id"]))

    @app.post("/tickets/{ticket_id}/assign")
    def assign(ticket_id: str, op: OperatorDep):
        return act(ticket_id, op, "ticket.assigned", {})

    @app.post("/tickets/{ticket_id}/actions")
    def action(ticket_id: str, body: ActionRequest, op: OperatorDep):
        extra = {"action": body.action, "text": body.text, "idempotency_key": body.idempotency_key}
        return act(ticket_id, op, "ticket.action", extra, body.idempotency_key)

    @app.post("/tickets/{ticket_id}/solve")
    def solve(ticket_id: str, op: OperatorDep):
        return act(ticket_id, op, "ticket.solved", {})

    return app


app = create_app()
