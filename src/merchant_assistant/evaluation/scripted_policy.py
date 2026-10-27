"""Rule-based behaviour for the scripted model, used by tests and by `eval --scripted`.

It mimics what a well-behaved model should do for the challenge scenarios, so the whole graph (routing, tools,
guards, persistence, tracing) can be exercised deterministically and at zero cost. It says nothing about the
quality of a real model: that is measured by the real evaluation run.
"""

from __future__ import annotations

import json
import re

from merchant_assistant.agents.common import guess_language
from merchant_assistant.llm.base import LLMError
from merchant_assistant.llm.scripted import ScriptedCall, ToolPlan

ROUTE_RULES: list[tuple[str, str, str | None]] = [
    (r"\b(?:atendente|humano|human|attendant|real person|falar com algu[eé]m)\b", "human_handoff", None),
    (r"card number|n[uú]mero (?:do|de) cart[aã]o|\bfraud|fraude|burlar|bypass|antifraud", "out_of_scope", None),
    (r"weather|previs[aã]o do tempo|\bclima\b|forecast", "general_web", None),
    (r"exchange rate|c[aâ]mbio|cota[cç][aã]o|\beuro\b|d[oó]lar", "general_web", None),
    (r"won'?t connect|n[aã]o conecta|sem conex|internet|wi-?fi", "knowledge_and_support", "device"),
    (r"decline|negad|recusad", "knowledge_and_support", "authorization"),
    (
        r"yesterday'?s sales|vendas de ontem|deposited|depositad|rcv_|receb[ií]ve(?:l|is) d[oa]",
        "support",
        "receivables",
    ),
    (r"^\W*(?:n[aã]o (?:est[aá] )?funciona(?:ndo)?|it'?s not working|not working|help)\W*$", "clarify", None),
    (
        r"get cl[aá]ssica|get smart|\bpix\b|antecipa|advance|credi[aá]rio|payment link|link de pagamento|whatsapp|"
        r"get xyz|maquininha|card machine",
        "knowledge",
        None,
    ),
]


def route_for(message: str) -> tuple[str, str | None]:
    for pattern, route, topic in ROUTE_RULES:
        if re.search(pattern, message, flags=re.IGNORECASE):
            return route, topic
    return "clarify", None


def _router(call: ScriptedCall) -> dict:
    message = call.spec.context["message"]
    route, topic = route_for(message)
    language = guess_language(message)
    question = None
    if route == "clarify":
        question = "Sobre o que você precisa de ajuda?" if language == "pt" else "What do you need help with?"
    safety = "unsafe" if route == "out_of_scope" else "none"
    return {
        "route": route,
        "language": language,
        "topic": topic,
        "intents": [route],
        "safety": safety,
        "clarification_question": question,
    }


def _first_sentences(text: str, limit: int = 220) -> str:
    body = text.split("\n", 1)[-1].replace("\n", " ")
    return body[:limit].rsplit(" ", 1)[0] if len(body) > limit else body


def _knowledge(call: ScriptedCall) -> dict:
    passages = call.spec.context.get("passages", [])
    if not passages or "get xyz" in call.spec.context["message"].lower():
        return {"points": [], "used_passages": [], "evidence_sufficient": False, "missing": ["not in passages"]}
    return {
        "points": [_first_sentences(passages[0]["text"])],
        "used_passages": [1],
        "evidence_sufficient": True,
        "missing": [],
    }


def _load(results: list[str], i: int) -> dict:
    return json.loads(results[i]) if i < len(results) else {}


def _support(call: ScriptedCall) -> ToolPlan:
    ctx = call.spec.context
    message, topic = ctx["message"], ctx.get("topic")
    pt = guess_language(message) == "pt"

    def failed(results: list[str]) -> dict | None:
        errors = [r for r in (json.loads(x) for x in results) if "error" in r]
        if errors:
            code = errors[0]["error"]["code"]
            if code == "FORBIDDEN_RESOURCE":
                return {
                    "points": ["Não consigo acessar esse registro." if pt else "I can't access that record."],
                    "needs_selection": False,
                    "missing": [],
                    "escalate": False,
                    "escalation_reason": None,
                }
            return {
                "points": [],
                "needs_selection": False,
                "missing": [],
                "escalate": True,
                "escalation_reason": f"tool_error:{code}",
            }
        return None

    if "rcv_002" in message:
        return ToolPlan(
            [("get_payout_status", {"receivable_ids": ["rcv_002_0001"]})],
            final=lambda r: (
                failed(r)
                or {"points": [], "needs_selection": False, "missing": [], "escalate": False, "escalation_reason": None}
            ),
        )
    if topic == "receivables":

        def follow(results: list[str]) -> list[tuple[str, dict]]:
            data = _load(results, 0)
            ids = [r["receivable_id"] for r in data.get("receivables", [])]
            return [("get_payout_status", {"receivable_ids": ids})] if ids else []

        def final(results: list[str]) -> dict:
            if (bad := failed(results)) is not None:
                return bad
            schedule, payouts = _load(results, 0), {p["receivable_id"]: p for p in _load(results, 1).get("payouts", [])}
            points = []
            for r in schedule.get("receivables", []):
                confirmed = payouts.get(r["receivable_id"], {}).get("credit_confirmed")
                state = (
                    ("crédito confirmado" if pt else "credit confirmed")
                    if confirmed
                    else ("crédito ainda não confirmado" if pt else "credit not confirmed yet")
                )
                points.append(
                    f"{r['payment_type']}: {r['net_amount']['display']} — {r['expected_payment_date']} — {state}"
                )
            return {
                "points": points,
                "needs_selection": False,
                "missing": [],
                "escalate": False,
                "escalation_reason": None,
            }

        return ToolPlan([("get_receivables_schedule", {"period": "yesterday"})], final=final, follow_up=follow)
    if topic == "device":

        def final_device(results: list[str]) -> dict:
            if (bad := failed(results)) is not None:
                return bad
            d = _load(results, 0)["devices"][0]
            steps = [s for s in ctx.get("procedure", "").split("\n") if s][:2]
            return {
                "points": [f"{d['model']}: {d['status']} ({d['minutes_since_last_seen']} min)", *steps],
                "needs_selection": False,
                "missing": [],
                "escalate": False,
                "escalation_reason": None,
            }

        return ToolPlan([("get_device_status", {})], final=final_device)
    if topic == "authorization":

        def final_auth(results: list[str]) -> dict:
            if (bad := failed(results)) is not None:
                return bad
            e = _load(results, 0)["events"][0]
            return {
                "points": [f"{e['amount']['display']}: {e['customer_message']}", e["next_step"]],
                "needs_selection": False,
                "missing": [],
                "escalate": False,
                "escalation_reason": None,
            }

        return ToolPlan([("find_authorization_events", {})], final=final_auth)
    return ToolPlan(
        [("get_contract_snapshot", {})],
        final=lambda r: (
            failed(r)
            or {
                "points": ["Produtos: " + ", ".join(_load(r, 0)["products"])],
                "needs_selection": False,
                "missing": [],
                "escalate": False,
                "escalation_reason": None,
            }
        ),
    )


def _personality(call: ScriptedCall) -> dict:
    c = call.spec.context["contributions"]
    parts = []
    if c.get("policy_text"):
        parts.append(c["policy_text"])
    if "knowledge" in c:
        parts += c["knowledge"]["points"] or [c["knowledge"].get("note", "")]
    if "support" in c:
        parts += c["support"]["points"]
    if "handoff" in c:
        parts.append(c["handoff"]["message"])
    return {"answer": "\n".join(p for p in parts if p)}


def handler(call: ScriptedCall):
    agent = call.spec.agent
    if agent == "router":
        return _router(call)
    if agent == "knowledge" and call.kind == "web":
        if "unavailable" in call.spec.input.lower():
            return LLMError("web search unavailable (scripted)")
        return {
            "text": "1 EUR = R$ 5,57 (Example FX, 2026-10-26 10:00).",
            "citations": [{"url": "https://example.com/fx", "title": "Example FX"}],
        }
    if agent == "knowledge":
        return _knowledge(call)
    if agent == "customer_support":
        return _support(call)
    if agent == "escalation":
        return {"summary": "Lojista pediu atendimento humano.", "pending_question": "Retornar ao lojista."}
    if agent == "personality":
        return _personality(call)
    raise AssertionError(f"unexpected agent {agent}")
