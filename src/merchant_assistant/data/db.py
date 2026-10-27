"""SQLite storage for the synthetic merchant systems and local records (handoffs, audit)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
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

SYNTHETIC_TABLES = (
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
    conn.executescript(SCHEMA)
    return conn
