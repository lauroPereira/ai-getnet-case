"""Conversations owned by one merchant: short history, rolling summary, fact register, case state, technical attempts
and the cached case prefix.

Ownership is checked before any read or write. A client may supply a new `conversation_id`; an id that already
belongs to another merchant is refused without revealing anything about it.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from merchant_assistant.data.clock import Clock
from merchant_assistant.tools.base import money

HISTORY_MAX_TOKENS = 1200
HISTORY_MAX_MESSAGES = 10
PREFIX_TTL = timedelta(minutes=30)
MAX_TECHNICAL_CYCLES = 2
FACT_KINDS = ("protocol", "amount", "percent", "date", "status", "product")  # closed set (migration 0014)
FACTS_IN_PROMPT = 40  # facts written in a prompt (protocols first, then the newest); the output guard uses all of them
SUMMARY_TURN_MAX_CHARS = 600  # older messages are capped for reply agents; clipping marks the history incomplete
SUMMARY_BLOCK_MESSAGES = 6  # D1 (amended): the summary advances by blocks of 3 turns that left the window
SUMMARY_BACKLOG_MAX_MESSAGES = 12  # older messages not summarized yet: at most this many per call and in `recent`
# The reply-writing agents receive recent turns plus any unsummarized messages outside the short history window.
PROMPT_HISTORY = {"support": 8, "personality": 4}


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


def _public_turn(row: sqlite3.Row) -> dict:
    """Turn as shown to clients: assistant turns carry `via`; operator turns also `operator_action` and `protocol`."""
    turn = {k: row[k] for k in ("role", "text", "route", "status", "created_at")}
    if row["role"] == "assistant":
        turn["via"] = row["via"] or "agent"
        if turn["via"] == "operator":
            meta = json.loads(row["meta"] or "{}")
            turn |= {"operator_action": meta.get("action"), "protocol": meta.get("protocol")}
    return turn


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

    def _window(self, conversation_id: str) -> list[sqlite3.Row]:
        """The short history, oldest first: newest messages within `HISTORY_MAX_MESSAGES` and `HISTORY_MAX_TOKENS`."""
        rows = self.conn.execute(
            "SELECT id, role, text, tokens FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, HISTORY_MAX_MESSAGES),
        ).fetchall()
        kept, budget = [], HISTORY_MAX_TOKENS
        for r in rows:  # newest first, until the token budget is used
            if r["tokens"] > budget:
                break
            budget -= r["tokens"]
            kept.append(r)
        return list(reversed(kept))

    def _uncovered(self, conversation_id: str) -> tuple[sqlite3.Row | None, list[sqlite3.Row], list[sqlite3.Row]]:
        """(the conversation's summary row, the messages out of the window the summary does not cover yet, oldest
        first, the window)."""
        row = self.conn.execute(
            "SELECT summary, summary_until_message_id FROM conversations WHERE conversation_id = ?", (conversation_id,)
        ).fetchone()
        window = self._window(conversation_id)
        if row is None:
            return None, [], window
        boundary = window[0]["id"] if window else None  # an empty window leaves every message out of it
        rows = self.conn.execute(
            "SELECT id, role, text FROM messages WHERE conversation_id = ? AND id > ? AND (? IS NULL OR id < ?) "
            "ORDER BY id",
            (conversation_id, row["summary_until_message_id"] or 0, boundary, boundary),
        ).fetchall()
        return row, rows, window

    def history(self, conversation_id: str) -> dict:
        """Return the summary, short history, and up to 12 newest unsummarized messages outside its window.

        `incomplete` is true when older unsummarized messages do not fit that bounded context block or any visible
        older message is clipped for reply-agent context. The full message remains in durable message storage and is
        sent to the summary model before its cursor advances.
        """
        row, uncovered, window = self._uncovered(conversation_id)
        visible = uncovered[-SUMMARY_BACKLOG_MAX_MESSAGES:]
        older = [
            {"role": r["role"], "text": r["text"][:SUMMARY_TURN_MAX_CHARS]}
            for r in visible
        ]
        recent = older + [{"role": r["role"], "text": r["text"]} for r in window]
        return {
            "summary": row["summary"] if row else None,
            "recent": recent,
            "uncovered": older,
            "incomplete": len(uncovered) > SUMMARY_BACKLOG_MAX_MESSAGES
            or any(len(r["text"]) > SUMMARY_TURN_MAX_CHARS for r in visible),
        }

    def _recent_ids(self, conversation_id: str) -> list[int]:
        """Ids of the messages of `history()['recent']`, in the same order."""
        _row, uncovered, window = self._uncovered(conversation_id)
        return [int(r["id"]) for r in [*uncovered[-SUMMARY_BACKLOG_MAX_MESSAGES:], *window]]

    def summary(self, conversation_id: str) -> str | None:
        row = self.conn.execute(
            "SELECT summary FROM conversations WHERE conversation_id = ?", (conversation_id,)
        ).fetchone()
        return row["summary"] if row else None

    def summary_backlog(self, conversation_id: str) -> tuple[str | None, list[dict], int] | None:
        """(previous summary, the oldest messages out of the window that it does not cover yet, id of the last of
        them), or None while fewer than `SUMMARY_BLOCK_MESSAGES` wait: the summary advances by blocks of 3 turns
        (D1, amended), at most `SUMMARY_BACKLOG_MAX_MESSAGES` messages per call. Full message text is retained here so
        the summary cursor never advances past content clipped from the model input."""
        row, uncovered, _window = self._uncovered(conversation_id)
        if row is None or len(uncovered) < SUMMARY_BLOCK_MESSAGES:
            return None
        block = uncovered[:SUMMARY_BACKLOG_MAX_MESSAGES]
        turns = [{"role": r["role"], "text": r["text"]} for r in block]
        return row["summary"], turns, int(block[-1]["id"])

    def save_summary(self, conversation_id: str, summary: str, until_message_id: int) -> None:
        self.conn.execute(
            "UPDATE conversations SET summary = ?, summary_until_message_id = ? WHERE conversation_id = ?",
            (summary, until_message_id, conversation_id),
        )

    def facts(self, conversation_id: str) -> list[dict]:
        """The fact register (task 92, D2), in the order the facts were recorded; the output guard reads all of it."""
        rows = self.conn.execute(
            "SELECT kind, value, source_tool, source_message_id, created_at FROM conversation_facts "
            "WHERE conversation_id = ? ORDER BY fact_id",
            (conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def earlier_facts(self, conversation_id: str, shown: int, limit: int = FACTS_IN_PROMPT) -> list[dict]:
        """Show facts recorded before the `shown` recent turns the agent reads, protocols first, then the newest facts,
        up to `limit`."""
        seen = self._recent_ids(conversation_id)[-shown:]
        boundary = seen[0] if seen else None
        rows = self.conn.execute(
            "SELECT kind, value, source_tool, source_message_id, created_at FROM conversation_facts "
            "WHERE conversation_id = ? AND (? IS NULL OR source_message_id < ?) "
            "ORDER BY kind <> 'protocol', fact_id DESC LIMIT ?",
            (conversation_id, boundary, boundary, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def add_facts(self, conversation_id: str, message_id: int | None, facts: list[tuple[str, str, str]]) -> None:
        """Records (kind, value, source tool) found in a turn. A value already in the register keeps its origin; the
        status of a record (`<id>: <status>`) replaces the earlier status of the same id, so only the latest stays."""
        now = self._now()
        for kind, value, tool in facts:
            value = value[:200]
            if kind == "status" and ": " in value:
                prefix = value.split(": ", 1)[0] + ": "
                self.conn.execute(
                    "DELETE FROM conversation_facts WHERE conversation_id = ? AND kind = 'status' AND value <> ? "
                    "AND substr(value, 1, ?) = ?",
                    (conversation_id, value, len(prefix), prefix),
                )
            self.conn.execute(
                "INSERT OR IGNORE INTO conversation_facts (conversation_id, kind, value, source_tool, "
                "source_message_id, created_at) VALUES (?,?,?,?,?,?)",
                (conversation_id, kind, value, tool, message_id, now),
            )

    def append(
        self,
        conversation_id: str,
        request_id: str,
        role: str,
        text: str,
        route: str | None,
        status: str | None,
        *,
        via: str | None = None,
        meta: dict | None = None,
    ) -> int:
        """`via` marks assistant turns: `agent` or `operator` (a human agent's reply, with `meta` = action and
        protocol). Merchant turns have no `via`. Returns the id of the message."""
        if role == "assistant" and via is None:
            via = "agent"
        cursor = self.conn.execute(
            "INSERT INTO messages (conversation_id, request_id, role, text, route, status, tokens, created_at, via, "
            "meta) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                conversation_id,
                request_id,
                role,
                text,
                route,
                status,
                estimate_tokens(text),
                self._now(),
                via,
                json.dumps(meta, ensure_ascii=False) if meta else None,
            ),
        )
        return int(cursor.lastrowid)

    def pending_operator_turn(self, conversation_id: str) -> dict | None:
        """Oldest operator reply not yet delivered in a merchant request (D8)."""
        row = self.conn.execute(
            "SELECT id, text, meta FROM messages WHERE conversation_id=? AND via='operator' AND delivered_at IS NULL "
            "ORDER BY id LIMIT 1",
            (conversation_id,),
        ).fetchone()
        return {"id": row["id"], "text": row["text"], "meta": json.loads(row["meta"] or "{}")} if row else None

    def mark_delivered(self, message_id: int) -> None:
        self.conn.execute(
            "UPDATE messages SET delivered_at=? WHERE id=? AND delivered_at IS NULL", (self._now(), message_id)
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
            "SELECT role, text, route, status, created_at, via, meta FROM messages WHERE conversation_id = ? "
            "ORDER BY id",
            (conversation_id,),
        ).fetchall()
        # `summary_until_message_id` is the summary's internal cursor (task 92): not part of the contract
        out = {k: row[k] for k in row.keys() if k not in ("prefix", "summary_until_message_id")}  # noqa: SIM118
        out["messages"] = [_public_turn(m) for m in messages]
        out["attempts"] = self.attempts(conversation_id)
        out["facts"] = self.facts(conversation_id)  # task 92 (D2); `summary` comes with the conversation's row
        # Task 66 (D24): webhook deliveries of the operator's reply to the merchant, one row per attempt. They are a
        # record of their own and never mark a turn as delivered in the conversation.
        out["webhook_deliveries"] = [
            dict(d)
            for d in self.conn.execute(
                "SELECT event, event_id, attempt, status, response_code, created_at FROM webhook_deliveries "
                "WHERE conversation_id = ? AND target = 'merchant' ORDER BY created_at, rowid",
                (conversation_id,),
            )
        ]
        return out


# --- fact register (task 92, spec v0.12.0 D2) ------------------------------------------------------------------------

_ISO_DAY = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})")
# when the tool looked and the period it was asked about (an echo of its arguments): not facts of the case
_SKIPPED_KEYS = {"observed_at", "date_from", "date_to", "date_field"}
_STATUS_KEYS = ("status", "normalized_status")  # the status of a record (receivables carry the normalized one)


def _echoes(args: object) -> set[str]:
    """The text values of a tool call's arguments: a result that repeats them says nothing new about the case."""
    if isinstance(args, dict):
        return {text for v in args.values() for text in _echoes(v)}
    if isinstance(args, list):
        return {text for v in args for text in _echoes(v)}
    return {args} if isinstance(args, str) else set()


def facts_from_tool(data: object, args: dict | None = None) -> list[tuple[str, str]]:
    """(kind, value) pairs of one tool result, read as the output guard reads it: amounts written with `R$`,
    percentages with `%` and ISO dates in its texts, plus each `protocol`, each entry of `products` and the `status` of
    a record that has an id. Texts that only echo the call's `args`, and the period fields, are left out. Only tool
    results and cases feed the register, never text written by a model."""
    from merchant_assistant.guardrails.output import amounts, percents  # the guard's own readers

    found: list[tuple[str, str]] = []
    echoes = _echoes(args or {})

    def text(key: str | None, value: str) -> None:
        if key in _SKIPPED_KEYS or value in echoes:
            return
        if key == "protocol":
            found.append(("protocol", value))
        found.extend(("amount", money(cents)["display"]) for cents in sorted(amounts(value)))
        found.extend(("percent", f"{p:g}%") for p in sorted(percents(value)))
        for y, m, d in _ISO_DAY.findall(value):
            try:
                found.append(("date", date(int(y), int(m), int(d)).isoformat()))
            except ValueError:
                continue

    def walk(key: str | None, value: object) -> None:
        if isinstance(value, dict):
            ident = next((v for k, v in value.items() if k.endswith("_id") and isinstance(v, str)), None)
            status = next((value[k] for k in _STATUS_KEYS if isinstance(value.get(k), str)), None)
            if ident and status:
                found.append(("status", f"{ident}: {status}"))
            for k, v in value.items():
                if k == "products" and isinstance(v, list):
                    found.extend(("product", item) for item in v if isinstance(item, str))
                if k not in _STATUS_KEYS:
                    walk(k, v)
        elif isinstance(value, list):
            for item in value:
                walk(key, item)
        elif isinstance(value, str):
            text(key, value)

    walk(None, data)
    return list(dict.fromkeys(found))
