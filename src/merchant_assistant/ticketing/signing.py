"""Webhook signature of the contract: `X-Signature: t=<unix>,v1=<hex>`, v1 = HMAC-SHA256(secret, "<t>.<raw body>")."""

from __future__ import annotations

import hashlib
import hmac


def signature(secret: str, body: bytes, timestamp: int) -> str:
    digest = hmac.new(secret.encode("utf-8"), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def verify(secret: str, header: str | None, body: bytes, now: float, tolerance_s: int) -> bool:
    """True only for a matching v1 and a timestamp within the tolerance window (both directions)."""
    if not secret or not header:
        return False
    timestamp, candidates = None, []
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t" and value.isdigit():
            timestamp = int(value)
        elif key == "v1" and value:
            candidates.append(value)
    if timestamp is None or not candidates or abs(now - timestamp) > tolerance_s:
        return False
    expected = signature(secret, body, timestamp).split("v1=", 1)[1]
    return any(hmac.compare_digest(expected, candidate) for candidate in candidates)
