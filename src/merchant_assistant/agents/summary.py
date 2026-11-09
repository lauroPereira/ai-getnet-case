"""Rolling summary (task 92, spec v0.12.0 D1): what left the short history of a long conversation, in one block.

`summary.v1` (minimal effort, at most 200 tokens) folds the turns that left the window into the previous summary. It
runs only when a block of 3 turns (6 messages) out of the window is not covered by the stored summary yet (D1, amended;
the newest 12 uncovered messages stay in recent context and are also passed to the reply-writing agents), after the
input guard lets the message through and under its own allowance of one call (outside `max_model_calls`, inside the
request's cost limit and the budget ledger). Older uncovered messages stay in the conversation store and are folded
in by later calls; while they exceed the context block, the agents and the reply disclose that history is incomplete.
The result is stored with the id of the last message it covers: one call per advance. The text is masked and reaches the
Router, Support and Personality as a data block; it is never evidence for the output guard (D2).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from merchant_assistant.agents.common import prompt
from merchant_assistant.conversations import ConversationStore, estimate_tokens
from merchant_assistant.guardrails.input import mask_sensitive
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import LimitExceeded, RunContext

SUMMARY_MAX_TOKENS = 200
RECOVERABLE = (LLMError, ValidationError, LimitExceeded, BudgetExceeded)


class SummaryOutput(BaseModel):
    summary: str = Field(description="The updated summary of the conversation, at most 120 words.")


def clip(text: str, max_tokens: int = SUMMARY_MAX_TOKENS) -> str:
    """At most `max_tokens` by the conversation store's estimate, cut at a word boundary."""
    if estimate_tokens(text) <= max_tokens:
        return text
    cut = text[: max_tokens * 4 - 1]
    return (cut.rsplit(" ", 1)[0] if " " in cut else cut).rstrip(" ,;:") + "…"


def refresh(store: ConversationStore, conversation_id: str, ctx: RunContext) -> str | None:
    """The summary this turn uses: the stored one, advanced first when the window moved past it. A failure keeps the
    stored summary and its id, so the next turn tries again; the reply never depends on it."""
    backlog = store.summary_backlog(conversation_id)
    if backlog is None:
        return store.summary(conversation_id)
    previous, turns, until = backlog
    step, t0 = ctx.trace.start("summary")
    p = prompt(ctx, "summary")
    lines = "\n".join(f"- {t['role']}: {mask_sensitive(t['text'])[0]}" for t in turns)
    spec = CallSpec(
        agent="summary",
        instructions=p.render(),
        input=(
            f"Previous summary:\n<<<\n{previous or '(none)'}\n>>>\n\n"
            f"Older turns to add (oldest first):\n<<<\n{lines}\n>>>"
        ),
        effort="none",
        max_output_tokens=300,
        context={"previous": previous, "turns": turns, "until_message_id": until},
    )
    try:
        text = ctx.llm_for("summary").parse(spec, SummaryOutput, ctx).value.summary.strip()
    except RECOVERABLE as exc:
        ctx.trace.finish(step, t0, "error", prompt=p.ref, error=f"{type(exc).__name__}: {exc}", turns=len(turns))
        return previous
    if not text:  # nothing usable: keep what there was, and let the next turn try again
        ctx.trace.finish(step, t0, "error", prompt=p.ref, error="empty summary", turns=len(turns))
        return previous
    summary = clip(mask_sensitive(text)[0])
    store.save_summary(conversation_id, summary, until)
    ctx.trace.finish(step, t0, "ok", prompt=p.ref, turns=len(turns), until_message_id=until)
    return summary
