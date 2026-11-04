"""SQLite storage owned by the ticketing service: tickets, ticket history, received webhooks and the outbox."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

STATUSES = ("new", "open", "pending", "solved")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL UNIQUE,
    protocol TEXT,
    conversation_id TEXT,
    customer_id TEXT,
    language TEXT,
    reason TEXT,
    summary TEXT,
    pending_question TEXT,
    draft_reply TEXT,
    transcript TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL CHECK (status IN ('new', 'open', 'pending', 'solved')),
    assignee TEXT,
    case_state TEXT,
    queue_state TEXT,
    reply_text TEXT,
    reply_delivered_at TEXT,
    closed_at TEXT,
    closed_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ticket_events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL REFERENCES tickets (ticket_id),
    kind TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    actor TEXT,
    detail TEXT NOT NULL DEFAULT '{}',
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inbound_deliveries (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    ticket_id TEXT,
    case_id TEXT,
    payload TEXT NOT NULL,
    received_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
    event_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES tickets (ticket_id),
    event_type TEXT NOT NULL,
    body TEXT NOT NULL,
    operator_id TEXT NOT NULL,
    idempotency_key TEXT UNIQUE,
    fingerprint TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'delivered', 'rejected', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at REAL,
    lease_until REAL,
    response_status INTEGER,
    response_body TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox_attempts (
    event_id TEXT NOT NULL REFERENCES outbox (event_id),
    attempt INTEGER NOT NULL,
    at TEXT NOT NULL,
    outcome TEXT NOT NULL,
    http_status INTEGER,
    error TEXT,
    PRIMARY KEY (event_id, attempt)
);
CREATE INDEX IF NOT EXISTS outbox_due ON outbox (status, next_attempt_at);
"""

# Ticket status reached when the assistant accepts each outgoing event, and the statuses it may come from.
TRANSITIONS = {
    "ticket.assigned": ({"new", "open"}, "open"),
    "ticket.action": ({"new", "open", "pending"}, "pending"),
    "ticket.solved": ({"new", "open", "pending"}, "solved"),
}


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="milliseconds")


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class TicketStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._ready = False

    def _connect(self) -> sqlite3.Connection:
        if not self._ready:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path), isolation_level=None, timeout=5, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        if not self._ready:
            conn.executescript(SCHEMA)
            self._ready = True
        return conn

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    @contextmanager
    def _read(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _event(conn, ticket_id, kind, now, *, actor=None, from_status=None, to_status=None, detail=None) -> None:
        conn.execute(
            "INSERT INTO ticket_events (ticket_id, kind, from_status, to_status, actor, detail, at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, kind, from_status, to_status, actor, _json(detail or {}), iso(now)),
        )

    def _set_status(self, conn, ticket: sqlite3.Row, status: str, now: datetime, actor: str | None) -> None:
        if ticket["status"] == status:
            return
        conn.execute(
            "UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?", (status, iso(now), ticket["ticket_id"])
        )
        self._event(
            conn,
            ticket["ticket_id"],
            "status_changed",
            now,
            actor=actor,
            from_status=ticket["status"],
            to_status=status,
        )

    # --- inbound webhooks (assistant -> ticketing) ----------------------------------------------------------------

    def receive(self, envelope: dict, now: datetime) -> dict:
        """Applies one assistant event exactly once. Returns {"result": created|recorded|duplicate|unknown_case}."""
        event_id, event_type, data = envelope["id"], envelope["type"], envelope.get("data") or {}
        with self._tx() as conn:
            if conn.execute("SELECT 1 FROM inbound_deliveries WHERE event_id = ?", (event_id,)).fetchone():
                return {"result": "duplicate"}
            case_id = data.get("case_id")
            ticket = conn.execute("SELECT * FROM tickets WHERE case_id = ?", (case_id,)).fetchone()
            if event_type == "handoff.created":
                result = "duplicate_case" if ticket else "created"
                ticket_id = ticket["ticket_id"] if ticket else self._create(conn, data, now)
            elif ticket is None:
                return {"result": "unknown_case"}
            else:
                ticket_id, result = ticket["ticket_id"], "recorded"
                if event_type == "conversation.replied":
                    conn.execute(
                        "UPDATE tickets SET reply_text = ?, reply_delivered_at = ?, updated_at = ? WHERE ticket_id = ?",
                        (data.get("reply_text"), data.get("delivered_at") or iso(now), iso(now), ticket_id),
                    )
                    self._event(
                        conn,
                        ticket_id,
                        "reply_delivered",
                        now,
                        actor=data.get("operator_id"),
                        detail={k: data.get(k) for k in ("action", "via", "request_id", "delivered_at")},
                    )
                else:  # handoff.closed
                    conn.execute(
                        "UPDATE tickets SET closed_at = ?, closed_by = ?, updated_at = ? WHERE ticket_id = ?",
                        (data.get("closed_at") or iso(now), data.get("closed_by"), iso(now), ticket_id),
                    )
                    self._event(
                        conn,
                        ticket_id,
                        "case_closed",
                        now,
                        actor=data.get("closed_by"),
                        detail={"closed_at": data.get("closed_at")},
                    )
            conn.execute(
                "INSERT INTO inbound_deliveries (event_id, event_type, ticket_id, case_id, payload, received_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, event_type, ticket_id, case_id, _json(envelope), iso(now)),
            )
            return {"result": result, "ticket_id": ticket_id}

    def _create(self, conn, data: dict, now: datetime) -> str:
        ticket_id = f"tkt_{uuid.uuid4().hex[:12]}"
        conn.execute(
            "INSERT INTO tickets (ticket_id, case_id, protocol, conversation_id, customer_id, language, reason, "
            "summary, pending_question, draft_reply, transcript, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)",
            (
                ticket_id,
                data["case_id"],
                data.get("protocol"),
                data.get("conversation_id"),
                data.get("customer_id"),
                data.get("language"),
                data.get("reason"),
                data.get("summary"),
                data.get("pending_question"),
                data.get("draft_reply"),
                _json(data.get("transcript") or []),
                iso(now),
                iso(now),
            ),
        )
        self._event(conn, ticket_id, "created", now, to_status="new", detail={"protocol": data.get("protocol")})
        return ticket_id

    # --- reading ----------------------------------------------------------------------------------------------------

    @staticmethod
    def _ticket(row: sqlite3.Row, outbox: sqlite3.Row | None) -> dict:
        ticket = dict(row)
        ticket["transcript"] = json.loads(ticket["transcript"])
        ticket["delivery"] = (
            {
                "event_id": outbox["event_id"],
                "event_type": outbox["event_type"],
                "status": outbox["status"],
                "attempts": outbox["attempts"],
            }
            if outbox
            else None
        )
        return ticket

    @staticmethod
    def _last_outbox(conn, ticket_id: str) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT * FROM outbox WHERE ticket_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1", (ticket_id,)
        ).fetchone()

    def list_tickets(self, status: str | None = None) -> list[dict]:
        with self._read() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM tickets WHERE status = ? ORDER BY created_at DESC, rowid DESC", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC, rowid DESC").fetchall()
            return [self._ticket(r, self._last_outbox(conn, r["ticket_id"])) for r in rows]

    def get(self, ticket_id: str) -> dict | None:
        with self._read() as conn:
            row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
            return self._ticket(row, self._last_outbox(conn, ticket_id)) if row else None

    def detail(self, ticket_id: str) -> dict | None:
        with self._read() as conn:
            row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
            if row is None:
                return None
            ticket = self._ticket(row, self._last_outbox(conn, ticket_id))
            ticket["events"] = [
                {**dict(e), "detail": json.loads(e["detail"])}
                for e in conn.execute("SELECT * FROM ticket_events WHERE ticket_id = ? ORDER BY seq", (ticket_id,))
            ]
            ticket["deliveries"] = {
                "received": [
                    {"event_id": d["event_id"], "event_type": d["event_type"], "received_at": d["received_at"]}
                    for d in conn.execute(
                        "SELECT * FROM inbound_deliveries WHERE ticket_id = ? ORDER BY received_at, rowid", (ticket_id,)
                    )
                ],
                "sent": [
                    {
                        "event_id": o["event_id"],
                        "event_type": o["event_type"],
                        "operator_id": o["operator_id"],
                        "idempotency_key": o["idempotency_key"],
                        "status": o["status"],
                        "response_status": o["response_status"],
                        "attempts": [
                            dict(a)
                            for a in conn.execute(
                                "SELECT attempt, at, outcome, http_status, error FROM outbox_attempts "
                                "WHERE event_id = ? ORDER BY attempt",
                                (o["event_id"],),
                            )
                        ],
                    }
                    for o in conn.execute(
                        "SELECT * FROM outbox WHERE ticket_id = ? ORDER BY created_at, rowid", (ticket_id,)
                    )
                ],
            }
            return ticket

    # --- outbox (ticketing -> assistant) ------------------------------------------------------------------------------

    def enqueue(
        self,
        ticket_id: str,
        envelope: dict,
        operator_id: str,
        now: datetime,
        *,
        idempotency_key: str | None = None,
        fingerprint: str | None = None,
    ) -> tuple[str, dict | None]:
        """Stores an outgoing event. Returns (outcome, row) with outcome created, existing, mismatch, busy, solved,
        not_found. A key already used returns the stored event instead of creating a second one."""
        with self._tx() as conn:
            if idempotency_key is not None:
                existing = conn.execute("SELECT * FROM outbox WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
                if existing is not None:
                    same = existing["ticket_id"] == ticket_id and existing["fingerprint"] == fingerprint
                    return ("existing" if same else "mismatch"), dict(existing)
            ticket = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
            if ticket is None:
                return "not_found", None
            if ticket["status"] == "solved":
                return "solved", None
            last = self._last_outbox(conn, ticket_id)
            if last is not None and last["status"] == "pending":
                return "busy", dict(last)
            conn.execute(
                "INSERT INTO outbox (event_id, ticket_id, event_type, body, operator_id, idempotency_key, fingerprint, "
                "status, next_attempt_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
                (
                    envelope["id"],
                    ticket_id,
                    envelope["type"],
                    _json(envelope),
                    operator_id,
                    idempotency_key,
                    fingerprint,
                    now.timestamp(),
                    iso(now),
                    iso(now),
                ),
            )
            self._event(
                conn,
                ticket_id,
                "event_queued",
                now,
                actor=operator_id,
                detail={"event_id": envelope["id"], "event_type": envelope["type"], "idempotency_key": idempotency_key},
            )
            return "created", dict(self._last_outbox(conn, ticket_id))

    def retry_failed(self, event_id: str, now: datetime) -> bool:
        """Puts a failed event (all attempts used) back in the queue, keeping its id so the assistant can dedupe."""
        with self._tx() as conn:
            changed = conn.execute(
                "UPDATE outbox SET status = 'pending', next_attempt_at = ?, lease_until = NULL, updated_at = ? "
                "WHERE event_id = ? AND status = 'failed'",
                (now.timestamp(), iso(now), event_id),
            ).rowcount
            return changed == 1

    def claim(self, event_id: str, now: datetime, lease_s: float) -> dict | None:
        with self._tx() as conn:
            changed = conn.execute(
                "UPDATE outbox SET lease_until = ? WHERE event_id = ? AND status = 'pending' "
                "AND (lease_until IS NULL OR lease_until < ?)",
                (now.timestamp() + lease_s, event_id, now.timestamp()),
            ).rowcount
            if changed != 1:
                return None
            return dict(conn.execute("SELECT * FROM outbox WHERE event_id = ?", (event_id,)).fetchone())

    def due(self, now: datetime) -> list[str]:
        with self._read() as conn:
            return [
                r["event_id"]
                for r in conn.execute(
                    "SELECT event_id FROM outbox WHERE status = 'pending' AND next_attempt_at <= ? "
                    "AND (lease_until IS NULL OR lease_until < ?) ORDER BY created_at, rowid",
                    (now.timestamp(), now.timestamp()),
                )
            ]

    def get_outbox(self, event_id: str) -> dict | None:
        with self._read() as conn:
            row = conn.execute("SELECT * FROM outbox WHERE event_id = ?", (event_id,)).fetchone()
            return dict(row) if row else None

    def record_attempt(
        self,
        event_id: str,
        now: datetime,
        *,
        outcome: str,
        http_status: int | None = None,
        error: str | None = None,
        response_body: dict | None = None,
        next_attempt_at: float | None = None,
        final_status: str = "pending",
    ) -> int:
        """Logs one delivery attempt and moves the outbox row. Applies the ticket transition when delivered."""
        with self._tx() as conn:
            row = conn.execute("SELECT * FROM outbox WHERE event_id = ?", (event_id,)).fetchone()
            attempt = row["attempts"] + 1
            conn.execute(
                "INSERT INTO outbox_attempts (event_id, attempt, at, outcome, http_status, error) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, attempt, iso(now), outcome, http_status, error),
            )
            conn.execute(
                "UPDATE outbox SET attempts = ?, status = ?, next_attempt_at = ?, lease_until = NULL, "
                "response_status = ?, response_body = ?, updated_at = ? WHERE event_id = ?",
                (
                    attempt,
                    final_status,
                    next_attempt_at,
                    http_status,
                    _json(response_body) if response_body is not None else None,
                    iso(now),
                    event_id,
                ),
            )
            ticket = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (row["ticket_id"],)).fetchone()
            detail = {
                "event_id": event_id,
                "event_type": row["event_type"],
                "attempt": attempt,
                "http_status": http_status,
            }
            if final_status == "delivered":
                self._apply(conn, ticket, row, response_body or {}, now)
            elif final_status == "rejected":
                self._event(
                    conn,
                    ticket["ticket_id"],
                    "event_rejected",
                    now,
                    actor=row["operator_id"],
                    detail={**detail, "response": response_body},
                )
            elif final_status == "failed":
                self._event(
                    conn,
                    ticket["ticket_id"],
                    "delivery_failed",
                    now,
                    actor=row["operator_id"],
                    detail={**detail, "error": error},
                )
            elif attempt == 1:
                self._event(
                    conn,
                    ticket["ticket_id"],
                    "delivery_pending",
                    now,
                    actor=row["operator_id"],
                    detail={**detail, "error": error},
                )
            return attempt

    def _apply(self, conn, ticket: sqlite3.Row, outbox: sqlite3.Row, response: dict, now: datetime) -> None:
        operator = outbox["operator_id"]
        body = json.loads(outbox["body"])
        sources, target = TRANSITIONS[outbox["event_type"]]
        conn.execute(
            "UPDATE tickets SET case_state = COALESCE(?, case_state), queue_state = COALESCE(?, queue_state), "
            "updated_at = ? WHERE ticket_id = ?",
            (response.get("case_state"), response.get("queue_state"), iso(now), ticket["ticket_id"]),
        )
        if outbox["event_type"] in ("ticket.assigned", "ticket.action") and ticket["status"] != "solved":
            conn.execute("UPDATE tickets SET assignee = ? WHERE ticket_id = ?", (operator, ticket["ticket_id"]))
        kind = {"ticket.assigned": "assigned", "ticket.action": "action_accepted", "ticket.solved": "solved"}
        detail = {
            "event_id": outbox["event_id"],
            "assistant_status": response.get("status"),
            "case_state": response.get("case_state"),
            "queue_state": response.get("queue_state"),
        }
        if outbox["event_type"] == "ticket.action":
            detail |= {k: body["data"].get(k) for k in ("action", "idempotency_key")}
        self._event(conn, ticket["ticket_id"], kind[outbox["event_type"]], now, actor=operator, detail=detail)
        if ticket["status"] in sources:
            self._set_status(conn, ticket, target, now, operator)
