"""v0.8.0 task 71 (spec D10, D19): the human calibration of the judge. The draw of the sample, the CSV the owner fills
in (no score of the judge in it), the line-by-line validation of the filled file and the agreement measures with numbers
fixed by hand. Synthetic data only; no model is called."""

from __future__ import annotations

import csv
import io
import json
import random
import re
from pathlib import Path

import pytest

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.data.db import connect
from merchant_assistant.data.migrations import RollbackRefused, migrate
from merchant_assistant.evaluation import calibration as cal
from merchant_assistant.evaluation.judge import CRITERIA, save_evaluation
from merchant_assistant.evaluation.scripted_judge import scripted_judge
from merchant_assistant.llm.base import NullMeter

ROUTES = ("knowledge", "support", "general_web", "human_handoff")
SPLITS = ("dev", "holdout")
SIZES = {  # members of each (route, split) stratum: 60 answers in 8 strata
    ("knowledge", "dev"): 14,
    ("knowledge", "holdout"): 10,
    ("support", "dev"): 8,
    ("support", "holdout"): 8,
    ("general_web", "dev"): 6,
    ("general_web", "holdout"): 6,
    ("human_handoff", "dev"): 4,
    ("human_handoff", "holdout"): 4,
}
JUDGE_SCORES = {"groundedness": 2, "factual_correctness": 3, "relevance": 1, "usefulness": 4}
SENTINEL = "ZZ-JUDGE-REASON"


def fake_row(index: int, route: str, split: str, *, scores=None, claim=False, reply=None, repetition=1) -> dict:
    """One answer of a campaign report, the way `runner.run` records it, with a judgement full of sentinels."""
    message = f"Pergunta sintética número {index}?"
    answer = reply or f"Resposta sintética número {index}."
    return {
        "id": f"SYN-{index:03d}",
        "repetition": repetition,
        "request_id": f"req_syn{index:04d}{repetition}",
        "split": split,
        "route": route,
        "language": "pt",
        "message": message,
        "answer": answer,
        "judge_input": {
            "merchant_message": message,
            "status": "answered",
            "route": route,
            "sources": [f"Fonte {index}", "Outra fonte"],
            "evidence": [
                {"kind": "passage", "label": f"doc-{index}", "text": f"Trecho do documento {index}."},
                {"kind": "tool_result", "label": "get_receivables", "text": '{"result": {"net": "R$ 10,00"}}'},
            ],
            "evidence_truncation": {
                "limit_chars": 6000,
                "original_chars": 90,
                "kept_chars": 90,
                "items": 2,
                "items_cut": 0,
                "truncated": False,
            },
            "evidence_notes": [],
            "reply": answer,
        },
        "judge": {
            "evaluation_id": f"eval_sentinel{index:04d}{repetition}",
            "rubric_version": "3",
            "repetition": 1,
            "provider": "sentinel-provider",
            "model": "sentinel-judge-model",
            "model_used": "sentinel-judge-model",
            "state": "completed",
            "scores": dict(scores or JUDGE_SCORES),
            "reasons": {c: f"{SENTINEL}-{c}-{index}" for c in CRITERIA},
            "unsupported_claim": claim,
            "cost_usd": 0.0,
            "error": None,
        },
    }


def fake_rows(sizes=None) -> list[dict]:
    rows, index = [], 0
    for (route, split), size in (sizes or SIZES).items():
        for _ in range(size):
            index += 1
            rows.append(fake_row(index, route, split))
    return rows


def write_source(path: Path, rows: list[dict]) -> Path:
    path.write_text(json.dumps({"config": {"mode": "scripted"}, "summary": {}, "cases": rows}), encoding="utf-8")
    return path


def make_csv(tmp_path, rows=None, *, size=24, seed=cal.DEFAULT_SEED, delimiter=";", name="avaliacao.json") -> Path:
    report = write_source(tmp_path / name, rows if rows is not None else fake_rows())
    sample, meta = cal.make_sample(report, size, seed)
    path = tmp_path / "amostra.csv"
    cal.write_csv(path, sample, meta, delimiter=delimiter)
    return path


def read_table(path: Path, delimiter=";") -> list[list[str]]:
    return list(csv.reader(io.StringIO(path.read_bytes().decode("utf-8-sig"), newline=""), delimiter=delimiter))


def fill(path: Path, values: dict[str, dict[str, str]], *, delimiter=";", everyone: dict | None = None) -> None:
    """Fills the human columns the way the owner would. `values` by sample id; `everyone` for every data row."""
    table = read_table(path, delimiter)
    at = next(i for i, row in enumerate(table) if row and row[0] == "sample_id")
    header = table[at]
    for row in table[at + 1 :]:
        for column, value in {**(everyone or {}), **values.get(row[0], {})}.items():
            row[header.index(column)] = value
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, delimiter=delimiter, lineterminator="\r\n").writerows(table)


GOOD = {
    "groundedness": "4",
    "factual_correctness": "4",
    "relevance": "5",
    "usefulness": "4",
    "unsupported_claim": "nao",
}


def physical_line(path: Path, sample_id: str) -> int:
    lines = path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").split("\n")
    return next(i for i, line in enumerate(lines, start=1) if line.startswith(f"{sample_id};"))


# --- the draw -------------------------------------------------------------------------------------------------------


def strata_of(sample: list[dict]) -> dict:
    counts: dict = {}
    for row in sample:
        counts[(row["route"], row["split"])] = counts.get((row["route"], row["split"]), 0) + 1
    return counts


def test_the_sample_is_balanced_over_route_and_split():
    rows = fake_rows()
    sample = cal.draw_sample(rows, 24, cal.DEFAULT_SEED)
    assert len(sample) == 24 and len({r["request_id"] for r in sample}) == 24
    assert strata_of(sample) == dict.fromkeys(SIZES, 3)  # eight strata, three answers each
    larger = strata_of(cal.draw_sample(rows, 36, cal.DEFAULT_SEED))
    assert larger[("human_handoff", "dev")] == larger[("human_handoff", "holdout")] == 4  # used up, not exceeded
    assert sum(larger.values()) == 36 and max(larger.values()) - min(larger.values()) <= 1


def test_a_rare_stratum_still_shows_up():
    rows = fake_rows({("knowledge", "dev"): 59, ("out_of_scope", "holdout"): 1})
    assert ("out_of_scope", "holdout") in strata_of(cal.draw_sample(rows, 24, 1))


def test_the_same_seed_gives_the_same_sample_whatever_the_order_of_the_rows():
    rows = fake_rows()
    first = [r["request_id"] for r in cal.draw_sample(rows, 24, 7)]
    shuffled = rows[:]
    random.Random(3).shuffle(shuffled)
    assert [r["request_id"] for r in cal.draw_sample(shuffled, 24, 7)] == first
    assert [r["request_id"] for r in cal.draw_sample(rows, 24, 8)] != first
    # the sample does not come out grouped by stratum
    assert [(r["route"], r["split"]) for r in cal.draw_sample(rows, 24, 7)] != sorted(
        (r["route"], r["split"]) for r in cal.draw_sample(rows, 24, 7)
    )


def test_a_small_population_is_taken_whole_and_a_size_below_one_is_refused():
    rows = fake_rows({("knowledge", "dev"): 3, ("support", "dev"): 2})
    assert len(cal.draw_sample(rows, 24, 1)) == 5
    with pytest.raises(cal.CalibrationError, match="pelo menos 1"):
        cal.draw_sample(rows, 0, 1)


def test_only_first_executions_with_a_completed_judgement_and_their_evidence_are_eligible(tmp_path):
    rows = fake_rows({("knowledge", "dev"): 4})
    rows.append(fake_row(90, "knowledge", "dev", repetition=2))  # a repetition of the agent
    failed = fake_row(91, "knowledge", "dev")
    failed["judge"]["state"] = "failed"
    unrecorded = fake_row(92, "knowledge", "dev")
    del unrecorded["judge_input"]
    unjudged = fake_row(93, "knowledge", "dev")
    del unjudged["judge"]
    eligible, stem = cal.load_source(write_source(tmp_path / "campanha-x.json", [*rows, failed, unrecorded, unjudged]))
    assert len(eligible) == 4 and stem == "campanha-x" and all(r["repetition"] == 1 for r in eligible)
    with pytest.raises(cal.CalibrationError, match="não tem respostas julgadas"):
        cal.load_source(write_source(tmp_path / "vazio.json", [failed, unrecorded]))
    broken = tmp_path / "quebrado.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(cal.CalibrationError, match="não consegui ler"):
        cal.load_source(broken)


# --- the CSV without the judge --------------------------------------------------------------------------------------


def test_the_csv_never_carries_a_score_of_the_judge(tmp_path):
    path = make_csv(tmp_path)
    text = path.read_bytes().decode("utf-8-sig")
    # the judge's own words and identity
    for needle in (SENTINEL, "eval_sentinel", "sentinel-judge-model", "sentinel-provider"):
        assert needle not in text
    # the judge's values, in every form they could be written: JSON, key=value, key: value
    for criterion, value in JUDGE_SCORES.items():
        for form in (
            f'"{criterion}": {value}',
            f"{criterion}={value}",
            f"{criterion}: {value}",
            f"{criterion};{value}",
        ):
            assert form not in text
    table = read_table(path)
    at = next(i for i, row in enumerate(table) if row and row[0] == "sample_id")
    assert tuple(table[at]) == cal.COLUMNS and not any("judge" in column or "score" in column for column in table[at])
    data = table[at + 1 :]
    assert len(data) == 24
    for row in data:
        record = dict(zip(table[at], row, strict=True))
        assert all(record[column] == "" for column in cal.HUMAN_COLUMNS)  # empty for the human to fill in
        assert record["sample_id"].startswith("S") and record["request_id"].startswith("req_syn")
    assert [row[0] for row in data] == [f"S{n:02d}" for n in range(1, 25)]


def test_the_csv_is_utf8_with_short_instructions_in_portuguese_and_the_seed(tmp_path):
    path = make_csv(tmp_path, seed=4242)
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM: a spreadsheet reads the accents
    text = raw.decode("utf-8")
    comments = [row[0] for row in read_table(path) if row and row[0].startswith("#")]
    assert 8 <= len(comments) <= 14 and all(len(c) < 420 for c in comments)  # short
    instructions = " ".join(comments)
    for criterion in CRITERIA:  # the rubric: the four criteria, 1-5, and the verdict
        assert criterion in instructions
    assert "1 (ruim) a 5 (excelente)" in instructions and "unsupported_claim" in instructions
    assert "as notas dele não estão" in instructions and "tool_result" in instructions
    assert any(
        c.startswith("# amostra: campanha=avaliacao; semente=4242; origem=avaliacao.json; sorteadas=24")
        for c in comments
    )
    assert "elegiveis=60" in instructions and "rubrica=judge.v3" in instructions
    assert "Calibração" in text and "fundamentação" in text  # accents survive


def test_the_same_report_and_seed_write_the_same_file(tmp_path):
    first = make_csv(tmp_path).read_bytes()
    assert make_csv(tmp_path).read_bytes() == first
    assert make_csv(tmp_path, seed=5).read_bytes() != first


def test_the_semicolon_and_the_comma_are_both_written_and_read(
    tmp_path,
):
    for delimiter in (";", ","):
        path = make_csv(tmp_path, delimiter=delimiter)
        fill(path, {}, delimiter=delimiter, everyone=GOOD)
        assert len(cal.read_filled(path.read_bytes().decode("utf-8-sig")).ratings) == 24


def test_answers_are_masked_again_and_a_cell_cannot_become_a_formula(tmp_path):
    rows = fake_rows({("knowledge", "dev"): 3})
    rows[0]["judge_input"]["reply"] = "Seu CPF 123.456.789-09 e o e-mail ana@example.com. - item"
    rows[1]["judge_input"]["reply"] = "=SOMA(A1:A2)"
    rows[2]["judge_input"]["merchant_message"] = "+55 11 99999-0000, meu cartão 4111 1111 1111 1111"
    path = make_csv(tmp_path, rows, size=3)
    text = path.read_bytes().decode("utf-8-sig")
    assert "123.456.789-09" not in text and "ana@example.com" not in text and "4111 1111 1111 1111" not in text
    assert "[CPF removed]" in text and "[card number removed]" in text
    data = [dict(zip(cal.COLUMNS, row, strict=True)) for row in read_table(path) if row[0].startswith("S0")]
    for column in ("message", "answer"):
        assert not any(record[column][:1] in "=+-@" for record in data)  # a leading space defuses the formula
    assert any("SOMA" in record["answer"] for record in data) and any("+55" in record["message"] for record in data)


def test_the_evidence_is_a_summary_with_the_cut_and_the_web_note_in_portuguese():
    given = fake_row(1, "knowledge", "dev")["judge_input"]
    short = cal.summarize_evidence(given)
    assert "[passage] doc-1: Trecho do documento 1." in short and "[tool_result] get_receivables" in short
    given["evidence"] = [{"kind": "passage", "label": "grande", "text": "palavra " * 1000}, given["evidence"][1]]
    given["evidence_notes"] = [
        "The reply comes from a web search whose text is not recorded: judge only whether it is "
        "consistent with the listed sources and say so in the reasons."
    ]
    given["evidence_truncation"] = given["evidence_truncation"] | {"truncated": True}
    summary = cal.summarize_evidence(given)
    assert len(summary) < cal.EVIDENCE_SUMMARY_CHARS + 400 and "[...cut]" in summary
    assert "[tool_result] get_receivables" in summary  # the long passage did not push the tool result out
    assert "Nota: A resposta vem de busca web" in summary and "já cortada em 6000 caracteres" in summary
    assert cal.summarize_evidence({"evidence": []}).startswith("(sem evidência")


# --- the filled file: validation line by line -----------------------------------------------------------------------


def test_a_well_filled_file_is_read_with_the_values_the_owner_typed(tmp_path):
    path = make_csv(tmp_path)
    fill(
        path,
        {"S02": {"unsupported_claim": "Sim", "note": "valor estranho"}, "S03": {"unsupported_claim": "NÃO"}},
        everyone=GOOD,
    )
    filled = cal.read_filled(path.read_bytes().decode("utf-8-sig"))
    assert len(filled.ratings) == 24 and filled.skipped == []
    assert filled.meta["campaign"] == "avaliacao" and filled.meta["seed"] == str(cal.DEFAULT_SEED)
    second = filled.ratings[1]
    assert (second.sample_id, second.unsupported_claim, second.note) == ("S02", True, "valor estranho")
    assert second.scores == {"groundedness": 4, "factual_correctness": 4, "relevance": 5, "usefulness": 4}
    assert filled.ratings[2].unsupported_claim is False and second.route and second.split and second.case_id


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("sim", True),
        ("SIM", True),
        ("s", True),
        ("true", True),
        ("1", True),
        ("verdadeiro", True),
        ("nao", False),
        ("não", False),
        ("Não", False),
        ("n", False),
        ("false", False),
        ("0", False),
    ],
)
def test_the_verdict_accepts_the_usual_spellings(tmp_path, typed, expected):
    path = make_csv(tmp_path, size=4)
    fill(path, {}, everyone=GOOD | {"unsupported_claim": typed})
    assert cal.read_filled(path.read_bytes().decode("utf-8-sig")).ratings[0].unsupported_claim is expected


def test_every_bad_cell_is_reported_with_its_line_and_sample(tmp_path):
    path = make_csv(tmp_path)
    fill(
        path,
        {
            "S03": {"groundedness": "7"},
            "S05": {"relevance": "abc", "usefulness": "4,5"},
            "S07": {"factual_correctness": "0"},
            "S08": {"unsupported_claim": "talvez"},
            "S09": {"relevance": ""},  # half filled
        },
        everyone=GOOD,
    )
    with pytest.raises(cal.CalibrationError) as caught:
        cal.read_filled(path.read_bytes().decode("utf-8-sig"))
    messages = caught.value.messages
    assert len(messages) == 5  # one per bad row, all of them in one pass
    expected = {
        "S03": "groundedness precisa ser um inteiro de 1 a 5, recebi '7'",
        "S05": (
            "relevance precisa ser um inteiro de 1 a 5, recebi 'abc'; "
            "usefulness precisa ser um inteiro de 1 a 5, recebi '4,5'"
        ),
        "S07": "factual_correctness precisa ser um inteiro de 1 a 5, recebi '0'",
        "S08": "unsupported_claim precisa ser sim ou nao, recebi 'talvez'",
        "S09": "relevance está vazio",
    }
    for sample_id, problem in expected.items():
        line = physical_line(path, sample_id)  # the physical line of the file, with the multi-line cells counted
        assert f"linha {line} ({sample_id}): {problem}" in next(m for m in messages if f"({sample_id})" in m)
    assert "Preencha os cinco campos ou deixe todos vazios" in messages[-1]
    assert str(caught.value) == "\n".join(messages)


def test_a_row_with_nothing_filled_is_skipped_and_a_note_alone_does_not_count(tmp_path):
    path = make_csv(tmp_path, size=6)
    fill(
        path,
        {"S02": {k: "" for k in GOOD}, "S04": {k: "" for k in GOOD} | {"note": "não consegui avaliar"}},
        everyone=GOOD,
    )
    filled = cal.read_filled(path.read_bytes().decode("utf-8-sig"))
    assert filled.skipped == ["S02", "S04"] and [r.sample_id for r in filled.ratings] == ["S01", "S03", "S05", "S06"]


def test_a_repeated_sample_id_and_an_empty_request_id_are_refused(tmp_path):
    path = make_csv(tmp_path, size=4)
    table = read_table(path)
    at = next(i for i, row in enumerate(table) if row and row[0] == "sample_id")
    table[at + 2][0] = "S01"
    table[at + 3][table[at].index("request_id")] = ""
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, delimiter=";").writerows(table)
    fill(path, {}, everyone=GOOD)
    with pytest.raises(cal.CalibrationError) as caught:
        cal.read_filled(path.read_bytes().decode("utf-8-sig"))
    text = str(caught.value)
    assert "sample_id repetido (já aparece na linha" in text and "request_id vazio" in text


def test_a_header_without_the_required_columns_or_without_a_header_is_refused(tmp_path):
    with pytest.raises(cal.CalibrationError, match="não encontrei o cabeçalho"):
        cal.read_filled("# so comentarios\n# amostra: campanha=x; semente=1\n")
    text = make_csv(tmp_path, size=2).read_bytes().decode("utf-8-sig").replace(";request_id;", ";pedido;", 1)
    with pytest.raises(cal.CalibrationError, match=r"linha \d+: faltam as colunas request_id"):
        cal.read_filled(text)
    only_header = ";".join(cal.COLUMNS) + "\n"
    assert cal.read_filled(only_header).ratings == []  # nothing to rate: the import says so


def test_an_unquoted_separator_inside_a_text_is_pointed_at():
    row = ["S01", "knowledge", "dev", "answered", "uma pergunta; com ponto e vírgula", "resp", "src", "ev"]
    row += ["", "", "", "", "", "", "req_1", "CASE-1"]
    text = f"# amostra: campanha=x; semente=1\n{';'.join(cal.COLUMNS)}\n{';'.join(row)}\n"
    with pytest.raises(cal.CalibrationError, match=r"linha 3: 17 colunas para um cabeçalho de 16"):
        cal.read_filled(text)


def test_a_spreadsheet_that_saved_the_file_again_still_reads(tmp_path):
    """A spreadsheet adds the empty cells to the comment rows, changes the quoting and may use tabs."""
    path = make_csv(tmp_path, size=4)
    fill(path, {}, everyone=GOOD)
    for delimiter in (";", ",", "\t"):
        table = read_table(path)
        width = len(next(row for row in table if row and row[0] == "sample_id"))
        saved = [(row + [""] * (width - len(row))) if row[0].startswith("#") else row for row in table]
        resaved = tmp_path / "resalvo.csv"
        with resaved.open("w", encoding="utf-8-sig", newline="") as handle:
            csv.writer(handle, delimiter=delimiter, lineterminator="\r\n", quoting=csv.QUOTE_ALL).writerows(saved)
            handle.write(delimiter * (width - 1) + "\r\n")  # an empty trailing row
        filled = cal.read_filled(resaved.read_bytes().decode("utf-8-sig"))
        assert len(filled.ratings) == 4 and filled.meta["campaign"] == "avaliacao"


def test_a_file_that_is_not_utf8_gets_a_clear_message(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    latin = tmp_path / "latin1.csv"
    latin.write_bytes("sample_id;request_id\nS01;req_ã\n".encode("latin-1"))
    with pytest.raises(cal.CalibrationError, match="não está em UTF-8: salve a planilha como 'CSV UTF-8'"):
        cal.import_filled(conn, latin)
    with pytest.raises(cal.CalibrationError, match="não consegui ler"):
        cal.import_filled(conn, tmp_path / "ausente.csv")
    conn.close()


def test_at_most_the_first_problems_are_listed_but_all_are_counted():
    error = cal.CalibrationError([f"linha {n}: x" for n in range(40)])
    assert len(error.messages) == 40 and cal.MAX_REPORTED_ERRORS == 25


# --- the ratings in the database, linked to the judgement by request_id ---------------------------------------------


def judged_database(tmp_path, rows):
    """A database where the campaign wrote the judgements of `rows` (repetition 1, principal cli:eval)."""
    conn = connect(tmp_path / "campaign.sqlite3")
    judge = scripted_judge(PROJECT_ROOT / "prompts", NullMeter())
    for row in rows:
        save_evaluation(conn, request_id=row["request_id"], judge=judge, record=row["judge"], data=row["judge_input"])
    return conn


def varied_rows() -> list[dict]:
    """24 answers whose judgements vary, so the agreement measures have something to measure."""
    rows = []
    for index in range(1, 25):
        scores = {c: 1 + (index + k) % 5 for k, c in enumerate(CRITERIA)}
        rows.append(fake_row(index, ROUTES[index % 4], SPLITS[index % 2], scores=scores, claim=index % 6 == 0))
    return rows


def human_like_judge(tmp_path, rows):
    """A filled CSV whose ratings equal the judge's, row by row (every request id is mapped back to its judgement)."""
    path = make_csv(tmp_path, rows)
    by_request = {r["request_id"]: r["judge"] for r in rows}
    table = read_table(path)
    at = next(i for i, row in enumerate(table) if row and row[0] == "sample_id")
    header = table[at]
    for row in table[at + 1 :]:
        judge = by_request[row[header.index("request_id")]]
        for criterion in CRITERIA:
            row[header.index(criterion)] = str(judge["scores"][criterion])
        row[header.index("unsupported_claim")] = "sim" if judge["unsupported_claim"] else "nao"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, delimiter=";", lineterminator="\r\n").writerows(table)
    return path


def test_the_ratings_are_stored_linked_to_the_judgement_of_the_same_request(tmp_path):
    rows = varied_rows()
    conn = judged_database(tmp_path, rows)
    path = human_like_judge(tmp_path, rows)
    fill(path, {"S01": {"note": "sem observações"}})
    result = cal.import_filled(conn, path, rater="owner")
    assert result["counts"] == {"created": 24, "updated": 0} and result["skipped"] == []
    stored = conn.execute("SELECT * FROM calibrations ORDER BY sample_id").fetchall()
    assert len(stored) == 24
    judged = {
        r["request_id"]: dict(r)
        for r in conn.execute("SELECT request_id, evaluation_id, scores, unsupported_claim FROM run_evaluations")
    }
    for row in stored:
        link = judged[row["request_id"]]
        assert row["evaluation_id"] == link["evaluation_id"] and row["rubric_version"] == "3"
        assert json.loads(row["scores"]) == json.loads(link["scores"])  # the human typed what the judge had
        assert row["unsupported_claim"] == link["unsupported_claim"] and row["rater"] == "owner"
        assert (row["campaign"], row["route"] in ROUTES, row["split"] in SPLITS) == ("avaliacao", True, True)
        assert row["case_id"].startswith("SYN-") and row["created_at"]
    assert next(r for r in stored if r["sample_id"] == "S01")["note"] == "sem observações"
    assert all(r["note"] is None for r in stored if r["sample_id"] != "S01")


def test_importing_the_same_file_again_updates_the_ratings_instead_of_adding_them(tmp_path):
    rows = varied_rows()
    conn = judged_database(tmp_path, rows)
    path = human_like_judge(tmp_path, rows)
    cal.import_filled(conn, path)
    was = json.loads(conn.execute("SELECT scores FROM calibrations WHERE sample_id='S05'").fetchone()[0])["relevance"]
    changed = 2 if was == 1 else 1
    fill(path, {"S05": {"relevance": str(changed)}})
    again = cal.import_filled(conn, path)
    assert again["counts"] == {"created": 0, "updated": 24}
    assert conn.execute("SELECT COUNT(*) FROM calibrations").fetchone()[0] == 24
    now = json.loads(conn.execute("SELECT scores FROM calibrations WHERE sample_id='S05'").fetchone()[0])
    assert now["relevance"] == changed != was
    other = cal.import_filled(conn, path, rater="outra pessoa")  # a second rater is a second set
    assert other["counts"]["created"] == 24 and conn.execute("SELECT COUNT(*) FROM calibrations").fetchone()[0] == 48


def test_nothing_is_written_when_a_line_is_wrong_or_a_judgement_is_missing(tmp_path):
    rows = varied_rows()
    conn = judged_database(tmp_path, rows)
    bad = human_like_judge(tmp_path, rows)
    fill(bad, {"S04": {"usefulness": "9"}})
    with pytest.raises(cal.CalibrationError, match=r"\(S04\): usefulness precisa ser"):
        cal.import_filled(conn, bad)
    assert conn.execute("SELECT COUNT(*) FROM calibrations").fetchone()[0] == 0
    conn.execute("DELETE FROM run_evaluations WHERE request_id=?", (rows[0]["request_id"],))
    missing = human_like_judge(tmp_path, rows)
    with pytest.raises(cal.CalibrationError) as caught:
        cal.import_filled(conn, missing)
    assert len(caught.value.messages) == 1 and rows[0]["request_id"] in caught.value.messages[0]
    assert (
        "não há julgamento da requisição" in caught.value.messages[0] and "run_evaluations" in caught.value.messages[0]
    )
    assert conn.execute("SELECT COUNT(*) FROM calibrations").fetchone()[0] == 0


def test_only_the_first_completed_judgement_of_the_campaign_is_the_one_compared(tmp_path):
    rows = varied_rows()[:4]
    conn = judged_database(tmp_path, rows)
    judge = scripted_judge(PROJECT_ROOT / "prompts", NullMeter())
    target = rows[0]
    later = {**target["judge"], "evaluation_id": "eval_later", "repetition": 2, "scores": dict.fromkeys(CRITERIA, 5)}
    failed = {
        **target["judge"],
        "evaluation_id": "eval_failed",
        "state": "failed",
        "scores": {},
        "reasons": {},
        "unsupported_claim": None,
    }
    save_evaluation(conn, request_id=target["request_id"], judge=judge, record=later, data=target["judge_input"])
    conn.execute("UPDATE run_evaluations SET created_at='2000-01-02T00:00:00+00:00' WHERE evaluation_id='eval_later'")
    save_evaluation(conn, request_id=target["request_id"], judge=judge, record=failed, data=target["judge_input"])
    other = {**target["judge"], "evaluation_id": "eval_000_other", "scores": dict.fromkeys(CRITERIA, 5)}
    save_evaluation(conn, request_id=target["request_id"], judge=judge, record=other, data=target["judge_input"])
    conn.execute(
        "UPDATE run_evaluations SET principal_id='api:someone', created_at='2000-01-01T00:00:00+00:00' "
        "WHERE evaluation_id='eval_000_other'"
    )
    other_rubric = {**target["judge"], "evaluation_id": "eval_000_v2", "scores": dict.fromkeys(CRITERIA, 5)}
    save_evaluation(conn, request_id=target["request_id"], judge=judge, record=other_rubric, data=target["judge_input"])
    conn.execute(
        "UPDATE run_evaluations SET rubric='comparison', created_at='2000-01-01T00:00:00+00:00' "
        "WHERE evaluation_id='eval_000_v2'"
    )
    # a judge.v2 judgement keeps no `scores` column: never the one compared, however early it is
    old_rubric = {**target["judge"], "evaluation_id": "eval_000_old"}
    save_evaluation(conn, request_id=target["request_id"], judge=judge, record=old_rubric, data=target["judge_input"])
    conn.execute(
        "UPDATE run_evaluations SET scores=NULL, created_at='2000-01-01T00:00:00+00:00' "
        "WHERE evaluation_id='eval_000_old'"
    )
    # the same answer judged again later (a judge-repeat report starts at repetition 1 again): the first one stays
    again = {**target["judge"], "evaluation_id": "eval_again", "scores": dict.fromkeys(CRITERIA, 5)}
    save_evaluation(conn, request_id=target["request_id"], judge=judge, record=again, data=target["judge_input"])
    conn.execute("UPDATE run_evaluations SET created_at='2999-01-01T00:00:00+00:00' WHERE evaluation_id='eval_again'")
    found = cal.judgement_for(conn, target["request_id"])
    assert found["evaluation_id"] == target["judge"]["evaluation_id"] and found["scores"] == target["judge"]["scores"]
    assert cal.judgement_for(conn, "req_unknown") is None


def test_the_rollback_of_the_schema_is_refused_once_a_human_rating_is_stored(tmp_path):
    rows = varied_rows()
    conn = judged_database(tmp_path, rows)
    cal.import_filled(conn, human_like_judge(tmp_path, rows))
    with pytest.raises(RollbackRefused, match="calibrations still holds 24 human score"):
        migrate(conn, 10)


def test_an_import_needs_the_campaign_a_rater_and_at_least_one_rated_line(tmp_path):
    rows = varied_rows()
    conn = judged_database(tmp_path, rows)
    path = human_like_judge(tmp_path, rows)
    text = path.read_bytes().decode("utf-8-sig")
    no_line = tmp_path / "sem-linha.csv"
    no_line.write_text("\n".join(row for row in text.split("\r\n") if "# amostra:" not in row), encoding="utf-8")
    with pytest.raises(cal.CalibrationError, match="falta a linha 'amostra:'"):
        cal.import_filled(conn, no_line)
    named = cal.import_filled(conn, no_line, campaign="v080 qa")  # --campaign stands in for the missing line
    assert named["meta"]["campaign"] == "v080-qa"
    with pytest.raises(cal.CalibrationError, match="--rater"):
        cal.import_filled(conn, path, rater="  ")
    empty = make_csv(tmp_path, rows)
    with pytest.raises(cal.CalibrationError, match="nenhuma linha de amostra.csv tem avaliação"):
        cal.import_filled(conn, empty)


# --- agreement: numbers fixed by hand -------------------------------------------------------------------------------


def test_agreement_on_a_small_table_computed_by_hand():
    human, judge = [1, 2, 3, 4, 5], [1, 3, 3, 4, 4]
    # exact: 3 of 5; within one point: 5 of 5; squared differences 0+1+0+0+1 = 2, and
    # the sum over every pair (human i, judge j) of the squared difference is 5*55 + 5*51 - 2*15*15 = 80,
    # so kappa = 1 - 5*2/80 = 0.875
    assert cal.exact_agreement(human, judge) == 0.6 and cal.within_one(human, judge) == 1.0
    assert cal.quadratic_kappa(human, judge) == pytest.approx(0.875)


def test_a_difference_of_two_points_is_not_within_one():
    human, judge = [1, 5, 3, 2], [3, 5, 4, 4]  # differences 2, 0, 1, 2
    assert cal.within_one(human, judge) == 0.5 and cal.exact_agreement(human, judge) == 0.25


def test_agreement_on_twelve_ratings():
    human = [5, 4, 4, 3, 5, 2, 4, 3, 1, 5, 4, 3]
    judge = [5, 5, 4, 3, 4, 2, 5, 3, 2, 5, 4, 4]
    # 7 equal and 5 off by one; sum of squared differences 5; human 43 and 171, judge 46 and 190:
    # sum over every pair = 12*171 + 12*190 - 2*43*46 = 376, kappa = 1 - 12*5/376
    assert cal.exact_agreement(human, judge) == pytest.approx(7 / 12) and cal.within_one(human, judge) == 1.0
    assert cal.quadratic_kappa(human, judge) == pytest.approx(1 - 60 / 376)
    assert round(cal.quadratic_kappa(human, judge), 4) == 0.8404


@pytest.mark.parametrize(
    ("human", "judge", "kappa"),
    [
        ([1, 2, 3, 4, 5], [1, 2, 3, 4, 5], 1.0),  # all equal, with variation
        ([5, 3, 1, 4], [5, 3, 1, 4], 1.0),
        ([1, 5], [5, 1], -1.0),  # the worst possible
        ([1, 2, 3, 4, 5], [5, 4, 3, 2, 1], -1.0),
        ([4, 4, 4, 4], [3, 4, 5, 4], 0.0),  # one side never varies: 0 by construction
        ([3, 4, 5, 4], [4, 4, 4, 4], 0.0),
        ([4, 4, 4], [3, 3, 3], 0.0),  # both constant, not equal
    ],
)
def test_kappa_edge_cases(human, judge, kappa):
    assert cal.quadratic_kappa(human, judge) == pytest.approx(kappa)


def test_kappa_is_not_defined_for_one_line_or_for_constant_equal_ratings():
    assert cal.quadratic_kappa([4], [4]) is None and cal.quadratic_kappa([4], [2]) is None
    assert cal.quadratic_kappa([], []) is None
    assert cal.quadratic_kappa([5, 5, 5], [5, 5, 5]) is None  # every value equal on both sides
    assert "uma linha só" in cal.kappa_note([4], [4], None)
    assert "iguais e sem variação dos dois lados" in cal.kappa_note([5, 5], [5, 5], None)
    assert "um dos lados não varia" in cal.kappa_note([4, 4], [3, 5], 0.0)
    assert cal.kappa_note([1, 2, 3], [1, 3, 3], 0.5) is None
    assert cal.exact_agreement([], []) is None and cal.within_one([], []) is None


def test_kappa_of_two_values_is_the_kappa_of_cohen():
    # 6 of 8 equal; each rater says yes 4 times: p_o = 0.75, p_e = 0.5 * 0.5 + 0.5 * 0.5 = 0.5, kappa = 0.5
    verdicts = ([1, 1, 0, 0, 1, 0, 1, 0], [1, 0, 0, 0, 1, 1, 1, 0])
    assert cal.quadratic_kappa(*verdicts, categories=(0, 1)) == pytest.approx(0.5)


def test_kappa_matches_an_independent_formula_on_random_ratings():
    """kappa = 1 - N * sum (a_p - b_p)^2 / sum over all (p, q) of (a_p - b_q)^2, a form with no table in it."""
    rng = random.Random(2026)
    checked = 0
    for _ in range(400):
        n = rng.randint(2, 30)
        human = [rng.choice([1, 2, 3, 4, 5, 5, 4]) for _ in range(n)]
        judge = [max(1, min(5, a + rng.choice([-1, 0, 0, 0, 1, 2]))) for a in human]
        everything = sum((a - b) ** 2 for a in human for b in judge)
        expected = (
            None
            if everything == 0
            else 1 - n * sum((a - b) ** 2 for a, b in zip(human, judge, strict=True)) / everything
        )
        got = cal.quadratic_kappa(human, judge)
        assert (got is None) == (expected is None) and (got is None or got == pytest.approx(expected))
        checked += expected is not None
    assert checked > 350


def test_the_proportions_have_a_wilson_interval():
    low, high = cal.wilson(24, 24)
    assert (round(low, 3), round(high, 3)) == (0.862, 1.0)  # even 24 of 24 leaves room below
    low, high = cal.wilson(12, 24)
    assert (round(low, 3), round(high, 3)) == (0.314, 0.686)
    assert cal.wilson(0, 24)[0] == 0.0 and round(cal.wilson(0, 24)[1], 3) == 0.138
    assert cal.wilson(0, 0) is None


def test_the_kappa_interval_is_seeded_and_absent_when_it_means_nothing():
    human = [5, 4, 4, 3, 5, 2, 4, 3, 1, 5, 4, 3]
    judge = [5, 5, 4, 3, 4, 2, 5, 3, 2, 5, 4, 4]
    first = cal.kappa_interval(human, judge, cal.SCALE, 7)
    assert first == cal.kappa_interval(human, judge, cal.SCALE, 7) and first != cal.kappa_interval(
        human, judge, cal.SCALE, 8
    )
    assert 0.4 < first[0] < 0.7 and 0.85 < first[1] <= 1.0  # around 0.84, wide with twelve ratings
    assert -1 <= first[0] < cal.quadratic_kappa(human, judge) < first[1] <= 1
    assert cal.kappa_interval([4], [4], cal.SCALE, 7) is None
    assert cal.kappa_interval([5, 5, 5], [5, 5, 5], cal.SCALE, 7) is None  # no resample has a kappa


# --- the analysis and the report ------------------------------------------------------------------------------------


def pair(sample_id, human: dict, judge: dict, human_claim=False, judge_claim=False, route="knowledge", split="dev"):
    rating = cal.Rating(sample_id, f"req_{sample_id}", f"CASE-{sample_id}", route, split, human, human_claim, "", 1)
    judgement = {
        "evaluation_id": f"eval_{sample_id}",
        "rubric_version": "3",
        "judge": "deepseek/deepseek-flash",
        "scores": judge,
        "unsupported_claim": judge_claim,
    }
    return cal.Pair(rating, judgement)


def fixed_pairs() -> list[cal.Pair]:
    human = [5, 4, 4, 3, 5, 2, 4, 3, 1, 5, 4, 3]
    judge = [5, 5, 4, 3, 4, 2, 5, 3, 2, 5, 4, 4]
    pairs = []
    for index, (h, j) in enumerate(zip(human, judge, strict=True), start=1):
        scores_h = dict.fromkeys(CRITERIA, h) | {"usefulness": 4}  # usefulness never varies on the human side
        scores_j = dict.fromkeys(CRITERIA, j)
        pairs.append(
            pair(f"S{index:02d}", scores_h, scores_j, human_claim=index in (1, 2, 3), judge_claim=index in (2, 3, 4, 5))
        )
    return pairs


def test_the_analysis_has_the_three_measures_per_criterion_and_the_verdict_table():
    analysis = cal.analyze(fixed_pairs(), seed=7)
    grounded = analysis["criteria"]["groundedness"]
    assert grounded["n"] == 12 and grounded["exact"] == pytest.approx(7 / 12) and grounded["within_one"] == 1.0
    assert grounded["kappa"] == pytest.approx(1 - 60 / 376) and grounded["kappa_note"] is None
    assert grounded["kappa_ci"][0] < grounded["kappa"] < grounded["kappa_ci"][1]
    assert (round(grounded["exact_ci"][0], 3), round(grounded["exact_ci"][1], 3)) == (0.320, 0.807)
    assert grounded["human_mean"] == pytest.approx(43 / 12) and grounded["judge_mean"] == pytest.approx(46 / 12)
    constant = analysis["criteria"]["usefulness"]  # the human gave 4 every time
    assert (
        constant["kappa"] == pytest.approx(0.0)
        and constant["kappa_ci"] is None
        and "não varia" in constant["kappa_note"]
    )
    verdict = analysis["verdict"]
    assert verdict["table"] == {"both": 2, "human_only": 1, "judge_only": 2, "neither": 7}
    assert verdict["exact"] == pytest.approx(9 / 12) and verdict["within_one"] is None
    # (p_o = 0.75; yes: human 3 of 12, judge 4 of 12; p_e = 0.25 * 0.3333 + 0.75 * 0.6667 = 0.5833)
    assert verdict["kappa"] == pytest.approx((0.75 - 7 / 12) / (1 - 7 / 12))
    gaps = {(g[0], g[4]) for g in analysis["gaps"]}  # the verdicts that differ, and the judge's 2 against the human 4
    assert gaps == {
        ("S01", "unsupported_claim"),
        ("S04", "unsupported_claim"),
        ("S05", "unsupported_claim"),
        ("S06", "usefulness"),
        ("S09", "usefulness"),
    }


def test_a_gap_of_two_points_or_more_is_listed():
    pairs = [
        pair("S01", dict.fromkeys(CRITERIA, 5), dict.fromkeys(CRITERIA, 3)),
        pair("S02", dict.fromkeys(CRITERIA, 4), dict.fromkeys(CRITERIA, 3)),
    ]
    gaps = cal.analyze(pairs, 1)["gaps"]
    assert len(gaps) == 4 and {g[0] for g in gaps} == {"S01"} and {g[5:] for g in gaps} == {("5", "3")}


def test_the_report_states_the_small_sample_caveat_and_every_number_with_its_interval():
    pairs = fixed_pairs()
    report = cal.render_report(
        {"campaign": "v080-qa", "seed": "7", "source": "avaliacao.json", "drawn": "12", "eligible": "69"},
        "owner",
        pairs,
        cal.analyze(pairs, 7),
        skipped=["S13"],
    )
    assert report.startswith("# Calibração humana do juiz (v0.8.0)")
    assert "Ressalva de amostra pequena (D19): 12 respostas" in report and "não como prova" in report
    assert "Campanha `v080-qa`" in report and "semente 7" in report and "Sem avaliação (linhas puladas): 1" in report
    assert "`deepseek/deepseek-flash`" in report and "rubrica `judge.v3`" in report
    line = next(r for r in report.splitlines() if r.startswith("| groundedness (fundamentação) | 12 |"))
    assert "0.583 (IC 95%: 0.32 a 0.81)" in line and "1.000 (IC 95%: 0.76 a 1.00)" in line
    assert re.search(r"\| 0\.840 \(IC 95%: 0\.\d\d a 0\.\d\d\) \|", line) and line.endswith("| 3.58 | 3.83 | +0.25 |")
    constant = next(r for r in report.splitlines() if r.startswith("| usefulness (utilidade) | 12 |"))
    assert "0.000 (sem intervalo)" in constant
    assert "um dos lados não varia: o kappa é 0 por construção" in report
    assert "| Humano: sim | 2 | 1 |" in report and "| Humano: não | 2 | 7 |" in report
    assert (
        "## Divergências grandes" in report
        and "| S01 | CASE-S01 | knowledge | dev | unsupported_claim | sim | não |" in report
    )
    assert "Rotas: knowledge 12. Splits: dev 12." in report
    assert "nenhuma nota do juiz" in report  # about the sample file


def test_the_report_for_one_line_and_for_identical_ratings_says_what_cannot_be_computed():
    one = [pair("S01", dict.fromkeys(CRITERIA, 4), dict.fromkeys(CRITERIA, 4))]
    report = cal.render_report({"campaign": "c"}, "owner", one, cal.analyze(one, 1), skipped=[])
    assert "uma linha só: o kappa não é definido" in report and "| n/d |" in report
    same = [pair(f"S{n}", dict.fromkeys(CRITERIA, 5), dict.fromkeys(CRITERIA, 5)) for n in range(1, 4)]
    report = cal.render_report({"campaign": "c"}, "owner", same, cal.analyze(same, 1), skipped=[])
    assert "iguais e sem variação dos dois lados" in report and "1.000 (IC 95%: 0.44 a 1.00)" in report
    assert "Nenhuma." in report  # no gap
