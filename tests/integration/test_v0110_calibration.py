"""Task 89 (spec v0.11.0 D4, D5, D6; CA-61, CA-62): the calibration with two raters, through the command line.

A campaign run with the scripted agent and judge (`judge.v3`), the same answers graded again under `judge.v5`; an
earlier sample with packets (its claims from the recorded v5 judgements); a new sample that leaves the earlier one out,
is enriched and sealed (its claims listed by the scripted `judge_claims.v1` call); two raters return the files and the
import measures them against both blocks, with the gold label and the D6 line. Round 2: the v5 judgement made with the
sample's own claims (`eval --claims-from`) pairs every gold claim, where a judge that lists them again in other words
pairs none. No network, no cost."""

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
from merchant_assistant.evaluation import calibration_packets as packets
from merchant_assistant.evaluation import scripted_judge

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
CASE_IDS = ["EX01", "EX02", "EX03", "UC14"]  # knowledge, web, support with tools, handoff
SOURCE_FILES = ("challenge_examples.jsonl", "core_cases.jsonl", "business_journeys.jsonl")
JUDGE = "scripted/scripted-judge-v3"
KINDS = {"owner": "owner:human", "second": "second:model:gpt-x+claude-y"}  # round 3 (Q22): declared kinds


def scenario_lines(*ids: str) -> list[str]:
    wanted, found = set(ids), {}
    for name in SOURCE_FILES:
        for line in (SCENARIOS / name).read_text(encoding="utf-8").splitlines():
            if line.strip() and (row_id := json.loads(line)["id"]) in wanted:
                found[row_id] = line
    return [found[i] for i in ids]


@pytest.fixture
def project(tmp_path, monkeypatch, settings):
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
    return {"root": root, "out": tmp_path / "out", "db": runtime / "merchant.sqlite3"}


def table(path) -> list[list[str]]:
    return list(csv.reader(io.StringIO(path.read_bytes().decode("utf-8-sig"), newline=""), delimiter=";"))


def save(path, rows) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, delimiter=";", lineterminator="\r\n").writerows(rows)


def rate(sample, *, verdict: str | None = None) -> None:
    rows = table(sample)
    at = next(i for i, row in enumerate(rows) if row and row[0] == "sample_id")
    head = rows[at]
    for row in rows[at + 1 :]:
        values = {"groundedness": "5", "factual_correctness": "5", "relevance": "4", "usefulness": "4"}
        values |= {"unsupported_claim": verdict} if verdict else {}
        for column, value in values.items():
            row[head.index(column)] = value
    save(sample, rows)


def mark(claims, generic_first: bool) -> None:
    """Every claim supported; with `generic_first`, the first claim that is not standard is generic."""
    rows = table(claims)
    at = next(i for i, row in enumerate(rows) if row and row[0] == "sample_id")
    head = rows[at]
    done = False
    for row in rows[at + 1 :]:
        flag = generic_first and not done and row[head.index("kind")] != "standard"
        row[head.index("verdict")] = "generic" if flag else "supported"
        done = done or flag
    save(claims, rows)


def type_verdicts(sample) -> None:
    """A model rater (the panel) types its verdict, as its marks give it: its verdict comes from the column alone
    (task 89 round 5, P2-1)."""
    claims = table(sample.with_name("sample-claims.csv"))
    at = next(i for i, row in enumerate(claims) if row and row[0] == "sample_id")
    head = claims[at]
    flagged = {
        row[0]
        for row in claims[at + 1 :]
        if row and row[head.index("kind")] != "standard" and row[head.index("verdict")] in {"generic", "not_found"}
    }
    rows = table(sample)
    at = next(i for i, row in enumerate(rows) if row and row[0] == "sample_id")
    for row in rows[at + 1 :]:
        if row:
            row[rows[at].index("unsupported_claim")] = "sim" if row[0] in flagged else "nao"
    save(sample, rows)


def copy(source, target) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())


def test_two_raters_end_to_end_from_the_command_line(project, settings, tmp_path, monkeypatch, capsys):
    out = project["out"]
    given = [
        "eval",
        "--scripted",
        "--judge",
        "--rubric",
        "v3",
        "--no-conversations",
        "--out",
        str(out),
        "--name",
        "campanha-v3",
    ]
    assert cli.main(given) == 0
    campaign = out / "campanha-v3.json"
    given = ["eval", "--scripted", "--judge-repeat", "1", "--rubric", "v5", "--answers-from", str(campaign)]
    assert cli.main([*given, "--out", str(out), "--name", "rejulgamento-v5"]) == 0

    # the earlier sample: its claims come from the recorded v5 judgements
    old = tmp_path / "antiga" / "sample.csv"
    given = ["eval-calibrate", "--sample", "2", "--from", str(out / "rejulgamento-v5.json"), "--campaign", "antiga"]
    assert cli.main([*given, "--packets", "--out", str(old)]) == 0
    assert "(gravadas-2)" in capsys.readouterr().out
    old_cases = {row[-1] for row in table(old) if row and row[0].startswith("S")}

    # the new sample leaves the earlier answers and cases out, is enriched in a route left and sealed
    report = json.loads(campaign.read_text(encoding="utf-8"))
    left = sorted({row["route"] for row in report["cases"] if row["id"] not in old_cases})
    new = tmp_path / "selada" / "sample.csv"
    given = ["eval-calibrate", "--sample", "2", "--from", str(campaign), "--exclude", str(old), "--enrich", left[0]]
    given += ["--seed", "5", "--seal", "--scripted", "--campaign", "v0110-qa", "--out", str(new)]
    assert cli.main(given) == 0
    printed = capsys.readouterr().out
    assert "excluded: 2 answers already calibrated" in printed and "judge_claims.v1-scripted" in printed
    seal = project["root"] / packets.SEAL_FILE
    assert seal.exists() and packets.read_seal(seal) in printed
    assert not {row[-1] for row in table(new) if row and row[0].startswith("S")} & old_cases
    assert len(list(new.with_name("sample-pacotes").glob("S*.md"))) == 2

    # two raters: owner rates the sealed sample (claims) and the earlier one (verdict in the CSV); second rates both
    files = {}
    for rater in ("owner", "second"):
        for name, sample in (("selada", new), ("antiga", old)):
            target = tmp_path / rater / name / "sample.csv"
            copy(sample, target)
            copy(sample.with_name("sample-claims.csv"), target.with_name("sample-claims.csv"))
            files[(rater, name)] = target
    rate(files[("owner", "selada")])
    mark(files[("owner", "selada")].with_name("sample-claims.csv"), generic_first=True)
    rate(files[("second", "selada")])
    mark(files[("second", "selada")].with_name("sample-claims.csv"), generic_first=True)
    rate(files[("owner", "antiga")], verdict="nao")
    rate(files[("second", "antiga")])
    mark(files[("second", "antiga")].with_name("sample-claims.csv"), generic_first=False)
    for name in ("selada", "antiga"):
        type_verdicts(files[("second", name)])

    runtime = settings.model_copy(update={"runtime_dir": project["db"].parent})  # where eval --scripted stored them
    monkeypatch.setattr(cli, "get_settings", lambda: runtime)
    result = tmp_path / "calibracao.md"
    given = ["eval-calibrate", "--import"]
    for rater, name in (("owner", "selada"), ("owner", "antiga"), ("second", "selada"), ("second", "antiga")):
        path = files[(rater, name)]
        claims = [] if (rater, name) == ("owner", "antiga") else [str(path.with_name("sample-claims.csv"))]
        given += ["--rater", KINDS[rater], str(path), *claims]
    given += ["--judge", JUDGE, "--judge-run", "campanha-v3", "--rubric", "v3"]
    given += ["--judge", JUDGE, "--judge-run", "rejulgamento-v5", "--rubric", "v5", "--out", str(result)]
    assert cli.main(given) == 0
    printed = capsys.readouterr().out
    assert "answers: 4 rated, 4 by both raters, 4 with a gold label, 2 sealed; adjudicated: 0" in printed
    text = result.read_text(encoding="utf-8")
    assert "## Seladas (2 respostas)" in text and "## Todas (4 respostas)" in text
    assert "`calibration_v0110` conferido" in text and "| ouro × juiz B |" in text
    # the scripted judge lists the same claims at sample time and in the v5 judgement: every gold claim has its pair
    sections = [part.split("\n### ", 1)[0] for part in text.split("### Por afirmação")[1:]]
    rows = [line for part in sections for line in part.splitlines() if line.startswith("| ouro × juiz B | ")]
    assert len(rows) == 2 and all(row.rstrip().endswith("| 0 |") for row in rows)
    assert "Regra D6(g)" in text and f"Sem bloco `judge.v3` com `{cal.D2_JUDGE}`" in text


def test_the_rater_option_keeps_the_v080_form_and_takes_files(project, monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "cmd_eval_calibrate", lambda settings, args: seen.append(args) or 0)
    assert cli.main(["eval-calibrate", "--import", "a.csv", "--rater", "lauro"]) == 0
    assert seen[-1].import_csv == "a.csv" and cli._calibrate_raters(seen[-1]) == [["lauro"]]
    given = ["eval-calibrate", "--import", "--rater", "a", "s.csv", "c.csv", "--rater", "b", "t.csv"]
    assert cli.main([*given, "--adjudication", "adj.csv"]) == 0
    assert seen[-1].import_csv == "" and seen[-1].adjudication == "adj.csv"
    assert cli._calibrate_raters(seen[-1]) == [["a", "s.csv", "c.csv"], ["b", "t.csv"]]
    assert cli.main(["eval-calibrate", "--import", "x.csv"]) == 0 and cli._calibrate_raters(seen[-1]) == [["owner"]]


def claim_rows(text: str, pair: str) -> list[str]:
    """The `| <pair> | ...` rows of the claim tables of a report, one per block of answers."""
    sections = [part.split("\n### ", 1)[0] for part in text.split("### Por afirmação")[1:]]
    return [line for part in sections for line in part.splitlines() if line.startswith(f"| {pair} | ")]


def test_claims_from_pairs_every_gold_claim_by_number(project, settings, tmp_path, monkeypatch, capsys):
    out = project["out"]
    assert cli.main(
        ["eval", "--scripted", "--judge", "--rubric", "v3", "--no-conversations", "--out", str(out), "--name", "base"]
    ) == 0
    campaign = out / "base.json"
    sample = tmp_path / "amostra" / "sample.csv"
    given = ["eval-calibrate", "--sample", "4", "--from", str(campaign), "--packets", "--scripted"]
    assert cli.main([*given, "--campaign", "v0110-qa", "--out", str(sample)]) == 0
    claims = sample.with_name("sample-claims.csv")
    listed = sum(1 for row in table(claims) if row and row[0].startswith("S") and row[2])
    assert listed > 4

    # from here on, a judge that lists the claims again words them otherwise
    calls = []
    original = scripted_judge.claims_handler

    def reworded(data):
        calls.append(1)
        found = original(data)
        return {"claims": [claim | {"text": "Em outras palavras: " + claim["text"]} for claim in found["claims"]]}

    monkeypatch.setattr(scripted_judge, "claims_handler", reworded)
    rejudge = ["eval", "--scripted", "--judge-repeat", "1", "--rubric", "v5", "--answers-from", str(campaign)]
    rejudge += ["--only-sample", str(sample), "--out", str(out)]
    assert cli.main([*rejudge, "--claims-from", str(claims), "--name", "v5-amostra"]) == 0
    printed = capsys.readouterr().out
    assert not calls and "judging the claims of sample-claims.csv (4 answers, no listing call)" in printed
    assert json.loads((out / "v5-amostra.json").read_text(encoding="utf-8"))["config"]["claims_from"] == [
        "sample-claims.csv"
    ]
    assert cli.main([*rejudge, "--name", "v5-relista"]) == 0
    assert len(calls) == 4

    conn = sqlite3.connect(project["db"])
    try:
        origins = [
            json.loads(found).get("origin")
            for (found,) in conn.execute("SELECT claims FROM run_evaluations WHERE claims IS NOT NULL")
        ]
    finally:
        conn.close()
    assert sorted(o is not None for o in origins) == [False] * 4 + [True] * 4
    assert all(o.startswith("amostra:sample-claims.csv#") for o in origins if o)

    files = {}
    for rater in ("owner", "second"):
        target = tmp_path / rater / "sample.csv"
        copy(sample, target)
        copy(claims, target.with_name("sample-claims.csv"))
        rate(target)
        mark(target.with_name("sample-claims.csv"), generic_first=True)
        if rater == "second":
            type_verdicts(target)
        files[rater] = target
    runtime = settings.model_copy(update={"runtime_dir": project["db"].parent})
    monkeypatch.setattr(cli, "get_settings", lambda: runtime)
    result = tmp_path / "calibracao.md"
    given = ["eval-calibrate", "--import"]
    for rater, path in files.items():
        given += ["--rater", KINDS[rater], str(path), str(path.with_name("sample-claims.csv"))]
    given += ["--judge", JUDGE, "--judge-run", "v5-amostra", "--rubric", "v5"]
    given += ["--judge", JUDGE, "--judge-run", "v5-relista", "--rubric", "v5", "--out", str(result)]
    assert cli.main(given) == 0
    text = result.read_text(encoding="utf-8")
    assert f"com marca ouro: {listed}." in text
    # every gold claim has its pair when the judge read the sample's list; none when it listed them again
    assert claim_rows(text, "ouro × juiz A") == [claim_rows(text, "ouro × juiz A")[0]]
    assert claim_rows(text, "ouro × juiz A")[0].startswith(f"| ouro × juiz A | {listed} |")
    assert claim_rows(text, "ouro × juiz A")[0].rstrip().endswith("| 0 |")
    assert claim_rows(text, "ouro × juiz B")[0] == f"| ouro × juiz B | 0 | - | - | - | - | {listed} |"
    assert "Bloco A: 4 de 4 julgamentos receberam a lista de afirmações da amostra" in text


def test_the_merge_panel_option_takes_two_claims_csvs_and_two_sample_csvs(project, monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "cmd_eval_calibrate", lambda settings, args: seen.append(args) or 0)
    given = ["eval-calibrate", "--merge-panel", "a-claims.csv", "b-claims.csv", "--sample-csv", "a.csv", "b.csv"]
    assert cli.main([*given, "--out", "painel.csv"]) == 0
    assert seen[-1].merge_panel == ["a-claims.csv", "b-claims.csv"] and seen[-1].sample_csv == ["a.csv", "b.csv"]
    assert seen[-1].out == "painel.csv" and seen[-1].import_csv is None and seen[-1].sample is None
    with pytest.raises(SystemExit):
        cli.main(["eval-calibrate", "--merge-panel", "a-claims.csv", "--out", "painel.csv"])
