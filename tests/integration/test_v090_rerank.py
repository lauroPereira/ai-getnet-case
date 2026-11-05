"""Task 81 (v0.9.0, D7, D8, CA-52): `eval-retrieval --mode --rerank --split` offline (hashing embeddings, programmed
reranker, memory Qdrant), RERANK reaching the Knowledge agent, and the holdout seal checked before any paid call.

The holdout split is exercised over a synthetic sealed set in a temporary directory: no test here reads the real
retrieval holdout."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from merchant_assistant import cli
from merchant_assistant.config import Settings
from merchant_assistant.evaluation import retrieval
from merchant_assistant.llm.base import LLMError
from merchant_assistant.rag.chunk import chunk_document
from merchant_assistant.rag.documents import load_all
from merchant_assistant.testing import merchant_headers, offline_orchestrator

CONFIGS = [("dense", "off"), ("hybrid", "off"), ("hybrid", "on")]


def offline_settings(tmp_path, **extra) -> Settings:
    return Settings(_env_file=None, openai_api_key=None, runtime_dir=tmp_path / "runtime", **extra)


def eval_args(**extra):
    base = {"fake": True, "k": 6, "mode": None, "rerank": None, "split": "dev", "out": None}
    return SimpleNamespace(**{**base, **extra})


@pytest.fixture
def synthetic_splits(tmp_path, monkeypatch):
    """A temporary scenarios directory: the real dev set and a small synthetic sealed holdout over real chunk ids."""
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    (scenarios / retrieval.SPLITS["dev"]).write_bytes((retrieval.SCENARIOS / retrieval.SPLITS["dev"]).read_bytes())
    chunk_ids = {c.chunk_id.split("#")[0]: c.chunk_id for d in load_all(Settings(_env_file=None).data_dir)
                 for c in chunk_document(d)}
    adq = next(cid for doc, cid in chunk_ids.items() if doc.endswith("erro-adq-4-91"))
    pix = next(cid for doc, cid in chunk_ids.items() if doc.endswith("como-fazer-uma-venda-com-pix-na-maquininha"))
    rows = [
        {"id": "SYN-1", "category": "exact_term", "language": "pt", "question": "Código ADQ 4-91 na tela",
         "relevant_chunks": {adq: 2}},
        {"id": "SYN-2", "category": "procedure", "language": "en", "question": "Pix sale on the card machine",
         "relevant_chunks": {pix: 2}},
    ]
    holdout = scenarios / retrieval.SPLITS["holdout_v090"]
    holdout.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    holdout.with_suffix(".sha256").write_text(f"{retrieval.seal_digest(holdout)}  {holdout.name}\n", encoding="utf-8")
    monkeypatch.setattr(retrieval, "SCENARIOS", scenarios)
    return holdout


def test_three_configurations_and_two_splits_offline_with_the_d7_line(tmp_path, capsys, synthetic_splits):
    settings, out = offline_settings(tmp_path), tmp_path / "report" / "retrieval.md"
    reports = {}
    for split in ("dev", "holdout_v090"):
        for mode, rerank in CONFIGS:
            assert cli.cmd_eval_retrieval(settings, eval_args(mode=mode, rerank=rerank, split=split, out=str(out))) == 0
            reports[(split, mode, rerank)] = json.loads(capsys.readouterr().out)
    for (split, mode, rerank), report in reports.items():
        assert (report["split"], report["mode"], report["rerank"]) == (split, mode, rerank == "on")
        overall = report["overall"]
        assert {"recall_at_k", "mrr", "ndcg_at_k", "mean_ms"} <= set(overall) and overall["mean_ms"] > 0
        assert report["embedding_model"] == "hash-embedder-v1" and report["embedding_tokens"] == 0
        assert ("holdout" in report) == (split == "holdout_v090")
        if rerank == "on":  # one programmed, metered call per question
            assert report["rerank_usage"]["calls"] == overall["n"] and report["rerank_failures"] == 0
            assert all(row["rerank"] == "ok" for row in report["cases"])
    assert reports[("holdout_v090", "dense", "off")]["holdout"] == {
        "split": "holdout_v090", "sha256": retrieval.seal_digest(synthetic_splits), "seal": "ok", "used": True,
    }
    assert reports[("dev", "dense", "off")]["overall"]["n"] == 19
    assert reports[("holdout_v090", "hybrid", "on")]["overall"]["n"] == 2
    # the measured mode really is the one reported (hybrid finds exact terms the hashing dense misses)
    dev_dense, dev_hybrid = reports[("dev", "dense", "off")], reports[("dev", "hybrid", "off")]
    assert [r["rank"] for r in dev_dense["cases"]] != [r["rank"] for r in dev_hybrid["cases"]]
    text = out.read_text(encoding="utf-8")
    for split in ("dev", "holdout_v090"):
        for config in ("dense", "hybrid", "hybrid+rerank"):
            assert f"| {split} | {config} |" in text
    assert "Holdout de retrieval: usado, lacre" in text and "Embeddings de hash" in text
    line = next(x for x in text.splitlines() if x.startswith("Modo padrão sugerido"))
    assert "RETRIEVAL_MODE=" in line and "RERANK=" in line and "indisponível" not in line
    data = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert set(data["results"]) == {"dev", "holdout_v090"} and data["results"]["holdout_v090"]["dense"]["runs"] == 1


def test_holdout_measured_again_is_marked_already_seen(tmp_path, capsys, synthetic_splits):
    settings, out = offline_settings(tmp_path), tmp_path / "retrieval.md"
    for _ in range(2):
        assert cli.cmd_eval_retrieval(settings, eval_args(mode="hybrid", split="holdout_v090", out=str(out))) == 0
    capsys.readouterr()
    assert "| holdout_v090 | hybrid | 2 |" in out.read_text(encoding="utf-8")
    assert "2 (holdout já visto)" in out.read_text(encoding="utf-8")


def test_holdout_with_a_broken_seal_is_refused_before_any_paid_call(tmp_path, synthetic_splits):
    synthetic_splits.write_text(synthetic_splits.read_text(encoding="utf-8") + "\n{}\n", encoding="utf-8")
    settings = offline_settings(tmp_path)  # no key: a paid path would stop on OPENAI_API_KEY instead
    with pytest.raises(SystemExit, match="sealed sha256"):
        cli.cmd_eval_retrieval(settings, eval_args(fake=False, split="holdout_v090"))
    synthetic_splits.with_suffix(".sha256").unlink()
    with pytest.raises(SystemExit, match="seal .* not found"):
        cli.cmd_eval_retrieval(settings, eval_args(split="holdout_v090"))
    assert not (tmp_path / "runtime" / "budget.sqlite3").exists()


def test_rerank_needs_hybrid_in_the_cli_and_in_settings(tmp_path):
    with pytest.raises(SystemExit, match="--mode hybrid"):
        cli.cmd_eval_retrieval(offline_settings(tmp_path), eval_args(mode="dense", rerank="on"))
    with pytest.raises(ValidationError, match="RERANK=on requires RETRIEVAL_MODE=hybrid"):
        offline_settings(tmp_path, rerank="on")
    assert offline_settings(tmp_path).rerank == "off"
    assert offline_settings(tmp_path, rerank="on", retrieval_mode="hybrid").rerank == "on"


def test_the_parser_offers_split_rerank_and_out(monkeypatch):
    parser_args = {}

    def capture(settings, args):
        parser_args.update(vars(args))
        return 0

    monkeypatch.setattr(cli, "cmd_eval_retrieval", capture)
    argv = ["eval-retrieval", "--fake", "--mode", "hybrid", "--rerank", "on", "--split", "holdout_v090"]
    assert cli.main([*argv, "--out", "docs/evidence/x.md"]) == 0
    assert (parser_args["mode"], parser_args["rerank"], parser_args["split"]) == ("hybrid", "on", "holdout_v090")
    assert parser_args["out"] == "docs/evidence/x.md"


# --- RERANK reaches the Knowledge agent ------------------------------------------------------------------------------

QUESTION = "Apareceu ADQ 4-91 na maquininha, o que significa?"


def ask(settings, handler=None):
    from fastapi.testclient import TestClient

    from merchant_assistant.api.app import create_app

    orchestrator, llm = offline_orchestrator(settings, handler=handler)
    client = TestClient(create_app(orchestrator, settings))
    headers = merchant_headers(client, "cliente1988")
    response = client.post("/messages", json={"message": QUESTION, "user_id": "cliente1988"}, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    step = next(s for s in orchestrator.trace(body["request_id"])["steps"] if s["step"] == "knowledge")
    return body, step["detail"], llm


def test_knowledge_reranks_when_rerank_is_on(settings):
    configured = settings.model_copy(update={"retrieval_mode": "hybrid", "rerank": "on"})
    body, detail, llm = ask(configured)
    assert body["route"] == "knowledge" and body["status"] == "answered"
    assert detail["rerank"]["status"] == "ok" and detail["rerank"]["prompt"] == "rerank@1"
    assert [c.spec.agent for c in llm.calls].count("rerank") == 1
    assert len(detail["hits"]) == configured.retrieval_top_k


def test_knowledge_keeps_the_fusion_order_when_the_reranker_fails(settings):
    from merchant_assistant.evaluation.scripted_policy import handler as default

    def failing(call):
        return LLMError("rerank provider down") if call.spec.agent == "rerank" else default(call)

    configured = settings.model_copy(update={"retrieval_mode": "hybrid", "rerank": "on"})
    body, detail, _ = ask(configured, failing)
    _, plain, _ = ask(settings.model_copy(update={"retrieval_mode": "hybrid"}))
    assert body["status"] == "answered" and detail["rerank"]["status"] == "failed"
    assert "rerank provider down" in detail["rerank"]["error"]
    assert [h["chunk_id"] for h in detail["hits"]][:3] == [h["chunk_id"] for h in plain["hits"]][:3]


def test_rerank_off_by_default_makes_no_call(settings):
    _, detail, llm = ask(settings.model_copy(update={"retrieval_mode": "hybrid"}))
    assert "rerank" not in detail and "rerank" not in [c.spec.agent for c in llm.calls]
