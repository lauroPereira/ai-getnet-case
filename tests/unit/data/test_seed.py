import sqlite3
from contextlib import closing
from datetime import timedelta

from merchant_assistant.data.clock import FixedClock, SystemClock, today
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import MAIN_CUSTOMER, OTHER_CUSTOMER, seed


def test_seed_is_deterministic_with_fixed_clock(tmp_path):
    clock = FixedClock("2026-10-26T10:00:00")
    first = connect(tmp_path / "a.sqlite3")
    second = connect(tmp_path / "b.sqlite3")
    seed(first, clock)
    seed(second, clock)
    rows_a = [tuple(r) for r in first.execute("SELECT * FROM receivables ORDER BY receivable_id")]
    rows_b = [tuple(r) for r in second.execute("SELECT * FROM receivables ORDER BY receivable_id")]
    assert rows_a == rows_b
    credit = first.execute("SELECT * FROM receivables WHERE receivable_id='rcv_1988_0002'").fetchone()
    assert credit["expected_payment_date"] == "2026-10-27"
    assert credit["amount_minor"] == 116220


def test_main_customer_always_has_sales_yesterday(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    clock = SystemClock()
    seed(conn, clock)
    yesterday = (today(clock) - timedelta(days=1)).isoformat()
    sales = conn.execute(
        "SELECT COUNT(*) FROM sales WHERE customer_id=? AND substr(captured_at,1,10)=?", (MAIN_CUSTOMER, yesterday)
    ).fetchone()[0]
    assert sales == 3


def test_seed_is_idempotent_and_keeps_handoffs(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    clock = FixedClock("2026-10-26T10:00:00")
    seed(conn, clock)
    conn.execute(
        "INSERT INTO handoff_cases (case_id, protocol, customer_id, idempotency_key, reason, payload, created_at) "
        "VALUES ('h1','SIM-1',?, 'k1','reason','{}','2026-10-26T10:00:00')",
        (MAIN_CUSTOMER,),
    )
    counts = seed(conn, clock)
    assert counts["customers"] == 2
    assert conn.execute("SELECT COUNT(*) FROM handoff_cases").fetchone()[0] == 1


def test_customers_have_distinct_data(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    owners = {r["customer_id"] for r in conn.execute("SELECT customer_id FROM devices")}
    assert owners == {MAIN_CUSTOMER, OTHER_CUSTOMER}
    declined = conn.execute(
        "SELECT COUNT(*) FROM authorization_events WHERE status='declined' AND customer_id=?", (MAIN_CUSTOMER,)
    ).fetchone()[0]
    assert declined == 2


def test_second_seed_keeps_the_audit(tmp_path):
    """D27: restarting the container (bootstrap -> seed) recreates the synthetic data but keeps the audit trail."""
    conn = connect(tmp_path / "db.sqlite3")
    clock = FixedClock("2026-10-26T10:00:00")
    seed(conn, clock)
    conn.execute(
        "INSERT INTO audit_events (at, customer_id, tool, resource_id, outcome, principal_id, scope) "
        "VALUES ('2026-10-26T10:00:00', ?, 'get_device_status', NULL, 'ok', 'merchant:cliente1988', 'support:read')",
        (MAIN_CUSTOMER,),
    )
    conn.execute("DELETE FROM devices")
    counts = seed(conn, clock)
    assert "audit_events" not in counts
    assert conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0] > 0  # domain data is recreated


class _OtherWriterAfterTheFirstRead:
    """The seed's connection, with another connection writing right after the seed's first read, as the lease heartbeat
    of a live comparison can do when a second worker starts."""

    def __init__(self, conn, path):
        self._conn, self._path, self.other_writer_blocked = conn, path, None

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def execute(self, sql, *args):
        cursor = self._conn.execute(sql, *args)
        if self.other_writer_blocked is None and "sqlite_master" in sql:
            other = sqlite3.connect(self._path, timeout=0.1, isolation_level=None)
            try:
                other.execute("INSERT INTO probe VALUES (1)")
                self.other_writer_blocked = False
            except sqlite3.OperationalError as exc:
                if exc.sqlite_errorcode != sqlite3.SQLITE_BUSY:
                    raise
                self.other_writer_blocked = True
            finally:
                other.close()
        return cursor


def test_seed_takes_the_write_lock_before_its_first_read(tmp_path):
    """A deferred BEGIN read the schema and then wrote: a commit by another connection in between made the upgrade
    fail at once with "database is locked" (SQLITE_BUSY_SNAPSHOT ignores busy_timeout). BEGIN IMMEDIATE holds the
    write lock from the start, so the other writer waits for the seed instead."""
    path = tmp_path / "db.sqlite3"
    with closing(connect(path)) as conn:
        conn.execute("CREATE TABLE probe (x INTEGER)")
        seed(conn, FixedClock("2026-10-26T10:00:00"))  # schema complete, as in a later start
        racing = _OtherWriterAfterTheFirstRead(conn, path)
        seed(racing, FixedClock("2026-10-26T10:00:00"))
        assert racing.other_writer_blocked is True
        assert conn.execute("SELECT COUNT(*) FROM receivables").fetchone()[0] > 0
