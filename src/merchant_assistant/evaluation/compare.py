"""`eval-compare --a <report> --b <report>` (task 93, spec v0.12.0 D3, CA-66): paired `eval` reports, no model call.

The reports are paired by case and repetition. For each criterion, the output gives both means and the mean paired
difference B - A with a seeded 95% bootstrap interval. The report describes each side's replanning configuration, so
the sign of the difference remains clear for either input order or when both reports use the same mode.

It also reports the ADR 0024 measures: every `replan` decision counted by its final origin (`rule:<name>` or `model`),
and the paired difference for pairs with at least one model decision versus pairs with rule decisions only. Model
choices include their observation, candidates and selected action. A model choice refused by the replanner guard is
counted under the final rule origin and listed separately with the attempted choice. Cases present in one report only
are listed, never compared; `hops > 0` identifies pairs where either run changed the initial plan.

Input paths inside the repository are reported relative to its root; external inputs are named by file name.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation.aggregate import cell
from merchant_assistant.evaluation.judge import CRITERIA
from merchant_assistant.evaluation.runner import CHECK_KEYS, _records

RESAMPLES = 2000
DEFAULT_SEED = 93
BINARY = ("passed", "deterministic", "content", *CHECK_KEYS)
JUDGE_PREFIX = "judge:"
GROUPS = (  # ADR 0024: pairs grouped by the origin of the `replan` decisions
    ("model", "com pelo menos uma decisão `model`"),
    ("rule", "só decisões por regra"),
    ("none", "sem decisão do `replan`"),
)
CONFIG_FIELDS = ("replan", "mode", "model", "split", "repeat", "cases", "judge", "ruler", "include_replan")


def _key(row: dict) -> tuple[str, int]:
    return row["id"], int(row.get("repetition", 1))


def value(row: dict, criterion: str) -> float | None:
    """1/0 for a check (None when the row has no verdict for it); the score of the first completed judgement for
    `judge:<criterion>`."""
    if criterion.startswith(JUDGE_PREFIX):
        done = [r for r in _records(row) if r.get("state") == "completed"]
        return float(done[0]["scores"][criterion.removeprefix(JUDGE_PREFIX)]) if done else None
    found = row.get(criterion)
    return None if found is None else float(bool(found))


def bootstrap(diffs: list[float], seed: int) -> tuple[float, float] | None:
    """95% percentile interval of the mean difference: the pairs resampled with replacement, `RESAMPLES` times."""
    n = len(diffs)
    if n < 2:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(diffs, k=n)) / n for _ in range(RESAMPLES))
    return means[round(0.025 * (RESAMPLES - 1))], means[round(0.975 * (RESAMPLES - 1))]


def paired(pairs: list[tuple[dict, dict]], criterion: str, seed: int) -> dict | None:
    values = [
        (a, b)
        for row_a, row_b in pairs
        if (a := value(row_a, criterion)) is not None and (b := value(row_b, criterion)) is not None
    ]
    if not values:
        return None
    n = len(values)
    diffs = [b - a for a, b in values]
    interval = bootstrap(diffs, seed)
    return {
        "n": n,
        "a": round(sum(a for a, _ in values) / n, 3),
        "b": round(sum(b for _, b in values) / n, 3),
        "diff": round(sum(diffs) / n, 3),
        "interval": [round(interval[0], 3), round(interval[1], 3)] if interval else None,
        "excludes_zero": bool(interval and (interval[0] > 0 or interval[1] < 0)),
    }


def by_criterion(pairs: list[tuple[dict, dict]], criteria: list[str], seed: int) -> dict:
    return {c: result for c in criteria if (result := paired(pairs, c, seed)) is not None}


def criteria_of(rows: list[dict]) -> list[str]:
    judged = any(_records(r) for r in rows)
    return [*BINARY, *(f"{JUDGE_PREFIX}{c}" for c in CRITERIA if judged)]


def group(row_a: dict, row_b: dict) -> str:
    origins = [d.get("origin", "") for d in (row_a.get("replan") or []) + (row_b.get("replan") or [])]
    if not origins:
        return "none"
    return "model" if "model" in origins else "rule"


def origins(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for decision in row.get("replan") or []:
            counts[decision.get("origin", "?")] = counts.get(decision.get("origin", "?"), 0) + 1
    return dict(sorted(counts.items()))


def changed_plan(row_a: dict, row_b: dict) -> bool:
    return any(d.get("hops", 0) > 0 for d in (row_a.get("replan") or []) + (row_b.get("replan") or []))


def refused_model(side: str, rows: list[dict]) -> list[dict]:
    """The choices of the model the guard refused: counted by their final origin, listed here."""
    return [
        {
            "side": side,
            "case_id": row["id"],
            "repetition": int(row.get("repetition", 1)),
            "route": row.get("route"),
            "observed": decision.get("observed"),
            "candidates": decision.get("candidates", []),
            "refused": decision.get("refused"),
            "origin": decision.get("origin"),
            "reason": decision.get("reason"),
        }
        for row in sorted(rows, key=_key)
        for decision in row.get("replan") or []
        if decision.get("refused_origin") == "model"
    ]


def display_path(path: Path, root: Path | None = None) -> str:
    """Relative to the repository root (`PROJECT_ROOT`, read at each call) when inside it; otherwise the file name
    only."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(Path(root or PROJECT_ROOT).resolve()).as_posix()
    except ValueError:
        return resolved.name


def model_decisions(side: str, rows: list[dict]) -> list[dict]:
    return [
        {
            "side": side,
            "case_id": row["id"],
            "repetition": int(row.get("repetition", 1)),
            "route": row.get("route"),
            "observed": decision.get("observed"),
            "candidates": decision.get("candidates", []),
            "next": decision.get("next"),
            "review": decision.get("review"),
            "reason": decision.get("reason"),
        }
        for row in sorted(rows, key=_key)
        for decision in row.get("replan") or []
        if decision.get("origin") == "model"
    ]


def compare(report_a: dict, report_b: dict, *, seed: int = DEFAULT_SEED) -> dict:
    rows_a = {_key(r): r for r in report_a["cases"]}
    rows_b = {_key(r): r for r in report_b["cases"]}
    keys = sorted(rows_a.keys() & rows_b.keys())
    pairs = [(rows_a[k], rows_b[k]) for k in keys]
    criteria = criteria_of([r for pair in pairs for r in pair])
    routes = sorted({a.get("route") or "-" for a, _ in pairs})
    count_a, count_b = origins(list(rows_a.values())), origins(list(rows_b.values()))
    groups = {name: [p for p in pairs if group(*p) == name] for name, _ in GROUPS}
    changed = [p for p in pairs if changed_plan(*p)]
    out = {
        "config": {
            side: {f: report.get("config", {}).get(f) for f in CONFIG_FIELDS}
            for side, report in zip(("a", "b"), (report_a, report_b), strict=True)
        },
        "seed": seed,
        "resamples": RESAMPLES,
        "pairs": len(pairs),
        "unpaired": {
            "a_only": [list(k) for k in sorted(rows_a.keys() - rows_b.keys())],
            "b_only": [list(k) for k in sorted(rows_b.keys() - rows_a.keys())],
        },
        "route_differs": [list(_key(a)) for a, b in pairs if a.get("route") != b.get("route")],
        "by_criterion": by_criterion(pairs, criteria, seed),
        "by_route": {
            route: by_criterion([p for p in pairs if (p[0].get("route") or "-") == route], criteria, seed)
            for route in routes
        },
        "origins": {
            "a": count_a,
            "b": count_b,
            "model_share": {
                side: round(counts.get("model", 0) / total, 3) if (total := sum(counts.values())) else None
                for side, counts in (("a", count_a), ("b", count_b))
            },
            "refused_model": {
                side: len(refused_model(side, list(rows.values()))) for side, rows in (("a", rows_a), ("b", rows_b))
            },
        },
        "by_decision_group": {
            name: {"pairs": len(selected), "by_criterion": by_criterion(selected, criteria, seed)}
            for name, selected in groups.items()
        },
        "changed_plan": {"pairs": len(changed), "by_criterion": by_criterion(changed, criteria, seed)},
        "model_decisions": [*model_decisions("a", list(rows_a.values())), *model_decisions("b", list(rows_b.values()))],
        "refused_model": [*refused_model("a", list(rows_a.values())), *refused_model("b", list(rows_b.values()))],
        "unrecorded_decisions": {
            side: sum("replan" not in r for r in rows.values()) for side, rows in (("a", rows_a), ("b", rows_b))
        },
    }
    convs_a = {c["id"]: c for c in report_a.get("conversations") or []}
    convs_b = {c["id"]: c for c in report_b.get("conversations") or []}
    if convs_a and convs_b:
        common = sorted(convs_a.keys() & convs_b.keys())
        out["conversations"] = {
            "rows": [{"id": c, "a": bool(convs_a[c]["passed"]), "b": bool(convs_b[c]["passed"])} for c in common],
            "passed": paired([(convs_a[c], convs_b[c]) for c in common], "passed", seed),
            "a_only": sorted(convs_a.keys() - convs_b.keys()),
            "b_only": sorted(convs_b.keys() - convs_a.keys()),
        }
    return out


# --- report -----------------------------------------------------------------------------------------------------------


def _num(value) -> str:
    return "-" if value is None else f"{value:.3f}"


def _interval(result: dict) -> str:
    return "-" if result["interval"] is None else f"[{result['interval'][0]:+.3f}, {result['interval'][1]:+.3f}]"


def _row(result: dict) -> str:
    return (
        f"{result['n']} | {_num(result['a'])} | {_num(result['b'])} | {result['diff']:+.3f} | {_interval(result)} | "
        f"{'sim' if result['excludes_zero'] else 'não'} |"
    )


def _replan_description(config: dict) -> str:
    mode = config.get("replan")
    if mode == "on":
        return "replanning enabled (`REPLAN=on`)"
    if mode == "off":
        return "replanning disabled (`REPLAN=off`)"
    return "replanning mode unspecified"


HEADER = "n | A | B | B − A | IC 95% | sem o zero |"
RULE = "--- | --- | --- | --- | --- | --- |"


def render(data: dict, sources: tuple[str, str]) -> list[str]:
    lines = [
        "# Comparação pareada de avaliações",
        "",
        f"- **A:** `{sources[0]}`, configuração `{json.dumps(data['config']['a'], ensure_ascii=False)}`.",
        f"- **B:** `{sources[1]}`, configuração `{json.dumps(data['config']['b'], ensure_ascii=False)}`.",
        "",
        f"Pareamento por caso e repetição: {data['pairs']} pares. Em cada critério, A e B são as médias (1 = aprovado; "
        "notas do juiz de 1 a 5), B − A é a média das diferenças pareadas e o intervalo de 95% vem do bootstrap dos "
        f"pares ({data['resamples']} reamostras, semente {data['seed']}). A usa "
        f"{_replan_description(data['config']['a'])} e B usa {_replan_description(data['config']['b'])}. "
        "Uma diferença positiva indica que B teve pontuação maior que A; uma negativa indica que A teve pontuação "
        "maior que B. Sem chamada de modelo.",
        "",
        "## Por critério",
        "",
        f"| Critério | {HEADER}",
        f"| --- | {RULE}",
    ]
    lines += [f"| {c} | {_row(r)}" for c, r in data["by_criterion"].items()]
    lines += ["", "## Por rota", "", "Rota do Router no relatório A (o plano inicial).", ""]
    if data["route_differs"]:
        listed = ", ".join(f"{i} (rep {r})" for i, r in data["route_differs"])
        lines += [f"Pares com rota diferente em B: {listed}.", ""]
    lines += [f"| Rota | Critério | {HEADER}", f"| --- | --- | {RULE}"]
    for route, results in data["by_route"].items():
        lines += [f"| {cell(route)} | {c} | {_row(r)}" for c, r in results.items()]

    o = data["origins"]
    lines += [
        "",
        "## Decisões do replanejamento por origem",
        "",
        "Todas as decisões do passo `replan` gravadas nos traces de cada relatório (ADR 0024, medida 1).",
        "",
        "| Origem | A | B |",
        "| --- | --- | --- |",
    ]
    for origin in sorted(set(o["a"]) | set(o["b"])):
        lines.append(f"| `{origin}` | {o['a'].get(origin, 0)} | {o['b'].get(origin, 0)} |")
    lines.append(f"| total | {sum(o['a'].values())} | {sum(o['b'].values())} |")
    share = o["model_share"]
    refused = o["refused_model"]
    lines += [
        "",
        f"Parte das decisões de origem `model`: A {_num(share['a'])}; B {_num(share['b'])}.",
        "",
        "Cada decisão conta pela origem final: a guarda do replanejador tem a última palavra, e a escolha do modelo "
        f"que ela recusou conta como `rule:<guarda>`. Modelo consultado e recusado pela guarda: A {refused['a']}; "
        f"B {refused['b']}.",
    ]
    missing = data["unrecorded_decisions"]
    if missing["a"] or missing["b"]:
        lines += [
            "",
            f"Linhas sem as decisões gravadas (relatório anterior à tarefa 93): A {missing['a']}; B {missing['b']}.",
        ]

    lines += [
        "",
        "## Diferença pareada por origem das decisões",
        "",
        "Pares separados pelas decisões do `replan` dos dois lados (ADR 0024, medida 2).",
    ]
    for name, title in GROUPS:
        block = data["by_decision_group"][name]
        lines += ["", f"### Pares {title}: {block['pairs']}", ""]
        if block["by_criterion"]:
            lines += [f"| Critério | {HEADER}", f"| --- | {RULE}"]
            lines += [f"| {c} | {_row(r)}" for c, r in block["by_criterion"].items()]
        else:
            lines.append("Nenhum par.")
    changed = data["changed_plan"]
    lines += ["", f"### Pares com mudança de plano (`hops > 0` em algum lado): {changed['pairs']}", ""]
    if changed["by_criterion"]:
        lines += [f"| Critério | {HEADER}", f"| --- | {RULE}"]
        lines += [f"| {c} | {_row(r)}" for c, r in changed["by_criterion"].items()]
    else:
        lines.append("Nenhum par.")

    lines += ["", "## Decisões de origem `model`", ""]
    if data["model_decisions"]:
        lines += [
            "| Lado | Caso | Rep | Rota | Observação | Candidatos | Escolha | Motivo |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for d in data["model_decisions"]:
            observed = json.dumps(d["observed"], ensure_ascii=False, sort_keys=True)
            lines.append(
                f"| {d['side'].upper()} | {cell(d['case_id'])} | {d['repetition']} | {cell(d['route'])} | "
                f"`{cell(observed)}` | {cell(', '.join(d['candidates']) or 'nenhum')} | "
                f"{cell(d['next'])} ({cell(d['review'])}) | {cell(d['reason'] or '-')} |"
            )
    else:
        lines.append("Nenhuma.")

    lines += ["", "## Modelo consultado e recusado pela guarda", ""]
    if data["refused_model"]:
        lines += [
            "| Lado | Caso | Rep | Rota | Observação | Candidatos | Escolha recusada | Origem final | Motivo |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for d in data["refused_model"]:
            observed = json.dumps(d["observed"], ensure_ascii=False, sort_keys=True)
            lines.append(
                f"| {d['side'].upper()} | {cell(d['case_id'])} | {d['repetition']} | {cell(d['route'])} | "
                f"`{cell(observed)}` | {cell(', '.join(d['candidates']) or 'nenhum')} | {cell(d['refused'])} | "
                f"`{cell(d['origin'])}` | {cell(d['reason'] or '-')} |"
            )
    else:
        lines.append("Nenhuma.")

    unpaired = data["unpaired"]
    lines += ["", "## Casos sem par", ""]
    if unpaired["a_only"] or unpaired["b_only"]:
        for side, keys in (("A", unpaired["a_only"]), ("B", unpaired["b_only"])):
            listed = ", ".join(f"{i} (rep {r})" for i, r in keys) or "nenhum"
            lines.append(f"- Só em {side}: {listed}.")
    else:
        lines.append("Nenhum.")

    if "conversations" in data:
        conv = data["conversations"]
        lines += ["", "## Conversas de vários turnos", "", "| Conversa | A | B |", "| --- | --- | --- |"]
        lines += [f"| {cell(r['id'])} | {'sim' if r['a'] else 'não'} | {'sim' if r['b'] else 'não'} |"
                  for r in conv["rows"]]
        if conv["passed"]:
            lines += ["", f"| Critério | {HEADER}", f"| --- | {RULE}", f"| passed | {_row(conv['passed'])}"]
        if conv["a_only"] or conv["b_only"]:
            lines += ["", f"Sem par: só em A {conv['a_only'] or 'nenhuma'}; só em B {conv['b_only'] or 'nenhuma'}."]
    return lines


def write(path_a: Path, path_b: Path, out_dir: Path, name: str, *, seed: int = DEFAULT_SEED) -> tuple[Path, Path, dict]:
    report_a = json.loads(Path(path_a).read_text(encoding="utf-8"))
    report_b = json.loads(Path(path_b).read_text(encoding="utf-8"))
    data = compare(report_a, report_b, seed=seed)
    sources = (display_path(path_a), display_path(path_b))  # keep personal paths out of the report
    data["sources"] = list(sources)
    out_dir.mkdir(parents=True, exist_ok=True)
    js = out_dir / f"{name}.json"
    md = out_dir / f"{name}.md"
    js.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    md.write_bytes(("\n".join(render(data, sources)) + "\n").encode("utf-8"))
    return md, js, data
