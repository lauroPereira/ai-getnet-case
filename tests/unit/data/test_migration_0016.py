"""Migration 0016 (v0.13.0, task 99; spec D4, D5): the comparison lease and the exhausted webhook intentions, up and
down."""

import sqlite3

import pytest

from merchant_assistant.data.db import connect
from merchant_assistant.data.migrations import LATEST, current_version, migrate

DOWN_16 = "down 0016_workers_and_resend"
UP_16 = "up 0016_workers_and_resend"


def columns(conn, table):
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def add_comparison(conn, comparison_id, state, **lease):
    names = ["comparison_id", "principal_id", "state", "config", "cells", "failures", "estimate", "created_at",
             "updated_at", *lease]
    values = [comparison_id, "demo:default", state, "{}", "[]", "[]", "{}", "t", "t", *lease.values()]
    conn.execute(f"INSERT INTO comparisons ({','.join(names)}) VALUES ({','.join('?' * len(names))})", values)


def add_outbox(conn, event_id, status, attempts, target="ticketing"):
    conn.execute(
        "INSERT INTO webhook_outbox (event_id,target,event,case_id,body,attempts,status) "
        "VALUES (?,?,'handoff.created','hc_1',?,?,?)",
        (event_id, target, f'{{"id":"{event_id}"}}', attempts, status),
    )


def outbox(conn):
    return [tuple(row) for row in conn.execute("SELECT * FROM webhook_outbox ORDER BY rowid")]


def test_0016_round_trip_keeps_every_comparison_and_intention(tmp_path):
    conn = connect(tmp_path / "workers.sqlite3")
    assert LATEST == 16 and current_version(conn) == 16
    assert {"worker_id", "heartbeat_at"} <= set(columns(conn, "comparisons"))
    assert columns(conn, "webhook_outbox")[-1] == "resend_count"

    assert migrate(conn, 15) == [DOWN_16]
    assert not {"worker_id", "heartbeat_at"} & set(columns(conn, "comparisons"))
    assert "resend_count" not in columns(conn, "webhook_outbox")
    add_comparison(conn, "pcmp_running", "running")
    add_comparison(conn, "pcmp_done", "completed")
    add_outbox(conn, "evt_b", "failed", 3)  # inserted first: the rowid order is the delivery order and must survive
    add_outbox(conn, "evt_a", "pending", 1)
    add_outbox(conn, "evt_c", "delivered", 1, target="merchant")
    add_outbox(conn, "evt_d", "rejected", 1)
    before = outbox(conn)

    assert migrate(conn) == [UP_16] and current_version(conn) == 16
    up = outbox(conn)
    assert [row[0] for row in up] == ["evt_b", "evt_a", "evt_c", "evt_d"]
    assert [(row[7], row[8]) for row in up] == [("exhausted", 0), ("pending", 0), ("delivered", 0), ("rejected", 0)]
    assert [row[:7] for row in up] == [row[:7] for row in before]
    lease = conn.execute("SELECT comparison_id, worker_id, heartbeat_at FROM comparisons ORDER BY comparison_id")
    assert [tuple(row) for row in lease] == [("pcmp_done", None, None), ("pcmp_running", None, None)]
    with pytest.raises(sqlite3.IntegrityError):  # `failed` is `exhausted` from 0016 on
        add_outbox(conn, "evt_e", "failed", 3)
    conn.execute("UPDATE webhook_outbox SET resend_count=2 WHERE event_id='evt_b'")
    conn.execute("UPDATE comparisons SET worker_id='host:1:abcd1234', heartbeat_at='2026-11-07T12:00:00.000+00:00'")
    assert conn.execute("PRAGMA index_list(webhook_outbox)").fetchall()

    assert migrate(conn, 15) == [DOWN_16]
    assert outbox(conn) == before  # `exhausted` is `failed` again; the resend count is dropped
    assert [row[0] for row in conn.execute("SELECT comparison_id FROM comparisons ORDER BY comparison_id")] == [
        "pcmp_done", "pcmp_running"
    ]
    with pytest.raises(sqlite3.IntegrityError):  # the 0015 schema has no `exhausted`
        add_outbox(conn, "evt_e", "exhausted", 3)
    assert migrate(conn) == [UP_16]
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
