"""v0.10.0, task 84 (spec D3, CA-58): a profile comparison stopped by an API restart becomes `interrupted`, keeps the
cells it finished and resumes through the API running only the cells without a result.

Synthetic and offline only: scripted model, hashing embedder, in-memory Qdrant, temporary SQLite databases. The
restart is a new app (new orchestrator and scripted model) over the same runtime directory, started with its lifespan.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant import comparisons
from merchant_assistant.api import v1
from merchant_assistant.testing import key_token

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


def create(client, headers) -> str:
    estimate = client.post("/v1/comparisons/estimate", headers=headers, json=selection())
    assert estimate.status_code == 200, estimate.json()
    body = estimate.json()
    created = client.post(
        "/v1/comparisons",
        headers=headers,
        json=selection()
        | {
            "confirmed": True,
            "max_cost_usd": body["estimated_cost_usd"],
            "expected_estimate_digest": body["estimate_digest"],
        },
    )
    assert created.status_code == 202, created.json()
    return created.json()["comparison_id"]


def join(comparison_id: str) -> None:
    thread = comparisons._ACTIVE.get(comparison_id)
    if thread:
        thread.join(timeout=60)
        assert not thread.is_alive()


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
        if not self.killed:
            self.real_save(*args, **kwargs)


def interrupted_comparison(settings, offline, monkeypatch):
    """Runs a comparison whose process dies during the second new execution, then restarts the API."""
    client, _, _ = offline()
    executions = Executions(monkeypatch, kill_at=2)
    comparison_id = create(client, login(client))
    join(comparison_id)
    assert db_state(settings, comparison_id) == "running"  # nothing recorded the end: the process was gone
    killed_request_id = executions.calls[1][2]
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
    with TestClient(restarted.app) as client:  # the lifespan runs: no thread survived the old process
        assert db_state(settings, comparison_id) == "interrupted"
        assert [getattr(r, "event", None) for r in caplog.records if r.name == "merchant_assistant.comparisons"] == [
            {"comparison_id": comparison_id}
        ]
        headers = login(client)
        lost = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
        assert lost["state"] == "interrupted" and lost["failures"][-1]["code"] == "interrupted"
        first, *rest = lost["cells"]
        assert first["status"] == "completed" and first["request_id"]  # the finished cell is preserved
        assert [cell["status"] for cell in rest] == ["pending"] * 3 and not any("request_id" in c for c in rest)
        assert rest[0]["interrupted_attempts"] == [{"request_id": killed_id, "cost_usd": pytest.approx(attempt_cost)}]
        assert "in_flight_request_id" not in str(lost["cells"])
        assert lost["cost_usd"] == pytest.approx(cost_before[0] + attempt_cost)  # added once
        again = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()
        assert again["cost_usd"] == lost["cost_usd"] and again["cells"] == lost["cells"]  # never added twice
        before = ledger(settings)
        assert set(before) == {first["request_id"], killed_id}

        executions = Executions(monkeypatch, llm=llm)
        resumed = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert resumed.status_code == 202, resumed.json()
        assert resumed.json() == {"comparison_id": comparison_id, "state": "running", "resumed_cells": 3}
        join(comparison_id)
        done = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()

    assert done["state"] == "completed", done["failures"]
    cells = done["cells"]
    assert len(cells) == 4 and all(cell["status"] == "completed" for cell in cells)
    assert cells[0] == first | {"model_calls": cells[0]["model_calls"]}  # untouched, only its call count recorded
    assert [(c[0], c[1]) for c in executions.calls] == [(c["scenario_id"], c["profile_id"]) for c in rest]
    new_ids = [cell["request_id"] for cell in cells[1:]]
    assert [c[2] for c in executions.calls] == new_ids and len(set(new_ids)) == 3
    # Every call of the scripted model after the restart happened inside the three missing cells, and the finished
    # cell and the interrupted attempt have exactly the ledger rows they had before the resume.
    assert all(executions.model_calls) and len(llm.calls) == sum(executions.model_calls)
    after = ledger(settings)
    assert set(after) == set(before) | set(new_ids)
    assert {rid: after[rid] for rid in before} == before
    expected_cost = sum(float(cell["cost_usd"] or 0) for cell in cells) + attempt_cost  # + the interrupted attempt
    assert done["cost_usd"] == pytest.approx(expected_cost)
    assert cells[1]["interrupted_attempts"] == rest[0]["interrupted_attempts"]
    assert done["aggregates"]["profiles"][0]["sample_size"] == 2 and done["aggregates"]["profiles"][1]["sample_size"]


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
        with TestClient(offline()[0].app):  # another app starting in this process leaves the live run alone
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


def test_resume_reserves_only_what_is_missing_and_refuses_changed_fixed_factors(keys, offline, monkeypatch):
    settings = keys
    comparison_id, _, restarted, orchestrator, _ = interrupted_comparison(settings, offline, monkeypatch)
    with TestClient(restarted.app) as client:
        headers = login(client)
        per_cell = float(settings.max_request_cost_usd)
        # Three cells are missing: a budget that holds three of them is enough, even if it could not hold four.
        monkeypatch.setattr(orchestrator.budget, "remaining", lambda: 3 * per_cell - 1e-9)
        short = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert short.status_code == 429 and short.json()["error"]["code"] == "installation_budget_exceeded"
        monkeypatch.setattr(orchestrator.budget, "remaining", lambda: 3 * per_cell)
        monkeypatch.setattr(comparisons, "prompt_versions", lambda _: {"router": "999"})
        changed = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert changed.status_code == 409 and changed.json()["error"]["code"] == "fixed_factors_changed"
        assert db_state(settings, comparison_id) == "interrupted"  # refusals change nothing
        monkeypatch.undo()
        monkeypatch.setattr(orchestrator.budget, "remaining", lambda: 3 * per_cell)
        resumed = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert resumed.status_code == 202, resumed.json()
        join(comparison_id)
        assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "completed"


# --- Task 84 review, round 1: races around the thread registry (P2-1, P2-2) ------------------------------------------


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

    def during():  # the row is already `running`; the thread exists but has not started
        comparison_id = window.params[0]
        seen["read"] = client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"]
        seen["resume"] = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)

    window = Window(monkeypatch, "INSERT INTO comparisons", during)
    comparison_id = create(client, headers)
    join(comparison_id)
    assert window.ran and seen["read"] == "running"  # never `interrupted` while its thread is registered
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

        def during():  # the claim committed `running`; the resumed thread exists but has not started
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
    assert len(executions.calls) == 3  # each missing cell once


def test_two_concurrent_resumes_claim_the_comparison_once(keys, offline, monkeypatch):
    settings = keys
    comparison_id, _, restarted, orchestrator, llm = interrupted_comparison(settings, offline, monkeypatch)
    with TestClient(restarted.app) as client:
        headers = login(client)
        executions = Executions(monkeypatch, llm=llm)
        barrier, lock, calls = threading.Barrier(2, timeout=30), threading.Lock(), []
        real_remaining = orchestrator.budget.remaining

        def remaining():  # both requests read the same `interrupted` row, then both try to claim it
            with lock:
                calls.append(None)
                first_two = len(calls) <= 2
            if first_two:
                barrier.wait()
            return real_remaining()

        monkeypatch.setattr(orchestrator.budget, "remaining", remaining)
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
    assert len(executions.calls) == 3 and len({call[2] for call in executions.calls}) == 3  # each missing cell once


def test_a_leaving_thread_keeps_resume_refused_and_unregisters_only_itself(keys, offline, monkeypatch):
    client, _, llm = offline()
    headers = login(client)
    executions = Executions(monkeypatch, fail_at=2, llm=llm)
    leaving, go, hold = threading.Event(), threading.Event(), threading.Event()
    real_rmtree = comparisons.shutil.rmtree

    def rmtree(path, *args, **kwargs):  # the final state is recorded; the thread has not left the registry yet
        if threading.current_thread().name.startswith("comparison-") and not go.is_set():
            leaving.set()
            go.wait(timeout=30)
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(comparisons.shutil, "rmtree", rmtree)
    comparison_id = create(client, headers)
    first = comparisons._ACTIVE[comparison_id]
    other = threading.Thread(target=hold.wait, args=(30,), daemon=True)
    try:
        assert leaving.wait(timeout=60)
        assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "partial"
        busy = client.post(f"/v1/comparisons/{comparison_id}/resume?retry_failed=true", headers=headers)
        assert busy.status_code == 409 and busy.json()["error"]["code"] == "comparison_running"
        # Another thread registered under the same id meanwhile is never removed by the one that is leaving.
        other.start()
        with comparisons._ACTIVE_LOCK:
            comparisons._ACTIVE[comparison_id] = other
        go.set()
        first.join(timeout=60)
        assert not first.is_alive() and comparisons._ACTIVE.get(comparison_id) is other
    finally:
        go.set()
        hold.set()
        if other.ident:
            other.join(timeout=60)
        comparisons._release(comparison_id, other)

    executions.calls.clear()
    executions.fail_at = None
    retried = client.post(f"/v1/comparisons/{comparison_id}/resume?retry_failed=true", headers=headers)
    assert retried.status_code == 202, retried.json()
    assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] in ("running", "completed")
    again = client.post(f"/v1/comparisons/{comparison_id}/resume?retry_failed=true", headers=headers)
    assert again.status_code == 409
    join(comparison_id)
    assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "completed"
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
            "INSERT INTO comparisons VALUES ('pcmp_final0000000000000','demo:default','completed','{}',"
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


def test_a_stale_liveness_check_never_marks_a_registered_comparison_interrupted(keys, offline, monkeypatch):
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
        # The check made before the write transaction saw no thread (as one being registered right then would);
        # the transaction looks at the registry again before marking anything.
        monkeypatch.setattr(comparisons, "_alive", lambda _: False)
        assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "running"
        busy = client.post(f"/v1/comparisons/{comparison_id}/resume", headers=headers)
        assert busy.status_code == 409 and busy.json()["error"]["code"] == "comparison_running"
        with TestClient(offline()[0].app):
            assert db_state(keys, comparison_id) == "running"
    finally:
        release.set()
        join(comparison_id)
    assert client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()["state"] == "completed"
