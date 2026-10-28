"""End-to-end evaluation over labeled scenarios: routing, status, tools, content checks, grounding, latency, cost,
plus an optional model-graded rubric (clearly labeled as model judgment, not human review)."""

from __future__ import annotations

import json
import re
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
    r"[.!?;,:\n]+|\b(?:but|however|whereas|although|yet|mas|porém|contudo|entretanto|todavia)\b",
    re.IGNORECASE,
)
_QUALIFIED_ASSERTION_PREFIXES = (
    re.compile(
        r"\b(?:cannot|can't|could not|couldn't|am not able to|is not able to|unable to)\s+"
        r"(?:confirm|verify|determine|tell)\s+(?:whether|if)\b[^.!?;,]{0,100}$",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:not sure|uncertain|not clear)\s+(?:whether|if|that)\b[^.!?;,]{0,100}$", re.IGNORECASE),
    re.compile(r"\b(?:cannot|can't|couldn't)\s+say\b[^.!?;,]{0,100}$", re.IGNORECASE),
    re.compile(
        r"\b(?:não foi possível|não é possível|não consigo|não podemos|não pude|não dá para)\s+"
        r"(?:confirmar|verificar|determinar|saber)\s+se\b[^.!?;,]{0,100}$",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:não sei|não tenho certeza|incerto|não está claro)\s+se\b[^.!?;,]{0,100}$", re.IGNORECASE),
    re.compile(r"\b(?:não posso|não dá para)\s+dizer\b[^.!?;,]{0,100}$", re.IGNORECASE),
)


def _assertion_is_present(answer: str, assertion: str) -> bool:
    """Match a forbidden EN/PT assertion, allowing only a small set of scoped uncertainty forms.

    This intentionally handles a bounded set of English and Portuguese constructions; it is not
    a general-purpose natural-language negation detector. Clause boundaries prevent an earlier
    lack-of-evidence statement from qualifying a later assertion.
    """
    normalized_assertion = assertion.casefold()
    for clause in _CLAUSE_BOUNDARIES.split(answer.casefold()):
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
        "forbidden_ok": not any(t.lower() in lower for t in case.must_not_include)
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
            spec = judge_spec(judge_prompt, judge_evidence(case.message, body, row["sources"]))
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
