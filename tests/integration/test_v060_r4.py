"""v0.6.0 QA r1 corrections (task 61): the JEV toggle really runs the TypeSafe adapter (P1-QA-01), the demo-limit
refund never fails open (P3-R3-01) and /ready shows the active knowledge-base version (observation O-3).

Synthetic and offline only: scripted model, fake JEV transport, hashing embedder, in-memory Qdrant."""

from __future__ import annotations

import sqlite3

import pytest
from pydantic import SecretStr

from merchant_assistant import comparisons
from merchant_assistant.api import v1
from merchant_assistant.llm.jev import JEV_MODEL, JevRouter
from merchant_assistant.orchestration.budget import BudgetExceeded

DEMO_KEY = "synthetic-demo-access-key-v060-r4"


@pytest.fixture
def system(settings, offline):
    settings.api_demo_access_key = SecretStr(DEMO_KEY)
    client, orchestrator, llm = offline()
    jev_payloads: list[dict] = []

    def transport(payload):
        jev_payloads.append(payload)
        return {
            "model": JEV_MODEL,
            "answers": {
                "route": {"choice": "support"},
                "language": {"choice": "pt"},
                "topic": {"choice": "receivables"},
                "safety": {"choice": "none"},
                "case_signal": {"choice": "none"},
            },
            "usage": {"input_tokens": 12, "output_tokens": 5},
        }

    def factory(provider, model):
        if provider == "typesafe":
            return JevRouter("synthetic-key", transport=transport)
        return llm  # every LLM agent (openai or deepseek in the profile) is the scripted model

    orchestrator.llm_factory = factory
    headers = {
        "Authorization": f"Bearer {client.post('/v1/sessions', json={'access_key': DEMO_KEY}).json()['access_token']}"
    }
    return client, orchestrator, llm, jev_payloads, headers


def ledger_rows(orchestrator, request_id):
    conn = sqlite3.connect(orchestrator.budget.path)
    try:
        return conn.execute("SELECT agent, model FROM ledger WHERE request_id=? ORDER BY id", (request_id,)).fetchall()
    finally:
        conn.close()


def test_jev_toggle_runs_the_typesafe_adapter_and_no_llm_router(system):  # P1-QA-01
    client, orchestrator, llm, jev_payloads, headers = system
    sent = client.post(
        "/v1/messages",
        headers=headers,
        json={
            "message": "Quando vai cair o dinheiro das vendas de ontem?",
            "scenario_id": "SC-RECEIVABLES",
            "profile_id": "reference",
            "profile_version": 1,
            "router_mechanism": "jev",
        },
    )
    assert sent.status_code == 200, sent.json()
    request_id = sent.json()["message"]["request_id"]
    assert len(jev_payloads) == 1
    assert not [call for call in llm.calls if call.spec.agent == "router"]
    rows = ledger_rows(orchestrator, request_id)
    assert ("router", JEV_MODEL) in rows and all(model != "scripted-v1" for agent, model in rows if agent == "router")
    run = client.get(f"/v1/runs/{request_id}", headers=headers).json()
    assert run["router_mechanism"] == "jev" and run["models"]["router"] == f"typesafe:{JEV_MODEL}"
    assert run["models_by_agent"]["router"]["models"] == [JEV_MODEL]  # what the UI lists as the effective model
    assert orchestrator.trace(request_id)["detail"]["models_by_agent"]["router"]["models"] == [JEV_MODEL]


def test_llm_toggle_still_uses_the_profile_router(system):
    client, _, llm, jev_payloads, headers = system
    sent = client.post(
        "/v1/messages",
        headers=headers,
        json={
            "message": "Olá, preciso de ajuda.",
            "profile_id": "reference",
            "profile_version": 1,
            "router_mechanism": "llm",
        },
    )
    assert sent.status_code == 200 and jev_payloads == []
    assert [call for call in llm.calls if call.spec.agent == "router"]


def test_profile_comparison_with_jev_runs_the_adapter_in_every_new_cell(system):  # P1-QA-01
    client, orchestrator, llm, jev_payloads, headers = system
    selection = {
        "profiles": [{"profile_id": "reference", "profile_version": 1}, {"profile_id": "hybrid", "profile_version": 1}],
        "scenario_ids": ["SC-RECEIVABLES"],
        "repetitions": 1,
        "router_mechanism": "jev",
    }
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
    ).json()
    comparisons._ACTIVE[created["comparison_id"]].join(timeout=60)
    comparison = client.get(f"/v1/comparisons/{created['comparison_id']}", headers=headers).json()
    assert comparison["state"] == "completed", comparison["failures"]
    assert len(jev_payloads) == 2 and not [call for call in llm.calls if call.spec.agent == "router"]
    for cell in comparison["cells"]:
        assert ("router", JEV_MODEL) in ledger_rows(orchestrator, cell["request_id"])
        assert cell["cost_by_agent"]["router"]["models"] == [JEV_MODEL]


def _count(settings):
    conn = sqlite3.connect(settings.db_path)
    try:
        return conn.execute("SELECT MAX(message_count) FROM api_sessions").fetchone()[0]
    finally:
        conn.close()


def test_failure_after_paid_calls_without_a_trace_does_not_refund(settings, system, monkeypatch):  # P3-R3-01
    client, orchestrator, _, _, headers = system

    def broken_persist(*_args, **_kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(orchestrator, "_persist", broken_persist)
    with pytest.raises(sqlite3.OperationalError):
        client.post(
            "/v1/messages",
            headers=headers,
            json={
                "message": "Olá, preciso de ajuda.",
                "profile_id": "reference",
                "profile_version": 1,
                "router_mechanism": "llm",
            },
        )
    assert _count(settings) == 1  # the ledger has the paid calls of this request: the action stays counted


def test_unreadable_ledger_never_refunds(settings, system, monkeypatch):  # P3-R3-01
    client, orchestrator, llm, _, headers = system

    def refuse(**kwargs):
        raise BudgetExceeded("installation", kwargs["amount"], 0)

    monkeypatch.setattr(orchestrator.budget, "reserve", refuse)
    monkeypatch.setattr(v1, "paid_attempts", lambda *_args: None)
    refused = client.post(
        "/v1/messages",
        headers=headers,
        json={
            "message": "Olá, preciso de ajuda.",
            "profile_id": "reference",
            "profile_version": 1,
            "router_mechanism": "llm",
        },
    )
    assert refused.status_code == 503 and llm.calls == []
    assert _count(settings) == 1


def test_paid_attempts_reads_reserved_and_settled_rows_only(tmp_path):
    from merchant_assistant.orchestration.budget import BudgetGuard

    guard = BudgetGuard(tmp_path / "ledger.sqlite3", 1.0)
    assert v1.paid_attempts(guard, "req_x") == 0
    cancelled = guard.reserve(request_id="req_x", agent="router", model="m", amount=0.01)
    guard.cancel(cancelled)
    assert v1.paid_attempts(guard, "req_x") == 0
    guard.reserve(request_id="req_x", agent="router", model="m", amount=0.01)
    assert v1.paid_attempts(guard, "req_x") == 1
    assert v1.paid_attempts(BudgetGuard(":memory:", 1.0), "req_x") is None


def test_ready_reports_the_active_knowledge_base_version(system):  # observation O-3
    client, orchestrator, _, _, _ = system
    kb = orchestrator.knowledge_base
    assert client.get("/ready").json()["knowledge_base"]["version_id"] == "kb_initial"
    estimate = kb.estimate({})
    version = kb.create_version({}, estimate["active_version_id"], estimate["digest"], True, 0.0)
    kb.test_version(version["version_id"], confirmed=True, max_cost_usd=0.0)
    kb.transition(version["version_id"], action="activate", expected_active="kb_initial", confirmed=True, actor="t")
    ready = client.get("/ready").json()["knowledge_base"]
    assert ready == {"version_id": version["version_id"], "collection": version["collection_name"]}


# --- review r4 residue (task 61, round 5): the comparison refund never fails open ---------------------------------


def _run_two_cells(client, headers):
    selection = {
        "profiles": [{"profile_id": "reference", "profile_version": 1}, {"profile_id": "hybrid", "profile_version": 1}],
        "scenario_ids": ["SC-HANDOFF"],
        "repetitions": 1,
        "router_mechanism": "llm",
    }
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
    ).json()
    comparisons._ACTIVE[created["comparison_id"]].join(timeout=60)
    return client.get(f"/v1/comparisons/{created['comparison_id']}", headers=headers).json()


def test_comparison_cells_that_failed_after_paid_calls_without_a_trace_are_not_given_back(  # P3-R4-02 (J5)
    settings, system, monkeypatch
):
    client, orchestrator, _, _, headers = system

    def broken_persist(*_args, **_kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(orchestrator, "_persist", broken_persist)
    comparison = _run_two_cells(client, headers)
    assert [cell["status"] for cell in comparison["cells"]] == ["failed", "failed"]
    assert all(orchestrator.trace(cell["request_id"]) is None for cell in comparison["cells"])  # no trace left
    assert all(ledger_rows(orchestrator, cell["request_id"]) for cell in comparison["cells"])  # but paid calls
    assert _count(settings) == 2  # both actions stay counted


def test_comparison_never_gives_back_a_started_cell_when_the_ledger_is_unreadable(  # P3-R4-02 (J7)
    settings, system, monkeypatch
):
    client, orchestrator, llm, _, headers = system

    def refuse(**kwargs):
        raise BudgetExceeded("installation", kwargs["amount"], 0)

    monkeypatch.setattr(orchestrator.budget, "reserve", refuse)
    monkeypatch.setattr(v1, "paid_attempts", lambda *_args: None)
    comparison = _run_two_cells(client, headers)
    started, skipped = comparison["cells"]
    assert started["request_id"] and not skipped.get("request_id") and llm.calls == []
    assert _count(settings) == 1  # the started cell stays counted; only the never-started one is given back
