import sqlite3

from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.migrations import LATEST, current_version, migrate
from merchant_assistant.data.seed import seed


def tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_new_database_reaches_latest(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    assert current_version(conn) == LATEST
    assert {
        "conversations",
        "messages",
        "case_attempts",
        "customers",
        "enablement_requests",
        "sale_cancellations",
        "profiles",
        "profile_versions",
        "api_principals",
        "api_sessions",
        "router_comparisons",
        "run_snapshots",
        "kb_documents",
        "kb_drafts",
        "kb_versions",
        "kb_state",
        "kb_events",
    } <= tables(conn)


def test_down_and_up_keep_core_data(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    assert migrate(conn, 1) == [
        "down 0009_identity_hitl",
        "down 0008_demo_results",
        "down 0007_kb_versions",
        "down 0006_profiles_api",
        "down 0005_business_journeys",
        "down 0004_handoff_conversation",
        "down 0003_case_attempts",
        "down 0002_conversations",
    ]
    assert "conversations" not in tables(conn) and current_version(conn) == 1
    assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 2
    assert migrate(conn) == [
        "up 0002_conversations",
        "up 0003_case_attempts",
        "up 0004_handoff_conversation",
        "up 0005_business_journeys",
        "up 0006_profiles_api",
        "up 0007_kb_versions",
        "up 0008_demo_results",
        "up 0009_identity_hitl",
    ]
    assert current_version(conn) == LATEST


def test_database_from_010_is_upgraded_in_place(tmp_path):
    path = tmp_path / "old.sqlite3"
    raw = sqlite3.connect(path, isolation_level=None)
    raw.executescript(
        "CREATE TABLE customers (customer_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, "
        "segment TEXT NOT NULL); INSERT INTO customers VALUES ('c1','Old','x');"
    )
    raw.close()
    conn = connect(path)
    assert current_version(conn) == LATEST
    assert conn.execute("SELECT display_name FROM customers").fetchone()[0] == "Old"


def test_full_rollback_and_invalid_target(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    migrate(conn, 0)
    assert tables(conn) <= {"schema_version", "sqlite_sequence"}
    try:
        migrate(conn, LATEST + 1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_journeys_migration_round_trip_preserves_core_data(tmp_path):
    conn = connect(tmp_path / "journeys.sqlite3")
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    before = conn.execute("SELECT sale_id, gross_minor FROM sales ORDER BY sale_id").fetchall()
    assert migrate(conn, 4) == [
        "down 0009_identity_hitl",
        "down 0008_demo_results",
        "down 0007_kb_versions",
        "down 0006_profiles_api",
        "down 0005_business_journeys",
    ]
    assert "enablement_requests" not in tables(conn)
    assert [tuple(row) for row in conn.execute("SELECT sale_id, gross_minor FROM sales ORDER BY sale_id")] == [
        tuple(row) for row in before
    ]
    assert migrate(conn, 5) == ["up 0005_business_journeys"]
    assert current_version(conn) == 5


def test_identity_migration_0009_round_trip(tmp_path):
    conn = connect(tmp_path / "identity.sqlite3")
    assert migrate(conn, 8) == ["down 0009_identity_hitl"]
    conn.execute("INSERT INTO api_principals VALUES ('demo:default','demo','cliente1988','d1',1)")
    conn.execute(
        "INSERT INTO api_sessions(session_id,token_digest,principal_id,created_at,expires_at) "
        "VALUES ('s1','t1','demo:default','a','b')"
    )
    assert migrate(conn) == ["up 0009_identity_hitl"]
    # Existing principals keep their sessions and receive the scopes of their role.
    assert conn.execute("SELECT scopes FROM api_principals").fetchone()[0] == (
        '["support:read","handoff:create","conversation:read"]'
    )
    assert {"principal_id", "scope"} <= {r[1] for r in conn.execute("PRAGMA table_info(audit_events)")}
    assert {"rate_limit_hits", "auth_accounts", "revoked_tokens"} <= tables(conn)
    assert "on_behalf_of" in {r[1] for r in conn.execute("PRAGMA table_info(audit_events)")}
    conn.execute("INSERT INTO api_principals(principal_id,role,scopes) VALUES ('service:t','service','[]')")
    conn.execute("INSERT INTO api_principals VALUES ('merchant:c1','merchant','c1','d2',1,'[]')")
    conn.execute("INSERT INTO api_principals VALUES ('operator:op','operator',NULL,'d3',1,'[]')")
    conn.execute(
        "INSERT INTO api_sessions(session_id,token_digest,principal_id,created_at,expires_at) "
        "VALUES ('s2','t2','merchant:c1','a','b')"
    )
    assert migrate(conn, 8) == ["down 0009_identity_hitl"]
    # Rolling back drops what the 0008 schema cannot hold: merchant/operator principals and their sessions.
    assert [tuple(r) for r in conn.execute("SELECT principal_id FROM api_principals")] == [("demo:default",)]
    assert [tuple(r) for r in conn.execute("SELECT session_id FROM api_sessions")] == [("s1",)]
    assert not {"rate_limit_hits", "auth_accounts", "revoked_tokens"} & tables(conn)
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    try:
        conn.execute("INSERT INTO api_principals VALUES ('merchant:c2','merchant','c2','d4',1)")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("0008 schema must refuse the merchant role")
    assert migrate(conn) == ["up 0009_identity_hitl"] and current_version(conn) == LATEST


def test_queue_part_of_0009_keeps_cases_and_messages(tmp_path):
    conn = connect(tmp_path / "queue.sqlite3")
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    assert migrate(conn, 8) == ["down 0009_identity_hitl"]
    conn.execute(
        "INSERT INTO conversations (conversation_id, customer_id, state, created_at, updated_at) "
        "VALUES ('conv_legacy0001','cliente1988','handoff','t','t')"
    )
    conn.execute(
        "INSERT INTO messages (conversation_id, request_id, role, text, tokens, created_at) "
        "VALUES ('conv_legacy0001','req_1','merchant','Quero um atendente',4,'t')"
    )
    conn.execute(
        "INSERT INTO handoff_cases (case_id, protocol, customer_id, idempotency_key, reason, payload, created_at, "
        "conversation_id) VALUES ('hc_legacy','SIM-20261026-ABCDEF','cliente1988','k1','customer_request','{}','t',"
        "'conv_legacy0001')"
    )
    assert migrate(conn) == ["up 0009_identity_hitl"]
    row = conn.execute("SELECT * FROM handoff_cases WHERE case_id='hc_legacy'").fetchone()
    assert (row["protocol"], row["queue_state"], row["resume_count"], row["thread_id"]) == (
        "SIM-20261026-ABCDEF",
        "open",
        0,
        None,
    )
    assert {"handoff_events", "webhook_deliveries"} <= tables(conn)
    assert conn.execute("SELECT via FROM messages").fetchone()[0] is None
    conn.execute("INSERT INTO handoff_events VALUES ('hev_1','hc_legacy','approve','op_ana','key-00000001','{}','t')")
    try:
        conn.execute("INSERT INTO handoff_events VALUES ('hev_2','hc_legacy','reply','op_ana','key-00000001','{}','t')")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("the idempotency key must be unique")
    try:
        conn.execute("UPDATE handoff_cases SET queue_state='lost' WHERE case_id='hc_legacy'")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("queue_state must be checked")
    assert migrate(conn, 8) == ["down 0009_identity_hitl"]
    assert not {"handoff_events", "webhook_deliveries"} & tables(conn)
    assert "queue_state" not in {r[1] for r in conn.execute("PRAGMA table_info(handoff_cases)")}
    assert conn.execute("SELECT protocol FROM handoff_cases").fetchone()[0] == "SIM-20261026-ABCDEF"
    assert conn.execute("SELECT text FROM messages").fetchone()[0] == "Quero um atendente"
