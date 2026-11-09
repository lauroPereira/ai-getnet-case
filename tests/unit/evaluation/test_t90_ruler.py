"""Task 90 (spec v0.11.0 D8, CA-64): the combined ruler of the journeys.

`deterministic` is every check but the required phrases; `content` is the judge's first judgement with the floor
written before the campaign (>= 4 in factual correctness and relevance, no unsupported claim); `passed` is both. The
literal ruler is the earlier one. Rows are built by the real checks (`_checks`) over a journey label and graded by the
programmed judge; no model call."""

from __future__ import annotations

import json

import pytest

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation import runner
from merchant_assistant.evaluation.runner import (
    CHECK_KEYS,
    DETERMINISTIC_KEYS,
    apply_ruler,
    case_from_label,
    content_verdict,
    load_cases,
    mark_journeys,
    summarize,
    write_report,
)
from merchant_assistant.evaluation.scripted_judge import scripted_judge

JOURNEYS = PROJECT_ROOT / "tests" / "scenarios" / "business_journeys.jsonl"
CASES = {case.id: case for case in load_cases([JOURNEYS])}
CONSISTENT = CASES["V030-PRICE-CONSISTENT"]  # "Is the fee on yesterday's debit sale consistent?", R$ 1,94
TOOL_TEXT = "simulate_pricing: expected fee R$ 1,94 for the debit sale; recorded fee R$ 1,94."

# A correct paraphrase: none of the required phrases ("consistent", "matches the pricing rule", "no difference"...)
PARAPHRASE = "Yesterday's debit sale was charged R$ 1,94, exactly the fee the pricing rule gives for that sale."
# The same paraphrase with a wrong value
WRONG_VALUE = "Yesterday's debit sale was charged R$ 1,49, exactly the fee the pricing rule gives for that sale."
# A generic sentence that carries a required phrase ("no difference") and the amount, but answers nothing asked
GENERIC = "R$ 1,94 is a usual value; there is normally no difference when pricing rules are applied correctly."


def judge():
    return scripted_judge(PROJECT_ROOT / "prompts")


def row_for(case, answer: str, *, graded: bool = True) -> dict:
    """A report row: the deterministic checks of `runner._checks` and, when `graded`, one programmed judgement."""
    body = {"answer": answer, "route": "support", "status": "answered", "language": "en", "sources": [{"t": 1}]}
    trace = {"steps": [{"step": "router"}, {"step": "tool:simulate_pricing"}], "detail": {}}
    checks = runner._checks(case, body, trace)
    row = {"id": case.id, "split": case.split, "language": case.language, "route": "support", "status": "answered",
           "duration_ms": 10, "cost_usd": 0.0, "expected_claims": case.expected_claims, **checks}
    row["passed"] = all(row[k] for k in CHECK_KEYS)
    if graded:
        data = {"merchant_message": case.message, "status": "answered", "route": "support", "sources": ["pricing"],
                "evidence": [{"kind": "tool_result", "title": "simulate_pricing", "text": TOOL_TEXT}],
                "evidence_notes": [], "reply": answer}
        row["judge_input"] = data
        row["judge"] = judge().evaluate(data)
    return row


def completed(factual: int = 5, relevance: int = 5, unsupported: bool = False, state: str = "completed") -> dict:
    scores = {"groundedness": 5, "factual_correctness": factual, "relevance": relevance, "usefulness": 5}
    return {"state": state, "scores": scores, "unsupported_claim": unsupported}


# --- labels: the required phrases of the journeys are now expected claims (field only) ----------------------------


def test_journey_labels_name_the_phrases_expected_claims_and_the_literal_ruler_still_reads_them():
    rows = [json.loads(line) for line in JOURNEYS.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 13 and all("expected_claims" in r and "must_include_any" not in r for r in rows)
    for row in rows:
        case = CASES[row["id"]]
        assert case.expected_claims == row["expected_claims"] == case.must_include_any


def test_a_label_without_expected_claims_is_not_a_journey():
    case = case_from_label({"id": "X", "split": "dev", "message": "m", "language": "en", "accepted_routes": ["support"],
                            "expected_status": "answered", "expected_tools": [], "must_include_amounts": [],
                            "must_include_any": [["a"]], "expect_sources": False})
    assert case.expected_claims is None and case.must_include_any == [["a"]]


# --- the content half ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (completed(), True),
        (completed(factual=4, relevance=4), True),  # the floor is inclusive
        (completed(factual=3), False),
        (completed(relevance=3), False),
        (completed(unsupported=True), False),
        (completed(state="failed"), None),
        (None, None),
    ],
)
def test_content_verdict_floor(record, expected):
    assert content_verdict(record) is expected


def test_deterministic_half_is_every_check_but_the_required_phrases():
    assert [k for k in CHECK_KEYS if k != "content_ok"] == DETERMINISTIC_KEYS
    assert {"route_ok", "status_ok", "tools_ok", "amounts_ok", "forbidden_ok", "sources_ok"} <= set(DETERMINISTIC_KEYS)


# --- the three answers of the task, through the real checks and the programmed judge --------------------------------


def test_a_correct_paraphrase_passes_the_combined_ruler_and_fails_the_literal_one():
    combined, literal = row_for(CONSISTENT, PARAPHRASE), row_for(CONSISTENT, PARAPHRASE)
    assert combined["content_ok"] is False  # no required phrase: the literal ruler refuses it
    apply_ruler([combined], "combined")
    apply_ruler([literal], "literal")
    assert (combined["deterministic"], combined["content"], combined["passed"]) == (True, True, True)
    assert literal["passed"] is False and "deterministic" not in literal


def test_a_paraphrase_with_a_wrong_value_fails_by_the_deterministic_half():
    row = row_for(CONSISTENT, WRONG_VALUE)
    apply_ruler([row], "combined")
    assert row["amounts_ok"] is False and row["deterministic"] is False and row["passed"] is False
    assert runner.ruled_failures(row)[0] == "amounts"


def test_a_generic_sentence_with_the_required_phrase_fails_by_the_content_half():
    combined, literal = row_for(CONSISTENT, GENERIC), row_for(CONSISTENT, GENERIC)
    apply_ruler([combined], "combined")
    apply_ruler([literal], "literal")
    assert literal["passed"] is True  # the literal ruler accepted it
    assert combined["deterministic"] is True and combined["content"] is False and combined["passed"] is False
    assert combined["judge"]["scores"]["relevance"] < runner.CONTENT_FLOOR
    assert runner.ruled_failures(combined) == ["conteúdo"]


def test_an_answer_without_a_completed_judgement_does_not_pass():
    row = row_for(CONSISTENT, PARAPHRASE, graded=False)
    apply_ruler([row], "combined")
    assert row["content"] is None and row["passed"] is False
    assert runner.ruled_failures(row)[-1] == "conteúdo não julgado"


def test_the_first_judgement_decides_when_the_answer_was_graded_again():
    row = row_for(CONSISTENT, PARAPHRASE)
    row["judge_runs"] = [completed(relevance=3), completed()]
    row["judge"] = row["judge_runs"][0]
    apply_ruler([row], "combined")
    assert row["content"] is False and row["passed"] is False


def test_literal_gives_back_the_literal_verdict_of_a_row_ruled_combined():
    row = row_for(CONSISTENT, PARAPHRASE)
    before = dict(row)
    apply_ruler([row], "combined")
    apply_ruler([row], "literal")
    assert before.pop("expected_claims") and row == before  # review P3-2: the literal row has no journey claims
    with pytest.raises(ValueError):
        apply_ruler([row], "lenient")


# --- the report ------------------------------------------------------------------------------------------------------


def three_rows() -> list[dict]:
    rows = [row_for(CONSISTENT, PARAPHRASE), row_for(CONSISTENT, WRONG_VALUE), row_for(CONSISTENT, GENERIC)]
    for repetition, row in enumerate(rows, start=1):
        row["repetition"] = repetition
    return rows


def test_combined_report_shows_both_halves_and_the_journeys_with_their_expected_claims(tmp_path):
    rows = three_rows()
    apply_ruler(rows, "combined")
    summary = summarize(rows)
    assert summary["overall"]["passed"] == 0.333 and summary["overall"]["deterministic"] == 0.667
    assert summary["overall"]["content"] == 0.333
    md, js = write_report(rows, summary, tmp_path, "combined", {"ruler": "combined"})
    text = md.read_text(encoding="utf-8")
    assert "Aprovadas: 1 de 3; pela régua literal (`--rubric literal`), 1 de 3." in text
    assert "| Recorte | n | Aprovados | Determinístico | Conteúdo (juiz) | Rota |" in text
    assert "Frases obrigatórias (informativo)" in text
    assert "## Jornadas (régua combinada)" in text and "1 de 3 jornadas aprovadas." in text
    lines = [line for line in text.splitlines() if line.startswith("| V030-PRICE-CONSISTENT | ")]
    journeys = [line for line in lines if "consistent ou matches the applicable pricing" in line]
    assert len(journeys) == 3
    assert journeys[0].startswith("| V030-PRICE-CONSISTENT | 1 | sim | sim | sim | - | 5 | ")
    assert journeys[1].startswith("| V030-PRICE-CONSISTENT | 2 | não | não | não | amounts, conteúdo | 3 | ")
    assert journeys[2].startswith("| V030-PRICE-CONSISTENT | 3 | sim | não | não | conteúdo | 5 | 3 | não | ")
    cases = [line for line in lines if "| dev | support | - | answered |" in line]  # the "Casos" table
    assert len(cases) == 3
    assert cases[0].endswith("| sim | sim | sim | - | 10 | 0.0 |")
    saved = json.loads(js.read_text(encoding="utf-8"))
    assert [c["passed"] for c in saved["cases"]] == [True, False, False]
    assert saved["cases"][0]["expected_claims"] == CONSISTENT.expected_claims


def test_literal_report_is_the_report_before_the_combined_ruler(tmp_path):
    """`--rubric literal` reproduces the earlier report: the rows, the summary and every table are unchanged."""
    ruled, untouched = three_rows(), three_rows()
    for row in untouched:
        row.pop("expected_claims", None)  # the rows of before task 90 (review P3-2: the literal JSON drops the key)
    apply_ruler(ruled, "literal")
    for row in (*ruled, *untouched):
        row["judge"]["evaluation_id"] = "fixed"
    assert ruled == untouched
    config = {"mode": "scripted"}
    old_md, _ = write_report(untouched, summarize(untouched), tmp_path / "old", "r", config)
    new_md, _ = write_report(ruled, summarize(ruled), tmp_path / "new", "r", {**config, "ruler": "literal"})

    def body(path):
        return [line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("Gerado em")]

    assert body(new_md) == body(old_md)
    text = new_md.read_text(encoding="utf-8")
    assert "Determinístico" not in text and "## Jornadas" not in text
    assert "| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes |" in text


def test_mark_journeys_fills_rows_recorded_before_the_rename():
    old = {"id": CONSISTENT.id}
    other = {"id": "EX01"}
    mark_journeys([old, other], list(CASES.values()))
    assert old["expected_claims"] == CONSISTENT.expected_claims and "expected_claims" not in other
