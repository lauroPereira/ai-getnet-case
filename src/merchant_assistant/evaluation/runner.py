"""End-to-end evaluation over labeled scenarios: routing, status, tools, content checks, grounding, latency, cost,
plus an optional model-graded rubric (clearly labeled as model judgment, not human review)."""

from __future__ import annotations

import json
import statistics
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from merchant_assistant.api.schemas import MessageRequest
from merchant_assistant.guardrails.output import amounts
from merchant_assistant.llm import pricing
from merchant_assistant.llm.base import CallSpec, NullMeter, Usage
from merchant_assistant.llm.prompts import load_prompt


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


def load_cases(paths: list[Path]) -> list[Case]:
    cases = []
    for path in paths:
        cases += [Case(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return cases


class BudgetMeter:
    """Meters judge calls against the installation budget (they are paid calls too)."""

    def __init__(self, budget) -> None:
        self.budget, self.cost_usd = budget, 0.0

    def reserve(
        self, *, agent: str, model: str, est_input_tokens: int, max_output_tokens: int, web_search_calls: int = 0
    ):
        amount = pricing.estimate(model, est_input_tokens, max_output_tokens, web_search_calls)
        return self.budget.reserve(request_id="eval-judge", agent=agent, model=model, amount=amount), model, amount

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


def _checks(case: Case, body: dict, trace: dict) -> dict:
    answer = body["answer"]
    lower = answer.lower()
    tools = [s["step"].removeprefix("tool:") for s in trace["steps"] if s["step"].startswith("tool:")]
    found_amounts = amounts(answer)
    return {
        "route_ok": body["route"] in case.accepted_routes,
        "status_ok": body["status"] == case.expected_status,
        "language_ok": body["language"] == case.language,
        "tools_ok": set(case.expected_tools) <= set(tools),
        "amounts_ok": set(case.must_include_amounts) <= found_amounts,
        "content_ok": all(any(t.lower() in lower for t in group) for group in case.must_include_any),
        "forbidden_ok": not any(t.lower() in lower for t in case.must_not_include),
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


def run(
    orchestrator, cases: list[Case], *, judge_llm=None, prompts_dir: Path | None = None, judge_meter=None
) -> list[dict]:
    results = []
    judge_prompt = load_prompt(prompts_dir, "judge") if judge_llm and prompts_dir else None
    for case in cases:
        request_id = f"req_eval{uuid.uuid4().hex[:12]}"
        response = orchestrator.handle(MessageRequest(message=case.message, user_id=case.user_id), request_id)
        body = response.model_dump()
        trace = orchestrator.trace(request_id)
        checks = _checks(case, body, trace)
        row = {
            "id": case.id,
            "split": case.split,
            "language": case.language,
            "message": case.message,
            "route": body["route"],
            "status": body["status"],
            "agents": body["agents"],
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
        if judge_prompt is not None:
            spec = CallSpec(
                agent="judge",
                instructions=judge_prompt.render(),
                effort="none",
                max_output_tokens=200,
                input=json.dumps(
                    {
                        "merchant_message": case.message,
                        "status": body["status"],
                        "route": body["route"],
                        "sources": row["sources"],
                        "reply": body["answer"],
                    },
                    ensure_ascii=False,
                ),
            )
            try:
                score = judge_llm.parse(spec, JudgeScore, judge_meter or NullMeter()).value
                row["judge"] = score.model_dump()
            except Exception as exc:  # the judge is optional; never fails the run
                row["judge"] = {"error": str(exc)}
        results.append(row)
    return results


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
        judged = [r["judge"] for r in selected if isinstance(r.get("judge"), dict) and "error" not in r["judge"]]
        if judged:
            out["judge_means"] = {
                k: round(statistics.mean(j[k] for j in judged), 2)
                for k in ("answers_question", "clarity_and_tone", "honesty")
            }
        return out

    return {
        "overall": block(rows),
        "by_split": {s: block([r for r in rows if r["split"] == s]) for s in sorted({r["split"] for r in rows})},
        "by_language": {lang: block([r for r in rows if r["language"] == lang]) for lang in ("en", "pt")},
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
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
        j = o["judge_means"]
        lines += [
            "",
            f"Rubrica por modelo (média 1-5, não é revisão humana): responde à pergunta {j['answers_question']}, "
            f"clareza e tom {j['clarity_and_tone']}, honestidade {j['honesty']}.",
        ]
    lines += [
        "",
        "## Casos",
        "",
        "| Caso | Split | Rota | Status | Aprovado | Falhas | ms | US$ |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        failed = [k.removesuffix("_ok") for k in CHECK_KEYS if not r[k]]
        lines.append(
            f"| {r['id']} | {r['split']} | {r['route']} | {r['status']} | {'sim' if r['passed'] else 'não'} | "
            f"{', '.join(failed) or '-'} | {r['duration_ms']} | {r['cost_usd']} |"
        )
    md_path = out_dir / f"{name}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path
