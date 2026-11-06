"""v0.10.0, task 84 (spec D3, CA-58): a profile comparison stopped by an API restart becomes `interrupted`, keeps the
cells it finished and resumes through the API running only the cells without a result.

Synthetic and offline only: scripted model, hashing embedder, in-memory Qdrant, temporary SQLite databases. The
restart is a new app (new orchestrator and scripted model) over the same runtime directory, started with its lifespan.
"""

from __future__ import annotations

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
        assert rest[0]["interrupted_attempts"] == [{"request_id": killed_id, "cost_usd": 0.0}]
        assert "in_flight_request_id" not in str(lost["cells"])
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
    expected_cost = sum(float(cell["cost_usd"] or 0) for cell in cells) + 0.0  # + the interrupted attempt (0 here)
    assert done["cost_usd"] == pytest.approx(expected_cost)
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
