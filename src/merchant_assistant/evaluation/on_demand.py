"""On-demand model evaluation of a persisted run (v0.6.0, RF-77).

No new agent and no new attendance: the existing `judge` rubric and `JudgeScore` grade the reply that was already
stored in the run snapshot. The evaluator configuration is fixed by the backend settings (not by the evaluated
profile) and recorded with every evaluation; the paid call is estimated, confirmed, reserved and settled under the
persistent budget guard, and its cost is kept apart from the attendance cost."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

from merchant_assistant.evaluation.runner import (
    JUDGE_MAX_OUTPUT_TOKENS,
    BudgetMeter,
    JudgeScore,
    judge_evidence,
    judge_spec,
)
from merchant_assistant.llm import pricing
from merchant_assistant.llm.base import estimate_tokens
from merchant_assistant.llm.prompts import load_prompt
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.profiles import digest

METHOD = "model"
RUBRIC = "judge"
STALE_RUNNING_SECONDS = 600


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def evaluator_config(settings) -> dict:
    return {
        "provider": settings.evaluator_provider,
        "model": settings.evaluator_model,
        "parameters": {"max_output_tokens": JUDGE_MAX_OUTPUT_TOKENS, "effort": "none"},
    }


def _evidence(conn, request_id: str, snapshot: dict) -> dict:
    body = snapshot["result"]
    message = snapshot.get("message")
    if message is None:  # runs stored before v0.6.0 keep the (masked) merchant text only in the conversation
        row = conn.execute(
            "SELECT text FROM messages WHERE request_id=? AND role='merchant' ORDER BY id LIMIT 1", (request_id,)
        ).fetchone()
        message = row["text"] if row else ""
    return judge_evidence(message, body, [source["title"] for source in body.get("sources", [])])


def _row(row) -> dict:
    return {
        "evaluation_id": row["evaluation_id"],
        "request_id": row["request_id"],
        "method": row["method"],
        "rubric": row["rubric"],
        "rubric_version": row["rubric_version"],
        "evaluator": json.loads(row["evaluator"]),
        "config_digest": row["config_digest"],
        "result": json.loads(row["result"]),
        "evidence": json.loads(row["evidence"]),
        "critical_failures": json.loads(row["critical_failures"]),
        "cost_usd": row["cost_usd"],
        "cost_is_estimate": True,
        "cost_scope": "evaluation (separate from the attendance cost)",
        "state": row["state"],
        "error": row["error"],
        "created_at": row["created_at"],
    }


def list_for(conn, request_id: str, principal_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM run_evaluations WHERE request_id=? AND principal_id=? ORDER BY created_at, rowid",
        (request_id, principal_id),
    ).fetchall()
    return [_row(row) for row in rows]


def estimate(app_state, conn, request_id: str, snapshot: dict, principal: dict) -> dict:
    """No paid call: price of one judge call over the persisted reply, plus any reusable evaluation."""
    settings = app_state.settings
    prompt = load_prompt(settings.prompts_dir, RUBRIC)
    evaluator = evaluator_config(settings)
    evidence = _evidence(conn, request_id, snapshot)
    spec = judge_spec(prompt, evidence)
    tokens = estimate_tokens(spec.instructions, spec.input)
    cost = pricing.estimate(evaluator["model"], tokens, JUDGE_MAX_OUTPUT_TOKENS)  # unknown price raises
    config_digest = digest({"request_id": request_id, "rubric_version": prompt.version, **evaluator})
    existing = next(
        (
            item
            for item in reversed(list_for(conn, request_id, principal["principal_id"]))
            if item["state"] == "completed" and item["config_digest"] == config_digest
        ),
        None,
    )
    body = {
        "request_id": request_id,
        "method": METHOD,
        "rubric": RUBRIC,
        "rubric_version": prompt.version,
        "evaluator": evaluator,
        "evidence_fields": sorted(evidence),
        "estimated_input_tokens": tokens,
        "estimated_cost_usd": cost,
        "estimate_basis": "catalog rate, conservative token estimate, one call",
        "existing_evaluation_id": existing["evaluation_id"] if existing else None,
        "repeat_required_for_new_call": existing is not None,
        "config_digest": config_digest,
    }
    body["estimate_digest"] = digest({k: body[k] for k in ("config_digest", "estimated_cost_usd", "evidence_fields")})
    return body


def evaluate(
    app_state,
    conn,
    request_id: str,
    snapshot: dict,
    principal: dict,
    *,
    confirmed: bool,
    max_cost_usd: float,
    expected_digest: str,
    repeat: bool,
) -> tuple[int, dict]:
    from merchant_assistant.api.v1 import DEMO_LIMIT_MESSAGE, consume_demo_messages, refund_demo_messages, run_checks

    if not confirmed:
        return 422, {"code": "confirmation_required", "message": "Explicit confirmation is required."}
    current = estimate(app_state, conn, request_id, snapshot, principal)
    if current["estimate_digest"] != expected_digest:
        return 409, {"code": "estimate_stale", "message": "The estimate changed; estimate again before confirming."}
    if current["existing_evaluation_id"] and not repeat:
        existing = next(
            item
            for item in list_for(conn, request_id, principal["principal_id"])
            if item["evaluation_id"] == current["existing_evaluation_id"]
        )
        return 200, existing | {"reused": True}
    if max_cost_usd < current["estimated_cost_usd"]:
        return 422, {"code": "max_cost_below_estimate", "message": "The confirmed cap is below the estimate."}
    orchestrator = app_state.orchestrator
    evaluator = current["evaluator"]
    try:
        llm = orchestrator._profile_llm("evaluation", {"provider": evaluator["provider"], "model": evaluator["model"]})
    except RuntimeError:
        return 503, {"code": "evaluator_unavailable", "message": "The configured evaluator is not available."}
    prompt = load_prompt(app_state.settings.prompts_dir, RUBRIC)
    evidence = _evidence(conn, request_id, snapshot)
    meter = BudgetMeter(orchestrator.budget, request_id=f"eval:{request_id}", max_cost_usd=max_cost_usd)
    checks = run_checks(app_state, conn, request_id, snapshot, principal)
    evaluation_id = f"eval_{uuid.uuid4().hex[:20]}"
    evaluator_record = evaluator | {"model_used": getattr(llm, "model", evaluator["model"])}

    # Atomic claim (P3-02): one `running` row per run and configuration, created in the same write transaction that
    # checks for a completed or running one, so two simultaneous requests can never both reach the paid call.
    conn.execute("BEGIN IMMEDIATE")
    try:
        _expire_stale(conn, request_id, current["config_digest"])
        claim = conn.execute(
            "SELECT evaluation_id,state FROM run_evaluations WHERE request_id=? AND principal_id=? AND config_digest=? "
            "AND state IN ('running','completed') ORDER BY created_at DESC, rowid DESC",
            (request_id, principal["principal_id"], current["config_digest"]),
        ).fetchall()
        if any(row["state"] == "running" for row in claim):
            conn.execute("ROLLBACK")
            return 409, {
                "code": "evaluation_running",
                "message": "An evaluation with this configuration is already running; refresh the run (GET).",
            }
        if claim and not repeat:
            conn.execute("ROLLBACK")
            existing = next(
                item
                for item in list_for(conn, request_id, principal["principal_id"])
                if item["evaluation_id"] == claim[0][0]
            )
            return 200, existing | {"reused": True}
        if not consume_demo_messages(conn, principal, 1, app_state.settings):
            conn.execute("ROLLBACK")
            return 429, {"code": "demo_message_limit_reached", "message": DEMO_LIMIT_MESSAGE}
        conn.execute(
            "INSERT INTO run_evaluations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                evaluation_id,
                request_id,
                principal["principal_id"],
                METHOD,
                RUBRIC,
                prompt.version,
                json.dumps(evaluator_record, sort_keys=True),
                current["config_digest"],
                "{}",
                json.dumps(evidence, sort_keys=True, ensure_ascii=False),
                json.dumps(checks["critical_failures"], sort_keys=True),
                None,
                "running",
                None,
                _now(),
            ),
        )
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise

    try:
        score = llm.parse(judge_spec(prompt, evidence), JudgeScore, meter)
    except BudgetExceeded:
        conn.execute("DELETE FROM run_evaluations WHERE evaluation_id=? AND state='running'", (evaluation_id,))
        refund_demo_messages(conn, principal, 1)
        return 429, {
            "code": "budget_exceeded",
            "message": "The evaluation was blocked by the budget before any call; nothing was recorded.",
        }
    except Exception as exc:  # provider or validation failure: recorded as a failed evaluation with its cost
        result, state, error = {}, "failed", type(exc).__name__
    else:
        result, state, error = score.value.model_dump(), "completed", None
        evaluator_record["model_used"] = score.model
    conn.execute(
        "UPDATE run_evaluations SET result=?,evaluator=?,cost_usd=?,state=?,error=? WHERE evaluation_id=?",
        (
            json.dumps(result, sort_keys=True),
            json.dumps(evaluator_record, sort_keys=True),
            round(meter.cost_usd, 8),
            state,
            error,
            evaluation_id,
        ),
    )
    saved = next(
        item for item in list_for(conn, request_id, principal["principal_id"]) if item["evaluation_id"] == evaluation_id
    )
    if saved["state"] == "failed":
        return 503, {
            "code": "evaluation_failed",
            "message": f"The evaluator failed; the attempt {saved['evaluation_id']} was recorded. Try again later.",
        }
    return 201, saved | {"reused": False}


def _expire_stale(conn, request_id: str, config_digest: str) -> None:
    """A `running` claim left by a stopped process is closed as failed after STALE_RUNNING_SECONDS."""
    cutoff = (datetime.now(UTC) - timedelta(seconds=STALE_RUNNING_SECONDS)).isoformat(timespec="seconds")
    conn.execute(
        "UPDATE run_evaluations SET state='failed',error='interrupted' "
        "WHERE request_id=? AND config_digest=? AND state='running' AND created_at<?",
        (request_id, config_digest, cutoff),
    )
