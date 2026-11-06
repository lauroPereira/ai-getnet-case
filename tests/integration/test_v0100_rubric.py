"""v0.10.0 task 83 (spec D1, D2, CA-57): moments 1 to 3 of the story, offline.

The v0.8.0 state is rebuilt with a DeepSeek judge under `judge.v3` (programmed: the scripted model behind the real
factory), a calibration sample of 24 rated by the owner and imported. Then the 24 recorded answers are graded again
under `judge.v4` by DeepSeek and by Opus (`eval --judge-repeat --rubric v4`), Opus also under `judge.v3`, and
`eval-calibrate --import` with three `--judge` blocks compares the four blocks against the same human ratings. No
network, no cost."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr

from merchant_assistant import cli, main
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.data.db import connect
from merchant_assistant.evaluation import calibration as cal
from merchant_assistant.evaluation.judge import Judge
from merchant_assistant.evaluation.runner import load_cases, persist_judgements, run, summarize, write_report
from merchant_assistant.llm.base import NullMeter
from merchant_assistant.llm.prompts import load_prompt
from merchant_assistant.llm.scripted import ScriptedLLM
from merchant_assistant.llm.scripted_anthropic import FIXED_JUDGEMENT, ScriptedAnthropic, judging
from merchant_assistant.testing import offline_orchestrator

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
PROMPTS = PROJECT_ROOT / "prompts"
DEEPSEEK = "deepseek/deepseek-flash"
OPUS = "anthropic/claude-opus-5-5"
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
V4_SENTENCE = "a general claim stated as fact with no source in the evidence"


def fill(sample, filled) -> None:
    """The owner's ratings, as in v0.9.0: four answers marked as an unsupported claim (S01, S07, S13 and S19)."""
    table = list(csv.reader(io.StringIO(sample.read_bytes().decode("utf-8-sig"), newline=""), delimiter=";"))
    at = next(i for i, row in enumerate(table) if row and row[0] == "sample_id")
    for number, row in enumerate(table[at + 1 :]):
        ratings = {"groundedness": "4", "factual_correctness": str(3 + number % 3), "relevance": "5"}
        ratings |= {"usefulness": "4", "unsupported_claim": "sim" if number % 6 == 0 else "nao"}
        for column, value in ratings.items():
            row[table[at].index(column)] = value
    with filled.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, delimiter=";", lineterminator="\r\n").writerows(table)


def key(data: dict) -> tuple[str, str]:
    return data["merchant_message"], data["reply"]


def deepseek_answer(flagged: set) -> callable:
    """The programmed DeepSeek: the fixed judgement; under judge.v4 it also marks the answers in `flagged` (and
    lowers their groundedness to 2, so the ±1 agreement of that criterion drops by 2 of 24)."""

    def answer(call) -> dict:
        data = json.loads(call.spec.input)
        if V4_SENTENCE in " ".join(call.spec.instructions.split()) and key(data) in flagged:
            return dict(FIXED_JUDGEMENT, groundedness=2, unsupported_claim=True)
        return dict(FIXED_JUDGEMENT)

    return answer


@pytest.fixture
def experiment(settings, tmp_path):
    """The v0.8.0 state with DeepSeek as the original judge (judge.v3, fixed judgement, no claim marked)."""
    names = ("challenge_examples.jsonl", "core_cases.jsonl", "business_journeys.jsonl")
    cases = load_cases([SCENARIOS / name for name in names])[:30]
    orchestrator, _ = offline_orchestrator(settings)
    llm = ScriptedLLM(deepseek_answer(set()), model="deepseek-flash")
    original = Judge(llm, "deepseek", "deepseek-flash", load_prompt(PROMPTS, "judge", "3"), NullMeter(), "x")
    rows = run(orchestrator, cases, judge=original)
    _, report = write_report(rows, summarize(rows), tmp_path / "out", "original", {"mode": "scripted"})
    conn = connect(settings.db_path)
    persist_judgements(conn, original, rows)
    conn.execute("UPDATE run_evaluations SET created_at='2026-11-04T12:00:00+00:00'")
    sample_rows, meta = cal.make_sample(report, 24, cal.DEFAULT_SEED)
    sample, filled = tmp_path / "amostra.csv", tmp_path / "amostra-preenchida.csv"
    cal.write_csv(sample, sample_rows, meta)
    fill(sample, filled)
    cal.import_filled(conn, filled, now=NOW)
    conn.close()
    ids = cal.sample_request_ids(filled)
    given = {row["request_id"]: row["judge_input"] for row in json.loads(report.read_text("utf-8"))["cases"]}
    position = {f"S{number:02d}": key(given[request_id]) for number, request_id in enumerate(ids, start=1)}
    return {"report": report, "csv": filled, "ids": ids, "position": position}


@pytest.fixture
def judges(settings, tmp_path, monkeypatch, experiment):
    """DeepSeek and Opus behind the real factory: DeepSeek under judge.v4 marks S01 and S13; Opus under judge.v4
    marks S01, S13 and S16, and keeps its scores."""
    at = experiment["position"]
    real = main.model_factory

    def factory(settings):
        inner = real(settings)

        def build(provider, model):
            if provider == "deepseek":
                return ScriptedLLM(deepseek_answer({at["S01"], at["S13"]}), model=model)
            return inner(provider, model)

        return build

    def opus_answer(data: dict) -> dict:
        flagged = {at["S01"], at["S13"], at["S16"]}
        return dict(FIXED_JUDGEMENT, unsupported_claim=key(data) in flagged and opus_answer.v4)

    opus_answer.v4 = False
    provider = ScriptedAnthropic(judging(opus_answer))
    original_handler = provider.handler

    def handler(body):  # the rubric is in the system prompt the SDK sends
        opus_answer.v4 = V4_SENTENCE in " ".join(json.dumps(body["system"]).split())
        return original_handler(body)

    provider.handler = handler
    monkeypatch.setattr(main, "model_factory", factory)
    monkeypatch.setattr(main, "anthropic_client", lambda settings: provider.client)
    deepseek = settings.model_copy(
        update={"deepseek_api_key": SecretStr("test-key"), "budget_runtime_dir": tmp_path / "project"}
    )
    opus = settings.model_copy(
        update={
            "judge_provider": "anthropic",
            "judge_model": "claude-opus-5-5",
            "anthropic_api_key": SecretStr("test-key"),
            "budget_runtime_dir": tmp_path / "anthropic",
            "budget_limit_usd": 4.0,
        }
    )
    return deepseek, opus, provider


def eval_args(experiment, tmp_path, name: str, **overrides) -> argparse.Namespace:
    values = {
        "scripted": False,
        "judge": False,
        "split": "all",
        "out": str(tmp_path / "out"),
        "name": name,
        "no_conversations": True,
        "repeat": 1,
        "judge_repeat": 3,
        "answers_from": str(experiment["report"]),
        "only_sample": str(experiment["csv"]),
        "limit": None,
    }
    return argparse.Namespace(**(values | overrides))


def stored(settings, run_name: str) -> list:
    conn = connect(settings.db_path)
    try:
        return conn.execute(
            "SELECT * FROM run_evaluations WHERE json_extract(evaluator,'$.run')=? ORDER BY created_at, rowid",
            (run_name,),
        ).fetchall()
    finally:
        conn.close()


def grade_all(experiment, judges, tmp_path) -> None:
    deepseek, opus, _ = judges
    assert cli.cmd_eval(deepseek, eval_args(experiment, tmp_path, "v0100-juiz-deepseek-v4", rubric="v4")) == 0
    assert cli.cmd_eval(opus, eval_args(experiment, tmp_path, "v090-juiz-opus-r3")) == 0  # no --rubric: judge.v3
    assert cli.cmd_eval(opus, eval_args(experiment, tmp_path, "v0100-juiz-opus-v4", rubric="v4")) == 0


def test_moments_1_and_2_the_v4_judgements_of_both_judges_record_their_rubric(experiment, judges, tmp_path):
    deepseek, opus, provider = judges
    grade_all(experiment, judges, tmp_path)
    for run_name, provider_name, version in (
        ("v0100-juiz-deepseek-v4", "deepseek", "4"),
        ("v090-juiz-opus-r3", "anthropic", "3"),
        ("v0100-juiz-opus-v4", "anthropic", "4"),
    ):
        rows = stored(deepseek, run_name)
        assert len(rows) == 72 and {r["state"] for r in rows} == {"completed"}
        assert {r["rubric_version"] for r in rows} == {version}
        evaluators = [json.loads(r["evaluator"]) for r in rows]
        assert {(e["provider"], e["rubric_version"], e["prompt"]) for e in evaluators} == {
            (provider_name, version, f"judge@{version}")
        }
        report = json.loads((tmp_path / "out" / f"{run_name}.json").read_text(encoding="utf-8"))
        assert report["config"]["judge_config"]["rubric_version"] == version
        assert [row["request_id"] for row in report["cases"]] == experiment["ids"]
    # what each provider received: the v3 prompt in the r3, the v4 prompt in the v4 run (72 calls each)
    systems = [V4_SENTENCE in " ".join(json.dumps(body["system"]).split()) for body in provider.requests]
    assert systems == [False] * 72 + [True] * 72
    flagged = [r for r in stored(opus, "v0100-juiz-opus-v4") if r["unsupported_claim"]]
    assert len(flagged) == 9  # S01, S13 and S16, three repetitions each


def calibrate_args(experiment, out, **overrides) -> argparse.Namespace:
    values = {
        "sample": None,
        "source": None,
        "import_csv": str(experiment["csv"]),
        "seed": None,
        "campaign": "v0100-juiz-v4",
        "rater": "owner",
        "delimiter": ";",
        "out": str(out),
        "judge": [DEEPSEEK, OPUS, OPUS],
        "judge_run": ["v0100-juiz-deepseek-v4", "v090-juiz-opus-r3", "v0100-juiz-opus-v4"],
        "rubric": ["v4", "v3", "v4"],
    }
    return argparse.Namespace(**(values | overrides))


def test_moment_3_four_blocks_against_the_same_human_ratings_with_the_d2_line(
    experiment, judges, tmp_path, capsys
):
    deepseek, _, _ = judges
    grade_all(experiment, judges, tmp_path)
    out = tmp_path / "v0100-juiz-v4.md"
    capsys.readouterr()
    assert cli.cmd_eval_calibrate(deepseek, calibrate_args(experiment, out)) == 0
    printed = capsys.readouterr().out
    assert "block O: deepseek/deepseek-flash judge.v3 (execution legado)" in printed
    assert "block C: anthropic/claude-opus-5-5 judge.v4 (execution v0100-juiz-opus-v4)" in printed
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Calibração humana do juiz: juízes e rubricas (v0.10.0)")
    assert "rubrica `judge.v4`, juiz `deepseek/deepseek-flash`." in text  # the first block's header
    for row in (
        "| O | `deepseek/deepseek-flash` | `judge.v3` | `legado` |",
        "| A | `deepseek/deepseek-flash` | `judge.v4` | `v0100-juiz-deepseek-v4` |",
        "| B | `anthropic/claude-opus-5-5` | `judge.v3` | `v090-juiz-opus-r3` |",
        "| C | `anthropic/claude-opus-5-5` | `judge.v4` | `v0100-juiz-opus-v4` |",
    ):
        assert row in text
    # agreement per block: the v4 DeepSeek lowered groundedness on its two marks (2 of 24 now off by 2 points)
    assert "| groundedness (fundamentação) | O `deepseek/deepseek-flash` judge.v3 | 1.000 | 1.000 |" in text
    assert "| groundedness (fundamentação) | A `deepseek/deepseek-flash` judge.v4 | 0.917 | 0.917 |" in text
    # verdict: the human marked S01, S07, S13 and S19
    assert "| O `deepseek/deepseek-flash` judge.v3 | 0.833 | 0.000 (sem intervalo) | 0 | 4 | 0 | 20 |" in text
    assert "| A `deepseek/deepseek-flash` judge.v4 | 0.917 |" in text and "| 2 | 2 | 0 | 20 |" in text
    assert "| C `anthropic/claude-opus-5-5` judge.v4 | 0.875 |" in text and "| 2 | 2 | 1 | 19 |" in text
    # the four general claims, with the verdict of each block, and the count
    assert "## Frases genéricas sem fonte (S01, S13, S16, S21)" in text
    assert "| Amostra | Caso | Rota | Humano | O | A | B | C |" in text
    assert "| Marcadas | - | - | 2 de 4 | 0 de 4 | 2 de 4 | 0 de 4 | 3 de 4 |" in text
    generic = text.split("## Frases genéricas sem fonte")[1].split("Respostas que o humano")[0]
    assert [line.split(" | ")[0] for line in generic.splitlines() if line.startswith("| S")] == [
        "| S01",
        "| S13",
        "| S16",
        "| S21",
    ]
    assert " | sim | não | sim | não | sim |" in generic  # S01 (and S13): human, DeepSeek v4 and Opus v4
    # D2, computed and not decided: A against O fails (c), C against B holds all three
    assert "## Regra D2 da v0.10.0 (informativa)" in text and "A decisão é registrada na tarefa 86." in text
    assert (
        "- A `deepseek/deepseek-flash` judge.v4 contra O `deepseek/deepseek-flash` judge.v3: (a) veredito 0.917 "
        "contra 0.833, não cai: sim; (b) frases genéricas marcadas: 2 de 4, pelo menos 2: sim; (c) ±1 groundedness "
        "0.917 contra 1.000 (-0.083), factual_correctness 1.000 contra 1.000 (+0.000), relevance 1.000 contra 1.000 "
        "(+0.000), usefulness 1.000 contra 1.000 (+0.000), nenhum piora mais de 0.05: não. Três condições "
        "atendidas: não."
    ) in text
    assert (
        "- C `anthropic/claude-opus-5-5` judge.v4 contra B `anthropic/claude-opus-5-5` judge.v3: (a) veredito 0.875 "
        "contra 0.833, não cai: sim; (b) frases genéricas marcadas: 3 de 4, pelo menos 2: sim;"
    ) in text and text.count("Três condições atendidas: sim.") == 1
    # each block's own judgements: 72 for the repeated runs, 24 for the original
    assert "| O `deepseek/deepseek-flash` judge.v3 | `legado` | 24 | 24 | 24 |" in text
    assert "| A `deepseek/deepseek-flash` judge.v4 | `v0100-juiz-deepseek-v4` | 24 | 72 | 72 |" in text
    assert "| C `anthropic/claude-opus-5-5` judge.v4 | 24 | 72 | 0 | unsupported_claim | 1.0 | - | 72 |" in text
    conn = connect(deepseek.db_path)
    try:
        linked = conn.execute(
            "SELECT c.rubric_version, e.rubric_version, json_extract(e.evaluator,'$.run') FROM calibrations c "
            "JOIN run_evaluations e ON e.evaluation_id=c.evaluation_id WHERE c.campaign='v0100-juiz-v4'"
        ).fetchall()
        assert [tuple(row) for row in linked] == [("4", "4", "v0100-juiz-deepseek-v4")] * 24
    finally:
        conn.close()


def test_rubric_v3_by_name_is_the_v090_report_and_bad_blocks_are_refused(experiment, judges, tmp_path):
    deepseek, _, _ = judges
    grade_all(experiment, judges, tmp_path)
    one = {"judge": OPUS, "judge_run": "v090-juiz-opus-r3"}
    plain, named = tmp_path / "plain.md", tmp_path / "named.md"
    conn = connect(deepseek.db_path)
    try:
        first = cal.import_filled(conn, experiment["csv"], campaign="v090-juiz-opus", now=NOW, **one)
        again = cal.import_filled(conn, experiment["csv"], campaign="v090-juiz-opus", now=NOW, rubric="3", **one)
    finally:
        conn.close()
    assert first["report"] == again["report"]  # --rubric v3 is the default: the v0.9.0 report, byte for byte
    assert first["report"].startswith("# Calibração humana do juiz: dois juízes (v0.9.0)")
    assert "blocks" not in first["comparison"]
    single = {"judge": [OPUS], "judge_run": ["v090-juiz-opus-r3"], "rubric": None, "campaign": "v090-juiz-opus"}
    assert cli.cmd_eval_calibrate(deepseek, calibrate_args(experiment, plain, **single)) == 0
    assert cli.cmd_eval_calibrate(deepseek, calibrate_args(experiment, named, **single | {"rubric": ["v3"]})) == 0
    unstamped = [re.sub(r"Gerado em \S+\.", "", path.read_text(encoding="utf-8")) for path in (plain, named)]
    assert unstamped[0] == unstamped[1] and unstamped[0].startswith("# Calibração humana do juiz: dois juízes (v0.9.0)")

    out = tmp_path / "refused.md"
    refusals = [
        ({"rubric": ["v4", "v4", "v4"]}, "gravou julgamentos judge.v3, não judge.v4: confira --rubric"),
        ({"judge_run": ["v0100-juiz-deepseek-v4"]}, "3 --judge need 3 --judge-run"),
        ({"rubric": ["v4"]}, "--rubric is given for every --judge or for none"),
        ({"judge": None, "judge_run": None}, "--rubric is used with --judge"),
        (
            {"judge": [OPUS, OPUS], "judge_run": ["v0100-juiz-opus-v4"] * 2, "rubric": ["v4", "v4"]},
            "foi pedido mais de uma vez",
        ),
        (
            {"judge": [DEEPSEEK], "judge_run": ["v0100-juiz-deepseek-v4"], "rubric": None},
            "a execução 'v0100-juiz-deepseek-v4' do juiz deepseek/deepseek-flash gravou julgamentos judge.v4, não "
            "judge.v3",
        ),
        ({"campaign": "original"}, "informe --campaign com um nome novo"),
    ]
    for overrides, expected in refusals:
        with pytest.raises(SystemExit) as refused:
            cli.cmd_eval_calibrate(deepseek, calibrate_args(experiment, out, **overrides))
        assert expected in str(refused.value), (overrides, str(refused.value))
    changed = tmp_path / "changed.csv"
    text = experiment["csv"].read_bytes().decode("utf-8-sig")
    changed.write_bytes(text.replace(";4;", ";2;", 1).encode("utf-8-sig"))
    with pytest.raises(SystemExit, match="difere da gravada na campanha original"):
        cli.cmd_eval_calibrate(deepseek, calibrate_args(experiment, out, import_csv=str(changed)))
    assert not out.exists()
    conn = connect(deepseek.db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM calibrations WHERE campaign='v0100-juiz-v4'").fetchone()[0] == 0
    finally:
        conn.close()
