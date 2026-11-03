"""Operator queue for handoff cases (RF-80, RF-81, RF-83; spec v0.7.0 D6, D7, D9, D10, D14).

The single service that the API (`/v1/handoffs`), the CLI (`merchant-assistant operator`) and, from task 66, the
ticketing integration call. Every state change runs under `BEGIN IMMEDIATE`: the first action on a case marks it as
resumed in the same transaction that records the event, so a second action with another idempotency key gets
`409 already_resumed`, and the same key returns the stored record (`replayed: true`). The graph is resumed only
after the commit, through one resume point (`resume`, provided by the orchestrator from task 65), never inside the
lock. Every call, accepted or refused, leaves an audit row with the acting principal and `handoff:operate`.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from merchant_assistant.guardrails.input import check_input

QueueState = Literal["open", "claimed", "answered", "rejected", "closed"]
Action = Literal["approve", "reply", "reject"]
QUEUE_STATES: tuple[str, ...] = ("open", "claimed", "answered", "rejected", "closed")
ACTIONS: tuple[str, ...] = ("approve", "reply", "reject")
SCOPE = "handoff:operate"
IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
STATE_AFTER: dict[str, str] = {"approve": "answered", "reply": "answered", "reject": "rejected"}  # D14
TRANSCRIPT_TURNS = 10

Resume = Callable[[dict, dict], object]


class HandoffError(Exception):
    """A refusal with its HTTP status and error code (shared by the API, the CLI and the ticketing entry)."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _audit(
    conn: sqlite3.Connection,
    case: sqlite3.Row | dict | None,
    tool: str,
    outcome: str,
    actor: str,
    on_behalf_of: str | None,
    case_id: str,
) -> None:
    conn.execute(
        "INSERT INTO audit_events (at, customer_id, tool, resource_id, outcome, principal_id, scope, on_behalf_of) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (_now(), case["customer_id"] if case else "", tool, case_id, outcome, actor, SCOPE, on_behalf_of),
    )


def _case(conn: sqlite3.Connection, case_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM handoff_cases WHERE case_id=?", (case_id,)).fetchone()


def _event(conn: sqlite3.Connection, case_id: str, action: str, operator_id: str, key: str | None, payload: dict):
    event_id = f"hev_{uuid.uuid4().hex[:16]}"
    stamp = _now()
    conn.execute(
        "INSERT INTO handoff_events (event_id, case_id, action, operator_id, idempotency_key, payload, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (event_id, case_id, action, operator_id, key, json.dumps(payload, ensure_ascii=False), stamp),
    )
    return event_id, stamp


def _record(case: sqlite3.Row | dict, event: sqlite3.Row | dict, *, replayed: bool, case_state: str | None) -> dict:
    payload = json.loads(event["payload"] or "{}")
    return {
        "case_id": case["case_id"],
        "protocol": case["protocol"],
        "event_id": event["event_id"],
        "action": event["action"],
        "operator_id": event["operator_id"],
        "text": payload.get("text"),
        "idempotency_key": event["idempotency_key"],
        "queue_state": case["queue_state"],
        "case_state": case_state,
        "created_at": event["created_at"],
        "replayed": replayed,
    }


def _case_state(conn: sqlite3.Connection, conversation_id: str | None) -> str | None:
    if not conversation_id:
        return None
    row = conn.execute("SELECT state FROM conversations WHERE conversation_id=?", (conversation_id,)).fetchone()
    return row["state"] if row else None


def _rollback(conn: sqlite3.Connection) -> None:
    if conn.in_transaction:
        conn.execute("ROLLBACK")


# --- reads --------------------------------------------------------------------------------------------------------


def _summary(row: sqlite3.Row) -> dict:
    payload = json.loads(row["payload"] or "{}")
    return {
        "case_id": row["case_id"],
        "protocol": row["protocol"],
        "customer_id": row["customer_id"],
        "conversation_id": row["conversation_id"],
        "reason": row["reason"],
        "summary": payload.get("summary"),
        "queue_state": row["queue_state"],
        "claimed_by": row["claimed_by"],
        "claimed_at": row["claimed_at"],
        "answered_at": row["answered_at"],
        "closed_at": row["closed_at"],
        "resume_count": row["resume_count"],
        "channel": row["channel"],
        "ticket_id": row["ticket_id"],
        "created_at": row["created_at"],
    }


def list_cases(conn: sqlite3.Connection, state: str | None = None, limit: int = 100) -> list[dict]:
    """Newest first; `state` filters by queue state."""
    if state is not None and state not in QUEUE_STATES:
        raise HandoffError(422, "invalid_state", f"state must be one of {', '.join(QUEUE_STATES)}.")
    query, params = "SELECT * FROM handoff_cases", []
    if state:
        query, params = query + " WHERE queue_state=?", [state]
    rows = conn.execute(query + " ORDER BY created_at DESC, rowid DESC LIMIT ?", (*params, limit)).fetchall()
    return [_summary(row) for row in rows]


def transcript(conn: sqlite3.Connection, conversation_id: str | None, turns: int = TRANSCRIPT_TURNS) -> list[dict]:
    """Last turns of the conversation, masked by the input guard (card numbers, documents, secrets)."""
    if not conversation_id:
        return []
    rows = conn.execute(
        "SELECT role, text, created_at FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
        (conversation_id, turns),
    ).fetchall()
    return [{"role": r["role"], "text": check_input(r["text"]).masked, "at": r["created_at"]} for r in reversed(rows)]


def get_case(conn: sqlite3.Connection, case_id: str) -> dict:
    row = _case(conn, case_id)
    if row is None:
        raise HandoffError(404, "case_not_found", "Handoff case not found.")
    payload = json.loads(row["payload"] or "{}")
    events = conn.execute(
        "SELECT event_id, action, operator_id, idempotency_key, payload, created_at FROM handoff_events "
        "WHERE case_id=? ORDER BY created_at, rowid",
        (case_id,),
    ).fetchall()
    deliveries = conn.execute(
        "SELECT delivery_id, event, target, attempt, status, response_code, created_at FROM webhook_deliveries "
        "WHERE case_id=? ORDER BY created_at, rowid",
        (case_id,),
    ).fetchall()
    return _summary(row) | {
        "pending_question": payload.get("pending_question"),
        "draft_reply": payload.get("draft_reply"),
        "language": payload.get("language"),
        "thread_id": row["thread_id"],
        "case_state": _case_state(conn, row["conversation_id"]),
        "transcript": transcript(conn, row["conversation_id"]),
        "events": [
            {
                "event_id": e["event_id"],
                "action": e["action"],
                "operator_id": e["operator_id"],
                "idempotency_key": e["idempotency_key"],
                "text": json.loads(e["payload"] or "{}").get("text"),
                "created_at": e["created_at"],
            }
            for e in events
        ],
        "deliveries": [dict(d) for d in deliveries],  # filled by the webhooks of task 66
    }


# --- writes -------------------------------------------------------------------------------------------------------


def claim(
    conn: sqlite3.Connection, case_id: str, operator_id: str, *, actor: str, on_behalf_of: str | None = None
) -> dict:
    """D9: an open case is claimed by the operator; claiming one's own case again is idempotent; a case held by
    another operator is `409 claimed_by_other`; a closed case is `409 case_closed`."""
    case = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        case = _case(conn, case_id)
        if case is None:
            raise HandoffError(404, "case_not_found", "Handoff case not found.")
        if case["claimed_by"] and case["claimed_by"] != operator_id:
            raise HandoffError(409, "claimed_by_other", "Another operator already holds this case.")
        if case["queue_state"] == "closed":
            raise HandoffError(409, "case_closed", "This case is closed.")
        replayed = case["claimed_by"] == operator_id
        if not replayed:
            stamp = _now()
            conn.execute(
                "UPDATE handoff_cases SET queue_state='claimed', claimed_by=?, claimed_at=? WHERE case_id=?",
                (operator_id, stamp, case_id),
            )
            _event(conn, case_id, "claim", operator_id, None, {})
        _audit(conn, case, "handoff.claim", "ok", actor, on_behalf_of, case_id)
        conn.execute("COMMIT")
    except HandoffError as exc:
        _rollback(conn)
        _audit(conn, case, "handoff.claim", exc.code, actor, on_behalf_of, case_id)
        raise
    except BaseException:
        _rollback(conn)
        raise
    return _summary(_case(conn, case_id)) | {"replayed": replayed}


def act(
    conn: sqlite3.Connection,
    case_id: str,
    operator_id: str,
    action: str,
    text: str | None,
    idempotency_key: str,
    *,
    actor: str,
    on_behalf_of: str | None = None,
    resume: Resume | None = None,
) -> dict:
    """`approve` (releases the draft), `reply` (operator text) or `reject` (instruction to the agent), D9, D10, D14.

    The same idempotency key returns the stored record with `replayed: true`; a key already used for another case
    or action is `409 idempotency_conflict`; a case already resumed is `409 already_resumed`. After the commit the
    case is handed to the single resume point (`resume(case, record)`), outside the lock."""
    if action not in ACTIONS:
        raise HandoffError(422, "invalid_action", f"action must be one of {', '.join(ACTIONS)}.")
    if not IDEMPOTENCY_KEY.match(idempotency_key or ""):
        raise HandoffError(422, "invalid_idempotency_key", "idempotency_key must have 8 to 80 of [A-Za-z0-9_-].")
    text = (text or "").strip() or None
    if action in ("reply", "reject") and not text:
        raise HandoffError(422, "text_required", f"{action} requires a text.")
    tool = f"handoff.{action}"
    case = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        case = _case(conn, case_id)
        existing = conn.execute("SELECT * FROM handoff_events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        if existing is not None:
            if (existing["case_id"], existing["action"], existing["operator_id"]) != (case_id, action, operator_id):
                raise HandoffError(409, "idempotency_conflict", "This idempotency_key was used for another action.")
            _audit(conn, case, tool, "replayed", actor, on_behalf_of, case_id)
            conn.execute("COMMIT")
            return _record(case, existing, replayed=True, case_state=_case_state(conn, case["conversation_id"]))
        if case is None:
            raise HandoffError(404, "case_not_found", "Handoff case not found.")
        if case["resume_count"] > 0 or case["queue_state"] in ("answered", "rejected"):
            raise HandoffError(409, "already_resumed", "This case was already resumed by another action.")
        if case["queue_state"] == "closed":
            raise HandoffError(409, "case_closed", "This case is closed.")
        if case["claimed_by"] and case["claimed_by"] != operator_id:
            raise HandoffError(409, "claimed_by_other", "Another operator already holds this case.")
        stamp = _now()
        if not case["claimed_by"]:  # D9: acting on an open case claims it in the same transaction
            conn.execute(
                "UPDATE handoff_cases SET claimed_by=?, claimed_at=? WHERE case_id=?", (operator_id, stamp, case_id)
            )
            _event(conn, case_id, "claim", operator_id, None, {"implicit": True})
        new_state = STATE_AFTER[action]
        conn.execute(
            "UPDATE handoff_cases SET queue_state=?, resume_count=resume_count+1, answered_at=? WHERE case_id=?",
            (new_state, stamp if new_state == "answered" else None, case_id),
        )
        _event(conn, case_id, action, operator_id, idempotency_key, {"text": text})
        _audit(conn, case, tool, "ok", actor, on_behalf_of, case_id)
        conn.execute("COMMIT")
    except HandoffError as exc:
        _rollback(conn)
        _audit(conn, case, tool, exc.code, actor, on_behalf_of, case_id)
        raise
    except BaseException:
        _rollback(conn)
        raise
    case = _case(conn, case_id)
    event = conn.execute("SELECT * FROM handoff_events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
    record = _record(case, event, replayed=False, case_state=_case_state(conn, case["conversation_id"]))
    if resume is not None:  # task 65: resumes the interrupted graph with the operator's action
        resume(dict(case), record)
        record["case_state"] = _case_state(conn, case["conversation_id"])
    return record


def close(
    conn: sqlite3.Connection, case_id: str, operator_id: str, *, actor: str, on_behalf_of: str | None = None
) -> dict:
    """D14: the case leaves the queue (`closed`), for instance when the ticket is solved. Idempotent."""
    case = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        case = _case(conn, case_id)
        if case is None:
            raise HandoffError(404, "case_not_found", "Handoff case not found.")
        if case["claimed_by"] and case["claimed_by"] != operator_id:
            raise HandoffError(409, "claimed_by_other", "Another operator already holds this case.")
        replayed = case["queue_state"] == "closed"
        if not replayed:
            stamp = _now()
            conn.execute(
                "UPDATE handoff_cases SET queue_state='closed', closed_at=?, closed_by=? WHERE case_id=?",
                (stamp, operator_id, case_id),
            )
            _event(conn, case_id, "close", operator_id, None, {})
        _audit(conn, case, "handoff.close", "ok", actor, on_behalf_of, case_id)
        conn.execute("COMMIT")
    except HandoffError as exc:
        _rollback(conn)
        _audit(conn, case, "handoff.close", exc.code, actor, on_behalf_of, case_id)
        raise
    except BaseException:
        _rollback(conn)
        raise
    return _summary(_case(conn, case_id)) | {"replayed": replayed}
