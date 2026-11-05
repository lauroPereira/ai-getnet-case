"""v0.9.0 task 79 (spec D1 to D5, RF-108, CA-56): the judge experiment, moments 1 to 3 of the story, offline.

A campaign is run with the scripted agent and the scripted judge (the "original" judge), a calibration sample of 24 is
drawn and rated, then the recorded answers of the sample are graded again by a Claude judge through the programmed
Anthropic provider (`eval --judge-repeat --only-sample`), and `eval-calibrate --import --judge` compares both judges
against the same human ratings. No network, no cost."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr

from merchant_assistant import cli, main
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.data.db import connect
from merchant_assistant.evaluation import calibration as cal
from merchant_assistant.evaluation.runner import load_cases, persist_judgements, run, summarize, write_report
from merchant_assistant.evaluation.scripted_judge import scripted_judge
from merchant_assistant.llm.base import NullMeter
from merchant_assistant.llm.scripted_anthropic import FIXED_JUDGEMENT, ScriptedAnthropic, judging, message
from merchant_assistant.testing import offline_orchestrator

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
CASES = 30
OPUS = "anthropic/claude-opus-5-5"
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
PER_JUDGEMENT = (3000 * 4.00 + 500 * 20.00) / 1e6  # the programmed usage at the Opus 5.5 prices


def fill(sample, filled) -> None:
    """The owner's ratings: fixed, with four answers marked as an unsupported claim (rows 1, 7, 13 and 19)."""
    table = list(csv.reader(io.StringIO(sample.read_bytes().decode("utf-8-sig"), newline=""), delimiter=";"))
    at = next(i for i, row in enumerate(table) if row and row[0] == "sample_id")
    for number, row in enumerate(table[at + 1 :]):
        ratings = {"groundedness": "4", "factual_correctness": str(3 + number % 3), "relevance": "5"}
        ratings |= {"usefulness": "4", "unsupported_claim": "sim" if number % 6 == 0 else "nao"}
        for column, value in ratings.items():
            row[table[at].index(column)] = value
    with filled.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, delimiter=";", lineterminator="\r\n").writerows(table)


@pytest.fixture
def experiment(settings, tmp_path):
    """The v0.8.0 state: a judged campaign, its report, a sample of 24 rated by the owner and imported."""
    names = ("challenge_examples.jsonl", "core_cases.jsonl", "business_journeys.jsonl")
    cases = load_cases([SCENARIOS / name for name in names])[:CASES]
    orchestrator, _ = offline_orchestrator(settings)
    judge = scripted_judge(PROJECT_ROOT / "prompts", NullMeter())
    rows = run(orchestrator, cases, judge=judge)
    _, report = write_report(rows, summarize(rows), tmp_path / "out", "original", {"mode": "scripted"})
    conn = connect(settings.db_path)
    persist_judgements(conn, judge, rows)
    sample_rows, meta = cal.make_sample(report, 24, cal.DEFAULT_SEED)
    sample, filled = tmp_path / "amostra.csv", tmp_path / "amostra-preenchida.csv"
    cal.write_csv(sample, sample_rows, meta)
    fill(sample, filled)
    first = cal.import_filled(conn, filled, now=NOW)
    conn.close()
    return {"report": report, "csv": filled, "first": first, "ids": cal.sample_request_ids(filled)}


@pytest.fixture
def opus(settings, tmp_path, monkeypatch):
    """Settings of the experiment (own Anthropic ledger, D5) and the programmed provider behind the factory."""
    provider = ScriptedAnthropic(judging())
    monkeypatch.setattr(main, "anthropic_client", lambda settings: provider.client)
    experiment_settings = settings.model_copy(
        update={
            "judge_provider": "anthropic",
            "judge_model": "claude-opus-5-5",
            "anthropic_api_key": SecretStr("test-key"),
            "budget_runtime_dir": tmp_path / "anthropic",
            "budget_limit_usd": 4.0,
        }
    )
    return experiment_settings, provider


def eval_args(tmp_path, **overrides) -> argparse.Namespace:
    values = {
        "scripted": False,
        "judge": False,
        "split": "all",
        "out": str(tmp_path / "out"),
        "name": "v090-juiz-opus-r3",
        "no_conversations": True,
        "repeat": 1,
        "judge_repeat": 3,
        "answers_from": None,
        "only_sample": None,
        "limit": None,
    }
    return argparse.Namespace(**(values | overrides))


def stored(settings, provider: str) -> list[sqlite3.Row]:
    conn = connect(settings.db_path)
    try:
        return conn.execute(
            "SELECT * FROM run_evaluations WHERE json_extract(evaluator,'$.provider')=? ORDER BY created_at, rowid",
            (provider,),
        ).fetchall()
    finally:
        conn.close()


def test_moments_1_and_2_the_probe_and_the_72_judgements_of_the_sample(experiment, opus, tmp_path, capsys):
    settings, provider = opus
    probe = eval_args(
        tmp_path,
        name="v090-juiz-opus-sonda",
        judge_repeat=1,
        answers_from=str(experiment["report"]),
        only_sample=str(experiment["csv"]),
        limit=3,
    )
    assert cli.cmd_eval(settings, probe) == 0
    err = capsys.readouterr().err
    assert "grading 3 of 30 recorded answers (24 request ids in amostra-preenchida.csv), --limit 3" in err
    assert json.loads(provider.requests[0]["messages"][0]["content"])["reply"]  # the recorded evidence, as it was
    assert len(stored(settings, "anthropic")) == 3

    full = eval_args(tmp_path, answers_from=str(experiment["report"]), only_sample=str(experiment["csv"]))
    assert cli.cmd_eval(settings, full) == 0
    report = json.loads((tmp_path / "out" / "v090-juiz-opus-r3.json").read_text(encoding="utf-8"))
    assert [row["request_id"] for row in report["cases"]] == experiment["ids"]  # the CSV's order
    selection = ("only_sample", "only_sample_ids", "recorded_answers", "selected_answers")
    assert [report["config"][key] for key in selection] == ["amostra-preenchida.csv", 24, 30, 24]
    assert report["config"]["judge_config"]["provider"] == "anthropic"
    assert report["config"]["judge_config"]["independence"] == "different_provider"
    assert report["summary"]["variation"]["overall"]["judgements"] == 72
    text = (tmp_path / "out" / "v090-juiz-opus-r3.md").read_text(encoding="utf-8")
    assert "Respostas julgadas: 24 de 30 gravadas, filtradas pelos 24 request_id de `amostra-preenchida.csv`." in text
    assert "## Variação: variação do juiz" in text
    rows = stored(settings, "anthropic")
    assert len(rows) == 75 and sum(1 for r in rows if r["repetition"] == 3) == 24
    assert all(json.loads(r["evaluator"])["model"] == "claude-opus-5-5" for r in rows)
    # D5: every reservation went to the Anthropic ledger, none to the project's
    ledger = sqlite3.connect(tmp_path / "anthropic" / "budget.sqlite3")
    entries = ledger.execute("SELECT model, status, actual_usd FROM ledger").fetchall()
    ledger.close()
    assert len(entries) == 75 and {(m, s) for m, s, _ in entries} == {("claude-opus-5-5", "settled")}
    assert sum(a for _, _, a in entries) == pytest.approx(75 * PER_JUDGEMENT)
    project = sqlite3.connect(settings.runtime_path / "budget.sqlite3")  # opened by the offline agent run
    assert project.execute("SELECT COUNT(*) FROM ledger WHERE model LIKE 'claude%'").fetchone()[0] == 0
    project.close()


def test_a_refusal_or_a_cut_judgement_is_counted_as_a_failure(experiment, opus, tmp_path):
    settings, provider = opus

    def handler(body):  # the calls follow the CSV's order: the first is refused, the second is cut
        calls = len(provider.requests)
        if calls == 1:
            return message("", stop_reason="refusal")
        if calls == 2:
            return message('{"groundedness": 4', stop_reason="max_tokens")
        return message(json.dumps(FIXED_JUDGEMENT))

    provider.handler = handler
    args = eval_args(
        tmp_path, judge_repeat=1, answers_from=str(experiment["report"]), only_sample=str(experiment["csv"]), limit=4
    )
    assert cli.cmd_eval(settings, args) == 0
    graded = json.loads((tmp_path / "out" / "v090-juiz-opus-r3.json").read_text(encoding="utf-8"))
    states = [row["judge"]["state"] for row in graded["cases"]]
    assert states == ["failed", "failed", "completed", "completed"]
    assert "refusal" in graded["cases"][0]["judge"]["error"] and "max_tokens" in graded["cases"][1]["judge"]["error"]
    assert graded["summary"]["overall"]["judge_failed"] == 2
    assert "2 julgamentos falharam" in (tmp_path / "out" / "v090-juiz-opus-r3.md").read_text(encoding="utf-8")
    rows = stored(settings, "anthropic")
    assert [r["state"] for r in rows] == states and rows[0]["scores"] is None and rows[0]["unsupported_claim"] is None


def test_only_sample_refuses_a_csv_whose_ids_are_not_in_the_answers(experiment, opus, tmp_path):
    settings, provider = opus
    other = tmp_path / "other.csv"
    other.write_text("sample_id;request_id\nS01;req_missing\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="1 of the 1 request ids of other.csv are not among the recorded answers"):
        cli.cmd_eval(settings, eval_args(tmp_path, answers_from=str(experiment["report"]), only_sample=str(other)))
    with pytest.raises(SystemExit, match="--limit must be at least 1"):
        cli.cmd_eval(settings, eval_args(tmp_path, answers_from=str(experiment["report"]), limit=0))
    assert provider.requests == [] and stored(settings, "anthropic") == []


def test_moment_3_both_judges_against_the_same_human_ratings(experiment, opus, tmp_path, capsys):
    settings, _ = opus
    full = eval_args(tmp_path, answers_from=str(experiment["report"]), only_sample=str(experiment["csv"]))
    assert cli.cmd_eval(settings, full) == 0
    out = tmp_path / "v090-juiz-opus.md"
    calibrate = argparse.Namespace(
        sample=None,
        source=None,
        import_csv=str(experiment["csv"]),
        seed=None,
        campaign="v090-juiz-opus",
        rater="owner",
        delimiter=";",
        out=str(out),
        judge=OPUS,
    )
    assert cli.cmd_eval_calibrate(settings, calibrate) == 0
    printed = capsys.readouterr().out
    assert "judges: anthropic/claude-opus-5-5 (campaign v090-juiz-opus) beside scripted/scripted-judge-v3" in printed
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Calibração humana do juiz: dois juízes (v0.9.0)")
    assert "A = `anthropic/claude-opus-5-5` (campanha `v090-juiz-opus`); B = `scripted/scripted-judge-v3`" in text
    assert "| Critério | Exata A | Exata B |" in text
    assert "| A `anthropic/claude-opus-5-5` | 0 | 4 | 0 | 20 |" in text  # the verdict matrix of the requested judge
    # consistency: Opus graded each of the 24 answers 3 times (3 pairs each); the original judge once (no pair)
    assert "| A `anthropic/claude-opus-5-5` | 24 | 72 | 0 | groundedness | 1.0 | 1.0 | 72 |" in text
    assert "| B `scripted/scripted-judge-v3` | 24 | 24 | 0 | groundedness | - | - | 0 |" in text
    assert f"| A `anthropic/claude-opus-5-5` | 72 | 0 | {72 * PER_JUDGEMENT:.6f} | {PER_JUDGEMENT:.6f} |" in text
    conn = connect(settings.db_path)
    try:
        linked = conn.execute(
            "SELECT c.campaign, json_extract(e.evaluator,'$.provider') FROM calibrations c "
            "JOIN run_evaluations e ON e.evaluation_id=c.evaluation_id"
        ).fetchall()
        counts: dict[tuple, int] = {}
        for campaign, provider in linked:
            counts[(campaign, provider)] = counts.get((campaign, provider), 0) + 1
        assert counts == {("original", "scripted"): 24, ("v090-juiz-opus", "anthropic"): 24}
        # without --judge, the v0.8.0 report is the same as before the Claude judgements existed
        again = cal.import_filled(conn, experiment["csv"], now=NOW)
        assert again["report"] == experiment["first"]["report"]
    finally:
        conn.close()


def test_the_comparison_refuses_other_ratings_the_original_campaign_name_and_a_judge_without_judgements(
    experiment, opus, tmp_path
):
    settings, _ = opus
    conn = connect(settings.db_path)
    try:
        with pytest.raises(cal.CalibrationError, match="não há julgamento do juiz anthropic/claude-opus-5-5"):
            cal.import_filled(conn, experiment["csv"], campaign="v090-juiz-opus", judge=OPUS)
        with pytest.raises(cal.CalibrationError, match="informe --campaign com um nome novo"):
            cal.import_filled(conn, experiment["csv"], campaign="original", judge=OPUS)
        with pytest.raises(cal.CalibrationError, match="<provedor>/<modelo>"):
            cal.import_filled(conn, experiment["csv"], campaign="v090-juiz-opus", judge="claude-opus-5-5")
        changed = tmp_path / "changed.csv"
        text = experiment["csv"].read_bytes().decode("utf-8-sig")
        changed.write_bytes(text.replace(";4;", ";2;", 1).encode("utf-8-sig"))
        with pytest.raises(cal.CalibrationError, match="difere da gravada na campanha original"):
            cal.import_filled(conn, changed, campaign="v090-juiz-opus", judge=OPUS)
        assert conn.execute("SELECT COUNT(*) FROM calibrations WHERE campaign='v090-juiz-opus'").fetchone()[0] == 0
    finally:
        conn.close()
