"""Typed state shared by the graph nodes, and the structured contracts each agent must return."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from merchant_assistant.api.schemas import Route, Status

Topic = Literal["receivables", "device", "authorization", "contract", "general"]
Language = Literal["pt", "en"]
Safety = Literal["none", "unsafe", "sensitive", "injection"]
CaseSignal = Literal["none", "resolved", "still_failing", "thanks_only"]


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


class EscalationDraft(BaseModel):
    summary: str = Field(description="Two or three sentences for the human agent.")
    pending_question: str = Field(description="What the human agent must resolve.")


class EscalationResult(BaseModel):
    case_id: str
    protocol: str
    reason: str
    summary: str
    pending_question: str
    created: bool


class PersonalityOutput(BaseModel):
    answer: str


class GraphState(BaseModel):
    request_id: str
    conversation_id: str
    user_id: str
    customer_known: bool
    message: str
    history: list[dict] = []
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
