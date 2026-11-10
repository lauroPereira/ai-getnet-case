"""Small, traceable profile comparison (v0.6.0, RF-78).

Two or three published profiles x up to three catalog scenarios x up to two repetitions (at most 18 cells).
New executions run outside the HTTP request, in a thread of the API worker that started or resumed the comparison,
under a lease recorded in the database (v0.13.0): any worker reads, interrupts and resumes it. Domain effects
(conversations, cases, attempts, handoffs, audit) go to a temporary copy of the synthetic database, while traces and
run snapshots are stored normally and marked with purpose=comparison. One knowledge-base version is captured for the
whole run."""

from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import sqlite3
import tempfile
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from merchant_assistant import scenarios as scenario_catalog
from merchant_assistant.api.schemas import MessageResponse
from merchant_assistant.data.db import connect
from merchant_assistant.guardrails.input import check_input
from merchant_assistant.llm.prompts import prompt_versions
from merchant_assistant.profiles import digest, get_profile

MIN_PROFILES, MAX_PROFILES, MAX_SCENARIOS, MAX_REPETITIONS = 2, 3, 3, 2
MAX_CELLS = MAX_PROFILES * MAX_SCENARIOS * MAX_REPETITIONS
JUDGE_CRITERIA = ("answers_question", "clarity_and_tone", "honesty")

log = logging.getLogger("merchant_assistant.comparisons")

# Lease of a running comparison (v0.13.0, task 99; spec D4). The row records who runs it (`worker_id`: host, process
# and a token of that claim) and when it last said so (`heartbeat_at`). The run renews it every HEARTBEAT_SECONDS from
# a thread of its own; a `running` row whose heartbeat is older than LEASE_SECONDS lost its process, in this worker or
# in any other, and becomes `interrupted`. The holder must still own the lease to record progress or reserve budget.
# Recovery and reservation take the same database write lock, so a takeover cannot miss a reservation by the old
# holder and automatically retry its cell.
HEARTBEAT_SECONDS = 5.0
LEASE_SECONDS = 20.0


class ComparisonError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _stamp() -> str:
    """Heartbeat time, in milliseconds (a test lease can be shorter than a second)."""
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _new_holder() -> str:
    """Holder of one claim: the host and process that run it, plus a token, so two claims never share a lease."""
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def _lease_alive(row) -> bool:
    """The holder of the row renewed its lease less than LEASE_SECONDS ago."""
    if not row["worker_id"] or not row["heartbeat_at"]:
        return False
    try:
        beat = datetime.fromisoformat(row["heartbeat_at"])
    except ValueError:
        return False
    return (datetime.now(UTC) - beat).total_seconds() <= LEASE_SECONDS


class _LeaseLost(BaseException):
    """Abort the comparison thread even across graph nodes that recover from provider exceptions."""


class _Lease:
    """Renews the lease of one comparison while its run lasts, from its own thread and connection. `lost` is set when
    the row is no longer `running` under this holder: it was marked `interrupted` after the heartbeat expired, and
    maybe claimed again by another worker."""

    def __init__(self, db_path, comparison_id: str, holder: str) -> None:
        self.db_path, self.comparison_id, self.holder = db_path, comparison_id, holder
        self.lost, self._stop = threading.Event(), threading.Event()
        self._thread = threading.Thread(target=self._beat, name=f"comparison-lease-{comparison_id}", daemon=True)

    def start(self) -> _Lease:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread.ident is not None:
            self._thread.join(timeout=HEARTBEAT_SECONDS + 10)

    @contextmanager
    def reservation(self, request_id: str) -> Iterator[None]:
        """Exclude takeover until the ledger reservation commits, using a connection local to the caller."""
        conn = connect(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT state,worker_id,heartbeat_at,cells FROM comparisons WHERE comparison_id=?",
                (self.comparison_id,),
            ).fetchone()
            if (
                row is None
                or row["state"] != "running"
                or row["worker_id"] != self.holder
                or not _lease_alive(row)
                or not any(cell.get("in_flight_request_id") == request_id for cell in json.loads(row["cells"]))
            ):
                raise _LeaseLost
            yield
            conn.execute("COMMIT")
        finally:
            conn.close()  # also rolls back on refusal or an exception

    def _beat(self) -> None:
        try:
            conn = connect(self.db_path)
        except Exception:  # the run's own writes fail the same way; without beats the lease expires
            log.exception("comparison lease cannot open the database")
            return
        try:
            while not self._stop.wait(HEARTBEAT_SECONDS):
                try:
                    renewed = conn.execute(
                        "UPDATE comparisons SET heartbeat_at=? "
                        "WHERE comparison_id=? AND worker_id=? AND state='running'",
                        (_stamp(), self.comparison_id, self.holder),
                    ).rowcount
                except sqlite3.Error:  # busy or unreadable for a moment: the next beat tries again
                    continue
                if renewed != 1:
                    self.lost.set()
                    return
        finally:
            conn.close()


def _drop_lease(db_path, comparison_id: str, holder: str) -> None:
    """The thread of a claim could not start: its lease is expired now, so the next read marks it `interrupted`."""
    conn = connect(db_path)
    try:
        conn.execute(
            "UPDATE comparisons SET heartbeat_at=NULL WHERE comparison_id=? AND worker_id=? AND state='running'",
            (comparison_id, holder),
        )
    finally:
        conn.close()


def _execution_mode(orchestrator) -> str:
    return "simulated" if type(orchestrator.llm).__name__ == "ScriptedLLM" else "real"


def _profile_changes(profiles: list[dict]) -> list[dict]:
    changes = []
    for i, left in enumerate(profiles):
        for right in profiles[i + 1 :]:
            agents = sorted(
                name
                for name in left["agents"]
                if json.dumps(left["agents"][name], sort_keys=True)
                != json.dumps(right["agents"].get(name), sort_keys=True)
            )
            changes.append({"profiles": [left["profile_id"], right["profile_id"]], "changed_agents": agents})
    return changes


def _verified_run(trace_of, request_id: str) -> bool:
    """A recorded run is offered for reuse only when its trace can be read and shows no budget refusal."""
    try:
        trace = trace_of(request_id)
    except Exception:
        return False
    return trace is not None and not _budget_denied(trace)


def _compatible_runs(
    conn, principal_id: str, profile: dict, scenario: dict, context: dict, trace_of, limit: int
) -> list[str]:
    """The oldest `limit` recorded runs that match the comparison's fixed factors and passed `_verified_run`; the
    trace is read only for runs whose snapshot already matches."""
    rows = conn.execute(
        "SELECT request_id,snapshot FROM run_snapshots WHERE principal_id=? AND profile_id=? AND profile_version=? "
        "ORDER BY created_at, request_id",
        (principal_id, profile["profile_id"], profile["version"]),
    ).fetchall()
    found = []
    for row in rows:
        snapshot = json.loads(row["snapshot"])
        if (
            snapshot.get("scenario_id") == scenario["id"]
            and snapshot.get("message") == check_input(scenario["message"]).masked
            and snapshot.get("profile_digest") == profile["digest"]
            and snapshot.get("router_mechanism") == context["router_mechanism"]
            and snapshot.get("knowledge_base_version_id") == context["knowledge_base_version_id"]
            and snapshot.get("prompt_set") == context["prompt_set"]
            and snapshot.get("execution_mode") == context["execution_mode"]
            and snapshot.get("history_turns") == 0  # only independent runs (no earlier turns) are comparable
            and "result" in snapshot
            and "error" not in snapshot
            and _verified_run(trace_of, row["request_id"])
        ):
            found.append(row["request_id"])
            if len(found) == limit:
                break
    return found


def plan(app_state, conn, principal: dict, selection: dict) -> dict:
    """Estimate without any paid call: cells, reused runs, new executions, fixed factors and cost upper bound."""
    from merchant_assistant.api import v1

    settings, orchestrator = app_state.settings, app_state.orchestrator
    refs = selection["profiles"]
    keys = [(ref["profile_id"], ref["profile_version"]) for ref in refs]
    if not MIN_PROFILES <= len(refs) <= MAX_PROFILES or len(set(keys)) != len(keys):
        raise ComparisonError(422, "invalid_selection", "Select two or three different published profiles.")
    scenario_ids = selection["scenario_ids"]
    if not 1 <= len(scenario_ids) <= MAX_SCENARIOS or len(set(scenario_ids)) != len(scenario_ids):
        raise ComparisonError(422, "invalid_selection", "Select one to three different catalog scenarios.")
    repetitions = selection["repetitions"]
    if not 1 <= repetitions <= MAX_REPETITIONS:
        raise ComparisonError(422, "invalid_selection", "Repetitions must be 1 or 2.")
    profiles = []
    for profile_id, version in keys:
        profile = get_profile(conn, profile_id, version, role=v1.profile_role(principal))
        if profile is None:
            raise ComparisonError(404, "not_found", "Profile not found or not published for this session.")
        profiles.append(profile)
    selected_scenarios = []
    for scenario_id in scenario_ids:
        scenario = scenario_catalog.get(settings.data_dir, scenario_id)
        if scenario is None:
            raise ComparisonError(422, "unknown_scenario", "Scenario is not in the catalog.")
        selected_scenarios.append(scenario)
    kb = getattr(orchestrator, "knowledge_base", None)
    context = {
        "router_mechanism": selection["router_mechanism"],
        "knowledge_base_version_id": kb.capture_active()[1] if kb else None,
        "prompt_set": prompt_versions(settings.prompts_dir),
        "execution_mode": _execution_mode(orchestrator),
    }
    per_cell = float(settings.max_request_cost_usd)
    cells = []
    for scenario in selected_scenarios:
        for profile in profiles:
            reusable = (
                _compatible_runs(
                    conn, principal["principal_id"], profile, scenario, context, orchestrator.trace, repetitions
                )
                if selection.get("reuse_recorded", True)
                else []
            )
            for repetition in range(1, repetitions + 1):
                reused = reusable[repetition - 1] if len(reusable) >= repetition else None
                cells.append(
                    {
                        "scenario_id": scenario["id"],
                        "profile_id": profile["profile_id"],
                        "profile_version": profile["version"],
                        "repetition": repetition,
                        "source": "recorded" if reused else "new",
                        "reused_request_id": reused,
                        "estimated_cost_usd": 0.0 if reused else per_cell,
                    }
                )
    changes = _profile_changes(profiles)
    new_cells = sum(cell["source"] == "new" for cell in cells)
    estimate = {
        "profiles": [
            {
                "profile_id": p["profile_id"],
                "profile_version": p["version"],
                "profile_digest": p["digest"],
                "agents": p["agents"],
            }
            for p in profiles
        ],
        "scenario_ids": scenario_ids,
        "repetitions": repetitions,
        "cells": cells,
        "sample_size": len(cells),
        "new_executions": new_cells,
        "reused_executions": len(cells) - new_cells,
        "estimated_cost_usd": round(new_cells * per_cell, 8),
        "estimate_basis": "request cost cap per new execution (upper bound, catalog rates)",
        "fixed_factors": {
            "scenarios": scenario_ids,
            "scenario_catalog_version": scenario_catalog.catalog(settings.data_dir)["version"],
            "knowledge_base_version_id": context["knowledge_base_version_id"],
            "prompt_set": context["prompt_set"],
            "router_mechanism": context["router_mechanism"],
            "data": "synthetic seed (temporary copy per comparison)",
            "tools": "customer_support tool registry",
            "evaluator": "deterministic checks over the same scenario labels",
        },
        "execution_mode": context["execution_mode"],
        "changes_between_profiles": changes,
        "exploratory": any(len(item["changed_agents"]) > 1 for item in changes),
        "limits": {
            "profiles": [MIN_PROFILES, MAX_PROFILES],
            "scenarios": MAX_SCENARIOS,
            "repetitions": MAX_REPETITIONS,
            "cells": MAX_CELLS,
        },
    }
    estimate["estimate_digest"] = digest(
        {key: estimate[key] for key in ("profiles", "cells", "fixed_factors", "execution_mode", "estimated_cost_usd")}
    )
    return estimate


def _cell_metrics(run: dict) -> dict:
    by_agent = {
        agent: {"cost_usd": usage.get("cost_usd", 0.0), "models": usage.get("models", [])}
        for agent, usage in (run.get("models_by_agent") or {}).items()
    }
    return {
        "duration_ms": run.get("duration_ms"),
        "cost_usd": run.get("cost_estimate_usd"),
        "cost_by_agent": by_agent,
        "route": (run.get("result") or {}).get("route"),
        "response_status": (run.get("result") or {}).get("status"),
    }


def _save(conn, comparison_id: str, holder: str, *, cells, failures, state=None, cost_usd=None) -> bool:
    """Records the run's progress under its lease, renewing it. False when `holder` no longer holds the comparison."""
    cursor = conn.execute(
        "UPDATE comparisons SET cells=?,failures=?,state=COALESCE(?,state),cost_usd=COALESCE(?,cost_usd),"
        "updated_at=?,heartbeat_at=? WHERE comparison_id=? AND worker_id=? AND state='running'",
        (json.dumps(cells), json.dumps(failures), state, cost_usd, _now(), _stamp(), comparison_id, holder),
    )
    return cursor.rowcount == 1


def _budget_denied(trace: dict | None) -> bool:
    if not trace:
        return False
    texts = [str(item) for item in trace.get("errors", [])]
    texts += [str(step.get("detail", {}).get("error", "")) for step in trace.get("steps", [])]
    return any("budget exceeded" in text.casefold() for text in texts)


def start(app, principal: dict, selection: dict, *, confirmed: bool, max_cost_usd: float, expected_digest: str):
    from merchant_assistant.api import v1

    settings, orchestrator = app.state.settings, app.state.orchestrator
    if not confirmed:
        raise ComparisonError(422, "confirmation_required", "Explicit confirmation is required.")
    conn = connect(settings.db_path)
    try:
        estimate = plan(app.state, conn, principal, selection)
        if estimate["estimate_digest"] != expected_digest:
            raise ComparisonError(409, "estimate_stale", "The estimate changed; estimate again before confirming.")
        if max_cost_usd < estimate["estimated_cost_usd"]:
            raise ComparisonError(422, "max_cost_below_estimate", "The confirmed cap is below the estimate.")
        if estimate["estimated_cost_usd"] > orchestrator.budget.remaining():
            raise ComparisonError(429, "installation_budget_exceeded", "The estimate exceeds the remaining budget.")
        comparison_id = f"pcmp_{uuid.uuid4().hex[:20]}"
        cells = [dict(cell, status="pending") for cell in estimate["cells"]]
        config = {key: estimate[key] for key in estimate if key not in ("cells",)} | {"max_cost_usd": max_cost_usd}
        kb = getattr(orchestrator, "knowledge_base", None)
        knowledge = kb.capture_active() if kb else (orchestrator.index, None)
        holder = _new_holder()
        # One write transaction checks the other running comparisons, counts the demo actions and records the lease,
        # so two requests of the same principal in two workers never both start one.
        conn.execute("BEGIN IMMEDIATE")
        try:
            running = conn.execute(
                "SELECT * FROM comparisons WHERE principal_id=? AND state='running'", (principal["principal_id"],)
            ).fetchall()
            if any(_lease_alive(row) for row in running):
                raise ComparisonError(
                    409, "comparison_running", "Another comparison is still running; refresh it first."
                )
            if (
                principal["role"] in v1.LIMITED_ROLES
                and estimate["new_executions"]
                and not v1.consume_demo_messages(conn, principal, estimate["new_executions"], settings)
            ):
                raise ComparisonError(
                    429,
                    "demo_message_limit_reached",
                    "This demo session cannot run that many new executions; reuse recorded runs or start a new "
                    "session.",
                )
            conn.execute(
                "INSERT INTO comparisons (comparison_id,principal_id,state,config,cells,failures,estimate,cost_usd,"
                "created_at,updated_at,worker_id,heartbeat_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    comparison_id,
                    principal["principal_id"],
                    "running",
                    json.dumps(config, sort_keys=True),
                    json.dumps(cells),
                    "[]",
                    json.dumps({"estimated_cost_usd": estimate["estimated_cost_usd"], "digest": expected_digest}),
                    0.0,
                    _now(),
                    _now(),
                    holder,
                    _stamp(),
                ),
            )
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    thread = threading.Thread(
        target=_run,
        args=(app, comparison_id, principal, config, cells, knowledge),
        kwargs={"holder": holder},
        name=f"comparison-{comparison_id}",
        daemon=True,
    )
    try:
        thread.start()
    except BaseException:
        _drop_lease(settings.db_path, comparison_id, holder)
        raise
    return comparison_id


def _run(
    app,
    comparison_id: str,
    principal: dict,
    config: dict,
    cells: list[dict],
    knowledge,
    *,
    holder: str,
    failures: list[dict] | None = None,
    spent: float = 0.0,
) -> None:
    """Runs every cell that has no result yet (`request_id`) under the lease of `holder`. A resume passes the recorded
    failures and the cost already accumulated, so the cap applies to the whole comparison and the cost keeps adding
    up (task 84). A holder that loses the lease ends the cell in progress, records nothing of it in `comparisons` and
    starts no other; the next holder reconciles that cell with the snapshot and ledger (task 99)."""
    from merchant_assistant.api import v1

    settings, orchestrator = app.state.settings, app.state.orchestrator
    failures = [] if failures is None else failures
    lease = _Lease(settings.db_path, comparison_id, holder).start()
    lost = False
    workdir = Path(tempfile.mkdtemp(prefix="comparison-"))
    conn = connect(settings.db_path)
    try:
        domain = workdir / "domain.sqlite3"
        source, target = sqlite3.connect(settings.db_path), sqlite3.connect(domain)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        if knowledge[1] != config["fixed_factors"]["knowledge_base_version_id"]:
            failures.append({"code": "knowledge_base_changed", "message": "The active knowledge base changed."})
            for cell in cells:
                if not cell.get("request_id"):  # a resumed comparison keeps the results it already has
                    cell["status"] = "skipped"
            return
        profiles = {(p["profile_id"], p["profile_version"]): p for p in config["profiles"]}
        stopped = None
        per_cell = float(settings.max_request_cost_usd)
        for cell in cells:
            if cell.get("request_id"):  # result already recorded (a resumed comparison): never run twice
                continue
            if lease.lost.is_set():
                raise _LeaseLost
            scenario = scenario_catalog.get(settings.data_dir, cell["scenario_id"])
            if stopped:
                cell.update(status="skipped", error=stopped)
                continue
            if cell["source"] == "recorded":
                row = conn.execute(
                    "SELECT snapshot FROM run_snapshots WHERE request_id=?", (cell["reused_request_id"],)
                ).fetchone()
                run = json.loads(row["snapshot"]) if row else None
                if run is None:
                    cell.update(status="failed", error="recorded_run_missing")
                    failures.append({"code": "recorded_run_missing", "cell": cell["reused_request_id"]})
                else:
                    cell.update(status="completed", origin="recorded", request_id=cell["reused_request_id"])
                    cell.update(_cell_metrics(run))
                    # No paid call here: a budget refusal or an unreadable trace fails only this cell (its stop code is
                    # ignored), and a retry reuses the same run again.
                    _check_completed(app.state, conn, cell, cell["request_id"], run, principal, failures)
                if not _save(conn, comparison_id, holder, cells=cells, failures=failures):
                    raise _LeaseLost
                continue
            if spent + per_cell > config["max_cost_usd"] + 1e-12:
                stopped = "comparison_cap_reached"
                cell.update(status="skipped", error=stopped)
                failures.append({"code": stopped, "message": "The confirmed comparison cap was reached."})
                continue
            key = (cell["profile_id"], cell["profile_version"])
            profile = {
                "profile_id": key[0],
                "version": key[1],
                "digest": profiles[key]["profile_digest"],
                "agents": profiles[key]["agents"],
            }
            request_id = f"req_{uuid.uuid4().hex[:20]}"
            # Recorded before the call so interruption recovery can find this cell's snapshot and ledger entries.
            # Each later reservation rechecks this request id and the lease under the takeover lock.
            cell["in_flight_request_id"] = request_id
            if not _save(conn, comparison_id, holder, cells=cells, failures=failures):
                raise _LeaseLost
            cell["request_id"] = request_id
            try:
                result = v1.execute_run(
                    app.state,
                    conn,
                    request_id=request_id,
                    principal=principal,
                    customer_id=principal["customer_id"],
                    profile=profile,
                    message=scenario["message"],
                    mechanism=config["fixed_factors"]["router_mechanism"],
                    scenario_id=scenario["id"],
                    purpose="comparison",
                    profile_comparison_id=comparison_id,
                    domain_db_path=domain,
                    knowledge=knowledge,
                    reservation_fence=lease.reservation,
                )
            except v1.RunFailure as exc:
                cell.update(status="failed", error=exc.code)
                failures.append({"code": exc.code, "request_id": request_id})
                attempt = _ledger_attempt(orchestrator.budget, request_id)
                try:
                    trace = orchestrator.trace(request_id)
                except Exception:
                    trace = None
                    stopped = "trace_unavailable"
                    failures.append({"code": stopped, "request_id": request_id})
                estimate = (trace or {}).get("cost_usd")
                if attempt is None:
                    stopped = "execution_cost_unknown"
                    failures.append({"code": stopped, "request_id": request_id, "cost_estimate_usd": estimate})
                else:
                    spent += _cell_cost(estimate, attempt)
                if _budget_denied(trace):
                    stopped = stopped or "budget_denied"
                    failures.append({"code": "budget_denied", "message": "The budget guard refused a paid call."})
            except Exception as exc:  # recorded as a failed cell, never raised from the thread
                cell.update(status="failed", error=type(exc).__name__)
                failures.append({"code": "execution_failed", "request_id": request_id})
                attempt = _ledger_attempt(orchestrator.budget, request_id)
                if attempt is None:
                    stopped = "execution_cost_unknown"
                    failures.append({"code": stopped, "request_id": request_id})
                else:
                    spent += attempt[1]
            else:
                run = result["run"]
                estimate = run.get("cost_estimate_usd")
                attempt = _ledger_attempt(orchestrator.budget, request_id)
                if attempt is None:
                    stopped = "execution_cost_unknown"
                    failures.append({"code": stopped, "request_id": request_id, "cost_estimate_usd": estimate})
                else:
                    spent += _cell_cost(estimate, attempt)
                cell.update(status="completed", origin=run.get("execution_mode"))
                cell.update(_cell_metrics(run | {"result": result["message"]}))
                completed_run = run | {"result": result["message"]}
                refused = _check_completed(app.state, conn, cell, request_id, completed_run, principal, failures)
                stopped = stopped or refused
            cell.pop("in_flight_request_id", None)
            if not _save(conn, comparison_id, holder, cells=cells, failures=failures, cost_usd=round(spent, 8)):
                raise _LeaseLost
    except _LeaseLost:  # another worker may run the comparison now: nothing more is recorded from here
        lost = True
        log.warning("comparison lease lost", extra={"event": {"comparison_id": comparison_id}})
    except Exception as exc:  # unexpected: keep what was recorded and mark the comparison failed
        failures.append({"code": "comparison_failed", "message": type(exc).__name__})
    finally:
        try:
            if not lost:
                _finish(app, conn, comparison_id, holder, principal, cells, failures, spent)
        finally:
            conn.close()
            lease.stop()
            shutil.rmtree(workdir, ignore_errors=True)


def _finish(app, conn, comparison_id: str, holder: str, principal: dict, cells, failures, spent: float) -> None:
    """Final state of a run that still holds its lease; the demo actions are given back in the same transaction, so
    a run that lost its lease meanwhile gives nothing back (the run that holds it now does)."""
    from merchant_assistant.api import v1

    orchestrator = app.state.orchestrator
    for cell in cells:
        cell.pop("in_flight_request_id", None)
    completed = sum(cell.get("status") == "completed" for cell in cells)
    cost_unknown = any(failure.get("code") == "execution_cost_unknown" for failure in failures)
    state = "completed" if completed == len(cells) and not cost_unknown else ("partial" if completed else "failed")
    unused = 0
    try:
        # New cells were counted against the demo limit at the start; give back those that made no model call
        # (skipped by a knowledge-base change, the confirmed cap or a budget refusal, or refused before a call).
        # The decision uses the ledger rows of each run; when they cannot be read nothing is given back (P3-R3-01).
        # A cell given back is flagged (`demo_refunded`): a resume counts it again before running it, and a
        # cell is never given back twice.
        for cell in cells:
            if cell.get("source") != "new" or cell.get("demo_refunded"):
                continue
            if not cell.get("request_id"):  # never started: certainly no model call
                cell["model_calls"] = 0
                cell["demo_refunded"] = True
                unused += 1
                continue
            if "model_calls" not in cell:  # cells finished by an earlier run keep their count
                cell["model_calls"] = v1.model_calls_made(orchestrator, cell["request_id"])
            if v1.paid_attempts(orchestrator.budget, cell["request_id"]) == 0:
                cell["demo_refunded"] = True
                unused += 1
    except Exception:  # accounting never hides the comparison result; nothing is given back
        unused = 0
        failures.append({"code": "demo_refund_failed"})
    conn.execute("BEGIN IMMEDIATE")
    try:
        try:
            v1.refund_demo_messages(conn, principal, unused)
        except Exception:  # accounting never hides the comparison result
            failures.append({"code": "demo_refund_failed"})
        if _save(conn, comparison_id, holder, cells=cells, failures=failures, state=state, cost_usd=round(spent, 8)):
            conn.execute("COMMIT")
        else:
            conn.execute("ROLLBACK")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise


def _judge_view(evaluations: list[dict]) -> dict | None:
    completed = [item for item in evaluations if item["state"] == "completed"]
    return completed[-1] if completed else None


def _ledger_attempt(budget, request_id: str) -> tuple[int, float] | None:
    """Paid reservations and their committed cost in one ledger read. None means the ledger is uncertain."""
    guard = getattr(budget, "primary", budget)
    guard = getattr(guard, "guard", guard)
    path = getattr(guard, "path", None)
    if not isinstance(path, str) or not path or path == ":memory:":
        return None
    try:
        ledger = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", timeout=10, uri=True)
        try:
            row = ledger.execute(
                "SELECT COUNT(*), COALESCE(SUM(CASE WHEN status='settled' THEN actual_usd "
                "WHEN status='reserved' THEN reserved_usd ELSE 0 END), 0) FROM ledger "
                "WHERE request_id=? AND status IN ('reserved','settled')",
                (request_id,),
            ).fetchone()
        finally:
            ledger.close()
    except (OSError, sqlite3.Error, ValueError):
        return None
    return int(row[0]), float(row[1] or 0.0)


def _traced_checks(app_state, conn, cell: dict, request_id: str, run: dict, principal: dict, failures) -> dict | None:
    """Records the deterministic checks of a completed cell and returns its trace. A trace that is missing (a failed
    save leaves none) or cannot be read fails the cell as `trace_unavailable` and returns None; it runs again only
    with `retry_failed`."""
    from merchant_assistant.api import v1

    try:
        trace = app_state.orchestrator.trace(request_id)
        if trace is not None:
            cell["checks"] = v1.run_checks(app_state, conn, request_id, run, principal)
    except Exception:
        trace = None
    if trace is None:
        cell.pop("checks", None)
        cell.update(status="failed", error="trace_unavailable")
        failures.append({"code": "trace_unavailable", "request_id": request_id})
    return trace


def _check_completed(app_state, conn, cell: dict, request_id: str, run: dict, principal: dict, failures) -> str | None:
    """Checks a completed cell (new, restored after an interruption, or reused) against its trace and returns the code
    that stops the comparison, if any. A budget refusal fails the cell; so does a trace that is missing or cannot be
    read, since a refusal cannot be ruled out then. A cell that ran counts its cost in the caller; a reused cell
    made no paid call and stops nothing."""
    trace = _traced_checks(app_state, conn, cell, request_id, run, principal, failures)
    if trace is None:
        return "trace_unavailable"
    if _budget_denied(trace):
        cell.update(status="failed", error="budget_denied")
        failures.append({"code": "budget_denied", "request_id": request_id})
        return "budget_denied"
    return None


def _cell_cost(estimate: float | None, attempt: tuple[int, float] | None) -> float:
    """Count a request once while covering any ledger costs outside the trace, such as query embeddings."""
    return max(float(estimate or 0.0), attempt[1] if attempt is not None else 0.0)


def _completed_snapshot(conn, row, cell, request_id: str) -> dict | None:
    """The durable run is reusable only for this owner's exact comparison cell."""
    stored = conn.execute(
        "SELECT rs.customer_id,rs.profile_id,rs.profile_version,rs.snapshot,p.customer_id "
        "AS owner_customer_id FROM run_snapshots rs JOIN api_principals p ON p.principal_id=rs.principal_id "
        "WHERE rs.request_id=? AND rs.principal_id=?",
        (request_id, row["principal_id"]),
    ).fetchone()
    if stored is None:
        return None
    try:
        snapshot = json.loads(stored["snapshot"])
    except (TypeError, json.JSONDecodeError):
        return None
    if (
        not isinstance(snapshot, dict)
        or stored["customer_id"] != stored["owner_customer_id"]
        or stored["profile_id"] != cell.get("profile_id")
        or stored["profile_version"] != cell.get("profile_version")
        or snapshot.get("profile_id") != cell.get("profile_id")
        or snapshot.get("profile_version") != cell.get("profile_version")
        or snapshot.get("scenario_id") != cell.get("scenario_id")
        or snapshot.get("profile_comparison_id") != row["comparison_id"]
        or snapshot.get("purpose") != "comparison"
    ):
        return None
    try:
        result = MessageResponse.model_validate(snapshot.get("result"))
    except ValidationError:
        return None
    if result.request_id != request_id:
        return None
    return snapshot | {"_customer_id": stored["customer_id"]}


def _mark_interrupted(conn, app_state, row) -> bool:
    """Recover durable cell results; retry an in-flight cell only when the ledger proves no paid call was reserved."""
    cells, failures = json.loads(row["cells"]), json.loads(row["failures"])
    cost = float(row["cost_usd"] or 0.0)
    orchestrator = getattr(app_state, "orchestrator", None)
    budget = getattr(orchestrator, "budget", None)
    for cell in cells:
        request_id = cell.pop("in_flight_request_id", None)
        if not request_id:
            continue
        attempt = _ledger_attempt(budget, request_id) if budget is not None else None
        snapshot = _completed_snapshot(conn, row, cell, request_id)
        if snapshot is not None:
            principal = {"principal_id": row["principal_id"], "customer_id": snapshot.get("_customer_id")}
            cell.update(status="completed", request_id=request_id, origin=snapshot.get("execution_mode"))
            cell.update(_cell_metrics(snapshot))
            if snapshot.get("model_calls") is not None:
                cell["model_calls"] = int(snapshot["model_calls"])
            _check_completed(app_state, conn, cell, request_id, snapshot, principal, failures)
            if attempt is None:
                failures.append(
                    {
                        "code": "execution_cost_unknown",
                        "request_id": request_id,
                        "cost_estimate_usd": snapshot.get("cost_estimate_usd"),
                    }
                )
            else:
                cost += _cell_cost(snapshot.get("cost_estimate_usd"), attempt)
            continue

        attempt_cost = attempt[1] if attempt is not None else None
        cell.setdefault("interrupted_attempts", []).append({"request_id": request_id, "cost_usd": attempt_cost})
        if attempt is None or attempt[0] > 0:
            cell.update(
                status="failed",
                request_id=request_id,
                error="interrupted_cost_unknown" if attempt is None else "interrupted_after_paid_attempt",
            )
            cost += attempt_cost or 0.0
            if attempt is None:
                failures.append({"code": "execution_cost_unknown", "request_id": request_id})
        else:
            cell.update(status="pending")
            cell.pop("request_id", None)

    failures.append({"code": "interrupted", "message": "The API process stopped before the comparison ended."})
    updated = conn.execute(
        "UPDATE comparisons SET cells=?,failures=?,state='interrupted',cost_usd=?,updated_at=? "
        "WHERE comparison_id=? AND state='running'",
        (json.dumps(cells), json.dumps(failures), round(cost, 8), _now(), row["comparison_id"]),
    )
    return updated.rowcount == 1


def _interrupt_if_orphan(conn, app_state, comparison_id: str) -> bool:
    """Marks the comparison `interrupted` if, read again inside one write transaction, it is still `running` and its
    lease expired. A claim records its lease in its own write transaction, and a holder renews it or records its
    final state in single statements, so a stale read outside the transaction never marks a live comparison."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT * FROM comparisons WHERE comparison_id=?", (comparison_id,)).fetchone()
        marked = (
            row is not None
            and row["state"] == "running"
            and not _lease_alive(row)
            and _mark_interrupted(conn, app_state, row)
        )
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return marked


def interrupt_orphans(app_state) -> list[str]:
    """At the startup of a worker, every `running` comparison whose lease expired becomes `interrupted` (task 84). The
    comparisons another worker is running keep their lease and are left alone (task 99)."""
    conn = connect(app_state.settings.db_path)
    try:
        marked = []
        for row in conn.execute("SELECT * FROM comparisons WHERE state='running'").fetchall():
            if not _lease_alive(row) and _interrupt_if_orphan(conn, app_state, row["comparison_id"]):
                marked.append(row["comparison_id"])
                log.info("comparison interrupted", extra={"event": {"comparison_id": row["comparison_id"]}})
        return marked
    finally:
        conn.close()


def resume(app, principal: dict, comparison_id: str, *, retry_failed: bool = False) -> dict:
    """Continues an `interrupted`, `partial` or `failed` comparison with its recorded configuration (task 84). Cells
    with a result (`request_id`) are never run again; failed cells run again only with `retry_failed`. The budget
    and the demo limit are checked only for the cells that still have to run.

    The claim (task 99) reads the row, checks it and records the new lease in one write transaction: between the
    read and the claim nothing else can resume, finish or interrupt the comparison, in this worker or another."""
    from merchant_assistant.api import v1

    settings, orchestrator = app.state.settings, app.state.orchestrator
    holder = _new_holder()
    conn = connect(settings.db_path)
    try:
        row = conn.execute(
            "SELECT * FROM comparisons WHERE comparison_id=? AND principal_id=?",
            (comparison_id, principal["principal_id"]),
        ).fetchone()
        if row is None:
            raise ComparisonError(404, "not_found", "Comparison not found.")
        if row["state"] == "running" and not _lease_alive(row):
            _interrupt_if_orphan(conn, app.state, comparison_id)
        # Read before the claim's transaction: capturing the knowledge base may write its registry.
        kb = getattr(orchestrator, "knowledge_base", None)
        knowledge = kb.capture_active() if kb else (orchestrator.index, None)
        prompt_set = prompt_versions(settings.prompts_dir)
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT * FROM comparisons WHERE comparison_id=?", (comparison_id,)).fetchone()
            if row["state"] == "running":
                raise ComparisonError(409, "comparison_running", "The comparison is still running.")
            if row["state"] == "completed":
                raise ComparisonError(
                    409, "comparison_completed", "The comparison already completed; nothing to resume."
                )
            running = conn.execute(
                "SELECT * FROM comparisons WHERE principal_id=? AND state='running'", (principal["principal_id"],)
            ).fetchall()
            if any(_lease_alive(item) for item in running):
                raise ComparisonError(
                    409, "comparison_running", "Another comparison is still running; refresh it first."
                )
            config, cells = json.loads(row["config"]), json.loads(row["cells"])
            failures, spent = json.loads(row["failures"]), float(row["cost_usd"] or 0.0)
            for cell in cells:
                if cell.get("error") == "interrupted_cost_unknown" and not any(
                    failure.get("request_id") == cell.get("request_id")
                    and failure.get("code") in ("execution_cost_unknown", "execution_cost_recovered")
                    for failure in failures
                ):
                    failures.append({"code": "execution_cost_unknown", "request_id": cell["request_id"]})
            for failure in failures:
                if failure.get("code") != "execution_cost_unknown":
                    continue
                attempt = _ledger_attempt(orchestrator.budget, failure["request_id"])
                if attempt is None:
                    raise ComparisonError(409, "execution_cost_unknown", "The cost of a prior execution is unknown.")
                spent += _cell_cost(failure.get("cost_estimate_usd"), attempt)
                for cell in cells:
                    if (
                        cell.get("request_id") == failure["request_id"]
                        and cell.get("error") == "interrupted_cost_unknown"
                    ):
                        cell["error"] = "interrupted_after_paid_attempt" if attempt[0] else "interrupted"
                        for entry in cell.get("interrupted_attempts", []):
                            if entry.get("request_id") == failure["request_id"] and entry.get("cost_usd") is None:
                                entry["cost_usd"] = attempt[1]
                failure["code"] = "execution_cost_recovered"
            fixed = config["fixed_factors"]
            if (
                knowledge[1] != fixed["knowledge_base_version_id"]
                or prompt_set != fixed["prompt_set"]
                or _execution_mode(orchestrator) != config["execution_mode"]
            ):
                raise ComparisonError(
                    409,
                    "fixed_factors_changed",
                    "The knowledge base, prompts or execution mode changed since the comparison started; start a new "
                    "one.",
                )
            for cell in cells:
                if (cell.get("status") == "failed" and not retry_failed) or (
                    cell.get("request_id") and cell.get("status") != "failed"
                ):
                    continue  # recorded result, or a failed cell without retry_failed: kept as it is
                previous = cell.pop("request_id", None)
                if previous:  # the failed attempt stays attached to the cell (and in the ledger under its own id)
                    cell.setdefault("previous_request_ids", []).append(previous)
                for key in ("error", "origin", "checks", "model_calls", *_cell_metrics({})):
                    cell.pop(key, None)
                cell["status"] = "pending"
            todo = [cell for cell in cells if cell["status"] == "pending"]
            if not todo and not (cells and all(cell.get("status") == "completed" for cell in cells)):
                raise ComparisonError(
                    409,
                    "nothing_to_resume",
                    "Every cell has a result; use retry_failed=true to run the failed ones again.",
                )
            new_cells = sum(cell["source"] == "new" for cell in todo)
            if new_cells * float(settings.max_request_cost_usd) > orchestrator.budget.remaining():
                raise ComparisonError(429, "installation_budget_exceeded", "The remaining cells exceed the budget.")
            recount = [cell for cell in todo if cell["source"] == "new" and cell.get("demo_refunded")]
            for cell in recount:  # counted again below: given back again only if it makes no paid call this time
                cell.pop("demo_refunded", None)
            conn.execute(
                "UPDATE comparisons SET state='running',cells=?,failures=?,cost_usd=?,updated_at=?,"
                "worker_id=?,heartbeat_at=? "
                "WHERE comparison_id=?",
                (json.dumps(cells), json.dumps(failures), round(spent, 8), _now(), holder, _stamp(), comparison_id),
            )
            if (
                principal["role"] in v1.LIMITED_ROLES
                and recount
                and not v1.consume_demo_messages(conn, principal, len(recount), settings)
            ):
                raise ComparisonError(
                    429,
                    "demo_message_limit_reached",
                    "This demo session cannot run that many new executions; start a new session.",
                )
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    thread = threading.Thread(
        target=_run,
        args=(app, comparison_id, principal, config, cells, knowledge),
        kwargs={"holder": holder, "failures": failures, "spent": spent},
        name=f"comparison-{comparison_id}",
        daemon=True,
    )
    try:
        thread.start()
    except BaseException:
        _drop_lease(settings.db_path, comparison_id, holder)
        raise
    return {"comparison_id": comparison_id, "state": "running", "resumed_cells": len(todo)}


def read(app_state, conn, principal: dict, comparison_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM comparisons WHERE comparison_id=? AND principal_id=?", (comparison_id, principal["principal_id"])
    ).fetchone()
    if row is None:
        raise ComparisonError(404, "not_found", "Comparison not found.")
    if row["state"] == "running" and not _lease_alive(row):
        # The worker that ran it stopped (its lease expired): the comparison becomes `interrupted` and can be resumed
        # (tasks 84 and 99). A holder that recorded its final state in the meantime is never overwritten (P3-01).
        _interrupt_if_orphan(conn, app_state, comparison_id)
        row = conn.execute("SELECT * FROM comparisons WHERE comparison_id=?", (comparison_id,)).fetchone()
    state = row["state"]
    cells, failures = json.loads(row["cells"]), json.loads(row["failures"])
    from merchant_assistant.api import v1

    evaluations = {
        cell["request_id"]: v1.list_evaluations(conn, cell["request_id"], principal)
        for cell in cells
        if cell.get("request_id")
    }
    config = json.loads(row["config"])
    return {
        "comparison_id": comparison_id,
        "state": state,
        "config": config,
        "estimate": json.loads(row["estimate"]),
        "cells": cells,
        "failures": failures,
        "cost_usd": row["cost_usd"],
        "cost_is_estimate": True,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "aggregates": aggregates(config, cells, evaluations),
    }


def aggregates(config: dict, cells: list[dict], evaluations: dict[str, list[dict]]) -> dict:
    profiles = []
    cost_by_agent: dict[tuple, dict] = {}
    for ref in config["profiles"]:
        key = (ref["profile_id"], ref["profile_version"])
        mine = [c for c in cells if (c["profile_id"], c["profile_version"]) == key]
        done = [c for c in mine if c.get("status") == "completed"]
        passed = sum((c.get("checks") or {}).get("passed", 0) for c in done)
        total = sum((c.get("checks") or {}).get("total", 0) for c in done)
        judged = [_judge_view(evaluations.get(c["request_id"], [])) for c in done]
        evaluator_keys = {
            json.dumps(item["evaluator"], sort_keys=True) + item["rubric_version"] for item in judged if item
        }
        model_quality = None
        if done and all(judged) and len(evaluator_keys) == 1:
            model_quality = {
                criterion: round(sum(item["result"][criterion] for item in judged) / len(judged), 2)
                for criterion in JUDGE_CRITERIA
            }
        costs = [float(c["cost_usd"]) for c in done if c.get("cost_usd") is not None]  # unknown is never zero
        durations = [c["duration_ms"] for c in done if c.get("duration_ms") is not None]
        profiles.append(
            {
                "profile_id": ref["profile_id"],
                "profile_version": ref["profile_version"],
                "planned": len(mine),
                "sample_size": len(done),
                "failed": len(mine) - len(done),
                "cost_mean_usd": round(sum(costs) / len(costs), 8) if costs else None,
                "cost_total_usd": round(sum(costs), 8) if costs else None,
                "cost_unknown_runs": len(done) - len(costs),
                "duration_mean_ms": round(sum(durations) / len(durations)) if durations else None,
                "deterministic_quality": round(passed / total, 4) if total else None,
                "deterministic_checks": {"passed": passed, "total": total},
                "critical_failures": sum(len((c.get("checks") or {}).get("critical_failures", [])) for c in done),
                "model_quality": model_quality,
                "model_quality_status": "evaluated" if model_quality else "not_evaluated",
            }
        )
        for cell in done:
            for agent, usage in (cell.get("cost_by_agent") or {}).items():
                # An agent that used several models in one run has one combined cost: it is not split or duplicated.
                for model in [" + ".join(usage.get("models") or []) or "unknown"]:
                    key = (ref["profile_id"], ref["profile_version"], agent, model)
                    entry = cost_by_agent.setdefault(
                        key,
                        {
                            "profile_id": key[0],
                            "profile_version": key[1],
                            "agent": agent,
                            "model": model,
                            "cost_usd": 0.0,
                            "request_ids": [],
                        },
                    )
                    if usage.get("cost_usd") is None:
                        entry["cost_unknown"] = True
                    else:
                        entry["cost_usd"] = round(entry["cost_usd"] + float(usage["cost_usd"]), 8)
                    if cell["request_id"] not in entry["request_ids"]:
                        entry["request_ids"].append(cell["request_id"])
    return {
        "quality_basis": "share of deterministic checks passed under the same scenario labels",
        "model_quality_basis": "model judge means only when every run of the profile was judged with one evaluator",
        "profiles": profiles,
        "cost_by_agent_model": list(cost_by_agent.values()),
        "exploratory": config.get("exploratory", False),
    }
