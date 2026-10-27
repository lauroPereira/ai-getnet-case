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
    assert {"conversations", "messages", "case_attempts", "customers"} <= tables(conn)


def test_down_and_up_keep_core_data(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    assert migrate(conn, 1) == ["down 0003_case_attempts", "down 0002_conversations"]
    assert "conversations" not in tables(conn) and current_version(conn) == 1
    assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 2
    assert migrate(conn) == ["up 0002_conversations", "up 0003_case_attempts"]
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
