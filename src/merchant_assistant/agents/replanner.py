"""Replanner (task 69; spec v0.8.0 D1 to D7, ADR 0019): after `knowledge`, `web` and `support`, a step observes what
came back and decides what happens next: finish, another specialist, the web, a human, or a question to the merchant.

Named rules settle the clear cases without a model call. `replan.v1` decides only when no rule applies or two rules
disagree about the next step. Whatever decides, the guards come last: a specialist runs at most once per request (D5),
decisions that leave the Router's initial plan are limited to `MAX_PLAN_HOPS` (D6), and the request's own limits of
calls, time and cost still hold. The decision, its reason, its origin (`rule:<name>` or `model`) and what was observed
go to the trace (D7). Nothing here touches the review graph that resumes a handed-off case (D3)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from merchant_assistant.agents.common import LANGUAGE_NAME, guess_language, policy, prompt
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded, RunContext
from merchant_assistant.orchestration.state import GraphState, ReplanDecision
from merchant_assistant.tools.registry import AGENT_TOOLS

RECOVERABLE = (LLMError, ValidationError, LimitExceeded, BudgetExceeded)

SPECIALISTS = ("knowledge", "web", "support")
INITIAL_PLAN = {  # what the Router's route asks for, in order (the `knowledge` node of `general_web` is the web search)
    "knowledge": ("knowledge",),
    "general_web": ("web",),
    "support": ("support",),
    "knowledge_and_support": ("knowledge", "support"),
}
OUTAGE = ("UNAVAILABLE", "TIMEOUT")  # tool failures that mean "the service is down", not "there is nothing"
MODEL_OUTPUT_TOKENS = 80

# The merchant asks about their own plan, contract, account or rates: product knowledge alone cannot answer it.
ACCOUNT_MESSAGE = re.compile(
    r"\b(?:meu|minha|meus|minhas)\s+(?:plano|contrato|conta|taxas?|tarifas?|limite|cadastro)\b"
    r"|\bmy\s+(?:plan|contract|account|rates?|fees?|limit|registration)\b",
    re.IGNORECASE,
)
# What Knowledge says it could not cover when the gap is the merchant's own data ("the merchant's contracted plan").
ACCOUNT_GAP = re.compile(
    r"\b(?:merchant'?s\s+(?:\w+\s+){0,2}(?:plan|contract|account|rates?|fees?|data)"
    r"|your\s+(?:\w+\s+){0,2}(?:plan|contract|account|rates?|fees?)|account\s+data"
    r"|(?:plano|contrato|conta|taxas?)\s+(?:\w+\s+){0,2}(?:do|de)\s+lojista"
    r"|(?:seu|sua|seus|suas)\s+(?:\w+\s+){0,2}(?:plano|contrato|conta|taxas?)|dados\s+da\s+conta)\b",
    re.IGNORECASE,
)
# The merchant also asks "how do I ...": a procedure, which is Knowledge's job, not a tool's.
HOW_TO = re.compile(
    r"\bcomo\s+(?:eu\s+)?(?:fa[çc]o|posso|fazer|devo)\b|\bo\s+que\s+(?:eu\s+)?fa[çc]o\b|\bpasso a passo\b"
    r"|\bhow\s+(?:do|can|should)\s+i\b|\bwhat\s+(?:do|should)\s+i\s+do\b|\bhow\s+to\b|\bsteps?\s+to\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Observed:
    """What the replanner sees after a specialist (D4 and D7): the part of the state that matters for the decision."""

    just_ran: str  # knowledge | web | support | "" (nothing identifiable ran)
    ran: tuple[str, ...]
    route: str
    hops: int
    pending: tuple[str, ...]  # specialists of the initial plan that have not run yet
    customer_known: bool
    knowledge_mode: str | None = None
    evidence_sufficient: bool | None = None  # None: Knowledge did not run
    knowledge_unavailable: bool = False
    knowledge_gap: tuple[str, ...] = ()
    support_points: bool = False
    support_missing: tuple[str, ...] = ()
    support_needs_selection: bool = False
    support_escalate: bool = False
    failed_tools: tuple[str, ...] = ()
    account_dependent: bool = False
    how_to: bool = False
    controlled_answer: bool = False  # a node failed and the state already carries a controlled answer

    @property
    def wants_account(self) -> bool:
        """The question depends on this merchant's account and Support has not looked yet."""
        return self.account_dependent and self.customer_known and "support" not in self.ran

    @property
    def wants_procedure(self) -> bool:
        """Support answered the account part; the "how do I" part still needs the official procedure."""
        return self.how_to and "support" in self.ran and "knowledge" not in self.ran and "web" not in self.ran

    @property
    def done(self) -> tuple[str, ...]:
        """Specialists that cannot run again (D5). On the `general_web` route the `knowledge` node is the web search and
        has no other mode there, so a second `knowledge` would repeat the search and overwrite its result."""
        return (*self.ran, "knowledge") if self.route == "general_web" else self.ran

    def as_dict(self) -> dict:
        return {
            key: list(value) if isinstance(value, tuple) else value for key, value in self.__dict__.items()
        }


@dataclass(frozen=True)
class Match:
    rule: str
    next: str
    review: str  # complete | incomplete
    reason: str
    gap: tuple[str, ...] = ()
    planned: bool = False  # the Router's own plan going on, not a deviation from it


@dataclass
class Chosen:
    next: str
    review: str
    reason: str
    origin: str  # rule:<name> | model
    gap: tuple[str, ...] = ()
    planned: bool = False
    notes: dict = field(default_factory=dict)


# --- observation -----------------------------------------------------------------------------------------------------


def observe(state: GraphState, ctx: RunContext) -> Observed:
    route = state.decision.route if state.decision else "knowledge"
    ran = tuple(state.plan.get("ran", []))
    k, s = state.knowledge, state.support
    specialist_tools = set(AGENT_TOOLS["customer_support"])
    last_by_tool = {o.name: o for o in ctx.outcomes if o.name in specialist_tools}
    failed = tuple(
        f"{name}:{o.error['code']}"
        for name, o in last_by_tool.items()
        if not o.ok and (o.error or {}).get("code") in OUTAGE
    )
    knowledge_gap = tuple(k.missing) if k else ()
    return Observed(
        just_ran=state.plan.get("last", ""),
        ran=ran,
        route=route,
        hops=int(state.plan.get("hops", 0)),
        pending=tuple(step for step in INITIAL_PLAN.get(route, ()) if step not in ran),
        customer_known=state.customer_known,
        knowledge_mode=k.mode if k else None,
        evidence_sufficient=k.evidence_sufficient if k else None,
        knowledge_unavailable=bool(k and "knowledge_unavailable" in k.missing),
        knowledge_gap=knowledge_gap,
        support_points=bool(s and s.points),
        support_missing=tuple(s.missing) if s else (),
        support_needs_selection=bool(s and s.needs_selection),
        support_escalate=bool(s and s.escalate),
        failed_tools=failed,
        account_dependent=bool(
            ACCOUNT_MESSAGE.search(state.message) or any(ACCOUNT_GAP.search(m) for m in knowledge_gap)
        ),
        how_to=bool(HOW_TO.search(state.message)),
        controlled_answer=bool(state.policy),
    )


# --- rules (D4): pure functions of the observation, each with a name -----------------------------------------------


def _specialist_failed(o: Observed) -> Match | None:
    if o.controlled_answer and not o.pending:
        return Match(
            "specialist_failed", "finish", "incomplete", "a specialist failed; the controlled answer stands",
            ("a specialist could not complete its check",),
        )
    return None


def _plan_pending(o: Observed) -> Match | None:
    if o.pending:
        step = o.pending[0]
        return Match("plan_pending", step, "incomplete", f"the Router's plan still has {step}", planned=True)
    return None


def _tool_failure_no_alternative(o: Observed) -> Match | None:
    if o.just_ran == "support" and o.failed_tools and not o.support_points:
        return Match(
            "tool_failure_no_alternative", "escalate", "incomplete",
            f"essential tool unavailable ({', '.join(o.failed_tools)}) and there is no other source",
        )
    return None


def _support_asked_for_human(o: Observed) -> Match | None:
    if o.just_ran == "support" and o.support_escalate:
        return Match("support_asked_for_human", "escalate", "incomplete", "support asked for a human to take over")
    return None


def _selection_pending(o: Observed) -> Match | None:
    if o.just_ran == "support" and o.support_needs_selection:
        return Match("selection_pending", "clarify", "incomplete", "the merchant must choose among several options")
    return None


def _account_dependent_question(o: Observed) -> Match | None:
    if o.just_ran in ("knowledge", "web") and not o.pending and o.wants_account:
        return Match(
            "account_dependent_question", "support", "incomplete",
            "the answer depends on this merchant's own plan or account data",
        )
    return None


def _procedure_gap(o: Observed) -> Match | None:
    if (
        o.just_ran == "support"
        and not o.pending
        and o.wants_procedure
        and not (o.support_escalate or o.support_needs_selection or o.failed_tools)
    ):
        return Match(
            "procedure_gap", "knowledge", "incomplete",
            "support covered the account part; the how-to part needs the official procedure",
        )
    return None


def _evidence_insufficient_web(o: Observed) -> Match | None:
    if (
        o.just_ran == "knowledge"
        and o.knowledge_mode == "rag"
        and o.evidence_sufficient is False
        and not o.knowledge_unavailable
        and "web" not in o.ran
        and not o.pending
    ):
        return Match(
            "evidence_insufficient_web", "web", "incomplete", "the official pages do not cover it; try the web"
        )
    return None


def _support_clean(o: Observed) -> bool:
    return (
        "support" not in o.ran
        or (
            o.support_points
            and not (o.support_missing or o.support_needs_selection or o.support_escalate or o.failed_tools)
        )
    )


def _complete(o: Observed) -> Match | None:
    # `evidence_sufficient` is Knowledge's own verdict that the passages answer the question; what it lists as `missing`
    # then is extra detail the reply states, not a reason to plan again (the account-dependent case has its own rule).
    if (
        not o.pending
        and not o.controlled_answer
        and o.evidence_sufficient is not False
        and _support_clean(o)
        and not o.wants_account
        and not o.wants_procedure
        and o.just_ran
    ):
        return Match("complete", "finish", "complete", "the results answer the question")
    return None


def _gap_declared(o: Observed) -> Match | None:
    """Something is missing and no specialist is left that could add it: finish and say what is unconfirmed."""
    if o.pending or o.controlled_answer or o.wants_account or o.wants_procedure or not o.just_ran:
        return None
    if o.support_escalate or o.support_needs_selection or (o.failed_tools and not o.support_points):
        return None  # the escalation and clarification rules own these
    gap: list[str] = []
    if o.evidence_sufficient is False:
        exhausted = o.knowledge_unavailable or o.knowledge_mode in ("web", "procedure") or "web" in o.ran
        if not exhausted:
            return None  # the official pages were not enough and the web was not tried: not settled by this rule
        gap += list(o.knowledge_gap) or ["information from reliable sources"]
    if "support" in o.ran:
        if o.support_points and o.support_missing:
            gap += list(o.support_missing)
        elif not o.support_points:
            gap.append("data from the merchant's account")
        if o.failed_tools:
            gap.append("part of the account data was unavailable")
    if not gap:
        return None
    return Match(
        "gap_declared", "finish", "incomplete", "nothing left to try; the answer states what could not be confirmed",
        tuple(gap),
    )


RULES = (
    _specialist_failed,
    _plan_pending,
    _tool_failure_no_alternative,
    _support_asked_for_human,
    _selection_pending,
    _account_dependent_question,
    _procedure_gap,
    _evidence_insufficient_web,
    _complete,
    _gap_declared,
)


def apply_rules(o: Observed) -> list[Match]:
    """Every rule that applies, in rule order. One distinct `next` is a rule decision; none, or two that disagree,
    goes to `replan.v1`."""
    return [match for rule in RULES if (match := rule(o)) is not None]


# --- the model, only for the ambiguity -------------------------------------------------------------------------------


def allowed_next(o: Observed) -> list[str]:
    """finish, escalate and clarify always; a specialist only if it has not run (D5), and support only for a known
    merchant."""
    options = [s for s in SPECIALISTS if s not in o.done and (s != "support" or o.customer_known)]
    return [*options, "escalate", "clarify", "finish"]


def _ask_model(state: GraphState, ctx: RunContext, o: Observed, matches: list[Match]) -> Chosen:
    language = state.decision.language if state.decision else guess_language(state.message)
    candidates = sorted({m.next for m in matches})
    allowed = allowed_next(o)
    p = prompt(ctx, "replan")
    ctx.step_notes["prompt"] = p.ref
    observed = o.as_dict()
    spec = CallSpec(
        agent="replan",
        instructions=p.render(
            language_name=LANGUAGE_NAME[language],
            observed=_pretty(observed),
            allowed=", ".join(allowed),
            candidates=", ".join(candidates) or "none",
            message=state.message,
        ),
        input="Decide the next step.",
        effort="none",
        max_output_tokens=MODEL_OUTPUT_TOKENS,
        context={"observed": observed, "allowed": allowed, "candidates": candidates, "message": state.message},
    )
    try:
        decision = ctx.llm_for("replan").parse(spec, ReplanDecision, ctx).value
    except RECOVERABLE as exc:  # the answer must not depend on the planner: say what is unconfirmed and stop
        ctx.step_notes["error"] = str(exc)
        return Chosen(
            "finish", "incomplete", "the planner was unavailable; finishing with what was collected",
            "rule:planner_unavailable", ("the check could not be completed",),
        )
    reason = decision.reason.strip()[:300]
    # concluding with an incomplete review is not a clean finish: the reason is what could not be confirmed (as in the
    # rules, so the Personality says it plainly)
    gap = (reason,) if decision.next == "finish" and decision.review == "incomplete" and reason else ()
    return Chosen(decision.next, decision.review, reason, "model", gap, notes={"candidates": candidates})


def _pretty(observed: dict) -> str:
    return json.dumps(observed, ensure_ascii=False, indent=1)


# --- guards (D5, D6, request limits) ------------------------------------------------------------------------


def _within_limits(ctx: RunContext) -> bool:
    """One more specialist and the final reply must still fit the request's calls, time and cost."""
    s = ctx.settings
    return (
        ctx.model_calls + 2 <= s.max_model_calls
        and ctx.remaining_seconds() > 0
        and ctx.cost_usd < s.max_request_cost_usd
    )


def _guard(chosen: Chosen, o: Observed, ctx: RunContext) -> Chosen:
    """Last word, for rules and model alike. A refusal becomes `finish` with the gap declared."""
    refusal = None
    if chosen.next in SPECIALISTS and chosen.next in o.done:
        refusal = ("no_repeat", f"{chosen.next} already ran in this request")
    elif chosen.next in SPECIALISTS and not chosen.planned:
        if chosen.next == "support" and not o.customer_known:
            refusal = ("unknown_merchant", "there is no account to look up")
        elif o.hops >= ctx.settings.max_plan_hops:
            refusal = ("hop_budget", f"the budget of {ctx.settings.max_plan_hops} plan changes is used")
        elif not _within_limits(ctx):
            refusal = ("request_limits", "the request's calls, time or cost leave no room for another specialist")
    if refusal is None:
        return chosen
    name, why = refusal
    return Chosen(
        "finish", "incomplete", f"{why}; finishing with what was collected", f"rule:{name}",
        gap=(*chosen.gap, "information that another check could have added"),
        notes={"refused": chosen.next, "refused_origin": chosen.origin},
    )


# --- the node -----------------------------------------------------------------------------------------------


def run(state: GraphState, ctx: RunContext) -> dict:
    o = observe(state, ctx)
    matches = apply_rules(o)
    if not o.just_ran and not o.controlled_answer:
        chosen = Chosen("finish", "incomplete", "no specialist result to review", "rule:nothing_to_review")
    elif len({m.next for m in matches}) == 1:
        m = matches[0]
        chosen = Chosen(m.next, m.review, m.reason, f"rule:{m.rule}", m.gap, m.planned)
    else:
        chosen = _ask_model(state, ctx, o, matches)
    chosen = _guard(chosen, o, ctx)

    leaves_plan = (chosen.next in SPECIALISTS and not chosen.planned) or chosen.next == "escalate"
    hops = o.hops + (1 if leaves_plan else 0)
    plan = {**state.plan, "next": chosen.next, "hops": hops}
    if chosen.gap and chosen.next in ("finish", "clarify"):
        plan["gap"] = [*state.plan.get("gap", []), *chosen.gap]
    ctx.step_notes.update(
        next=chosen.next, reason=chosen.reason, review=chosen.review, hops=hops, origin=chosen.origin,
        observed=o.as_dict(), **chosen.notes,
    )
    update: dict = {"plan": plan}
    language = state.decision.language if state.decision else guess_language(state.message)
    if chosen.next == "clarify":
        update["status"] = "needs_clarification"
        if not state.policy and not (state.support and (state.support.needs_selection or state.support.missing)):
            update["policy"] = policy("clarify", language)
    elif chosen.next == "escalate" and o.failed_tools and state.support and not state.support.escalate:
        # the reason the Escalation agent records is the tool failure, not a generic "needs a human"
        update["support"] = state.support.model_copy(
            update={"escalate": True, "escalation_reason": f"tool_error:{o.failed_tools[0].split(':')[1]}"}
        )
    return update
