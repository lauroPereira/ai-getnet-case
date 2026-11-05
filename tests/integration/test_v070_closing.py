"""v0.7.0 task 68: the release path is ready for the QA. The scripted evaluation runs the 40 labeled cases and the 4
follow-up conversations through the CLI in process, the `v070-qa` campaign cap mounts once at USD 0.20 combined with
the primary ledger, the package is 0.9.0 and the compose file declares the four services. No network, no cost."""

from __future__ import annotations

import argparse
import json
import tomllib

import pytest
import yaml

from merchant_assistant import __version__
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.orchestration.budget import BudgetExceeded, BudgetGuard, CombinedBudgetGuard, FixedBudgetGuard
from merchant_assistant.testing import merchant_headers

CAMPAIGN_ID, CAMPAIGN_USD = "v070-qa", 0.20
PRIMARY_SPENT_BEFORE = 0.69  # accumulated by the project before v0.7.0 (spec, "Requisitos não funcionais")

# Baseline measured on the tag v0.6.0 with this same command (scripted model): 25 of 40 cases pass `content_ok`. The 15
# below fail only because the scripted Knowledge policy returns the retrieved passage as the answer instead of writing
# one; the real model is what the QA campaign measures. The v0.7.0 contract changes two labelled texts (the protocol
# prefix `HO-` instead of `SIM-`, D7, and the handoff line without "simulated"): they must keep passing.
V060_CONTENT_FAILURES = frozenset(
    "EX01 EX02 EX04 EX05 EX06 EX09 EX10 NOEV PT01 PT02 PT04 PT05 PT06 PT09 PT10".split()
)


def test_eval_cli_runs_the_40_cases_and_the_followup_conversations(settings, tmp_path, capsys):
    from merchant_assistant.cli import cmd_eval

    args = argparse.Namespace(
        scripted=True, judge=False, split="all", out=str(tmp_path), name="v070", no_conversations=False
    )
    assert cmd_eval(settings, args) == 0
    assert "conversations: 4/4 passed" in capsys.readouterr().out
    report = json.loads((tmp_path / "v070.json").read_text(encoding="utf-8"))
    assert report["config"]["cases"] == 40 and len(report["cases"]) == 40
    assert {c["split"] for c in report["cases"]} == {"dev", "holdout"}
    assert report["summary"]["overall"]["cost_usd"] == 0
    checks = ("route_ok", "status_ok", "language_ok", "tools_ok", "amounts_ok", "forbidden_ok")
    checks += ("sources_ok", "grounded_ok")
    for check in checks:
        assert all(case[check] for case in report["cases"]), (check, [c["id"] for c in report["cases"] if not c[check]])
    failing = {case["id"] for case in report["cases"] if not case["content_ok"]}
    worse = sorted(failing - V060_CONTENT_FAILURES)
    assert not worse, f"content_ok worse than v0.6.0 in: {worse}"
    assert report["summary"]["overall"]["content_ok"] >= 0.625
    assert len(report["conversations"]) == 4 and all(c["passed"] for c in report["conversations"])


def test_v070_campaign_cap_mounts_once_at_twenty_cents_combined_with_the_primary_ledger(tmp_path):
    primary = BudgetGuard(tmp_path / "budget.sqlite3", 5.0)
    seeded = primary.reserve(request_id="before-v070", agent="history", model="test", amount=PRIMARY_SPENT_BEFORE)
    primary.settle(seeded, PRIMARY_SPENT_BEFORE)
    cap_path = tmp_path / "campaign-v070-qa.sqlite3"
    campaign = FixedBudgetGuard(cap_path, CAMPAIGN_USD, cap_id=CAMPAIGN_ID)
    guard = CombinedBudgetGuard(primary, campaign)
    assert guard.remaining() == pytest.approx(CAMPAIGN_USD)  # the campaign cap binds, not the USD 4.31 left in total
    reservation = guard.reserve(request_id="qa-1", agent="router", model="test", amount=0.05)
    guard.settle(reservation, 0.04)
    assert primary.spent() == pytest.approx(PRIMARY_SPENT_BEFORE + 0.04)  # one charge, seen by both ledgers
    assert campaign.guard.spent() == pytest.approx(0.04)
    assert guard.remaining() == pytest.approx(0.16)
    with pytest.raises(BudgetExceeded):
        guard.reserve(request_id="qa-2", agent="router", model="test", amount=0.17)  # over the campaign, not the total
    assert primary.spent() == pytest.approx(PRIMARY_SPENT_BEFORE + 0.04)  # the refused reservation left nothing
    remounted = FixedBudgetGuard(cap_path, CAMPAIGN_USD, cap_id=CAMPAIGN_ID)  # the same campaign mounts again
    assert remounted.guard.spent() == pytest.approx(0.04)
    with pytest.raises(ValueError):
        FixedBudgetGuard(cap_path, 0.25, cap_id=CAMPAIGN_ID)  # the cap is fixed once
    with pytest.raises(ValueError):
        FixedBudgetGuard(cap_path, CAMPAIGN_USD, cap_id="v060-qa")  # the ledger belongs to this campaign


def test_a_request_runs_through_the_campaign_guard_and_both_ledgers_record_it(offline, tmp_path):
    """The mounted campaign is what the orchestrator's calls reserve against: one request, scripted model, no cost."""
    client, orchestrator, llm = offline()
    primary = orchestrator.budget

    def ledger_rows(guard) -> int:
        conn = guard._conn()
        try:
            return conn.execute("SELECT COUNT(*) FROM ledger WHERE status='settled'").fetchone()[0]
        finally:
            conn.close()

    before = ledger_rows(primary)
    campaign = FixedBudgetGuard(tmp_path / "campaign-v070-qa.sqlite3", CAMPAIGN_USD, cap_id=CAMPAIGN_ID)
    orchestrator.budget = CombinedBudgetGuard(primary, campaign)
    sent = client.post(
        "/messages", json={"message": "Quando cai o dinheiro das vendas de ontem?"}, headers=merchant_headers(client)
    )
    assert sent.status_code == 200 and llm.calls, sent.text
    calls = orchestrator.trace(sent.json()["request_id"])["model_calls"]
    assert calls > 0 and ledger_rows(primary) - before == ledger_rows(campaign.guard) == calls  # seen by both
    assert primary.spent() == campaign.guard.spent() == 0  # the scripted model is free


def test_package_version_is_0_8_0():
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == __version__ == "0.9.0"


def test_compose_declares_api_ticketing_mocks_and_qdrant_with_the_webhook_contract():
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert {"api", "ticketing", "mocks", "qdrant"} <= set(services)
    api, ticketing, mocks = services["api"]["environment"], services["ticketing"]["environment"], services["mocks"]
    assert api["TICKETING_WEBHOOK_URL"] == "http://ticketing:8002/webhooks/assistant"
    assert api["CONVERSATION_WEBHOOK_URL"] == "http://mocks:8001/merchant/events"
    assert ticketing["ASSISTANT_URL"] == "http://api:8000"
    for name in ("TICKETING_WEBHOOK_SECRET", "ASSISTANT_WEBHOOK_SECRET"):  # same fictitious default on both sides
        assert api[name] == ticketing[name] and api[name].endswith("-fictitious}")
    assert api["CONVERSATION_WEBHOOK_SECRET"] == mocks["environment"]["CONVERSATION_WEBHOOK_SECRET"]
    depends = services["api"]["depends_on"]  # the first handoff.created after `up` finds the receivers listening
    assert depends["ticketing"]["condition"] == depends["mocks"]["condition"] == "service_healthy"
    assert "depends_on" not in services["ticketing"]  # no cycle: the ticketing never waits for the api
    assert services["api"]["ports"] == ["127.0.0.1:8000:8000"] and services["ticketing"]["ports"] == [
        "127.0.0.1:8002:8002"
    ]
    assert "ports" not in services["mocks"] and "ports" not in services["qdrant"]


def test_catalog_scenarios_carry_the_message_and_labels_of_their_source_cases():
    """The bench catalog copies its labels from the evaluation cases named in `source_case` (round 1 of the review
    of task 68: SC-HANDOFF kept `SIM-` after UC14 moved to `HO-`). A label changed in one place must change in
    the other."""
    from merchant_assistant.evaluation.runner import load_cases
    from merchant_assistant.scenarios import LABEL_FIELDS, as_case, catalog

    scenarios = PROJECT_ROOT / "tests" / "scenarios"
    files = ("challenge_examples", "core_cases", "business_journeys")
    cases = {case.id: case for case in load_cases([scenarios / f"{name}.jsonl" for name in files])}
    sourced = {
        sid: item for sid, item in catalog(PROJECT_ROOT / "data")["scenarios"].items() if item.get("source_case")
    }
    assert "SC-HANDOFF" in sourced and len(sourced) >= 9
    for scenario_id, item in sourced.items():
        case = cases[item["source_case"]]  # a missing source case is a failure too
        effective = as_case(item, "cliente1988")  # what the bench actually checks, defaults included
        assert effective.message == case.message and effective.language == case.language, scenario_id
        for field in LABEL_FIELDS:
            assert getattr(effective, field) == getattr(case, field), (scenario_id, field)
    handoff = sourced["SC-HANDOFF"]
    assert handoff["must_include_any"] == [["HO-"]] and handoff["must_not_include"] == ["SIM-", "simul"]


def test_handoff_scenario_passes_every_check_through_the_api_with_the_scripted_model(offline):
    """Review P2-1 of task 68: a correct handoff run from the bench scenario is 11 of 11, as it was in v0.6.0."""
    client, _, _ = offline()
    headers = merchant_headers(client)
    listed = client.get("/v1/scenarios", headers=headers).json()["scenarios"]
    item = next(s for s in listed if s["scenario_id"] == "SC-HANDOFF")
    sent = client.post(
        "/v1/messages",
        headers=headers,
        json={
            "message": item["message"],
            "profile_id": "reference",
            "profile_version": 1,
            "router_mechanism": "llm",
            "scenario_id": "SC-HANDOFF",
        },
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["message"]["status"] == "handoff" and "HO-" in sent.json()["message"]["answer"]
    checks = client.get(f"/v1/runs/{sent.json()['message']['request_id']}", headers=headers).json()["checks"]
    assert checks["origin"] == "scenario:SC-HANDOFF" and checks["critical_failures"] == []
    assert checks["results"]["content_ok"] is True and checks["results"]["forbidden_ok"] is True
    assert checks["passed"] == checks["total"] == 11 and all(checks["results"].values())
