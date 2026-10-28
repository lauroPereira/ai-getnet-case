"""Small, traceable profile comparison (v0.6.0, RF-78).

Two or three published profiles x up to three catalog scenarios x up to two repetitions (at most 18 cells).
New executions run outside the HTTP request, in a thread of the API process; domain effects (conversations, cases,
attempts, handoffs, audit) go to a temporary copy of the synthetic database, while traces and run snapshots are
stored normally and marked with purpose=comparison. One knowledge-base version is captured for the whole run."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from merchant_assistant import scenarios as scenario_catalog
from merchant_assistant.data.db import connect
from merchant_assistant.guardrails.input import check_input
from merchant_assistant.llm.prompts import prompt_versions
from merchant_assistant.profiles import digest, get_profile

MIN_PROFILES, MAX_PROFILES, MAX_SCENARIOS, MAX_REPETITIONS = 2, 3, 3, 2
MAX_CELLS = MAX_PROFILES * MAX_SCENARIOS * MAX_REPETITIONS
JUDGE_CRITERIA = ("answers_question", "clarity_and_tone", "honesty")

_ACTIVE: dict[str, threading.Thread] = {}
_ACTIVE_LOCK = threading.Lock()


class ComparisonError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


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


def _compatible_runs(conn, principal_id: str, profile: dict, scenario: dict, context: dict) -> list[str]:
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
        ):
            found.append(row["request_id"])
    return found


def plan(app_state, conn, principal: dict, selection: dict) -> dict:
    """Estimate without any paid call: cells, reused runs, new executions, fixed factors and cost upper bound."""
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
        profile = get_profile(conn, profile_id, version, role=principal["role"])
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
                _compatible_runs(conn, principal["principal_id"], profile, scenario, context)
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


def _save(conn, comparison_id: str, *, cells, failures, state=None, cost_usd=None) -> None:
    conn.execute(
        "UPDATE comparisons SET cells=?,failures=?,state=COALESCE(?,state),cost_usd=COALESCE(?,cost_usd),"
        "updated_at=? WHERE comparison_id=?",
        (json.dumps(cells), json.dumps(failures), state, cost_usd, _now(), comparison_id),
    )


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
        running = [
            row[0]
            for row in conn.execute(
                "SELECT comparison_id FROM comparisons WHERE principal_id=? AND state='running'",
                (principal["principal_id"],),
            )
        ]
        with _ACTIVE_LOCK:
            busy = any(item in _ACTIVE and _ACTIVE[item].is_alive() for item in running)
        if busy:
            raise ComparisonError(409, "comparison_running", "Another comparison is still running; refresh it first.")
        if (
            principal["role"] == "demo"
            and estimate["new_executions"]
            and not v1.consume_demo_messages(conn, principal, estimate["new_executions"], settings)
        ):
            raise ComparisonError(
                429,
                "demo_message_limit_reached",
                "This demo session cannot run that many new executions; reuse recorded runs or start a new session.",
            )
        comparison_id = f"pcmp_{uuid.uuid4().hex[:20]}"
        cells = [dict(cell, status="pending") for cell in estimate["cells"]]
        config = {key: estimate[key] for key in estimate if key not in ("cells",)} | {"max_cost_usd": max_cost_usd}
        conn.execute(
            "INSERT INTO comparisons VALUES (?,?,?,?,?,?,?,?,?,?)",
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
            ),
        )
    finally:
        conn.close()
    kb = getattr(orchestrator, "knowledge_base", None)
    knowledge = kb.capture_active() if kb else (orchestrator.index, None)
    thread = threading.Thread(
        target=_run,
        args=(app, comparison_id, principal, config, cells, knowledge),
        name=f"comparison-{comparison_id}",
        daemon=True,
    )
    with _ACTIVE_LOCK:
        _ACTIVE[comparison_id] = thread
    thread.start()
    return comparison_id


def _run(app, comparison_id: str, principal: dict, config: dict, cells: list[dict], knowledge) -> None:
    from merchant_assistant.api import v1

    settings, orchestrator = app.state.settings, app.state.orchestrator
    failures: list[dict] = []
    spent = 0.0
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
                cell["status"] = "skipped"
            return
        profiles = {(p["profile_id"], p["profile_version"]): p for p in config["profiles"]}
        stopped = None
        per_cell = float(settings.max_request_cost_usd)
        for cell in cells:
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
                    cell["checks"] = v1.run_checks(app.state, conn, cell["request_id"], run, principal)
                _save(conn, comparison_id, cells=cells, failures=failures)
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
                )
            except v1.RunFailure as exc:
                cell.update(status="failed", error=exc.code)
                failures.append({"code": exc.code, "request_id": request_id})
                trace = orchestrator.trace(request_id)
                spent += float((trace or {}).get("cost_usd") or 0.0)
                if _budget_denied(trace):
                    stopped = "budget_denied"
                    failures.append({"code": stopped, "message": "The budget guard refused a paid call."})
            except Exception as exc:  # recorded as a failed cell, never raised from the thread
                cell.update(status="failed", error=type(exc).__name__)
                failures.append({"code": "execution_failed", "request_id": request_id})
            else:
                run = result["run"]
                spent += float(run.get("cost_estimate_usd") or 0.0)
                cell.update(status="completed", origin=run.get("execution_mode"))
                cell.update(_cell_metrics(run | {"result": result["message"]}))
                completed_run = run | {"result": result["message"]}
                cell["checks"] = v1.run_checks(app.state, conn, request_id, completed_run, principal)
                if _budget_denied(orchestrator.trace(request_id)):
                    cell.update(status="failed", error="budget_denied")
                    stopped = "budget_denied"
                    failures.append({"code": stopped, "request_id": request_id})
            _save(conn, comparison_id, cells=cells, failures=failures, cost_usd=round(spent, 8))
    except Exception as exc:  # unexpected: keep what was recorded and mark the comparison failed
        failures.append({"code": "comparison_failed", "message": type(exc).__name__})
    finally:
        completed = sum(cell.get("status") == "completed" for cell in cells)
        state = "completed" if completed == len(cells) else ("partial" if completed else "failed")
        try:
            # New cells were counted against the demo limit at the start; give back those that made no model call
            # (skipped by a knowledge-base change, the confirmed cap or a budget refusal, or refused before a call).
            # The decision uses the ledger rows of each run; when they cannot be read nothing is given back (P3-R3-01).
            unused = 0
            for cell in cells:
                if cell.get("source") != "new":
                    continue
                if not cell.get("request_id"):  # never started: certainly no model call
                    cell["model_calls"] = 0
                    unused += 1
                    continue
                cell["model_calls"] = v1.model_calls_made(orchestrator, cell["request_id"])
                if v1.paid_attempts(orchestrator.budget, cell["request_id"]) == 0:
                    unused += 1
            v1.refund_demo_messages(conn, principal, unused)
        except Exception:  # accounting never hides the comparison result
            failures.append({"code": "demo_refund_failed"})
        try:
            _save(conn, comparison_id, cells=cells, failures=failures, state=state, cost_usd=round(spent, 8))
        finally:
            conn.close()
            shutil.rmtree(workdir, ignore_errors=True)
            with _ACTIVE_LOCK:
                _ACTIVE.pop(comparison_id, None)


def _judge_view(evaluations: list[dict]) -> dict | None:
    completed = [item for item in evaluations if item["state"] == "completed"]
    return completed[-1] if completed else None


def _alive(comparison_id: str) -> bool:
    with _ACTIVE_LOCK:
        return comparison_id in _ACTIVE and _ACTIVE[comparison_id].is_alive()


def read(app_state, conn, principal: dict, comparison_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM comparisons WHERE comparison_id=? AND principal_id=?", (comparison_id, principal["principal_id"])
    ).fetchone()
    if row is None:
        raise ComparisonError(404, "not_found", "Comparison not found.")
    if row["state"] == "running" and not _alive(comparison_id):
        # The API process restarted while the thread was running. The update only applies while the row is still
        # `running`, so a thread that recorded its final state in the meantime is never overwritten (P3-01).
        cells, failures = json.loads(row["cells"]), json.loads(row["failures"])
        failures.append({"code": "interrupted", "message": "The API process stopped before the comparison ended."})
        for cell in cells:
            if cell.get("status") == "pending":
                cell.update(status="skipped", error="interrupted")
        conn.execute(
            "UPDATE comparisons SET cells=?,failures=?,state='failed',updated_at=? "
            "WHERE comparison_id=? AND state='running'",
            (json.dumps(cells), json.dumps(failures), _now(), comparison_id),
        )
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
