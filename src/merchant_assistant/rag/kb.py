"""Persistent, versioned knowledge-base administration."""

from __future__ import annotations

import difflib
import hashlib
import json
import math
import uuid
from datetime import UTC, datetime

from merchant_assistant.llm import pricing
from merchant_assistant.orchestration.budget import BudgetExceeded, BudgetGuard, CombinedBudgetGuard
from merchant_assistant.rag.chunk import chunk_document
from merchant_assistant.rag.documents import Document, content_hash
from merchant_assistant.rag.embed import HashEmbedder
from merchant_assistant.rag.index import KnowledgeIndex

MAX_DOCUMENT_BYTES = 64 * 1024


class KBBuildFailure(RuntimeError):
    """Sanitized candidate build failure; the active version remains untouched."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _check_cap(value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value) or value < 0:
        raise ValueError("The confirmed cost cap must be finite and non-negative.")


class KnowledgeBase:
    """Owns document snapshots and immutable candidate indexes for one runtime."""

    def __init__(
        self,
        *,
        db_path,
        index: KnowledgeIndex,
        data_dir,
        budget: BudgetGuard | CombinedBudgetGuard,
    ) -> None:
        self.db_path, self.index, self.data_dir, self.budget = db_path, index, data_dir, budget

    def _connect(self):
        from merchant_assistant.data.db import connect

        return connect(self.db_path)

    def _registered(self) -> bool:
        """Read-only check: documents and an active version are already recorded (no write lock is taken)."""
        conn = self._connect()
        try:
            documents = conn.execute("SELECT EXISTS(SELECT 1 FROM kb_documents)").fetchone()[0]
            state = conn.execute("SELECT active_version_id FROM kb_state WHERE singleton=1").fetchone()
            return bool(documents) and state is not None and state[0] is not None
        finally:
            conn.close()

    def bootstrap(self) -> None:
        """Register source snapshots once; the current collection remains untouched."""
        from merchant_assistant.rag.documents import load_all

        if self._registered():  # readiness and per-request capture stay read-only once the registry exists
            return
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT COUNT(*) FROM kb_documents").fetchone()[0] == 0:
                for doc in load_all(self.data_dir):
                    conn.execute(
                        "INSERT INTO kb_documents VALUES(?,?,?,?,?,?,?,?)",
                        (
                            doc.doc_id,
                            doc.title,
                            doc.source_kind,
                            doc.url,
                            _json(doc.metadata),
                            doc.text,
                            content_hash(doc.text),
                            _now(),
                        ),
                    )
            row = conn.execute("SELECT active_version_id FROM kb_state WHERE singleton=1").fetchone()
            if row and row[0] is None:
                version_id = "kb_initial"
                manifest = {
                    "collection": self.index.collection,
                    "embedding_model": self.index.embedder.model,
                    "dim": self.index.embedder.dim,
                    "source": "pre-v0.5-preserved",
                }
                try:
                    facts = self.index.inspect()  # read-only: fixes what the preserved collection holds today
                except Exception:  # an unreachable store must not block registration; transitions verify again
                    facts = None
                if facts and facts["points"]:
                    manifest |= {"chunks": facts["points"], "point_digest": facts["point_digest"]}
                snapshot = self._current_snapshot(conn, {})
                conn.execute(
                    "INSERT OR IGNORE INTO kb_versions("
                    "version_id,parent_version_id,collection_name,state,manifest,snapshot,created_at,updated_at) "
                    "VALUES(?,NULL,?,'active',?,?,?,?)",
                    (version_id, self.index.collection, _json(manifest), _json(snapshot), _now(), _now()),
                )
                conn.execute(
                    "UPDATE kb_state SET active_version_id=?,revision=revision+1 WHERE singleton=1", (version_id,)
                )
                conn.execute(
                    "INSERT INTO kb_events(actor,action,to_version_id,evidence,created_at) "
                    "VALUES('system','bootstrap',?,?,?)",
                    (version_id, _json({"collection_preserved": True}), _now()),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def _current_snapshot(self, conn, revisions: dict[str, int]) -> list[dict]:
        rows = conn.execute("SELECT * FROM kb_documents ORDER BY document_id").fetchall()
        result = []
        for row in rows:
            draft = conn.execute("SELECT * FROM kb_drafts WHERE document_id=?", (row["document_id"],)).fetchone()
            use_draft = draft is not None and (not revisions or revisions.get(row["document_id"]) == draft["revision"])
            result.append(
                {
                    "document_id": row["document_id"],
                    "title": row["title"],
                    "source_kind": row["source_kind"],
                    "url": row["url"],
                    "metadata": json.loads(row["metadata"]),
                    "content": draft["content"] if use_draft else row["content"],
                    "content_hash": draft["content_hash"] if use_draft else row["content_hash"],
                    "draft_revision": draft["revision"] if use_draft else None,
                }
            )
        unknown = set(revisions) - {item["document_id"] for item in result}
        if unknown:
            raise LookupError("Document not found")
        for doc_id, revision in revisions.items():
            draft = conn.execute("SELECT revision FROM kb_drafts WHERE document_id=?", (doc_id,)).fetchone()
            if draft is None or draft["revision"] != revision:
                raise RuntimeError("Draft revision changed")
        return result

    def list_documents(self, *, admin: bool) -> dict:
        self.bootstrap()
        conn = self._connect()
        try:
            items = []
            for row in conn.execute("SELECT * FROM kb_documents ORDER BY document_id"):
                draft = (
                    conn.execute(
                        "SELECT revision,content_hash FROM kb_drafts WHERE document_id=?", (row["document_id"],)
                    ).fetchone()
                    if admin
                    else None
                )
                items.append(
                    {
                        "document_id": row["document_id"],
                        "title": row["title"],
                        "source_kind": row["source_kind"],
                        "url": row["url"],
                        "content_hash": row["content_hash"],
                        "editable": row["source_kind"] == "simulated_internal",
                        "draft_revision": draft["revision"] if draft else None,
                        "draft_hash": draft["content_hash"] if draft else None,
                    }
                )
            return {"documents": items}
        finally:
            conn.close()

    def document(self, document_id: str, *, admin: bool) -> dict:
        self.bootstrap()
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM kb_documents WHERE document_id=?", (document_id,)).fetchone()
            if row is None:
                raise LookupError("Document not found")
            if not admin and row["source_kind"] != "public_official":
                raise LookupError("Document not found")
            draft = (
                conn.execute("SELECT * FROM kb_drafts WHERE document_id=?", (document_id,)).fetchone()
                if admin
                else None
            )
            return {
                "document_id": row["document_id"],
                "title": row["title"],
                "source_kind": row["source_kind"],
                "url": row["url"],
                "metadata": json.loads(row["metadata"]),
                "content": row["content"],
                "content_hash": row["content_hash"],
                "draft": dict(draft) if draft else None,
            }
        finally:
            conn.close()

    def save_draft(self, document_id: str, content: str, expected_revision: int) -> dict:
        encoded = content.encode("utf-8")
        if not content.strip() or len(encoded) > MAX_DOCUMENT_BYTES:
            raise ValueError("Content must be non-empty and at most 64 KiB UTF-8.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            doc = conn.execute("SELECT source_kind FROM kb_documents WHERE document_id=?", (document_id,)).fetchone()
            if doc is None:
                raise LookupError("Document not found")
            if doc["source_kind"] != "simulated_internal":
                raise PermissionError("Official source documents are read-only.")
            row = conn.execute("SELECT revision FROM kb_drafts WHERE document_id=?", (document_id,)).fetchone()
            current = row["revision"] if row else 0
            if current != expected_revision:
                raise RuntimeError("Draft revision changed")
            revision, digest = current + 1, content_hash(content)
            conn.execute(
                "INSERT INTO kb_drafts VALUES(?,?,?,?,?) "
                "ON CONFLICT(document_id) DO UPDATE SET revision=excluded.revision,"
                "content=excluded.content,content_hash=excluded.content_hash,updated_at=excluded.updated_at",
                (document_id, revision, content, digest, _now()),
            )
            conn.execute("COMMIT")
            return {"document_id": document_id, "revision": revision, "content_hash": digest}
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def diff(self, document_id: str) -> dict:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT x.content,x.content_hash,x.revision FROM kb_documents d "
                "JOIN kb_drafts x USING(document_id) "
                "WHERE d.document_id=? AND d.source_kind='simulated_internal'",
                (document_id,),
            ).fetchone()
            if row is None:
                raise LookupError("Draft not found")
            original = conn.execute("SELECT content FROM kb_documents WHERE document_id=?", (document_id,)).fetchone()[
                0
            ]
            return {
                "document_id": document_id,
                "revision": row["revision"],
                "content_hash": row["content_hash"],
                "diff": "\n".join(
                    difflib.unified_diff(
                        original.splitlines(),
                        row["content"].splitlines(),
                        fromfile="published",
                        tofile="draft",
                        lineterm="",
                    )
                ),
            }
        finally:
            conn.close()

    def estimate(self, revisions: dict[str, int]) -> dict:
        self.bootstrap()
        conn = self._connect()
        try:
            snapshot = self._current_snapshot(conn, revisions)
        finally:
            conn.close()
        docs = [
            Document(x["document_id"], x["title"], x["content"], x["source_kind"], x["url"], x["metadata"])
            for x in snapshot
        ]
        chunks = [chunk for doc in docs for chunk in chunk_document(doc)]
        model = self.index.embedder.model
        price = {"input_per_mtok": 0.0} if isinstance(self.index.embedder, HashEmbedder) else pricing.model_price(model)
        tokens = sum(math.ceil(len(chunk.text.encode("utf-8")) / 3) for chunk in chunks)
        cost = round(tokens * price["input_per_mtok"] / 1_000_000, 8)
        digest = hashlib.sha256(_json([(x["document_id"], x["content_hash"]) for x in snapshot]).encode()).hexdigest()
        state = self._connect()
        try:
            active = state.execute("SELECT active_version_id,revision FROM kb_state WHERE singleton=1").fetchone()
        finally:
            state.close()
        return {
            "digest": digest,
            "documents": len(docs),
            "chunks": len(chunks),
            "estimated_tokens": tokens,
            "estimated_cost_usd": cost,
            "embedding_model": model,
            "dimension": self.index.embedder.dim,
            "active_version_id": active["active_version_id"],
            "active_revision": active["revision"],
            "revisions": revisions,
            "snapshot": snapshot,
        }

    def create_version(
        self,
        revisions: dict[str, int],
        expected_active: str,
        expected_digest: str,
        confirmed: bool,
        max_cost_usd: float,
    ) -> dict:
        _check_cap(max_cost_usd)
        estimate = self.estimate(revisions)
        if not confirmed or estimate["digest"] != expected_digest:
            raise RuntimeError("Confirmation or corpus digest is stale.")
        if expected_active != estimate["active_version_id"]:
            raise RuntimeError("Active version changed.")
        if estimate["estimated_cost_usd"] > max_cost_usd:
            raise BudgetExceeded("installation", estimate["estimated_cost_usd"], max_cost_usd)
        conn = self._connect()
        version_id = f"kb_{uuid.uuid4().hex[:16]}"
        collection = f"getnet_{version_id}"
        try:
            conn.execute("BEGIN IMMEDIATE")
            active = conn.execute("SELECT active_version_id FROM kb_state WHERE singleton=1").fetchone()[0]
            if active != expected_active:
                raise RuntimeError("Active version changed.")
            current = self._current_snapshot(conn, revisions)
            if (
                estimate["digest"]
                != hashlib.sha256(_json([(x["document_id"], x["content_hash"]) for x in current]).encode()).hexdigest()
            ):
                raise RuntimeError("Corpus changed.")
            if KnowledgeIndex(self.index.client, collection, self.index.embedder).exists():
                raise RuntimeError("Candidate collection already exists.")
            manifest = {
                k: estimate[k]
                for k in (
                    "digest",
                    "documents",
                    "chunks",
                    "estimated_tokens",
                    "estimated_cost_usd",
                    "embedding_model",
                    "dimension",
                )
            }
            conn.execute(
                "INSERT INTO kb_versions("
                "version_id,parent_version_id,collection_name,state,manifest,snapshot,created_at,updated_at) "
                "VALUES(?,?,?,'building',?,?,?,?)",
                (version_id, active, collection, _json(manifest), _json(current), _now(), _now()),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            conn.close()
            raise
        conn.close()
        try:
            docs = [
                Document(x["document_id"], x["title"], x["content"], x["source_kind"], x["url"], x["metadata"])
                for x in estimate["snapshot"]
            ]
            chunks = [chunk for doc in docs for chunk in chunk_document(doc)]
            # A conservative reservation is made before every provider batch by OpenAIEmbedder.
            candidate_index = KnowledgeIndex(self.index.client, collection, self.index.embedder)
            built = candidate_index.rebuild(chunks, replace_existing=False)
            if (
                built["chunks"] != estimate["chunks"]
                or built["embedding_model"] != estimate["embedding_model"]
                or built["dim"] != estimate["dimension"]
            ):
                raise RuntimeError("Built index does not match the approved manifest.")
            manifest.update(built)
            self._verify_integrity(collection, manifest)  # what was stored is what the manifest promises
            self._set_version(version_id, "testing", manifest=manifest)
            return self.version(version_id, admin=True)
        except BudgetExceeded:
            self._set_version(version_id, "failed", error="Candidate build exceeded the configured budget.")
            raise
        except Exception as exc:
            self._set_version(version_id, "failed", error="Candidate build failed; active version was preserved.")
            raise KBBuildFailure("Candidate build failed; active version was preserved.") from exc

    def _set_version(
        self, version_id: str, state: str, *, manifest=None, error=None, test_result=None, from_states=()
    ) -> bool:
        """Update a version row; with `from_states` the write applies only while the row is still in one of them,
        so a concurrent activation can never be overwritten. Returns whether the row was updated."""
        conn = self._connect()
        try:
            guard = f" AND state IN ({','.join('?' * len(from_states))})" if from_states else ""
            cursor = conn.execute(
                "UPDATE kb_versions SET state=?,manifest=COALESCE(?,manifest),error=?,"
                "test_result=COALESCE(?,test_result),updated_at=? WHERE version_id=?" + guard,
                (
                    state,
                    _json(manifest) if manifest is not None else None,
                    error,
                    _json(test_result) if test_result is not None else None,
                    _now(),
                    version_id,
                    *from_states,
                ),
            )
            return cursor.rowcount > 0
        finally:
            conn.close()

    def _verify_integrity(self, collection_name: str, manifest: dict) -> None:
        """Confirm, read-only and without embeddings, that the stored collection matches its manifest."""
        facts = KnowledgeIndex(self.index.client, collection_name, self.index.embedder).inspect()
        dimension = manifest.get("dim") or manifest.get("dimension")
        expected_points, expected_digest = manifest.get("chunks"), manifest.get("point_digest")
        if not (
            facts is not None
            and facts["points"] > 0
            and manifest.get("embedding_model") == self.index.embedder.model
            and dimension == self.index.embedder.dim == facts["dim"]
            and (expected_points is None or facts["points"] == expected_points)
            and (expected_digest is None or facts["point_digest"] == expected_digest)
        ):
            raise RuntimeError("Collection integrity could not be confirmed.")

    def version(self, version_id: str, *, admin: bool) -> dict:
        self.bootstrap()
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM kb_versions WHERE version_id=?", (version_id,)).fetchone()
            if row is None:
                raise LookupError("Version not found")
            if not admin and row["state"] not in ("active", "retired"):
                raise LookupError("Version not found")
            return {
                "version_id": row["version_id"],
                "parent_version_id": row["parent_version_id"],
                "collection_name": row["collection_name"],
                "state": row["state"],
                "manifest": json.loads(row["manifest"]),
                "snapshot": json.loads(row["snapshot"]),
                "test_result": json.loads(row["test_result"]) if row["test_result"] else None,
                "error": row["error"],
            }
        finally:
            conn.close()

    def versions(self, *, admin: bool) -> dict:
        self.bootstrap()
        conn = self._connect()
        try:
            state = dict(conn.execute("SELECT * FROM kb_state WHERE singleton=1").fetchone())
            rows = conn.execute(
                "SELECT version_id,parent_version_id,collection_name,state,manifest,test_result,error,created_at "
                "FROM kb_versions ORDER BY created_at DESC"
            ).fetchall()
            items = [
                dict(row)
                | {
                    "manifest": json.loads(row["manifest"]),
                    "test_result": json.loads(row["test_result"]) if row["test_result"] else None,
                }
                for row in rows
                if admin or row["state"] in ("active", "retired")
            ]
            return {
                "active_version_id": state["active_version_id"],
                "previous_version_id": state["previous_version_id"],
                "revision": state["revision"],
                "versions": items,
            }
        finally:
            conn.close()

    def test_version(self, version_id: str, *, confirmed: bool, max_cost_usd: float) -> dict:
        version = self.version(version_id, admin=True)
        if version["state"] not in ("testing", "ready"):
            raise RuntimeError("Only candidate versions can be tested.")
        if not confirmed:
            raise ValueError("Explicit confirmation is required.")
        _check_cap(max_cost_usd)
        probe = "How can I get help with a payment?"
        price = (
            {"input_per_mtok": 0.0}
            if isinstance(self.index.embedder, HashEmbedder)
            else pricing.model_price(self.index.embedder.model)
        )
        cost = round(math.ceil(len(probe) / 3) * price["input_per_mtok"] / 1_000_000, 8)
        if cost > max_cost_usd:
            raise BudgetExceeded("installation", cost, max_cost_usd)
        candidate_states = ("testing", "ready")  # a published version is never rewritten by a test
        try:
            self._verify_integrity(version["collection_name"], version["manifest"])
        except RuntimeError:
            outcome = {"passed": False, "hits": 0, "probe": probe, "estimated_cost_usd": 0.0}
            error = "Collection integrity could not be confirmed."
            if not self._set_version(
                version_id, "failed", error=error, test_result=outcome, from_states=candidate_states
            ):
                raise RuntimeError("Version state changed during the test.") from None
            return outcome
        index = KnowledgeIndex(self.index.client, version["collection_name"], self.index.embedder)
        result = index.search(probe, k=3)
        outcome = {"passed": bool(result), "hits": len(result), "probe": probe, "estimated_cost_usd": cost}
        if not self._set_version(
            version_id, "ready" if outcome["passed"] else "testing", test_result=outcome, from_states=candidate_states
        ):
            raise RuntimeError("Version state changed during the test.")
        return outcome

    def transition(self, version_id: str, *, action: str, expected_active: str, confirmed: bool, actor: str) -> dict:
        if action not in ("activate", "rollback") or not confirmed:
            raise ValueError("Explicit confirmation is required.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            state = conn.execute("SELECT * FROM kb_state WHERE singleton=1").fetchone()
            if state["active_version_id"] != expected_active:
                raise RuntimeError("Active version changed.")
            target = version_id
            if action == "rollback":
                target = state["previous_version_id"]
                if target != version_id or target is None:
                    raise RuntimeError("Requested version is not the previous version.")
            row = conn.execute(
                "SELECT state,collection_name,manifest FROM kb_versions WHERE version_id=?", (target,)
            ).fetchone()
            if row is None or (action == "activate" and row["state"] != "ready"):
                raise RuntimeError("Target version is not complete.")
            self._verify_integrity(row["collection_name"], json.loads(row["manifest"]))
            old = state["active_version_id"]
            conn.execute(
                "UPDATE kb_versions SET state='retired',updated_at=? WHERE version_id=? AND state='active'",
                (_now(), old),
            )
            conn.execute("UPDATE kb_versions SET state='active',updated_at=? WHERE version_id=?", (_now(), target))
            conn.execute(
                "UPDATE kb_state SET previous_version_id=?,active_version_id=?,revision=revision+1 WHERE singleton=1",
                (old, target),
            )
            conn.execute(
                "INSERT INTO kb_events(actor,action,from_version_id,to_version_id,evidence,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (actor, action, old, target, _json({"expected_active": expected_active}), _now()),
            )
            conn.execute("COMMIT")
            return {"active_version_id": target, "previous_version_id": old, "revision": state["revision"] + 1}
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def capture_active(self):
        """Return a stable index and version ID for one in-flight request."""
        self.bootstrap()
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT v.version_id,v.collection_name FROM kb_state s "
                "JOIN kb_versions v ON v.version_id=s.active_version_id WHERE s.singleton=1"
            ).fetchone()
            if row is None:
                return self.index, None
            return KnowledgeIndex(self.index.client, row["collection_name"], self.index.embedder), row["version_id"]
        finally:
            conn.close()
