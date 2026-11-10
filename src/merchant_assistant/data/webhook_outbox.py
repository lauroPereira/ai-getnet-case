"""Transactional assistant webhook intentions, independent of transport and process lifetime."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from merchant_assistant.guardrails.input import check_input

TARGETS = {
    "handoff.created": ("ticketing", "telegram"),
    "conversation.replied": ("ticketing", "merchant"),
    "handoff.closed": ("ticketing",),
}
# An intention whose attempts ran out (`exhausted`) is queued again once by the startup of a worker when its last
# attempt is older than this (task 99, spec v0.13.0 D5); an operator can resend it at any time.
RESEND_AFTER_SECONDS = 3600
# The Telegram adapter (task 100) shows the operator only the protocol and the masked summary: it receives nothing else.
TELEGRAM_FIELDS = ("case_id", "protocol", "summary")
# Destination -> (URL setting, secret setting); the environment variables are the same names in upper case.
DESTINATIONS = {
    "ticketing": ("ticketing_webhook_url", "ticketing_webhook_secret"),
    "merchant": ("conversation_webhook_url", "conversation_webhook_secret"),
    "telegram": ("telegram_webhook_url", "telegram_webhook_secret"),
}


def target_config(settings, name: str) -> tuple[str | None, str]:
    """(URL, secret) of a destination of DESTINATIONS. The one reading shared by the intention (`webhook_targets`) and
    the delivery (`Webhooks`), so that they never disagree about what can be delivered."""
    url_field, secret_field = DESTINATIONS[name]
    url, secret = getattr(settings, url_field), getattr(settings, secret_field)
    return url, secret.get_secret_value().strip() if secret else ""


def configuration_warnings(settings) -> list[str]:
    """Startup warnings for a destination that has a URL but no secret: it cannot sign, so it receives no intention
    (`webhook_targets`) and its events are neither queued nor sent. Names the variables, never their values."""
    warnings = []
    for name, fields in DESTINATIONS.items():
        url_variable, secret_variable = (field.upper() for field in fields)
        url, secret = target_config(settings, name)
        if url and not secret:
            warnings.append(
                f"{url_variable} is set but {secret_variable} is empty: webhook events for the {name} are not "
                f"queued or sent until the secret is configured"
            )
    return warnings


def webhook_targets(settings) -> set[str]:
    """Destinations that can be delivered to now: URL **and** secret configured, as the delivery requires. Only they
    receive an intention: a destination missing either one queues nothing (it would stay pending for good)."""
    return {name for name in DESTINATIONS if all(target_config(settings, name))}


def enqueue(conn, event_type: str, data: dict, key: str, targets: set[str] | None = None) -> str:
    """Enqueue alongside the domain change in the caller's transaction; repeat calls never replace the body.
    `targets` limits the destinations (default: all of the event's); a destination left out gets no intention."""
    event_id = "evt_" + hashlib.sha256(f"{event_type}:{key}".encode()).hexdigest()[:32]
    wanted = [target for target in TARGETS[event_type] if targets is None or target in targets]
    if not wanted:
        return event_id
    masked = dict(data)
    for field in ("reason", "summary", "pending_question", "draft_reply", "reply_text"):
        if isinstance(masked.get(field), str):
            masked[field] = check_input(masked[field]).masked
    if isinstance(masked.get("transcript"), list):
        masked["transcript"] = [
            item | {"text": check_input(item["text"]).masked} if isinstance(item.get("text"), str) else item
            for item in masked["transcript"]
        ]
    created_at = datetime.now(UTC).isoformat(timespec="seconds")
    for target in wanted:
        target_data = {k: v for k, v in masked.items() if not (target == "merchant" and k == "operator_id")}
        if target == "telegram":
            target_data = {k: v for k, v in target_data.items() if k in TELEGRAM_FIELDS}
        event = {"id": event_id, "type": event_type, "created_at": created_at, "data": target_data}
        conn.execute(
            "INSERT OR IGNORE INTO webhook_outbox (event_id,target,event,case_id,conversation_id,body) "
            "VALUES (?,?,?,?,?,?)",
            (event_id, target, event_type, data.get("case_id"), data.get("conversation_id"),
             json.dumps(event, ensure_ascii=False, separators=(",", ":"))),
        )
    return event_id


def resend(conn, event_id: str, target: str) -> int | None:
    """An `exhausted` intention goes back to `pending` with another round of attempts, in the caller's transaction.
    Returns its new `resend_count`, or None when the intention is not exhausted."""
    row = conn.execute(
        "UPDATE webhook_outbox SET status='pending', resend_count=resend_count+1 "
        "WHERE event_id=? AND target=? AND status='exhausted' RETURNING resend_count",
        (event_id, target),
    ).fetchone()
    return None if row is None else int(row[0])


def resend_exhausted(conn, *, now: datetime | None = None) -> list[tuple[str, str]]:
    """Startup: every intention exhausted for more than RESEND_AFTER_SECONDS (counted from its last attempt) and
    never sent again goes back to `pending` once, in the caller's transaction. Returns (event id, destination)."""
    cutoff = ((now or datetime.now(UTC)) - timedelta(seconds=RESEND_AFTER_SECONDS)).isoformat(timespec="seconds")
    rows = conn.execute(
        "SELECT o.event_id, o.target FROM webhook_outbox o WHERE o.status='exhausted' AND o.resend_count=0 "
        "AND COALESCE((SELECT MAX(d.created_at) FROM webhook_deliveries d "
        "WHERE d.event_id=o.event_id AND d.target=o.target), '') < ? ORDER BY o.rowid",
        (cutoff,),
    ).fetchall()
    return [(row[0], row[1]) for row in rows if resend(conn, row[0], row[1]) is not None]
