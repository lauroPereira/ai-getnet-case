"""Persistent spending guard: reserve before every paid call, settle with the real usage afterwards.

The ledger lives in SQLite under the runtime directory. Reservations are atomic (BEGIN IMMEDIATE), so concurrent
requests cannot overspend the installation limit.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    request_id TEXT,
    agent TEXT NOT NULL,
    model TEXT NOT NULL,
    reserved_usd REAL NOT NULL,
    actual_usd REAL,
    status TEXT NOT NULL
);
"""


class BudgetExceeded(Exception):
    def __init__(self, scope: str, needed: float, remaining: float) -> None:
        super().__init__(f"{scope} budget exceeded: needed {needed:.5f} USD, remaining {remaining:.5f} USD")
        self.scope, self.needed, self.remaining = scope, needed, remaining


class BudgetGuard:
    def __init__(self, path: Path | str, limit_usd: float) -> None:
        self.path, self.limit_usd = str(path), limit_usd
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(LEDGER_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    @staticmethod
    def _committed(conn: sqlite3.Connection) -> float:
        row = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN status='settled' THEN actual_usd WHEN status='reserved' "
            "THEN reserved_usd ELSE 0 END), 0) FROM ledger"
        ).fetchone()
        return float(row[0])

    def spent(self) -> float:
        conn = self._conn()
        try:
            return self._committed(conn)
        finally:
            conn.close()

    def remaining(self) -> float:
        return max(self.limit_usd - self.spent(), 0.0)

    def reserve(self, *, request_id: str | None, agent: str, model: str, amount: float) -> int:
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            committed = self._committed(conn)
            if committed + amount > self.limit_usd:
                conn.execute("ROLLBACK")
                raise BudgetExceeded("installation", amount, self.limit_usd - committed)
            cur = conn.execute(
                "INSERT INTO ledger (at, request_id, agent, model, reserved_usd, status) "
                "VALUES (?,?,?,?,?, 'reserved')",
                (datetime.now(UTC).isoformat(timespec="seconds"), request_id, agent, model, amount),
            )
            conn.execute("COMMIT")
            return int(cur.lastrowid)
        finally:
            conn.close()

    def settle(self, reservation_id: int, actual_usd: float | None) -> None:
        conn = self._conn()
        try:
            if actual_usd is None:  # usage unknown: keep the reserved amount as spent
                conn.execute(
                    "UPDATE ledger SET status='settled', actual_usd=reserved_usd WHERE id=?", (reservation_id,)
                )
            else:
                conn.execute(
                    "UPDATE ledger SET status='settled', actual_usd=? WHERE id=?", (actual_usd, reservation_id)
                )
        finally:
            conn.close()

    def record(self, *, request_id: str | None, agent: str, model: str, actual_usd: float) -> None:
        """Direct entry for tiny costs measured after the fact (e.g. query embeddings)."""
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO ledger (at, request_id, agent, model, reserved_usd, actual_usd, status) "
                "VALUES (?,?,?,?,?,?, 'settled')",
                (datetime.now(UTC).isoformat(timespec="seconds"), request_id, agent, model, actual_usd, actual_usd),
            )
        finally:
            conn.close()

    def record_embedding(self, model: str, tokens: int) -> None:
        from merchant_assistant.llm.pricing import model_price

        self.record(
            request_id=None,
            agent="embeddings",
            model=model,
            actual_usd=tokens * model_price(model)["input_per_mtok"] / 1e6,
        )
