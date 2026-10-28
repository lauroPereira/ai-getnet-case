"""v0.6.0 stabilization (task 54): regressions for the R2 review findings and the exposure controls.

Synthetic only: temporary ledgers and SQLite files, in-memory Qdrant, fake API keys and no network."""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
from pathlib import Path

import pytest
from pydantic import SecretStr
from qdrant_client import models

from merchant_assistant.config import PROJECT_ROOT, Settings
from merchant_assistant.orchestration.budget import BudgetGuard, FixedBudgetGuard

# --- R2-01: the persistent ceiling is written with an exact representation ----------------------------------------


@pytest.mark.parametrize("limit", [1 / 3, 0.1 + 0.2, 0.123456789012345])
def test_first_mount_accepts_its_own_ceiling_and_remounts_with_the_same_value(tmp_path, limit):
    path = tmp_path / "ledger.sqlite3"
    first = BudgetGuard(path, limit)
    assert float(Path(f"{path}.limit").read_text(encoding="ascii").strip()) == limit
    again = BudgetGuard(path, limit)
    assert first.limit_usd == again.limit_usd == limit
    with pytest.raises(ValueError):
        BudgetGuard(path, limit + 1e-9)  # still cannot be raised by remounting


# --- R2-02: the ceiling file is published atomically ---------------------------------------------------------------


def test_concurrent_first_mounts_never_see_a_partial_ceiling(tmp_path):
    failures: list[str] = []
    for round_number in range(40):
        path = tmp_path / f"ledger-{round_number}.sqlite3"
        barrier = threading.Barrier(8)

        def mount(path=path, barrier=barrier):
            barrier.wait()
            try:
                BudgetGuard(path, 0.75)
            except Exception as exc:  # every failure is a regression
                failures.append(f"{type(exc).__name__}: {exc}")

        threads = [threading.Thread(target=mount) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert Path(f"{path}.limit").read_text(encoding="ascii").strip() == repr(0.75)
    assert failures == []
    assert not [item for item in tmp_path.iterdir() if item.name.endswith(".tmp")]


def test_an_existing_ceiling_is_never_overwritten(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    BudgetGuard(path, 0.4)
    BudgetGuard(path, 0.2)  # a stricter mount keeps the recorded ceiling
    assert float(Path(f"{path}.limit").read_text(encoding="ascii").strip()) == 0.4


# --- campaign cap of the approved v0.6.0 plan (v060-qa, USD 0.50) --------------------------------------------------


def test_campaign_cap_accepts_the_approved_half_dollar_once(tmp_path):
    path = tmp_path / "campaign.sqlite3"
    guard = FixedBudgetGuard(path, 0.5, cap_id="v060-qa")
    assert guard.guard.limit_usd == 0.5
    with pytest.raises(ValueError):
        FixedBudgetGuard(path, 0.25, cap_id="v060-qa")
    with pytest.raises(ValueError):
        FixedBudgetGuard(tmp_path / "other.sqlite3", 0.5000001, cap_id="v060-qa")


# --- R2-03: readiness and capture are read-only once the registry exists -------------------------------------------


def test_capture_and_readiness_do_not_need_the_write_lock_after_registration(settings, offline):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    kb.bootstrap()  # the first initialization writes the registry once
    holder = sqlite3.connect(settings.db_path, isolation_level=None, timeout=1)
    holder.execute("BEGIN IMMEDIATE")  # another writer (for example an activation) holds the write lock
    try:
        started = time.perf_counter()
        _, version_id = kb.capture_active()
        ready = orchestrator.readiness()
        elapsed = time.perf_counter() - started
    finally:
        holder.execute("ROLLBACK")
        holder.close()
    assert version_id == "kb_initial"
    assert ready["ready"] is True and ready["index_chunks"] > 0
    assert elapsed < 3  # before the fix each call waited for busy_timeout (5 s) and then failed


def test_first_readiness_still_registers_documents_and_initial_version_once(settings, offline):
    _, orchestrator, _ = offline()
    conn = sqlite3.connect(settings.db_path)
    assert conn.execute("SELECT COUNT(*) FROM kb_versions").fetchone()[0] == 0
    conn.close()
    orchestrator.readiness()
    orchestrator.readiness()
    conn = sqlite3.connect(settings.db_path)
    counts = [conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("kb_versions", "kb_events")]
    documents = conn.execute("SELECT COUNT(*) FROM kb_documents").fetchone()[0]
    conn.close()
    assert counts == [1, 1] and documents > 0


# --- R2-05 / R2-08a: real clients have explicit timeouts and no SDK retries (no network) ---------------------------


def test_real_provider_clients_disable_sdk_retries_and_set_explicit_timeouts():
    from merchant_assistant import cli, main

    settings = Settings(
        _env_file=None,
        openai_api_key=SecretStr("sk-synthetic-not-a-key"),
        deepseek_api_key=SecretStr("sk-synthetic-not-a-key"),
    )
    for client in (main.openai_client(settings), main.deepseek_client(settings), cli._openai_client(settings)):
        assert client.max_retries == 0
        assert client.timeout == 30
    assert str(main.deepseek_client(settings).base_url).startswith("https://api.deepseek.com")


def test_deepseek_client_requires_its_key():
    from merchant_assistant import main

    with pytest.raises(RuntimeError):
        main.deepseek_client(Settings(_env_file=None, deepseek_api_key=None))


# --- R2-07: no ledger entry can bypass the reservation ------------------------------------------------------------


def test_budget_guard_has_no_direct_spending_entry_points():
    assert not hasattr(BudgetGuard, "record")
    assert not hasattr(BudgetGuard, "record_embedding")


# --- R2-08b: a legacy manifest without counts never activates an empty collection --------------------------------


def _ready_candidate(kb):
    estimate = kb.estimate({})
    version = kb.create_version({}, estimate["active_version_id"], estimate["digest"], True, 0.0)
    assert kb.test_version(version["version_id"], confirmed=True, max_cost_usd=0.0)["passed"]
    return kb.version(version["version_id"], admin=True)


def _legacy_manifest_and_empty_collection(kb, settings, version_id, collection):
    conn = sqlite3.connect(settings.db_path)
    legacy = {
        "collection": collection,
        "embedding_model": kb.index.embedder.model,
        "dim": kb.index.embedder.dim,
        "source": "pre-v0.5-preserved",
    }
    conn.execute("UPDATE kb_versions SET manifest=? WHERE version_id=?", (json.dumps(legacy), version_id))
    conn.commit()
    conn.close()
    kb.index.client.delete_collection(collection)
    kb.index.client.create_collection(
        collection, vectors_config=models.VectorParams(size=kb.index.embedder.dim, distance=models.Distance.COSINE)
    )


def test_activation_with_legacy_manifest_and_empty_collection_is_refused(settings, offline):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    candidate = _ready_candidate(kb)
    _legacy_manifest_and_empty_collection(kb, settings, candidate["version_id"], candidate["collection_name"])
    with pytest.raises(RuntimeError, match="integrity"):
        kb.transition(
            candidate["version_id"], action="activate", expected_active="kb_initial", confirmed=True, actor="t"
        )
    assert kb.capture_active()[1] == "kb_initial"


def test_rollback_to_legacy_manifest_with_empty_collection_is_refused(settings, offline):
    _, orchestrator, _ = offline()
    kb = orchestrator.knowledge_base
    candidate = _ready_candidate(kb)
    kb.transition(candidate["version_id"], action="activate", expected_active="kb_initial", confirmed=True, actor="t")
    _legacy_manifest_and_empty_collection(kb, settings, "kb_initial", kb.index.collection)
    with pytest.raises(RuntimeError, match="integrity"):
        kb.transition(
            "kb_initial", action="rollback", expected_active=candidate["version_id"], confirmed=True, actor="t"
        )
    assert kb.capture_active()[1] == candidate["version_id"]


# --- exposure: the packaged API listens only on the loopback interface of the host --------------------------------


def test_compose_publishes_the_api_only_on_loopback():
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    before_api, api_section = compose.split("\n  api:", 1)
    ports = api_section.split("ports:", 1)[1].split("env_file:", 1)[0]
    assert re.findall(r'- "([^"]+)"', ports) == ["127.0.0.1:8000:8000"]
    assert "ports:" not in before_api  # qdrant and mocks stay internal
