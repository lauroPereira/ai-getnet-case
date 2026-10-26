"""Section-aware chunking that keeps document metadata on every fragment."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from merchant_assistant.rag.documents import Document


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    position: int
    text: str
    title: str
    url: str | None
    source_kind: str
    metadata: dict

    def payload(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "position": self.position,
            "text": self.text,
            "title": self.title,
            "url": self.url,
            "source_kind": self.source_kind,
            **{k: v for k, v in self.metadata.items() if v is not None},
        }


def _sections(doc: Document) -> list[str]:
    if doc.source_kind == "simulated_internal":
        parts = re.split(r"\n(?=## )", doc.text)
        return [p.strip() for p in parts if p.strip()]
    return [p.strip() for p in re.split(r"\n{2,}", doc.text) if p.strip()] or [doc.text]


def _windows(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    lines, windows, current = text.split("\n"), [], ""
    for line in lines:
        while len(line) > max_chars:  # very long line: hard split
            head, line = line[:max_chars], line[max_chars - overlap :]
            if current:
                windows.append(current)
                current = ""
            windows.append(head)
        if len(current) + len(line) + 1 > max_chars and current:
            windows.append(current)
            tail = current[-overlap:]
            current = tail[tail.find("\n") + 1 :] if "\n" in tail else ""
        current = f"{current}\n{line}" if current else line
    if current.strip():
        windows.append(current)
    return windows


def chunk_document(doc: Document, *, max_chars: int = 1200, overlap: int = 150) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in _sections(doc):
        for window in _windows(section, max_chars, overlap):
            body = window.strip()
            if len(body) < 40:
                continue
            position = len(chunks)
            digest = hashlib.sha1(f"{doc.doc_id}|{position}|{body}".encode()).hexdigest()[:16]
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}#{position}-{digest}",
                    doc_id=doc.doc_id,
                    position=position,
                    text=f"{doc.title}\n{body}",
                    title=doc.title,
                    url=doc.url,
                    source_kind=doc.source_kind,
                    metadata=doc.metadata,
                )
            )
    return chunks
