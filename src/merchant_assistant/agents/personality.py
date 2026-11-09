"""Personality: writes the final reply in a consistent voice from the agents' structured contributions.

It cannot change facts: the output guard checks amounts, dates and percentages against the request evidence and the
conversation's fact register (task 92); the rolling summary is never evidence.
"""

from __future__ import annotations

import json
import re
import unicodedata

from pydantic import ValidationError

from merchant_assistant.agents import cancellation
from merchant_assistant.agents.common import (
    LANGUAGE_NAME,
    format_history,
    history_coverage_instruction,
    policy,
    prompt,
)
from merchant_assistant.cases import Turn, next_state
from merchant_assistant.conversations import PROMPT_HISTORY
from merchant_assistant.data.clock import today
from merchant_assistant.guardrails.output import drop_unsupported_sentences, unsupported
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded, RunContext
from merchant_assistant.orchestration.state import GraphState, PersonalityOutput

RECOVERABLE = (LLMError, ValidationError, LimitExceeded, BudgetExceeded)

HANDOFF_LINE = {
    "pt": "Encaminhei seu caso para um atendente da nossa equipe, que vai responder por aqui. Protocolo: {protocol}.",
    "en": "I've handed your case to a human agent on our support team, who will reply here. Protocol: {protocol}.",
}
HISTORY_INCOMPLETE_NOTICE = {
    "pt": (
        "Parte do histórico anterior não está disponível no contexto desta resposta. Vou responder com o contexto "
        "disponível; se sua pergunta depender de um detalhe ausente, por favor, repita-o."
    ),
    "en": "Part of the earlier conversation is not available in this reply's context. I will answer with the context "
    "available; if your question depends on a missing detail, please repeat it.",
}


# a reply made only of thanks and offers of help ("Por nada! Fico à disposição se precisar de mais alguma
# ajuda.") does not answer a question. Each sentence is checked with accents folded; a sentence with a digit or with
# anything outside these courtesies is an answer.
_COURTESY = re.compile(
    r"\s*(?:(?:por nada|de nada|disponha|imagina|nao ha de que|eu que agradeco|obrigad[oa] (?:a|por) voce|"
    r"(?:fico|estou|sigo|continuo) (?:a )?(?:sua )?disposicao|(?:fico|estou) (?:por )?aqui|conte comigo|"
    r"(?:e )?so (?:me )?chamar|(?:se|caso) (?:precisar|tiver|quiser)|qualquer (?:coisa|duvida)|"
    r"(?:de|para|com) (?:mais )?(?:alguma|qualquer) (?:coisa|ajuda|duvida)|(?:mais )?(?:alguma|qualquer) "
    r"(?:coisa|ajuda|duvida)|ajudar|ajuda|"
    r"fico feliz em ajudar|feliz em ajudar|ate mais|ate logo|tenha um (?:otimo|bom) dia|bom dia|boa tarde|boa noite|"
    r"(?:quer|deseja|gostaria de) saber (?:mais )?(?:alguma|outra) coisa|posso ajudar (?:em|com) (?:mais )?"
    r"(?:alguma|outra) coisa|obrigad[oa] (?:a )?voce|estou aqui para ajudar|aqui para ajudar|"
    r"(?:you'?re|you are) welcome|no problem|my pleasure|glad to help|happy to help|any ?time|if you need|"
    r"(?:just )?let me know|i'?m here|anything else|more help|further help|feel free to ask)[\s,!.]*)+"
)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold().replace("\u2019", "'"))
    return "".join(c for c in text if not unicodedata.combining(c))


def courtesy_only(text: str) -> bool:
    """True when every sentence of `text` is only thanks or an offer of further help."""
    sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if s.strip()]
    return bool(sentences) and all(
        not re.search(r"\d", s) and _COURTESY.fullmatch(_fold(s).rstrip(".!? ")) for s in sentences
    )


def final_status(state: GraphState) -> str:
    return state.status or "answered"


def operator_text(state: GraphState) -> str | None:
    """The human agent's reply (approved draft or own text); None for `reject` or outside a resumed flow."""
    if state.operator and state.operator.get("action") in ("approve", "reply"):
        return (state.operator.get("text") or "").strip() or None
    return None


def contributions(state: GraphState, language: str) -> dict:
    data: dict = {"status": final_status(state), "language": language}
    if state.operator:  # resumed by a human agent: only the operator's reply or the re-run support speaks
        data["operator"] = {"action": state.operator.get("action"), "from_operator": True}
        if text := operator_text(state):
            data["operator"]["text"] = text
        if state.support and state.operator.get("action") == "reject":
            data["support"] = {
                "points": state.support.points,
                "missing": state.support.missing,
                "needs_selection": state.support.needs_selection,
            }
        return data
    if state.policy:
        data["policy_text"] = state.policy
    if state.knowledge:
        k = state.knowledge
        data["knowledge"] = {
            "mode": k.mode,
            "points": k.points,
            "evidence_sufficient": k.evidence_sufficient,
            "missing": k.missing,
            "sources": [c.title for c in k.citations],
        }
        if not k.evidence_sufficient and not k.points:
            data["knowledge"]["note"] = (
                policy("no_evidence", language) if k.mode != "web" else policy("unavailable", language)
            )
    if state.support:
        data["support"] = {
            "points": state.support.points,
            "missing": state.support.missing,
            "needs_selection": state.support.needs_selection,
        }
    if state.escalation:
        data["handoff"] = {
            "protocol": state.escalation.protocol,
            "message": HANDOFF_LINE[language].format(protocol=state.escalation.protocol),
        }
    if gap := state.plan.get("gap"):  # the replanner ran out of ways to confirm this: say so, without guessing
        data["unconfirmed"] = gap
    if sale_cancellation := cancellation.view(state.cancellation_event, language):  # task 94
        data["cancellation"] = sale_cancellation
    return data


def deterministic_answer(state: GraphState, language: str, case_state: str | None = None) -> str:
    """Fallback used when the model is unavailable or its text fails the output guard."""
    if state.operator:
        text = operator_text(state)
        points = state.support.points if state.support and not text else []
        return text or "\n".join(points) or policy("unavailable", language)
    if state.decision and state.decision.route == "acknowledgement":
        return policy("ack_resolved" if case_state == "resolved" else "ack", language)
    parts: list[str] = []
    if state.policy:
        parts.append(state.policy)
    already_says_missing = False
    if state.knowledge and state.knowledge.mode != "procedure":  # procedure points are guidance for the support agent
        parts += state.knowledge.points or (
            [policy("no_evidence", language)] if state.knowledge.mode != "web" else [policy("unavailable", language)]
        )
        already_says_missing = not state.knowledge.points
    if state.support:
        parts += state.support.points
    if state.plan.get("gap") and not already_says_missing:  # the replanner declared something it could not confirm
        parts.append(policy("unconfirmed", language))
    if state.escalation:
        parts.append(HANDOFF_LINE[language].format(protocol=state.escalation.protocol))
    if sale_cancellation := cancellation.view(state.cancellation_event, language):  # task 94: what happened, in code
        parts.append(sale_cancellation["message"])
    return "\n".join(p for p in parts if p) or policy("unavailable", language)


def evidence(state: GraphState, ctx: RunContext) -> list[str]:
    texts = [state.message, state.policy or ""]
    texts += [json.dumps(o.data, ensure_ascii=False, default=str) for o in ctx.outcomes if o.ok]
    if state.knowledge:
        texts += state.knowledge.evidence_texts
    if state.escalation:
        texts.append(state.escalation.protocol)
    if text := operator_text(state):  # the human agent's text is valid evidence for the output guard
        texts.append(text)
    texts += [fact["value"] for fact in state.facts]  # task 92 (D2): the register of earlier turns; never the summary
    if state.cancellation_event:  # task 94: the request as the code read or changed it in this turn
        texts.append(json.dumps(state.cancellation_event, ensure_ascii=False, default=str))
    return texts


def _with_cancellation_line(draft: str, sale_cancellation: dict | None) -> str:
    """The fixed line of the cancellation (task 94): always, while the request is not confirmed (it says nothing was
    cancelled and, while it waits, asks for the explicit yes); for a confirmed one, when the reply misses the
    protocol."""
    if not sale_cancellation:
        return draft
    if sale_cancellation["status"] == "confirmed":
        missing = sale_cancellation["protocol"] not in draft
    else:  # the model's curly quotes or line breaks do not make the same line a different one
        missing = not cancellation.contains_line(draft, sale_cancellation["message"])
    return f"{draft}\n{sale_cancellation['message']}" if missing else draft


def run(state: GraphState, ctx: RunContext) -> dict:
    language = state.decision.language if state.decision else "en"
    state = state.model_copy(update={"cancellation_event": cancellation.turn_event(state, ctx)})
    status = final_status(state)
    agents = [*state.agents, "personality"]
    signal = state.decision.case_signal if state.decision else "none"
    tool_verified = bool(state.support and state.support.issue_verified_by_tool)
    case_state, evidence = next_state(
        state.case.get("state", "in_progress"),
        state.case.get("evidence"),
        Turn(status, signal, tool_verified, via_operator=state.operator is not None),
    )
    case_next = {"state": case_state, "evidence": evidence}
    data = contributions(state, language)
    # the status the reply will give, from code; only in a turn about a cancellation
    support_text = "\n".join(state.support.points) if state.support else ""  # the Support model's text
    if cancellation.about_cancellation(state, support_text) and (block := cancellation.status_block(ctx, language)):
        data["cancellation_status"] = {"message": block, "note": "The system writes this status itself."}
    data |= {
        "route": state.decision.route if state.decision else None,
        "case_signal": signal,
        "case_state_after_reply": case_state,
    }
    p = prompt(ctx, "personality")
    ctx.step_notes["prompt"] = p.ref
    instructions = p.render(
        language_name=LANGUAGE_NAME[language],
        status=status,
        today=today(ctx.clock).isoformat(),
        contributions=json.dumps(data, ensure_ascii=False, indent=1),
        history=format_history(
            state.history,
            limit=PROMPT_HISTORY["personality"],
            summary=state.summary,
            facts=state.prompt_facts.get("personality"),
            uncovered=state.uncovered_history,
            incomplete=state.history_incomplete,
        ),
        message=state.message,  # personality.v7: the reply answers this message
        case_state=case_state,
    ) + history_coverage_instruction(state.history_incomplete)
    spec = CallSpec(
        agent="personality",
        instructions=instructions,
        input="Write the final reply to the merchant.",
        effort="none",
        max_output_tokens=600,
        context={"contributions": data, "status": status, "language": language, "message": state.message},
    )
    try:
        draft = ctx.llm_for("personality").parse(spec, PersonalityOutput, ctx).value.answer.strip()
        source = "personality"
    except RECOVERABLE as exc:
        ctx.step_notes["error"] = str(exc)
        draft, source = deterministic_answer(state, language, case_state), "fallback"
    if state.escalation and not state.operator and state.escalation.protocol not in draft:
        draft = f"{draft}\n{HANDOFF_LINE[language].format(protocol=state.escalation.protocol)}"
    draft = _with_cancellation_line(draft, data.get("cancellation"))  # never present for an operator's turn
    ctx.step_notes.update(source=source, case_state=case_state, evidence=evidence)
    return {
        "draft_answer": draft,
        "status": status,
        "agents": agents,
        "case_next": case_next,
        "cancellation_event": state.cancellation_event,
    }


def run_output_guard(state: GraphState, ctx: RunContext) -> dict:
    language = state.decision.language if state.decision else "en"
    answer = state.draft_answer or deterministic_answer(state, language, state.case_next.get("state"))
    ev = evidence(state, ctx)
    ref = today(ctx.clock)
    violations = unsupported(answer, ev, ref)
    ctx.step_notes["violations"] = [f"{v.kind}:{v.value}" for v in violations]
    route = state.decision.route if state.decision else None
    if not violations and route != "acknowledgement" and "?" in state.message and courtesy_only(answer):
        # a question answered only with thanks; the specialists' contributions answer it instead
        fallback = deterministic_answer(state, language, state.case_next.get("state"))
        if not courtesy_only(fallback):
            ctx.step_notes["courtesy_only"] = True
            answer = fallback
    if violations:
        fallback = deterministic_answer(state, language, state.case_next.get("state"))
        if not unsupported(fallback, ev, ref):
            answer = fallback
        else:
            answer = drop_unsupported_sentences(answer, ev, ref) or policy("unavailable", language)
    if operator_text(state) is not None:
        # A human agent's text (a reply or an approved draft) is never changed by a cancellation rule
        return {"answer": answer, "output_violations": [f"{v.kind}:{v.value}" for v in violations]}
    sale_cancellation = cancellation.view(state.cancellation_event, language)
    handoff = (  # a case the turn opened is still announced when the reply is swapped for the fixed line
        f"\n{HANDOFF_LINE[language].format(protocol=state.escalation.protocol)}"
        if state.escalation and not state.operator
        else ""
    )
    # also when an operator's "reject" reran the Support; a sales question that looked the status up
    # follows the normal flow unless the model's text (its draft or the Support's points) mentions a cancellation
    model_text = "\n".join([state.draft_answer or "", *(state.support.points if state.support else [])])
    about = cancellation.about_cancellation(state, model_text)
    asked = cancellation.asked_about_cancellation(state)  # the current question, not the conversation
    official = bool(  # the Knowledge answered (a question of procedure): never replaced by the question for the sale
        (state.decision and state.decision.route == "knowledge") or (state.knowledge and state.knowledge.points)
    )
    block = cancellation.status_block(ctx, language) if about else None
    requested_now = bool(  # this turn's request_sale_cancellation left a request waiting for the yes
        sale_cancellation
        and sale_cancellation["status"] == "pending_confirmation"
        and any(o.ok and o.name == "request_sale_cancellation" for o in ctx.outcomes)
    )
    if sale_cancellation and sale_cancellation["replaces_reply"]:
        # a request the tool refused (any sale the reply describes may not be the one asked for) or a bare
        # yes or no to a request already closed: the fixed line is the whole reply
        ctx.step_notes["cancellation_fixed_reply"] = "closed" if sale_cancellation["status"] != "not_requested" else (
            "not_requested"
        )
        answer = sale_cancellation["message"] + handoff
    elif block is not None or requested_now:
        # the turn looked up a cancellation status; the status comes from the lookups' data, never from the
        # model. the turn asked for a cancellation that now waits; the request is told by its fixed line
        # alone. No text of the model is used: the official points, the block of the other sales looked up, the
        # request's line, what Support still needs, the handoff and, when Support also answered something else, a
        # fixed sentence asking for that question separately
        ctx.step_notes["cancellation_request_from_code" if requested_now else "cancellation_status_from_code"] = True
        parts = list(state.knowledge.points) if state.knowledge and state.knowledge.mode != "procedure" else []
        parts += [block, sale_cancellation["message"] if requested_now else None]
        if state.support:
            parts += state.support.missing
            # a successful tool besides the cancellation ones, and points: Support answered something else (a tool
            # that only helped to find the sale cannot be told apart and also brings the sentence)
            if state.support.points and set(state.support.tools_ok) - cancellation.STATUS_TOOLS:
                parts.append(cancellation.STATUS_LINES["rest"]["pt" if language == "pt" else "en"])
        answer = "\n".join(p for p in parts if p) + handoff
    elif asked and sale_cancellation is None and not official and cancellation.states_sale_status(answer):
        # the current question is about a cancellation (not only a request earlier in the conversation), the
        # Support looked nothing up (no block), no request moved and no official answer was given (a question of
        # procedure): the state of a specific sale the model states is not checked; the reply asks which sale it is
        ctx.step_notes["cancellation_status_unchecked"] = True
        answer = cancellation.STATUS_LINES["ask_sale"]["pt" if language == "pt" else "en"] + handoff
    elif sale_cancellation and not sale_cancellation["executed"]:
        # task 94: a cancellation not confirmed is never described as done or promised; after a no or a refusal the
        # reply is only about it, and the wider word list is an extra defense there
        wide = sale_cancellation["status"] in ("declined", "refused")
        claims = cancellation.claims_status if wide else cancellation.promises_execution
        if claims(answer):
            ctx.step_notes["cancellation_promise"] = True
            fallback = deterministic_answer(state, language, state.case_next.get("state"))
            answer = fallback if not claims(fallback) else sale_cancellation["message"] + handoff
    answer = _with_cancellation_line(answer, sale_cancellation)  # the fixed line survives every swap above
    if state.history_incomplete:
        answer = f"{HISTORY_INCOMPLETE_NOTICE[language]}\n{answer}"
    return {"answer": answer, "output_violations": [f"{v.kind}:{v.value}" for v in violations]}
