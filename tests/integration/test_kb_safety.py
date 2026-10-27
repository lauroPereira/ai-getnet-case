"""Knowledge base safety: published collections are immutable and verified before any pointer change.

Synthetic only: the offline orchestrator (hashing embedder, in-memory Qdrant) and temporary SQLite databases."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import SecretStr
from qdrant_client import models

from merchant_assistant import cli
from merchant_assistant.rag import kb as kb_module
from merchant_assistant.rag.index import KnowledgeIndex

ADMIN_KEY = "synthetic-admin-access-key-v050"


def pointer(kb):
    state = kb.versions(admin=True)
    return state["active_version_id"], state["previous_version_id"], state["revision"]


def create_candidate(kb):
    estimate = kb.estimate({})
    return kb.create_version({}, estimate["active_version_id"], estimate["digest"], True, 0.0)


def build_ready(kb):
    version = create_candidate(kb)
    assert kb.test_version(version["version_id"], confirmed=True, max_cost_usd=0.0)["passed"]
    return kb.version(version["version_id"], admin=True)


def activate(kb, version_id, expected_active):
    return kb.transition(version_id, action="activate", expected_active=expected_active, confirmed=True, actor="t")


def rollback(kb, version_id, expected_active):
    return kb.transition(version_id, action="rollback", expected_active=expected_active, confirmed=True, actor="t")


def corrupt(kb, collection: str, mode: str) -> None:
    """Tamper with a collection of the in-memory Qdrant used by the test."""
    client, dim = kb.index.client, kb.index.embedder.dim
    records, _ = client.scroll(collection, limit=10_000, with_payload=True, with_vectors=True)
    if mode == "missing_point":
        client.delete(collection, points_selector=models.PointIdsList(points=[records[0].id]))
    elif mode == "foreign_point":
        client.set_payload(collection, payload={"chunk_id": "tampered"}, points=[records[0].id])
    else:
        client.delete_collection(collection)
        if mode == "empty":
            client.create_collection(
                collection, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE)
            )
        elif mode == "wrong_dimension":
            client.create_collection(
                collection, vectors_config=models.VectorParams(size=8, distance=models.Distance.COSINE)
            )
            client.upsert(
                collection,
                points=[models.PointStruct(id=r.id, vector=[0.1] * 8, payload=r.payload) for r in records],
            )
        else:
            assert mode == "dropped"


CORRUPTIONS = ["empty", "dropped", "missing_point", "foreign_point", "wrong_dimension"]


# --- R1-03: integrity is verified against the manifest before activation and rollback -----------------------------


@pytest.mark.parametrize("mode", CORRUPTIONS)
def test_activation_refuses_a_candidate_whose_collection_no_longer_matches_its_manifest(settings, offline, mode):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    version = build_ready(kb)
    before = pointer(kb)
    corrupt(kb, version["collection_name"], mode)
    with pytest.raises(RuntimeError):
        activate(kb, version["version_id"], before[0])
    assert pointer(kb) == before and kb.capture_active()[1] == before[0]
    assert kb.version(version["version_id"], admin=True)["state"] == "ready"


@pytest.mark.parametrize("mode", CORRUPTIONS)
def test_rollback_refuses_a_previous_collection_that_no_longer_matches_its_manifest(settings, offline, mode):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    initial = kb.capture_active()[1]
    version = build_ready(kb)
    activate(kb, version["version_id"], initial)
    before = pointer(kb)
    assert before[:2] == (version["version_id"], initial)
    corrupt(kb, kb.index.collection, mode)  # the configured collection is the one kb_initial preserved
    with pytest.raises(RuntimeError):
        rollback(kb, initial, version["version_id"])
    assert pointer(kb) == before and kb.capture_active()[1] == version["version_id"]


def test_valid_activation_and_rollback_still_pass_the_integrity_check(settings, offline):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    initial = kb.capture_active()[1]
    version = build_ready(kb)
    assert activate(kb, version["version_id"], initial)["active_version_id"] == version["version_id"]
    assert rollback(kb, initial, version["version_id"])["active_version_id"] == initial


def test_integrity_refusal_is_a_409_and_leaves_the_active_version_alone(settings, offline):
    settings.api_admin_access_key = SecretStr(ADMIN_KEY)
    client, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    token = client.post("/v1/sessions", json={"access_key": ADMIN_KEY}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    version = build_ready(kb)
    before = pointer(kb)
    corrupt(kb, version["collection_name"], "empty")
    response = client.post(
        f"/v1/kb/versions/{version['version_id']}/activate",
        headers=headers,
        json={"expected_active_version_id": before[0], "confirmed": True},
    )
    assert response.status_code == 409
    assert client.get("/v1/kb/versions", headers=headers).json()["active_version_id"] == before[0]


def test_testing_a_corrupted_candidate_marks_it_failed_without_a_search(settings, offline, monkeypatch):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    version = create_candidate(kb)
    corrupt(kb, version["collection_name"], "empty")

    def forbidden(self, *args, **kwargs):
        raise AssertionError("no embedding or search may run on a collection that failed its integrity check")

    monkeypatch.setattr(KnowledgeIndex, "search", forbidden)
    outcome = kb.test_version(version["version_id"], confirmed=True, max_cost_usd=0.0)
    assert outcome["passed"] is False
    stored = kb.version(version["version_id"], admin=True)
    assert stored["state"] == "failed" and stored["error"] and stored["test_result"]["passed"] is False


def test_readiness_observes_the_index_of_the_version_that_is_active_now(settings, offline):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    initial = kb.capture_active()[1]
    baseline = orchestrator.readiness()
    assert baseline["ready"] is True and baseline["index_chunks"] > 0

    version = build_ready(kb)
    activate(kb, version["version_id"], initial)
    assert orchestrator.readiness()["index_chunks"] == kb.capture_active()[0].count() > 0

    corrupt(kb, version["collection_name"], "empty")  # the original collection is still healthy
    assert kb.index.count() > 0
    degraded = orchestrator.readiness()
    assert degraded["ready"] is False and degraded["index_chunks"] == 0


# --- R1-05: testing never rewrites the state of a published version -----------------------------------------------


def test_testing_a_published_version_is_refused_and_keeps_its_state(settings, offline):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    initial = kb.capture_active()[1]
    with pytest.raises(RuntimeError):
        kb.test_version(initial, confirmed=True, max_cost_usd=0.0)
    assert kb.version(initial, admin=True)["state"] == "active"

    version = build_ready(kb)
    activate(kb, version["version_id"], initial)
    before = pointer(kb)
    for published, state in ((version["version_id"], "active"), (initial, "retired")):
        with pytest.raises(RuntimeError):
            kb.test_version(published, confirmed=True, max_cost_usd=0.0)
        assert kb.version(published, admin=True)["state"] == state
    assert pointer(kb) == before and kb.capture_active()[1] == version["version_id"]


def test_testing_a_published_version_over_the_api_is_a_409_and_changes_nothing(settings, offline):
    settings.api_admin_access_key = SecretStr(ADMIN_KEY)
    client, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    token = client.post("/v1/sessions", json={"access_key": ADMIN_KEY}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    active = kb.capture_active()[1]
    response = client.post(
        f"/v1/kb/versions/{active}/test", headers=headers, json={"confirmed": True, "max_cost_usd": 0.0}
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "version_not_testable"
    assert client.get(f"/v1/kb/versions/{active}", headers=headers).json()["state"] == "active"
    assert kb.capture_active()[1] == active


def test_activation_racing_with_a_test_is_never_overwritten(settings, offline, monkeypatch):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    initial = kb.capture_active()[1]
    version = build_ready(kb)
    original = KnowledgeIndex.search

    def search_then_activate(self, query, **kwargs):
        result = original(self, query, **kwargs)
        activate(kb, version["version_id"], initial)  # the transition wins between the test's read and its write
        return result

    monkeypatch.setattr(KnowledgeIndex, "search", search_then_activate)
    with pytest.raises(RuntimeError):
        kb.test_version(version["version_id"], confirmed=True, max_cost_usd=0.0)
    assert kb.version(version["version_id"], admin=True)["state"] == "active"
    assert pointer(kb)[:2] == (version["version_id"], initial)


# --- R1-02: a new candidate never collides with, replaces or deletes an existing collection -----------------------


def test_candidate_id_collision_is_refused_before_touching_the_existing_collection(settings, offline, monkeypatch):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    fixed = SimpleNamespace(hex="c0ffee" * 6)
    monkeypatch.setattr(kb_module, "uuid", SimpleNamespace(uuid4=lambda: fixed))
    name = f"getnet_kb_{fixed.hex[:16]}"
    kb.index.client.create_collection(name, vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE))
    kb.index.client.upsert(name, points=[models.PointStruct(id=1, vector=[1, 0, 0, 0], payload={"chunk_id": "keep"})])
    marker = KnowledgeIndex(kb.index.client, name, kb.index.embedder).inspect()
    before = pointer(kb)
    with pytest.raises(RuntimeError):
        create_candidate(kb)
    assert KnowledgeIndex(kb.index.client, name, kb.index.embedder).inspect() == marker
    assert pointer(kb) == before and len(kb.versions(admin=True)["versions"]) == 1


def test_candidate_build_never_replaces_a_collection_that_appears_during_the_build(settings, offline, monkeypatch):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    fixed = SimpleNamespace(hex="beef42" * 6)
    monkeypatch.setattr(kb_module, "uuid", SimpleNamespace(uuid4=lambda: fixed))
    name = f"getnet_kb_{fixed.hex[:16]}"
    kb.index.client.create_collection(name, vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE))
    kb.index.client.upsert(name, points=[models.PointStruct(id=1, vector=[1, 0, 0, 0], payload={"chunk_id": "keep"})])
    marker = KnowledgeIndex(kb.index.client, name, kb.index.embedder).inspect()
    monkeypatch.setattr(KnowledgeIndex, "exists", lambda self: False)  # the pre-check misses the late collection
    with pytest.raises(kb_module.KBBuildFailure):
        create_candidate(kb)
    monkeypatch.undo()
    assert KnowledgeIndex(kb.index.client, name, kb.index.embedder).inspect() == marker
    assert kb.version(f"kb_{fixed.hex[:16]}", admin=True)["state"] == "failed"
    assert kb.capture_active()[1] == "kb_initial"


def test_cli_never_rebuilds_a_collection_referenced_by_the_registry(settings, offline, monkeypatch):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    client = kb.index.client
    monkeypatch.setattr(client, "close", lambda: None)
    monkeypatch.setattr("merchant_assistant.rag.index.open_qdrant", lambda url, local_path: client)
    initial = kb.capture_active()[1]
    version = build_ready(kb)
    activate(kb, version["version_id"], initial)  # now: active = candidate, previous = kb_initial
    registry = kb.versions(admin=True)
    referenced = {item["collection_name"] for item in registry["versions"] if item["state"] in ("active", "retired")}
    assert referenced == {version["collection_name"], kb.index.collection}
    facts = {name: KnowledgeIndex(client, name, kb.index.embedder).inspect() for name in referenced}

    for name in sorted(referenced):
        target = settings.model_copy(update={"qdrant_collection": name})
        with pytest.raises(SystemExit):
            cli.cmd_index(target, SimpleNamespace(fake=True))
        with pytest.raises(SystemExit):
            cli.cmd_bootstrap(target, SimpleNamespace(force_index=True))
        assert KnowledgeIndex(client, name, kb.index.embedder).inspect() == facts[name]
    assert pointer(kb)[:2] == (version["version_id"], initial)
