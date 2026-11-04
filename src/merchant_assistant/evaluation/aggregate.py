"""Aggregation of repeated judgements (spec v0.8.0 D12, D19): mean, dispersion and agreement of each criterion,
by route and by split.

The two sources of variation are never mixed. `assistant`: the agent answered each case N times and the judge graded
every answer once. `judge`: the same recorded answers graded N times. Both are summarised the same way, over the
scores that belong to one case:

- mean: average of all the scores of the group;
- std: average, over the cases of the group, of the sample standard deviation of the scores of one case (how much
  the repetitions of a case move; the spread between easy and hard cases is not in it);
- exact and within_one: share of the pairs of repetitions of the same case whose scores are equal, or differ by at
  most one point. The verdict `unsupported_claim` has the rate of `true` and the exact agreement only."""

from __future__ import annotations

import statistics
from itertools import combinations

from merchant_assistant.evaluation.judge import CRITERIA

FEW_CASES = 10  # a group with fewer cases is flagged: its numbers move a lot with one case
KINDS = {
    "assistant": "variação do assistente (o agente roda cada caso N vezes e o juiz avalia cada resposta uma vez)",
    "judge": "variação do juiz (as mesmas respostas gravadas avaliadas N vezes)",
}


def agreement(values: list) -> tuple[int, int, int]:
    """(pairs that are equal, pairs within one point, pairs) over the scores of one case."""
    pairs = list(combinations(values, 2))
    equal = sum(1 for a, b in pairs if a == b)
    close = sum(1 for a, b in pairs if abs(int(a) - int(b)) <= 1)
    return equal, close, len(pairs)


def _rate(part: int, whole: int) -> float | None:
    return round(part / whole, 3) if whole else None


def _criterion(series: list[list[int]]) -> dict:
    scores = [score for case in series for score in case]
    spreads = [statistics.stdev(case) for case in series if len(case) >= 2]
    counts = [agreement(case) for case in series]
    pairs = sum(total for _, _, total in counts)
    return {
        "mean": round(float(statistics.mean(scores)), 2) if scores else None,
        "std": round(float(statistics.mean(spreads)), 2) if spreads else None,
        "exact": _rate(sum(equal for equal, _, _ in counts), pairs),
        "within_one": _rate(sum(close for _, close, _ in counts), pairs),
        "pairs": pairs,
    }


def _block(entries: list[dict]) -> dict:
    """One group of cases: `entries` hold the judgement records of each case."""
    done = [[r for r in entry["records"] if r["state"] == "completed"] for entry in entries]
    failed = sum(1 for entry in entries for r in entry["records"] if r["state"] != "completed")
    criteria = {c: _criterion([[r["scores"][c] for r in records] for records in done if records]) for c in CRITERIA}
    verdicts = [[r["unsupported_claim"] for r in records] for records in done if records]
    counts = [agreement(case) for case in verdicts]
    pairs = sum(total for _, _, total in counts)
    flat = [v for case in verdicts for v in case]
    return {
        "cases": len(entries),
        "judgements": len(flat),
        "failed": failed,
        "few_cases": len(entries) < FEW_CASES,
        "criteria": criteria,
        "unsupported_claim": {
            "rate": _rate(sum(flat), len(flat)),
            "exact": _rate(sum(equal for equal, _, _ in counts), pairs),
            "pairs": pairs,
        },
    }


def _entries(rows: list[dict], kind: str) -> list[dict]:
    """The judgement records of each case: across the repetitions of the agent, or across the runs of the judge."""
    entries: dict[str, dict] = {}
    for row in rows:
        entry = entries.setdefault(row["id"], {"route": row["route"], "split": row["split"], "records": []})
        records = row.get("judge_runs") if kind == "judge" else [row.get("judge")]
        entry["records"] += [record for record in records or [] if record]
    return list(entries.values())


def caveat(cases: int, repetitions: int) -> str:
    return (
        f"Ressalva de amostra pequena (D19): {cases} casos com {repetitions} repetições cada; os recortes por rota e "
        f"por split têm menos casos ainda (marcados com * quando há menos de {FEW_CASES}). Médias, desvios e "
        "concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno."
    )


def variation(rows: list[dict], kind: str, repetitions: int) -> dict:
    """Mean, dispersion and agreement of the judgements in `rows`, overall, by route and by split."""
    if kind not in KINDS:
        raise ValueError(f"unknown variation {kind}")
    entries = _entries(rows, kind)
    return {
        "kind": kind,
        "description": KINDS[kind],
        "repetitions": repetitions,
        "caveat": caveat(len(entries), repetitions),
        "overall": _block(entries),
        "by_route": {r: _block([e for e in entries if e["route"] == r]) for r in sorted({e["route"] for e in entries})},
        "by_split": {s: _block([e for e in entries if e["split"] == s]) for s in sorted({e["split"] for e in entries})},
    }


def _fmt(value) -> str:
    return "-" if value is None else str(value)


def render(data: dict) -> list[str]:
    """Markdown of one variation: a table per group with a row per criterion."""
    lines = [
        f"## Variação: {data['description']}",
        "",
        f"Repetições por caso: {data['repetitions']}. Desvio: média, entre os casos, do desvio-padrão amostral dos "
        "scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou "
        "com diferença de até 1 ponto (±1).",
        "",
        f"> {data['caveat']}",
        "",
        "| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    groups = {
        "geral": data["overall"],
        **{f"rota {k}": v for k, v in data["by_route"].items()},
        **{f"split {k}": v for k, v in data["by_split"].items()},
    }
    for label, block in groups.items():
        cases = f"{block['cases']}{'*' if block['few_cases'] else ''}"
        for criterion in CRITERIA:
            c = block["criteria"][criterion]
            lines.append(
                f"| {label} | {cases} | {criterion} | {_fmt(c['mean'])} | {_fmt(c['std'])} | {_fmt(c['exact'])} | "
                f"{_fmt(c['within_one'])} | {c['pairs']} |"
            )
        u = block["unsupported_claim"]
        lines.append(
            f"| {label} | {cases} | unsupported_claim (taxa de verdadeiro) | {_fmt(u['rate'])} | - | "
            f"{_fmt(u['exact'])} | - | {u['pairs']} |"
        )
    failed = data["overall"]["failed"]
    if failed:
        lines += ["", f"{failed} julgamentos falharam e ficaram fora das médias (estado `failed` na avaliação)."]
    return lines
