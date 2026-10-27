"""Conversations owned by one merchant: short history, case state, technical attempts and the cached case prefix.

Ownership is checked before any read or write. A client may supply a new `conversation_id`; an id that already
belongs to another merchant is refused without revealing anything about it.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from merchant_assistant.data.clock import Clock

HISTORY_MAX_TOKENS = 1200
HISTORY_MAX_MESSAGES = 10
PREFIX_TTL = timedelta(minutes=30)
MAX_TECHNICAL_CYCLES = 2


class ConversationNotFound(Exception):
    """The conversation does not exist for this merchant."""


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class Conversation:
    conversation_id: str
    customer_id: str
    state: str
    topic: str | None
    technical_cycles: int
    resolution_evidence: str | None
    prefix: dict | None
    prefix_topic: str | None
    prefix_at: str | None
    created: bool = False
    attempts: list[dict] = field(default_factory=list)

    def case_view(self) -> dict:
        return {
            "state": self.state,
            "topic": self.topic,
            "technical_cycles": self.technical_cycles,
            "max_technical_cycles": MAX_TECHNICAL_CYCLES,
            "attempts": self.attempts,
            "evidence": self.resolution_evidence,
            "new": self.created,
        }


class ConversationStore:
    def __init__(self, conn: sqlite3.Connection, clock: Clock) -> None:
        self.conn, self.clock = conn, clock

    def _now(self) -> str:
        return self.clock.now().isoformat(timespec="seconds")

    def open(self, conversation_id: str | None, customer_id: str) -> Conversation:
        conversation_id = conversation_id or f"conv_{uuid.uuid4().hex[:20]}"
        row = self.conn.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,)).fetchone()
        if row is None:
            now = self._now()
            self.conn.execute(
                "INSERT INTO conversations (conversation_id, customer_id, state, technical_cycles, created_at, "
                "updated_at) VALUES (?,?,?,?,?,?)",
                (conversation_id, customer_id, "in_progress", 0, now, now),
            )
            return Conversation(conversation_id, customer_id, "in_progress", None, 0, None, None, None, None, True)
        if row["customer_id"] != customer_id:
            raise ConversationNotFound(conversation_id)
        conv = Conversation(
            conversation_id,
            customer_id,
            row["state"],
            row["topic"],
            row["technical_cycles"],
            row["resolution_evidence"],
            json.loads(row["prefix"]) if row["prefix"] else None,
            row["prefix_topic"],
            row["prefix_at"],
        )
        conv.attempts = self.attempts(conversation_id)
        return conv

    def history(self, conversation_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT role, text, tokens FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, HISTORY_MAX_MESSAGES),
        ).fetchall()
        kept, budget = [], HISTORY_MAX_TOKENS
        for r in rows:  # newest first, until the token budget is used
            if r["tokens"] > budget:
                break
            budget -= r["tokens"]
            kept.append({"role": r["role"], "text": r["text"]})
        return list(reversed(kept))

    def append(
        self, conversation_id: str, request_id: str, role: str, text: str, route: str | None, status: str | None
    ) -> None:
        self.conn.execute(
            "INSERT INTO messages (conversation_id, request_id, role, text, route, status, tokens, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (conversation_id, request_id, role, text, route, status, estimate_tokens(text), self._now()),
        )

    def cached_prefix(self, conv: Conversation, topic: str) -> dict | None:
        if not conv.prefix or conv.prefix_topic != topic or not conv.prefix_at:
            return None
        if self.clock.now() - datetime.fromisoformat(conv.prefix_at) > PREFIX_TTL:
            return None
        return conv.prefix

    def attempts(self, conversation_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT cycle, step, result FROM case_attempts WHERE conversation_id = ? ORDER BY id", (conversation_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def record_feedback(self, conversation_id: str, result: str, evidence: str) -> None:
        """Marks the pending attempts of the case with the merchant's feedback."""
        self.conn.execute(
            "UPDATE case_attempts SET result = ?, evidence = ?, updated_at = ? WHERE conversation_id = ? "
            "AND result = 'pending'",
            (result, evidence, self._now(), conversation_id),
        )

    def add_attempts(self, conversation_id: str, cycle: int, steps: list[str]) -> None:
        now = self._now()
        self.conn.executemany(
            "INSERT INTO case_attempts (conversation_id, cycle, step, result, created_at, updated_at) "
            "VALUES (?,?,?,'pending',?,?)",
            [(conversation_id, cycle, step[:300], now, now) for step in steps],
        )

    def save(
        self,
        conv: Conversation,
        *,
        state: str,
        topic: str | None,
        technical_cycles: int,
        evidence: str | None,
        prefix: dict | None = None,
        prefix_topic: str | None = None,
    ) -> None:
        fields = {
            "state": state,
            "topic": topic,
            "technical_cycles": technical_cycles,
            "resolution_evidence": evidence,
            "updated_at": self._now(),
        }
        if prefix is not None:
            fields |= {
                "prefix": json.dumps(prefix, ensure_ascii=False, default=str),
                "prefix_topic": prefix_topic,
                "prefix_at": self._now(),
            }
        assignments = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(
            f"UPDATE conversations SET {assignments} WHERE conversation_id = ?",  # noqa: S608 - fixed keys
            [*fields.values(), conv.conversation_id],
        )

    def get(self, conversation_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,)).fetchone()
        if row is None:
            return None
        messages = self.conn.execute(
            "SELECT role, text, route, status, created_at FROM messages WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
        out = {k: row[k] for k in row.keys() if k != "prefix"}  # noqa: SIM118 - sqlite3.Row
        out["messages"] = [dict(m) for m in messages]
        out["attempts"] = self.attempts(conversation_id)
        return out
