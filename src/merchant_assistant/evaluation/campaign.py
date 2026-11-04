"""Budget and cost planning for the v0.8.0 evaluation campaign."""

from __future__ import annotations

import math
from collections import defaultdict

AGENT_REPETITIONS = 3
JUDGE_REPETITIONS = 3
MIN_MEASURED_CASES = 5


def estimate_campaign_cost(
    measured_rows: list[dict],
    case_counts: dict[str, int],
    *,
    min_measured_cases: int = MIN_MEASURED_CASES,
) -> dict:
    """Project the v0.8.0 campaign from first-run measurements, keeping each split visible.

    The first D12 phase runs each case three times and judges every answer once. The second phase judges the first
    answer three times. A case measured once therefore contributes three agent costs and six judge costs.
    Splits without a sample use the global sample means; the report records that fallback explicitly.
    """
    if not isinstance(case_counts, dict) or not case_counts:
        raise ValueError("At least one split with a case count is required.")

    counts: dict[str, int] = {}
    for split, count in case_counts.items():
        if not isinstance(split, str) or not split.strip() or isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("Split names and case counts must be valid strings and integers.")
        if count < 0:
            raise ValueError(f"Case count for split {split} cannot be negative.")
        counts[split] = count

    first_rows: dict[str, dict] = {}
    for row in measured_rows:
        repetition = row.get("repetition", 1)
        if repetition != 1:
            continue
        case_id = row.get("id")
        split = row.get("split")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("Every measured row needs a case id.")
        if split not in counts:
            raise ValueError(f"Measured case {case_id} has an unknown split: {split!r}.")
        if case_id in first_rows:
            raise ValueError(f"Measured case {case_id} appears more than once in repetition 1.")
        first_rows[case_id] = row

    if len(first_rows) < min_measured_cases:
        raise ValueError(
            f"At least {min_measured_cases} distinct first-run cases are required to "
            "estimate the campaign."
        )

    by_split: dict[str, list[tuple[float, float]]] = defaultdict(list)
    all_costs: list[tuple[float, float]] = []
    for case_id, row in first_rows.items():
        agent_cost = row.get("cost_usd")
        judge_cost = (row.get("judge") or {}).get("cost_usd")
        costs = (agent_cost, judge_cost)
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in costs):
            raise ValueError(f"Measured case {case_id} must include numeric agent and first-judge costs.")
        if any(not math.isfinite(value) or value < 0 for value in costs):
            raise ValueError(f"Measured case {case_id} has a negative or non-finite cost.")
        normalized = (float(agent_cost), float(judge_cost))
        by_split[row["split"]].append(normalized)
        all_costs.append(normalized)

    global_agent = sum(agent for agent, _ in all_costs) / len(all_costs)
    global_judge = sum(judge for _, judge in all_costs) / len(all_costs)
    split_estimates = {}
    for split, count in sorted(counts.items()):
        sample = by_split.get(split)
        agent_average, judge_average = (
            (sum(agent for agent, _ in sample) / len(sample), sum(judge for _, judge in sample) / len(sample))
            if sample
            else (global_agent, global_judge)
        )
        source = "split sample" if sample else "global sample fallback"
        agent_total = count * AGENT_REPETITIONS * agent_average
        first_phase_judge_total = count * AGENT_REPETITIONS * judge_average
        judge_repeat_total = count * JUDGE_REPETITIONS * judge_average
        split_estimates[split] = {
            "cases": count,
            "sample_cases": len(sample) if sample else 0,
            "sample_source": source,
            "mean_agent_cost_usd": round(agent_average, 8),
            "mean_judge_cost_usd": round(judge_average, 8),
            "agent_phase_usd": round(agent_total, 8),
            "assistant_variation_judges_usd": round(first_phase_judge_total, 8),
            "judge_variation_usd": round(judge_repeat_total, 8),
            "estimated_cost_usd": round(agent_total + first_phase_judge_total + judge_repeat_total, 8),
        }

    return {
        "measured_cases": len(first_rows),
        "agent_repetitions": AGENT_REPETITIONS,
        "judge_repetitions": JUDGE_REPETITIONS,
        "formula_per_case": "3 * measured_agent_cost + 6 * measured_first_judge_cost",
        "by_split": split_estimates,
        "estimated_cost_usd": round(sum(part["estimated_cost_usd"] for part in split_estimates.values()), 8),
    }
