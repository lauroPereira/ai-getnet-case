from __future__ import annotations

import pytest

from merchant_assistant.evaluation.campaign import estimate_campaign_cost


def measured(case_id: str, split: str, agent: float, judge: float, repetition: int = 1) -> dict:
    return {
        "id": case_id,
        "split": split,
        "repetition": repetition,
        "cost_usd": agent,
        "judge": {"cost_usd": judge},
    }


def test_campaign_estimate_applies_both_d12_phases_and_keeps_splits_separate():
    rows = [
        measured("D1", "dev", 0.01, 0.002),
        measured("D2", "dev", 0.03, 0.004),
        measured("H1", "holdout", 0.02, 0.003),
        measured("H2", "holdout", 0.04, 0.005),
        measured("H3", "holdout", 0.03, 0.001),
        measured("D1", "dev", 99.0, 99.0, repetition=2),  # D12 repeats never inflate the five-case sample.
    ]

    estimate = estimate_campaign_cost(
        rows, {"dev": 10, "holdout": 5, "holdout_v080": 20}, followup_conversations=4, followup_turns=10
    )

    assert estimate["measured_cases"] == 5
    assert estimate["measured_agent_cost_usd"] == 0.13
    assert estimate["measured_first_judge_cost_usd"] == 0.015
    assert estimate["agent_repetitions"] == estimate["judge_repetitions"] == 3
    assert estimate["formula_per_case"] == "3 * measured_agent_cost + 6 * measured_first_judge_cost"
    assert estimate["by_split"]["dev"] == {
        "cases": 10,
        "sample_cases": 2,
        "sample_source": "split sample",
        "mean_agent_cost_usd": 0.02,
        "mean_judge_cost_usd": 0.003,
        "agent_phase_usd": 0.6,
        "assistant_variation_judges_usd": 0.09,
        "judge_variation_usd": 0.09,
        "estimated_cost_usd": 0.78,
    }
    assert estimate["by_split"]["holdout"]["estimated_cost_usd"] == 0.54
    assert estimate["by_split"]["holdout_v080"]["sample_source"] == "global sample fallback"
    assert estimate["by_split"]["holdout_v080"]["estimated_cost_usd"] == 1.92
    assert estimate["followup_conversations"] == {
        "conversations": 4,
        "turns": 10,
        "runs_per_turn": 1,
        "mean_agent_cost_per_turn_usd": 0.026,
        "agent_cost_usd": 0.26,
        "judge_runs": 0,
        "judge_cost_usd": 0.0,
        "formula": "followup_turns * global_measured_mean_agent_cost; no judge",
        "estimated_cost_usd": 0.26,
    }
    assert estimate["estimated_cost_usd"] == 3.5


def test_campaign_estimate_requires_five_distinct_first_run_cases():
    rows = [measured(f"D{i}", "dev", 0.01, 0.002) for i in range(4)]
    rows += [measured("D1", "dev", 0.01, 0.002, repetition=2)]

    with pytest.raises(ValueError, match="At least 5 distinct first-run cases"):
        estimate_campaign_cost(rows, {"dev": 10})


@pytest.mark.parametrize(
    ("rows", "counts", "message"),
    [
        ([measured(f"D{i}", "other", 0.01, 0.002) for i in range(5)], {"dev": 1}, "unknown split"),
        ([measured(f"D{i}", "dev", -0.01, 0.002) for i in range(5)], {"dev": 1}, "negative or non-finite"),
        ([measured("D1", "dev", 0.01, 0.002)] * 5, {"dev": 1}, "appears more than once"),
    ],
)
def test_campaign_estimate_rejects_bad_measurements(rows, counts, message):
    with pytest.raises(ValueError, match=message):
        estimate_campaign_cost(rows, counts)
