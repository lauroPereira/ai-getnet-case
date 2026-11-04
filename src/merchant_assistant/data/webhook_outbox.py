"""Transactional assistant webhook intentions, independent of transport and process lifetime."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from merchant_assistant.guardrails.input import check_input

TARGETS = {
    "handoff.created": ("ticketing",),
    "conversation.replied": ("ticketing", "merchant"),
    "handoff.closed": ("ticketing",),
}


def webhook_targets(settings) -> set[str]:
    """Destinations with a URL configured now. Only they receive an intention: an empty URL queues nothing."""
    urls = {"ticketing": settings.ticketing_webhook_url, "merchant": settings.conversation_webhook_url}
    return {name for name, url in urls.items() if url}


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
        event = {"id": event_id, "type": event_type, "created_at": created_at, "data": target_data}
        conn.execute(
            "INSERT OR IGNORE INTO webhook_outbox (event_id,target,event,case_id,conversation_id,body) "
            "VALUES (?,?,?,?,?,?)",
            (event_id, target, event_type, data.get("case_id"), data.get("conversation_id"),
             json.dumps(event, ensure_ascii=False, separators=(",", ":"))),
        )
    return event_id
