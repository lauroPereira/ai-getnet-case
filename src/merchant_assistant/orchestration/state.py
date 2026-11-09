"""Typed state shared by the graph nodes, and the structured contracts each agent must return."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from merchant_assistant.api.schemas import Route, Status

Topic = Literal[
    "receivables", "device", "authorization", "contract", "general", "pricing", "enablement", "cancellation"
]
Language = Literal["pt", "en"]
Safety = Literal["none", "unsafe", "sensitive", "injection"]
CaseSignal = Literal["none", "resolved", "still_failing", "thanks_only"]
Confirmation = Literal["yes", "no", "other"]


def _no_default_in_schema(schema: dict) -> None:
    """The model always answers the field (strict structured output); the default only serves decisions built in
    code and scripted models written before the field existed."""
    schema.pop("default", None)


class RouterDecision(BaseModel):
    route: Route
    language: Language
    topic: Topic | None = Field(description="Support topic when the route needs merchant data; otherwise null.")
    intents: list[str] = Field(description="Short labels of what the merchant wants.")
    safety: Safety
    clarification_question: str | None = Field(description="Only for route=clarify: one objective question.")
    case_signal: CaseSignal = Field(
        description="Merchant's reaction to the assistant's previous reply in this conversation: resolved, "
        "still_failing, thanks_only, or none."
    )
    confirmation: Confirmation = Field(  # router.v7 (task 94); validated in code by `router.enforce`
        default="other",
        description="Only when a sale cancellation waits for the merchant's answer: yes when the message only "
        "confirms it, no when it only refuses it; anything else, or no pending cancellation, is other.",
        json_schema_extra=_no_default_in_schema,
    )


class KnowledgeDraft(BaseModel):
    points: list[str] = Field(description="Factual statements answering the question, in the merchant's language.")
    used_passages: list[int] = Field(description="Numbers of the passages that support the points.")
    evidence_sufficient: bool
    missing: list[str] = Field(description="What the passages do not cover.")


class Citation(BaseModel):
    title: str
    url: str | None = None
    source_kind: Literal["public_official", "simulated_internal", "web"]
    chunk_id: str | None = None


class KnowledgeResult(BaseModel):
    mode: Literal["rag", "web", "procedure"]
    points: list[str]
    citations: list[Citation] = []
    evidence_sufficient: bool
    missing: list[str] = []
    procedure_id: str | None = None
    evidence_texts: list[str] = Field(default_factory=list, description="Passages/web text used by the output guard.")


class SupportDraft(BaseModel):
    points: list[str] = Field(description="What the merchant needs to know, based only on tool results.")
    needs_selection: bool = Field(description="True when the merchant must choose among several resources.")
    missing: list[str] = Field(description="Information still needed from the merchant.")
    escalate: bool = Field(description="True when a human must take over.")
    escalation_reason: str | None
    steps_given: list[str] = Field(
        description="Short labels of the troubleshooting steps suggested in this reply (empty if none)."
    )
    issue_verified_by_tool: bool = Field(
        description="True only when a tool result directly confirms the merchant's issue is solved."
    )


class SupportResult(SupportDraft):
    steps_given: list[str] = []
    issue_verified_by_tool: bool = False
    tools_used: list[str] = []
    tools_ok: list[str] = []  # the specialist tools that answered (no error)


class EscalationDraft(BaseModel):
    summary: str = Field(description="Two or three sentences for the human agent.")
    pending_question: str = Field(description="What the human agent must resolve.")
    draft_reply: str = Field(description="Reply the human agent may approve, in the merchant's language.")


class EscalationResult(BaseModel):
    case_id: str
    protocol: str
    reason: str
    summary: str
    pending_question: str
    created: bool
    draft_reply: str | None = None


class PersonalityOutput(BaseModel):
    answer: str


ReplanNext = Literal["finish", "knowledge", "web", "support", "escalate", "clarify"]


class ReplanDecision(BaseModel):
    """What the `replan` prompt returns when no rule settles the next step (task 69, spec v0.8.0 D2, D4)."""

    next: ReplanNext = Field(
        description="The next step: one specialist that has not run yet, or finish, escalate or clarify."
    )
    reason: str = Field(
        description="One short sentence saying why, for the trace. With finish and review=incomplete it is also "
        "what the reply says could not be confirmed, so state that missing fact."
    )
    review: Literal["complete", "incomplete"] = Field(
        description="complete only when the results collected so far answer the merchant's question."
    )


class GraphState(BaseModel):
    request_id: str
    conversation_id: str
    user_id: str
    customer_known: bool
    message: str
    history: list[dict] = []  # the short history (`ConversationStore.history()['recent']`)
    summary: str | None = None  # task 92 (D1): what left the short history; data for prompts, never evidence
    uncovered_history: list[dict] = []  # up to 12 messages outside the window that are not covered by the summary
    history_incomplete: bool = False  # older uncovered messages were omitted from the bounded prompt context
    facts: list[dict] = []  # task 92 (D2): the fact register of earlier turns, evidence for the output guard
    # The facts each prompt shows, by agent (`support`, `personality`): from messages older than its recent turns.
    prompt_facts: dict[str, list[dict]] = {}
    case: dict = {}
    prefix_cache: dict | None = None
    guard_findings: list[str] = []
    guard_blocked: bool = False
    decision: RouterDecision | None = None
    knowledge: KnowledgeResult | None = None
    prefix: dict = {}
    support: SupportResult | None = None
    escalation: EscalationResult | None = None
    policy: str | None = None
    status: Status | None = None
    draft_answer: str | None = None
    answer: str | None = None
    agents: list[str] = []
    errors: list[str] = []
    output_violations: list[str] = []
    case_next: dict = {}
    operator: dict | None = None  # set when an operator resumes the flow: action, text, operator_id
    plan: dict = {}  # replanning (task 69): `hops` taken away from the initial plan, `next` step, `gap` declared
    # task 94 (D5): the sale cancellation request waiting for an answer in this conversation when the turn started
    # (request_id, sale_date, amount, turns_waited), and what the code did with it in this turn (the request's view)
    cancellation: dict | None = None
    cancellation_event: dict | None = None
    # the conversation already had a cancellation request of this merchant (waiting or closed) when the
    # turn started
    cancellation_in_conversation: bool = False
