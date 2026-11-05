"""End-to-end evaluation over labeled scenarios: routing, status, tools, content checks, grounding, latency, cost,
plus an optional model-graded rubric (clearly labeled as model judgment, not human review)."""

from __future__ import annotations

import json
import re
import statistics
import uuid
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from merchant_assistant.api.schemas import MessageRequest
from merchant_assistant.evaluation import aggregate, evidence
from merchant_assistant.evaluation.judge import CRITERIA, Judge, save_evaluation
from merchant_assistant.guardrails.output import amounts
from merchant_assistant.llm import pricing
from merchant_assistant.llm.base import CallSpec, Usage
from merchant_assistant.orchestration.budget import BudgetExceeded


@dataclass
class Case:
    id: str
    split: str
    message: str
    language: str
    accepted_routes: list[str]
    expected_status: str
    expected_tools: list[str]
    must_include_amounts: list[int]
    must_include_any: list[list[str]]
    expect_sources: bool
    must_not_include: list[str] = field(default_factory=list)
    user_id: str = "cliente1988"
    must_not_assert: list[str] = field(default_factory=list)


_CLAUSE_BOUNDARIES = re.compile(
    r"[.!?;,:\n\u2013\u2014]+|\b(?:but|however|whereas|although|yet|mas|porém|contudo|entretanto|todavia)\b",
    re.IGNORECASE,
)
# Typographic apostrophes and look-alikes (U+2018, U+2019, U+02BC, U+2032, U+00B4, U+0060) compare as "'".
_APOSTROPHES = str.maketrans(dict.fromkeys("\u2018\u2019\u02bc\u2032\u00b4\u0060", "'"))
_QUALIFIED_ASSERTION_PREFIXES = (
    # Only the doubt forms that predate v0.8.0 (cannot confirm/verify/determine/tell whether, not sure/uncertain/
    # not clear whether, cannot say, não consigo/não sei ... se, não posso dizer) keep their 100-character window.
    # Every form added since then, every "that"/"que" complement, "does not mean", "no indication" and an open
    # conditional only qualify the assertion that follows them directly, so a later, unqualified claim in the
    # same clause ("... that there was a problem and the fee is correct") is still caught.
    re.compile(
        r"\b(?:cannot|can't|could not|couldn't|am not able to|is not able to|unable to)\s+"
        r"(?:confirm|verify|determine|tell)\s+(?:whether|if)\b[^.!?;,]{0,100}$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:cannot|can not|can't|could not|couldn't|am not able to|is not able to|are not able to|"
        r"was not able to|wasn't able to|unable to|(?:not possible|impossible|no way) to)\s+"
        r"(?:confirm|verify|determine|tell|know|say|establish)\s+(?:whether|if|that)\s+$",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:not sure|uncertain|not clear)\s+(?:whether|if)\b[^.!?;,]{0,100}$", re.IGNORECASE),
    re.compile(r"\b(?:not sure|uncertain|unclear|not clear)\s+(?:whether|if|that)\s+$", re.IGNORECASE),
    re.compile(r"\b(?:do not|don't|does not|doesn't|did not|didn't)\s+know\s+(?:whether|if)\s+$", re.IGNORECASE),
    re.compile(r"\b(?:cannot|can't|couldn't)\s+say\b(?!\s+that\b)[^.!?;,]{0,100}$", re.IGNORECASE),
    re.compile(
        r"\b(?:does not|doesn't|do not|don't|did not|didn't|would not|wouldn't|will not|won't)\s+"
        r"(?:necessarily\s+)?(?:mean|establish|indicate|show|prove|imply|confirm)\s+(?:that\s+)?$",
        re.IGNORECASE,
    ),
    re.compile(r"\bno\s+(?:indication|evidence|sign|proof)\s+that\s+$", re.IGNORECASE),
    re.compile(r"\b(?:if|in case)\s+(?:you\s+(?:think|believe|suspect|feel)\s+(?:that\s+)?)?$", re.IGNORECASE),
    re.compile(
        r"\b(?:não foi possível|não é possível|não consigo|não podemos|não pude|não dá para)\s+"
        r"(?:confirmar|verificar|determinar|saber)\s+se\b[^.!?;,]{0,100}$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:não foi possível|não é possível|não consigo|não conseguimos|não podemos|não pude|não dá para|"
        r"não há como|não tem como)\s+(?:confirmar|verificar|determinar|saber|afirmar|dizer|garantir)\s+"
        r"(?:se|que)\s+$",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:não sei|não tenho certeza|incerto|não está claro)\s+se\b[^.!?;,]{0,100}$", re.IGNORECASE),
    re.compile(r"\b(?:não sabemos|não se sabe|não temos certeza)\s+se\s+$", re.IGNORECASE),
    re.compile(r"\b(?:não posso|não dá para)\s+dizer\b(?!\s+que\b)[^.!?;,]{0,100}$", re.IGNORECASE),
    re.compile(r"\b(?:não posso|não podemos|não dá para)\s+(?:dizer|afirmar)\s+(?:(?:se|que)\s+)?$", re.IGNORECASE),
    re.compile(
        r"\bnão\s+(?:necessariamente\s+)?(?:significa|quer dizer|indica|mostra|prova|implica|comprova|confirma)"
        r"\s+que\s+$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bnão há\s+(?:indicação|indício|indícios|evidência|evidências|sinal|sinais|prova|provas)\s+de\s+que\s+$",
        re.IGNORECASE,
    ),
)


def _normalize(text: str) -> str:
    return text.translate(_APOSTROPHES).casefold()


def _assertion_is_present(answer: str, assertion: str) -> bool:
    """Match a forbidden EN/PT assertion, allowing only a small set of scoped uncertainty forms.

    This intentionally handles a bounded set of English and Portuguese constructions (doubt, "does not mean that",
    "no indication that", "não significa que", "não há como saber se", a directly preceding conditional); it is not
    a general-purpose natural-language negation detector. Typographic apostrophes are compared as "'". Clause
    boundaries prevent an earlier lack-of-evidence statement from qualifying a later assertion.
    """
    normalized_assertion = _normalize(assertion)
    for clause in _CLAUSE_BOUNDARIES.split(_normalize(answer)):
        start = 0
        while (index := clause.find(normalized_assertion, start)) >= 0:
            prefix = clause[:index]
            if not any(pattern.search(prefix) for pattern in _QUALIFIED_ASSERTION_PREFIXES):
                return True
            start = index + len(normalized_assertion)
    return False


def load_cases(paths: list[Path]) -> list[Case]:
    cases = []
    for path in paths:
        cases += [Case(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return cases


class BudgetMeter:
    """Meters judge calls against the installation budget (they are paid calls too)."""

    def __init__(self, budget, *, request_id: str = "eval-judge", max_cost_usd: float | None = None) -> None:
        self.budget, self.cost_usd = budget, 0.0
        self.request_id, self.max_cost_usd = request_id, max_cost_usd

    def reserve(
        self,
        *,
        agent: str,
        model: str,
        est_input_tokens: int,
        max_output_tokens: int,
        web_search_calls: int = 0,
        effective_parameters: dict | None = None,
    ):
        amount = pricing.estimate(model, est_input_tokens, max_output_tokens, web_search_calls)
        if self.max_cost_usd is not None and self.cost_usd + amount > self.max_cost_usd:
            raise BudgetExceeded("evaluation", amount, self.max_cost_usd - self.cost_usd)
        return self.budget.reserve(request_id=self.request_id, agent=agent, model=model, amount=amount), model, amount

    def settle(self, reservation, usage: Usage | None) -> None:
        ledger_id, model, amount = reservation
        actual = pricing.cost(model, usage) if usage else None
        self.budget.settle(ledger_id, actual)
        self.cost_usd += amount if actual is None else actual


class JudgeScore(BaseModel):
    answers_question: int = Field(description="1-5: does the reply address what the merchant asked?")
    clarity_and_tone: int = Field(description="1-5: clear, concise, polite support language in the right language?")
    honesty: int = Field(description="1-5: avoids unsupported claims, promises and internal jargon; admits gaps?")
    comment: str = Field(description="One short sentence justifying the lowest score.")


JUDGE_MAX_OUTPUT_TOKENS = 200


def judge_evidence(message: str, body: dict, sources: list[str]) -> dict:
    """The only data sent to the model judge: question, outcome labels, source titles and the persisted reply."""
    return {
        "merchant_message": message,
        "status": body["status"],
        "route": body["route"],
        "sources": sources,
        "reply": body["answer"],
    }


def judge_spec(judge_prompt, evidence: dict) -> CallSpec:
    return CallSpec(
        agent="judge",
        instructions=judge_prompt.render(),
        effort="none",
        max_output_tokens=JUDGE_MAX_OUTPUT_TOKENS,
        input=json.dumps(evidence, ensure_ascii=False),
    )


def _checks(case: Case, body: dict, trace: dict) -> dict:
    answer = body["answer"]
    lower = answer.translate(_APOSTROPHES).lower()
    tools = [s["step"].removeprefix("tool:") for s in trace["steps"] if s["step"].startswith("tool:")]
    found_amounts = amounts(answer)
    return {
        "route_ok": body["route"] in case.accepted_routes,
        "status_ok": body["status"] == case.expected_status,
        "language_ok": body["language"] == case.language,
        "tools_ok": set(case.expected_tools) <= set(tools),
        "amounts_ok": set(case.must_include_amounts) <= found_amounts,
        "content_ok": all(
            any(t.translate(_APOSTROPHES).lower() in lower for t in group) for group in case.must_include_any
        ),
        "forbidden_ok": not any(t.translate(_APOSTROPHES).lower() in lower for t in case.must_not_include)
        and not any(_assertion_is_present(answer, assertion) for assertion in case.must_not_assert),
        "sources_ok": bool(body["sources"]) if case.expect_sources else True,
        "grounded_ok": not trace["detail"].get("output_violations"),
        "tools_called": tools,
    }


CHECK_KEYS = [
    "route_ok",
    "status_ok",
    "language_ok",
    "tools_ok",
    "amounts_ok",
    "content_ok",
    "forbidden_ok",
    "sources_ok",
    "grounded_ok",
]


CRITICAL_CHECKS = {
    "grounded_ok": "unsupported_answer",
    "forbidden_ok": "forbidden_assertion_or_promise",
    "isolation_ok": "cross_customer_leak",
}


def persisted_checks(body: dict | None, trace: dict | None, case: Case | None, *, foreign_markers=()) -> dict:
    """Deterministic checks over a persisted reply and its trace, without any model call.

    With a scenario label every existing check applies; without one only the label-independent checks run
    (grounding/output violations, errors and cross-customer markers) and the rest is reported as not evaluated.
    Critical failures are listed one by one and never averaged."""
    label_independent = ["grounded_ok", "errors_ok", "isolation_ok"]
    if body is None or trace is None:
        return {
            "origin": None,
            "status": "unavailable",
            "results": {},
            "not_evaluated": [*CHECK_KEYS, "errors_ok", "isolation_ok"],
            "critical_failures": [],
            "passed": 0,
            "total": 0,
            "tools_called": [],
        }
    if case is not None:
        full = _checks(case, body, trace)
        results = {key: bool(full[key]) for key in CHECK_KEYS}
        tools_called = full["tools_called"]
    else:
        results = {"grounded_ok": not trace["detail"].get("output_violations")}
        tools_called = [s["step"].removeprefix("tool:") for s in trace["steps"] if s["step"].startswith("tool:")]
    results["errors_ok"] = not trace.get("errors")
    lower = body["answer"].casefold()
    results["isolation_ok"] = not any(marker.casefold() in lower for marker in foreign_markers if marker)
    critical = [
        {"code": code, "check": key} for key, code in CRITICAL_CHECKS.items() if results.get(key) is False
    ]
    if case is not None and case.expected_status != "refused" and body["status"] == "refused":
        critical.append({"code": "undue_refusal", "check": "status_ok"})
    return {
        "origin": f"scenario:{case.id}" if case is not None else "label_independent",
        "status": "evaluated",
        "results": results,
        "not_evaluated": [key for key in [*CHECK_KEYS, *label_independent] if key not in results],
        "critical_failures": critical,
        "passed": sum(results.values()),
        "total": len(results),
        "tools_called": tools_called,
        "violations": trace["detail"].get("output_violations", []),
    }


# The router opens every attendance and the personality closes it; the specialists in between are the path (D16).
FRAMING_AGENTS = ("router", "personality")


def executed_path(agents: list[str]) -> str:
    """The specialists that ran, in order, from the `agents` list of the reply (e.g. `knowledge → customer_support`).
    It describes what happened after any replanning and never changes `route_ok`, which compares the route the
    Router chose (the initial plan) with the accepted routes of the case (D16)."""
    return " → ".join(agent for agent in agents if agent not in FRAMING_AGENTS)


def run(
    orchestrator,
    cases: list[Case],
    *,
    judge: Judge | None = None,
    repeat: int = 1,
    keep_evidence: bool = False,
) -> list[dict]:
    """Runs every case `repeat` times through the system. With a `judge`, each answer is graded once, over the
    evidence it was built from (variation of the assistant, D12). `keep_evidence` records that evidence without a
    judge, so the answers can be graded later (`rejudge`)."""
    if repeat < 1:
        raise ValueError("repeat must be at least 1")
    needs_evidence = judge is not None or keep_evidence
    texts = evidence.chunk_texts(orchestrator.settings.data_dir) if needs_evidence else {}
    results = []
    for repetition in range(1, repeat + 1):
        for case in cases:
            results.append(_run_case(orchestrator, case, repetition, judge, needs_evidence, texts))
    return results


def _run_case(orchestrator, case: Case, repetition: int, judge: Judge | None, needs_evidence: bool, texts) -> dict:
    request_id = f"req_eval{uuid.uuid4().hex[:12]}"
    with evidence.record_tool_results() if needs_evidence else nullcontext([]) as outcomes:
        response = orchestrator.handle(MessageRequest(message=case.message, user_id=case.user_id), request_id)
    body = response.model_dump()
    trace = orchestrator.trace(request_id)
    checks = _checks(case, body, trace)
    row = {
        "id": case.id,
        "repetition": repetition,
        "request_id": request_id,
        "split": case.split,
        "language": case.language,
        "message": case.message,
        "route": body["route"],
        "status": body["status"],
        "agents": body["agents"],
        "executed_path": executed_path(body["agents"]),
        "answer": body["answer"],
        "sources": [s["title"] for s in body["sources"]],
        "duration_ms": trace["duration_ms"],
        "cost_usd": trace["cost_usd"],
        "model_calls": trace["model_calls"],
        "errors": trace["errors"],
        "violations": trace["detail"].get("output_violations", []),
        **checks,
    }
    row["passed"] = all(row[k] for k in CHECK_KEYS)
    if needs_evidence:
        row["judge_input"], row["evidence_truncation"] = evidence.judge_input(
            case.message, body, row["sources"], outcomes, trace, texts
        )
    if judge is not None:
        row["judge"] = judge.evaluate(row["judge_input"])
    return row


def load_recorded_answers(path: Path) -> tuple[list[dict], dict]:
    """The answers of the first execution of a campaign report, with the evidence they were judged on."""
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = [row for row in report["cases"] if row.get("repetition", 1) == 1]
    if not rows:
        raise ValueError(f"{path} has no recorded answers")
    unrecorded = [row["id"] for row in rows if "judge_input" not in row]
    if unrecorded:
        raise ValueError(
            f"{path} did not record the evidence of {len(unrecorded)} answer(s) (for example {unrecorded[0]}): run "
            "the campaign with --judge or --repeat so the answers can be graded again"
        )
    return rows, report["config"]


def rejudge(rows: list[dict], judge: Judge, repeat: int) -> list[dict]:
    """Variation of the judge (D12): the same recorded answers graded `repeat` times; the agent does not run."""
    if repeat < 1:
        raise ValueError("repeat must be at least 1")
    graded = []
    for row in rows:
        runs = [judge.evaluate(row["judge_input"], repetition=k) for k in range(1, repeat + 1)]
        kept = {key: value for key, value in row.items() if key != "judge"}
        replaced = {"source_cost_usd": row["cost_usd"], "cost_usd": 0.0, "judge": runs[0], "judge_runs": runs}
        graded.append(kept | replaced)
    return graded


def _records(row: dict) -> list[dict]:
    return row.get("judge_runs") or ([row["judge"]] if row.get("judge") else [])


def persist_judgements(conn, judge: Judge, rows: list[dict]) -> int:
    """Writes every judgement of the rows into `run_evaluations`; returns how many."""
    count = 0
    for row in rows:
        for record in _records(row):
            save_evaluation(conn, request_id=row["request_id"], judge=judge, record=record, data=row["judge_input"])
            count += 1
    return count


def _rate(rows: list[dict], key: str) -> float | None:
    return round(sum(bool(r[key]) for r in rows) / len(rows), 3) if rows else None


def summarize(rows: list[dict]) -> dict:
    def block(selected: list[dict]) -> dict:
        durations = sorted(r["duration_ms"] for r in selected)
        out = {"n": len(selected), "passed": _rate(selected, "passed")}
        out |= {k: _rate(selected, k) for k in CHECK_KEYS}
        if durations:
            out["latency_p50_ms"] = int(statistics.median(durations))
            out["latency_p95_ms"] = durations[min(len(durations) - 1, int(round(0.95 * (len(durations) - 1))))]
        out["cost_usd"] = round(sum(r["cost_usd"] or 0 for r in selected), 5)
        records = [record for r in selected for record in _records(r)]
        done = [record for record in records if record.get("state") == "completed"]
        if records:
            out["judge_failed"] = len(records) - len(done)
            judged = [r for r in selected if _records(r)]
            web = [r for r in judged if evidence.WEB_NOTE in (r.get("judge_input") or {}).get("evidence_notes", [])]
            out["judge_web_note"] = {
                "judged_answers": len(judged),
                "answers": len(web),
                "unsupported": sum(1 for r in web if any(rec.get("unsupported_claim") for rec in _records(r))),
            }
        if done:
            means = {c: statistics.mean(rec["scores"][c] for rec in done) for c in CRITERIA}
            out["judge_means"] = {c: round(float(value), 2) for c, value in means.items()}
            out["unsupported_claim_rate"] = round(sum(bool(rec["unsupported_claim"]) for rec in done) / len(done), 3)
        return out

    paths: dict[str, dict[str, int]] = {}
    for r in rows:
        counts = paths.setdefault(r["route"], {})
        counts[r.get("executed_path", "")] = counts.get(r.get("executed_path", ""), 0) + 1
    summary = {
        "overall": block(rows),
        "by_split": {s: block([r for r in rows if r["split"] == s]) for s in sorted({r["split"] for r in rows})},
        "by_language": {lang: block([r for r in rows if r["language"] == lang]) for lang in ("en", "pt")},
        "paths": {route: dict(sorted(counts.items())) for route, counts in sorted(paths.items())},
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    judged = [record for r in rows for record in _records(r)]
    if judged:
        summary["judge_cost_usd"] = round(sum(record.get("cost_usd") or 0 for record in judged), 5)
    return summary


CRITERIA_LABELS = {
    "groundedness": "fundamentação",
    "factual_correctness": "correção factual",
    "relevance": "relevância",
    "usefulness": "utilidade",
}


def write_report(rows: list[dict], summary: dict, out_dir: Path, name: str, config: dict) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{name}.json"
    json_path.write_text(
        json.dumps({"config": config, "summary": summary, "cases": rows}, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8",
    )
    o = summary["overall"]
    lines = [
        f"# Relatório de avaliação: {name}",
        "",
        f"Gerado em {summary['generated_at']}. Configuração: `{json.dumps(config, ensure_ascii=False)}`.",
        "",
        "## Resumo",
        "",
        "| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | "
        "p50 (ms) | p95 (ms) | Custo (US$) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    blocks = {
        "geral": o,
        **{f"split {k}": v for k, v in summary["by_split"].items()},
        **{f"idioma {k}": v for k, v in summary["by_language"].items()},
    }
    for label, b in blocks.items():
        lines.append(
            f"| {label} | {b['n']} | {b['passed']} | {b['route_ok']} | {b['status_ok']} | {b['tools_ok']} | "
            f"{b['amounts_ok']} | {b['content_ok']} | {b['sources_ok']} | {b['grounded_ok']} | "
            f"{b.get('latency_p50_ms', '-')} | {b.get('latency_p95_ms', '-')} | {b['cost_usd']} |"
        )
    if "judge_means" in o:
        means = ", ".join(f"{CRITERIA_LABELS[c]} {o['judge_means'][c]}" for c in CRITERIA)
        lines += [
            "",
            f"Rubrica por modelo (média 1-5, não é revisão humana): {means}. Afirmações sem suporte: "
            f"{o['unsupported_claim_rate']} das respostas julgadas. "
            f"Custo do juiz: US$ {summary.get('judge_cost_usd', 0)}.",
        ]
    if o.get("judge_failed"):
        lines += ["", f"{o['judge_failed']} julgamentos falharam e ficaram fora das médias."]
    if "judge_web_note" in o:
        web = o["judge_web_note"]
        lines += [
            "",
            f"Respostas julgadas sob a nota de busca web: {web['answers']} de {web['judged_answers']}. O texto da "
            "busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode "
            "conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de "
            f"ferramenta. Dessas respostas, {web['unsupported']} foram marcadas como afirmação sem suporte.",
        ]
    recorded = [r["evidence_truncation"] for r in rows if "evidence_truncation" in r]
    if recorded:
        cut = sum(1 for t in recorded if t["truncated"])
        lines += [
            "",
            f"Evidência truncada em {cut} de {len(recorded)} respostas (limite de {recorded[0]['limit_chars']} "
            "caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).",
        ]
    flagged = [(r, [rec for rec in _records(r) if rec.get("unsupported_claim")]) for r in rows]
    if any(marks for _, marks in flagged):
        lines += [
            "",
            "## Afirmações sem suporte (veredito crítico)",
            "",
            "Listadas uma a uma, nunca diluídas na média.",
            "",
            "| Caso | Rep | Rota | Julgamentos marcados | Fundamentação (primeiro julgamento marcado) |",
            "| --- | --- | --- | --- | --- |",
        ]
        for r, marks in flagged:
            if marks:
                lines.append(
                    f"| {aggregate.cell(r['id'])} | {r.get('repetition', 1)} | {aggregate.cell(r['route'])} | "
                    f"{len(marks)} de {len(_records(r))} | {aggregate.cell(marks[0]['reasons']['groundedness'])} |"
                )
    lines += [
        "",
        "## Rota planejada e caminho executado",
        "",
        "A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista "
        "de agentes da resposta e não entra em `route_ok` (D16).",
        "",
        "| Rota | Caminho executado | Respostas |",
        "| --- | --- | --- |",
    ]
    for route, counts in summary.get("paths", {}).items():
        for path, count in counts.items():
            lines.append(f"| {aggregate.cell(route)} | {aggregate.cell(path or '-')} | {count} |")
    if "variation" in summary:
        lines += ["", *aggregate.render(summary["variation"])]
    lines += [
        "",
        "## Casos",
        "",
        "| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        failed = [k.removesuffix("_ok") for k in CHECK_KEYS if not r[k]]
        lines.append(
            f"| {aggregate.cell(r['id'])} | {r.get('repetition', 1)} | {aggregate.cell(r['split'])} | "
            f"{aggregate.cell(r['route'])} | {aggregate.cell(r.get('executed_path') or '-')} | {r['status']} | "
            f"{'sim' if r['passed'] else 'não'} | {', '.join(failed) or '-'} | {r['duration_ms']} | {r['cost_usd']} |"
        )
    md_path = out_dir / f"{name}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


# --- multi-turn conversations -------------------------------------------------------------------------------------


def _accepts(expected, value) -> bool:
    if expected is None:
        return True
    return value in expected if isinstance(expected, list) else value == expected


def run_conversations(orchestrator, path: Path, user_id: str = "cliente1988") -> list[dict]:
    """Each scenario is one conversation; every turn is checked for route, status, case state and evidence."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        scenario = json.loads(line)
        conversation_id, protocols, turns = None, [], []
        for spec in scenario["turns"]:
            request_id = f"req_evalfu{uuid.uuid4().hex[:10]}"
            response = orchestrator.handle(
                MessageRequest(message=spec["message"], user_id=user_id, conversation_id=conversation_id), request_id
            )
            conversation_id = response.conversation_id
            trace = orchestrator.trace(request_id)
            if response.handoff:
                protocols.append(response.handoff.protocol)
            checks = {
                "route_ok": response.route in spec["accepted_routes"],
                "status_ok": _accepts(spec.get("expected_status"), response.status),
                "state_ok": _accepts(spec.get("expected_case_state"), response.resolution.state),
                "evidence_ok": _accepts(spec.get("expected_evidence"), response.resolution.evidence)
                if spec.get("expected_evidence")
                else True,
                "same_protocol_ok": len(set(protocols)) <= 1 if spec.get("same_protocol") else True,
                "grounded_ok": not trace["detail"].get("output_violations"),
            }
            turns.append(
                {
                    "message": spec["message"],
                    "route": response.route,
                    "status": response.status,
                    "case_state": response.resolution.state,
                    "evidence": response.resolution.evidence,
                    "answer": response.answer,
                    "duration_ms": trace["duration_ms"],
                    "cost_usd": trace["cost_usd"],
                    **checks,
                    "passed": all(checks.values()),
                }
            )
        rows.append(
            {
                "id": scenario["id"],
                "split": scenario["split"],
                "language": scenario["language"],
                "description": scenario["description"],
                "turns": turns,
                "passed": all(t["passed"] for t in turns),
                "cost_usd": round(sum(t["cost_usd"] or 0 for t in turns), 6),
            }
        )
    return rows


def append_conversation_report(md_path: Path, json_path: Path, rows: list[dict]) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data["conversations"] = rows
    passed = sum(r["passed"] for r in rows)
    data["summary"]["conversations"] = {
        "n": len(rows),
        "passed": passed,
        "cost_usd": round(sum(r["cost_usd"] for r in rows), 5),
    }
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    lines = [
        "",
        "## Conversas de vários turnos",
        "",
        f"{passed} de {len(rows)} conversas aprovadas em todos os turnos.",
        "",
        "| Conversa | Turno | Rota | Status | Caso | Aprovado | Falhas |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    keys = ["route_ok", "status_ok", "state_ok", "evidence_ok", "same_protocol_ok", "grounded_ok"]
    for r in rows:
        for i, t in enumerate(r["turns"], start=1):
            failed = [k.removesuffix("_ok") for k in keys if not t[k]]
            lines.append(
                f"| {r['id']} | {i} | {t['route']} | {t['status']} | {t['case_state']} | "
                f"{'sim' if t['passed'] else 'não'} | {', '.join(failed) or '-'} |"
            )
    md_path.write_text(md_path.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8")
