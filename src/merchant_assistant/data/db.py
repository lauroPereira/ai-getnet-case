"""SQLite storage for the synthetic merchant systems and local records (conversations, handoffs, audit).

The schema is owned by `migrations.py`; `connect` brings any database to the latest version."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from merchant_assistant.data.migrations import migrate

SYNTHETIC_TABLES = (
    "sale_cancellations",
    "enablement_requests",
    "contract_pricing_context",
    "audit_events",
    "authorization_events",
    "payouts",
    "receivables",
    "sales",
    "devices",
    "support_cases",
    "contracts",
    "response_codes",
    "customers",
)


def connect(path: Path | str) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    migrate(conn)
    return conn
