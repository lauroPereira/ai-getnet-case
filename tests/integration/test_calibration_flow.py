"""v0.8.0 task 71 (spec D10, D19): `eval-calibrate` from the command line, over a campaign run with the scripted agent
and the scripted judge. The sample CSV has no score of the judge; the filled file is validated line by line, stored in
`calibrations` linked to the judgement of the same request, and measured against it. No network, no cost."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
from pathlib import Path

import pytest

from merchant_assistant import cli
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.data.db import connect
from merchant_assistant.evaluation import calibration as cal
from merchant_assistant.evaluation.judge import CRITERIA
from merchant_assistant.evaluation.runner import (
    load_cases,
    persist_judgements,
    run,
    summarize,
    write_report,
)
from merchant_assistant.evaluation.scripted_judge import scripted_judge
from merchant_assistant.guardrails.input import mask_sensitive
from merchant_assistant.llm.base import NullMeter
from merchant_assistant.testing import offline_orchestrator

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
CASES = 30  # enough answers, in several routes and two splits, for a sample of 24


@pytest.fixture
def campaign(settings, tmp_path):
    """A campaign run offline with the scripted judge: its report, and its judgements in the runtime database."""
    names = ("challenge_examples.jsonl", "core_cases.jsonl", "business_journeys.jsonl")
    cases = load_cases([SCENARIOS / name for name in names])[:CASES]
    orchestrator, _ = offline_orchestrator(settings)
    judge = scripted_judge(PROJECT_ROOT / "prompts", NullMeter())
    rows = run(orchestrator, cases, judge=judge)
    _, report = write_report(rows, summarize(rows), tmp_path / "out", "avaliacao", {"mode": "scripted"})
    conn = connect(settings.db_path)
    assert persist_judgements(conn, judge, rows) == CASES
    conn.close()
    return report, rows


def args(**values) -> argparse.Namespace:
    base = {
        "sample": None,
        "source": None,
        "import_csv": None,
        "seed": None,
        "campaign": None,
        "rater": "owner",
        "delimiter": ";",
        "out": None,
    }
    return argparse.Namespace(**(base | values))


def table(path: Path, delimiter=";") -> list[list[str]]:
    return list(csv.reader(io.StringIO(path.read_bytes().decode("utf-8-sig"), newline=""), delimiter=delimiter))


def fill(path: Path, ratings, delimiter=";") -> None:
    """`ratings(record) -> dict` fills the human columns of every data row."""
    rows = table(path, delimiter)
    at = next(i for i, row in enumerate(rows) if row and row[0] == "sample_id")
    for row in rows[at + 1 :]:
        record = dict(zip(rows[at], row, strict=True))
        for column, value in ratings(record).items():
            row[rows[at].index(column)] = value
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, delimiter=delimiter, lineterminator="\r\n").writerows(rows)


def stored_judgements(settings) -> dict[str, dict]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    found = {
        row["request_id"]: dict(row)
        for row in conn.execute("SELECT request_id, evaluation_id, scores, unsupported_claim FROM run_evaluations")
    }
    conn.close()
    return found


def test_sample_fill_import_and_report_end_to_end(settings, tmp_path, campaign, capsys):
    report, rows = campaign
    out = tmp_path / "amostra.csv"
    assert cli.cmd_eval_calibrate(settings, args(sample=24, source=str(report), out=str(out))) == 0
    printed = capsys.readouterr().out
    assert f"sample: 24 answers of {CASES} eligible, seed {cal.DEFAULT_SEED}, campaign avaliacao" in printed

    # the sample: 24 answers, every route and split of the campaign that fits, no score of the judge
    data = [dict(zip(cal.COLUMNS, row, strict=True)) for row in table(out) if row and row[0].startswith("S")]
    assert len(data) == 24 and len({d["request_id"] for d in data}) == 24
    strata_in_campaign = {(r["route"], r["split"]) for r in rows}
    assert {(d["route"], d["split"]) for d in data} == strata_in_campaign  # fewer strata than draws: all appear
    text = out.read_bytes().decode("utf-8-sig")
    judged = {r["request_id"]: r["judge"] for r in rows}
    assert "Scripted judge" not in text and not any(j["evaluation_id"] in text for j in judged.values())
    assert not any(d[column] for d in data for column in cal.HUMAN_COLUMNS)
    for d in data:  # masked answers and messages: masking them again changes nothing
        for column in ("answer", "message", "evidence"):
            plain = d[column][1:] if d[column][:2] in {" =", " +", " -", " @"} else d[column]
            assert mask_sensitive(plain)[0] == plain

    # the owner rates: the judge's scores, except a few that she sees differently
    by_request = {r["request_id"]: r["judge"] for r in rows}
    sample_ids = [d["sample_id"] for d in data]
    skipped, off_by_two, opposite = sample_ids[0], sample_ids[1], sample_ids[2]

    def rating(record):
        if record["sample_id"] == skipped:
            return {}
        judge = by_request[record["request_id"]]
        values = {c: str(judge["scores"][c]) for c in CRITERIA}
        values["unsupported_claim"] = "sim" if judge["unsupported_claim"] else "nao"
        if record["sample_id"] == off_by_two:
            values["relevance"] = str(max(1, judge["scores"]["relevance"] - 2))
        if record["sample_id"] == opposite:
            values["unsupported_claim"] = "nao" if judge["unsupported_claim"] else "sim"
        return values

    fill(out, rating)
    final = tmp_path / "calibracao.md"
    assert cli.cmd_eval_calibrate(settings, args(import_csv=str(out), out=str(final), rater="lauro")) == 0
    assert "calibrations: 23 stored, 0 updated, 1 skipped (campaign avaliacao, rater lauro)" in capsys.readouterr().out

    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    stored = conn.execute("SELECT * FROM calibrations").fetchall()
    conn.close()
    links = stored_judgements(settings)
    assert len(stored) == 23 and skipped not in {r["sample_id"] for r in stored}
    assert {r["rater"] for r in stored} == {"lauro"}
    for row in stored:
        assert row["evaluation_id"] == links[row["request_id"]]["evaluation_id"] and row["rubric_version"] == "3"
    markdown = final.read_text(encoding="utf-8")
    assert "Ressalva de amostra pequena (D19): 23 respostas" in markdown
    assert "Campanha `avaliacao`, avaliador humano `lauro`" in markdown and f"semente {cal.DEFAULT_SEED}" in markdown
    assert "Sem avaliação (linhas puladas): 1" in markdown and "`scripted/scripted-judge-v3`" in markdown
    assert f"| {off_by_two} |" in markdown and "relevance | " in markdown  # the 2-point gap is listed
    # the exact agreement of a criterion, recomputed from the two tables of the database
    exact = sum(
        json.loads(row["scores"])["usefulness"] == json.loads(links[row["request_id"]]["scores"])["usefulness"]
        for row in stored
    )
    assert exact == 23 and "| usefulness (utilidade) | 23 | 1.000 (IC 95%:" in markdown
    relevance = next(line for line in markdown.splitlines() if line.startswith("| relevance (relevância) | 23 |"))
    assert " 0.957 (IC 95%:" in relevance  # 22 of 23 equal: the one off by two is the difference

    # the same file again changes the ratings in place
    assert cli.cmd_eval_calibrate(settings, args(import_csv=str(out), out=str(final), rater="lauro")) == 0
    assert "calibrations: 0 stored, 23 updated, 1 skipped" in capsys.readouterr().out
    conn = sqlite3.connect(settings.db_path)
    assert conn.execute("SELECT COUNT(*) FROM calibrations").fetchone()[0] == 23
    conn.close()


def test_a_wrong_line_stops_the_import_and_the_message_names_it(settings, tmp_path, campaign, monkeypatch):
    report, _ = campaign
    out = tmp_path / "amostra.csv"
    cli.cmd_eval_calibrate(settings, args(sample=24, source=str(report), out=str(out), delimiter=","))
    fill(
        out,
        lambda r: {
            "groundedness": "9" if r["sample_id"] == "S02" else "4",
            "factual_correctness": "4",
            "relevance": "4",
            "usefulness": "4",
            "unsupported_claim": "nao",
        },
        delimiter=",",
    )
    with pytest.raises(SystemExit) as stopped:
        cli.cmd_eval_calibrate(settings, args(import_csv=str(out), out=str(tmp_path / "calibracao.md")))
    message = str(stopped.value)
    assert (
        message.startswith("eval-calibrate: linha ")
        and "(S02): groundedness precisa ser um inteiro de 1 a 5" in message
    )
    assert "recebi '9'" in message and not (tmp_path / "calibracao.md").exists()
    conn = sqlite3.connect(settings.db_path)
    assert conn.execute("SELECT COUNT(*) FROM calibrations").fetchone()[0] == 0
    conn.close()

    monkeypatch.setattr(cal, "MAX_REPORTED_ERRORS", 5)  # a sample of 24 can have at most 24 wrong lines
    fill(
        out,
        lambda r: {
            "usefulness": "x",
            "groundedness": "4",
            "factual_correctness": "4",
            "relevance": "4",
            "unsupported_claim": "nao",
        },
        delimiter=",",
    )
    with pytest.raises(SystemExit) as many:
        cli.cmd_eval_calibrate(settings, args(import_csv=str(out)))
    lines = str(many.value).splitlines()
    assert len(lines) == 6 and lines[0].startswith("eval-calibrate: linha ") and lines[-1] == "(+19 more)"
    assert all("usefulness precisa ser um inteiro de 1 a 5, recebi 'x'" in line for line in lines[:5])


def test_the_arguments_are_checked_before_anything_happens(settings, tmp_path):
    with pytest.raises(SystemExit, match="choose --sample N --from <report.json>, or --import <csv>"):
        cli.cmd_eval_calibrate(settings, args())
    with pytest.raises(SystemExit, match="choose --sample N"):
        cli.cmd_eval_calibrate(settings, args(sample=24, import_csv="x.csv"))
    with pytest.raises(SystemExit, match="--sample needs --from"):
        cli.cmd_eval_calibrate(settings, args(sample=24))
    with pytest.raises(SystemExit, match=r"eval-calibrate: não consegui ler o relatório"):
        cli.cmd_eval_calibrate(settings, args(sample=24, source=str(tmp_path / "nao-existe.json")))
    with pytest.raises(SystemExit, match="no database at"):
        cli.cmd_eval_calibrate(settings, args(import_csv=str(tmp_path / "x.csv")))
    assert not settings.db_path.exists()  # a missing database is reported, not created


def test_the_default_files_are_the_ones_in_docs_evidence_and_a_short_sample_is_warned(
    settings, tmp_path, campaign, capsys, monkeypatch
):
    report, _ = campaign
    root = tmp_path / "project"
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    capsys.readouterr()
    cli.cmd_eval_calibrate(settings, args(sample=6, source=str(report), seed=99, campaign="v080 qa"))
    captured = capsys.readouterr()
    sample_file = root / "docs" / "evidence" / "v080-calibracao-amostra.csv"
    assert sample_file.exists() and "seed 99, campaign v080-qa" in captured.out
    assert "the sample has 6 answers; RF-91 asks for at least 24" in captured.err
    comments = " ".join(row[0] for row in table(sample_file) if row and row[0].startswith("#"))
    assert "campanha=v080-qa; semente=99;" in comments
    fill(
        sample_file,
        lambda r: {
            "groundedness": "5",
            "factual_correctness": "5",
            "relevance": "5",
            "usefulness": "5",
            "unsupported_claim": "nao",
        },
    )
    cli.cmd_eval_calibrate(settings, args(import_csv=str(sample_file)))
    assert (root / "docs" / "evidence" / "v080-calibracao.md").exists()
    markdown = (root / "docs" / "evidence" / "v080-calibracao.md").read_text(encoding="utf-8")
    assert "semente 99" in markdown and "Ressalva de amostra pequena (D19): 6 respostas" in markdown


def test_the_command_is_reachable_from_the_parser(settings, tmp_path, campaign, monkeypatch):
    report, _ = campaign
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    out = tmp_path / "pelo-parser.csv"
    assert cli.main(["eval-calibrate", "--sample", "5", "--from", str(report), "--out", str(out)]) == 0
    assert out.exists() and len([r for r in table(out) if r and r[0].startswith("S")]) == 5
    with pytest.raises(SystemExit):
        cli.main(["eval-calibrate", "--delimiter", "|", "--sample", "5"])
