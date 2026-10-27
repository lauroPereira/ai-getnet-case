"""Persistent spending guard: reserve before every paid call, settle with the real usage afterwards.

The ledger lives in SQLite under the runtime directory. Reservations are atomic (BEGIN IMMEDIATE), so concurrent
requests cannot overspend the installation limit.
"""

from __future__ import annotations

import math
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ABSOLUTE_BUDGET_LIMIT_USD = 5.0  # project-wide ceiling for every paid call; no setting or ledger may exceed it
CAMPAIGN_CAP_LIMIT_USD = 0.25  # largest additional cap a bounded QA campaign may fix

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
        if not math.isfinite(limit_usd) or not 0 <= limit_usd <= ABSOLUTE_BUDGET_LIMIT_USD:
            raise ValueError("Budget limit must be finite and between USD 0 and USD 5.")
        self.path = str(path)
        if self.path != ":memory:":
            ledger_path = Path(self.path)
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            sidecar = Path(f"{self.path}.limit")
            if not sidecar.exists():
                # A pre-existing ledger predates the sidecar and used the native USD 1 ceiling.
                # Keep that legacy ceiling unless the caller asks for a stricter one.
                ceiling = min(limit_usd, 1.0) if ledger_path.exists() else limit_usd
                try:
                    fd = os.open(sidecar, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                except FileExistsError:  # another process fixed the ceiling first
                    pass
                else:
                    with os.fdopen(fd, "w", encoding="ascii") as stream:
                        stream.write(f"{ceiling:.12g}\n")
            try:
                ceiling = float(sidecar.read_text(encoding="ascii").strip())
            except (OSError, ValueError) as exc:
                raise ValueError("Persistent budget ceiling is missing or invalid.") from exc
            if not math.isfinite(ceiling) or not 0 <= ceiling <= ABSOLUTE_BUDGET_LIMIT_USD or limit_usd > ceiling:
                raise ValueError("Configured budget limit exceeds the persistent ceiling.")
        self.limit_usd = limit_usd
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
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Reservation amount must be finite and non-negative.")
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
        if actual_usd is not None and (not math.isfinite(actual_usd) or actual_usd < 0):
            raise ValueError("Settled amount must be finite and non-negative.")
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status,reserved_usd,actual_usd FROM ledger WHERE id=?", (reservation_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Unknown budget reservation.")
            effective = float(row[1]) if actual_usd is None else actual_usd
            if row[0] == "settled":
                if math.isclose(float(row[2]), effective, rel_tol=0.0, abs_tol=1e-12):
                    conn.execute("COMMIT")
                    return
                raise ValueError("Budget reservation was already settled with a different amount.")
            if row[0] != "reserved":
                raise ValueError("Only a reserved budget entry can be settled.")
            conn.execute("UPDATE ledger SET status='settled',actual_usd=? WHERE id=?", (effective, reservation_id))
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def cancel(self, reservation_id: int) -> None:
        """Release a reservation only when canceled before provider dispatch."""
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE ledger SET status='cancelled',actual_usd=0 WHERE id=? AND status='reserved'",
                (reservation_id,),
            )
        finally:
            conn.close()

    def record(self, *, request_id: str | None, agent: str, model: str, actual_usd: float) -> None:
        """Direct entry for tiny costs measured after the fact (e.g. query embeddings)."""
        if not math.isfinite(actual_usd) or actual_usd < 0:
            raise ValueError("Recorded amount must be finite and non-negative.")
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


class FixedBudgetGuard:
    """Persistent one-time cap for a bounded QA campaign."""

    def __init__(self, path: Path | str, limit_usd: float, *, cap_id: str) -> None:
        if not 0 < limit_usd <= CAMPAIGN_CAP_LIMIT_USD:
            raise ValueError("QA campaign cap must be greater than zero and no more than USD 0.25.")
        self.guard = BudgetGuard(path, limit_usd)
        conn = self.guard._conn()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS fixed_budget_cap "
                "(cap_id TEXT PRIMARY KEY, limit_usd REAL NOT NULL, created_at TEXT NOT NULL)"
            )
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT cap_id,limit_usd FROM fixed_budget_cap").fetchall()
            if existing and (len(existing) != 1 or existing[0][0] != cap_id):
                conn.execute("ROLLBACK")
                raise ValueError("The persistent QA cap is already assigned to a different campaign.")
            row = conn.execute("SELECT limit_usd FROM fixed_budget_cap WHERE cap_id=?", (cap_id,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO fixed_budget_cap VALUES(?,?,?)",
                    (cap_id, limit_usd, datetime.now(UTC).isoformat(timespec="seconds")),
                )
            elif abs(float(row[0]) - limit_usd) > 1e-12:
                conn.execute("ROLLBACK")
                raise ValueError("The persistent QA budget cap is already fixed to a different amount.")
            conn.execute("COMMIT")
        finally:
            conn.close()
        self.cap_id = cap_id

    def reserve(self, **kwargs) -> int:
        return self.guard.reserve(**kwargs)

    def settle(self, reservation_id: int, actual_usd: float | None) -> None:
        self.guard.settle(reservation_id, actual_usd)

    def cancel(self, reservation_id: int) -> None:
        self.guard.cancel(reservation_id)

    def remaining(self) -> float:
        return self.guard.remaining()


class CombinedBudgetGuard:
    """Reserve paid calls against an existing ledger and the fixed QA cap."""

    def __init__(self, primary: BudgetGuard, campaign: FixedBudgetGuard) -> None:
        self.primary, self.campaign = primary, campaign

    def reserve(self, **kwargs) -> tuple[int, int]:
        campaign_id = self.campaign.reserve(**kwargs)
        try:
            primary_id = self.primary.reserve(**kwargs)
        except Exception:
            self.campaign.cancel(campaign_id)
            raise
        return primary_id, campaign_id

    def settle(self, reservation_ids: tuple[int, int], actual_usd: float | None) -> None:
        primary_id, campaign_id = reservation_ids
        self.primary.settle(primary_id, actual_usd)
        self.campaign.settle(campaign_id, actual_usd)

    def remaining(self) -> float:
        return min(self.primary.remaining(), self.campaign.remaining())
