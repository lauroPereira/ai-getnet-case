"""CLI index commands: paid embeddings always sit behind the persistent guard and existing collections are never
rebuilt. Everything is synthetic: a fake provider transport, an in-memory Qdrant and temporary ledgers."""

from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest
from pydantic import SecretStr
from qdrant_client import QdrantClient

from merchant_assistant import cli
from merchant_assistant.config import Settings
from merchant_assistant.orchestration.budget import BudgetExceeded, BudgetGuard
from merchant_assistant.rag.chunk import chunk_document
from merchant_assistant.rag.documents import load_all
from merchant_assistant.rag.embed import HashEmbedder, OpenAIEmbedder
from merchant_assistant.rag.index import KnowledgeIndex

COMMANDS = ["index", "bootstrap", "eval-retrieval"]


class FakeOpenAI:
    """Synthetic embeddings transport. It records every call and what the ledger looked like at that moment."""

    def __init__(self, ledger=None, *, usage="ok", fail=None) -> None:
        self.embeddings = self
        self.ledger, self.usage, self.fail = ledger, usage, fail
        self.calls = 0
        self.ledger_at_call: list[tuple[int, int]] = []

    def create(self, *, model, input):  # noqa: A002 - mirrors the provider signature
        self.calls += 1
        if self.ledger is not None and self.ledger.exists():
            rows = ledger_rows(self.ledger)
            self.ledger_at_call.append((sum(r[0] == "reserved" for r in rows), sum(r[0] == "settled" for r in rows)))
        if self.fail:
            raise self.fail
        usage = {
            "ok": SimpleNamespace(total_tokens=5 * len(input)),
            "missing": None,
            "negative": SimpleNamespace(total_tokens=-1),
            "text": SimpleNamespace(total_tokens="many"),
        }[self.usage]
        return SimpleNamespace(
            usage=usage, data=[SimpleNamespace(index=i, embedding=[0.1] * 1536) for i in range(len(input))]
        )


def ledger_rows(path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT status, reserved_usd, actual_usd FROM ledger ORDER BY id").fetchall()
    finally:
        conn.close()


def make_settings(tmp_path, **overrides) -> Settings:
    values = {
        "runtime_dir": tmp_path / "runtime",
        "qdrant_url": ":memory:",
        "budget_limit_usd": 1.0,
        "openai_api_key": SecretStr("synthetic-placeholder"),
    }
    return Settings(_env_file=None, **(values | overrides))


@pytest.fixture
def qdrant(monkeypatch):
    """One in-memory Qdrant shared by every CLI call of a test; the CLI's close() must not wipe it."""
    client = QdrantClient(":memory:")
    monkeypatch.setattr(client, "close", lambda: None)
    monkeypatch.setattr("merchant_assistant.rag.index.open_qdrant", lambda url, local_path: client)
    return client


@pytest.fixture
def transport(monkeypatch, tmp_path):
    fake = FakeOpenAI(tmp_path / "runtime" / "budget.sqlite3")
    monkeypatch.setattr(cli, "_openai_client", lambda settings: fake)
    return fake


def run(command: str, settings: Settings, *, force_index: bool = False):
    if command == "index":
        return cli.cmd_index(settings, SimpleNamespace(fake=False))
    if command == "bootstrap":
        return cli.cmd_bootstrap(settings, SimpleNamespace(force_index=force_index))
    return cli.cmd_eval_retrieval(settings, SimpleNamespace(fake=False, k=6))


def some_chunks(count: int = 3):
    return [chunk for doc in load_all(Settings(_env_file=None).data_dir) for chunk in chunk_document(doc)][:count]


# --- R1-01: every paid embedding path reserves first ---------------------------------------------------------------


def test_build_embedder_refuses_a_paid_embedder_without_the_guard(monkeypatch, tmp_path):
    def forbidden(settings):
        raise AssertionError("a provider client must not be created without the persistent guard")

    monkeypatch.setattr(cli, "_openai_client", forbidden)
    with pytest.raises(SystemExit):
        cli.build_embedder(make_settings(tmp_path), fake=False, budget=None)
    assert isinstance(cli.build_embedder(make_settings(tmp_path), fake=True), HashEmbedder)


def test_openai_embedder_without_a_guard_fails_before_the_provider():
    client = FakeOpenAI()
    with pytest.raises(RuntimeError):
        OpenAIEmbedder(client, "text-embedding-3-small").embed(["synthetic text"])
    assert client.calls == 0


@pytest.mark.parametrize("usage", ["missing", "negative", "text"])
def test_unusable_usage_report_keeps_the_conservative_reservation(tmp_path, usage):
    path = tmp_path / "b.sqlite3"
    client = FakeOpenAI(usage=usage)
    embedder = OpenAIEmbedder(client, "text-embedding-3-small", budget=BudgetGuard(path, 1.0))
    assert len(embedder.embed(["synthetic text"])) == 1
    (status, reserved, actual) = ledger_rows(path)[0]
    assert status == "settled" and actual == reserved and reserved > 0
    assert embedder.tokens_used == 0 and client.calls == 1


@pytest.mark.parametrize("command", COMMANDS)
def test_cli_reserves_before_every_paid_batch_and_settles_each_reservation_once(command, qdrant, transport, tmp_path):
    settings = make_settings(tmp_path)
    run(command, settings)
    rows = ledger_rows(settings.runtime_path / "budget.sqlite3")
    assert transport.calls > 0 and len(rows) == transport.calls
    assert all(status == "settled" and actual > 0 for status, _, actual in rows)
    # At the k-th provider call exactly one reservation was open and k-1 had already settled.
    assert transport.ledger_at_call == [(1, k) for k in range(transport.calls)]


@pytest.mark.parametrize("command", COMMANDS)
def test_cli_denied_reservation_stops_before_the_provider(command, qdrant, transport, tmp_path):
    settings = make_settings(tmp_path, budget_limit_usd=0.00000001)
    with pytest.raises(BudgetExceeded):
        run(command, settings)
    assert transport.calls == 0
    assert ledger_rows(settings.runtime_path / "budget.sqlite3") == []
    assert qdrant.get_collections().collections == []


@pytest.mark.parametrize("command", COMMANDS)
def test_cli_unknown_usage_keeps_the_reservation_and_does_not_retry(command, qdrant, tmp_path, monkeypatch):
    settings = make_settings(tmp_path)
    failing = FakeOpenAI(settings.runtime_path / "budget.sqlite3", fail=TimeoutError("synthetic provider timeout"))
    monkeypatch.setattr(cli, "_openai_client", lambda s: failing)
    with pytest.raises(TimeoutError):
        run(command, settings)
    assert failing.calls == 1  # no hidden retry
    ((status, reserved, actual),) = ledger_rows(settings.runtime_path / "budget.sqlite3")
    assert status == "settled" and actual == reserved and reserved > 0
    assert qdrant.get_collections().collections == []  # a failed paid build leaves nothing behind


def test_cli_fake_embedder_needs_no_ledger_and_no_provider(qdrant, monkeypatch, tmp_path):
    def forbidden(settings):
        raise AssertionError("the offline embedder never builds a provider client")

    monkeypatch.setattr(cli, "_openai_client", forbidden)
    settings = make_settings(tmp_path)
    assert cli.cmd_index(settings, SimpleNamespace(fake=True)) == 0
    assert not (settings.runtime_path / "budget.sqlite3").exists()


# --- R1-02: the CLI never replaces or rebuilds an existing collection ----------------------------------------------


def published_collection(qdrant, settings):
    index = KnowledgeIndex(qdrant, settings.qdrant_collection, HashEmbedder())
    index.rebuild(some_chunks())
    return index, index.inspect()


@pytest.mark.parametrize("fake", [True, False])
def test_index_command_refuses_to_rebuild_an_existing_collection(fake, qdrant, transport, tmp_path):
    settings = make_settings(tmp_path)
    index, before = published_collection(qdrant, settings)
    with pytest.raises(SystemExit):
        cli.cmd_index(settings, SimpleNamespace(fake=fake))
    assert index.inspect() == before
    assert transport.calls == 0


def test_bootstrap_force_index_refuses_an_existing_collection(qdrant, transport, tmp_path):
    settings = make_settings(tmp_path)
    index, before = published_collection(qdrant, settings)
    with pytest.raises(SystemExit):
        cli.cmd_bootstrap(settings, SimpleNamespace(force_index=True))
    assert index.inspect() == before
    assert transport.calls == 0


def test_bootstrap_leaves_a_stale_existing_collection_untouched(qdrant, transport, tmp_path, capsys):
    settings = make_settings(tmp_path)
    index, before = published_collection(qdrant, settings)
    assert cli.cmd_bootstrap(settings, SimpleNamespace(force_index=False)) == 0
    assert "untouched" in capsys.readouterr().out
    assert index.inspect() == before
    assert transport.calls == 0


def test_bootstrap_is_idempotent_and_never_rebuilds_what_it_created(qdrant, transport, tmp_path, capsys):
    settings = make_settings(tmp_path)
    ledger = settings.runtime_path / "budget.sqlite3"
    assert cli.cmd_bootstrap(settings, SimpleNamespace(force_index=False)) == 0
    built = KnowledgeIndex(qdrant, settings.qdrant_collection, HashEmbedder()).inspect()
    calls, rows = transport.calls, ledger_rows(ledger)
    assert built["points"] > 0 and calls > 0

    capsys.readouterr()
    assert cli.cmd_bootstrap(settings, SimpleNamespace(force_index=False)) == 0
    assert "current; skipping" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.cmd_bootstrap(settings, SimpleNamespace(force_index=True))
    assert KnowledgeIndex(qdrant, settings.qdrant_collection, HashEmbedder()).inspect() == built
    assert transport.calls == calls and ledger_rows(ledger) == rows
