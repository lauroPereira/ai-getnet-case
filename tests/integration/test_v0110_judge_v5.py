"""Task 88 (spec v0.11.0 D3, CA-61): `--rubric v5` in `eval`, `eval --judge-repeat` and `eval-calibrate --import`, run
through the command line with the scripted agent and the scripted judge answering both calls. The report keeps the
aggregation of v3 (the verdict stays a boolean) and adds, per answer, the claims by verdict. No network, no cost."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import tempfile

import pytest

from merchant_assistant import cli
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation import calibration as cal
from merchant_assistant.evaluation.judge import CLAIM_VERDICTS

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


@pytest.fixture
def project(tmp_path, monkeypatch, settings):
    """A temporary project root with four real dev cases; the scripted runtime lands in one known directory."""
    root = tmp_path / "project"
    scenarios = root / "tests" / "scenarios"
    scenarios.mkdir(parents=True)
    (scenarios / "challenge_examples.jsonl").write_text("\n".join(scenario_lines(*CASE_IDS[:3])) + "\n", "utf-8")
    (scenarios / "core_cases.jsonl").write_text("\n".join(scenario_lines("UC14")) + "\n", encoding="utf-8")
    for name in ("business_journeys.jsonl", "replan.jsonl"):
        (scenarios / name).write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    runtime = tmp_path / "scripted-runtime"
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix="": runtime.mkdir(exist_ok=True) or str(runtime))
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    return {"out": tmp_path / "out", "db": runtime / "merchant.sqlite3"}


def report(project, name) -> dict:
    return json.loads((project["out"] / f"{name}.json").read_text(encoding="utf-8"))


def markdown(project, name) -> str:
    return (project["out"] / f"{name}.md").read_text(encoding="utf-8")


def evaluate(project, name, *extra) -> int:
    given = ["eval", "--scripted", "--judge", "--no-conversations", "--out", str(project["out"]), "--name", name]
    return cli.main([*given, *extra])


def test_eval_rubric_v5_keeps_the_aggregation_and_reports_the_claims_of_each_answer(project):
    assert evaluate(project, "under-v3", "--rubric", "v3") == 0
    assert evaluate(project, "under-v5", "--rubric", "v5") == 0
    v3, v5 = report(project, "under-v3"), report(project, "under-v5")
    config = v5["config"]["judge_config"]
    assert (config["rubric_version"], config["prompt"], config["claims_prompt"]) == ("5", "judge@5", "judge_claims@1")
    assert "claims_prompt" not in v3["config"]["judge_config"]

    # the same aggregation: the scripted v5 verdict is the scripted v3 verdict, case by case
    def by_case(rows):
        return {row["id"]: (row["judge"]["unsupported_claim"], row["judge"]["scores"]) for row in rows}

    assert by_case(v5["cases"]) == by_case(v3["cases"])
    for key in ("judge_means", "unsupported_claim_rate", "judge_failed", "n"):
        assert v5["summary"]["overall"][key] == v3["summary"]["overall"][key], key
    assert all(row["judge"]["state"] == "completed" and row["judge"]["claims"] for row in v5["cases"])
    total = v5["summary"]["overall"]["claim_verdicts"]
    assert total["claims"] == sum(len(row["judge"]["claims"]["claims"]) for row in v5["cases"]) > 0
    assert sum(total[verdict] for verdict in CLAIM_VERDICTS) == total["claims"]
    assert "claim_verdicts" not in v3["summary"]["overall"]
    # the tokens of both calls are in each judgement
    assert all(row["judge"]["usage"]["output_tokens"] == 120 for row in v5["cases"])

    text = markdown(project, "under-v5")
    assert "## Afirmações por veredito (judge.v5)" in text
    assert "| Caso | Rep | Julgamento | Afirmações | supported | partial | generic | not_found | standard |" in text
    for row in v5["cases"]:
        counts = [str(len(row["judge"]["claims"]["claims"]))]
        verdicts = [v["verdict"] for v in row["judge"]["claims"]["claim_verdicts"]]
        counts += [str(verdicts.count(verdict)) for verdict in CLAIM_VERDICTS]
        assert f"| {row['id']} | 1 | 1 | {' | '.join(counts)} |" in text
    assert "## Afirmações por veredito" not in markdown(project, "under-v3")
    # the line of the means and of the unsupported-claim rate is the v3 one, with the same numbers
    rate = v3["summary"]["overall"]["unsupported_claim_rate"]
    assert "Rubrica por modelo (média 1-5, não é revisão humana)" in text and f"Afirmações sem suporte: {rate}" in text

    stored = sqlite3.connect(project["db"])
    stored.row_factory = sqlite3.Row
    rows = stored.execute("SELECT * FROM run_evaluations WHERE json_extract(evaluator, '$.run') = 'under-v5'")
    rows = rows.fetchall()
    assert len(rows) == 4 and {row["rubric_version"] for row in rows} == {"5"}
    assert all(json.loads(row["claims"]) == json.loads(row["result"])["claims"] for row in rows)
    assert {json.loads(row["evaluator"])["claims_prompt"] for row in rows} == {"judge_claims@1"}
    legacy = stored.execute("SELECT claims FROM run_evaluations WHERE json_extract(evaluator, '$.run') = 'under-v3'")
    assert {row["claims"] for row in legacy} == {None}
    stored.close()


def test_judge_repeat_under_v5_grades_the_recorded_answers_with_both_calls(project):
    assert evaluate(project, "answers") == 0
    answers = str(project["out"] / "answers.json")
    given = ["eval", "--scripted", "--judge-repeat", "2", "--rubric", "v5", "--answers-from", answers]
    assert cli.main([*given, "--out", str(project["out"]), "--name", "rejudged-v5"]) == 0
    graded = report(project, "rejudged-v5")
    assert graded["config"]["judge_config"]["rubric_version"] == "5" and graded["config"]["judge_repeat"] == 2
    runs = [record for row in graded["cases"] for record in row["judge_runs"]]
    assert len(runs) == 8 and all(record["rubric_version"] == "5" and record["claims"] for record in runs)
    assert graded["summary"]["variation"]["kind"] == "judge"
    text = markdown(project, "rejudged-v5")
    assert "## Afirmações por veredito (judge.v5)" in text and text.count(f"| {CASE_IDS[0]} | 1 | 2 |") == 1


def test_eval_calibrate_accepts_rubric_v5_and_refuses_an_unknown_one(project, monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "cmd_eval_calibrate", lambda settings, args: seen.append(args) or 0)
    given = ["eval-calibrate", "--import", "filled.csv", "--judge", "deepseek/deepseek-flash", "--rubric", "v5"]
    assert cli.main(given) == 0 and seen[0].rubric == ["v5"]
    assert cal._rubric("v5") == "5" and cli._calibrate_blocks(seen[0]) == [("deepseek/deepseek-flash", None, "v5")]
    with pytest.raises(SystemExit) as refused:
        cli.main([*given[:-1], "v6"])
    assert refused.value.code == 2  # argparse: not a choice
    with pytest.raises(SystemExit):
        evaluate(project, "unknown", "--rubric", "v6")


def fill(sample, filled) -> None:
    """The owner's ratings of the sample: the first answer marked as an unsupported claim, the others not."""
    table = list(csv.reader(io.StringIO(sample.read_bytes().decode("utf-8-sig"), newline=""), delimiter=";"))
    at = next(i for i, row in enumerate(table) if row and row[0] == "sample_id")
    for number, row in enumerate(table[at + 1 :]):
        ratings = {"groundedness": "4", "factual_correctness": "4", "relevance": "5", "usefulness": "4"}
        ratings |= {"unsupported_claim": "sim" if number == 0 else "nao"}
        for column, value in ratings.items():
            row[table[at].index(column)] = value
    with filled.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, delimiter=";", lineterminator="\r\n").writerows(table)


def test_eval_calibrate_imports_the_v5_judgements_recorded_by_eval_scripted(project, monkeypatch, settings, tmp_path):
    """Review P3-4: end to end, no stub. The owner rates a sample of a judge.v3 campaign; `eval --scripted --rubric
    v5` grades the same recorded answers again; `eval-calibrate --import` reads those v5 judgements by default."""
    assert evaluate(project, "original", "--rubric", "v3") == 0
    source = project["out"] / "original.json"
    sample, filled, out = tmp_path / "amostra.csv", tmp_path / "amostra-preenchida.csv", tmp_path / "calibracao"
    given = ["eval-calibrate", "--sample", "4", "--from", str(source), "--campaign", "t88-original"]
    assert cli.main([*given, "--out", str(sample)]) == 0
    fill(sample, filled)
    runtime = settings.model_copy(update={"runtime_dir": project["db"].parent})  # where eval --scripted stored them
    monkeypatch.setattr(cli, "get_settings", lambda: runtime)
    assert cli.main(["eval-calibrate", "--import", str(filled), "--out", str(out / "original.md")]) == 0
    given = ["eval", "--scripted", "--judge-repeat", "1", "--rubric", "v5", "--answers-from", str(source)]
    assert cli.main([*given, "--out", str(project["out"]), "--name", "graded-v5"]) == 0

    judge = "scripted/scripted-judge-v3"
    given = [
        "eval-calibrate",
        "--import",
        str(filled),
        "--campaign",
        "t88-v5",
        "--judge",
        judge,
        "--judge-run",
        "graded-v5",
    ]
    assert cli.main([*given, "--out", str(out / "v5.md")]) == 0

    stored = sqlite3.connect(project["db"])
    stored.row_factory = sqlite3.Row
    linked = stored.execute(
        "SELECT c.rubric_version AS rated, e.rubric_version AS judged, e.claims, e.evaluator FROM calibrations c "
        "JOIN run_evaluations e ON e.evaluation_id = c.evaluation_id WHERE c.campaign = 't88-v5'"
    ).fetchall()
    original = stored.execute(
        "SELECT e.rubric_version FROM calibrations c JOIN run_evaluations e ON e.evaluation_id = c.evaluation_id "
        "WHERE c.campaign = 't88-original'"
    ).fetchall()
    stored.close()
    assert len(linked) == len(original) == 4 and {row[0] for row in original} == {"3"}
    assert {row["judged"] for row in linked} == {"5"} and all(json.loads(row["claims"]) for row in linked)
    assert {json.loads(row["evaluator"])["run"] for row in linked} == {"graded-v5"}
    text = (out / "v5.md").read_text(encoding="utf-8")
    assert "## Juízes e rubricas contra as mesmas notas humanas" in text
    assert f"| O | `{judge}` | `judge.v3` |" in text and f"| A | `{judge}` | `judge.v5` | `graded-v5` |" in text
    assert "## Regra histórica D2 da v0.10.0 (informativa)" in text
    assert "não governa `judge.v5`" in text and "D6(g) da v0.11.0" in text
