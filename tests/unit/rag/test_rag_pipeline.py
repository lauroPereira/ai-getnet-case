from pathlib import Path

import pytest

from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.rag.chunk import chunk_document
from merchant_assistant.rag.collect import clean_text
from merchant_assistant.rag.documents import Document, load_all, slug_for
from merchant_assistant.rag.embed import HashEmbedder
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


def test_min_score_filters_irrelevant(index):
    assert index.search("zzz qqq xyzzy", k=3, min_score=0.5) == []
