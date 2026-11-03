"""v0.7.0 task 68: the release path is ready for the QA. The scripted evaluation runs the 40 labeled cases and the 4
follow-up conversations through the CLI in process, the `v070-qa` campaign cap mounts once at USD 0.20 combined with
the primary ledger, the package is 0.7.0 and the compose file declares the four services. No network, no cost."""

from __future__ import annotations

import argparse
import json
import tomllib

import pytest
import yaml

from merchant_assistant import __version__
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.orchestration.budget import BudgetExceeded, BudgetGuard, CombinedBudgetGuard, FixedBudgetGuard

CAMPAIGN_ID, CAMPAIGN_USD = "v070-qa", 0.20
PRIMARY_SPENT_BEFORE = 0.69  # accumulated by the project before v0.7.0 (spec, "Requisitos não funcionais")


def test_eval_cli_runs_the_40_cases_and_the_followup_conversations(settings, tmp_path, capsys):
    from merchant_assistant.cli import cmd_eval

    args = argparse.Namespace(
        scripted=True, judge=False, split="all", out=str(tmp_path), name="v070", no_conversations=False
    )
    assert cmd_eval(settings, args) == 0
    assert "conversations: 4/4 passed" in capsys.readouterr().out
    report = json.loads((tmp_path / "v070.json").read_text(encoding="utf-8"))
    assert report["config"]["cases"] == 40 and len(report["cases"]) == 40
    assert report["summary"]["overall"]["cost_usd"] == 0
    for check in ("route_ok", "status_ok", "language_ok", "tools_ok", "amounts_ok", "forbidden_ok"):
        assert all(case[check] for case in report["cases"]), (check, [c["id"] for c in report["cases"] if not c[check]])
    assert len(report["conversations"]) == 4 and all(c["passed"] for c in report["conversations"])


def test_v070_campaign_cap_mounts_once_at_twenty_cents_combined_with_the_primary_ledger(tmp_path):
    primary = BudgetGuard(tmp_path / "budget.sqlite3", 5.0)
    seeded = primary.reserve(request_id="before-v070", agent="history", model="test", amount=PRIMARY_SPENT_BEFORE)
    primary.settle(seeded, PRIMARY_SPENT_BEFORE)
    cap_path = tmp_path / "campaign-v070-qa.sqlite3"
    campaign = FixedBudgetGuard(cap_path, CAMPAIGN_USD, cap_id=CAMPAIGN_ID)
    guard = CombinedBudgetGuard(primary, campaign)
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


def test_package_version_is_0_7_0():
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == __version__ == "0.7.0"


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
    assert services["api"]["ports"] == ["127.0.0.1:8000:8000"] and services["ticketing"]["ports"] == [
        "127.0.0.1:8002:8002"
    ]
    assert "ports" not in services["mocks"] and "ports" not in services["qdrant"]
