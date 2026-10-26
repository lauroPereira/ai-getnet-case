"""Documents for the knowledge base: public snapshots and the synthetic operational corpus."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

SourceKind = Literal["public_official", "simulated_internal"]


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    text: str
    source_kind: SourceKind
    url: str | None = None
    metadata: dict = field(default_factory=dict)


def slug_for(url: str) -> str:
    path = re.sub(r"^https?://", "", url).rstrip("/")
    return re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")[:120]


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    _, block, body = raw.split("---", 2)
    meta = {}
    for line in block.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body.lstrip()


def load_public_snapshots(pages_dir: Path) -> list[Document]:
    docs = []
    for path in sorted(pages_dir.glob("*.json")):
        snap = json.loads(path.read_text(encoding="utf-8"))
        docs.append(
            Document(
                doc_id=f"pub:{path.stem}",
                title=snap["title"],
                text=snap["text"],
                source_kind="public_official",
                url=snap["url"],
                metadata={
                    "market": snap.get("market"),
                    "language": snap.get("language"),
                    "topic": snap.get("topic"),
                    "products": snap.get("products", []),
                    "collected_at": snap.get("collected_at"),
                    "capture": snap.get("capture"),
                    "content_hash": snap.get("content_hash"),
                },
            )
        )
    return docs


def load_demo_corpus(demo_dir: Path) -> list[Document]:
    docs = []
    for path in sorted(demo_dir.glob("[0-9]*.md")):
        meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
        title_match = re.search(r"^# (.+)$", body, flags=re.M)
        docs.append(
            Document(
                doc_id=f"demo:{meta.get('id', path.stem)}",
                title=title_match.group(1).strip() if title_match else path.stem,
                text=body,
                source_kind="simulated_internal",
                url=None,
                metadata={
                    "procedure_id": meta.get("id"),
                    "version": meta.get("version"),
                    "domain": meta.get("domain"),
                    "environment": meta.get("environment", "demo"),
                    "content_hash": content_hash(body),
                },
            )
        )
    return docs


def load_all(data_dir: Path) -> list[Document]:
    return load_public_snapshots(data_dir / "snapshots" / "public" / "pages") + load_demo_corpus(
        data_dir / "knowledge-demo"
    )
