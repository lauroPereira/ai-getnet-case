"""v0.8.0 task 70: the evaluation campaign. The agent repeats apart from the judge (D12), the judge reads the
evidence of each answer, the executed path is reported without touching `route_ok` (D16) and a split is reported on
its own (D14). Scripted model and scripted judge: no network, no cost. The sealed holdout is never opened here; the
split path is exercised with a synthetic `holdout_v080` split in a temporary scenario tree."""

from __future__ import annotations

import argparse
import itertools
import json
import sqlite3
import tempfile

import pytest

from merchant_assistant import cli
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.data.db import connect
from merchant_assistant.evaluation import aggregate
from merchant_assistant.evaluation.judge import CRITERIA, Judge
from merchant_assistant.evaluation.runner import (
    Case,
    _checks,
    executed_path,
    load_cases,
    persist_judgements,
    rejudge,
    run,
    summarize,
    write_report,
)
from merchant_assistant.evaluation.scripted_judge import handler as judge_handler
from merchant_assistant.evaluation.scripted_judge import scripted_judge
from merchant_assistant.llm.base import NullMeter
from merchant_assistant.llm.scripted import ScriptedLLM
from merchant_assistant.testing import offline_orchestrator

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
CASE_IDS = ["EX01", "EX02", "EX03", "UC14"]  # knowledge, web, support with tools, handoff
SOURCE_FILES = ("challenge_examples.jsonl", "core_cases.jsonl", "business_journeys.jsonl")


def scenario_lines(*ids: str) -> list[str]:
    wanted, found = set(ids), {}
    for name in SOURCE_FILES:
        for line in (SCENARIOS / name).read_text(encoding="utf-8").splitlines():
            if line.strip() and (row_id := json.loads(line)["id"]) in wanted:
                found[row_id] = line
    return [found[i] for i in ids]


def selected_cases() -> list[Case]:
    by_id = {case.id: case for case in load_cases([SCENARIOS / name for name in SOURCE_FILES])}
    return [by_id[i] for i in CASE_IDS]


def cycling_judge(prompts_dir=PROJECT_ROOT / "prompts") -> Judge:
    """A noisy judge: groundedness cycles 5, 4, 5 over its calls, so a case judged three times in a row gets 5, 4, 5."""
    counter = itertools.count()
    scale = (5, 4, 5)

    def noisy(call):
        return judge_handler(call) | {"groundedness": scale[next(counter) % 3]}

    return scripted_judge(prompts_dir, NullMeter(), ScriptedLLM(noisy, model="scripted-judge-v3"))


def agent_calls(llm, agent="router") -> int:
    return sum(1 for call in llm.calls if call.spec.agent == agent)


# --- D16: the executed path ----------


def test_executed_path_lists_the_specialists_that_ran_in_order():
    assert executed_path(["router", "knowledge", "customer_support", "personality"]) == "knowledge → customer_support"
    assert executed_path(["router", "knowledge", "knowledge", "personality"]) == "knowledge → knowledge"  # replanned
    assert executed_path(["router", "personality"]) == ""
    assert executed_path(["router", "customer_support", "escalation", "personality"]) == "customer_support → escalation"


def test_route_ok_still_compares_the_initial_plan_whatever_path_ran():
    case = Case("X1", "dev", "m", "pt", ["knowledge"], "answered", [], [], [], False)
    trace = {"steps": [], "detail": {}}
    body = {"answer": "a", "route": "knowledge", "status": "answered", "language": "pt", "sources": []}
    assert _checks(case, body, trace)["route_ok"] is True
    assert _checks(case, body | {"agents": ["router", "knowledge", "web", "personality"]}, trace)["route_ok"] is True
    assert _checks(case, body | {"route": "general_web", "agents": ["router", "knowledge"]}, trace)["route_ok"] is False


def test_each_row_reports_the_path_derived_from_its_agents_and_the_report_lists_the_paths(settings, tmp_path):
    orchestrator, _ = offline_orchestrator(settings)
    rows = run(orchestrator, selected_cases())
    assert all(row["executed_path"] == executed_path(row["agents"]) for row in rows)
    by_id = {row["id"]: row for row in rows}
    assert "customer_support" in by_id["EX03"]["executed_path"] and "escalation" in by_id["UC14"]["executed_path"]
    assert by_id["EX01"]["executed_path"] == "knowledge"
    assert all(row["route_ok"] for row in rows)  # the paths changed nothing in the verdict
    summary = summarize(rows)
    assert summary["paths"][by_id["EX01"]["route"]]["knowledge"] >= 1
    md, js = write_report(rows, summary, tmp_path, "paths", {"mode": "scripted"})
    text = md.read_text(encoding="utf-8")
    assert "## Rota planejada e caminho executado" in text and "| Rota | Caminho executado | Respostas |" in text
    assert json.loads(js.read_text(encoding="utf-8"))["cases"][0]["executed_path"] == "knowledge"


# --- D9: the judge reads the evidence of each answer ----------


def test_each_answer_is_judged_once_over_the_evidence_it_was_built_from(settings):
    orchestrator, _ = offline_orchestrator(settings)
    judge = scripted_judge(PROJECT_ROOT / "prompts", NullMeter())
    rows = run(orchestrator, selected_cases(), judge=judge)
    assert len(judge.llm.calls) == len(rows) == 4
    by_id = {row["id"]: row for row in rows}
    assert all(row["judge"]["state"] == "completed" and set(row["judge"]["scores"]) == set(CRITERIA) for row in rows)
    support = by_id["EX03"]["judge_input"]["evidence"]
    assert {item["label"] for item in support if item["kind"] == "tool_result"} >= {"get_receivables_schedule"}
    knowledge = by_id["EX01"]["judge_input"]["evidence"]
    assert knowledge and all(item["kind"] == "passage" and item["text"] for item in knowledge)
    for row in rows:
        assert row["judge_input"]["reply"] == row["answer"] and row["judge_input"]["sources"] == row["sources"]
        assert row["evidence_truncation"]["limit_chars"] == 6000 and "truncated" in row["evidence_truncation"]
    summary = summarize(rows)
    assert set(summary["overall"]["judge_means"]) == set(CRITERIA) and "unsupported_claim_rate" in summary["overall"]
    assert summary["judge_cost_usd"] == 0


def test_unsupported_claims_are_listed_one_by_one_and_never_only_averaged(settings, tmp_path):
    orchestrator, _ = offline_orchestrator(settings)
    cases = selected_cases()
    flagged_message = cases[2].message  # EX03

    def flags_one_case(call):
        data = json.loads(call.spec.input)
        return judge_handler(call) | {"unsupported_claim": data["merchant_message"] == flagged_message}

    judge = scripted_judge(
        PROJECT_ROOT / "prompts", NullMeter(), ScriptedLLM(flags_one_case, model="scripted-judge-v3")
    )
    rows = run(orchestrator, cases, judge=judge, repeat=2)
    md, _ = write_report(rows, summarize(rows), tmp_path, "flagged", {"mode": "scripted"})
    text = md.read_text(encoding="utf-8")
    assert "## Afirmações sem suporte (veredito crítico)" in text and "nunca diluídas na média" in text
    listed = [line for line in text.splitlines() if line.startswith("| EX03 | ") and "1 de 1" in line]
    assert len(listed) == 2 and [line.split(" | ")[1] for line in listed] == ["1", "2"]  # one line per repetition
    assert not any(
        line.startswith(f"| {case.id} | ") and "de 1" in line for case in cases[:2] for line in text.splitlines()
    )
    clean = scripted_judge(
        PROJECT_ROOT / "prompts", NullMeter(), ScriptedLLM(lambda c: judge_handler(c) | {"unsupported_claim": False})
    )
    quiet = run(orchestrator, cases[:1], judge=clean)
    md, _ = write_report(quiet, summarize(quiet), tmp_path, "quiet", {"mode": "scripted"})
    assert "veredito crítico" not in md.read_text(encoding="utf-8")


# --- D12: the two variations stay apart ----------


def test_repeat_runs_the_agent_n_times_and_the_judge_once_per_answer(settings):
    orchestrator, llm = offline_orchestrator(settings)
    judge = scripted_judge(PROJECT_ROOT / "prompts", NullMeter())
    rows = run(orchestrator, selected_cases(), judge=judge, repeat=3)
    assert [row["repetition"] for row in rows] == [1] * 4 + [2] * 4 + [3] * 4
    assert len({row["request_id"] for row in rows}) == 12
    assert agent_calls(llm, "router") == 12  # the agent answered every case three times
    assert len(judge.llm.calls) == 12 and all(row["judge"]["repetition"] == 1 for row in rows)  # one judgement each
    variation = aggregate.variation(rows, "assistant", 3)
    assert variation["kind"] == "assistant" and variation["overall"]["judgements"] == 12
    assert variation["overall"]["cases"] == 4
    with pytest.raises(ValueError):
        run(orchestrator, selected_cases(), repeat=0)


def test_judge_repeat_grades_the_recorded_answers_again_without_running_the_agent(settings):
    orchestrator, llm = offline_orchestrator(settings)
    first = run(orchestrator, selected_cases(), judge=scripted_judge(PROJECT_ROOT / "prompts", NullMeter()))
    agent_calls_before = len(llm.calls)
    noisy = cycling_judge()
    graded = rejudge(first, noisy, 3)
    assert len(llm.calls) == agent_calls_before  # the agent did not run again
    assert len(noisy.llm.calls) == 12
    assert [row["request_id"] for row in graded] == [row["request_id"] for row in first]
    assert all([r["repetition"] for r in row["judge_runs"]] == [1, 2, 3] for row in graded)
    assert all(
        row["cost_usd"] == 0.0 and row["answer"] == old["answer"] for row, old in zip(graded, first, strict=True)
    )
    variation = aggregate.variation(graded, "judge", 3)
    # every case scored 5, 4, 5: mean 14 / 3, std 0.5774, one equal pair of three, all within one point
    assert variation["kind"] == "judge" and variation["overall"]["criteria"]["groundedness"] == {
        "mean": 4.67,
        "std": 0.58,
        "exact": 0.333,
        "within_one": 1.0,
        "pairs": 12,
    }
    assert variation["overall"]["criteria"]["relevance"]["exact"] == 1.0  # only groundedness was noisy
    # the same noisy judge, used once per answer, shows no judge variation at all: the two sources are not mixed
    once = aggregate.variation(first, "assistant", 1)
    assert once["overall"]["criteria"]["groundedness"]["pairs"] == 0


def test_the_judge_report_does_not_carry_the_cost_of_the_agent_run(settings):
    orchestrator, _ = offline_orchestrator(settings)
    first = run(orchestrator, selected_cases()[:2], judge=scripted_judge(PROJECT_ROOT / "prompts", NullMeter()))
    for row in first:
        row["cost_usd"] = 0.0123  # the agent run was paid
    graded = rejudge(first, scripted_judge(PROJECT_ROOT / "prompts", NullMeter()), 2)
    assert all(g["cost_usd"] == 0.0 and g["source_cost_usd"] == 0.0123 for g in graded)
    assert summarize(graded)["overall"]["cost_usd"] == 0 and summarize(first)["overall"]["cost_usd"] == 0.0246


def test_every_judgement_is_stored_with_its_repetition_provider_and_model(settings, tmp_path):
    orchestrator, _ = offline_orchestrator(settings)
    judge = scripted_judge(PROJECT_ROOT / "prompts", NullMeter())
    graded = rejudge(run(orchestrator, selected_cases(), judge=judge), judge, 2)
    conn = connect(tmp_path / "campaign.sqlite3")
    assert persist_judgements(conn, judge, graded) == 8
    by_repetition = conn.execute("SELECT repetition, COUNT(*) FROM run_evaluations GROUP BY repetition").fetchall()
    assert [tuple(r) for r in by_repetition] == [(1, 4), (2, 4)]
    row = conn.execute("SELECT * FROM run_evaluations WHERE request_id=? AND repetition=2", (graded[0]["request_id"],))
    stored = row.fetchone()
    assert json.loads(stored["evaluator"])["provider"] == "scripted" and stored["rubric_version"] == "3"
    assert stored["evaluation_id"] == graded[0]["judge_runs"][1]["evaluation_id"]
    conn.close()


# --- the CLI ----------


@pytest.fixture
def scenario_tree(tmp_path, monkeypatch):
    """A temporary project root: four real dev cases plus a SYNTHETIC `holdout_v080` split (two cases written here)."""
    root = tmp_path / "project"
    scenarios = root / "tests" / "scenarios"
    scenarios.mkdir(parents=True)
    (scenarios / "challenge_examples.jsonl").write_text(
        "\n".join(scenario_lines(*CASE_IDS[:3])) + "\n", encoding="utf-8"
    )
    (scenarios / "core_cases.jsonl").write_text("\n".join(scenario_lines("UC14")) + "\n", encoding="utf-8")
    (scenarios / "business_journeys.jsonl").write_text("", encoding="utf-8")
    synthetic = []
    for new_id, line in zip(("SYN-H1", "SYN-H2"), scenario_lines("EX01", "EX03"), strict=True):
        synthetic.append(json.dumps(json.loads(line) | {"id": new_id, "split": "holdout_v080"}))
    (scenarios / "holdout_v080.jsonl").write_text("\n".join(synthetic) + "\n", encoding="utf-8")
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    runtime = tmp_path / "scripted-runtime"
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix="": runtime.mkdir(exist_ok=True) or str(runtime))
    return root


def eval_args(tmp_path, **overrides) -> argparse.Namespace:
    values = {
        "scripted": True,
        "judge": True,
        "split": "all",
        "out": str(tmp_path / "out"),
        "name": "campaign",
        "no_conversations": True,
        "repeat": 1,
        "judge_repeat": None,
        "answers_from": None,
    }
    return argparse.Namespace(**(values | overrides))


def read_report(tmp_path, name) -> dict:
    return json.loads((tmp_path / "out" / f"{name}.json").read_text(encoding="utf-8"))


def test_cli_repeat_then_judge_repeat_report_each_variation_on_its_own(settings, tmp_path, scenario_tree, monkeypatch):
    assert cli.cmd_eval(settings, eval_args(tmp_path, name="agent", repeat=2)) == 0
    agent = read_report(tmp_path, "agent")
    assert agent["config"]["repeat"] == 2 and agent["config"]["judge_config"]["provider"] == "scripted"
    assert agent["config"]["agent_provider"] == "scripted" and len(agent["cases"]) == 8
    assert agent["summary"]["variation"]["kind"] == "assistant" and agent["summary"]["variation"]["repetitions"] == 2
    assert all("judge_input" in row and row["judge"]["state"] == "completed" for row in agent["cases"])
    text = (tmp_path / "out" / "agent.md").read_text(encoding="utf-8")
    assert "## Variação: variação do assistente" in text and "Ressalva de amostra pequena (D19)" in text
    stored = sqlite3.connect(tmp_path / "scripted-runtime" / "merchant.sqlite3")
    assert stored.execute("SELECT COUNT(*) FROM run_evaluations WHERE rubric_version='3'").fetchone()[0] == 8
    stored.close()

    from merchant_assistant import testing

    def agent_must_not_run(*args, **kwargs):
        raise AssertionError("--judge-repeat must not run the agent")

    monkeypatch.setattr(testing, "offline_orchestrator", agent_must_not_run)
    answers = str(tmp_path / "out" / "agent.json")
    assert (
        cli.cmd_eval(settings, eval_args(tmp_path, name="judge", judge=False, judge_repeat=3, answers_from=answers))
        == 0
    )
    judged = read_report(tmp_path, "judge")
    assert judged["config"]["judge_repeat"] == 3 and judged["config"]["answers_from"] == "agent.json"
    assert len(judged["cases"]) == 4 and all(len(row["judge_runs"]) == 3 for row in judged["cases"])  # first execution
    assert judged["summary"]["variation"]["kind"] == "judge" and judged["summary"]["overall"]["cost_usd"] == 0
    assert "## Variação: variação do juiz" in (tmp_path / "out" / "judge.md").read_text(encoding="utf-8")
    assert [row["request_id"] for row in judged["cases"]] == [
        row["request_id"] for row in agent["cases"] if row["repetition"] == 1
    ]


def test_repeat_without_a_judge_records_the_evidence_for_a_later_judge_repeat(settings, tmp_path, scenario_tree):
    assert cli.cmd_eval(settings, eval_args(tmp_path, name="agent-only", judge=False, repeat=2)) == 0
    recorded = read_report(tmp_path, "agent-only")
    assert len(recorded["cases"]) == 8 and "variation" not in recorded["summary"]
    assert all("judge_input" in row and "judge" not in row for row in recorded["cases"])
    answers = str(tmp_path / "out" / "agent-only.json")
    args = eval_args(tmp_path, name="judged", judge=False, judge_repeat=2, answers_from=answers)
    assert cli.cmd_eval(settings, args) == 0
    judged = read_report(tmp_path, "judged")
    assert len(judged["cases"]) == 4 and all(len(row["judge_runs"]) == 2 for row in judged["cases"])
    assert [row["request_id"] for row in judged["cases"]] == [
        row["request_id"] for row in recorded["cases"] if row["repetition"] == 1
    ]


def test_report_names_do_not_overwrite_each_other_and_a_judge_run_never_replaces_its_answers(
    settings, tmp_path, scenario_tree, capsys
):
    assert cli._report_name(argparse.Namespace(name=None, split="all", judge_repeat=None)) == "avaliacao"
    assert cli._report_name(argparse.Namespace(name=None, split="dev", judge_repeat=None)) == "avaliacao"
    assert cli._report_name(argparse.Namespace(name=None, split="holdout_v080", judge_repeat=None)) == (
        "avaliacao-holdout-v080"
    )
    assert cli._report_name(argparse.Namespace(name=None, split="all", judge_repeat=3)) == "avaliacao-juiz"
    assert cli._report_name(argparse.Namespace(name="mine", split="holdout_v080", judge_repeat=None)) == "mine"
    assert cli.cmd_eval(settings, eval_args(tmp_path, name=None, split="holdout_v080")) == 0
    assert (tmp_path / "out" / "avaliacao-holdout-v080.json").exists()
    assert not (tmp_path / "out" / "avaliacao.json").exists()  # the development report keeps its name

    assert cli.cmd_eval(settings, eval_args(tmp_path, name="agent")) == 0
    answers = tmp_path / "out" / "agent.json"
    before = answers.read_bytes()
    args = eval_args(tmp_path, name="agent", judge=False, judge_repeat=2, answers_from=str(answers))
    with pytest.raises(SystemExit, match="would overwrite the answers being graded"):
        cli.cmd_eval(settings, args)
    assert answers.read_bytes() == before
    capsys.readouterr()
    args = eval_args(tmp_path, name=None, split="dev", judge=False, judge_repeat=2, answers_from=str(answers))
    assert cli.cmd_eval(settings, args) == 0
    assert "--split is ignored with --judge-repeat" in capsys.readouterr().err
    assert (tmp_path / "out" / "avaliacao-juiz.json").exists()


def test_the_markdown_escapes_pipes_and_line_breaks_and_summarises_the_truncation(settings, tmp_path):
    orchestrator, _ = offline_orchestrator(settings)
    cases = selected_cases()

    def flags_with_a_pipe(call):
        return judge_handler(call) | {"unsupported_claim": True, "groundedness_reason": "taxa | prazo\nsegunda linha"}

    judge = scripted_judge(PROJECT_ROOT / "prompts", NullMeter(), ScriptedLLM(flags_with_a_pipe))
    rows = run(orchestrator, cases, judge=judge)
    rows[0]["evidence_truncation"] = rows[0]["evidence_truncation"] | {"truncated": True}
    rows[1]["id"] = "EX|02"
    md, _ = write_report(rows, summarize(rows), tmp_path, "escaped", {"mode": "scripted"})
    lines = md.read_text(encoding="utf-8").splitlines()
    flagged = [line for line in lines if line.startswith(f"| {cases[0].id} | 1 | ") and "de 1 |" in line]
    assert len(flagged) == 1 and flagged[0].endswith("taxa \\| prazo segunda linha |")
    assert not any(line.startswith("segunda linha") for line in lines)  # the line break did not leak out of the cell
    assert any(line.startswith("| EX\\|02 | ") for line in lines)
    assert "Evidência truncada em 1 de 4 respostas (limite de 6000 caracteres" in "\n".join(lines)


def test_the_two_repetition_options_are_not_combined_and_judge_repeat_needs_recorded_answers(settings, tmp_path):
    with pytest.raises(SystemExit, match="not combined"):
        cli.cmd_eval(settings, eval_args(tmp_path, repeat=2, judge_repeat=3, answers_from="x.json"))
    with pytest.raises(SystemExit, match="needs --answers-from"):
        cli.cmd_eval(settings, eval_args(tmp_path, judge_repeat=3))
    with pytest.raises(SystemExit, match="--repeat must be at least 1"):
        cli.cmd_eval(settings, eval_args(tmp_path, repeat=0))
    with pytest.raises(SystemExit, match="eval:"):
        cli.cmd_eval(settings, eval_args(tmp_path, judge_repeat=3, answers_from=str(tmp_path / "missing.json")))
    orchestrator, _ = offline_orchestrator(settings)
    plain = run(orchestrator, selected_cases()[:1])  # a run without judge and without recorded evidence
    write_report(plain, summarize(plain), tmp_path / "out", "plain", {"mode": "scripted", "model": "scripted-v1"})
    with pytest.raises(SystemExit, match="did not record the evidence of 1 answer"):
        cli.cmd_eval(settings, eval_args(tmp_path, judge_repeat=3, answers_from=str(tmp_path / "out" / "plain.json")))


def test_a_judge_equal_to_the_agent_or_without_a_key_is_refused_before_anything_is_built(
    settings, tmp_path, monkeypatch
):
    from pydantic import SecretStr

    import merchant_assistant.main as main

    def nothing_may_be_built(*args, **kwargs):
        raise AssertionError("the judge must be refused before the system is built")

    monkeypatch.setattr(main, "build_orchestrator", nothing_may_be_built)
    real = eval_args(tmp_path, scripted=False)
    with pytest.raises(SystemExit) as no_key:
        cli.cmd_eval(settings, real)
    assert str(no_key.value).startswith("eval: ") and "DEEPSEEK_API_KEY" in str(no_key.value)
    same = settings.model_copy(
        update={
            "openai_api_key": SecretStr("synthetic-openai-key"),
            "judge_provider": "openai",
            "judge_model": settings.agent_model,
        }
    )
    with pytest.raises(SystemExit, match="same model as the agent"):
        cli.cmd_eval(same, real)
    assert not (tmp_path / "out").exists() and not settings.runtime_path.joinpath("budget.sqlite3").exists()


def test_an_installation_with_only_an_openai_key_is_refused_by_eval_judge_before_any_call(
    settings, tmp_path, monkeypatch
):
    """P2-01: the campaign judge needs the DeepSeek key; the /v1 evaluator (openai/gpt-6-luna) does not."""
    from pydantic import SecretStr

    import merchant_assistant.main as main

    def nothing_may_run(*args, **kwargs):
        raise AssertionError("no system and no model client may be built for a refused judge")

    for name in ("build_orchestrator", "openai_client", "deepseek_client"):
        monkeypatch.setattr(main, name, nothing_may_run)
    only_openai = settings.model_copy(
        update={"openai_api_key": SecretStr("synthetic-openai-key"), "deepseek_api_key": None}
    )
    assert (only_openai.evaluator_provider, only_openai.evaluator_model) == ("openai", "gpt-6-luna")
    with pytest.raises(SystemExit) as refused:
        cli.cmd_eval(only_openai, eval_args(tmp_path, scripted=False))
    message = str(refused.value)
    assert message.startswith("eval: ") and "DEEPSEEK_API_KEY" in message
    assert "does not switch to another judge" in message and message.endswith("No call was made.")
    assert not (tmp_path / "out").exists()


def test_judge_repeat_in_real_mode_is_refused_without_the_judge_key_before_the_budget_is_touched(
    settings, tmp_path, scenario_tree
):
    assert cli.cmd_eval(settings, eval_args(tmp_path, name="agent", repeat=1)) == 0
    answers = str(tmp_path / "out" / "agent.json")
    with pytest.raises(SystemExit, match="DEEPSEEK_API_KEY"):
        cli.cmd_eval(settings, eval_args(tmp_path, scripted=False, judge_repeat=3, answers_from=answers, name="real"))
    assert not settings.runtime_path.joinpath("budget.sqlite3").exists()
    assert not (tmp_path / "out" / "real.json").exists()


def test_a_split_is_reported_on_its_own_and_the_holdout_split_is_never_part_of_all(settings, tmp_path, scenario_tree):
    assert cli.cmd_eval(settings, eval_args(tmp_path, name="everything", split="all")) == 0
    everything = read_report(tmp_path, "everything")
    assert sorted(row["id"] for row in everything["cases"]) == sorted(CASE_IDS)  # no synthetic holdout case
    assert set(everything["summary"]["by_split"]) == {"dev", "holdout"}

    args = eval_args(tmp_path, name="holdout", split="holdout_v080", repeat=2, no_conversations=False)
    assert (
        cli.cmd_eval(settings, args) == 0
    )  # no followup.jsonl in the tree: the conversations do not run for this split
    held = read_report(tmp_path, "holdout")
    assert {row["id"] for row in held["cases"]} == {"SYN-H1", "SYN-H2"} and held["config"]["split"] == "holdout_v080"
    assert set(held["summary"]["by_split"]) == {"holdout_v080"}
    assert set(held["summary"]["variation"]["by_split"]) == {"holdout_v080"}
    assert "conversations" not in held
    assert "| split holdout_v080 |" in (tmp_path / "out" / "holdout.md").read_text(encoding="utf-8")


def test_a_report_with_two_splits_keeps_their_summaries_and_variations_apart(settings):
    orchestrator, _ = offline_orchestrator(settings)
    judge = scripted_judge(PROJECT_ROOT / "prompts", NullMeter())
    cases = selected_cases()
    cases[2:] = [Case(**{**case.__dict__, "split": "holdout_synthetic"}) for case in cases[2:]]
    rows = run(orchestrator, cases, judge=judge, repeat=2)
    summary = summarize(rows)
    assert {k: v["n"] for k, v in summary["by_split"].items()} == {"dev": 4, "holdout_synthetic": 4}
    data = aggregate.variation(rows, "assistant", 2)
    assert {k: v["cases"] for k, v in data["by_split"].items()} == {"dev": 2, "holdout_synthetic": 2}
