"""Deterministic stand-in for the model judge `judge.v3` (zero cost, offline).

It reads the same JSON a real judge receives and applies fixed rules, so the campaign path (evidence, repetitions,
aggregation, reports) runs end to end in tests and in `eval --scripted --judge`. It says nothing about the real
quality of a reply. Kept apart from `scripted_policy.py`, which belongs to the attendance agents."""

from __future__ import annotations

import json
import re

from merchant_assistant.evaluation.judge import RUBRIC, Judge, rubric_version
from merchant_assistant.guardrails.output import amounts
from merchant_assistant.llm.base import LLM, Meter, NullMeter
from merchant_assistant.llm.prompts import load_prompt
from merchant_assistant.llm.scripted import ScriptedCall, ScriptedLLM

MODEL = "scripted-judge-v3"
_WORDS = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
# The merchant's own account, in the words a reply uses for it ("seu saldo", "your settlement"). The prompt tells the
# judge to keep flagging such specifics under a web note when no tool result shows them; this is the stand-in for that.
_ACCOUNT = re.compile(
    r"\b(?:seu|sua|seus|suas|your)\s+(?:saldo|conta|extrato|agenda|vendas?|recebíveis|recebível|liquidações|liquidação|"
    r"pagamentos?|balance|account|statement|sales|receivables?|settlements?|payouts?)\b",
    re.IGNORECASE,
)


def _words(text: str) -> set[str]:
    return {word.casefold() for word in _WORDS.findall(text)}


def _invented_amounts(data: dict) -> tuple[set[int], bool]:
    """The amounts of the reply that nothing supports, and whether they are account data under a web note.

    Plain evidence: an amount the question and the evidence do not contain. Under an evidence note (a web answer whose
    text is not recorded) a public amount cannot be checked and is left alone, as `judge.v3` says; an amount stated
    about the merchant's own account (see `_ACCOUNT`) still needs a tool result or the question to show it."""
    reply, message, items = data["reply"], data["merchant_message"], data["evidence"]
    if not data.get("evidence_notes"):
        return amounts(reply) - amounts(" ".join([message, *(item["text"] for item in items)])), False
    if not _ACCOUNT.search(reply):
        return set(), False
    shown = " ".join([message, *(item["text"] for item in items if item["kind"] == "tool_result")])
    return amounts(reply) - amounts(shown), True


def handler(call: ScriptedCall) -> dict:
    """Groundedness and factual correctness drop when the reply states an amount that neither the evidence nor the
    merchant message contains (and the verdict turns on); relevance follows the words the reply shares with the
    question; usefulness follows the length of the reply. Like `judge.v3`, it does not hold a missing passage against a
    reply whose evidence notes say that its source text is not available (a web answer), but it keeps flagging data of
    the merchant's own account that no tool result shows."""
    data = json.loads(call.spec.input)
    reply = data["reply"]
    invented, account = _invented_amounts(data)
    shared = len(_words(data["merchant_message"]) & _words(reply))
    relevance = 5 if shared >= 2 else 4 if shared == 1 else 3
    usefulness = 5 if len(reply) >= 80 else 4 if len(reply) >= 30 else 2
    where = "of the merchant's account is not in a tool result" if account else "in the reply is not in the evidence"
    return {
        "groundedness": 2 if invented else 5,
        "groundedness_reason": f"Scripted judge: an amount {where}."
        if invented
        else "Scripted judge: every amount in the reply is in the evidence or in the question.",
        "factual_correctness": 3 if invented else 5,
        "factual_correctness_reason": "Scripted judge: the amount cannot be checked."
        if invented
        else "Scripted judge: no amount contradicts the evidence.",
        "relevance": relevance,
        "relevance_reason": f"Scripted judge: the reply shares {shared} word(s) with the question.",
        "usefulness": usefulness,
        "usefulness_reason": f"Scripted judge: the reply has {len(reply)} characters.",
        "unsupported_claim": bool(invented),
    }


def scripted_llm() -> LLM:
    return ScriptedLLM(handler, model=MODEL)


def scripted_judge(
    prompts_dir, meter: Meter | None = None, llm: LLM | None = None, rubric: str | None = None
) -> Judge:
    """The stand-in under `judge.v3`, or under the rubric named (`rubric`, spec v0.10.0 D1). Its rules are the same
    for both: it records which prompt it was given, it does not imitate the new sentence of `judge.v4`."""
    return Judge(
        llm or scripted_llm(),
        "scripted",
        MODEL,
        load_prompt(prompts_dir, RUBRIC, rubric_version(rubric)),
        meter or NullMeter(),
        "scripted",
    )
