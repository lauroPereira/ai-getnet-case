"""Numbered, reversible schema migrations (decision 0006). `schema_version` records what is applied."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    up: str
    down: str


CORE_UP = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    segment TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contracts (
    customer_id TEXT PRIMARY KEY REFERENCES customers(customer_id),
    products TEXT NOT NULL,
    settlement_account_type TEXT NOT NULL,
    settlement_plan TEXT NOT NULL,
    effective_from TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sales (
    sale_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    captured_at TEXT NOT NULL,
    gross_minor INTEGER NOT NULL,
    currency TEXT NOT NULL,
    payment_type TEXT NOT NULL,
    installments INTEGER NOT NULL,
    channel TEXT NOT NULL,
    device_id TEXT
);
CREATE TABLE IF NOT EXISTS receivables (
    receivable_id TEXT PRIMARY KEY,
    sale_id TEXT NOT NULL REFERENCES sales(sale_id),
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    amount_minor INTEGER NOT NULL,
    fee_minor INTEGER NOT NULL,
    currency TEXT NOT NULL,
    expected_payment_date TEXT NOT NULL,
    source_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payouts (
    receivable_id TEXT PRIMARY KEY REFERENCES receivables(receivable_id),
    stage TEXT NOT NULL,
    credit_confirmed INTEGER NOT NULL,
    confirmed_at TEXT
);
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    model TEXT NOT NULL,
    connectivity TEXT NOT NULL,
    status TEXT NOT NULL,
    last_seen_at TEXT,
    config TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS response_codes (
    code TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    customer_message TEXT NOT NULL,
    next_step TEXT NOT NULL,
    retry_allowed INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS authorization_events (
    transaction_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    device_id TEXT,
    occurred_at TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency TEXT NOT NULL,
    payment_type TEXT NOT NULL,
    status TEXT NOT NULL,
    response_code TEXT
);
CREATE TABLE IF NOT EXISTS support_cases (
    case_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    topic TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    attempts TEXT NOT NULL,
    created_at TEXT NOT NULL,
    closed_at TEXT
);
CREATE TABLE IF NOT EXISTS handoff_cases (
    case_id TEXT PRIMARY KEY,
    protocol TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    reason TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    resource_id TEXT,
    outcome TEXT NOT NULL
);
"""

CORE_DOWN = """
DROP TABLE IF EXISTS audit_events;
DROP TABLE IF EXISTS handoff_cases;
DROP TABLE IF EXISTS support_cases;
DROP TABLE IF EXISTS authorization_events;
DROP TABLE IF EXISTS response_codes;
DROP TABLE IF EXISTS devices;
DROP TABLE IF EXISTS payouts;
DROP TABLE IF EXISTS receivables;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS contracts;
DROP TABLE IF EXISTS customers;
"""

CONVERSATIONS_UP = """
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    state TEXT NOT NULL,
    topic TEXT,
    technical_cycles INTEGER NOT NULL DEFAULT 0,
    resolution_evidence TEXT,
    prefix TEXT,
    prefix_topic TEXT,
    prefix_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS conversations_customer ON conversations(customer_id);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
    request_id TEXT NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    route TEXT,
    status TEXT,
    tokens INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_conversation ON messages(conversation_id, id);
"""

CONVERSATIONS_DOWN = """
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS conversations;
"""

ATTEMPTS_UP = """
CREATE TABLE IF NOT EXISTS case_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
    cycle INTEGER NOT NULL,
    step TEXT NOT NULL,
    result TEXT NOT NULL,
    evidence TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS attempts_conversation ON case_attempts(conversation_id, id);
"""

ATTEMPTS_DOWN = "DROP TABLE IF EXISTS case_attempts;"

HANDOFF_CONVERSATION_UP = """
ALTER TABLE handoff_cases ADD COLUMN conversation_id TEXT;
CREATE INDEX IF NOT EXISTS handoff_conversation ON handoff_cases(conversation_id);
"""

HANDOFF_CONVERSATION_DOWN = """
DROP INDEX IF EXISTS handoff_conversation;
ALTER TABLE handoff_cases DROP COLUMN conversation_id;
"""

JOURNEYS_UP = """
CREATE TABLE contract_pricing_context (
    customer_id TEXT PRIMARY KEY REFERENCES customers(customer_id),
    pricing_plan TEXT NOT NULL,
    pricing_version TEXT NOT NULL,
    effective_from TEXT NOT NULL
);
CREATE TABLE enablement_requests (
    request_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    scheme TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'rejected')),
    protocol TEXT NOT NULL UNIQUE,
    requested_at TEXT NOT NULL,
    activated_at TEXT
);
CREATE INDEX enablement_requests_customer ON enablement_requests(customer_id, requested_at);
CREATE TABLE sale_cancellations (
    transaction_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    status TEXT NOT NULL CHECK (status IN ('requested', 'completed', 'rejected', 'unknown')),
    requested_at TEXT NOT NULL,
    processed_at TEXT,
    reason_code TEXT,
    FOREIGN KEY (transaction_id) REFERENCES sales(sale_id)
);
CREATE INDEX sale_cancellations_customer ON sale_cancellations(customer_id, requested_at);
"""

JOURNEYS_DOWN = """
DROP INDEX IF EXISTS sale_cancellations_customer;
DROP TABLE IF EXISTS sale_cancellations;
DROP INDEX IF EXISTS enablement_requests_customer;
DROP TABLE IF EXISTS enablement_requests;
DROP TABLE IF EXISTS contract_pricing_context;
"""

MIGRATIONS: list[Migration] = [
    Migration(1, "core", CORE_UP, CORE_DOWN),
    Migration(2, "conversations", CONVERSATIONS_UP, CONVERSATIONS_DOWN),
    Migration(3, "case_attempts", ATTEMPTS_UP, ATTEMPTS_DOWN),
    Migration(4, "handoff_conversation", HANDOFF_CONVERSATION_UP, HANDOFF_CONVERSATION_DOWN),
    Migration(5, "business_journeys", JOURNEYS_UP, JOURNEYS_DOWN),
]
LATEST = MIGRATIONS[-1].version


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, name TEXT NOT NULL, "
        "applied_at TEXT NOT NULL)"
    )


def current_version(conn: sqlite3.Connection) -> int:
    _ensure_table(conn)
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return int(row[0] or 0)


def migrate(conn: sqlite3.Connection, target: int | None = None) -> list[str]:
    """Moves the schema up or down to `target` (default: latest). Returns the applied steps."""
    target = LATEST if target is None else target
    if not 0 <= target <= LATEST:
        raise ValueError(f"unknown schema version {target}")
    applied: list[str] = []
    current = current_version(conn)
    for m in MIGRATIONS:
        if current < m.version <= target:
            conn.executescript(m.up)
            conn.execute(
                "INSERT OR IGNORE INTO schema_version VALUES (?,?,?)",
                (m.version, m.name, datetime.now(UTC).isoformat(timespec="seconds")),
            )
            applied.append(f"up {m.version:04d}_{m.name}")
    for m in reversed(MIGRATIONS):
        if target < m.version <= current:
            conn.executescript(m.down)
            conn.execute("DELETE FROM schema_version WHERE version = ?", (m.version,))
            applied.append(f"down {m.version:04d}_{m.name}")
    return applied
