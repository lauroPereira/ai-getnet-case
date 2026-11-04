"""Rule-based behaviour for the scripted model, used by tests and by `eval --scripted`.

It mimics what a well-behaved model should do for the challenge scenarios, so the whole graph (routing, tools,
guards, persistence, tracing) can be exercised deterministically and at zero cost. It says nothing about the
quality of a real model: that is measured by the real evaluation run.
"""

from __future__ import annotations

import json
import re

from merchant_assistant.agents.common import guess_language, policy
from merchant_assistant.llm.base import LLMError
from merchant_assistant.llm.scripted import ScriptedCall, ToolPlan

# `router.v6`: a question about whether different conditions, plan or rate were used for a charge or sale (any
# interrogative form, "Were...", "Was...", "Did...", "Foi...") is a pricing question about one real charge of the
# merchant, never a clarification. It needs a word of difference or change, the conditions or plan, a charge or sale,
# and a period that points at one the merchant already had ("yesterday's credit charge"): a general question such as
# "Do the conditions change for sales above R$ 1.000?" stays a knowledge question.
CONDITIONS_QUESTION = (
    r"(?s)^(?=.*\b(?:differ(?:s|ed)?|different|chang(?:e|es|ed)|diferentes?|distint[ao]s?|mudou|mudaram)\b)"
    r"(?=.*(?:\bconditions?\b|\bplans?\b|\bplano\b|condi[cç][aãoõ]\w*))"
    r"(?=.*(?:\bcharge[ds]?\b|\bsales?\b|\bvendas?\b|cobran[cç]a|cobrad))"
    r"(?=.*\b(?:yesterday|today|last|latest|ontem|hoje|passad[ao]|[uú]ltim[ao])\b)"
)

ROUTE_RULES: list[tuple[str, str, str | None]] = [
    (
        r"encerrar (?:o |meu )?contrato|fechar (?:o |meu )?contrato|terminate (?:the )?contract|close (?:my )?contract",
        "human_handoff",
        None,
    ),
    (r"\b(?:atendente|humano|human|attendant|real person|falar com algu[eé]m)\b", "human_handoff", None),
    (r"card number|n[uú]mero (?:do|de) cart[aã]o|\bfraud|fraude|burlar|bypass|antifraud", "out_of_scope", None),
    (r"weather|previs[aã]o do tempo|\bclima\b|forecast", "general_web", None),
    (r"exchange rate|c[aâ]mbio|cota[cç][aã]o|\beuro\b|d[oó]lar", "general_web", None),
    (r"bandeira|card scheme|habilita[cç][aã]o|enablement|visa|mastercard", "support", "enablement"),
    (
        r"cancelamento|cancelar venda|sale cancellation|cancel sale|cancellation status",
        "support",
        "cancellation",
    ),
    (
        r"\bfee\b|charge|pricing|cobran[cç]a|"
        r"(?:taxa|tarifa).{0,50}(?:venda|pix|cr[eé]dito|d[eé]bito|coerente|cobrad)|"
        r"(?:diverg|insuficiente|comparar).{0,50}(?:taxa|tarifa)",
        "support",
        "pricing",
    ),
    (CONDITIONS_QUESTION, "support", "pricing"),
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


RESOLVED = r"voltou a funcionar|funcionou|resolvid|deu certo|it works|it worked|working now|fixed"
STILL_FAILING = r"continua|ainda n[aã]o|still|didn'?t work|n[aã]o funcionou|j[aá] fiz|j[aá] tentei|already tried"
THANKS = r"^\W*(?:obrigad[oa]|valeu|thanks|thank you|ok|entendi)\W*$"


def case_signal_for(message: str, has_history: bool) -> str:
    if not has_history:
        return "none"
    if re.search(RESOLVED, message, flags=re.IGNORECASE):
        return "resolved"
    if re.search(STILL_FAILING, message, flags=re.IGNORECASE):
        return "still_failing"
    if re.search(THANKS, message, flags=re.IGNORECASE):
        return "thanks_only"
    return "none"


def _router(call: ScriptedCall) -> dict:
    ctx = call.spec.context
    message = ctx["message"]
    history = ctx.get("history", [])
    signal = case_signal_for(message, bool(history))
    route, topic = route_for(message)
    case_topic = (ctx.get("case") or {}).get("topic")
    if signal in ("resolved", "thanks_only"):
        route, topic = "acknowledgement", None
    elif signal == "still_failing" and case_topic:
        route, topic = "knowledge_and_support", case_topic
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
        "case_signal": signal,
    }


def _first_sentences(text: str, limit: int = 220) -> str:
    body = text.split("\n", 1)[-1].replace("\n", " ")
    return body[:limit].rsplit(" ", 1)[0] if len(body) > limit else body


def _knowledge(call: ScriptedCall) -> dict:
    passages = call.spec.context.get("passages", [])
    if not passages or "get xyz" in call.spec.context["message"].lower():
        return {"points": [], "used_passages": [], "evidence_sufficient": False, "missing": ["not in passages"]}
    if call.spec.context.get("mode") == "procedure":  # several steps, one per passage
        top = passages[:4]
        return {
            "points": [_first_sentences(p["text"], 120) for p in top],
            "used_passages": [p["n"] for p in top],
            "evidence_sufficient": True,
            "missing": [],
        }
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
            tried = {a["step"] for a in ctx.get("attempts", [])}
            candidates = [s.lstrip("- ").strip() for s in ctx.get("procedure", "").split("\n") if s.strip()]
            steps = [s[:80] for s in candidates if s[:80] not in tried][:2]
            if not steps:
                return {
                    "points": [],
                    "needs_selection": False,
                    "missing": [],
                    "escalate": True,
                    "escalation_reason": "no_untried_steps",
                    "steps_given": [],
                }
            return {
                "points": [f"{d['model']}: {d['status']} ({d['minutes_since_last_seen']} min)", *steps],
                "needs_selection": False,
                "missing": [],
                "escalate": False,
                "escalation_reason": None,
                "steps_given": steps,
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
    if topic == "pricing":
        low = message.casefold()
        args = {"period": "yesterday"}
        if any(
            word in low
            for word in ("insuficiente", "sem evidência", "no evidence", "not enough evidence", "insufficient")
        ):
            args = {"period": "latest", "payment_type": "credit", "installments": 2}
        elif re.search(CONDITIONS_QUESTION, message, flags=re.IGNORECASE) or any(
            word in low for word in ("diferentes condições", "condições diferentes", "different conditions", "legacy")
        ):
            args["payment_type"] = (
                "pix" if "pix" in low else "debit" if re.search(r"d[eé]bito|debit", low) else "credit"
            )
        elif any(word in low for word in ("divergência", "divergente", "diverg", "mismatch")):
            args["payment_type"] = "pix"
        else:
            args["payment_type"] = "debit"

        def final_price(results: list[str]) -> dict:
            if (bad := failed(results)) is not None:
                return bad
            comparison = _load(results, 0).get("comparison", {})
            result = comparison.get("result", "insufficient_evidence")
            labels = {
                "consistent": "A comparação sintética encontrou valores coerentes."
                if pt
                else "The synthetic comparison found consistent values.",
                "different_conditions": (
                    "As condições registradas diferem das condições simuladas; isso não comprova erro."
                )
                if pt
                else "Recorded conditions differ from the simulated conditions; that does not prove an error.",
                "divergence": (
                    "Há uma divergência na comparação sintética. Vou encaminhar para análise; "
                    "isso não confirma reembolso."
                )
                if pt
                else (
                    "The synthetic comparison shows a divergence. I will refer it for review; "
                    "this does not confirm a refund."
                ),
                "insufficient_evidence": ("Não há evidência aplicável suficiente para comparar os valores.")
                if pt
                else "There is not enough applicable evidence to compare the amounts.",
            }
            points = [labels[result]]
            if comparison.get("expected_fee_display") is not None:
                if pt:
                    points.append(
                        f"Taxa esperada: {comparison['expected_fee_display']}; "
                        f"cobrada: {comparison['charged_fee_display']}."
                    )
                else:
                    points.append(
                        f"Expected {comparison['expected_fee_display']}; charged {comparison['charged_fee_display']}."
                    )
            if result == "divergence" and comparison.get("difference_display") is not None:
                points.append(
                    f"Diferença: {comparison['difference_display']}."
                    if pt
                    else f"Difference: {comparison['difference_display']}."
                )
            return {
                "points": points,
                "needs_selection": False,
                "missing": [],
                "escalate": result == "divergence",
                "escalation_reason": "fee_divergence" if result == "divergence" else None,
            }

        return ToolPlan([("simulate_pricing", args)], final=final_price)
    if topic == "enablement":
        scheme = (
            "visa"
            if re.search(r"visa", message, re.I)
            else "mastercard"
            if re.search(r"mastercard", message, re.I)
            else None
        )
        return ToolPlan(
            [("get_enablement_requests", {"scheme": scheme} if scheme else {})],
            final=lambda r: (
                failed(r)
                or {
                    "points": [
                        (
                            f"{item['scheme']}: {item['status']}, protocolo {item['protocol']}; "
                            f"disponibilidade no equipamento: {item['device_availability']['available']}."
                            if pt
                            else f"{item['scheme']}: {item['status']}, protocol {item['protocol']}; "
                            f"device availability: {item['device_availability']['available']}."
                        )
                        for item in _load(r, 0).get("requests", [])
                    ],
                    "needs_selection": False,
                    "missing": [],
                    "escalate": False,
                    "escalation_reason": None,
                }
            ),
        )
    if topic == "cancellation":
        return ToolPlan(
            [("get_sale_cancellation_context", {"period": "yesterday"})],
            final=lambda r: (
                failed(r)
                or {
                    "points": [
                        (
                            f"Status do cancelamento da venda: {item['status']}. Consulta sem execução de ação."
                            if pt
                            else f"Sale cancellation status: {item['status']}. This is a read-only lookup."
                        )
                        for item in _load(r, 0).get("cancellations", [])
                    ],
                    "needs_selection": False,
                    "missing": [],
                    "escalate": False,
                    "escalation_reason": None,
                }
            ),
        )
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


def _web(call: ScriptedCall) -> dict | Exception:
    """The scripted web search. A product the pages do not know ("Get XYZ", the `_knowledge` trigger below) has a
    third-party page about it; everything else keeps the exchange-rate answer the general web cases have always had."""
    text = call.spec.input
    if "unavailable" in text.lower():
        return LLMError("web search unavailable (scripted)")
    if "get xyz" in text.lower():
        english = guess_language(text) == "en"
        return {
            "text": "A third-party page says the Get XYZ accepts contactless (NFC) payments."
            if english
            else "Uma página pública de terceiros informa que a Get XYZ aceita pagamento por aproximação (NFC).",
            "citations": [{"url": "https://example.com/get-xyz", "title": "Third-party review of the Get XYZ"}],
        }
    return {
        "text": "1 EUR = R$ 5,57 (Example FX, 2026-10-26 10:00).",
        "citations": [{"url": "https://example.com/fx", "title": "Example FX"}],
    }


# What the scripted planner prefers when the `replan` prompt is asked (the rules disagree): a human, then the merchant's
# account, then the official pages, then the web, then a question.
REPLAN_PREFERENCE = ("escalate", "support", "knowledge", "web", "clarify")


def _replan(call: ScriptedCall) -> dict:
    ctx = call.spec.context
    choice = next((n for n in REPLAN_PREFERENCE if n in ctx["candidates"] and n in ctx["allowed"]), "finish")
    return {
        "next": choice,
        "review": "complete" if choice == "finish" else "incomplete",
        "reason": f"scripted planner: {choice}",
    }


def _personality(call: ScriptedCall) -> dict:
    c = call.spec.context["contributions"]
    if c.get("route") == "acknowledgement":
        key = "ack_resolved" if c.get("case_state_after_reply") == "resolved" else "ack"
        return {"answer": policy(key, call.spec.context["language"])}
    parts = []
    if (c.get("operator") or {}).get("text"):  # a human agent's reply is delivered as given
        parts.append(c["operator"]["text"])
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
        return _web(call)
    if agent == "replan":
        return _replan(call)
    if agent == "knowledge":
        return _knowledge(call)
    if agent == "customer_support":
        plan = _support(call)
        original = plan.final
        plan.final = lambda results: {"steps_given": [], "issue_verified_by_tool": False, **original(results)}
        return plan
    if agent == "escalation":
        english = call.spec.context.get("language") == "en"
        return {
            "summary": "Lojista pediu atendimento humano.",
            "pending_question": "Retornar ao lojista.",
            "draft_reply": "Our team reviewed your case and will follow up here."
            if english
            else "Nossa equipe analisou o seu caso e vai responder por aqui.",
        }
    if agent == "personality":
        return _personality(call)
    if agent == "judge":  # deterministic stand-in for the model judge; says nothing about real quality
        return {"answers_question": 4, "clarity_and_tone": 4, "honesty": 4, "comment": "Scripted judge."}
    raise AssertionError(f"unexpected agent {agent}")
