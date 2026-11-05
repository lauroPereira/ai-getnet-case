"""Task 80 (v0.9.0, D7): RETRIEVAL_MODE reaches the Knowledge agent through the active version, with fake embeddings."""

import json

import pytest

from merchant_assistant.testing import merchant_headers, offline_orchestrator

QUESTION = "Qual a diferença entre a Get Clássica e a Get Smart?"


def knowledge_hits(orchestrator, request_id):
    return next(s["detail"]["hits"] for s in orchestrator.trace(request_id)["steps"] if s["step"] == "knowledge")


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
def test_knowledge_answers_in_both_modes_with_the_configured_one(settings, mode):
    from fastapi.testclient import TestClient

    from merchant_assistant.api.app import create_app

    configured = settings.model_copy(update={"retrieval_mode": mode})
    orchestrator, _ = offline_orchestrator(configured)
    client = TestClient(create_app(orchestrator, configured))
    response = client.post(
        "/messages",
        json={"message": QUESTION, "user_id": "cliente1988"},
        headers=merchant_headers(client, "cliente1988"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["route"] == "knowledge" and body["status"] == "answered" and body["sources"]
    active, _ = orchestrator.knowledge_base.capture_active()
    assert active.mode == mode  # the per-request index keeps RETRIEVAL_MODE
    hits = knowledge_hits(orchestrator, body["request_id"])
    assert hits and any("maquininhas" in hit["doc"] for hit in hits)


# --- round 2 (review P2-3: M10 and M12) -------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
def test_production_assembly_passes_retrieval_mode_and_runtime_bm25_dir(settings, mode):
    """`main.build_orchestrator` (the service's assembly), offline: scripted model, hashing embedder, memory Qdrant."""
    from merchant_assistant import main
    from merchant_assistant.evaluation.scripted_policy import handler
    from merchant_assistant.llm.scripted import ScriptedLLM
    from merchant_assistant.rag.chunk import chunk_document
    from merchant_assistant.rag.documents import load_all
    from merchant_assistant.rag.embed import HashEmbedder

    configured = settings.model_copy(update={"retrieval_mode": mode})
    orchestrator = main.build_orchestrator(configured, llm=ScriptedLLM(handler), embedder=HashEmbedder())
    index = orchestrator.index
    assert (index.mode, index.bm25_dir) == (mode, configured.runtime_path)
    assert orchestrator.knowledge_base.index is index
    index.rebuild([c for d in load_all(configured.data_dir) for c in chunk_document(d)])
    hits = index.search("Apareceu ADQ 4-91 na maquininha, o que faço?")  # no mode: RETRIEVAL_MODE decides
    pickles = list(configured.runtime_path.glob("bm25-*.pkl"))
    if mode == "hybrid":
        assert {h.origin for h in hits} - {"dense"} and len(pickles) == 1
    else:
        assert {h.origin for h in hits} == {"dense"} and pickles == []


def test_eval_retrieval_hybrid_report_measures_the_hybrid_search(tmp_path, capsys):
    from types import SimpleNamespace

    from merchant_assistant import cli
    from merchant_assistant.config import PROJECT_ROOT, Settings
    from merchant_assistant.evaluation.retrieval import load_cases

    exact = {
        c.id for c in load_cases(PROJECT_ROOT / "tests" / "scenarios" / "retrieval.jsonl") if c.case == "EXACT-TERM"
    }
    settings = Settings(_env_file=None, openai_api_key=None, runtime_dir=tmp_path / "runtime")
    ranks, overall = {}, {}
    for mode in ("dense", "hybrid"):
        assert cli.cmd_eval_retrieval(settings, SimpleNamespace(fake=True, k=6, mode=mode)) == 0
        report = json.loads(capsys.readouterr().out)
        ranks[mode] = [row["rank"] for row in report["cases"] if row["id"] in exact]
        overall[mode] = report["overall"]
    assert len(ranks["hybrid"]) >= 3 and all(ranks["hybrid"])  # hashing embedder: reference, not proof
    assert sum(rank is None for rank in ranks["dense"]) >= 3
    assert overall["hybrid"]["mrr"] > overall["dense"]["mrr"]
