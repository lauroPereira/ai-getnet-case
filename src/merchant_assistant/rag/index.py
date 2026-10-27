"""Vector index over Qdrant (server, embedded local path or in-memory)."""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from qdrant_client import QdrantClient, models

from merchant_assistant.rag.chunk import Chunk
from merchant_assistant.rag.embed import Embedder

_CLIENT_LOCKS: dict[int, threading.Lock] = {}
_CLIENT_LOCKS_GUARD = threading.Lock()


@dataclass(frozen=True)
class Hit:
    score: float
    payload: dict

    @property
    def chunk_id(self) -> str:
        return self.payload["chunk_id"]


def open_qdrant(url: str | None, local_path: Path) -> QdrantClient:
    if url == ":memory:":
        return QdrantClient(":memory:")
    if url:
        return QdrantClient(url=url, timeout=10)
    local_path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(local_path))


def corpus_hash(chunks: list[Chunk]) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c.chunk_id.encode())
    return h.hexdigest()


def point_digest(chunk_ids) -> str:
    """Order-independent digest of the chunk ids stored in a collection."""
    return hashlib.sha256("\n".join(sorted(chunk_ids)).encode()).hexdigest()


class KnowledgeIndex:
    def __init__(self, client: QdrantClient, collection: str, embedder: Embedder) -> None:
        self.client, self.collection, self.embedder = client, collection, embedder
        # Captured and candidate indices can share one local Qdrant client.
        with _CLIENT_LOCKS_GUARD:
            self._lock = _CLIENT_LOCKS.setdefault(id(client), threading.Lock())

    def count(self) -> int:
        with self._lock:
            if not self.client.collection_exists(self.collection):
                return 0
            return self.client.count(self.collection, exact=True).count

    def exists(self) -> bool:
        with self._lock:
            return self.client.collection_exists(self.collection)

    def inspect(self) -> dict | None:
        """Read-only facts about the stored collection (no embeddings, no network); None when it is missing."""
        with self._lock:
            if not self.client.collection_exists(self.collection):
                return None
            vectors = self.client.get_collection(self.collection).config.params.vectors
            chunk_ids: list[str] = []
            offset = None
            while True:
                records, offset = self.client.scroll(
                    self.collection, limit=256, offset=offset, with_payload=["chunk_id"], with_vectors=False
                )
                chunk_ids += [str((record.payload or {}).get("chunk_id")) for record in records]
                if offset is None:
                    break
            return {
                "dim": getattr(vectors, "size", None),
                "points": self.client.count(self.collection, exact=True).count,
                "point_digest": point_digest(chunk_ids),
            }

    def rebuild(
        self,
        chunks: list[Chunk],
        manifest_path: Path | None = None,
        *,
        replace_existing: bool = False,
    ) -> dict:
        """Build the collection. A published collection is immutable, so an existing one is never replaced unless
        the caller explicitly opts in for a disposable collection."""
        with self._lock:
            if self.client.collection_exists(self.collection) and not replace_existing:
                raise RuntimeError("Collection already exists.")
        vectors = self.embedder.embed([c.text for c in chunks])  # paid: nothing is created before it succeeds
        points = [
            models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, c.chunk_id)), vector=v, payload=c.payload())
            for c, v in zip(chunks, vectors, strict=True)
        ]
        with self._lock:
            if self.client.collection_exists(self.collection):
                if not replace_existing:
                    raise RuntimeError("Collection already exists.")
                self.client.delete_collection(self.collection)
            self.client.create_collection(
                self.collection,
                vectors_config=models.VectorParams(size=self.embedder.dim, distance=models.Distance.COSINE),
            )
            with warnings.catch_warnings():  # local/in-memory Qdrant ignores payload indexes and warns about it
                warnings.simplefilter("ignore", UserWarning)
                self.client.create_payload_index(self.collection, "source_kind", models.PayloadSchemaType.KEYWORD)
            for i in range(0, len(points), 128):
                self.client.upsert(self.collection, points=points[i : i + 128])
        manifest = {
            "collection": self.collection,
            "embedding_model": self.embedder.model,
            "dim": self.embedder.dim,
            "chunks": len(chunks),
            "documents": len({c.doc_id for c in chunks}),
            "corpus_hash": corpus_hash(chunks),
            "point_digest": point_digest(c.chunk_id for c in chunks),
            "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        if manifest_path:
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        return manifest

    def search(
        self, query: str, *, k: int = 6, source_kinds: list[str] | None = None, min_score: float = 0.0
    ) -> list[Hit]:
        vector = self.embedder.embed([query])[0]
        query_filter = None
        if source_kinds:
            query_filter = models.Filter(
                must=[models.FieldCondition(key="source_kind", match=models.MatchAny(any=source_kinds))]
            )
        with self._lock:
            result = self.client.query_points(
                self.collection, query=vector, limit=k, query_filter=query_filter, with_payload=True
            )
        return [Hit(p.score, dict(p.payload or {})) for p in result.points if p.score >= min_score]
