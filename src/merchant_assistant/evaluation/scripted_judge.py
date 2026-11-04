"""Deterministic stand-in for the model judge `judge.v3` (zero cost, offline).

It reads the same JSON a real judge receives and applies fixed rules, so the campaign path (evidence, repetitions,
aggregation, reports) runs end to end in tests and in `eval --scripted --judge`. It says nothing about the real
quality of a reply. Kept apart from `scripted_policy.py`, which belongs to the attendance agents."""

from __future__ import annotations

import json
import re

from merchant_assistant.evaluation.judge import RUBRIC, RUBRIC_VERSION, Judge
from merchant_assistant.guardrails.output import amounts
from merchant_assistant.llm.base import LLM, Meter
from merchant_assistant.llm.prompts import load_prompt
from merchant_assistant.llm.scripted import ScriptedCall, ScriptedLLM

MODEL = "scripted-judge-v3"
_WORDS = re.compile(r"[^\W\d_]{4,}", re.UNICODE)


def _words(text: str) -> set[str]:
    return {word.casefold() for word in _WORDS.findall(text)}


def handler(call: ScriptedCall) -> dict:
    """Groundedness and factual correctness drop when the reply states an amount that neither the evidence nor the
    merchant message contains (and the verdict turns on); relevance follows the words the reply shares with the
    question; usefulness follows the length of the reply."""
    data = json.loads(call.spec.input)
    reply = data["reply"]
    support = " ".join([data["merchant_message"], *(item["text"] for item in data["evidence"])])
    invented = amounts(reply) - amounts(support)
    shared = len(_words(data["merchant_message"]) & _words(reply))
    relevance = 5 if shared >= 2 else 4 if shared == 1 else 3
    usefulness = 5 if len(reply) >= 80 else 4 if len(reply) >= 30 else 2
    return {
        "groundedness": 2 if invented else 5,
        "groundedness_reason": "Scripted judge: an amount in the reply is not in the evidence."
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


def scripted_judge(prompts_dir, meter: Meter, llm: LLM | None = None) -> Judge:
    return Judge(
        llm or scripted_llm(),
        "scripted",
        MODEL,
        load_prompt(prompts_dir, RUBRIC, RUBRIC_VERSION),
        meter,
        "scripted",
    )
