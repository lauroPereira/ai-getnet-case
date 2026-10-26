"""Public HTTP contract for `POST /messages`."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["answered", "needs_clarification", "handoff", "refused"]
Route = Literal[
    "knowledge", "support", "knowledge_and_support", "general_web", "clarify", "human_handoff", "out_of_scope"
]
ResolutionState = Literal["in_progress", "awaiting_customer", "resolved", "handoff"]

CHALLENGE_EXAMPLES = [
    "What's the difference between the Get Clássica and the Get Smart?",
    "What's the weather forecast in Porto Alegre tomorrow?",
    "When will the money from yesterday's sales be deposited?",
    "Do I need a bank account to receive my sales via Pix?",
    "My card machine won't connect to the internet, what should I do?",
    "How does receivables advance (antecipação) work with Getnet?",
    "What's the euro exchange rate today?",
    "My card machine is showing a transaction decline error.",
    "How many installments can I split a sale into with the crediário?",
    "Can I sell through WhatsApp using the Payment Link?",
]


class MessageRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"message": m, "user_id": "cliente1988"} for m in CHALLENGE_EXAMPLES]},
    )

    message: str = Field(min_length=1, max_length=2000, description="Merchant message, in Portuguese or English.")
    user_id: str = Field(
        pattern=r"^[A-Za-z0-9_\-.]{1,64}$",
        description="Synthetic merchant identifier for the demo scenario. It does not prove identity.",
    )
    conversation_id: str | None = Field(default=None, pattern=r"^conv_[A-Za-z0-9]{8,40}$")


class Source(BaseModel):
    type: Literal["official", "demo_procedure", "web", "tool"]
    title: str
    url: str | None = None
    observed_at: str | None = None


class Resolution(BaseModel):
    state: ResolutionState
    evidence: str | None = None


class Handoff(BaseModel):
    protocol: str
    simulated: bool = True
    reason: str


class MessageResponse(BaseModel):
    answer: str
    status: Status
    route: Route
    agents: list[str]
    language: Literal["pt", "en"]
    sources: list[Source] = Field(default_factory=list)
    request_id: str
    conversation_id: str
    resolution: Resolution
    handoff: Handoff | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorBody(BaseModel):
    error: ErrorDetail
