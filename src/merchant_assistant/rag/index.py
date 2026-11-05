"""Vector index over Qdrant (server, embedded local path or in-memory)."""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
import warnings
import weakref
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from qdrant_client import QdrantClient, models

from merchant_assistant.rag import bm25
from merchant_assistant.rag.chunk import Chunk
from merchant_assistant.rag.embed import Embedder

_CLIENT_LOCKS: dict[int, threading.Lock] = {}
_CLIENT_LOCKS_GUARD = threading.Lock()
# v0.9.0 (task 80): BM25 built per (client, collection). Weak keys: a closed client does not keep, or lend, its cache.
_BM25_CACHE: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_BM25_GUARD = threading.Lock()
_BM25_BUILD_LOCKS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()  # one builder per (client, collection)

RETRIEVAL_MODES = ("dense", "hybrid")
RRF_K = 60  # reciprocal rank fusion constant (plan, technical decision 17)


@dataclass(frozen=True)
class Hit:
    score: float
    payload: dict
    origin: str = "dense"  # which list found it: dense, bm25 or both (hybrid trace)

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


def rrf(dense: list[Hit], lexical: list[tuple[float, dict]], k: int) -> list[Hit]:
    """Reciprocal rank fusion of two rankings; on equal score the better dense rank wins, then the BM25 rank."""
    absent = len(dense) + len(lexical) + 1
    fused: dict[str, dict] = {}
    for rank, hit in enumerate(dense, start=1):
        fused[hit.chunk_id] = {"score": 1 / (RRF_K + rank), "dense": rank, "bm25": absent, "payload": hit.payload}
    for rank, (_, payload) in enumerate(lexical, start=1):
        entry = fused.setdefault(
            str(payload["chunk_id"]), {"score": 0.0, "dense": absent, "bm25": absent, "payload": dict(payload)}
        )
        entry["score"] += 1 / (RRF_K + rank)
        entry["bm25"] = rank
    ordered = sorted(fused.values(), key=lambda e: (-e["score"], e["dense"], e["bm25"]))[:k]
    return [
        Hit(
            e["score"],
            e["payload"],
            "both" if e["dense"] < absent and e["bm25"] < absent else "dense" if e["dense"] < absent else "bm25",
        )
        for e in ordered
    ]


class KnowledgeIndex:
    def __init__(
        self,
        client: QdrantClient,
        collection: str,
        embedder: Embedder,
        *,
        mode: str = "dense",
        bm25_dir: Path | None = None,
    ) -> None:
        if mode not in RETRIEVAL_MODES:
            raise ValueError(f"Unknown retrieval mode: {mode!r}")
        self.client, self.collection, self.embedder = client, collection, embedder
        self.mode, self.bm25_dir = mode, bm25_dir  # search() without `mode` uses this (RETRIEVAL_MODE)
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
        with _BM25_GUARD:  # a replaced collection never answers with the BM25 of the previous corpus
            _BM25_CACHE.get(self.client, {}).pop(self.collection, None)
        manifest = {
            "collection": self.collection,
            "embedding_model": self.embedder.model,
            "dim": self.embedder.dim,
            "chunks": len(chunks),
            "documents": len({c.doc_id for c in chunks}),
            "corpus_hash": corpus_hash(chunks),
            "point_digest": point_digest(c.chunk_id for c in chunks),
            "bm25_corpus_hash": bm25.corpus_hash([c.payload() for c in chunks]),
            "retrieval_modes": list(RETRIEVAL_MODES),
            "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        if manifest_path:
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        return manifest

    def bm25_index(self) -> bm25.Bm25Index:
        """The BM25 over this collection's stored chunks, loaded from `bm25_dir` or built once per client. The
        payloads come from this read of the collection, not from the file; concurrent first searches wait for one
        builder instead of each building (and writing) its own."""
        with _BM25_GUARD:
            cached = _BM25_CACHE.get(self.client, {}).get(self.collection)
            if cached is not None:
                return cached
            build_lock = _BM25_BUILD_LOCKS.setdefault(self.client, {}).setdefault(self.collection, threading.Lock())
        with build_lock:
            with _BM25_GUARD:
                cached = _BM25_CACHE.get(self.client, {}).get(self.collection)
            if cached is not None:
                return cached
            records: list[dict] = []
            offset = None
            with self._lock:
                while True:
                    page, offset = self.client.scroll(
                        self.collection, limit=256, offset=offset, with_payload=True, with_vectors=False
                    )
                    records += [dict(record.payload or {}) for record in page]
                    if offset is None:
                        break
            index, _ = bm25.load_or_build(records, self.bm25_dir)
            with _BM25_GUARD:
                _BM25_CACHE.setdefault(self.client, {})[self.collection] = index
        return index

    def search(
        self,
        query: str,
        *,
        k: int = 6,
        source_kinds: list[str] | None = None,
        min_score: float = 0.0,
        mode: str | None = None,
    ) -> list[Hit]:
        """Dense by default. `hybrid` fuses the dense and BM25 top 3k by RRF; `min_score` filters only the dense list
        and the returned score is the fused one."""
        mode = mode or self.mode
        if mode == "dense":
            return self._dense(query, k=k, source_kinds=source_kinds, min_score=min_score)
        if mode != "hybrid":
            raise ValueError(f"Unknown retrieval mode: {mode!r}")
        depth = 3 * k
        dense = self._dense(query, k=depth, source_kinds=source_kinds, min_score=min_score)
        lexical = self.bm25_index().search(query, k=depth, source_kinds=source_kinds)
        return rrf(dense, lexical, k)

    def _dense(self, query: str, *, k: int, source_kinds: list[str] | None, min_score: float) -> list[Hit]:
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
