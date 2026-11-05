"""Aggregation of repeated judgements with fixed numbers (spec v0.8.0 D12, D19): every figure below was worked out by
hand from the scores listed in the fixture."""

from __future__ import annotations

import pytest

from merchant_assistant.evaluation import aggregate
from merchant_assistant.evaluation.judge import CRITERIA


def record(groundedness: int, claim: bool = False, *, state: str = "completed") -> dict:
    if state != "completed":
        return {"state": state, "scores": {}, "unsupported_claim": None}
    scores = {"groundedness": groundedness, "factual_correctness": 4, "relevance": 5, "usefulness": 3}
    return {"state": state, "scores": scores, "unsupported_claim": claim}


# Case A, B and C, three judgements each. Groundedness: A 4,4,5  B 3,3,3  C 5,4,3.
# Verdict (unsupported_claim):                           A F,F,T  B F,F,F  C T,T,T.
CASES = {
    "A": ("support", "dev", [record(4), record(4), record(5, True)]),
    "B": ("support", "dev", [record(3), record(3), record(3)]),
    "C": ("knowledge", "holdout_synthetic", [record(5, True), record(4, True), record(3, True)]),
}


def assistant_rows() -> list[dict]:
    """Variation of the assistant: one row per execution, one judgement per row."""
    return [
        {"id": case, "route": route, "split": split, "repetition": n, "judge": records[n - 1]}
        for case, (route, split, records) in CASES.items()
        for n in (1, 2, 3)
    ]


def judge_rows() -> list[dict]:
    """Variation of the judge: one row per recorded answer, the judgements in `judge_runs`."""
    return [
        {"id": case, "route": route, "split": split, "judge": records[0], "judge_runs": records}
        for case, (route, split, records) in CASES.items()
    ]


def test_agreement_counts_the_pairs_of_repetitions_of_one_case():
    assert aggregate.agreement([4, 4, 5]) == (1, 3, 3)  # (4,4) equal; (4,5) and (4,5) one apart
    assert aggregate.agreement([3, 3, 3]) == (3, 3, 3)
    assert aggregate.agreement([5, 4, 3]) == (0, 2, 3)  # (5,3) is two apart
    assert aggregate.agreement([4]) == (0, 0, 0)  # one judgement has no pair
    assert aggregate.agreement([True, False, False]) == (1, 3, 3)


@pytest.mark.parametrize("kind, rows", [("assistant", assistant_rows()), ("judge", judge_rows())])
def test_overall_figures_by_criterion(kind, rows):
    overall = aggregate.variation(rows, kind, 3)["overall"]
    assert (overall["cases"], overall["judgements"], overall["failed"]) == (3, 9, 0)
    # mean (13 + 9 + 12) / 9; std (0.5774 + 0 + 1) / 3; exact (1 + 3 + 0) / 9; within one (3 + 3 + 2) / 9
    assert overall["criteria"]["groundedness"] == {
        "mean": 3.78,
        "std": 0.53,
        "exact": 0.444,
        "within_one": 0.889,
        "pairs": 9,
    }
    for constant, mean in (("factual_correctness", 4.0), ("relevance", 5.0), ("usefulness", 3.0)):
        assert overall["criteria"][constant] == {"mean": mean, "std": 0.0, "exact": 1.0, "within_one": 1.0, "pairs": 9}
    # verdict: 4 of 9 true; the pairs agree in 1 + 3 + 3 of 9
    assert overall["unsupported_claim"] == {"rate": 0.444, "exact": 0.778, "pairs": 9}


def test_figures_by_route_and_by_split_are_separate_groups():
    data = aggregate.variation(assistant_rows(), "assistant", 3)
    assert set(data["by_route"]) == {"knowledge", "support"}
    assert set(data["by_split"]) == {"dev", "holdout_synthetic"}
    # support (A and B): mean 22 / 6; std (0.5774 + 0) / 2; exact (1 + 3) / 6; within one 6 / 6
    assert data["by_route"]["support"]["criteria"]["groundedness"] == {
        "mean": 3.67,
        "std": 0.29,
        "exact": 0.667,
        "within_one": 1.0,
        "pairs": 6,
    }
    # knowledge (C): 5, 4, 3
    assert data["by_route"]["knowledge"]["criteria"]["groundedness"] == {
        "mean": 4.0,
        "std": 1.0,
        "exact": 0.0,
        "within_one": 0.667,
        "pairs": 3,
    }
    assert data["by_split"]["dev"] == data["by_route"]["support"]  # the same two cases
    assert data["by_split"]["holdout_synthetic"] == data["by_route"]["knowledge"]
    assert data["by_route"]["knowledge"]["unsupported_claim"] == {"rate": 1.0, "exact": 1.0, "pairs": 3}
    assert data["by_route"]["support"]["unsupported_claim"] == {"rate": 0.167, "exact": 0.667, "pairs": 6}


def test_failed_judgements_are_counted_and_left_out_of_the_figures():
    rows = judge_rows()
    rows[1]["judge_runs"] = [*rows[1]["judge_runs"], record(0, state="failed")]
    overall = aggregate.variation(rows, "judge", 3)["overall"]
    assert (overall["judgements"], overall["failed"]) == (9, 1)
    assert overall["criteria"]["groundedness"]["mean"] == 3.78 and overall["criteria"]["groundedness"]["pairs"] == 9


def test_a_case_with_a_single_judgement_adds_to_the_mean_but_not_to_dispersion_or_agreement():
    rows = [{"id": "solo", "route": "support", "split": "dev", "judge": record(2)}]
    block = aggregate.variation(rows, "assistant", 1)["overall"]
    solo = {"mean": 2.0, "std": None, "exact": None, "within_one": None, "pairs": 0}
    assert block["criteria"]["groundedness"] == solo
    assert block["unsupported_claim"] == {"rate": 0.0, "exact": None, "pairs": 0}


def test_the_two_variations_read_different_fields_and_are_never_mixed():
    both = [row | {"judge_runs": [record(1), record(1), record(1)]} for row in assistant_rows()]
    assert aggregate.variation(both, "assistant", 3)["overall"]["criteria"]["groundedness"]["mean"] == 3.78
    assert aggregate.variation(both, "judge", 3)["overall"]["criteria"]["groundedness"]["mean"] == 1.0
    with pytest.raises(ValueError):
        aggregate.variation(both, "both", 3)


def test_the_report_carries_the_small_sample_caveat_and_marks_small_groups():
    data = aggregate.variation(assistant_rows(), "assistant", 3)
    assert data["caveat"].startswith("Ressalva de amostra pequena (D19): 3 casos com 3 repetições cada")
    assert all(block["few_cases"] for block in (data["overall"], *data["by_route"].values()))
    text = "\n".join(aggregate.render(data))
    assert data["caveat"] in text and "| geral | 3* | groundedness | 3.78 | 0.53 | 0.444 | 0.889 | 9 |" in text
    assert "| rota knowledge | 1* | groundedness | 4.0 | 1.0 | 0.0 | 0.667 | 3 |" in text
    assert "| split holdout_synthetic | 1* | usefulness | 3.0 | 0.0 | 1.0 | 1.0 | 3 |" in text
    assert all(criterion in text for criterion in CRITERIA) and "unsupported_claim (taxa de verdadeiro)" in text


def test_a_group_of_ten_cases_is_not_flagged_as_small():
    rows = [
        {"id": f"case-{n}", "route": "support", "split": "dev", "judge": record(4)} for n in range(aggregate.FEW_CASES)
    ]
    block = aggregate.variation(rows, "assistant", 1)["overall"]
    assert block["cases"] == 10 and block["few_cases"] is False
