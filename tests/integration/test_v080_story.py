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

    higher_budget = tmp_path / "separate-project-budget"
    higher_estimate = tmp_path / "higher-estimate.json"
    higher_estimate.write_text(json.dumps({"estimated_cost_usd": 0.75}), encoding="utf-8")
    higher_settings = isolated.model_copy(update={"budget_runtime_dir": higher_budget})
    larger = cli._evaluation_budget_guard(
        higher_settings,
        "v080-qa",
        campaign_cap_usd=1.0,
        estimate_report=higher_estimate,
    )
    assert larger.remaining() == pytest.approx(1.0)


def test_paid_sample_refuses_isolated_runtime_without_a_persistent_budget_dir(settings, tmp_path, monkeypatch):
    isolated = settings.model_copy(
        update={
            "data_dir": tmp_path / "data",
            "runtime_dir": tmp_path / "runtime-isolated",
            "budget_runtime_dir": None,
        }
    )
    monkeypatch.setattr(cli, "_eval_judge", lambda *args, **kwargs: pytest.fail("provider initialized"))
    args = eval_args(tmp_path, scripted=False, judge=True, include_replan=True, limit=5, no_conversations=True)
    with pytest.raises(SystemExit, match="BUDGET_RUNTIME_DIR"):
        cli.cmd_eval(isolated, args)


def test_package_version_and_compose_services_are_ready_for_v080_qa():
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == __version__ == "0.8.0"
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert {"api", "ticketing", "mocks", "qdrant"} <= set(compose["services"])
