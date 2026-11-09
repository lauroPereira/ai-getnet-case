"""The evidence the model judge reads (spec v0.8.0 D9): what the system had in hand when it wrote a reply.

Two kinds of items: the passages of official pages and demo procedures the Knowledge step cited, and the data the
tools returned for the merchant's own synthetic account. Everything is masked with the input guard, then fitted to
EVIDENCE_LIMIT_CHARS; the cut is recorded, never silent. The trace keeps only the call of a tool, so the runner
reads the data through the registry observer while a case runs (`record_tool_results`).

A web-search reply (spec v0.11.0 D2, task 87) adds the text of the pages it cited, fetched after the reply by the
`WebPages` that `use_web_pages` sets (the evaluation commands set it from WEB_EVIDENCE; nothing is fetched without it).
The note in `evidence_notes` has three forms: pages fetched, a page unavailable (the search summary the assistant
wrote is given instead), and no URL recorded (the note of v0.10.0)."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

from merchant_assistant.evaluation.web_pages import PageText, WebPages
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
WEB_PAGE_NOTE = (
    'The reply comes from a web search. Each evidence item of kind "web_page" is the text of a page the search '
    "cited (its title and url are given), fetched when the reply was evaluated, masked and cut like the other items: "
    "judge the reply against it as you would a passage. The page may have changed since the reply was written."
)
WEB_SUMMARY_NOTE = (
    "page unavailable; the search summary written by the assistant is given instead, it is not a page. The evidence "
    'item of kind "web_summary" is what the web search returned to the assistant: use it to see what the search '
    "said, not as confirmation by an independent source."
)
# The form of each web note, as counted in the report of `eval`.
WEB_NOTE_FORMS = {WEB_PAGE_NOTE: "web_page", WEB_SUMMARY_NOTE: "web_summary", WEB_NOTE: "no_url"}
WEB_SUMMARY_LABEL = "web search summary (written by the assistant)"
_WEB_PAGES: ContextVar[WebPages | None] = ContextVar("web_pages", default=None)


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


@contextmanager
def use_web_pages(pages: WebPages | None) -> Iterator[WebPages | None]:
    """The page fetcher `judge_input` uses inside the block; None (the default outside any block) fetches nothing."""
    token = _WEB_PAGES.set(pages)
    try:
        yield pages
    finally:
        _WEB_PAGES.reset(token)


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


def _add(notes: list[str], note: str) -> None:
    if note not in notes:
        notes.append(note)


def web_items(detail: dict, pages: WebPages, seen: set[str]) -> tuple[list[dict], list[str]]:
    """The evidence of one web-search step with recorded URLs: one `web_page` item per page fetched; when a page is
    unavailable (or every one was), the search summary of the step as one `web_summary` item. `seen` skips a URL
    already given by an earlier step."""
    items: list[dict] = []
    notes: list[str] = []
    unavailable = False
    fresh = [entry for entry in detail["web_urls"] if entry.get("url") and entry["url"] not in seen]
    if not fresh and any(entry.get("url") in seen for entry in detail["web_urls"]):
        return [], []  # every page of this step was already given by an earlier one
    for entry in fresh:
        url = entry["url"]
        if url in seen:
            continue
        seen.add(url)
        page = pages.fetch(url)
        if isinstance(page, PageText):
            title = entry.get("title") or page.title or url
            items.append({"kind": "web_page", "label": title, "title": title, "url": url, "text": _masked(page.text)})
        else:
            unavailable = True
    if items:
        _add(notes, WEB_PAGE_NOTE)
    if unavailable or not items:
        summary = detail.get("web_summary") or ""
        if summary:
            items.append({"kind": "web_summary", "label": WEB_SUMMARY_LABEL, "text": _masked(summary)})
            _add(notes, WEB_SUMMARY_NOTE)
        elif not items:
            _add(notes, WEB_NOTE)
    return items, notes


def passage_items(
    trace: dict, texts: dict[str, str], pages: WebPages | None = None
) -> tuple[list[dict], list[str]]:
    """Cited passages of the Knowledge step. The full chunk text comes from the corpus; the 400-character excerpt kept
    in the trace is the fallback. Without any citation the retrieved passages are used, as the step itself does. A
    web-search step adds its pages (`web_items`) when `pages` is given and the step recorded URLs; otherwise it adds
    the note that the web text is not available."""
    cited: list[str] = []
    hits: dict[str, dict] = {}
    notes: list[str] = []
    web_steps: list[dict] = []
    for step in trace.get("steps", []):
        if step["step"] not in KNOWLEDGE_STEPS:
            continue
        detail = step.get("detail", {})
        cited += [chunk_id for chunk_id in detail.get("citations", []) if chunk_id]
        for hit in detail.get("hits", []):
            hits.setdefault(hit["chunk_id"], hit)
        if step["step"] == "web" or detail.get("mode") == "web":
            if pages is not None and detail.get("web_urls"):
                web_steps.append(detail)
            else:
                _add(notes, WEB_NOTE)
    items = []
    for chunk_id in dict.fromkeys(cited) or list(hits):
        hit = hits.get(chunk_id, {})
        text = texts.get(chunk_id) or hit.get("excerpt") or ""
        if text:
            items.append({"kind": "passage", "label": hit.get("doc") or chunk_id, "text": _masked(text)})
    seen: set[str] = set()
    for detail in web_steps:
        more, more_notes = web_items(detail, pages, seen)
        items += more
        for note in more_notes:
            _add(notes, note)
    return items, notes


def web_note_counts(rows: list[dict]) -> dict:
    """How many answers of a report carry each form of the web note (task 87): pages fetched, summary in place of an
    unavailable page, no URL. An answer whose steps fell in two forms counts in both."""
    given = [row["judge_input"] for row in rows if row.get("judge_input")]
    counts = {"answers": len(given), **dict.fromkeys(WEB_NOTE_FORMS.values(), 0)}
    for data in given:
        for form in {WEB_NOTE_FORMS[note] for note in data.get("evidence_notes", []) if note in WEB_NOTE_FORMS}:
            counts[form] += 1
    return counts


def web_note_line(counts: dict) -> str:
    """The sentence of the Markdown report (in Portuguese, like the rest of it)."""
    return (
        f"Evidência da busca web (tarefa 87), em {counts['answers']} respostas com evidência gravada: "
        f"{counts['web_page']} com página citada buscada na avaliação, {counts['web_summary']} com o resumo da busca "
        f"no lugar de uma página indisponível e {counts['no_url']} sem URL gravada (só os títulos das fontes)."
    )


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
    passages, notes = passage_items(trace, texts, _WEB_PAGES.get())
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
