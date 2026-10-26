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
        "INSERT INTO handoff_cases VALUES ('h1','SIM-1',?, 'k1','reason','{}','2026-10-26T10:00:00')", (MAIN_CUSTOMER,)
    )
    counts = seed(conn, clock)
    assert counts["customers"] == 2
    assert conn.execute("SELECT COUNT(*) FROM handoff_cases").fetchone()[0] == 1


def test_customers_have_distinct_data(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    owners = {r["customer_id"] for r in conn.execute("SELECT customer_id FROM devices")}
    assert owners == {MAIN_CUSTOMER, OTHER_CUSTOMER}
    declined = conn.execute("SELECT COUNT(*) FROM authorization_events WHERE status='declined' AND customer_id=?",
                            (MAIN_CUSTOMER,)).fetchone()[0]
    assert declined == 2
