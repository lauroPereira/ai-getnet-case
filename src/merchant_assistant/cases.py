"""Case state machine. A reply never closes a case by itself: resolution needs identified evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CaseState = Literal["in_progress", "awaiting_customer", "resolved", "handoff"]
Evidence = Literal["customer_confirmed", "tool_verified"]

ALLOWED: dict[str, set[str]] = {
    "in_progress": {"in_progress", "awaiting_customer", "resolved", "handoff"},
    "awaiting_customer": {"in_progress", "awaiting_customer", "resolved", "handoff"},
    "resolved": {"resolved", "in_progress", "awaiting_customer", "handoff"},  # a new issue reopens the case
    "handoff": {"handoff"},  # stays with the human team
}


class InvalidTransition(Exception):
    pass


@dataclass(frozen=True)
class Turn:
    status: str  # answered | needs_clarification | handoff | refused
    case_signal: str  # none | resolved | still_failing | thanks_only
    tool_verified: bool = False
    via_operator: bool = False  # the reply comes from a human agent's action (approve, reply or reject)


def transition(current: str, new: str) -> str:
    if new not in ALLOWED.get(current, set()):
        raise InvalidTransition(f"{current} -> {new}")
    return new


def next_state(current: str, previous_evidence: str | None, turn: Turn) -> tuple[str, str | None]:
    """Returns (state, evidence) after a turn. Only an operator's action takes a case out of `handoff` (D14): it goes
    to `resolved` with tool evidence, otherwise to `awaiting_customer`, and never back to `handoff`."""
    if turn.via_operator:
        if turn.tool_verified:
            return "resolved", "tool_verified"
        return "awaiting_customer", None
    if current == "handoff" or turn.status == "handoff":
        return transition(current, "handoff"), previous_evidence
    if turn.case_signal == "resolved" and current in ("in_progress", "awaiting_customer"):
        return transition(current, "resolved"), "customer_confirmed"
    if turn.tool_verified:
        return transition(current, "resolved"), "tool_verified"
    if turn.case_signal == "thanks_only":  # gratitude alone neither resolves nor reopens
        return current, previous_evidence
    return transition(current, "awaiting_customer"), None
