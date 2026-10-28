"""v0.6.0 review r1 corrections (task 60): P3-01, P3-02, P3-03, P3-06 and P3-09 (a, c).

Synthetic and offline only: scripted model, hashing embedder, in-memory Qdrant and temporary SQLite databases."""

from __future__ import annotations

import json
import sqlite3
import threading

import pytest
from pydantic import SecretStr

from merchant_assistant import comparisons
from merchant_assistant.orchestration.budget import BudgetExceeded

DEMO_KEY = "synthetic-demo-access-key-v060-r2"
ADMIN_KEY = "synthetic-admin-access-key-v060-r2"


@pytest.fixture
def api(settings, offline):
    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    settings.api_admin_access_key = SecretStr(ADMIN_KEY)
    return offline()


def login(client, key=DEMO_KEY) -> dict:
    return {"Authorization": f"Bearer {client.post('/v1/sessions', json={'access_key': key}).json()['access_token']}"}


def send(client, headers, message="Olá, preciso de ajuda.", **extra):
    payload = {"message": message, "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm"}
    return client.post("/v1/messages", headers=headers, json=payload | extra)


def evaluate(client, headers, request_id, **extra):
    estimate = client.post(f"/v1/runs/{request_id}/evaluations/estimate", headers=headers).json()
    body = {
        "confirmed": True,
        "max_cost_usd": estimate["estimated_cost_usd"],
        "expected_estimate_digest": estimate["estimate_digest"],
    }
    return client.post(f"/v1/runs/{request_id}/evaluations", headers=headers, json=body | extra)


def compare_routers(client, headers):
    payload = {"message": "My card machine won't connect", "profile_id": "hybrid", "profile_version": 1}
    return client.post("/v1/router/compare", headers=headers, json=payload | {"selected_mechanism": "jev"})


def run_comparison(client, headers, selection):
    estimate = client.post("/v1/comparisons/estimate", headers=headers, json=selection).json()
    created = client.post(
        "/v1/comparisons",
        headers=headers,
        json=selection
        | {
            "confirmed": True,
            "max_cost_usd": estimate["estimated_cost_usd"],
            "expected_estimate_digest": estimate["estimate_digest"],
        },
    )
    assert created.status_code == 202, created.json()
    comparison_id = created.json()["comparison_id"]
    comparisons._ACTIVE[comparison_id].join(timeout=60)
    return client.get(f"/v1/comparisons/{comparison_id}", headers=headers).json()


SELECTION = {
    "profiles": [{"profile_id": "reference", "profile_version": 1}, {"profile_id": "hybrid", "profile_version": 1}],
    "scenario_ids": ["SC-HANDOFF"],
    "repetitions": 1,
    "router_mechanism": "llm",
}


# --- P3-01: reading never overwrites a final state recorded at the same time ---------------------------------------


def test_reading_a_comparison_never_overwrites_a_final_state_written_concurrently(settings, api, monkeypatch):
    client, _, _ = api
    headers = login(client)
    conn = sqlite3.connect(settings.db_path)
    conn.execute(
        "INSERT INTO comparisons VALUES ('pcmp_race00000000000000','demo:default','running','{\"profiles\": []}',"
        "'[{\"status\": \"pending\", \"profile_id\": \"reference\", \"profile_version\": 1}]','[]','{}',0,'t','t')"
    )
    conn.commit()
    conn.close()

    def thread_finishes_now(comparison_id):  # the thread records its final state between the read and the check
        writer = sqlite3.connect(settings.db_path)
        writer.execute(
            "UPDATE comparisons SET state='completed',cells=? WHERE comparison_id=?",
            (json.dumps([{"status": "completed", "profile_id": "reference", "profile_version": 1}]), comparison_id),
        )
        writer.commit()
        writer.close()
        return False

    monkeypatch.setattr(comparisons, "_alive", thread_finishes_now)
    body = client.get("/v1/comparisons/pcmp_race00000000000000", headers=headers).json()
    assert body["state"] == "completed" and body["failures"] == []
    assert body["cells"][0]["status"] == "completed"
    conn = sqlite3.connect(settings.db_path)
    assert conn.execute("SELECT state FROM comparisons").fetchone()[0] == "completed"
    conn.close()


# --- P3-02: simultaneous evaluations with the same configuration make one paid call ---------------------------------


def test_simultaneous_evaluations_with_the_same_configuration_call_the_judge_once(api):
    client, _, llm = api
    headers = login(client)
    request_id = send(client, headers).json()["message"]["request_id"]
    started, release = threading.Event(), threading.Event()
    original = llm.handler

    def slow_judge(call):
        if call.spec.agent == "judge":
            started.set()
            release.wait(timeout=30)
        return original(call)

    llm.handler = slow_judge
    first: dict = {}
    worker = threading.Thread(target=lambda: first.update(response=evaluate(client, headers, request_id)))
    worker.start()
    assert started.wait(timeout=30)
    second = evaluate(client, headers, request_id)
    repeated = evaluate(client, headers, request_id, repeat=True)
    release.set()
    worker.join(timeout=30)
    assert first["response"].status_code == 201
    assert second.status_code == 409 and second.json()["error"]["code"] == "evaluation_running"
    assert repeated.status_code == 409  # an explicit repeat also waits for the running one
    assert len([call for call in llm.calls if call.spec.agent == "judge"]) == 1
    evaluations = client.get(f"/v1/runs/{request_id}", headers=headers).json()["evaluations"]
    assert [item["state"] for item in evaluations] == ["completed"]


def test_a_running_claim_left_by_a_stopped_process_expires(settings, api):
    client, _, llm = api
    headers = login(client)
    request_id = send(client, headers).json()["message"]["request_id"]
    estimate = client.post(f"/v1/runs/{request_id}/evaluations/estimate", headers=headers).json()
    conn = sqlite3.connect(settings.db_path)
    conn.execute(
        "INSERT INTO run_evaluations VALUES ('eval_stale','" + request_id + "','demo:default','model','judge','2',"
        "'{}',?,'{}','{}','[]',NULL,'running',NULL,'2000-01-01T00:00:00+00:00')",
        (estimate["config_digest"],),
    )
    conn.commit()
    conn.close()
    assert evaluate(client, headers, request_id).status_code == 201
    states = {
        item["evaluation_id"]: item["state"]
        for item in client.get(f"/v1/runs/{request_id}", headers=headers).json()["evaluations"]
    }
    assert states.pop("eval_stale") == "failed" and list(states.values()) == ["completed"]


# --- P3-03: the demo limit counts every paid action and only paid actions -------------------------------------------


def test_stale_router_comparison_does_not_consume_the_demo_limit(settings, api):
    client, _, llm = api
    settings.demo_session_message_limit = 1
    headers = login(client)
    stale = send(client, headers, comparison_id="cmp_doesnotexist")
    assert stale.status_code == 409 and llm.calls == []
    assert send(client, headers).status_code == 200  # the refused attempt did not use the only allowed action
    assert send(client, headers).json()["error"]["code"] == "demo_message_limit_reached"


def test_router_comparison_and_evaluation_count_as_paid_actions(settings, api):
    client, _, _ = api
    settings.demo_session_message_limit = 3
    headers = login(client)
    assert compare_routers(client, headers).status_code == 201  # 1
    request_id = send(client, headers).json()["message"]["request_id"]  # 2
    assert evaluate(client, headers, request_id).status_code == 201  # 3
    assert evaluate(client, headers, request_id).status_code == 200  # reused: no new paid call, not counted
    assert send(client, headers).status_code == 429
    assert compare_routers(client, headers).json()["error"]["code"] == "demo_message_limit_reached"
    assert evaluate(client, headers, request_id, repeat=True).json()["error"]["code"] == "demo_message_limit_reached"
    admin = login(client, ADMIN_KEY)
    assert compare_routers(client, admin).status_code == 201  # admin is not limited


def test_budget_refusals_before_any_call_give_the_action_back(settings, api, monkeypatch):
    client, orchestrator, _ = api
    settings.demo_session_message_limit = 2
    headers = login(client)
    request_id = send(client, headers).json()["message"]["request_id"]  # 1
    original = orchestrator.budget.reserve

    def refuse(**kwargs):
        raise BudgetExceeded("installation", kwargs["amount"], 0)

    monkeypatch.setattr(orchestrator.budget, "reserve", refuse)
    assert evaluate(client, headers, request_id).status_code == 429
    assert compare_routers(client, headers).status_code == 429
    monkeypatch.setattr(orchestrator.budget, "reserve", original)
    assert compare_routers(client, headers).status_code == 201  # 2: both refusals were refunded
    assert send(client, headers).status_code == 429


# --- P3-06: only independent runs are reused -------------------------------------------------------------------------


def test_comparison_reuses_only_runs_without_conversation_history(api):
    client, _, _ = api
    headers = login(client)
    message = "Quero falar com um atendente humano"
    first = send(client, headers, message, scenario_id="SC-HANDOFF").json()
    conversation_id = first["message"]["conversation_id"]
    second = send(client, headers, message, scenario_id="SC-HANDOFF", conversation_id=conversation_id)
    assert second.status_code == 200
    runs = [
        client.get(f"/v1/runs/{item['message']['request_id']}", headers=headers).json()
        for item in (first, second.json())
    ]
    assert [run["history_turns"] for run in runs] == [0, 2]
    estimate = client.post("/v1/comparisons/estimate", headers=headers, json=SELECTION | {"repetitions": 2}).json()
    reference = [cell for cell in estimate["cells"] if cell["profile_id"] == "reference"]
    assert [cell["source"] for cell in reference] == ["recorded", "new"]
    assert reference[0]["reused_request_id"] == first["message"]["request_id"]


# --- P3-09a: one knowledge-base version for the whole comparison, and reuse only on the same version -----------------


def _ready_candidate(orchestrator):
    kb = orchestrator.knowledge_base
    estimate = kb.estimate({})
    version = kb.create_version({}, estimate["active_version_id"], estimate["digest"], True, 0.0)
    assert kb.test_version(version["version_id"], confirmed=True, max_cost_usd=0.0)["passed"]
    return version["version_id"]


def test_activation_during_a_comparison_does_not_change_its_knowledge_base_version(api):
    client, orchestrator, llm = api
    headers = login(client)
    candidate = _ready_candidate(orchestrator)
    original, activated = llm.handler, []

    def activate_on_first_call(call):
        if not activated:
            activated.append(
                orchestrator.knowledge_base.transition(
                    candidate, action="activate", expected_active="kb_initial", confirmed=True, actor="t"
                )
            )
        return original(call)

    llm.handler = activate_on_first_call
    comparison = run_comparison(client, headers, SELECTION | {"scenario_ids": ["SC-HANDOFF", "SC-RECEIVABLES"]})
    assert activated and orchestrator.knowledge_base.capture_active()[1] == candidate
    assert comparison["state"] == "completed"
    versions = {
        client.get(f"/v1/runs/{cell['request_id']}", headers=headers).json()["knowledge_base_version_id"]
        for cell in comparison["cells"]
    }
    assert versions == {"kb_initial"}


def test_runs_recorded_on_another_knowledge_base_version_are_not_reused(api):
    client, orchestrator, _ = api
    headers = login(client)
    run_comparison(client, headers, SELECTION)
    assert client.post("/v1/comparisons/estimate", headers=headers, json=SELECTION).json()["reused_executions"] == 2
    candidate = _ready_candidate(orchestrator)
    orchestrator.knowledge_base.transition(
        candidate, action="activate", expected_active="kb_initial", confirmed=True, actor="t"
    )
    again = client.post("/v1/comparisons/estimate", headers=headers, json=SELECTION).json()
    assert again["reused_executions"] == 0 and again["fixed_factors"]["knowledge_base_version_id"] == candidate


# --- P3-09c: unknown cost is never zero and a multi-model agent is not duplicated ------------------------------------


def test_aggregates_keep_unknown_cost_unknown_and_do_not_split_a_combined_agent_cost():
    config = {"profiles": [{"profile_id": "p", "profile_version": 1}]}
    cells = [
        {
            "profile_id": "p",
            "profile_version": 1,
            "status": "completed",
            "request_id": "r1",
            "cost_usd": None,
            "duration_ms": 10,
            "cost_by_agent": {"support": {"cost_usd": 0.004, "models": ["a", "b"]}},
        },
        {"profile_id": "p", "profile_version": 1, "status": "completed", "request_id": "r2", "cost_usd": None},
    ]
    result = comparisons.aggregates(config, cells, {})
    profile = result["profiles"][0]
    assert profile["cost_mean_usd"] is None and profile["cost_total_usd"] is None
    assert profile["cost_unknown_runs"] == 2
    assert result["cost_by_agent_model"] == [
        {
            "profile_id": "p",
            "profile_version": 1,
            "agent": "support",
            "model": "a + b",
            "cost_usd": 0.004,
            "request_ids": ["r1"],
        }
    ]


# --- review r2 residues (task 60, round 3) -------------------------------------------------------------------------


def _session_count(settings) -> int:
    conn = sqlite3.connect(settings.db_path)
    try:
        return conn.execute("SELECT MAX(message_count) FROM api_sessions").fetchone()[0]
    finally:
        conn.close()


def test_message_refused_by_the_budget_before_any_model_call_does_not_consume(settings, api, monkeypatch):  # P3-R2-01
    client, orchestrator, llm = api
    settings.demo_session_message_limit = 1
    headers = login(client)
    original = orchestrator.budget.reserve

    def refuse(**kwargs):
        raise BudgetExceeded("installation", kwargs["amount"], 0)

    monkeypatch.setattr(orchestrator.budget, "reserve", refuse)
    refused = send(client, headers)
    assert refused.status_code == 503 and llm.calls == []
    assert _session_count(settings) == 0
    monkeypatch.setattr(orchestrator.budget, "reserve", original)
    assert send(client, headers).status_code == 200  # the only allowed action is still available
    assert send(client, headers).status_code == 429


def test_comparison_cells_without_a_model_call_are_given_back(settings, api, monkeypatch):  # P3-R2-01
    client, orchestrator, _ = api
    settings.demo_session_message_limit = 10
    headers = login(client)
    original = orchestrator.budget.reserve
    calls = {"n": 0}

    def reserve(**kwargs):
        calls["n"] += 1
        if calls["n"] > 1:  # the first cell starts, every later reservation is refused
            raise BudgetExceeded("installation", kwargs["amount"], 0)
        return original(**kwargs)

    monkeypatch.setattr(orchestrator.budget, "reserve", reserve)
    comparison = run_comparison(client, headers, SELECTION | {"scenario_ids": ["SC-HANDOFF", "SC-RECEIVABLES"]})
    inferred = [cell for cell in comparison["cells"] if cell.get("model_calls")]
    assert len(inferred) == 1 and any(item["code"] == "budget_denied" for item in comparison["failures"])
    assert _session_count(settings) == 1  # 4 counted at the start, 3 cells without inference given back


def test_using_the_router_decision_consumes_the_demo_limit(settings, api):  # P3-R2-03
    client, _, _ = api
    settings.demo_session_message_limit = 2
    headers = login(client)
    compared = compare_routers(client, headers)  # 1
    assert compared.status_code == 201
    used = send(
        client,
        headers,
        "My card machine won't connect",
        profile_id="hybrid",
        router_mechanism="jev",
        comparison_id=compared.json()["comparison_id"],
    )  # 2
    assert used.status_code == 200
    assert _session_count(settings) == 2
    assert send(client, headers).json()["error"]["code"] == "demo_message_limit_reached"
