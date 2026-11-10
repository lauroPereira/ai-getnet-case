"""v0.10.0, task 84 (spec D3, CA-58): a profile comparison stopped by an API restart becomes `interrupted`, keeps the
cells it finished and resumes through the API running only the cells without a result.

Synthetic and offline only: scripted model, hashing embedder, in-memory Qdrant, temporary SQLite databases. The
restart is a new app (new orchestrator and scripted model) over the same runtime directory, started with its lifespan.
Since task 99 a running comparison holds a lease in the database instead of a thread registry: a process that died
stops renewing it, which these tests reproduce by ageing the heartbeat (the two-process test is in
`test_v0130_workers.py`).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant import comparisons
from merchant_assistant.api import v1
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.rag.embed import OpenAIEmbedder
from merchant_assistant.testing import join_comparison, key_token

DEMO_KEY = "synthetic-demo-access-key-v0100"
ADMIN_KEY = "synthetic-admin-access-key-v0100"


@pytest.fixture
def keys(settings):
    settings.api_demo_password = SecretStr(DEMO_KEY)
    settings.api_admin_password = SecretStr(ADMIN_KEY)
    return settings


def login(client, key=DEMO_KEY) -> dict:
    return {"Authorization": f"Bearer {key_token(client, key)}"}


def selection() -> dict:
    return {
        "profiles": [{"profile_id": "reference", "profile_version": 1}, {"profile_id": "hybrid", "profile_version": 1}],
        "scenario_ids": ["SC-RECEIVABLES", "SC-HANDOFF"],
        "repetitions": 1,
        "router_mechanism": "llm",
        "reuse_recorded": False,
    }


def create(client, headers, selected=None) -> str:
    selected = selection() if selected is None else selected
    estimate = client.post("/v1/comparisons/estimate", headers=headers, json=selected)
    assert estimate.status_code == 200, estimate.json()
    body = estimate.json()
    created = client.post(
        "/v1/comparisons",
        headers=headers,
        json=selected
        | {
            "confirmed": True,
            "max_cost_usd": body["estimated_cost_usd"],
            "expected_estimate_digest": body["estimate_digest"],
        },
    )
    assert created.status_code == 202, created.json()
    return created.json()["comparison_id"]


def join(comparison_id: str) -> None:
    join_comparison(comparison_id)


def expire_lease(settings, comparison_id: str) -> None:
    """The holder's process is gone: its last heartbeat is older than the lease."""
    conn = sqlite3.connect(settings.db_path)
    try:
        conn.execute(
            "UPDATE comparisons SET heartbeat_at='2026-01-01T00:00:00.000+00:00' WHERE comparison_id=?",
            (comparison_id,),
        )
        conn.commit()
    finally:
        conn.close()


def lease(settings, comparison_id: str) -> tuple[str | None, str | None]:
    conn = sqlite3.connect(settings.db_path)
    try:
        return tuple(
            conn.execute(
                "SELECT worker_id, heartbeat_at FROM comparisons WHERE comparison_id=?", (comparison_id,)
            ).fetchone()
        )
    finally:
        conn.close()


def db_state(settings, comparison_id: str) -> str:
    conn = sqlite3.connect(settings.db_path)
    try:
        return conn.execute("SELECT state FROM comparisons WHERE comparison_id=?", (comparison_id,)).fetchone()[0]
    finally:
        conn.close()


def ledger(settings) -> dict[str, int]:
    conn = sqlite3.connect(settings.runtime_path / "budget.sqlite3")
    try:
        rows = conn.execute(
            "SELECT request_id, COUNT(*) FROM ledger WHERE status IN ('reserved','settled') GROUP BY request_id"
        )
        return {row[0]: row[1] for row in rows}
    finally:
        conn.close()


class Executions:
    """Wraps `v1.execute_run`: records every execution, and can simulate the process dying during one of them (the
    real run happens, then nothing else the thread does reaches the database, as after a `taskkill`)."""

    def __init__(self, monkeypatch, kill_at: int | None = None, fail_at: int | None = None, llm=None) -> None:
        self.real, self.real_save = v1.execute_run, comparisons._save
        self.calls: list[tuple[str, str, str]] = []
        self.llm, self.model_calls = llm, []  # scripted model calls made inside each execution
        self.kill_at, self.fail_at, self.killed = kill_at, fail_at, False
        monkeypatch.setattr(v1, "execute_run", self.execute_run)
        monkeypatch.setattr(comparisons, "_save", self.save)
        real_refund = v1.refund_demo_messages
        monkeypatch.setattr(v1, "refund_demo_messages", lambda *a, **k: None if self.killed else real_refund(*a, **k))

    def execute_run(self, app_state, conn, **kwargs):
        if self.killed:
            raise RuntimeError("process is gone")
        self.calls.append((kwargs["scenario_id"], kwargs["profile"]["profile_id"], kwargs["request_id"]))
        if len(self.calls) == self.fail_at:
            raise v1.RunFailure(503, "provider_unavailable", "synthetic failure")
        before = len(self.llm.calls) if self.llm else 0
        try:
            result = self.real(app_state, conn, **kwargs)
        finally:
            self.model_calls.append(len(self.llm.calls) - before if self.llm else None)
        if len(self.calls) == self.kill_at:
            self.killed = True
            raise RuntimeError("process is gone")
        return result

    def save(self, *args, **kwargs):
        return None if self.killed else self.real_save(*args, **kwargs)


def interrupted_comparison(settings, offline, monkeypatch, *, kill_at=2):
    """Runs a comparison whose process dies after persisting the snapshot, then restarts the API."""
    client, _, _ = offline()
    executions = Executions(monkeypatch, kill_at=kill_at)
    comparison_id = create(client, login(client))
    join(comparison_id)
    assert db_state(settings, comparison_id) == "running"  # nothing recorded the end: the process was gone
    expire_lease(settings, comparison_id)  # and nothing renews its lease any more
    killed_request_id = executions.calls[kill_at - 1][2]
    monkeypatch.undo()
    restarted, orchestrator, llm = offline()
    return comparison_id, killed_request_id, restarted, orchestrator, llm


def test_restart_marks_the_comparison_interrupted_and_resume_runs_only_the_missing_cells(
    keys, offline, monkeypatch, caplog
):
    settings = keys
    caplog.set_level(logging.INFO, logger="merchant_assistant.comparisons")
    comparison_id, killed_id, restarted, orchestrator, llm = interrupted_comparison(settings, offline, monkeypatch)
    # The attempt that died has a cost in the ledger: its settled calls, plus a reservation never settled because the
    # process stopped during the call (review P2-3: the cost must reach `cost_usd`, once).
    budget = sqlite3.connect(settings.runtime_path / "budget.sqlite3")
    budget.execute("UPDATE ledger SET actual_usd=0.004 WHERE request_id=? AND status='settled'", (killed_id,))
    budget.execute(
        "INSERT INTO ledger (at, request_id, agent, model, reserved_usd, status) "
        "VALUES ('t', ?, 'router', 'synthetic', 0.002, 'reserved')",
        (killed_id,),
    )
    budget.commit()
    settled = budget.execute(
        "SELECT COUNT(*) FROM ledger WHERE request_id=? AND status='settled'", (killed_id,)
    ).fetchone()[0]
    budget.close()
    attempt_cost = settled * 0.004 + 0.002
    recorded = sqlite3.connect(settings.db_path)
    cost_before = recorded.execute("SELECT cost_usd FROM comparisons WHERE comparison_id=?", (comparison_id,))
    cost_before = cost_before.fetchone()
    recorded.close()
    with TestClient(restarted.app) as client:  # the lifespan runs: the lease of the old process expired
        assert db_state(settings, comparison_id) == "interrupted"
        assert [
            getattr(r, "event", None)
            for r in caplog.records
            if r.name == "merchant_assistant.comparisons" and r.getMessage() == "comparison interrupted"
        ] == [{"comparison_id": comparison_id}]
        headers = login(client)
        lost = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
        assert lost["state"] == "interrupted" and lost["failures"][-1]["code"] == "interrupted"
        first, recovered, *rest = lost["cells"]
        assert first["status"] == "completed" and first["request_id"]  # the finished cell is preserved
        assert recovered["status"] == "completed" and recovered["request_id"] == killed_id
        persisted = client.get(f"/v1/runs/{killed_id}", headers=headers).json()
        assert recovered["checks"] == persisted["checks"] and recovered["checks"]["total"] > 0
        assert recovered["cost_usd"] == persisted["cost_estimate_usd"]
        assert recovered["duration_ms"] == persisted["duration_ms"]
        assert recovered["model_calls"] == persisted["model_calls"] > 0
        assert recovered["route"] == persisted["result"]["route"]
        assert recovered["response_status"] == persisted["result"]["status"]
        assert [cell["status"] for cell in rest] == ["pending"] * 2 and not any("request_id" in c for c in rest)
        assert "in_flight_request_id" not in str(lost["cells"])
        recovered_cost = float(recovered["cost_usd"] or 0.0)
        assert lost["cost_usd"] == pytest.approx(cost_before[0] + max(recovered_cost, attempt_cost))  # added once
        again = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
        assert again["cost_usd"] == lost["cost_usd"] and again["cells"] == lost["cells"]  # never added twice
        before = ledger(settings)
        assert set(before) == {first["request_id"], killed_id}

        executions = Executions(monkeypatch, llm=llm)
        resumed = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert resumed.status_code == 202, resumed.json()
        assert resumed.json() == {"comparison_id": comparison_id, "state": "running", "resumed_cells": 2}
        join(comparison_id)
        done = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()

    assert done["state"] == "completed", done["failures"]
    cells = done["cells"]
    assert len(cells) == 4 and all(cell["status"] == "completed" for cell in cells)
    assert cells[0] == first | {"model_calls": cells[0]["model_calls"]}  # untouched, only its call count recorded
    assert [(c[0], c[1]) for c in executions.calls] == [(c["scenario_id"], c["profile_id"]) for c in rest]
    new_ids = [cell["request_id"] for cell in cells[2:]]
    assert [c[2] for c in executions.calls] == new_ids and len(set(new_ids)) == 2
    assert cells[1] == recovered
    # Every call of the scripted model after the restart happened inside the two missing cells, and the finished
    # cells keep their ledger rows from before the resume.
    assert all(executions.model_calls) and len(llm.calls) == sum(executions.model_calls)
    after = ledger(settings)
    assert set(after) == set(before) | set(new_ids)
    assert {rid: after[rid] for rid in before} == before
    expected_cost = sum(float(cell["cost_usd"] or 0) for cell in cells) + max(0.0, attempt_cost - recovered_cost)
    assert done["cost_usd"] == pytest.approx(expected_cost)
    assert done["aggregates"]["profiles"][0]["sample_size"] == 2 and done["aggregates"]["profiles"][1]["sample_size"]


def test_resume_finalizes_when_the_last_cell_was_recovered(keys, offline, monkeypatch):
    comparison_id, killed_id, restarted, _, llm = interrupted_comparison(keys, offline, monkeypatch, kill_at=4)
    before = ledger(keys)
    with TestClient(restarted.app) as client:
        headers = login(client)
        path = f"/v1/comparisons/{comparison_id}"
        interrupted = client.get(path, headers=headers).json()
        assert interrupted["state"] == "interrupted"
        assert interrupted["cells"][-1]["request_id"] == killed_id
        resumed = client.post(f"{path}/resume", headers=headers)
        assert resumed.status_code == 202 and resumed.json()["resumed_cells"] == 0
        join(comparison_id)
        done = client.get(path, headers=headers).json()
        assert done["state"] == "completed"
        assert done["cost_usd"] == interrupted["cost_usd"]
        assert done["cells"][-1] == interrupted["cells"][-1]
    assert llm.calls == [] and ledger(keys) == before


@pytest.mark.parametrize("ledger_state", ["empty", "paid", "unreadable"])
def test_interrupted_cell_without_durable_result_uses_ledger_to_decide_retry(keys, offline, monkeypatch, ledger_state):
    settings = keys
    real_attempt = comparisons._ledger_attempt
    client, _, llm = offline()
    headers = login(client)
    with monkeypatch.context() as setup:
        setup.setattr(comparisons, "_run", lambda *args, **kwargs: None)
        comparison_id = create(client, headers)
        join(comparison_id)

    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM comparisons WHERE comparison_id=?", (comparison_id,)).fetchone()
    cells = json.loads(row["cells"])
    cell = cells[0]
    request_id = "req_synthetic_interrupted_cell"
    cell["in_flight_request_id"] = request_id
    customer_id = conn.execute(
        "SELECT customer_id FROM api_principals WHERE principal_id=?", (row["principal_id"],)
    ).fetchone()[0]
    partial = {
        "profile_id": cell["profile_id"],
        "profile_version": cell["profile_version"],
        "scenario_id": cell["scenario_id"],
        "purpose": "comparison",
        "profile_comparison_id": comparison_id,
    }
    conn.execute("UPDATE comparisons SET cells=? WHERE comparison_id=?", (json.dumps(cells), comparison_id))
    conn.execute(
        "INSERT INTO run_snapshots VALUES (?,?,?,?,?,?,?)",
        (
            request_id,
            row["principal_id"],
            customer_id,
            cell["profile_id"],
            cell["profile_version"],
            json.dumps(partial),
            "synthetic",
        ),
    )
    conn.commit()
    before_cost = float(row["cost_usd"] or 0.0)
    conn.close()

    if ledger_state in ("paid", "unreadable"):
        budget = sqlite3.connect(settings.runtime_path / "budget.sqlite3")
        budget.execute(
            "INSERT INTO ledger (at, request_id, agent, model, reserved_usd, status) "
            "VALUES ('synthetic', ?, 'router', 'synthetic', 0.002, 'reserved')",
            (request_id,),
        )
        budget.commit()
        budget.close()
    if ledger_state == "unreadable":
        monkeypatch.setattr(comparisons, "_ledger_attempt", lambda *args, **kwargs: None)

    expire_lease(settings, comparison_id)
    path = f"/v1/comparisons/{comparison_id}"
    interrupted = client.get(path, headers=headers).json()
    interrupted_cell = interrupted["cells"][0]
    assert interrupted["state"] == "interrupted"
    if ledger_state == "paid":
        assert interrupted_cell["status"] == "failed"
        assert interrupted_cell["request_id"] == request_id
        assert interrupted_cell["error"] == "interrupted_after_paid_attempt"
        assert interrupted_cell["interrupted_attempts"] == [{"request_id": request_id, "cost_usd": 0.002}]
        assert interrupted["cost_usd"] == pytest.approx(before_cost + 0.002)
    elif ledger_state == "unreadable":
        assert interrupted_cell["status"] == "failed"
        assert interrupted_cell["request_id"] == request_id
        assert interrupted_cell["error"] == "interrupted_cost_unknown"
        assert interrupted_cell["interrupted_attempts"] == [{"request_id": request_id, "cost_usd": None}]
        assert interrupted["cost_usd"] == pytest.approx(before_cost)
    else:
        assert interrupted_cell["status"] == "pending"
        assert "request_id" not in interrupted_cell
        assert interrupted_cell["interrupted_attempts"] == [{"request_id": request_id, "cost_usd": 0.0}]
        assert interrupted["cost_usd"] == pytest.approx(before_cost)

    executions = Executions(monkeypatch, llm=llm)
    if ledger_state == "unreadable":
        for suffix in ("", "?retry_failed=true"):
            refused = client.post(f"{path}/resume{suffix}", headers=headers)
            assert refused.status_code == 409 and refused.json()["error"]["code"] == "execution_cost_unknown"
        assert executions.calls == []
        monkeypatch.setattr(comparisons, "_ledger_attempt", real_attempt)
    resumed = client.post(f"{path}/resume", headers=headers)
    assert resumed.status_code == 202, resumed.json()
    assert resumed.json()["resumed_cells"] == (4 if ledger_state == "empty" else 3)
    join(comparison_id)
    after_resume = client.get(path, headers=headers).json()
    if ledger_state == "unreadable":
        assert after_resume["cost_usd"] == pytest.approx(before_cost + 0.002)

    if ledger_state == "empty":
        assert after_resume["state"] == "completed"
        assert after_resume["cells"][0]["request_id"] != request_id
        assert len(executions.calls) == 4
    else:
        assert after_resume["state"] == "partial"
        assert after_resume["cells"][0]["request_id"] == request_id
        assert after_resume["cells"][0]["status"] == "failed"
        assert len(executions.calls) == 3
        explicit = client.post(f"{path}/resume?retry_failed=true", headers=headers)
        assert explicit.status_code == 202 and explicit.json()["resumed_cells"] == 1
        join(comparison_id)
        done = client.get(path, headers=headers).json()
        retried = done["cells"][0]
        assert done["state"] == "completed" and len(executions.calls) == 4
        assert retried["status"] == "completed" and retried["request_id"] == executions.calls[-1][2] != request_id
        assert retried["previous_request_ids"] == [request_id]
        if ledger_state == "unreadable":
            assert retried["interrupted_attempts"] == [{"request_id": request_id, "cost_usd": 0.002}]
        else:
            assert retried["interrupted_attempts"] == interrupted_cell["interrupted_attempts"]
        assert done["cost_usd"] == pytest.approx(after_resume["cost_usd"] + retried["cost_usd"])


def test_resume_is_refused_while_running_and_after_completion_and_lifespan_spares_a_live_thread(
    keys, offline, monkeypatch
):
    client, _, _ = offline()
    headers = login(client)
    release = threading.Event()
    real = v1.execute_run

    def blocked(*args, **kwargs):
        release.wait(timeout=30)
        return real(*args, **kwargs)

    monkeypatch.setattr(v1, "execute_run", blocked)
    comparison_id = create(client, headers)
    try:
        running = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert running.status_code == 409 and running.json()["error"]["code"] == "comparison_running"
        with TestClient(offline()[0].app):  # another worker starting leaves the live run (fresh lease) alone
            assert db_state(keys, comparison_id) == "running"
    finally:
        release.set()
        join(comparison_id)
    assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "completed"
    completed = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
    assert completed.status_code == 409 and completed.json()["error"]["code"] == "comparison_completed"
    missing = client.post("/v1/comparisons/pcmp_missing0000000000/resume", headers=headers)
    assert missing.status_code == 404
    other = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=login(client, ADMIN_KEY))
    assert other.status_code == 404  # same owner rule as the read
    assert client.post(f"/v1/comparisons/{comparison_id}/resume").status_code == 401


def test_failed_cells_run_again_only_with_retry_failed(keys, offline, monkeypatch):
    client, _, llm = offline()
    headers = login(client)
    executions = Executions(monkeypatch, fail_at=2, llm=llm)
    comparison_id = create(client, headers)
    join(comparison_id)
    partial = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    assert partial["state"] == "partial"
    failed = [cell for cell in partial["cells"] if cell["status"] == "failed"]
    assert len(failed) == 1 and failed[0]["request_id"] == executions.calls[1][2]

    nothing = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
    assert nothing.status_code == 409 and nothing.json()["error"]["code"] == "nothing_to_resume"

    executions.calls.clear()
    executions.model_calls.clear()
    executions.fail_at = None
    calls_before = len(llm.calls)
    retried = client.post(f"/v1/comparisons/{comparison_id}/resume?retry_failed=true", headers=headers)
    assert retried.status_code == 202 and retried.json()["resumed_cells"] == 1
    join(comparison_id)
    done = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    assert done["state"] == "completed", done["failures"]
    assert [(c[0], c[1]) for c in executions.calls] == [(failed[0]["scenario_id"], failed[0]["profile_id"])]
    cell = done["cells"][partial["cells"].index(failed[0])]
    assert cell["previous_request_ids"] == [failed[0]["request_id"]] and cell["request_id"] == executions.calls[0][2]
    for before, after in zip(partial["cells"], done["cells"], strict=True):
        if before["status"] == "completed":  # finished cells keep their result
            assert after["request_id"] == before["request_id"]
    assert len(llm.calls) - calls_before == executions.model_calls[0] > 0  # only the retried cell called the model


@pytest.mark.parametrize("unreadable", [False, True])
@pytest.mark.parametrize("trace_unavailable", [False, True])
def test_execution_error_accounts_paid_attempt_before_running_more_cells(
    keys, offline, monkeypatch, unreadable, trace_unavailable
):
    client, orchestrator, _ = offline()
    headers = login(client)
    calls = []
    actual = float(keys.max_request_cost_usd) * 1.5
    ledger_readable = not unreadable
    real_attempt = comparisons._ledger_attempt

    def run_then_fail(app_state, conn, **kwargs):
        request_id = kwargs["request_id"]
        calls.append(request_id)
        with kwargs["reservation_fence"](request_id):
            reservation = orchestrator.budget.reserve(
                request_id=request_id, agent="router", model="synthetic", amount=actual / 2
            )
        orchestrator.budget.settle(reservation, actual)
        if trace_unavailable:
            raise v1.RunFailure(503, "provider_unavailable", "synthetic failure after payment")
        raise RuntimeError("synthetic provider failure after payment")

    def attempt(budget, request_id):
        return real_attempt(budget, request_id) if ledger_readable else None

    monkeypatch.setattr(v1, "execute_run", run_then_fail)
    monkeypatch.setattr(comparisons, "_ledger_attempt", attempt)
    if trace_unavailable:

        def unavailable_trace(_):
            raise sqlite3.OperationalError("synthetic trace unavailable")

        monkeypatch.setattr(orchestrator, "trace", unavailable_trace)
    comparison_id = create(client, headers, selection() | {"scenario_ids": ["SC-RECEIVABLES"]})
    join(comparison_id)
    path = f"/v1/comparisons/{comparison_id}"
    result = client.get(path, headers=headers).json()
    assert len(calls) == 1
    assert result["cells"][0]["status"] == "failed"
    assert result["cells"][0]["request_id"] == calls[0]
    assert result["cells"][1]["status"] == "skipped"
    assert result["cost_usd"] == pytest.approx(0 if unreadable else actual)
    assert not any(failure["code"] == "comparison_failed" for failure in result["failures"])
    if trace_unavailable:
        assert result["cells"][0]["error"] == "provider_unavailable"
        assert any(failure["code"] == "trace_unavailable" for failure in result["failures"])
        if not unreadable:
            assert result["cells"][1]["error"] == "trace_unavailable"

    if unreadable:
        assert result["cells"][1]["error"] == "execution_cost_unknown"
        denied = client.post(f"{path}/resume", headers=headers)
        assert denied.status_code == 409 and denied.json()["error"]["code"] == "execution_cost_unknown"
        assert len(calls) == 1
        ledger_readable = True

    for _ in range(2):
        resumed = client.post(f"{path}/resume", headers=headers)
        assert resumed.status_code == 202, resumed.json()
        join(comparison_id)
        result = client.get(path, headers=headers).json()
        assert result["cost_usd"] == pytest.approx(actual)
        assert result["cells"][1]["error"] == "comparison_cap_reached"
        assert len(calls) == 1
    assert ledger(keys) == {calls[0]: 1}


def test_completed_execution_waits_for_ledger_before_continuing(keys, offline, monkeypatch):
    client, orchestrator, _ = offline()
    headers = login(client)
    real_execute, real_attempt = v1.execute_run, comparisons._ledger_attempt
    calls = []
    readable = False
    actual = float(keys.max_request_cost_usd) * 1.5

    def execute(*args, **kwargs):
        calls.append(kwargs["request_id"])
        result = real_execute(*args, **kwargs)
        with kwargs["reservation_fence"](calls[-1]):
            reservation = orchestrator.budget.reserve(
                request_id=calls[-1], agent="router", model="synthetic", amount=actual / 2
            )
        orchestrator.budget.settle(reservation, actual)
        return result

    def attempt(budget, request_id):
        return real_attempt(budget, request_id) if readable or request_id not in calls else None

    monkeypatch.setattr(v1, "execute_run", execute)
    monkeypatch.setattr(comparisons, "_ledger_attempt", attempt)
    comparison_id = create(client, headers, selection() | {"scenario_ids": ["SC-RECEIVABLES"]})
    join(comparison_id)
    path = f"/v1/comparisons/{comparison_id}"
    result = client.get(path, headers=headers).json()
    assert len(calls) == 1 and result["cells"][0]["request_id"] == calls[0]
    assert result["cells"][0]["status"] == "completed" and result["cells"][1]["error"] == "execution_cost_unknown"
    assert result["cost_usd"] == 0
    assert client.post(f"{path}/resume", headers=headers).status_code == 409
    readable = True
    for _ in range(2):
        assert client.post(f"{path}/resume", headers=headers).status_code == 202
        join(comparison_id)
        result = client.get(path, headers=headers).json()
        assert result["cost_usd"] == pytest.approx(actual)
        assert result["cells"][1]["error"] == "comparison_cap_reached"
        assert len(calls) == 1


def test_recovered_snapshot_waits_for_ledger_before_resuming(keys, offline, monkeypatch):
    comparison_id, request_id, client, orchestrator, llm = interrupted_comparison(keys, offline, monkeypatch)
    reservation = orchestrator.budget.reserve(request_id=request_id, agent="router", model="synthetic", amount=0.002)
    orchestrator.budget.settle(reservation, 0.002)
    real_attempt = comparisons._ledger_attempt
    actual = real_attempt(orchestrator.budget, request_id)[1]
    monkeypatch.setattr(comparisons, "_ledger_attempt", lambda *_: None)
    headers = login(client)
    path = f"/v1/comparisons/{comparison_id}"
    interrupted = client.get(path, headers=headers).json()
    recovered = interrupted["cells"][1]
    assert recovered["status"] == "completed" and recovered["request_id"] == request_id
    before = interrupted["cost_usd"]
    for suffix in ("", "?retry_failed=true"):
        response = client.post(f"{path}/resume{suffix}", headers=headers)
        assert response.status_code == 409 and response.json()["error"]["code"] == "execution_cost_unknown"
    assert llm.calls == []
    monkeypatch.setattr(comparisons, "_ledger_attempt", real_attempt)
    assert client.post(f"{path}/resume", headers=headers).status_code == 202
    join(comparison_id)
    done = client.get(path, headers=headers).json()
    expected = before + max(actual, recovered["cost_usd"] or 0)
    assert done["cost_usd"] == pytest.approx(expected)
    assert done["cells"][1]["request_id"] == request_id
    assert client.get(path, headers=headers).json()["cost_usd"] == done["cost_usd"]
    assert client.post(f"{path}/resume", headers=headers).status_code == 409


def test_resume_reserves_only_what_is_missing_and_refuses_changed_fixed_factors(keys, offline, monkeypatch):
    settings = keys
    comparison_id, _, restarted, orchestrator, _ = interrupted_comparison(settings, offline, monkeypatch)
    with TestClient(restarted.app) as client:
        headers = login(client)
        per_cell = float(settings.max_request_cost_usd)
        # Two cells are missing. The budget for those two is enough.
        monkeypatch.setattr(orchestrator.budget, "remaining", lambda: 2 * per_cell - 1e-9)
        short = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert short.status_code == 429 and short.json()["error"]["code"] == "installation_budget_exceeded"
        monkeypatch.setattr(orchestrator.budget, "remaining", lambda: 2 * per_cell)
        monkeypatch.setattr(comparisons, "prompt_versions", lambda _: {"router": "999"})
        changed = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert changed.status_code == 409 and changed.json()["error"]["code"] == "fixed_factors_changed"
        assert db_state(settings, comparison_id) == "interrupted"  # refusals change nothing
        monkeypatch.undo()
        monkeypatch.setattr(orchestrator.budget, "remaining", lambda: 2 * per_cell)
        resumed = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert resumed.status_code == 202, resumed.json()
        join(comparison_id)
        assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "completed"


# --- Task 84 review, round 1: races around the claim (P2-1, P2-2); the lease of task 99 keeps them closed ------------


class Window:
    """Wraps `comparisons.connect` for the request threads: when the connection whose statement made a comparison
    `running` (the INSERT of `start`, the claim of `resume`) closes, after its commit and before the comparison thread
    starts, runs `during` once. The comparison threads get the real connection."""

    def __init__(self, monkeypatch, marker: str, during) -> None:
        real, window = comparisons.connect, self
        self.ran, self.params = False, ()

        class Conn:
            def __init__(self, conn) -> None:
                self._conn, self._hit = conn, False

            def execute(self, sql, *args):
                if marker in sql and not self._hit:
                    self._hit, window.params = True, args[0] if args else ()
                return self._conn.execute(sql, *args)

            def close(self) -> None:
                self._conn.close()
                if self._hit and not window.ran:
                    window.ran = True
                    during()

            def __getattr__(self, name):
                return getattr(self._conn, name)

        def connect(path):
            conn = real(path)
            return conn if threading.current_thread().name.startswith("comparison-") else Conn(conn)

        monkeypatch.setattr(comparisons, "connect", connect)


def test_read_and_resume_while_start_is_registering_never_run_a_cell_twice(keys, offline, monkeypatch):
    client, _, llm = offline()
    headers = login(client)
    executions = Executions(monkeypatch, llm=llm)
    seen: dict = {}

    def during():  # the row is already `running` under a fresh lease; the thread has not started
        comparison_id = window.params[0]
        seen["read"] = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"]
        seen["resume"] = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)

    window = Window(monkeypatch, "INSERT INTO comparisons", during)
    comparison_id = create(client, headers)
    join(comparison_id)
    assert window.ran and seen["read"] == "running"  # never `interrupted` while its lease is fresh
    assert seen["resume"].status_code == 409 and seen["resume"].json()["error"]["code"] == "comparison_running"
    done = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    assert done["state"] == "completed", done["failures"]
    assert len(executions.calls) == 4 and len({call[2] for call in executions.calls}) == 4  # each cell once


def test_read_and_resume_while_resume_is_registering_never_run_a_cell_twice(keys, offline, monkeypatch):
    settings = keys
    comparison_id, _, restarted, _, llm = interrupted_comparison(settings, offline, monkeypatch)
    with TestClient(restarted.app) as client:
        headers = login(client)
        executions = Executions(monkeypatch, llm=llm)
        seen: dict = {}

        def during():  # the claim committed `running` and its lease; the resumed thread has not started
            seen["read"] = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"]
            seen["resume"] = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)

        window = Window(monkeypatch, "SET state='running'", during)
        resumed = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert resumed.status_code == 202, resumed.json()
        join(comparison_id)
        done = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    assert window.ran and seen["read"] == "running"
    assert seen["resume"].status_code == 409 and seen["resume"].json()["error"]["code"] == "comparison_running"
    assert done["state"] == "completed", done["failures"]
    assert len(executions.calls) == 2  # each missing cell once


def test_two_concurrent_resumes_claim_the_comparison_once(keys, offline, monkeypatch):
    settings = keys
    comparison_id, _, restarted, orchestrator, llm = interrupted_comparison(settings, offline, monkeypatch)
    with TestClient(restarted.app) as client:
        headers = login(client)
        executions = Executions(monkeypatch, llm=llm)
        barrier, lock, calls = threading.Barrier(2, timeout=30), threading.Lock(), []
        real_capture = orchestrator.knowledge_base.capture_active

        def capture_active():  # both requests read the same `interrupted` row, then both try to claim it
            with lock:
                calls.append(None)
                first_two = len(calls) <= 2
            if first_two:
                barrier.wait()
            return real_capture()

        monkeypatch.setattr(orchestrator.knowledge_base, "capture_active", capture_active)
        responses: list = []
        workers = [
            threading.Thread(
                target=lambda: responses.append(client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers))
            )
            for _ in range(2)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=60)
        assert sorted(response.status_code for response in responses) == [202, 409]
        refused = next(response for response in responses if response.status_code == 409)
        assert refused.json()["error"]["code"] == "comparison_running"
        join(comparison_id)
        done = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    assert done["state"] == "completed", done["failures"]
    assert len(executions.calls) == 2 and len({call[2] for call in executions.calls}) == 2  # each missing cell once


def test_a_leaving_holder_writes_nothing_over_the_next_claim(keys, offline, monkeypatch):
    """Task 99: the final state ends the lease. A thread still cleaning up after it does not keep the comparison
    busy, and a holder that lost its lease (here the one leaving, once another claim exists) records nothing more."""
    settings = keys
    client, _, llm = offline()
    headers = login(client)
    executions = Executions(monkeypatch, fail_at=2, llm=llm)
    leaving, go = threading.Event(), threading.Event()
    real_rmtree = comparisons.shutil.rmtree
    first_name: list[str] = []

    def rmtree(path, *args, **kwargs):  # the final state is recorded; the first thread has not left yet
        if threading.current_thread().name.startswith("comparison-") and not first_name:
            first_name.append(threading.current_thread().name)
            leaving.set()
            go.wait(timeout=30)
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(comparisons.shutil, "rmtree", rmtree)
    comparison_id = create(client, headers)
    first = next(t for t in threading.enumerate() if t.name == f"comparison-{comparison_id}")
    try:
        assert leaving.wait(timeout=60)
        old_holder = lease(settings, comparison_id)[0]
        assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "partial"
        executions.calls.clear()
        executions.fail_at = None
        retried = client.post(f"/v1/comparisons/{comparison_id}/resume?retry_failed=true", headers=headers)
        assert retried.status_code == 202, retried.json()
        new_holder = lease(settings, comparison_id)[0]
        assert new_holder and new_holder != old_holder
        again = client.post(f"/v1/comparisons/{comparison_id}/resume?retry_failed=true", headers=headers)
        assert again.status_code == 409 and again.json()["error"]["code"] == "comparison_running"
        conn = comparisons.connect(settings.db_path)
        try:  # the old holder is fenced out: its writes match no row
            assert comparisons._save(conn, comparison_id, old_holder, cells=[], failures=[], state="failed") is False
        finally:
            conn.close()
    finally:
        go.set()
        first.join(timeout=60)
    join(comparison_id)
    done = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    assert done["state"] == "completed", done["failures"]
    assert len(executions.calls) == 1  # the failed cell ran again once


# --- Task 84 review, round 1: P3-1, P3-2, P3-3 ------------------------------------------------------------------------


def comparison_cells(settings, comparison_id: str) -> list[dict]:
    conn = sqlite3.connect(settings.db_path)
    try:
        row = conn.execute("SELECT cells FROM comparisons WHERE comparison_id=?", (comparison_id,)).fetchone()
        return json.loads(row[0])
    finally:
        conn.close()


def save_cells(settings, comparison_id: str, cells: list[dict]) -> None:
    conn = sqlite3.connect(settings.db_path)
    try:
        conn.execute("UPDATE comparisons SET cells=? WHERE comparison_id=?", (json.dumps(cells), comparison_id))
        conn.commit()
    finally:
        conn.close()


def demo_count(settings) -> int:
    conn = sqlite3.connect(settings.db_path)
    try:
        return conn.execute("SELECT SUM(message_count) FROM api_sessions WHERE principal_id LIKE 'demo%'").fetchone()[0]
    finally:
        conn.close()


def test_resume_recounts_given_back_cells_and_never_gives_one_back_twice(keys, offline, monkeypatch):
    settings = keys
    client, _, llm = offline()
    headers = login(client)
    executions = Executions(monkeypatch, fail_at=2, llm=llm)
    comparison_id = create(client, headers)
    join(comparison_id)
    assert demo_count(settings) == 3  # four counted at the start; the cell that failed before any call given back
    cells = comparison_cells(settings, comparison_id)
    failed = next(i for i, cell in enumerate(cells) if cell["status"] == "failed")
    assert cells[failed]["demo_refunded"] is True
    # The last cell becomes one the process never reached (already counted, never given back).
    keep = ("scenario_id", "profile_id", "profile_version", "repetition", "source", "reused_request_id")
    cells[-1] = {key: cells[-1][key] for key in (*keep, "estimated_cost_usd")} | {"status": "pending"}
    save_cells(settings, comparison_id, cells)

    executions.fail_at = None
    resumed = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
    assert resumed.status_code == 202 and resumed.json()["resumed_cells"] == 1
    join(comparison_id)
    assert demo_count(settings) == 3  # the failed cell, given back before, is not given back again

    retried = client.post(f"/v1/comparisons/{comparison_id}/resume?retry_failed=true", headers=headers)
    assert retried.status_code == 202 and retried.json()["resumed_cells"] == 1
    join(comparison_id)
    assert demo_count(settings) == 4  # the given-back cell is counted again before it runs, and it made a paid call
    assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "completed"


def test_a_failed_recorded_cell_runs_again_only_with_retry_failed(keys, offline, monkeypatch):
    settings = keys
    client, _, llm = offline()
    headers = login(client)
    executions = Executions(monkeypatch, fail_at=2, llm=llm)
    comparison_id = create(client, headers)
    join(comparison_id)
    cells = comparison_cells(settings, comparison_id)
    failed = next(i for i, cell in enumerate(cells) if cell["status"] == "failed")
    recorded = next(cell["request_id"] for cell in cells if cell["status"] == "completed")
    keep = ("scenario_id", "profile_id", "profile_version", "repetition", "status")
    cells[failed] = {key: cells[failed][key] for key in keep} | {
        "source": "recorded",
        "reused_request_id": recorded,
        "estimated_cost_usd": 0.0,
        "error": "recorded_run_missing",
    }
    save_cells(settings, comparison_id, cells)

    nothing = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
    assert nothing.status_code == 409 and nothing.json()["error"]["code"] == "nothing_to_resume"
    executions.calls.clear()
    retried = client.post(f"/v1/comparisons/{comparison_id}/resume?retry_failed=true", headers=headers)
    assert retried.status_code == 202 and retried.json()["resumed_cells"] == 1
    join(comparison_id)
    done = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    assert done["state"] == "completed", done["failures"]
    assert done["cells"][failed]["request_id"] == recorded and executions.calls == []  # reused, no new execution


def test_marking_interrupted_never_overwrites_a_final_state(keys, offline):
    settings = keys
    client, _, _ = offline()
    conn = comparisons.connect(settings.db_path)
    try:
        conn.execute(
            "INSERT INTO comparisons (comparison_id,principal_id,state,config,cells,failures,estimate,cost_usd,"
            "created_at,updated_at) VALUES ('pcmp_final0000000000000','demo:default','completed','{}',"
            "'[{\"status\": \"completed\", \"in_flight_request_id\": \"req_x\"}]','[]','{}',0.5,'t','t')"
        )
        row = conn.execute("SELECT * FROM comparisons WHERE comparison_id='pcmp_final0000000000000'").fetchone()
        assert comparisons._mark_interrupted(conn, client.app.state, row) is False  # a stale `running` view
        after = conn.execute("SELECT * FROM comparisons WHERE comparison_id='pcmp_final0000000000000'").fetchone()
        assert tuple(after) == tuple(row)
    finally:
        conn.close()


def test_resume_route_declares_its_error_responses(keys, offline):
    client, _, _ = offline()
    responses = client.app.openapi()["paths"]["/v1/comparisons/{comparison_id}/resume"]["post"]["responses"]
    assert {"202", "404", "409", "422", "429"} <= set(responses)
    for status in ("404", "409", "422", "429"):
        assert responses[status]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorBody")


def test_a_stale_lease_check_never_marks_a_live_comparison_interrupted(keys, offline, monkeypatch):
    client, _, _ = offline()
    headers = login(client)
    release = threading.Event()
    real = v1.execute_run

    def blocked(*args, **kwargs):
        release.wait(timeout=30)
        return real(*args, **kwargs)

    monkeypatch.setattr(v1, "execute_run", blocked)
    comparison_id = create(client, headers)
    real_alive, seen = comparisons._lease_alive, []

    def stale_outside_the_transaction(row):  # the check made on the row read before the write transaction says
        seen.append(None)  # "expired" (an old read); the transaction reads the row again and asks again
        return False if len(seen) % 2 else real_alive(row)

    try:
        monkeypatch.setattr(comparisons, "_lease_alive", stale_outside_the_transaction)
        assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "running"
        seen.clear()
        busy = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert busy.status_code == 409 and busy.json()["error"]["code"] == "comparison_running"
        monkeypatch.setattr(comparisons, "_lease_alive", real_alive)
        with TestClient(offline()[0].app):
            assert db_state(keys, comparison_id) == "running"
    finally:
        release.set()
        join(comparison_id)
    assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "completed"


# --- Task 99: the lease -----------------------------------------------------------------------------------------------


def test_the_lease_is_recorded_renewed_and_left_after_the_final_state(keys, offline, monkeypatch):
    """The lease thread, not the run's own writes, keeps a long cell alive: with the cell blocked after its last
    write, the heartbeat keeps changing and a read made after more than LEASE_SECONDS still sees `running`."""
    settings = keys
    monkeypatch.setattr(comparisons, "HEARTBEAT_SECONDS", 0.05)
    monkeypatch.setattr(comparisons, "LEASE_SECONDS", 0.4)
    client, _, _ = offline()
    headers = login(client)
    entered, release = threading.Event(), threading.Event()
    real = v1.execute_run

    def blocked(*args, **kwargs):  # the run wrote its progress and is now inside the cell
        entered.set()
        release.wait(timeout=30)
        return real(*args, **kwargs)

    monkeypatch.setattr(v1, "execute_run", blocked)
    comparison_id = create(client, headers)
    try:
        assert entered.wait(timeout=30)
        holder, last_save = lease(settings, comparison_id)
        host, pid, token = holder.rsplit(":", 2)
        assert int(pid) == os.getpid() and len(token) == 8 and host
        beats, started = set(), time.monotonic()
        while time.monotonic() - started < 3 * comparisons.LEASE_SECONDS:
            beats.add(lease(settings, comparison_id)[1])
            time.sleep(0.02)
        assert len(beats - {last_save}) >= 3  # renewed by the lease thread while the cell was blocked
        # More than LEASE_SECONDS after the last write of the run, a read does not take it for an orphan.
        assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "running"
        assert db_state(settings, comparison_id) == "running" and lease(settings, comparison_id)[0] == holder
    finally:
        release.set()
        join(comparison_id)
    assert db_state(settings, comparison_id) == "completed"
    assert not [t for t in threading.enumerate() if t.name == f"comparison-lease-{comparison_id}"]


def test_an_expired_lease_is_interrupted_on_read_and_a_fresh_one_is_not(keys, offline, monkeypatch):
    settings = keys
    client, _, _ = offline()
    executions = Executions(monkeypatch, kill_at=2)
    headers = login(client)
    comparison_id = create(client, headers)
    join(comparison_id)
    assert executions.killed and db_state(settings, comparison_id) == "running"
    # The heartbeat is still fresh: the holder may be alive in another worker.
    assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "running"
    busy = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
    assert busy.status_code == 409 and busy.json()["error"]["code"] == "comparison_running"
    monkeypatch.setattr(comparisons, "LEASE_SECONDS", 0.0)  # now older than the lease
    assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "interrupted"


def test_a_holder_that_lost_its_lease_calls_no_model_and_records_nothing(keys, offline, monkeypatch):
    """A worker that stalled for longer than the lease finds, at its next write, that the comparison was interrupted
    (and maybe claimed by another worker): it stops before the next call and writes nothing over it."""
    settings = keys
    client, _, llm = offline()
    headers = login(client)
    executions = Executions(monkeypatch, llm=llm)
    real_execute = executions.execute_run

    def stall_then_lose(app_state, conn, **kwargs):  # during the first cell another worker interrupts it
        result = real_execute(app_state, conn, **kwargs)
        if len(executions.calls) == 1:
            other = sqlite3.connect(settings.db_path)
            other.execute("UPDATE comparisons SET state='interrupted' WHERE state='running'")
            other.commit()
            other.close()
        return result

    monkeypatch.setattr(v1, "execute_run", stall_then_lose)
    comparison_id = create(client, headers)
    join(comparison_id)
    assert len(executions.calls) == 1  # no second cell after the lease was lost
    assert db_state(settings, comparison_id) == "interrupted"
    cells = comparison_cells(settings, comparison_id)
    assert [cell["status"] for cell in cells] == ["pending"] * 4  # the lost holder recorded no result


def test_a_paused_holder_cannot_reserve_after_an_empty_cell_is_claimed(keys, offline, monkeypatch):
    old_client, _, old_llm = offline()
    new_client, _, _ = offline()
    old_headers, new_headers = login(old_client), login(new_client)
    saved, release = threading.Event(), threading.Event()
    original_save = comparisons._save
    paused: list[tuple[threading.Thread, str]] = []

    def pause_after_in_flight_save(conn, comparison_id, holder, **kwargs):
        result = original_save(conn, comparison_id, holder, **kwargs)
        if result and not paused:
            for cell in kwargs["cells"]:
                if request_id := cell.get("in_flight_request_id"):
                    paused.append((threading.current_thread(), request_id))
                    saved.set()
                    assert release.wait(timeout=60)
                    break
        return result

    monkeypatch.setattr(comparisons, "HEARTBEAT_SECONDS", 60)
    monkeypatch.setattr(comparisons, "_save", pause_after_in_flight_save)
    comparison_id = create(old_client, old_headers)
    path = f"/v1/comparisons/{comparison_id}"
    try:
        assert saved.wait(timeout=20)
        old_thread, old_request = paused[0]
        old_holder = lease(keys, comparison_id)[0]
        assert ledger(keys) == {}
        expire_lease(keys, comparison_id)
        interrupted = new_client.get(path, headers=new_headers).json()
        assert interrupted["state"] == "interrupted"
        assert interrupted["cells"][0]["status"] == "pending"
        resumed = new_client.post(f"{path}/resume", headers=new_headers)
        assert resumed.status_code == 202 and resumed.json()["resumed_cells"] == 4
        assert lease(keys, comparison_id)[0] != old_holder
    finally:
        release.set()
        join(comparison_id)

    assert not old_thread.is_alive()
    done = new_client.get(path, headers=new_headers).json()
    assert done["state"] == "completed", done["failures"]
    assert old_llm.calls == []
    assert old_request not in ledger(keys)
    assert set(ledger(keys)) == {cell["request_id"] for cell in done["cells"]}


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
def test_comparison_query_embedding_reserves_under_lease_and_releases_before_provider(keys, offline, monkeypatch, mode):
    monkeypatch.setattr(comparisons, "HEARTBEAT_SECONDS", 60)
    keys.rerank = "off"
    keys.retrieval_mode = mode
    client, orchestrator, _ = offline()
    orchestrator.knowledge_base.capture_active()
    hash_embedder = orchestrator.index.embedder
    real_reserve = orchestrator.budget.reserve
    reservations, calls = [], []

    def reserve(**kwargs):
        if kwargs["agent"] == "embeddings":
            conn = sqlite3.connect(keys.db_path, timeout=0)
            try:
                with pytest.raises(sqlite3.OperationalError, match="database is locked"):
                    conn.execute("BEGIN IMMEDIATE")
            finally:
                conn.close()
            reservations.append(kwargs["request_id"])
        return real_reserve(**kwargs)

    def embed(*, model, input):
        conn = sqlite3.connect(keys.db_path, timeout=0)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.rollback()
        finally:
            conn.close()
        calls.append(model)
        return SimpleNamespace(
            data=[SimpleNamespace(index=i, embedding=vector) for i, vector in enumerate(hash_embedder.embed(input))],
            usage=SimpleNamespace(total_tokens=30),
        )

    monkeypatch.setattr(orchestrator.budget, "reserve", reserve)
    orchestrator.index.embedder = OpenAIEmbedder(
        SimpleNamespace(embeddings=SimpleNamespace(create=embed)),
        "text-embedding-3-small",
        dim=hash_embedder.dim,
        budget=orchestrator.budget,
    )
    headers = login(client)
    comparison_id = create(client, headers, selection() | {"scenario_ids": ["SC-KNOWLEDGE-PRODUCTS"]})
    join(comparison_id)
    done = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    assert done["state"] == "completed", done["failures"]
    ids = [cell["request_id"] for cell in done["cells"]]
    assert reservations == ids
    assert calls == ["text-embedding-3-small"] * len(ids)
    conn = sqlite3.connect(keys.runtime_path / "budget.sqlite3")
    try:
        rows = conn.execute(
            "SELECT request_id, actual_usd, status FROM ledger WHERE agent='embeddings' ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    assert [row[0] for row in rows] == ids and all(row[2] == "settled" for row in rows)
    assert done["cost_usd"] == pytest.approx(sum(row[1] for row in rows))


def test_interrupted_budget_denied_snapshot_keeps_failed_cell_and_cost_until_explicit_retry(keys, offline, monkeypatch):
    client, orchestrator, llm = offline()
    llm.model = "gpt-6-luna"  # priced metering with the scripted provider
    real_reserve = orchestrator.budget.reserve

    def refuse_after_router(**kwargs):
        if kwargs["agent"] != "router":
            raise BudgetExceeded("installation", kwargs["amount"], 0.0)
        return real_reserve(**kwargs)

    with monkeypatch.context() as setup:
        setup.setattr(orchestrator.budget, "reserve", refuse_after_router)
        executions = Executions(setup, kill_at=1)
        comparison_id = create(client, login(client))
        join(comparison_id)
        assert executions.killed and db_state(keys, comparison_id) == "running"
    expire_lease(keys, comparison_id)
    request_id = executions.calls[0][2]
    attempt = comparisons._ledger_attempt(orchestrator.budget, request_id)
    assert attempt is not None and attempt[1] > 0

    restarted, _, _ = offline()
    headers = login(restarted)
    path = f"/v1/comparisons/{comparison_id}"
    lost = restarted.get(path, headers=headers).json()
    assert lost["state"] == "interrupted"
    failed = lost["cells"][0]
    assert (failed["status"], failed["error"], failed["request_id"]) == ("failed", "budget_denied", request_id)
    assert {"code": "budget_denied", "request_id": request_id} in lost["failures"]
    assert lost["cost_usd"] == pytest.approx(attempt[1])
    assert restarted.get(path, headers=headers).json()["cost_usd"] == lost["cost_usd"]

    resumed = restarted.post(f"{path}/resume", headers=headers)
    assert resumed.status_code == 202 and resumed.json()["resumed_cells"] == 3
    join(comparison_id)
    partial = restarted.get(path, headers=headers).json()
    assert partial["state"] == "partial" and partial["cells"][0]["request_id"] == request_id
    assert partial["cost_usd"] == lost["cost_usd"]

    retried = restarted.post(f"{path}/resume?retry_failed=true", headers=headers)
    assert retried.status_code == 202 and retried.json()["resumed_cells"] == 1
    join(comparison_id)
    done = restarted.get(path, headers=headers).json()
    assert done["state"] == "completed", done["failures"]
    assert done["cells"][0]["previous_request_ids"] == [request_id]
    assert done["cells"][0]["request_id"] != request_id
    assert done["cost_usd"] == lost["cost_usd"]


def test_a_run_that_lost_its_lease_before_its_final_state_gives_nothing_back(keys, offline, monkeypatch):
    """The demo actions are given back in the transaction of the final state: when the lease was lost after the last
    cell, the final write matches no row and the refund is rolled back with it (the next holder decides)."""
    settings = keys
    client, _, llm = offline()
    headers = login(client)
    Executions(monkeypatch, fail_at=2, llm=llm)  # the failed cell made no call: it would be given back
    real_finish = comparisons._finish

    def lose_then_finish(app, conn, comparison_id, *args):  # another worker interrupts it just before the end
        other = sqlite3.connect(settings.db_path)
        try:
            other.execute("UPDATE comparisons SET state='interrupted' WHERE comparison_id=?", (comparison_id,))
            other.commit()
        finally:
            other.close()
        return real_finish(app, conn, comparison_id, *args)

    monkeypatch.setattr(comparisons, "_finish", lose_then_finish)
    comparison_id = create(client, headers)
    join(comparison_id)
    assert demo_count(settings) == 4  # four counted at the start, nothing given back
    assert db_state(settings, comparison_id) == "interrupted"
    assert not any(cell.get("demo_refunded") for cell in comparison_cells(settings, comparison_id))


def test_resume_reads_the_row_again_inside_its_claim(keys, offline, monkeypatch):
    """A resume reads the row, then claims it in a write transaction. When another resume claims, runs and completes
    the comparison in between, the claim sees the row as it is now and runs nothing."""
    settings = keys
    comparison_id, _, restarted, _, llm = interrupted_comparison(settings, offline, monkeypatch)
    with TestClient(restarted.app) as client:
        headers = login(client)
        executions = Executions(monkeypatch, llm=llm)
        real_prompts, first = comparisons.prompt_versions, []

        def prompt_versions(path):  # called after the first read and before the claim's transaction
            if not first:
                first.append(None)  # the nested resume below goes through untouched
                first[0] = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
                join(comparison_id)
            return real_prompts(path)

        monkeypatch.setattr(comparisons, "prompt_versions", prompt_versions)
        late = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert first[0].status_code == 202, first[0].json()
        assert late.status_code == 409 and late.json()["error"]["code"] == "comparison_completed", late.json()
        done = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    assert done["state"] == "completed", done["failures"]
    assert len(executions.calls) == 2 and len({call[2] for call in executions.calls}) == 2  # each missing cell once


def test_two_starts_of_one_principal_never_both_run(keys, offline, monkeypatch):
    client, _, _ = offline()
    headers = login(client)
    release = threading.Event()
    real = v1.execute_run

    def blocked(*args, **kwargs):
        release.wait(timeout=30)
        return real(*args, **kwargs)

    monkeypatch.setattr(v1, "execute_run", blocked)
    first = create(client, headers)
    try:
        estimate = client.post("/v1/comparisons/estimate", headers=headers, json=selection()).json()
        second = client.post(
            "/v1/comparisons",
            headers=headers,
            json=selection()
            | {
                "confirmed": True,
                "max_cost_usd": estimate["estimated_cost_usd"],
                "expected_estimate_digest": estimate["estimate_digest"],
            },
        )
        assert second.status_code == 409 and second.json()["error"]["code"] == "comparison_running"
    finally:
        release.set()
        join(first)


# --- v0.13.0: unreadable traces, the reservation fence and a cost read late ------------------------------------------


def broken_trace(_request_id):
    raise sqlite3.OperationalError("synthetic trace store failure")


def test_unreadable_trace_after_a_completed_execution_fails_the_cell_and_keeps_its_cost(keys, offline, monkeypatch):
    client, orchestrator, _ = offline()
    headers = login(client)
    real_execute, real_trace = v1.execute_run, orchestrator.trace
    calls, broken, extra = [], [], 0.003

    def execute(*args, **kwargs):
        calls.append(kwargs["request_id"])
        result = real_execute(*args, **kwargs)
        with kwargs["reservation_fence"](calls[-1]):
            reservation = orchestrator.budget.reserve(
                request_id=calls[-1], agent="router", model="synthetic", amount=extra
            )
        orchestrator.budget.settle(reservation, extra)
        if len(calls) == 1:  # the trace store fails after the run read its own trace
            broken.append(None)
        return result

    monkeypatch.setattr(v1, "execute_run", execute)
    monkeypatch.setattr(orchestrator, "trace", lambda rid: broken_trace(rid) if broken else real_trace(rid))
    comparison_id = create(client, headers, selection() | {"scenario_ids": ["SC-RECEIVABLES"]})
    join(comparison_id)
    path = f"/v1/comparisons/{comparison_id}"
    result = client.get(path, headers=headers).json()
    first, second = result["cells"]
    assert len(calls) == 1
    assert (first["status"], first["error"], first["request_id"]) == ("failed", "trace_unavailable", calls[0])
    assert "checks" not in first
    assert (second["status"], second["error"]) == ("skipped", "trace_unavailable")
    assert {"code": "trace_unavailable", "request_id": calls[0]} in result["failures"]
    assert not any(failure["code"] == "comparison_failed" for failure in result["failures"])
    assert result["state"] == "failed"
    paid = comparisons._ledger_attempt(orchestrator.budget, calls[0])[1]
    assert paid >= extra
    assert result["cost_usd"] == pytest.approx(max(float(first["cost_usd"] or 0), paid))

    broken.clear()
    resumed = client.post(f"{path}/resume", headers=headers)
    assert resumed.status_code == 202 and resumed.json()["resumed_cells"] == 1  # the paid cell needs retry_failed
    join(comparison_id)
    partial = client.get(path, headers=headers).json()
    assert partial["state"] == "partial" and len(calls) == 2
    kept = partial["cells"][0]
    assert kept == first | {"model_calls": kept["model_calls"]}  # only its call count, unreadable before, recorded
    assert partial["cells"][1]["status"] == "completed"


@pytest.mark.parametrize("trace_failure", ["unreadable", "missing"])
def test_an_orphan_whose_trace_cannot_be_read_is_interrupted_with_its_cost(keys, offline, monkeypatch, trace_failure):
    comparison_id, request_id, client, orchestrator, llm = interrupted_comparison(keys, offline, monkeypatch)
    conn = sqlite3.connect(keys.db_path)
    try:
        before = conn.execute("SELECT cost_usd FROM comparisons WHERE comparison_id=?", (comparison_id,)).fetchone()
    finally:
        conn.close()
    before = float(before[0] or 0)
    paid = 0.004  # the scripted model is unpriced: a settled call gives the attempt a known cost
    reservation = orchestrator.budget.reserve(request_id=request_id, agent="router", model="synthetic", amount=paid)
    orchestrator.budget.settle(reservation, paid)
    assert comparisons._ledger_attempt(orchestrator.budget, request_id)[1] == pytest.approx(paid)
    real_trace = orchestrator.trace
    monkeypatch.setattr(orchestrator, "trace", broken_trace if trace_failure == "unreadable" else lambda _: None)
    headers = login(client)
    path = f"/v1/comparisons/{comparison_id}"
    response = client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    lost = response.json()
    assert lost["state"] == "interrupted"
    cell = lost["cells"][1]
    assert (cell["status"], cell["error"], cell["request_id"]) == ("failed", "trace_unavailable", request_id)
    assert float(cell["cost_usd"] or 0) < paid
    assert {"code": "trace_unavailable", "request_id": request_id} in lost["failures"]
    assert lost["cost_usd"] == pytest.approx(before + paid)  # counted, exactly once
    assert client.get(path, headers=headers).json()["cost_usd"] == lost["cost_usd"]

    monkeypatch.setattr(orchestrator, "trace", real_trace)
    executions = Executions(monkeypatch, llm=llm)
    resumed = client.post(f"{path}/resume", headers=headers)
    assert resumed.status_code == 202 and resumed.json()["resumed_cells"] == 2
    join(comparison_id)
    done = client.get(path, headers=headers).json()
    assert done["state"] == "partial" and len(executions.calls) == 2
    assert done["cells"][1] == cell
    new_cost = sum(float(c["cost_usd"] or 0) for c in done["cells"][2:])
    assert done["cost_usd"] == pytest.approx(lost["cost_usd"] + new_cost)  # not counted again by the resume


def test_a_budget_refusal_with_no_saved_trace_never_ends_completed(keys, offline, monkeypatch):
    """A failed trace save leaves no trace (the reply goes on): the cell cannot be shown free of a budget refusal, so
    it fails as `trace_unavailable` instead of `completed`, and its ledger cost is counted."""
    client, orchestrator, llm = offline()
    llm.model = "gpt-6-luna"  # priced metering with the scripted provider
    real_reserve = orchestrator.budget.reserve

    def refuse_after_router(**kwargs):
        if kwargs["agent"] != "router":
            raise BudgetExceeded("installation", kwargs["amount"], 0.0)
        return real_reserve(**kwargs)

    def failed_save(*args, **kwargs):
        raise sqlite3.OperationalError("synthetic trace store failure")

    monkeypatch.setattr(orchestrator.budget, "reserve", refuse_after_router)
    monkeypatch.setattr(orchestrator.traces, "save", failed_save)
    headers = login(client)
    comparison_id = create(client, headers, selection() | {"scenario_ids": ["SC-RECEIVABLES"]})
    join(comparison_id)
    result = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    first, second = result["cells"]
    assert (first["status"], first["error"]) == ("failed", "trace_unavailable")
    assert (second["status"], second["error"]) == ("skipped", "trace_unavailable")
    assert {"code": "trace_unavailable", "request_id": first["request_id"]} in result["failures"]
    assert result["state"] == "failed"
    paid = comparisons._ledger_attempt(orchestrator.budget, first["request_id"])[1]
    assert paid > 0 and result["cost_usd"] == pytest.approx(paid)


def test_recorded_cells_with_an_unreadable_trace_fail_alone_and_reuse_on_retry(keys, offline, monkeypatch):
    client, orchestrator, llm = offline()
    headers = login(client)
    recorded = create(client, headers)
    join(recorded)
    assert client.get(f"/v1/comparisons/{recorded}", headers=headers).json()["state"] == "completed"
    real_trace = orchestrator.trace

    def broken_while_running(request_id):  # the estimate saw the traces; they fail while the comparison runs
        running = threading.current_thread().name.startswith("comparison-")
        return broken_trace(request_id) if running else real_trace(request_id)

    monkeypatch.setattr(orchestrator, "trace", broken_while_running)
    executions = Executions(monkeypatch, llm=llm)
    comparison_id = create(client, headers, selection() | {"reuse_recorded": True})
    join(comparison_id)
    path = f"/v1/comparisons/{comparison_id}"
    result = client.get(path, headers=headers).json()
    assert executions.calls == []
    assert all(cell["source"] == "recorded" for cell in result["cells"])
    assert [(cell["status"], cell.get("error")) for cell in result["cells"]] == [("failed", "trace_unavailable")] * 4
    assert not any("checks" in cell for cell in result["cells"])
    assert not any(failure["code"] == "comparison_failed" for failure in result["failures"])
    assert result["state"] == "failed" and result["aggregates"]["profiles"][0]["sample_size"] == 0

    monkeypatch.setattr(orchestrator, "trace", real_trace)
    retried = client.post(f"{path}/resume?retry_failed=true", headers=headers)
    assert retried.status_code == 202 and retried.json()["resumed_cells"] == 4
    join(comparison_id)
    done = client.get(path, headers=headers).json()
    assert done["state"] == "completed", done["failures"]
    assert executions.calls == [] and all(cell["checks"]["total"] > 0 for cell in done["cells"])


def test_a_refused_reservation_aborts_the_run_instead_of_being_absorbed_by_a_node(keys, offline, monkeypatch):
    """The fence refusal crosses every graph node (they recover from ordinary exceptions): the run stops at the first
    reservation, with no further reservation, no model call and nothing recorded."""
    client, _, llm = offline()
    headers = login(client)
    fenced, outcomes = [], []
    real_execute = v1.execute_run

    @contextmanager
    def refuse(self, request_id):
        fenced.append(request_id)
        raise comparisons._LeaseLost
        yield  # pragma: no cover

    def execute(*args, **kwargs):
        try:
            result = real_execute(*args, **kwargs)
        except BaseException as exc:
            outcomes.append(type(exc))
            raise
        outcomes.append("returned")
        return result

    monkeypatch.setattr(comparisons._Lease, "reservation", refuse)
    monkeypatch.setattr(v1, "execute_run", execute)
    comparison_id = create(client, headers)
    join(comparison_id)
    assert outcomes == [comparisons._LeaseLost]
    assert len(fenced) == 1
    assert llm.calls == [] and ledger(keys) == {}
    assert [cell["status"] for cell in comparison_cells(keys, comparison_id)] == ["pending"] * 4


def test_all_cells_completed_with_the_last_cost_unknown_resume_closes_without_running(keys, offline, monkeypatch):
    client, orchestrator, llm = offline()
    headers = login(client)
    real_execute, real_attempt = v1.execute_run, comparisons._ledger_attempt
    calls, readable, extra = [], [False], 0.002

    def execute(*args, **kwargs):
        calls.append(kwargs["request_id"])
        result = real_execute(*args, **kwargs)
        with kwargs["reservation_fence"](calls[-1]):
            reservation = orchestrator.budget.reserve(
                request_id=calls[-1], agent="router", model="synthetic", amount=extra
            )
        orchestrator.budget.settle(reservation, extra)
        return result

    def attempt(budget, request_id):
        last = len(calls) == 4 and request_id == calls[-1]
        return None if last and not readable[0] else real_attempt(budget, request_id)

    monkeypatch.setattr(v1, "execute_run", execute)
    monkeypatch.setattr(comparisons, "_ledger_attempt", attempt)
    comparison_id = create(client, headers)
    join(comparison_id)
    path = f"/v1/comparisons/{comparison_id}"
    first = client.get(path, headers=headers).json()
    assert len(calls) == 4 and all(cell["status"] == "completed" for cell in first["cells"])
    assert first["state"] == "partial"
    assert any(f["code"] == "execution_cost_unknown" and f["request_id"] == calls[3] for f in first["failures"])
    for suffix in ("", "?retry_failed=true"):
        refused = client.post(f"{path}/resume{suffix}", headers=headers)
        assert refused.status_code == 409 and refused.json()["error"]["code"] == "execution_cost_unknown"
    assert db_state(keys, comparison_id) == "partial"

    readable[0] = True
    model_calls = len(llm.calls)
    resumed = client.post(f"{path}/resume", headers=headers)
    assert resumed.status_code == 202
    assert resumed.json() == {"comparison_id": comparison_id, "state": "running", "resumed_cells": 0}
    join(comparison_id)
    done = client.get(path, headers=headers).json()
    assert done["state"] == "completed", done["failures"]
    assert len(calls) == 4 and len(llm.calls) == model_calls  # no new execution
    assert done["cells"] == first["cells"]
    assert any(f["code"] == "execution_cost_recovered" and f["request_id"] == calls[3] for f in done["failures"])
    in_ledger = sum(real_attempt(orchestrator.budget, request_id)[1] for request_id in calls)
    assert in_ledger == pytest.approx(4 * extra)
    assert done["cost_usd"] == pytest.approx(in_ledger)


SINGLE = selection() | {"scenario_ids": ["SC-RECEIVABLES"]}  # reuse_recorded false
DEFAULT_REUSE = {key: value for key, value in SINGLE.items() if key != "reuse_recorded"}  # reuse is the default


def refused_comparison(client, orchestrator, llm, monkeypatch, headers) -> str:
    """Comparison over SC-RECEIVABLES whose first cell is refused by the budget after the router; returns that run."""
    llm.model = "gpt-6-luna"  # priced metering with the scripted provider
    real_reserve = orchestrator.budget.reserve

    def refuse_after_router(**kwargs):
        if kwargs["agent"] != "router":
            raise BudgetExceeded("installation", kwargs["amount"], 0.0)
        return real_reserve(**kwargs)

    with monkeypatch.context() as setup:
        setup.setattr(orchestrator.budget, "reserve", refuse_after_router)
        denied_id = create(client, headers, SINGLE)
        join(denied_id)
    denied = client.get(f"/v1/comparisons/{denied_id}", headers=headers).json()
    assert denied["state"] == "failed"
    assert [(c["status"], c.get("error")) for c in denied["cells"]] == [
        ("failed", "budget_denied"),
        ("skipped", "budget_denied"),
    ]
    return denied["cells"][0]["request_id"]


def offered(client, headers, chosen) -> list[tuple[str, str | None]]:
    estimate = client.post("/v1/comparisons/estimate", headers=headers, json=chosen).json()
    return [(cell["source"], cell["reused_request_id"]) for cell in estimate["cells"]]


def test_only_a_readable_trace_without_a_budget_refusal_is_offered_for_reuse():
    def unreadable(_):
        raise sqlite3.OperationalError("synthetic trace store failure")

    assert comparisons._verified_run(lambda _: {"errors": [], "steps": []}, "req") is True
    assert comparisons._verified_run(lambda _: None, "req") is False
    assert comparisons._verified_run(unreadable, "req") is False
    refused = {"errors": [], "steps": [{"detail": {"error": "Budget exceeded (installation)"}}]}
    assert comparisons._verified_run(lambda _: refused, "req") is False


def test_the_estimate_skips_a_refused_run_and_offers_a_valid_one_or_new(keys, offline, monkeypatch):
    client, orchestrator, llm = offline()
    headers = login(client)
    refused_run = refused_comparison(client, orchestrator, llm, monkeypatch, headers)
    assert offered(client, headers, DEFAULT_REUSE) == [("new", None), ("new", None)]  # no valid run yet

    fresh = []  # two valid comparisons; the estimate offers the runs of the older one
    for _ in range(2):
        fresh_id = create(client, headers, SINGLE)
        join(fresh_id)
        fresh.append(client.get(f"/v1/comparisons/{fresh_id}", headers=headers).json())
        assert fresh[-1]["state"] == "completed", fresh[-1]["failures"]
    valid = [cell["request_id"] for cell in fresh[0]["cells"]]
    real_trace, reads = orchestrator.trace, []
    monkeypatch.setattr(orchestrator, "trace", lambda request_id: reads.append(request_id) or real_trace(request_id))
    assert offered(client, headers, DEFAULT_REUSE) == [("recorded", request_id) for request_id in valid]
    # Reads stop at the first valid run of each profile: the refused run and the older valid one for `reference`,
    # the older valid one for `hybrid`; the newer comparison's runs are never read.
    assert reads == [refused_run, valid[0], valid[1]]
    monkeypatch.setattr(orchestrator, "trace", real_trace)

    comparison_id = create(client, headers, DEFAULT_REUSE)
    join(comparison_id)
    done = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    assert done["state"] == "completed", done["failures"]
    assert [cell["request_id"] for cell in done["cells"]] == valid and refused_run not in valid


def test_a_recorded_run_refused_by_the_budget_is_never_reused_as_completed(keys, offline, monkeypatch):
    """Second barrier: a refused run offered anyway (an estimate made while its trace still looked clean) fails as
    `budget_denied` when the comparison reuses it."""
    client, orchestrator, llm = offline()
    headers = login(client)
    refused_run = refused_comparison(client, orchestrator, llm, monkeypatch, headers)
    monkeypatch.setattr(comparisons, "_verified_run", lambda *_: True)
    reuse = SINGLE | {"reuse_recorded": True}
    assert offered(client, headers, reuse) == [("recorded", refused_run), ("new", None)]
    comparison_id = create(client, headers, reuse)
    join(comparison_id)
    result = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
    recorded, new = result["cells"]
    assert (recorded["source"], recorded["request_id"]) == ("recorded", refused_run)
    assert (recorded["status"], recorded["error"]) == ("failed", "budget_denied")
    assert new["source"] == "new" and new["status"] == "completed"  # nothing stopped: the reuse made no paid call
    assert {"code": "budget_denied", "request_id": refused_run} in result["failures"]
    assert result["state"] == "partial"
    assert [item["sample_size"] for item in result["aggregates"]["profiles"]] == [0, 1]
