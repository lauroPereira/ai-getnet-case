"""Ticketing -> assistant: `POST /v1/integrations/ticketing/events` (task 66; spec v0.7.0 "Contrato entre os times").

Every event needs both a `client_credentials` token with `handoff:integrate` and the signature with
`ASSISTANT_WEBHOOK_SECRET` (window of 300 s). `ticket.assigned`, `ticket.action` and `ticket.solved` go through the
same queue service as `/v1/handoffs` (`handoffs.claim`, `act`, `close`), with the same `409` and idempotency rules,
and the audit records `service:ticketing` acting on behalf of `operator:<id>`. An event id already answered returns
the stored answer without a new effect; a `5xx` answer is not stored, so the ticketing's retry processes it again."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from merchant_assistant import handoffs
from merchant_assistant.api.identity import HANDOFF_INTEGRATE, active_operator
from merchant_assistant.api.schemas import ErrorBody
from merchant_assistant.api.v1 import AUTH, _db, _error, insufficient_scope, rate_limited
from merchant_assistant.api.webhooks import verify_signature

router = APIRouter(prefix="/v1/integrations", tags=["integrations"])
EVENTS = ("ticket.assigned", "ticket.action", "ticket.solved")
SOURCE = "ticketing"


async def raw_body(request: Request) -> bytes:
    return await request.body()


RAW_BODY = Depends(raw_body)


def _secret(settings) -> str:
    value = settings.assistant_webhook_secret
    return value.get_secret_value().strip() if value else ""


def _parse(raw: bytes, header_id: str | None) -> dict | None:
    try:
        event = json.loads(raw)
    except ValueError:
        return None
    if not (
        isinstance(event, dict)
        and isinstance(event.get("id"), str)
        and 0 < len(event["id"]) <= 100
        and isinstance(event.get("type"), str)
        and isinstance(event.get("data"), dict)
    ):
        return None
    if header_id is not None and header_id != event["id"]:
        return None
    return event


def _states(conn, case_id: str) -> tuple[str | None, str | None]:
    row = conn.execute("SELECT queue_state, conversation_id FROM handoff_cases WHERE case_id=?", (case_id,)).fetchone()
    if row is None:
        return None, None
    return handoffs._case_state(conn, row["conversation_id"]), row["queue_state"]


def _store(conn, event: dict, status: int, body: dict) -> None:
    """Answers below 500 are final: the same event id gets them again without a new effect."""
    if status >= 500:
        return
    conn.execute(
        "INSERT OR IGNORE INTO webhook_inbox (event_id, source, event, case_id, status_code, response, received_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            event["id"],
            SOURCE,
            event["type"],
            (event.get("data") or {}).get("case_id"),
            status,
            json.dumps(body, ensure_ascii=False),
            datetime.now(UTC).isoformat(timespec="seconds"),
        ),
    )


@router.post(
    "/ticketing/events",
    responses={
        400: {"model": ErrorBody},
        401: {"model": ErrorBody},
        403: {"model": ErrorBody},
        404: {"model": ErrorBody},
        409: {"model": ErrorBody},
        422: {"model": ErrorBody},
        429: {"model": ErrorBody},
        503: {"model": ErrorBody},
    },
)
def ticketing_events(request: Request, principal=AUTH, raw: bytes = RAW_BODY):
    """Signed ticketing event (`ticket.assigned`, `ticket.action`, `ticket.solved`). Answer:
    `200 {"status": "accepted"|"replayed", "case_state", "queue_state"}`."""
    if isinstance(principal, JSONResponse):
        return principal
    if principal["role"] != "service" or HANDOFF_INTEGRATE not in principal["scopes"]:
        conn = _db(request)
        try:
            handoffs.audit_access(conn, "handoff.integrate", "insufficient_scope", principal["principal_id"])
        finally:
            conn.close()
        return insufficient_scope(request, "Ticketing events require the handoff:integrate scope.")
    if limited := rate_limited(request, principal):
        return limited
    settings = request.app.state.settings
    secret = _secret(settings)
    if not secret:
        return _error(503, "webhook_not_configured", "ASSISTANT_WEBHOOK_SECRET is not configured.", request)
    if not verify_signature(secret, request.headers.get("x-signature"), raw, time.time()):
        return _error(401, "invalid_signature", "Invalid or expired webhook signature.", request)
    event = _parse(raw, request.headers.get("x-webhook-id"))
    if event is None:
        return _error(400, "invalid_payload", "Expected the webhook envelope {id, type, created_at, data}.", request)
    actor = principal["principal_id"]
    conn = _db(request)
    try:
        seen = conn.execute("SELECT status_code, response FROM webhook_inbox WHERE event_id=?", (event["id"],))
        if (stored := seen.fetchone()) is not None:  # delivery already answered: no new effect
            body = json.loads(stored["response"])
            if stored["status_code"] == 200:
                case_state, queue_state = _states(conn, body.get("case_id") or event["data"].get("case_id") or "")
                return {"status": "replayed", "case_state": case_state, "queue_state": queue_state}
            return JSONResponse(status_code=stored["status_code"], content=body)
        status, body = _apply(request, conn, event, actor)
        _store(conn, event, status, body)
        if status == 200:
            return {k: body[k] for k in ("status", "case_state", "queue_state")}
        return _error(status, body["error"]["code"], body["error"]["message"], request)
    finally:
        conn.close()


def _failure(status: int, code: str, message: str) -> tuple[int, dict]:
    return status, {"error": {"code": code, "message": message}}


def _apply(request: Request, conn, event: dict, actor: str) -> tuple[int, dict]:
    data = event["data"]
    if event["type"] not in EVENTS:
        return _failure(422, "unknown_event", f"Event {event['type']} is not handled by the assistant.")
    fields = ("ticket_id", "case_id", "operator_id")
    if not all(isinstance(data.get(name), str) and data[name] for name in fields):
        return _failure(400, "invalid_payload", "data.ticket_id, data.case_id and data.operator_id are required.")
    case_id, operator_id = data["case_id"], data["operator_id"]
    tool = {"ticket.assigned": "handoff.claim", "ticket.solved": "handoff.close"}.get(
        event["type"], f"handoff.{data.get('action')}"
    )
    if not active_operator(request.app.state.settings, operator_id):
        handoffs.audit_access(conn, tool, "unknown_operator", actor, case_id)
        return _failure(422, "unknown_operator", "operator_id is not an active operator.")
    on_behalf_of = f"operator:{operator_id}"
    webhooks = request.app.state.webhooks
    try:
        if event["type"] == "ticket.assigned":
            result = handoffs.claim(conn, case_id, operator_id, actor=actor, on_behalf_of=on_behalf_of)
        elif event["type"] == "ticket.action":
            action = data.get("action")
            text = data.get("text") if isinstance(data.get("text"), str) else None
            key = data.get("idempotency_key") if isinstance(data.get("idempotency_key"), str) else ""
            result = handoffs.act(
                conn,
                case_id,
                operator_id,
                action if isinstance(action, str) else "",
                text,
                key,
                actor=actor,
                on_behalf_of=on_behalf_of,
                resume=webhooks.resume_point(getattr(request.app.state.orchestrator, "resume_handoff", None)),
            )
        else:
            result = handoffs.close(conn, case_id, operator_id, actor=actor, on_behalf_of=on_behalf_of)
            if not result["replayed"]:
                webhooks.handoff_closed(dict(handoffs._case(conn, case_id)))
    except handoffs.HandoffError as exc:
        return _failure(exc.status, exc.code, exc.message)
    conn.execute(  # the ticket that holds this case, from the first accepted event; a refusal changes nothing
        "UPDATE handoff_cases SET ticket_id=? WHERE case_id=? AND ticket_id IS NULL", (data["ticket_id"], case_id)
    )
    case_state, queue_state = _states(conn, case_id)
    status = "replayed" if result.get("replayed") else "accepted"
    return 200, {"status": status, "case_state": case_state, "queue_state": queue_state, "case_id": case_id}
