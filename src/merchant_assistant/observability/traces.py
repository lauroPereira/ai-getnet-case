"""Per-request traces (steps with duration, tokens and cost) stored locally and emitted as JSON logs."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger("merchant_assistant.trace")

TRACE_SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    request_id TEXT PRIMARY KEY,
    at TEXT NOT NULL,
    user_id TEXT NOT NULL,
    route TEXT,
    status TEXT,
    language TEXT,
    duration_ms INTEGER,
    cost_usd REAL,
    model_calls INTEGER,
    tool_calls INTEGER,
    errors TEXT,
    detail TEXT
);
CREATE TABLE IF NOT EXISTS steps (
    request_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    step TEXT NOT NULL,
    started_at TEXT NOT NULL,
    duration_ms INTEGER,
    status TEXT NOT NULL,
    detail TEXT,
    PRIMARY KEY (request_id, seq)
);
"""


@dataclass
class Step:
    seq: int
    step: str
    started_at: str
    duration_ms: int = 0
    status: str = "ok"
    detail: dict = field(default_factory=dict)


class TraceRecorder:
    def __init__(self, request_id: str) -> None:
        self.request_id = request_id
        self.steps: list[Step] = []
        self._t0 = time.perf_counter()

    def start(self, step: str) -> tuple[Step, float]:
        s = Step(len(self.steps) + 1, step, datetime.now(UTC).isoformat(timespec="milliseconds"))
        self.steps.append(s)
        return s, time.perf_counter()

    def finish(self, step: Step, started: float, status: str = "ok", **detail: object) -> None:
        step.duration_ms = int((time.perf_counter() - started) * 1000)
        step.status = status
        step.detail.update(detail)
        log.info("step", extra={"event": {"request_id": self.request_id, **asdict(step)}})

    def event(self, step: str, status: str = "ok", **detail: object) -> None:
        s, t = self.start(step)
        self.finish(s, t, status, **detail)

    @property
    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._t0) * 1000)


class TraceStore:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._conn()
        conn.executescript(TRACE_SCHEMA)
        conn.close()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, recorder: TraceRecorder, summary: dict) -> None:
        conn = self._conn()
        try:
            conn.execute("BEGIN")
            conn.execute(
                "INSERT OR REPLACE INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    recorder.request_id,
                    datetime.now(UTC).isoformat(timespec="seconds"),
                    summary.get("user_id", ""),
                    summary.get("route"),
                    summary.get("status"),
                    summary.get("language"),
                    recorder.elapsed_ms,
                    summary.get("cost_usd"),
                    summary.get("model_calls"),
                    summary.get("tool_calls"),
                    json.dumps(summary.get("errors", [])),
                    json.dumps(summary.get("detail", {}), default=str),
                ),
            )
            conn.executemany(
                "INSERT OR REPLACE INTO steps VALUES (?,?,?,?,?,?,?)",
                [
                    (
                        recorder.request_id,
                        s.seq,
                        s.step,
                        s.started_at,
                        s.duration_ms,
                        s.status,
                        json.dumps(s.detail, default=str),
                    )
                    for s in recorder.steps
                ],
            )
            conn.execute("COMMIT")
        finally:
            conn.close()

    def get(self, request_id: str) -> dict | None:
        conn = self._conn()
        try:
            req = conn.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
            if req is None:
                return None
            steps = conn.execute("SELECT * FROM steps WHERE request_id=? ORDER BY seq", (request_id,)).fetchall()
            out = dict(req)
            out["errors"] = json.loads(out["errors"] or "[]")
            out["detail"] = json.loads(out["detail"] or "{}")
            out["steps"] = [{**dict(s), "detail": json.loads(s["detail"] or "{}")} for s in steps]
            return out
        finally:
            conn.close()
