from pathlib import Path

import pytest

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.orchestration.budget import BudgetExceeded, BudgetGuard
from merchant_assistant.rag.chunk import chunk_document
from merchant_assistant.rag.collect import clean_text
from merchant_assistant.rag.documents import Document, load_all, slug_for
from merchant_assistant.rag.embed import HashEmbedder, OpenAIEmbedder
from merchant_assistant.rag.index import KnowledgeIndex, open_qdrant

DATA = PROJECT_ROOT / "data"


def test_clean_text_removes_site_boilerplate():
    raw = "Título\n" + "Conteúdo útil. " * 20 + "\nRespondeu à sua dúvida?\nSim\nNão\nFale já"
    cleaned = clean_text(raw)
    assert "Respondeu" not in cleaned and cleaned.startswith("Título")


def test_slug_is_stable():
    assert slug_for("https://site.getnet.com.br/pix/") == "site-getnet-com-br-pix"


def test_corpus_loads_public_and_demo_documents():
    docs = load_all(DATA)
    kinds = {d.source_kind for d in docs}
    assert kinds == {"public_official", "simulated_internal"}
    assert any(d.url == "https://www.getnet.net/en/" for d in docs)
    demo = [d for d in docs if d.source_kind == "simulated_internal"]
    assert all(d.metadata["procedure_id"].startswith("KB-DEMO-") for d in demo)


def test_chunks_keep_metadata_and_size():
    doc = Document(
        "demo:X",
        "Doc X",
        "## A\n" + "linha de texto\n" * 200 + "## B\nfim do documento aqui",
        "simulated_internal",
        metadata={"procedure_id": "KB-X", "version": "1"},
    )
    chunks = chunk_document(doc, max_chars=500, overlap=50)
    assert len(chunks) > 2
    assert all(len(c.text) <= 520 + len(doc.title) for c in chunks)
    assert all(
        c.payload()["procedure_id"] == "KB-X" and c.payload()["source_kind"] == "simulated_internal" for c in chunks
    )
    assert len({c.chunk_id for c in chunks}) == len(chunks)


@pytest.fixture(scope="module")
def index():
    idx = KnowledgeIndex(open_qdrant(":memory:", Path(".")), "test", HashEmbedder())
    idx.rebuild([c for d in load_all(DATA) for c in chunk_document(d)])
    return idx


def test_index_search_and_filter(index):
    hits = index.search("Em quantas parcelas posso vender no crediário?", k=3)
    assert any("crediario" in h.payload["doc_id"] for h in hits)
    demo_only = index.search("transação negada código de resposta", k=3, source_kinds=["simulated_internal"])
    assert demo_only and all(h.payload["source_kind"] == "simulated_internal" for h in demo_only)


def test_candidate_rebuild_refuses_existing_collection_without_replacing_it():
    client = open_qdrant(":memory:", Path("."))
    protected = KnowledgeIndex(client, "protected", HashEmbedder())
    chunks = [chunk_document(load_all(DATA)[-1])[0]]
    protected.rebuild(chunks)
    before = protected.count()
    try:
        protected.rebuild([], replace_existing=False)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected candidate collection collision")
    assert protected.count() == before


def test_rebuild_never_replaces_an_existing_collection_unless_asked_explicitly():  # R1-02
    client = open_qdrant(":memory:", Path("."))
    index = KnowledgeIndex(client, "published", HashEmbedder())
    chunks = [chunk_document(load_all(DATA)[-1])[0]]
    index.rebuild(chunks)
    before = index.inspect()
    with pytest.raises(RuntimeError):
        index.rebuild(chunks)  # the default is to refuse
    with pytest.raises(RuntimeError):
        index.rebuild([], replace_existing=False)
    assert index.inspect() == before


def test_failed_embedding_creates_no_collection():  # R1-02
    class Failing:
        model, dim = "synthetic-failing", 8

        def embed(self, texts):
            raise TimeoutError("synthetic provider timeout")

    client = open_qdrant(":memory:", Path("."))
    index = KnowledgeIndex(client, "never_created", Failing())
    with pytest.raises(TimeoutError):
        index.rebuild([chunk_document(load_all(DATA)[-1])[0]])
    assert not index.exists() and client.get_collections().collections == []


def test_inspect_reports_read_only_facts_that_match_the_manifest():  # R1-03
    from merchant_assistant.rag.index import point_digest

    client = open_qdrant(":memory:", Path("."))
    index = KnowledgeIndex(client, "facts", HashEmbedder())
    chunks = [c for d in load_all(DATA)[:4] for c in chunk_document(d)]
    manifest = index.rebuild(chunks)
    assert index.inspect() == {
        "dim": HashEmbedder().dim,
        "points": len(chunks),
        "point_digest": manifest["point_digest"],
    }
    assert manifest["point_digest"] == point_digest(c.chunk_id for c in reversed(chunks))
    assert KnowledgeIndex(client, "absent", HashEmbedder()).inspect() is None


def test_min_score_filters_irrelevant(index):
    assert index.search("zzz qqq xyzzy", k=3, min_score=0.5) == []


def test_embedding_budget_is_reserved_before_provider_and_settled_once(tmp_path):
    class Embeddings:
        calls = 0

        def create(self, **_):
            self.calls += 1
            from types import SimpleNamespace

            return SimpleNamespace(
                usage=SimpleNamespace(total_tokens=3),
                data=[SimpleNamespace(index=0, embedding=[0.1] * 1536)],
            )

    class Client:
        embeddings = Embeddings()

    denied_budget = BudgetGuard(tmp_path / "denied.sqlite3", 0.00000001)
    embedder = OpenAIEmbedder(Client(), "text-embedding-3-small", budget=denied_budget)
    try:
        embedder.embed(["x" * 900])
    except BudgetExceeded:
        pass
    else:
        raise AssertionError("expected reservation to be denied")
    assert embedder.client.embeddings.calls == 0

    allowed_budget = BudgetGuard(tmp_path / "allowed.sqlite3", 1.0)
    embedder = OpenAIEmbedder(Client(), "text-embedding-3-small", budget=allowed_budget)
    embedder.embed(["short synthetic probe"])
    conn = __import__("sqlite3").connect(tmp_path / "allowed.sqlite3")
    rows = conn.execute("SELECT status, actual_usd FROM ledger").fetchall()
    conn.close()
    assert len(rows) == 1 and rows[0][0] == "settled" and rows[0][1] == 0.00000006

    class FailedEmbeddings:
        calls = 0

        def create(self, **_):
            self.calls += 1
            raise TimeoutError("synthetic provider timeout")

    class FailedClient:
        embeddings = FailedEmbeddings()

    failed_budget = BudgetGuard(tmp_path / "failed.sqlite3", 1.0)
    failed = OpenAIEmbedder(FailedClient(), "text-embedding-3-small", budget=failed_budget)
    with pytest.raises(TimeoutError):
        failed.embed(["short synthetic probe"])
    failed_conn = __import__("sqlite3").connect(tmp_path / "failed.sqlite3")
    failed_row = failed_conn.execute("SELECT status, reserved_usd, actual_usd FROM ledger").fetchone()
    failed_conn.close()
    assert failed.client.embeddings.calls == 1
    assert failed_row[0] == "settled" and failed_row[1] == failed_row[2]
