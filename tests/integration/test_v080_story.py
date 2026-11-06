"""T73: integrated scripted story, measured campaign estimate, and fixed QA budget wiring."""

from __future__ import annotations

import argparse
import json
import tempfile
import tomllib
import uuid

import pytest
import yaml

from merchant_assistant import __version__, cli
from merchant_assistant.agents import replanner
from merchant_assistant.api.schemas import MessageRequest
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation.runner import Case, _checks
from merchant_assistant.orchestration.budget import BudgetExceeded, BudgetGuard, FixedBudgetGuard
from merchant_assistant.testing import offline_orchestrator

SOURCE_SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
REPLAN_CASES = [
    json.loads(line)
    for line in (SOURCE_SCENARIOS / "replan.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
CONDITIONS_CASE = next(
    json.loads(line)
    for line in (SOURCE_SCENARIOS / "business_journeys.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip() and json.loads(line)["id"] == "V030-PRICE-CONDITIONS"
)


def make_story_tree(tmp_path, monkeypatch):
    root = tmp_path / "project"
    scenarios = root / "tests" / "scenarios"
    scenarios.mkdir(parents=True)
    (scenarios / "challenge_examples.jsonl").write_text("", encoding="utf-8")
    (scenarios / "core_cases.jsonl").write_text("", encoding="utf-8")
    (scenarios / "business_journeys.jsonl").write_text(json.dumps(CONDITIONS_CASE) + "\n", encoding="utf-8")
    (scenarios / "replan.jsonl").write_text(
        "\n".join(json.dumps(row) for row in REPLAN_CASES) + "\n", encoding="utf-8"
    )
    synthetic_holdout = [
        json.dumps(row | {"id": f"SYN-H{i}", "split": "holdout_v080"})
        for i, row in enumerate(REPLAN_CASES[:2], start=1)
    ]
    (scenarios / "holdout_v080.jsonl").write_text("\n".join(synthetic_holdout) + "\n", encoding="utf-8")
    (scenarios / "followup.jsonl").write_text(
        (SOURCE_SCENARIOS / "followup.jsonl").read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    runtime = tmp_path / "scripted-runtime"

    def fixed_tempdir(prefix=""):
        runtime.mkdir(parents=True, exist_ok=True)
        return str(runtime)

    monkeypatch.setattr(tempfile, "mkdtemp", fixed_tempdir)
    return root


def make_estimate_tree(tmp_path, monkeypatch):
    root = tmp_path / "estimate-project"
    scenarios = root / "tests" / "scenarios"
    scenarios.mkdir(parents=True)
    (scenarios / "challenge_examples.jsonl").write_text("", encoding="utf-8")
    (scenarios / "core_cases.jsonl").write_text("", encoding="utf-8")
    (scenarios / "business_journeys.jsonl").write_text(json.dumps(CONDITIONS_CASE) + "\n", encoding="utf-8")
    (scenarios / "replan.jsonl").write_text(
        "\n".join(json.dumps(row) for row in REPLAN_CASES) + "\n", encoding="utf-8"
    )
    (scenarios / "followup.jsonl").write_text(
        (SOURCE_SCENARIOS / "followup.jsonl").read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    return root


def eval_args(tmp_path, **overrides):
    values = {
        "scripted": True,
        "judge": True,
        "split": "all",
        "out": str(tmp_path / "out"),
        "name": "agent",
        "no_conversations": False,
        "repeat": 3,
        "judge_repeat": None,
        "answers_from": None,
        "limit": None,
        "include_replan": False,
        "campaign": None,
    }
    return argparse.Namespace(**(values | overrides))


def test_story_runs_replanning_agent_and_judge_variations_and_synthetic_split(
    settings, tmp_path, monkeypatch, capsys
):
    make_story_tree(tmp_path, monkeypatch)

    trace_settings = settings.model_copy(update={"runtime_dir": tmp_path / "story-traces"})
    trace_orchestrator, _ = offline_orchestrator(trace_settings, faults={"simulate_pricing": "UNAVAILABLE"})
    for row in REPLAN_CASES:
        request_id = f"req_t73_{uuid.uuid4().hex[:12]}"
        response = trace_orchestrator.handle(
            MessageRequest(message=row["message"], user_id="cliente1988"), request_id
        )
        trace = trace_orchestrator.trace(request_id)
        checks = _checks(Case(**row), response.model_dump(), trace)
        assert all(checks[key] for key in ("route_ok", "status_ok", "tools_ok", "amounts_ok", "content_ok"))
        decisions = [step["detail"] for step in trace["steps"] if step["step"] == "replan"]
        assert decisions and all({"next", "reason", "review", "hops", "origin"} <= set(step) for step in decisions)
        assert max(step["hops"] for step in decisions) <= 3

    original_judge = cli._eval_judge

    def independent_scripted_judge(*args, **kwargs):
        judge = original_judge(*args, **kwargs)
        judge.provider = "deepseek"
        judge.model = "deepseek-flash"
        judge.independence = "different_provider"
        return judge

    monkeypatch.setattr(cli, "_eval_judge", independent_scripted_judge)
    assert cli.cmd_eval(
        settings, eval_args(tmp_path, name="agent", limit=5, include_replan=True, no_conversations=True)
    ) == 0
    agent = json.loads((tmp_path / "out" / "agent.json").read_text(encoding="utf-8"))
    assert agent["config"]["cases"] == 5 and len(agent["cases"]) == 15
    assert {row["id"] for row in agent["cases"] if row["repetition"] == 1} == {
        "REPLAN-WEB",
        "REPLAN-PROCEDURE",
        "REPLAN-TOOL-DOWN",
        "REPLAN-ACCOUNT",
        "V030-PRICE-CONDITIONS",
    }
    assert agent["config"]["agent_provider"] == "scripted"
    assert agent["config"]["judge_config"]["provider"] == "deepseek"
    assert agent["summary"]["by_split"]["dev"]["n"] == 15
    assert agent["summary"]["variation"]["kind"] == "assistant"
    assert all(row["judge"]["state"] == "completed" for row in agent["cases"])
    assert "conversations:" not in capsys.readouterr().out

    assert (
        cli.cmd_eval(
            settings,
            eval_args(
                tmp_path,
                name="judge",
                judge=False,
                repeat=1,
                judge_repeat=3,
                answers_from=str(tmp_path / "out" / "agent.json"),
                no_conversations=True,
            ),
        )
        == 0
    )
    judged = json.loads((tmp_path / "out" / "judge.json").read_text(encoding="utf-8"))
    assert len(judged["cases"]) == 5
    assert all(len(row["judge_runs"]) == 3 for row in judged["cases"])
    assert judged["summary"]["variation"]["kind"] == "judge"
    assert judged["summary"]["by_split"]["dev"]["n"] == 5
    capsys.readouterr()

    assert cli.cmd_eval(
        settings, eval_args(tmp_path, name="with-conversations", repeat=1, include_replan=True)
    ) == 0
    assert "conversations: 4/4 passed" in capsys.readouterr().out

    assert cli.cmd_eval(settings, eval_args(tmp_path, split="holdout_v080", name="synthetic-holdout", repeat=1)) == 0
    holdout = json.loads((tmp_path / "out" / "synthetic-holdout.json").read_text(encoding="utf-8"))
    assert {row["split"] for row in holdout["cases"]} == {"holdout_v080"}
    assert holdout["summary"]["by_split"]["holdout_v080"]["n"] == 2


def test_eval_estimate_requires_positive_real_measurements_and_projects_followups(
    settings, tmp_path, monkeypatch, capsys
):
    from pydantic import SecretStr

    root = make_estimate_tree(tmp_path, monkeypatch)
    scenarios = root / "tests" / "scenarios"
    assert not (scenarios / "holdout_v080.jsonl").exists()
    monkeypatch.setattr(cli, "V080_HOLDOUT_CASE_COUNT", 2)
    judge_config = {"provider": "deepseek", "model": "deepseek-flash", "independence": "different_provider"}
    cases = [
        {
            "id": f"MEASURED-{index}",
            "split": "dev",
            "repetition": 1,
            "cost_usd": 0.01,
            "judge": {
                "state": "completed",
                "provider": "deepseek",
                "model": "deepseek-flash",
                "cost_usd": 0.002,
                "scores": {"groundedness": 4, "factual_correctness": 4, "relevance": 4, "usefulness": 4},
            },
        }
        for index in range(1, 6)
    ]
    sample = {
        "config": {
            "mode": "real",
            "model": "gpt-6-luna",
            "agent_provider": "openai",
            "judge": True,
            "repeat": 1,
            "judge_config": judge_config,
        },
        "cases": cases,
    }
    report_path = tmp_path / "real-sample.json"
    out_path = tmp_path / "estimate.json"
    args = argparse.Namespace(source=str(report_path), out=str(out_path))
    report_path.write_text(json.dumps(sample), encoding="utf-8")
    scripted = json.loads(json.dumps(sample))
    scripted["config"].update(mode="scripted", agent_provider="scripted")
    report_path.write_text(json.dumps(scripted), encoding="utf-8")
    with pytest.raises(SystemExit, match="real paid sample"):
        cli.cmd_eval_estimate(settings, args)
    incomplete = json.loads(json.dumps(sample))
    incomplete["cases"][0]["judge"]["state"] = "failed"
    report_path.write_text(json.dumps(incomplete), encoding="utf-8")
    with pytest.raises(SystemExit, match="incomplete judge result"):
        cli.cmd_eval_estimate(settings, args)
    inconsistent = json.loads(json.dumps(sample))
    inconsistent["cases"][0]["judge"]["provider"] = "openai"
    report_path.write_text(json.dumps(inconsistent), encoding="utf-8")
    with pytest.raises(SystemExit, match="incomplete or inconsistent judge result"):
        cli.cmd_eval_estimate(settings, args)
    repeated = json.loads(json.dumps(sample))
    repeated["config"]["repeat"] = 3
    report_path.write_text(json.dumps(repeated), encoding="utf-8")
    with pytest.raises(SystemExit, match="single-run five-case measurement"):
        cli.cmd_eval_estimate(settings, args)
    zero_cost = json.loads(json.dumps(sample))
    for row in zero_cost["cases"]:
        row["cost_usd"] = 0.0
        row["judge"]["cost_usd"] = 0.0
    report_path.write_text(json.dumps(zero_cost), encoding="utf-8")
    with pytest.raises(SystemExit, match="costs must be positive"):
        cli.cmd_eval_estimate(settings, args)
    report_path.write_text(json.dumps(sample), encoding="utf-8")
    assert cli.cmd_eval_estimate(settings, args) == 0
    estimate = json.loads(capsys.readouterr().out)
    assert estimate["measured_cases"] == 5
    assert estimate["estimated_cost_usd"] == pytest.approx(0.394)
    assert estimate["followup_conversations"] == {
        "conversations": 4,
        "turns": 10,
        "runs_per_turn": 1,
        "mean_agent_cost_per_turn_usd": 0.01,
        "agent_cost_usd": 0.1,
        "judge_runs": 0,
        "judge_cost_usd": 0.0,
        "formula": "followup_turns * global_measured_mean_agent_cost; no judge",
        "estimated_cost_usd": 0.1,
    }
    assert not (scenarios / "holdout_v080.jsonl").exists()

    high_sample = json.loads(json.dumps(sample))
    monkeypatch.setattr(cli, "V080_HOLDOUT_CASE_COUNT", 5)
    high_sample_path = tmp_path / "real-high-sample.json"
    high_estimate_path = tmp_path / "verified-estimate.json"
    high_sample_path.write_text(json.dumps(high_sample), encoding="utf-8")
    assert cli.cmd_eval_estimate(
        settings, argparse.Namespace(source=str(high_sample_path), out=str(high_estimate_path))
    ) == 0
    capsys.readouterr()
    verified_estimate = json.loads(high_estimate_path.read_text(encoding="utf-8"))
    assert 0.50 < verified_estimate["estimated_cost_usd"] <= 1.00
    assert verified_estimate["campaign_cap_usd"] == 1.00
    assert verified_estimate["source_report"] == high_sample_path.name
    assert verified_estimate["estimate_format_version"] == 1

    budget_dir = tmp_path / "verified-budget"
    high_cap_settings = settings.model_copy(update={"budget_runtime_dir": budget_dir})
    guard = cli._evaluation_budget_guard(
        high_cap_settings, "v080-qa", campaign_cap_usd=1.00, estimate_report=high_estimate_path
    )
    assert guard.remaining() == pytest.approx(1.00)

    with pytest.raises(SystemExit, match="above USD 1.00 and at most USD 1.10"):
        cli._evaluation_budget_guard(
            high_cap_settings, "v080-qa", campaign_cap_usd=1.10, estimate_report=high_estimate_path
        )
    assert guard.remaining() == pytest.approx(1.00)

    minimal_path = tmp_path / "minimal-estimate.json"
    minimal_path.write_text(json.dumps({"estimated_cost_usd": 0.75}), encoding="utf-8")
    minimal_budget = tmp_path / "minimal-budget"
    minimal_settings = settings.model_copy(
        update={
            "budget_runtime_dir": minimal_budget,
            "deepseek_api_key": SecretStr("synthetic-deepseek-key"),
        }
    )
    with pytest.raises(SystemExit, match="safe measured source-report reference"):
        cli._evaluation_budget_guard(
            minimal_settings, "v080-qa", campaign_cap_usd=1.00, estimate_report=minimal_path
        )
    assert not minimal_budget.exists()
    with pytest.raises(SystemExit, match="USD 1.10 v080-qa cap requires --campaign-estimate"):
        cli._evaluation_budget_guard(minimal_settings, "v080-qa", campaign_cap_usd=1.10)
    assert not minimal_budget.exists()

    monkeypatch.setattr(cli, "get_settings", lambda: minimal_settings)
    with pytest.raises(SystemExit, match="USD 1.10 v080-qa cap requires --campaign-estimate"):
        cli.main(["eval", "--scripted", "--campaign", "v080-qa", "--campaign-cap-usd", "1.10"])

    provider_calls = []
    monkeypatch.setattr(cli, "_eval_judge", lambda *args, **kwargs: provider_calls.append(True))
    paid_args = eval_args(
        tmp_path,
        scripted=False,
        judge=True,
        split="dev",
        limit=1,
        no_conversations=True,
        campaign="v080-qa",
        campaign_cap_usd=1.00,
        campaign_estimate=str(minimal_path),
    )
    with pytest.raises(SystemExit, match="safe measured source-report reference"):
        cli.cmd_eval(minimal_settings, paid_args)
    assert not provider_calls
    assert not (minimal_budget / "budget-v080-qa.sqlite3").exists()

    paid_exceptional_args = eval_args(
        tmp_path,
        scripted=False,
        judge=True,
        split="dev",
        limit=1,
        no_conversations=True,
        campaign="v080-qa",
        campaign_cap_usd=1.10,
    )
    with pytest.raises(SystemExit, match="USD 1.10 v080-qa cap requires --campaign-estimate"):
        cli.cmd_eval(minimal_settings, paid_exceptional_args)
    assert not provider_calls
    assert not (minimal_budget / "budget-v080-qa.sqlite3").exists()

    tampered = json.loads(json.dumps(verified_estimate))
    tampered["estimated_cost_usd"] = 0.75
    tampered_path = tmp_path / "tampered-estimate.json"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(SystemExit, match="altered or does not match"):
        cli._evaluation_budget_guard(
            minimal_settings, "v080-qa", campaign_cap_usd=1.00, estimate_report=tampered_path
        )
    assert not (minimal_budget / "budget-v080-qa.sqlite3").exists()

    exceptional_sample = json.loads(json.dumps(sample))
    for row in exceptional_sample["cases"]:
        row["cost_usd"] = 0.02115386
        row["judge"]["cost_usd"] = 0.00423076
    exceptional_sample_path = tmp_path / "real-exceptional-sample.json"
    exceptional_estimate_path = tmp_path / "verified-exceptional-estimate.json"
    exceptional_sample_path.write_text(json.dumps(exceptional_sample), encoding="utf-8")
    assert cli.cmd_eval_estimate(
        settings,
        argparse.Namespace(source=str(exceptional_sample_path), out=str(exceptional_estimate_path)),
    ) == 0
    capsys.readouterr()
    exceptional_estimate = json.loads(exceptional_estimate_path.read_text(encoding="utf-8"))
    assert exceptional_estimate["estimated_cost_usd"] == 1.10
    assert exceptional_estimate["campaign_cap_usd"] == 1.10
    assert exceptional_estimate["requires_supervisor_decision"] is False

    primary_dir = tmp_path / "approved-primary"
    primary_path = primary_dir / "budget.sqlite3"
    approved_primary = BudgetGuard(primary_path, 1.70)
    prior_campaign_related = approved_primary.reserve(
        request_id="prior-approved-spend", agent="router", model="test", amount=0.55947501
    )
    approved_primary.settle(prior_campaign_related, 0.55947501)
    approved_settings = settings.model_copy(
        update={"budget_runtime_dir": primary_dir, "budget_limit_usd": 1.70}
    )
    exceptional_guard = cli._evaluation_budget_guard(
        approved_settings,
        "v080-qa",
        campaign_cap_usd=1.10,
        estimate_report=exceptional_estimate_path,
    )
    assert exceptional_guard.primary.remaining() == pytest.approx(1.14052499)
    assert exceptional_guard.campaign.remaining() == pytest.approx(1.10)
    first_phase = exceptional_guard.reserve(
        request_id="first-v080-qa-phase", agent="judge", model="test", amount=0.04052499
    )
    exceptional_guard.settle(first_phase, 0.04052499)
    reopened_guard = cli._evaluation_budget_guard(
        approved_settings,
        "v080-qa",
        campaign_cap_usd=1.10,
        estimate_report=exceptional_estimate_path,
    )
    assert reopened_guard.primary.remaining() == pytest.approx(1.10)
    assert reopened_guard.campaign.remaining() == pytest.approx(1.05947501)
    remaining_campaign = reopened_guard.reserve(
        request_id="remaining-v080-qa-phases", agent="judge", model="test", amount=1.05947501
    )
    reopened_guard.settle(remaining_campaign, 1.05947501)
    assert reopened_guard.primary.spent() == pytest.approx(1.65947501)
    assert reopened_guard.campaign.guard.spent() == pytest.approx(1.10)

    insufficient_dir = tmp_path / "insufficient-primary"
    insufficient_primary = BudgetGuard(insufficient_dir / "budget.sqlite3", 1.70)
    prior_insufficient = insufficient_primary.reserve(
        request_id="prior-insufficient-spend", agent="router", model="test", amount=0.6001
    )
    insufficient_primary.settle(prior_insufficient, 0.6001)
    insufficient_settings = settings.model_copy(
        update={"budget_runtime_dir": insufficient_dir, "budget_limit_usd": 1.70}
    )
    with pytest.raises(SystemExit, match="does not fit in the remaining primary budget"):
        cli._evaluation_budget_guard(
            insufficient_settings,
            "v080-qa",
            campaign_cap_usd=1.10,
            estimate_report=exceptional_estimate_path,
        )
    assert not (insufficient_dir / "budget-v080-qa.sqlite3").exists()

    above_limit_sample = json.loads(json.dumps(exceptional_sample))
    for row in above_limit_sample["cases"]:
        row["cost_usd"] = 0.0212
        row["judge"]["cost_usd"] = 0.00424
    above_limit_path = tmp_path / "real-above-exceptional-sample.json"
    above_limit_estimate_path = tmp_path / "above-exceptional-estimate.json"
    above_limit_path.write_text(json.dumps(above_limit_sample), encoding="utf-8")
    assert cli.cmd_eval_estimate(
        settings,
        argparse.Namespace(source=str(above_limit_path), out=str(above_limit_estimate_path)),
    ) == 0
    capsys.readouterr()
    above_limit_estimate = json.loads(above_limit_estimate_path.read_text(encoding="utf-8"))
    assert above_limit_estimate["estimated_cost_usd"] > 1.10
    assert above_limit_estimate["campaign_cap_usd"] is None
    assert above_limit_estimate["requires_supervisor_decision"] is True
    above_limit_budget = tmp_path / "above-limit-budget"
    above_limit_settings = settings.model_copy(
        update={"budget_runtime_dir": above_limit_budget, "budget_limit_usd": 1.70}
    )
    with pytest.raises(SystemExit, match="above USD 1.00 and at most USD 1.10"):
        cli._evaluation_budget_guard(
            above_limit_settings,
            "v080-qa",
            campaign_cap_usd=1.10,
            estimate_report=above_limit_estimate_path,
        )
    assert not (above_limit_budget / "budget-v080-qa.sqlite3").exists()

    tampered_exceptional = json.loads(json.dumps(exceptional_estimate))
    tampered_exceptional["estimated_cost_usd"] = 1.01
    tampered_exceptional_path = tmp_path / "tampered-exceptional-estimate.json"
    tampered_exceptional_path.write_text(json.dumps(tampered_exceptional), encoding="utf-8")
    with pytest.raises(SystemExit, match="altered or does not match"):
        cli._evaluation_budget_guard(
            above_limit_settings,
            "v080-qa",
            campaign_cap_usd=1.10,
            estimate_report=tampered_exceptional_path,
        )
    assert not (above_limit_budget / "budget-v080-qa.sqlite3").exists()

    scripted_sample = json.loads(json.dumps(high_sample))
    scripted_sample["config"].update(mode="scripted", agent_provider="scripted")
    scripted_sample_path = tmp_path / "scripted-sample.json"
    scripted_sample_path.write_text(json.dumps(scripted_sample), encoding="utf-8")
    incompatible = json.loads(json.dumps(verified_estimate))
    incompatible["source_report"] = scripted_sample_path.name
    incompatible_path = tmp_path / "incompatible-estimate.json"
    incompatible_path.write_text(json.dumps(incompatible), encoding="utf-8")
    with pytest.raises(SystemExit, match="source is invalid.*real paid sample"):
        cli._evaluation_budget_guard(
            minimal_settings, "v080-qa", campaign_cap_usd=1.00, estimate_report=incompatible_path
        )
    assert not (minimal_budget / "budget-v080-qa.sqlite3").exists()


@pytest.mark.parametrize(
    ("database_bytes", "sidecar_text"),
    [
        (None, "1.1\n"),
        (None, "1.15\n"),
        (b"invalid sqlite database", "1.1\n"),
    ],
    ids=["orphan-exact-sidecar", "orphan-higher-sidecar", "invalid-database"],
)
def test_exceptional_campaign_refuses_preexisting_unmatched_files(
    settings, tmp_path, monkeypatch, database_bytes, sidecar_text
):
    budget_dir = tmp_path / "budget"
    settings = settings.model_copy(update={"budget_runtime_dir": budget_dir, "budget_limit_usd": 1.70})
    primary = BudgetGuard(budget_dir / "budget.sqlite3", 1.70)
    assert primary.remaining() == pytest.approx(1.70)

    campaign_path = budget_dir / "budget-v080-qa.sqlite3"
    sidecar_path = budget_dir / "budget-v080-qa.sqlite3.limit"
    if database_bytes is not None:
        campaign_path.write_bytes(database_bytes)
    sidecar_path.write_text(sidecar_text, encoding="ascii")
    monkeypatch.setattr(cli, "_verified_v080_campaign_estimate", lambda _path: 1.01)

    with pytest.raises(SystemExit, match="pre-existing v080-qa database or ceiling sidecar.*does not match"):
        cli._evaluation_budget_guard(
            settings,
            "v080-qa",
            campaign_cap_usd=1.10,
            estimate_report=tmp_path / "synthetic-estimate.json",
        )

    assert primary.remaining() == pytest.approx(1.70)
    assert campaign_path.exists() is (database_bytes is not None)
    if database_bytes is not None:
        assert campaign_path.read_bytes() == database_bytes
    assert sidecar_path.read_text(encoding="ascii") == sidecar_text


def test_simple_and_forced_loop_follow_the_story_limits(settings, monkeypatch):
    simple_settings = settings.model_copy(update={"runtime_dir": settings.runtime_path / "simple"})
    orchestrator, llm = offline_orchestrator(simple_settings)
    request_id = f"req_t73_{uuid.uuid4().hex[:12]}"
    simple = orchestrator.handle(
        MessageRequest(
            message="What's the difference between the Get Clássica and the Get Smart?",
            user_id="cliente1988",
        ),
        request_id,
    )
    trace = orchestrator.trace(request_id)
    assert simple.route == "knowledge" and trace["detail"]["plan_hops"] == 0
    assert not [call for call in llm.calls if call.spec.agent == "replan"]

    from merchant_assistant.evaluation.scripted_policy import handler as default_handler

    loop_settings = settings.model_copy(update={"runtime_dir": settings.runtime_path / "loop"})
    decisions = iter(("web", "support", "escalate"))

    def loop_handler(call):
        if call.spec.agent == "replan":
            return {"next": next(decisions), "review": "incomplete", "reason": "The previous result leaves a gap."}
        return default_handler(call)

    monkeypatch.setattr(replanner, "apply_rules", lambda observed: [])
    loop_orchestrator, loop_llm = offline_orchestrator(loop_settings, handler=loop_handler)
    request_id = f"req_t73_{uuid.uuid4().hex[:12]}"
    loop = loop_orchestrator.handle(
        MessageRequest(
            message="What's the difference between the Get Clássica and the Get Smart?",
            user_id="cliente1988",
        ),
        request_id,
    )
    trace = loop_orchestrator.trace(request_id)
    specialists = [name for name in loop.agents if name in {"knowledge", "web", "customer_support"}]
    assert len(specialists) == len(set(specialists)) == 3
    assert trace["detail"]["plan_hops"] == 3 and loop.status == "handoff"
    assert [call.spec.agent for call in loop_llm.calls].count("replan") == 3


def test_v080_campaign_reuses_the_persistent_primary_and_cap_when_runtime_changes(settings, tmp_path):
    budget_dir = tmp_path / "project-budget"
    settings = settings.model_copy(
        update={
            "data_dir": tmp_path / "data",
            "runtime_dir": tmp_path / "qa-runtime-one",
            "budget_runtime_dir": budget_dir,
        }
    )
    primary_path = budget_dir / "budget.sqlite3"
    prior = BudgetGuard(primary_path, settings.budget_limit_usd)
    history = prior.reserve(request_id="history", agent="router", model="test", amount=0.2)
    prior.settle(history, 0.2)

    sample_budget = cli._eval_budget_for_args(settings, eval_args(tmp_path))
    assert sample_budget.path == str(primary_path) and sample_budget.spent() == pytest.approx(0.2)
    first = cli._evaluation_budget_guard(settings, "v080-qa")
    reservation = first.reserve(request_id="t73", agent="router", model="test", amount=0.1)
    first.settle(reservation, 0.1)
    assert first.primary.spent() == pytest.approx(0.3)
    assert first.campaign.guard.spent() == pytest.approx(0.1)

    isolated = settings.model_copy(update={"runtime_dir": tmp_path / "qa-runtime-two"})
    remounted = cli._evaluation_budget_guard(isolated, "v080-qa")
    assert remounted.primary.path == first.primary.path == str(primary_path)
    assert remounted.campaign.guard.path == first.campaign.guard.path == str(
        budget_dir / "budget-v080-qa.sqlite3"
    )
    assert remounted.primary.spent() == pytest.approx(0.3)
    assert remounted.campaign.guard.spent() == pytest.approx(0.1)
    assert remounted.remaining() == pytest.approx(0.4)
    with pytest.raises(BudgetExceeded):
        remounted.reserve(request_id="t73-over", agent="judge", model="test", amount=0.41)
    assert remounted.primary.spent() == pytest.approx(0.3)
    assert remounted.campaign.guard.spent() == pytest.approx(0.1)

    lower_cap = budget_dir / "budget-v080-qa.sqlite3"
    with pytest.raises(ValueError):
        FixedBudgetGuard(lower_cap, 0.49, cap_id="v080-qa", cap_ceiling_usd=0.5)
    with pytest.raises(SystemExit, match="unsupported campaign"):
        cli._evaluation_budget_guard(isolated, "other-qa")

def test_paid_sample_refuses_isolated_runtime_without_a_persistent_budget_dir(settings, tmp_path, monkeypatch):
    from pydantic import SecretStr

    isolated = settings.model_copy(
        update={
            "data_dir": tmp_path / "data",
            "runtime_dir": tmp_path / "runtime-isolated",
            "budget_runtime_dir": None,
            "deepseek_api_key": SecretStr("synthetic-deepseek-key"),
        }
    )
    monkeypatch.setattr(cli, "_eval_judge", lambda *args, **kwargs: pytest.fail("provider initialized"))
    args = eval_args(tmp_path, scripted=False, judge=True, include_replan=True, limit=5, no_conversations=True)
    with pytest.raises(SystemExit, match="BUDGET_RUNTIME_DIR"):
        cli.cmd_eval(isolated, args)


def test_package_version_and_compose_services_are_ready_for_v080_qa():
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == __version__ == "0.10.0"
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert {"api", "ticketing", "mocks", "qdrant"} <= set(compose["services"])
