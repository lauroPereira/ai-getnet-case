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


def test_fake_runs_refuse_the_real_holdout(tmp_path):
    """Review P3-11: offline (the BM25 half is real) it would show holdout results outside the measurement; refused
    before the file is opened. The synthetic holdouts of these tests are elsewhere and still run."""
    with pytest.raises(SystemExit, match="--fake does not run on the sealed holdout_v090"):
        cli.cmd_eval_retrieval(offline_settings(tmp_path), eval_args(split="holdout_v090"))
    assert not (tmp_path / "runtime").exists()


class Unpaid:
    """OpenAI client stand-in that must never be called."""

    @property
    def responses(self):
        raise AssertionError("no model call in this test")


def test_paid_reranker_of_eval_retrieval_has_the_cap_per_run(tmp_path, monkeypatch):
    """Review P2-3 (C2): the paid eval-retrieval reranker goes through the project ledger with a US$0.05 cap per run;
    past the cap the meter refuses (and the reranker counts a failure). No call is made."""
    from merchant_assistant.llm.base import Usage
    from merchant_assistant.orchestration.budget import BudgetExceeded, BudgetGuard

    monkeypatch.setattr(cli, "_openai_client", lambda settings: Unpaid())
    settings = offline_settings(tmp_path)
    budget = BudgetGuard(tmp_path / "budget.sqlite3", 1.0)
    reranker, meter = cli._retrieval_reranker(settings, fake=False, budget=budget)
    assert reranker.llm.model == settings.agent_model and cli.RERANK_EVAL_CAP_USD == 0.05
    call = {"agent": "rerank", "model": settings.agent_model, "est_input_tokens": 4000, "max_output_tokens": 150}
    spent = 0
    while True:
        try:
            reservation = meter.reserve(**call)
        except BudgetExceeded as exc:
            assert exc.scope == "evaluation"
            break
        meter.settle(reservation, Usage(input_tokens=4000, output_tokens=150))
        spent += 1
        assert spent < 10_000, "no cap"
    assert 0.04 < meter.summary()["cost_usd"] <= 0.05 and meter.calls == spent
    assert 0.04 < budget.spent() <= 0.05  # every reranker call reached the project ledger


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


def ask(settings, handler=None, *, with_trace: bool = False):
    from fastapi.testclient import TestClient

    from merchant_assistant.api.app import create_app

    orchestrator, llm = offline_orchestrator(settings, handler=handler)
    client = TestClient(create_app(orchestrator, settings))
    headers = merchant_headers(client, "cliente1988")
    response = client.post("/messages", json={"message": QUESTION, "user_id": "cliente1988"}, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    trace = orchestrator.trace(body["request_id"])
    step = next(s for s in trace["steps"] if s["step"] == "knowledge")
    return (body, step["detail"], llm, trace) if with_trace else (body, step["detail"], llm)


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
    assert detail["hits"] == plain["hits"]  # review P2-1: the whole top k of RERANK=off, scores included


def test_the_knowledge_reranker_is_metered_by_the_request(settings):
    """Review P2-3 (K2): the reranker call goes through the request's Meter, so it counts in max_model_calls, in the
    request cost and in the ledger; with a NullMeter it would be a paid call outside every guard."""
    import sqlite3

    on, plain = (
        ask(settings.model_copy(update={"retrieval_mode": "hybrid", **extra}), with_trace=True)
        for extra in ({"rerank": "on"}, {})
    )
    (body, _, llm, trace), (_, _, plain_llm, plain_trace) = on, plain
    assert trace["model_calls"] == len(llm.calls) == len(plain_llm.calls) + 1 == plain_trace["model_calls"] + 1
    assert trace["detail"]["models_by_agent"]["rerank"]["calls"] == 1  # the request's usage_by_agent
    with sqlite3.connect(settings.runtime_path / "budget.sqlite3") as conn:
        agents = [a for (a,) in conn.execute("SELECT agent FROM ledger WHERE request_id = ?", (body["request_id"],))]
    assert agents.count("rerank") == 1


def test_rerank_off_by_default_makes_no_call(settings):
    _, detail, llm = ask(settings.model_copy(update={"retrieval_mode": "hybrid"}))
    assert "rerank" not in detail and "rerank" not in [c.spec.agent for c in llm.calls]
