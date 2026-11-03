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

PROFILES_API_UP = """
CREATE TABLE profiles (
    profile_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    demo_allowed INTEGER NOT NULL DEFAULT 0,
    draft_version INTEGER NOT NULL DEFAULT 1,
    published_version INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE profile_versions (
    profile_id TEXT NOT NULL REFERENCES profiles(profile_id),
    version INTEGER NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('draft', 'published')),
    agents TEXT NOT NULL,
    digest TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (profile_id, version)
);
CREATE TABLE api_principals (
    principal_id TEXT PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('demo', 'admin')),
    customer_id TEXT,
    access_key_digest TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE api_sessions (
    session_id TEXT PRIMARY KEY,
    token_digest TEXT NOT NULL UNIQUE,
    principal_id TEXT NOT NULL REFERENCES api_principals(principal_id),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE TABLE router_comparisons (
    comparison_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL REFERENCES api_principals(principal_id),
    customer_id TEXT NOT NULL,
    conversation_id TEXT,
    message_digest TEXT NOT NULL,
    state_digest TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    profile_version INTEGER NOT NULL,
    selected_mechanism TEXT NOT NULL CHECK (selected_mechanism IN ('llm', 'jev')),
    decisions TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE run_snapshots (
    request_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL REFERENCES api_principals(principal_id),
    customer_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    profile_version INTEGER NOT NULL,
    snapshot TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX api_sessions_expiration ON api_sessions(expires_at);
CREATE INDEX comparisons_owner ON router_comparisons(principal_id, created_at);
CREATE INDEX snapshots_owner ON run_snapshots(principal_id, created_at);
"""

PROFILES_API_DOWN = """
DROP INDEX IF EXISTS snapshots_owner;
DROP INDEX IF EXISTS comparisons_owner;
DROP INDEX IF EXISTS api_sessions_expiration;
DROP TABLE IF EXISTS run_snapshots;
DROP TABLE IF EXISTS router_comparisons;
DROP TABLE IF EXISTS api_sessions;
DROP TABLE IF EXISTS api_principals;
DROP TABLE IF EXISTS profile_versions;
DROP TABLE IF EXISTS profiles;
"""

KB_VERSIONS_UP = """
CREATE TABLE kb_documents (
    document_id TEXT PRIMARY KEY, title TEXT NOT NULL, source_kind TEXT NOT NULL
      CHECK(source_kind IN ('public_official','simulated_internal')),
    url TEXT, metadata TEXT NOT NULL, content TEXT NOT NULL, content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE kb_drafts (
    document_id TEXT PRIMARY KEY REFERENCES kb_documents(document_id), revision INTEGER NOT NULL,
    content TEXT NOT NULL, content_hash TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE kb_versions (
    version_id TEXT PRIMARY KEY, parent_version_id TEXT, collection_name TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL CHECK(state IN ('building','testing','ready','active','retired','failed')),
    manifest TEXT NOT NULL, snapshot TEXT NOT NULL, test_result TEXT, error TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE kb_state (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1), active_version_id TEXT,
    previous_version_id TEXT, revision INTEGER NOT NULL DEFAULT 0
);
INSERT INTO kb_state(singleton, active_version_id, previous_version_id, revision) VALUES(1,NULL,NULL,0);
CREATE TABLE kb_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL, action TEXT NOT NULL,
    from_version_id TEXT, to_version_id TEXT, evidence TEXT NOT NULL, created_at TEXT NOT NULL
);
"""

KB_VERSIONS_DOWN = """
DROP TABLE IF EXISTS kb_events;
DROP TABLE IF EXISTS kb_state;
DROP TABLE IF EXISTS kb_versions;
DROP TABLE IF EXISTS kb_drafts;
DROP TABLE IF EXISTS kb_documents;
"""

DEMO_RESULTS_UP = """
ALTER TABLE api_sessions ADD COLUMN message_count INTEGER NOT NULL DEFAULT 0;
CREATE TABLE run_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    principal_id TEXT NOT NULL,
    method TEXT NOT NULL CHECK (method IN ('deterministic', 'model')),
    rubric TEXT NOT NULL,
    rubric_version TEXT NOT NULL,
    evaluator TEXT NOT NULL,
    config_digest TEXT NOT NULL,
    result TEXT NOT NULL,
    evidence TEXT NOT NULL,
    critical_failures TEXT NOT NULL,
    cost_usd REAL,
    state TEXT NOT NULL CHECK (state IN ('running', 'completed', 'failed')),
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX run_evaluations_run ON run_evaluations(request_id, created_at);
CREATE TABLE comparisons (
    comparison_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('running', 'completed', 'failed', 'partial')),
    config TEXT NOT NULL,
    cells TEXT NOT NULL,
    failures TEXT NOT NULL,
    estimate TEXT NOT NULL,
    cost_usd REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX comparisons_owner_v060 ON comparisons(principal_id, created_at);
"""

DEMO_RESULTS_DOWN = """
DROP INDEX IF EXISTS comparisons_owner_v060;
DROP TABLE IF EXISTS comparisons;
DROP INDEX IF EXISTS run_evaluations_run;
DROP TABLE IF EXISTS run_evaluations;
ALTER TABLE api_sessions DROP COLUMN message_count;
"""

# v0.7.0 (ADR 0017). `api_principals` is rebuilt because SQLite cannot change a CHECK constraint in place: the
# documented procedure (foreign keys off, new table, copy, drop, rename) keeps the rows that sessions, comparisons and
# run snapshots reference. Principals now come from verified JWTs, so the access key digest becomes optional, and
# existing demo/admin principals receive the scopes of their role. Accounts keep only PBKDF2 hashes. The handoff
# queue (task 64) lives in the same migration: queue state, operator, resume counter, checkpoint thread (D6), ticket
# id, events with a unique idempotency key (D10), webhook deliveries and `messages.via`. Cases created before 0009
# enter the queue as `open`. Task 66: one `webhook_deliveries` row per outgoing attempt (event id, error) and
# `webhook_inbox`, the ids of the ticketing events already answered (a repeated id has no new effect).
IDENTITY_UP = """
PRAGMA foreign_keys = OFF;
BEGIN;
CREATE TABLE api_principals_v9 (
    principal_id TEXT PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('demo', 'admin', 'merchant', 'operator', 'service')),
    customer_id TEXT,
    access_key_digest TEXT UNIQUE,
    active INTEGER NOT NULL DEFAULT 1,
    scopes TEXT NOT NULL DEFAULT '[]'
);
INSERT INTO api_principals_v9 (principal_id, role, customer_id, access_key_digest, active, scopes)
SELECT principal_id, role, customer_id, access_key_digest, active,
       CASE role
           WHEN 'admin' THEN
               '["kb:admin","profiles:admin","support:read","handoff:create","conversation:read"]'
           ELSE '["support:read","handoff:create","conversation:read"]'
       END
FROM api_principals;
DROP TABLE api_principals;
ALTER TABLE api_principals_v9 RENAME TO api_principals;
CREATE TABLE auth_accounts (
    account_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('user', 'client')),
    principal_id TEXT NOT NULL,
    role TEXT NOT NULL,
    customer_id TEXT,
    secret_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);
CREATE TABLE revoked_tokens (
    jti TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT NOT NULL
);
CREATE INDEX revoked_tokens_expiration ON revoked_tokens(expires_at);
ALTER TABLE audit_events ADD COLUMN principal_id TEXT;
ALTER TABLE audit_events ADD COLUMN scope TEXT;
ALTER TABLE audit_events ADD COLUMN on_behalf_of TEXT;
CREATE INDEX audit_events_principal ON audit_events(principal_id, id);
CREATE TABLE rate_limit_hits (
    principal_id TEXT NOT NULL,
    window_start INTEGER NOT NULL,
    count INTEGER NOT NULL,
    PRIMARY KEY (principal_id, window_start)
);
ALTER TABLE handoff_cases ADD COLUMN queue_state TEXT NOT NULL DEFAULT 'open'
    CHECK (queue_state IN ('open', 'claimed', 'answered', 'rejected', 'closed'));
ALTER TABLE handoff_cases ADD COLUMN claimed_by TEXT;
ALTER TABLE handoff_cases ADD COLUMN claimed_at TEXT;
ALTER TABLE handoff_cases ADD COLUMN answered_at TEXT;
ALTER TABLE handoff_cases ADD COLUMN closed_at TEXT;
ALTER TABLE handoff_cases ADD COLUMN closed_by TEXT;
ALTER TABLE handoff_cases ADD COLUMN resume_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE handoff_cases ADD COLUMN channel TEXT;
ALTER TABLE handoff_cases ADD COLUMN thread_id TEXT;
ALTER TABLE handoff_cases ADD COLUMN ticket_id TEXT;
CREATE INDEX handoff_queue ON handoff_cases(queue_state, created_at);
CREATE TABLE handoff_events (
    event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES handoff_cases(case_id),
    action TEXT NOT NULL CHECK (action IN ('claim', 'approve', 'reply', 'reject', 'close')),
    operator_id TEXT NOT NULL,
    idempotency_key TEXT UNIQUE,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX handoff_events_case ON handoff_events(case_id, created_at);
CREATE TABLE webhook_deliveries (
    delivery_id TEXT PRIMARY KEY,
    event TEXT NOT NULL,
    target TEXT NOT NULL,
    case_id TEXT,
    conversation_id TEXT,
    attempt INTEGER NOT NULL,
    status TEXT NOT NULL,
    response_code INTEGER,
    created_at TEXT NOT NULL,
    event_id TEXT,
    error TEXT
);
CREATE INDEX webhook_deliveries_case ON webhook_deliveries(case_id, created_at);
CREATE INDEX webhook_deliveries_conversation ON webhook_deliveries(conversation_id, created_at);
CREATE TABLE webhook_inbox (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    event TEXT NOT NULL,
    case_id TEXT,
    status_code INTEGER NOT NULL,
    response TEXT NOT NULL,
    received_at TEXT NOT NULL
);
ALTER TABLE messages ADD COLUMN via TEXT;
ALTER TABLE messages ADD COLUMN meta TEXT;
ALTER TABLE messages ADD COLUMN delivered_at TEXT;
ALTER TABLE handoff_cases ADD COLUMN resume_status TEXT
    CHECK (resume_status IS NULL OR resume_status IN ('pending', 'done', 'failed'));
ALTER TABLE handoff_cases ADD COLUMN resume_error TEXT;
ALTER TABLE handoff_cases ADD COLUMN resume_started_at TEXT;
ALTER TABLE handoff_cases ADD COLUMN resume_request_id TEXT;
COMMIT;
PRAGMA foreign_keys = ON;
"""

# Rolling back removes what only exists from 0009 on: merchant, operator and service principals with their sessions,
# Router comparisons and run snapshots (the 0008 schema cannot hold them), accounts, revoked tokens, the queue columns,
# handoff events and webhook deliveries. Cases and messages themselves are kept.
IDENTITY_DOWN = """
PRAGMA foreign_keys = OFF;
BEGIN;
ALTER TABLE handoff_cases DROP COLUMN resume_request_id;
ALTER TABLE handoff_cases DROP COLUMN resume_started_at;
ALTER TABLE handoff_cases DROP COLUMN resume_error;
ALTER TABLE handoff_cases DROP COLUMN resume_status;
ALTER TABLE messages DROP COLUMN delivered_at;
ALTER TABLE messages DROP COLUMN meta;
ALTER TABLE messages DROP COLUMN via;
DROP TABLE IF EXISTS webhook_inbox;
DROP INDEX IF EXISTS webhook_deliveries_conversation;
DROP INDEX IF EXISTS webhook_deliveries_case;
DROP TABLE IF EXISTS webhook_deliveries;
DROP INDEX IF EXISTS handoff_events_case;
DROP TABLE IF EXISTS handoff_events;
DROP INDEX IF EXISTS handoff_queue;
ALTER TABLE handoff_cases DROP COLUMN ticket_id;
ALTER TABLE handoff_cases DROP COLUMN thread_id;
ALTER TABLE handoff_cases DROP COLUMN channel;
ALTER TABLE handoff_cases DROP COLUMN resume_count;
ALTER TABLE handoff_cases DROP COLUMN closed_by;
ALTER TABLE handoff_cases DROP COLUMN closed_at;
ALTER TABLE handoff_cases DROP COLUMN answered_at;
ALTER TABLE handoff_cases DROP COLUMN claimed_at;
ALTER TABLE handoff_cases DROP COLUMN claimed_by;
ALTER TABLE handoff_cases DROP COLUMN queue_state;
DROP TABLE IF EXISTS rate_limit_hits;
DROP INDEX IF EXISTS audit_events_principal;
ALTER TABLE audit_events DROP COLUMN on_behalf_of;
ALTER TABLE audit_events DROP COLUMN scope;
ALTER TABLE audit_events DROP COLUMN principal_id;
DROP INDEX IF EXISTS revoked_tokens_expiration;
DROP TABLE IF EXISTS revoked_tokens;
DROP TABLE IF EXISTS auth_accounts;
DELETE FROM run_snapshots WHERE principal_id IN
    (SELECT principal_id FROM api_principals WHERE role IN ('merchant', 'operator', 'service'));
DELETE FROM router_comparisons WHERE principal_id IN
    (SELECT principal_id FROM api_principals WHERE role IN ('merchant', 'operator', 'service'));
DELETE FROM api_sessions WHERE principal_id IN
    (SELECT principal_id FROM api_principals WHERE role IN ('merchant', 'operator', 'service'));
CREATE TABLE api_principals_v8 (
    principal_id TEXT PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('demo', 'admin')),
    customer_id TEXT,
    access_key_digest TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1
);
INSERT INTO api_principals_v8 (principal_id, role, customer_id, access_key_digest, active)
SELECT principal_id, role, customer_id, COALESCE(access_key_digest, 'migrated:' || principal_id), active
FROM api_principals WHERE role IN ('demo', 'admin');
DROP TABLE api_principals;
ALTER TABLE api_principals_v8 RENAME TO api_principals;
COMMIT;
PRAGMA foreign_keys = ON;
"""

MIGRATIONS: list[Migration] = [
    Migration(1, "core", CORE_UP, CORE_DOWN),
    Migration(2, "conversations", CONVERSATIONS_UP, CONVERSATIONS_DOWN),
    Migration(3, "case_attempts", ATTEMPTS_UP, ATTEMPTS_DOWN),
    Migration(4, "handoff_conversation", HANDOFF_CONVERSATION_UP, HANDOFF_CONVERSATION_DOWN),
    Migration(5, "business_journeys", JOURNEYS_UP, JOURNEYS_DOWN),
    Migration(6, "profiles_api", PROFILES_API_UP, PROFILES_API_DOWN),
    Migration(7, "kb_versions", KB_VERSIONS_UP, KB_VERSIONS_DOWN),
    Migration(8, "demo_results", DEMO_RESULTS_UP, DEMO_RESULTS_DOWN),
    Migration(9, "identity_hitl", IDENTITY_UP, IDENTITY_DOWN),
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
