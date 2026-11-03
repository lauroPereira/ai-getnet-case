"""Operator queue for handoff cases (RF-80, RF-81, RF-83; spec v0.7.0 D6, D7, D9, D10, D14).

The single service that the API (`/v1/handoffs`), the CLI (`merchant-assistant operator`) and the ticketing
integration (`/v1/integrations/ticketing/events`, task 66) call. Every state change runs under `BEGIN IMMEDIATE`: the
first action on a case marks it as resumed in the same transaction that records the event, so a second action with
another idempotency key gets `409 already_resumed`, and the same key returns the stored record (`replayed: true`).
The graph is resumed only after the commit, through one resume point (`resume`, provided by the orchestrator from
task 65), never inside the lock. Every call, accepted or refused, leaves an audit row with the acting principal and
`handoff:operate`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import threading
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Literal

from merchant_assistant.data.webhook_outbox import enqueue
from merchant_assistant.guardrails.input import check_input

QueueState = Literal["open", "claimed", "answered", "rejected", "closed"]
Action = Literal["approve", "reply", "reject"]
QUEUE_STATES: tuple[str, ...] = ("open", "claimed", "answered", "rejected", "closed")
ACTIONS: tuple[str, ...] = ("approve", "reply", "reject")
SCOPE = "handoff:operate"
IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
STATE_AFTER: dict[str, str] = {"approve": "answered", "reply": "answered", "reject": "rejected"}  # D14
TRANSCRIPT_TURNS = 10
_CASE_LOCKS = tuple(threading.Lock() for _ in range(64))

Resume = Callable[[dict, dict], object]
log = logging.getLogger("merchant_assistant.handoffs")


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
    case_id: str | None,
) -> None:
    conn.execute(
        "INSERT INTO audit_events (at, customer_id, tool, resource_id, outcome, principal_id, scope, on_behalf_of) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (_now(), case["customer_id"] if case else "", tool, case_id, outcome, actor, SCOPE, on_behalf_of),
    )


def audit_access(
    conn: sqlite3.Connection, tool: str, outcome: str, actor: str, case_id: str | None = None, on_behalf_of=None
) -> None:
    """D23: reads of the queue and refusals at its gate are audited like its writes."""
    _audit(conn, _case(conn, case_id) if case_id else None, tool, outcome, actor, on_behalf_of, case_id)


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
        "resume_status": case["resume_status"],
        "resume_error": case["resume_error"],
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
        "resume_status": row["resume_status"],
        "resume_error": row["resume_error"],
        "channel": row["channel"],
        "ticket_id": row["ticket_id"],
        "created_at": row["created_at"],
    }


def list_cases(
    conn: sqlite3.Connection,
    state: str | None = None,
    limit: int = 100,
    *,
    actor: str | None = None,
    on_behalf_of: str | None = None,
) -> list[dict]:
    """Newest first; `state` filters by queue state. With `actor`, the read is audited (D23)."""
    if state is not None and state not in QUEUE_STATES:
        if actor:
            _audit(conn, None, "handoff.list", "invalid_state", actor, on_behalf_of, None)
        raise HandoffError(422, "invalid_state", f"state must be one of {', '.join(QUEUE_STATES)}.")
    if actor:
        _audit(conn, None, "handoff.list", "ok", actor, on_behalf_of, None)
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


def get_case(
    conn: sqlite3.Connection, case_id: str, *, actor: str | None = None, on_behalf_of: str | None = None
) -> dict:
    """One case with its masked conversation. With `actor`, the read is audited (D23)."""
    row = _case(conn, case_id)
    if actor:
        _audit(conn, row, "handoff.read", "ok" if row else "case_not_found", actor, on_behalf_of, case_id)
    if row is None:
        raise HandoffError(404, "case_not_found", "Handoff case not found.")
    payload = json.loads(row["payload"] or "{}")
    events = conn.execute(
        "SELECT event_id, action, operator_id, idempotency_key, payload, created_at FROM handoff_events "
        "WHERE case_id=? ORDER BY created_at, rowid",
        (case_id,),
    ).fetchall()
    deliveries = conn.execute(
        "SELECT delivery_id, event_id, event, target, attempt, status, response_code, error, created_at "
        "FROM webhook_deliveries "
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
        "deliveries": [dict(d) for d in deliveries],  # one row per webhook attempt (task 66)
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


@contextmanager
def _case_lock(conn: sqlite3.Connection, case_id: str):
    """Serialize actions on a case across workers; the OS releases the lock on process exit."""
    stripe = int.from_bytes(hashlib.sha256(case_id.encode()).digest()[:8], "big") % len(_CASE_LOCKS)
    local = _CASE_LOCKS[stripe]
    if not local.acquire(timeout=5):
        raise HandoffError(503, "resume_failed", "The case is still being processed; retry the action.")
    lock = None
    try:
        db_path = next(row[2] for row in conn.execute("PRAGMA database_list") if row[1] == "main")
        if db_path:
            lock = sqlite3.connect(f"{db_path}.case-lock-{stripe:02d}", timeout=5, isolation_level=None)
            try:
                lock.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                raise HandoffError(
                    503, "resume_failed", "The case is still being processed; retry the action."
                ) from exc
        yield
    finally:
        if lock is not None:
            lock.close()
        local.release()


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
    with _case_lock(conn, case_id):
        return _act_locked(
            conn, case_id, operator_id, action, text, idempotency_key,
            actor=actor, on_behalf_of=on_behalf_of, resume=resume,
        )


def _act_locked(
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
    or action is `409 idempotency_conflict`; a case already resumed is `409 already_resumed`; a case created before
    v0.7.0 (no saved flow) is `409 not_resumable`; a case whose checkpoint was not saved when it opened is
    `503 checkpoint_missing` (D28). After the commit the case is handed to the single resume point
    (`resume(case, record)`), outside the lock. A failed resume is recorded (`resume_status = failed`, visible in the
    queue) and answered with `503 resume_failed`; repeating the action with the same key resumes again."""
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
            stored_text = json.loads(existing["payload"] or "{}").get("text")
            if (existing["case_id"], existing["action"], existing["operator_id"], stored_text) != (
                case_id,
                action,
                operator_id,
                text,
            ):  # D22: only an identical repetition is a replay
                raise HandoffError(409, "idempotency_conflict", "This idempotency_key was used for another action.")
            retry = resume is not None and _claim_retry(conn, case)
            _audit(conn, case, tool, "retried" if retry else "replayed", actor, on_behalf_of, case_id)
            conn.execute("COMMIT")
            if retry:
                _resume(conn, case_id, existing, resume, actor, on_behalf_of)
            case = _case(conn, case_id)
            return _record(case, existing, replayed=True, case_state=_case_state(conn, case["conversation_id"]))
        if case is None:
            raise HandoffError(404, "case_not_found", "Handoff case not found.")
        if case["resume_count"] > 0 or case["queue_state"] in ("answered", "rejected"):
            raise HandoffError(409, "already_resumed", "This case was already resumed by another action.")
        if case["queue_state"] == "closed":
            raise HandoffError(409, "case_closed", "This case is closed.")
        if case["claimed_by"] and case["claimed_by"] != operator_id:
            raise HandoffError(409, "claimed_by_other", "Another operator already holds this case.")
        if not case["thread_id"]:
            raise HandoffError(
                409, "not_resumable", "This case was opened before v0.7.0 and has no saved flow to resume."
            )
        if case["resume_status"] == "checkpoint_failed":  # D28: nothing to resume; refused before any change
            raise HandoffError(
                503, "checkpoint_missing", "The saved flow of this case could not be stored when it opened."
            )
        stamp = _now()
        if not case["claimed_by"]:  # D9: acting on an open case claims it in the same transaction
            conn.execute(
                "UPDATE handoff_cases SET claimed_by=?, claimed_at=? WHERE case_id=?", (operator_id, stamp, case_id)
            )
            _event(conn, case_id, "claim", operator_id, None, {"implicit": True})
        new_state = STATE_AFTER[action]
        conn.execute(
            "UPDATE handoff_cases SET queue_state=?, resume_count=resume_count+1, answered_at=?, "
            "resume_status='pending', resume_error=NULL, resume_started_at=? WHERE case_id=?",
            (new_state, stamp if new_state == "answered" else None, stamp, case_id),
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
    event = conn.execute("SELECT * FROM handoff_events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
    if resume is not None:
        _resume(conn, case_id, event, resume, actor, on_behalf_of)
    case = _case(conn, case_id)
    return _record(case, event, replayed=False, case_state=_case_state(conn, case["conversation_id"]))


def _claim_retry(conn: sqlite3.Connection, case: sqlite3.Row) -> bool:
    """The case lock proves no previous attempt is still running, including after a process crash."""
    cursor = conn.execute(
        "UPDATE handoff_cases SET resume_status='pending', resume_error=NULL, resume_started_at=? "
        "WHERE case_id=? AND resume_status IN ('failed', 'pending')",
        (_now(), case["case_id"]),
    )
    return cursor.rowcount == 1


def _resume(
    conn: sqlite3.Connection,
    case_id: str,
    event: sqlite3.Row,
    resume: Resume,
    actor: str,
    on_behalf_of: str | None,
) -> None:
    """Calls the single resume point and records its outcome on the case; a failure never leaves the case silent."""
    case = _case(conn, case_id)
    record = _record(case, event, replayed=False, case_state=None)
    try:
        result = resume(dict(case), record) or {}
    except Exception as exc:
        code = getattr(exc, "code", None) or type(exc).__name__
        log.exception("resume failed", extra={"event": {"case_id": case_id, "code": code}})
        conn.execute(
            "UPDATE handoff_cases SET resume_status='failed', resume_error=? WHERE case_id=?", (str(code), case_id)
        )
        _audit(conn, case, "handoff.resume", f"failed:{code}", actor, on_behalf_of, case_id)
        raise HandoffError(
            503,
            "resume_failed",
            "The action was recorded but the reply could not be produced; retry it with the same idempotency_key.",
        ) from exc
    conn.execute(
        "UPDATE handoff_cases SET resume_status='done', resume_error=NULL, resume_request_id=? WHERE case_id=?",
        (result.get("request_id") if isinstance(result, dict) else None, case_id),
    )


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
            enqueue(conn, "handoff.closed", {
                "case_id": case_id, "protocol": case["protocol"], "closed_at": stamp, "closed_by": operator_id,
            }, case_id)
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
