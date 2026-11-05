"""The evidence the model judge reads (spec v0.8.0 D9): what the system had in hand when it wrote a reply.

Two kinds of items: the passages of official pages and demo procedures the Knowledge step cited, and the data the
tools returned for the merchant's own synthetic account. Everything is masked with the input guard, then fitted to
EVIDENCE_LIMIT_CHARS; the cut is recorded, never silent. The trace keeps only the call of a tool, so the runner
reads the data through the registry observer while a case runs (`record_tool_results`)."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from merchant_assistant.guardrails.input import check_input, mask_sensitive
from merchant_assistant.tools import registry
from merchant_assistant.tools.registry import ToolOutcome

EVIDENCE_LIMIT_CHARS = 6000
CUT_MARK = " [...cut]"
HANDOFF_PROTOCOL = re.compile(r"HO-\d{8}-[A-F0-9]{6}\Z")
KNOWLEDGE_STEPS = ("knowledge", "web")  # the web-search node of the replanning writes its own step, named `web`
WEB_NOTE = (
    "The reply comes from a web search whose text is not recorded: judge only whether it is consistent with the "
    "listed sources and say so in the reasons."
)


@contextmanager
def record_tool_results() -> Iterator[list[ToolOutcome]]:
    """Collects the outcome of every tool call made inside the block, by the code of this run only (the graph copies
    the context to the threads it uses; another run, in another thread, has its own observers)."""
    outcomes: list[ToolOutcome] = []
    token = registry.OUTCOME_OBSERVERS.set((*registry.OUTCOME_OBSERVERS.get(), outcomes.append))
    try:
        yield outcomes
    finally:
        registry.OUTCOME_OBSERVERS.reset(token)


@lru_cache
def chunk_texts(data_dir: Path) -> dict[str, str]:
    """Full text of every chunk of the corpus by chunk id (the index is built from the same files)."""
    from merchant_assistant.rag.chunk import chunk_document
    from merchant_assistant.rag.documents import load_all

    return {chunk.chunk_id: chunk.text for doc in load_all(data_dir) for chunk in chunk_document(doc)}


def _masked(text: str) -> str:
    return mask_sensitive(text)[0]


def tool_items(outcomes: list[ToolOutcome]) -> list[dict]:
    items = []
    for outcome in outcomes:
        body = {"arguments": outcome.arguments, "result": outcome.data if outcome.ok else {"error": outcome.error}}
        text = json.dumps(body, ensure_ascii=False, sort_keys=True, default=str)
        items.append({"kind": "tool_result", "label": outcome.name, "text": _masked(text)})
    return items


def handoff_protocol_items(status: str, trace: dict) -> list[dict]:
    """Expose only a verified protocol from a successful escalation step for a handoff."""
    if status != "handoff":
        return []

    protocols: set[str] = set()
    for step in trace.get("steps", []):
        if step.get("step") != "escalation" or step.get("status") != "ok":
            continue
        protocol = step.get("detail", {}).get("protocol")
        if isinstance(protocol, str) and HANDOFF_PROTOCOL.fullmatch(protocol):
            protocols.add(protocol)
    if len(protocols) != 1:
        return []

    (protocol,) = protocols
    return [{"kind": "trace", "label": "escalation protocol", "text": _masked(protocol)}]


def passage_items(trace: dict, texts: dict[str, str]) -> tuple[list[dict], list[str]]:
    """Cited passages of the Knowledge step. The full chunk text comes from the corpus; the 400-character excerpt kept
    in the trace is the fallback. Without any citation the retrieved passages are used, as the step itself does."""
    cited: list[str] = []
    hits: dict[str, dict] = {}
    notes: list[str] = []
    for step in trace.get("steps", []):
        if step["step"] not in KNOWLEDGE_STEPS:
            continue
        detail = step.get("detail", {})
        cited += [chunk_id for chunk_id in detail.get("citations", []) if chunk_id]
        for hit in detail.get("hits", []):
            hits.setdefault(hit["chunk_id"], hit)
        if (step["step"] == "web" or detail.get("mode") == "web") and WEB_NOTE not in notes:
            notes.append(WEB_NOTE)
    items = []
    for chunk_id in dict.fromkeys(cited) or list(hits):
        hit = hits.get(chunk_id, {})
        text = texts.get(chunk_id) or hit.get("excerpt") or ""
        if text:
            items.append({"kind": "passage", "label": hit.get("doc") or chunk_id, "text": _masked(text)})
    return items, notes


def _cut(text: str, share: int) -> str:
    return text[: share - len(CUT_MARK)] + CUT_MARK if share > 2 * len(CUT_MARK) else text[:share]


def fit_items(items: list[dict], limit: int = EVIDENCE_LIMIT_CHARS) -> tuple[list[dict], dict]:
    """Fits the items to `limit` characters in total. Short items stay whole and the long ones share what is left, so
    a long passage never pushes a tool result out. Returns the kept items and the truncation record."""
    original = sum(len(item["text"]) for item in items)
    if original <= limit:
        return items, {
            "limit_chars": limit,
            "original_chars": original,
            "kept_chars": original,
            "items": len(items),
            "items_cut": 0,
            "truncated": False,
        }
    kept: list[dict] = list(items)
    budget, remaining = limit, len(items)
    for index in sorted(range(len(items)), key=lambda i: len(items[i]["text"])):
        text = items[index]["text"]
        share = budget // remaining
        if len(text) > share:
            kept[index] = items[index] | {"text": _cut(text, share), "cut": True}
        budget -= len(kept[index]["text"])
        remaining -= 1
    return kept, {
        "limit_chars": limit,
        "original_chars": original,
        "kept_chars": sum(len(item["text"]) for item in kept),
        "items": len(items),
        "items_cut": sum(1 for item in kept if item.get("cut")),
        "truncated": True,
    }


def judge_input(
    message: str, body: dict, sources: list[str], outcomes: list[ToolOutcome], trace: dict, texts: dict[str, str]
) -> tuple[dict, dict]:
    """The only data the model judge receives, and the truncation record that is stored beside it."""
    passages, notes = passage_items(trace, texts)
    kept, truncation = fit_items([*tool_items(outcomes), *handoff_protocol_items(body["status"], trace), *passages])
    data = {
        "merchant_message": check_input(message).masked,
        "status": body["status"],
        "route": body["route"],
        "sources": sources,
        "evidence": kept,
        "evidence_truncation": truncation,
        "evidence_notes": notes,
        "reply": body["answer"],
    }
    return data, truncation
