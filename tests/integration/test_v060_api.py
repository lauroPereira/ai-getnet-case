"""v0.6.0 contracts: scenario catalog, demo session limit, run checks, on-demand evaluation and profile comparison.

Synthetic and offline only: scripted model, hashing embedder, in-memory Qdrant and temporary SQLite databases."""

from __future__ import annotations

import json
import sqlite3

import pytest
from pydantic import SecretStr

from merchant_assistant import comparisons
from merchant_assistant.data.migrations import current_version, migrate

DEMO_KEY = "synthetic-demo-access-key-v060"
ADMIN_KEY = "synthetic-admin-access-key-v060"
DOMAIN_TABLES = ("conversations", "messages", "case_attempts", "handoff_cases", "support_cases", "audit_events")


def login(client, key=DEMO_KEY) -> dict:
    response = client.post("/v1/sessions", json={"access_key": key})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def api(settings, offline):
    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    settings.api_admin_access_key = SecretStr(ADMIN_KEY)
    client, orchestrator, llm = offline()
    return client, orchestrator, llm


def scenario(client, headers, scenario_id):
    items = client.get("/v1/scenarios", headers=headers).json()["scenarios"]
    return next(item for item in items if item["scenario_id"] == scenario_id)


def send(client, headers, message, **extra):
    payload = {"message": message, "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm"}
    return client.post("/v1/messages", headers=headers, json=payload | extra)


def counts(path) -> dict:
    conn = sqlite3.connect(path)
    try:
        return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in DOMAIN_TABLES}
    finally:
        conn.close()


# --- catalog and scenario_id ---------------------------------------------------------------------------------------


def test_scenario_catalog_requires_a_session_and_lists_labeled_scenarios(api):
    client, _, _ = api
    assert client.get("/v1/scenarios").status_code == 401
    body = client.get("/v1/scenarios", headers=login(client)).json()
    ids = [item["scenario_id"] for item in body["scenarios"]]
    assert body["version"] == "1" and len(ids) == 10 and len(set(ids)) == len(ids)
    journeys = {item["journey"] for item in body["scenarios"]}
    assert journeys >= {"knowledge", "receivables", "device", "authorization", "pricing", "enablement"}
    assert journeys >= {"cancellation", "handoff", "safety", "doc_effect"}  # P3-08: every essential journey
    assert "SC-DOC-EFFECT" in ids and "SC-HANDOFF" in ids and "SC-INJECTION" in ids
    assert all("route_ok" in item["checks"] and item["message"] for item in body["scenarios"])


def test_scenario_id_is_validated_and_recorded_in_the_run(api):
    client, _, _ = api
    headers = login(client)
    item = scenario(client, headers, "SC-RECEIVABLES")
    assert send(client, headers, item["message"], scenario_id="SC-UNKNOWN").json()["error"]["code"] == (
        "unknown_scenario"
    )
    mismatch = send(client, headers, "Outra pergunta qualquer", scenario_id="SC-RECEIVABLES")
    assert mismatch.status_code == 422 and mismatch.json()["error"]["code"] == "scenario_message_mismatch"
    sent = send(client, headers, item["message"], scenario_id="SC-RECEIVABLES")
    assert sent.status_code == 200
    run = client.get(f"/v1/runs/{sent.json()['message']['request_id']}", headers=headers).json()
    assert run["scenario_id"] == "SC-RECEIVABLES" and run["purpose"] == "attendance"
    assert run["checks"]["origin"] == "scenario:SC-RECEIVABLES"
    assert run["checks"]["results"]["tools_ok"] is True and run["checks"]["not_evaluated"] == []
    assert run["route"] == sent.json()["message"]["route"]
    assert any(step["step"] == "router" for step in run["steps"])
    assert any(step["step"].startswith("tool:") for step in run["steps"])
    assert run["prompts_used"] and run["evaluations"] == []


def test_free_message_only_gets_label_independent_checks(api):
    client, _, _ = api
    headers = login(client)
    sent = send(client, headers, "Minha maquininha não conecta na internet, o que eu faço?")
    run = client.get(f"/v1/runs/{sent.json()['message']['request_id']}", headers=headers).json()
    checks = run["checks"]
    assert checks["origin"] == "label_independent"
    assert set(checks["results"]) == {"grounded_ok", "errors_ok", "isolation_ok"}
    assert "route_ok" in checks["not_evaluated"] and "tools_ok" in checks["not_evaluated"]
    knowledge = next(step for step in run["steps"] if step["step"] == "knowledge")
    assert knowledge["hits"] and all(hit["chunk_id"] and hit["excerpt"] for hit in knowledge["hits"])


def test_persisted_checks_list_critical_failures_individually():
    from merchant_assistant.evaluation.runner import Case, persisted_checks

    case = Case("X", "demo", "q", "pt", ["support"], "answered", [], [], [], False, must_not_include=["garantido"])
    body = {
        "answer": "Reembolso garantido para Loja Demo 002",
        "route": "support",
        "status": "refused",
        "language": "pt",
    }
    body["sources"] = []
    trace = {"steps": [], "errors": [], "detail": {"output_violations": ["unsupported_amount"]}}
    result = persisted_checks(body, trace, case, foreign_markers=["Loja Demo 002"])
    codes = [item["code"] for item in result["critical_failures"]]
    assert codes == ["unsupported_answer", "forbidden_assertion_or_promise", "cross_customer_leak", "undue_refusal"]
    unlabeled = persisted_checks(body, trace, None, foreign_markers=[])
    assert [item["code"] for item in unlabeled["critical_failures"]] == ["unsupported_answer"]
    assert persisted_checks(None, None, None)["status"] == "unavailable"


# --- demo session message limit ---


def test_demo_session_limit_is_enforced_by_the_backend(settings, api):
    client, _, llm = api
    settings.demo_session_message_limit = 2
    demo = login(client)
    assert send(client, demo, "Olá, preciso de ajuda.").status_code == 200
    assert send(client, demo, "Olá, preciso de ajuda.").status_code == 200
    calls = len(llm.calls)
    refused = send(client, demo, "Olá, preciso de ajuda.")
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "demo_message_limit_reached"
    assert "new one" in refused.json()["error"]["message"]
    assert len(llm.calls) == calls  # refused before any model call
    admin = login(client, ADMIN_KEY)
    for _ in range(3):
        assert send(client, admin, "Olá, preciso de ajuda.").status_code == 200
    assert send(client, login(client), "Olá, preciso de ajuda.").status_code == 200  # a new session starts at zero


# --- on-demand evaluation ---


def _evaluate(client, headers, request_id, **extra):
    estimate = client.post(f"/v1/runs/{request_id}/evaluations/estimate", headers=headers)
    assert estimate.status_code == 200
    body = estimate.json()
    payload = {
        "confirmed": True,
        "max_cost_usd": body["estimated_cost_usd"],
        "expected_estimate_digest": body["estimate_digest"],
    }
    return body, client.post(f"/v1/runs/{request_id}/evaluations", headers=headers, json=payload | extra)


def test_evaluation_grades_the_persisted_reply_once_and_repeats_only_on_request(api):
    client, orchestrator, llm = api
    headers = login(client)
    item = scenario(client, headers, "SC-HANDOFF")
    sent = send(client, headers, item["message"], scenario_id="SC-HANDOFF").json()
    request_id = sent["message"]["request_id"]
    attendance_calls = [call.spec.agent for call in llm.calls]

    estimate = client.post(f"/v1/runs/{request_id}/evaluations/estimate", headers=headers).json()
    assert [call.spec.agent for call in llm.calls] == attendance_calls  # estimating made no call
    estimate, created = _evaluate(client, headers, request_id)
    assert estimate["method"] == "model" and estimate["rubric"] == "judge" and estimate["rubric_version"] == "2"
    assert estimate["evaluator"] == {
        "provider": "openai",
        "model": "gpt-6-luna",
        "parameters": {"max_output_tokens": 200, "effort": "none"},
    }
    assert estimate["estimated_cost_usd"] > 0 and estimate["existing_evaluation_id"] is None
    assert created.status_code == 201
    evaluation = created.json()
    assert evaluation["state"] == "completed" and evaluation["reused"] is False
    assert set(evaluation["result"]) == {"answers_question", "clarity_and_tone", "honesty", "comment"}
    assert evaluation["evidence"]["reply"] == sent["message"]["answer"]
    assert evaluation["evidence"]["merchant_message"] == item["message"]
    assert evaluation["cost_scope"].startswith("evaluation")
    judge_calls = [call for call in llm.calls if call.spec.agent == "judge"]
    assert len(judge_calls) == 1 and len(llm.calls) == len(attendance_calls) + 1  # no attendance was repeated

    estimate_again, reused = _evaluate(client, headers, request_id)
    assert estimate_again["existing_evaluation_id"] == evaluation["evaluation_id"]
    assert reused.status_code == 200 and reused.json()["reused"] is True
    assert reused.json()["evaluation_id"] == evaluation["evaluation_id"]
    assert len([call for call in llm.calls if call.spec.agent == "judge"]) == 1

    _, repeated = _evaluate(client, headers, request_id, repeat=True)
    assert repeated.status_code == 201 and repeated.json()["evaluation_id"] != evaluation["evaluation_id"]
    run = client.get(f"/v1/runs/{request_id}", headers=headers).json()
    assert [item["evaluation_id"] for item in run["evaluations"]] == [
        evaluation["evaluation_id"],
        repeated.json()["evaluation_id"],
    ]
    ledger = sqlite3.connect(orchestrator.budget.path)
    judge_rows = ledger.execute("SELECT request_id,status FROM ledger WHERE agent='judge'").fetchall()
    ledger.close()
    assert judge_rows == [(f"eval:{request_id}", "settled")] * 2


def test_evaluation_requires_confirmation_fresh_estimate_ownership_and_budget(settings, api, monkeypatch):
    from merchant_assistant.orchestration.budget import BudgetExceeded

    client, orchestrator, llm = api
    demo = login(client)
    request_id = send(client, demo, "Olá, preciso de ajuda.").json()["message"]["request_id"]
    estimate = client.post(f"/v1/runs/{request_id}/evaluations/estimate", headers=demo).json()
    base = {"max_cost_usd": 1.0, "expected_estimate_digest": estimate["estimate_digest"]}
    assert (
        client.post(f"/v1/runs/{request_id}/evaluations", headers=demo, json=base | {"confirmed": False}).json()[
            "error"
        ]["code"]
        == "confirmation_required"
    )
    stale = client.post(
        f"/v1/runs/{request_id}/evaluations",
        headers=demo,
        json=base | {"confirmed": True, "expected_estimate_digest": "stale"},
    )
    assert stale.status_code == 409
    low = client.post(
        f"/v1/runs/{request_id}/evaluations", headers=demo, json=base | {"confirmed": True, "max_cost_usd": 0.0}
    )
    assert low.status_code == 422 and low.json()["error"]["code"] == "max_cost_below_estimate"
    admin = login(client, ADMIN_KEY)
    assert client.post(f"/v1/runs/{request_id}/evaluations/estimate", headers=admin).status_code == 404

    def refuse(**_kwargs):
        raise BudgetExceeded("installation", 1, 0)

    monkeypatch.setattr(orchestrator.budget, "reserve", refuse)
    denied = client.post(f"/v1/runs/{request_id}/evaluations", headers=demo, json=base | {"confirmed": True})
    assert denied.status_code == 429
    assert not [call for call in llm.calls if call.spec.agent == "judge"]
    assert client.get(f"/v1/runs/{request_id}", headers=demo).json()["evaluations"] == []


def test_unknown_evaluator_price_blocks_the_estimate(settings, api):
    client, _, _ = api
    settings.evaluator_model = "unpriced-model"
    demo = login(client)
    request_id = send(client, demo, "Olá, preciso de ajuda.").json()["message"]["request_id"]
    response = client.post(f"/v1/runs/{request_id}/evaluations/estimate", headers=demo)
    assert response.status_code == 503 and response.json()["error"]["code"] == "evaluator_price_unknown"


def test_failed_evaluation_is_recorded_without_inventing_scores(api):
    client, _, llm = api
    demo = login(client)
    request_id = send(client, demo, "Olá, preciso de ajuda.").json()["message"]["request_id"]
    original = llm.handler
    llm.handler = lambda call: ValueError("bad judge output") if call.spec.agent == "judge" else original(call)
    _, failed = _evaluate(client, demo, request_id)
    assert failed.status_code == 503 and failed.json()["error"]["code"] == "evaluation_failed"
    evaluations = client.get(f"/v1/runs/{request_id}", headers=demo).json()["evaluations"]
    assert len(evaluations) == 1 and evaluations[0]["state"] == "failed" and evaluations[0]["result"] == {}


# --- profile comparison ---


def _selection(**extra):
    return {
        "profiles": [{"profile_id": "reference", "profile_version": 1}, {"profile_id": "hybrid", "profile_version": 1}],
        "scenario_ids": ["SC-RECEIVABLES", "SC-HANDOFF"],
        "repetitions": 1,
        "router_mechanism": "llm",
    } | extra


def _run_comparison(client, headers, selection):
    estimate = client.post("/v1/comparisons/estimate", headers=headers, json=selection)
    assert estimate.status_code == 200, estimate.json()
    body = estimate.json()
    created = client.post(
        "/v1/comparisons",
        headers=headers,
        json=selection
        | {
            "confirmed": True,
            "max_cost_usd": body["estimated_cost_usd"],
            "expected_estimate_digest": body["estimate_digest"],
        },
    )
    assert created.status_code == 202, created.json()
    comparison_id = created.json()["comparison_id"]
    thread = comparisons._ACTIVE.get(comparison_id)
    if thread:
        thread.join(timeout=60)
    return body, client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()


def test_comparison_limits_and_estimate_have_no_side_effects(settings, api):
    client, orchestrator, llm = api
    headers = login(client)
    one = {"profiles": [{"profile_id": "reference", "profile_version": 1}]}
    assert client.post("/v1/comparisons/estimate", headers=headers, json=_selection(**one)).status_code == 422
    four = _selection(scenario_ids=["SC-RECEIVABLES", "SC-HANDOFF", "SC-DEVICE", "SC-DECLINE"])
    assert client.post("/v1/comparisons/estimate", headers=headers, json=four).status_code == 422
    assert client.post("/v1/comparisons/estimate", headers=headers, json=_selection(repetitions=3)).status_code == 422
    same = _selection(profiles=[{"profile_id": "reference", "profile_version": 1}] * 2)
    assert client.post("/v1/comparisons/estimate", headers=headers, json=same).json()["error"]["code"] == (
        "invalid_selection"
    )
    unknown = client.post("/v1/comparisons/estimate", headers=headers, json=_selection(scenario_ids=["SC-NOPE"]))
    assert unknown.json()["error"]["code"] == "unknown_scenario"
    estimate = client.post(
        "/v1/comparisons/estimate",
        headers=headers,
        json=_selection(
            profiles=[
                {"profile_id": "reference", "profile_version": 1},
                {"profile_id": "hybrid", "profile_version": 1},
                {"profile_id": "adjusted", "profile_version": 1},
            ],
            scenario_ids=["SC-RECEIVABLES", "SC-HANDOFF", "SC-DEVICE"],
            repetitions=2,
        ),
    ).json()
    assert estimate["sample_size"] == 18 and estimate["new_executions"] == 18
    assert estimate["estimated_cost_usd"] == pytest.approx(18 * settings.max_request_cost_usd)
    assert estimate["exploratory"] is True  # Reference and Adjusted differ in two agents
    assert estimate["fixed_factors"]["knowledge_base_version_id"] == "kb_initial"
    assert llm.calls == [] and orchestrator.budget.spent() == 0
    conn = sqlite3.connect(settings.db_path)
    assert conn.execute("SELECT COUNT(*) FROM comparisons").fetchone()[0] == 0
    conn.close()


def test_comparison_runs_outside_the_request_isolated_and_traceable(settings, api):
    client, orchestrator, _ = api
    headers = login(client)
    before = counts(settings.db_path)
    estimate, comparison = _run_comparison(client, headers, _selection())
    assert estimate["exploratory"] is False and estimate["new_executions"] == 4
    assert comparison["state"] == "completed", comparison["failures"]
    assert counts(settings.db_path) == before  # nothing created in the original attendance data
    cells = comparison["cells"]
    assert len(cells) == 4 and all(cell["status"] == "completed" and cell["origin"] == "simulated" for cell in cells)
    for cell in cells:
        run = client.get(f"/v1/runs/{cell['request_id']}", headers=headers).json()
        assert run["purpose"] == "comparison" and run["profile_comparison_id"] == comparison["comparison_id"]
        assert run["knowledge_base_version_id"] == "kb_initial"
        trace = orchestrator.trace(cell["request_id"])
        assert trace["detail"]["purpose"] == "comparison"
        assert trace["detail"]["profile_comparison_id"] == comparison["comparison_id"]
    profiles = comparison["aggregates"]["profiles"]
    assert [item["sample_size"] for item in profiles] == [2, 2]
    assert all(item["deterministic_quality"] is not None for item in profiles)
    assert all(item["model_quality"] is None and item["model_quality_status"] == "not_evaluated" for item in profiles)
    bars = comparison["aggregates"]["cost_by_agent_model"]
    assert bars and all(set(bar["request_ids"]) <= {cell["request_id"] for cell in cells} for bar in bars)

    again, second = _run_comparison(client, headers, _selection())
    assert again["new_executions"] == 0 and again["reused_executions"] == 4 and again["estimated_cost_usd"] == 0
    assert all(cell["origin"] == "recorded" for cell in second["cells"])
    assert {cell["request_id"] for cell in second["cells"]} == {cell["request_id"] for cell in cells}


def test_model_quality_appears_only_when_every_run_of_a_profile_was_judged(api):
    client, _, _ = api
    headers = login(client)
    _, comparison = _run_comparison(client, headers, _selection())
    reference = [cell for cell in comparison["cells"] if cell["profile_id"] == "reference"]
    _evaluate(client, headers, reference[0]["request_id"])
    partial = client.get(f"/v1/comparisons/{comparison['comparison_id']}", headers=headers).json()
    assert partial["aggregates"]["profiles"][0]["model_quality"] is None
    _evaluate(client, headers, reference[1]["request_id"])
    full = client.get(f"/v1/comparisons/{comparison['comparison_id']}", headers=headers).json()
    assert full["aggregates"]["profiles"][0]["model_quality"] == {
        "answers_question": 4.0,
        "clarity_and_tone": 4.0,
        "honesty": 4.0,
    }
    assert full["aggregates"]["profiles"][1]["model_quality_status"] == "not_evaluated"


def test_budget_denial_stops_the_remaining_cells_and_is_recorded(settings, api, monkeypatch):
    from merchant_assistant.orchestration.budget import BudgetExceeded

    client, orchestrator, _ = api
    headers = login(client)
    original = orchestrator.budget.reserve
    calls = {"n": 0}

    def reserve(**kwargs):
        calls["n"] += 1
        if calls["n"] > 3:
            raise BudgetExceeded("installation", kwargs["amount"], 0)
        return original(**kwargs)

    monkeypatch.setattr(orchestrator.budget, "reserve", reserve)
    _, comparison = _run_comparison(client, headers, _selection())
    assert comparison["state"] in ("partial", "failed")
    assert any(item["code"] == "budget_denied" for item in comparison["failures"])
    statuses = [cell["status"] for cell in comparison["cells"]]
    assert "skipped" in statuses and statuses[0] in ("completed", "failed")


def test_comparison_requires_confirmation_and_fresh_estimate_and_lost_threads_fail(settings, api):
    client, _, llm = api
    headers = login(client)
    estimate = client.post("/v1/comparisons/estimate", headers=headers, json=_selection()).json()
    base = _selection() | {"max_cost_usd": 1.0, "expected_estimate_digest": estimate["estimate_digest"]}
    assert client.post("/v1/comparisons", headers=headers, json=base | {"confirmed": False}).status_code == 422
    stale = client.post(
        "/v1/comparisons", headers=headers, json=base | {"confirmed": True, "expected_estimate_digest": "x"}
    )
    assert stale.status_code == 409
    low = client.post("/v1/comparisons", headers=headers, json=base | {"confirmed": True, "max_cost_usd": 0.0})
    assert low.json()["error"]["code"] == "max_cost_below_estimate"
    assert llm.calls == []
    conn = sqlite3.connect(settings.db_path)
    conn.execute(
        "INSERT INTO comparisons VALUES ('pcmp_lost000000000000','demo:default','running','{\"profiles\": []}',"
        "'[{\"status\": \"pending\", \"profile_id\": \"reference\", \"profile_version\": 1}]','[]','{}',0,'t','t')"
    )
    conn.commit()
    conn.close()
    lost = client.get("/v1/comparisons/pcmp_lost000000000000", headers=headers).json()
    assert lost["state"] == "failed" and lost["failures"][-1]["code"] == "interrupted"
    assert client.get("/v1/comparisons/pcmp_lost000000000000", headers=login(client, ADMIN_KEY)).status_code == 404


def test_demo_comparison_new_executions_count_against_the_session_limit(settings, api):
    client, _, llm = api
    settings.demo_session_message_limit = 3
    headers = login(client)
    estimate = client.post("/v1/comparisons/estimate", headers=headers, json=_selection()).json()
    refused = client.post(
        "/v1/comparisons",
        headers=headers,
        json=_selection()
        | {"confirmed": True, "max_cost_usd": 1.0, "expected_estimate_digest": estimate["estimate_digest"]},
    )
    assert refused.status_code == 429 and refused.json()["error"]["code"] == "demo_message_limit_reached"
    assert llm.calls == []


# --- migration 0008 ---


def test_migration_0008_round_trip_on_a_synthetic_database(settings, api):
    client, _, _ = api
    headers = login(client)
    send(client, headers, "Olá, preciso de ajuda.")
    conn = sqlite3.connect(settings.db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    snapshots = conn.execute("SELECT * FROM run_snapshots").fetchall()
    sessions = conn.execute("SELECT session_id, principal_id FROM api_sessions").fetchall()
    assert current_version(conn) == 8
    assert migrate(conn, 7) == ["down 0008_demo_results"]
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "run_evaluations" not in tables and "comparisons" not in tables
    columns = [row[1] for row in conn.execute("PRAGMA table_info(api_sessions)")]
    assert "message_count" not in columns
    assert [tuple(row) for row in conn.execute("SELECT session_id, principal_id FROM api_sessions")] == [
        tuple(row) for row in sessions
    ]
    assert [tuple(row) for row in conn.execute("SELECT * FROM run_snapshots")] == [tuple(row) for row in snapshots]
    assert migrate(conn, 8) == ["up 0008_demo_results"]
    assert [tuple(row) for row in conn.execute("SELECT DISTINCT message_count FROM api_sessions")] == [(0,)]
    assert json.loads(conn.execute("SELECT snapshot FROM run_snapshots").fetchone()[0])["purpose"] == "attendance"
    conn.close()


def test_evaluation_of_a_run_stored_before_v060_uses_the_conversation_text(settings, api):
    client, _, _ = api
    headers = login(client)
    request_id = send(client, headers, "Olá, preciso de ajuda.").json()["message"]["request_id"]
    conn = sqlite3.connect(settings.db_path)
    snapshot = json.loads(conn.execute("SELECT snapshot FROM run_snapshots").fetchone()[0])
    for key in ("message", "scenario_id", "purpose", "prompt_set"):
        snapshot.pop(key)
    conn.execute("UPDATE run_snapshots SET snapshot=?", (json.dumps(snapshot),))
    conn.commit()
    conn.close()
    run = client.get(f"/v1/runs/{request_id}", headers=headers).json()
    assert run["checks"]["origin"] == "label_independent"
    _, created = _evaluate(client, headers, request_id)
    assert created.status_code == 201
    assert created.json()["evidence"]["merchant_message"] == "Olá, preciso de ajuda."
