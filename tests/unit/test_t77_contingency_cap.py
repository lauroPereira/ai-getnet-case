"""Task 77: the USD 1.40 contingency cap only continues the mounted v080-qa campaign, and the transition script.

Synthetic ledgers in tmp_path only; no network, no paid call. The numbers mirror the ledgers recorded after QA r4
(primary 1.70 with US$1.14385079 committed, campaign 1.10 with US$0.58164655 committed, zero reservations).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
from pathlib import Path

import pytest

from merchant_assistant import cli
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.orchestration.budget import BudgetGuard, FixedBudgetGuard

SCRIPT = PROJECT_ROOT / "tools" / "scripts" / "v080_contingency_transition.py"
PRIMARY_COMMITTED = 1.14385079
CAMPAIGN_COMMITTED = 0.58164655


def _load_script():
    spec = importlib.util.spec_from_file_location("v080_contingency_transition", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


transition = _load_script()


def _no_processes():
    return []


def _ledgers(budget_dir: Path, *, open_reservation: bool = False) -> tuple[Path, Path]:
    """Primary (1.70) and campaign (v080-qa, 1.10) with settled history, as left by QA r4."""
    primary_path, campaign_path = budget_dir / "budget.sqlite3", budget_dir / "budget-v080-qa.sqlite3"
    primary = BudgetGuard(primary_path, 1.70)
    prior = primary.reserve(request_id="before-campaign", agent="router", model="m", amount=0.1)
    primary.settle(prior, PRIMARY_COMMITTED - CAMPAIGN_COMMITTED)
    campaign = FixedBudgetGuard(campaign_path, 1.10, cap_id="v080-qa", cap_ceiling_usd=1.10)
    for index, amount in enumerate((0.3, CAMPAIGN_COMMITTED - 0.3)):
        ids = [
            guard.reserve(request_id=f"qa-{index}", agent="judge", model="m", amount=0.01)
            for guard in (primary, campaign)
        ]
        primary.settle(ids[0], amount)
        campaign.settle(ids[1], amount)
    if open_reservation:
        campaign.reserve(request_id="in-flight", agent="judge", model="m", amount=0.001)
    return primary_path, campaign_path


def _bytes(*paths: Path) -> dict[str, str]:
    files = [*paths, *(Path(f"{p}.limit") for p in paths)]
    return {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


def _ceiling_bytes(value: float) -> bytes:
    """What the budget guard itself publishes on this platform (text mode: CRLF on Windows)."""
    return f"{value!r}{os.linesep}".encode("ascii")


def _settings(settings, budget_dir: Path, limit: float):
    return settings.model_copy(update={"budget_runtime_dir": budget_dir, "budget_limit_usd": limit})


def _guard(settings, cap=1.40, estimate=True):
    return cli._evaluation_budget_guard(
        settings, "v080-qa", campaign_cap_usd=cap, estimate_report="synthetic-estimate.json" if estimate else None
    )


@pytest.fixture
def verified_estimate(monkeypatch):
    monkeypatch.setattr(cli, "_verified_v080_campaign_estimate", lambda _path: 1.03174096)


# --- FixedBudgetGuard ---------------------------------------------------------------------------------------------


def test_the_budget_guard_never_mounts_a_new_campaign_above_usd_1_10(tmp_path):
    fresh = tmp_path / "fresh.sqlite3"
    with pytest.raises(ValueError, match="only continues an existing campaign ledger"):
        FixedBudgetGuard(fresh, 1.40, cap_id="v080-qa", cap_ceiling_usd=1.40)
    assert not fresh.exists() and not Path(f"{fresh}.limit").exists()

    bare = tmp_path / "bare.sqlite3"
    BudgetGuard(bare, 1.40)  # a ledger with a 1.40 ceiling but no campaign cap record
    with pytest.raises(ValueError, match="only continues an existing campaign cap"):
        FixedBudgetGuard(bare, 1.40, cap_id="v080-qa", cap_ceiling_usd=1.40)
    with sqlite3.connect(bare) as conn:
        assert conn.execute("SELECT COUNT(*) FROM fixed_budget_cap").fetchone() == (0,)

    with pytest.raises(ValueError):
        FixedBudgetGuard(tmp_path / "other.sqlite3", 1.40, cap_id="v070-qa", cap_ceiling_usd=1.40)
    with pytest.raises(ValueError):
        FixedBudgetGuard(tmp_path / "above.sqlite3", 1.41, cap_id="v080-qa", cap_ceiling_usd=1.41)


def test_the_budget_guard_keeps_a_1_10_campaign_at_1_10(tmp_path):
    _, campaign = _ledgers(tmp_path)
    with pytest.raises(ValueError):  # sidecar 1.10 is below the requested 1.40
        FixedBudgetGuard(campaign, 1.40, cap_id="v080-qa", cap_ceiling_usd=1.40)
    Path(f"{campaign}.limit").write_text("1.4\n", encoding="ascii")
    with pytest.raises(ValueError, match="already fixed to a different amount"):
        FixedBudgetGuard(campaign, 1.40, cap_id="v080-qa", cap_ceiling_usd=1.40)


# --- CLI ------------------------------------------------------------------------------------------------------------


def test_cli_accepts_1_40_only_as_a_choice_that_needs_an_estimate(settings, tmp_path, monkeypatch):
    budget_dir = tmp_path / "budget"
    local = _settings(settings, budget_dir, 2.0)
    monkeypatch.setattr(cli, "get_settings", lambda: local)
    with pytest.raises(SystemExit, match="USD 1.40 v080-qa cap requires --campaign-estimate"):
        cli.main(["eval", "--scripted", "--campaign", "v080-qa", "--campaign-cap-usd", "1.40"])
    with pytest.raises(SystemExit) as refused:
        cli.main(["eval", "--scripted", "--campaign", "v080-qa", "--campaign-cap-usd", "1.30"])
    assert refused.value.code == 2  # argparse: not one of the four choices
    with pytest.raises(SystemExit, match="safe measured source-report reference"):  # the real verifier runs
        bad = tmp_path / "unverified.json"
        bad.write_text(json.dumps({"estimated_cost_usd": 1.05}), encoding="utf-8")
        cli._evaluation_budget_guard(local, "v080-qa", campaign_cap_usd=1.40, estimate_report=bad)
    assert not budget_dir.exists()


@pytest.mark.parametrize("estimate", [0.75, 1.00, 1.11, 1.40, True])
def test_cli_refuses_1_40_without_the_estimate_that_justified_the_campaign(settings, tmp_path, monkeypatch, estimate):
    monkeypatch.setattr(cli, "_verified_v080_campaign_estimate", lambda _path: estimate)
    primary, campaign = _ledgers(tmp_path / "budget")
    before = _bytes(primary, campaign)
    with pytest.raises(SystemExit, match="above USD 1.00 and at most USD 1.10"):
        _guard(_settings(settings, tmp_path / "budget", 1.70))
    assert _bytes(primary, campaign) == before


def test_cli_refuses_1_40_when_no_campaign_was_mounted(settings, tmp_path, verified_estimate):
    budget_dir = tmp_path / "budget"
    with pytest.raises(SystemExit, match="only continues the v080-qa campaign already mounted"):
        _guard(_settings(settings, budget_dir, 2.0))
    assert not budget_dir.exists()
    BudgetGuard(budget_dir / "budget.sqlite3", 2.0)  # a primary ledger alone is not a campaign
    with pytest.raises(SystemExit, match="only continues the v080-qa campaign already mounted"):
        _guard(_settings(settings, budget_dir, 2.0))
    assert not (budget_dir / "budget-v080-qa.sqlite3").exists()


def test_cli_refuses_1_40_before_the_transition_and_1_10_after_it(settings, tmp_path, verified_estimate):
    budget_dir = tmp_path / "budget"
    primary, campaign = _ledgers(budget_dir)
    before = _bytes(primary, campaign)
    with pytest.raises(SystemExit, match="still fixed at USD 1.10; apply the reviewed contingency transition"):
        _guard(_settings(settings, budget_dir, 1.70))
    assert _bytes(primary, campaign) == before

    transition.apply(primary, campaign, tmp_path / "audit", processes=_no_processes)
    with pytest.raises(SystemExit, match="does not match the fixed USD 1.10 cap"):
        _guard(_settings(settings, budget_dir, 1.70), cap=1.10)


def test_cli_refuses_1_40_when_the_persisted_primary_does_not_cover_it(settings, tmp_path, verified_estimate):
    budget_dir = tmp_path / "budget"
    primary, campaign = _ledgers(budget_dir)
    with sqlite3.connect(campaign) as conn:  # only the campaign side raised: the primary is still 1.70
        conn.execute("UPDATE fixed_budget_cap SET limit_usd=1.4")
    conn.close()
    Path(f"{campaign}.limit").write_text("1.4\n", encoding="ascii")
    with pytest.raises(SystemExit, match="persisted primary ceiling does not cover"):
        _guard(_settings(settings, budget_dir, 1.70))


def test_cli_continues_the_campaign_after_the_transition(settings, tmp_path, verified_estimate):
    budget_dir = tmp_path / "budget"
    primary, campaign = _ledgers(budget_dir)
    transition.apply(primary, campaign, tmp_path / "audit", processes=_no_processes)
    guard = _guard(_settings(settings, budget_dir, 2.0))
    assert guard.campaign.remaining() == pytest.approx(1.40 - CAMPAIGN_COMMITTED)
    assert guard.primary.remaining() == pytest.approx(2.0 - PRIMARY_COMMITTED)
    assert guard.remaining() == pytest.approx(0.81835345)
    ids = guard.reserve(request_id="r5", agent="judge", model="m", amount=0.81)
    guard.settle(ids, 0.81835345)
    assert guard.campaign.guard.spent() == pytest.approx(1.40)
    with pytest.raises(Exception, match="budget exceeded"):
        guard.reserve(request_id="r6", agent="judge", model="m", amount=0.0001)


# --- transition script -----------------------------------------------------------------------------------------------


def test_dry_run_checks_both_ledgers_and_writes_nothing(tmp_path, monkeypatch, capsys):
    primary, campaign = _ledgers(tmp_path / "budget")
    before = _bytes(primary, campaign)
    monkeypatch.setattr(transition, "project_processes", _no_processes)
    assert transition.main(["--primary", str(primary), "--campaign", str(campaign)]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["result"] == "dry_run"
    assert plan["would_change"] == ["primary_ceiling", "campaign_ceiling", "campaign_cap"]
    state = plan["state"]
    assert state["primary"]["committed_usd"] == PRIMARY_COMMITTED
    assert state["campaign"]["committed_usd"] == CAMPAIGN_COMMITTED
    assert state["primary"]["open_reservations"] == state["campaign"]["open_reservations"] == 0
    assert state["coverage_after_usd"] == {"primary_room": 0.85614921, "campaign_room": 0.81835345}
    assert _bytes(primary, campaign) == before
    assert sorted(p.name for p in (tmp_path / "budget").iterdir()) == [
        "budget-v080-qa.sqlite3",
        "budget-v080-qa.sqlite3.limit",
        "budget.sqlite3",
        "budget.sqlite3.limit",
    ]


def test_apply_raises_both_ceilings_preserves_history_and_records_the_audit(tmp_path):
    primary, campaign = _ledgers(tmp_path / "budget")
    before = transition.inspect(primary, campaign)
    audit = tmp_path / "audit"
    applied = transition.apply(primary, campaign, audit, processes=_no_processes)

    assert applied["result"] == "applied" and all(applied["checks"].values())
    assert Path(f"{campaign}.limit").read_bytes() == _ceiling_bytes(1.4)
    assert Path(f"{primary}.limit").read_bytes() == _ceiling_bytes(2.0)
    with sqlite3.connect(campaign) as conn:
        assert conn.execute("SELECT cap_id,limit_usd FROM fixed_budget_cap").fetchall() == [("v080-qa", 1.4)]
    conn.close()
    after = transition.inspect(primary, campaign)
    for name in ("primary", "campaign"):
        for key in ("logical_sha256", "entries", "last_id", "committed_usd"):
            assert after[name][key] == before[name][key]

    prepared = json.loads((audit / "prepared.json").read_text(encoding="utf-8"))
    recorded = json.loads((audit / "applied.json").read_text(encoding="utf-8"))
    assert prepared["before"]["stages"] == {
        "primary_ceiling": "before",
        "campaign_ceiling": "before",
        "campaign_cap": "before",
    }
    assert prepared["procedure_sha256"] == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert recorded["after"]["complete"] is True
    for name in ("primary", "campaign"):
        backup = prepared["backups"][name]
        assert backup["logical_sha256"] == before[name]["logical_sha256"]
        assert recorded["after"][name]["logical_sha256"] == prepared["before"][name]["logical_sha256"]
        assert Path(backup["sidecar_bytes"]).read_bytes() == _ceiling_bytes(1.7 if name == "primary" else 1.1)
        assert hashlib.sha256(Path(backup["sqlite"]).read_bytes()).hexdigest() == backup["sqlite_sha256"]

    # idempotent: a second run changes nothing and needs no audit directory
    state = _bytes(primary, campaign)
    assert transition.apply(primary, campaign, tmp_path / "unused", processes=_no_processes)["result"] == (
        "already_applied"
    )
    assert _bytes(primary, campaign) == state and not (tmp_path / "unused").exists()


def test_apply_finishes_an_interrupted_transition(tmp_path):
    primary, campaign = _ledgers(tmp_path / "budget")
    transition._raise_campaign_cap(campaign)  # interrupted after the first step
    result = transition.apply(primary, campaign, tmp_path / "audit", processes=_no_processes)
    assert result["result"] == "applied"
    prepared = json.loads((tmp_path / "audit" / "prepared.json").read_text(encoding="utf-8"))
    assert prepared["before"]["stages"]["campaign_cap"] == "after"
    assert transition.inspect(primary, campaign)["complete"]


def test_apply_is_refused_with_an_open_reservation(tmp_path):
    primary, campaign = _ledgers(tmp_path / "budget", open_reservation=True)
    before = _bytes(primary, campaign)
    with pytest.raises(transition.TransitionError, match="campaign ledger has 1 open reservation"):
        transition.apply(primary, campaign, tmp_path / "audit", processes=_no_processes)
    assert _bytes(primary, campaign) == before and not (tmp_path / "audit").exists()


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        (lambda p, c: Path(f"{p}.limit").write_text("1.5\n", encoding="ascii"), "primary ceiling sidecar is 1.5"),
        (lambda p, c: Path(f"{c}.limit").write_text("1.0\n", encoding="ascii"), "campaign ceiling sidecar is 1.0"),
        (lambda p, c: Path(f"{c}.limit").write_text("1.4\n", encoding="ascii"), "not a state this procedure"),
        (lambda p, c: Path(f"{c}.limit").unlink(), "missing or invalid ceiling sidecar"),
    ],
    ids=["primary-unexpected", "campaign-unexpected", "sidecar-ahead-of-record", "sidecar-missing"],
)
def test_apply_is_refused_on_an_unknown_state(tmp_path, setup, message):
    primary, campaign = _ledgers(tmp_path / "budget")
    setup(primary, campaign)
    with pytest.raises(transition.TransitionError, match=message):
        transition.apply(primary, campaign, tmp_path / "audit", processes=_no_processes)
    assert not (tmp_path / "audit").exists()


def test_apply_is_refused_with_project_processes_a_used_audit_dir_or_one_ledger_twice(tmp_path, capsys):
    primary, campaign = _ledgers(tmp_path / "budget")
    before = _bytes(primary, campaign)
    with pytest.raises(transition.TransitionError, match="project processes are running"):
        transition.apply(primary, campaign, tmp_path / "audit", processes=lambda: ["4242\tpython -m uvicorn app"])
    used = tmp_path / "used"
    used.mkdir()
    (used / "prepared.json").write_text("{}", encoding="utf-8")
    with pytest.raises(transition.TransitionError, match="must be new or empty"):
        transition.apply(primary, campaign, used, processes=_no_processes)
    with pytest.raises(transition.TransitionError, match="different ledgers"):
        transition.apply(primary, primary, tmp_path / "audit", processes=_no_processes)
    assert _bytes(primary, campaign) == before

    with pytest.raises(SystemExit):
        transition.main(["--primary", str(primary), "--campaign", str(campaign), "--apply"])
    assert "--apply needs --audit-dir" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        transition.main(["--campaign", str(campaign), "--apply", "--audit-dir", str(tmp_path / "a")])
    assert _bytes(primary, campaign) == before


def test_apply_keeps_the_line_terminator_of_each_sidecar(tmp_path):
    primary, campaign = _ledgers(tmp_path / "budget")
    Path(f"{primary}.limit").write_bytes(b"1.7\n")
    Path(f"{campaign}.limit").write_bytes(b"1.1\r\n")
    transition.apply(primary, campaign, tmp_path / "audit", processes=_no_processes)
    assert Path(f"{primary}.limit").read_bytes() == b"2.0\n"
    assert Path(f"{campaign}.limit").read_bytes() == b"1.4\r\n"
