"""Task 90 (spec v0.11.0 D7, D8; CA-63, CA-64), through the command line and the service assembly, offline.

`eval-retrieval` with the control `hybrid@36` and the BM25 floor over the dev set and a synthetic sealed holdout (no
test reads the real retrieval holdout); the floor reaching the Knowledge agent; and `eval` grading the journeys by the
combined ruler, with `--rubric literal` for the earlier one. Scripted agent, scripted judge, hashing embeddings."""

from __future__ import annotations

import json
import tempfile
from types import SimpleNamespace

import pytest

from merchant_assistant import cli
from merchant_assistant.config import PROJECT_ROOT, Settings
from merchant_assistant.evaluation import retrieval
from merchant_assistant.rag.chunk import chunk_document
from merchant_assistant.rag.documents import load_all
from merchant_assistant.testing import merchant_headers, offline_orchestrator

FOUR = [("dense", "off"), ("hybrid", "off"), ("hybrid@36", "off"), ("hybrid", "on")]


def offline_settings(tmp_path, **extra) -> Settings:
    return Settings(_env_file=None, openai_api_key=None, runtime_dir=tmp_path / "runtime", **extra)


def eval_args(**extra):
    base = {"fake": True, "k": 6, "mode": None, "rerank": None, "split": "dev", "out": None, "bm25_min_score": None}
    return SimpleNamespace(**{**base, **extra})


@pytest.fixture
def synthetic_splits(tmp_path, monkeypatch):
    """The real dev set and a small synthetic sealed holdout over real chunk ids, in a temporary directory."""
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    (scenarios / retrieval.SPLITS["dev"]).write_bytes((retrieval.SCENARIOS / retrieval.SPLITS["dev"]).read_bytes())
    chunk_ids = {c.chunk_id.split("#")[0]: c.chunk_id for d in load_all(PROJECT_ROOT / "data")
                 for c in chunk_document(d)}
    adq = next(cid for doc, cid in chunk_ids.items() if doc.endswith("erro-adq-4-91"))
    pix = next(cid for doc, cid in chunk_ids.items() if doc.endswith("como-fazer-uma-venda-com-pix-na-maquininha"))
    rows = [
        {"id": "SYN-1", "language": "pt", "question": "Código ADQ 4-91 na tela", "relevant_chunks": {adq: 2}},
        {"id": "SYN-2", "language": "en", "question": "Pix sale on the card machine", "relevant_chunks": {pix: 2}},
    ]
    holdout = scenarios / retrieval.SPLITS["holdout_v090"]
    holdout.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    holdout.with_suffix(".sha256").write_text(f"{retrieval.seal_digest(holdout)}  {holdout.name}\n", encoding="utf-8")
    monkeypatch.setattr(retrieval, "SCENARIOS", scenarios)
    return holdout


# --- eval-retrieval: four modes, the floor, both splits ------------------------------------------------------------


def test_four_modes_and_the_floor_in_both_splits_with_the_rerankers_own_gain(tmp_path, capsys, synthetic_splits):
    settings, out = offline_settings(tmp_path), tmp_path / "report" / "retrieval.md"
    reports = {}
    for split in ("dev", "holdout_v090"):
        for mode, rerank in FOUR:
            args = eval_args(mode=mode, rerank=rerank, split=split, out=str(out))
            assert cli.cmd_eval_retrieval(settings, args) == 0
            reports[(split, mode, rerank)] = json.loads(capsys.readouterr().out)
        args = eval_args(mode="hybrid@36", split=split, out=str(out), bm25_min_score=0.5)
        assert cli.cmd_eval_retrieval(settings, args) == 0
        reports[(split, "floor")] = json.loads(capsys.readouterr().out)
    control = reports[("dev", "hybrid@36", "off")]
    assert (control["mode"], control["rerank"], control["bm25_min_score"]) == ("hybrid@36", False, 0.0)
    assert "bm25_dropped" not in control and "rerank_usage" not in control
    floored = reports[("dev", "floor")]
    assert floored["bm25_min_score"] == 0.5 and floored["bm25_dropped"] > 0
    assert floored["bm25_dropped"] == sum(row["bm25_dropped"] for row in floored["cases"])
    assert reports[("holdout_v090", "floor")]["holdout"]["seal"] == "ok"

    text = out.read_text(encoding="utf-8")
    configs = ("dense | — |", "hybrid | 0 |", "hybrid@36 | 0 |", "hybrid+rerank | 0 |", "hybrid@36 bm25>=0.5 | 0.5 |")
    for split in ("dev", "holdout_v090"):
        for config in configs:
            assert f"| {split} | {config}" in text, (split, config)
    assert "| Piso BM25 |" in text and "| Descartados |" in text
    gain_dev = round(
        reports[("dev", "hybrid", "on")]["overall"]["ndcg_at_k"] - control["overall"]["ndcg_at_k"], 3
    )
    assert "Ganho próprio do reranker (`hybrid+rerank` menos `hybrid@36`" in text
    gain_line = next(line for line in text.splitlines() if line.startswith("| dev | ") and line.count("|") == 5)
    assert gain_line.endswith(f"| {gain_dev:+.3f} |")
    line = next(x for x in text.splitlines() if x.startswith("Modo padrão sugerido"))
    assert "indisponível:" not in line and "RERANK=" in line and "hybrid@36" in line
    data = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert set(data["results"]["dev"]) == {"dense", "hybrid", "hybrid@36", "hybrid+rerank", "hybrid@36 bm25>=0.5"}
    assert data["results"]["dev"]["hybrid@36 bm25>=0.5"]["bm25_min_score"] == 0.5


@pytest.mark.parametrize("extra", [{"mode": "hybrid@36"}, {"mode": "hybrid", "bm25_min_score": 0.3}])
def test_fake_runs_still_refuse_the_real_holdout(tmp_path, extra):
    with pytest.raises(SystemExit, match="--fake does not run on the sealed holdout_v090"):
        cli.cmd_eval_retrieval(offline_settings(tmp_path), eval_args(split="holdout_v090", **extra))
    assert not (tmp_path / "runtime").exists()


def test_the_floor_needs_a_hybrid_mode_and_a_fraction(tmp_path):
    settings = offline_settings(tmp_path)
    with pytest.raises(SystemExit, match="use a hybrid mode"):
        cli.cmd_eval_retrieval(settings, eval_args(mode="dense", bm25_min_score=0.3))
    for wrong in (-0.1, 1.5):
        with pytest.raises(SystemExit, match="from 0 to 1"):
            cli.cmd_eval_retrieval(settings, eval_args(mode="hybrid", bm25_min_score=wrong))
    with pytest.raises(SystemExit, match="--mode hybrid"):
        cli.cmd_eval_retrieval(settings, eval_args(mode="hybrid@36", rerank="on"))


def test_the_floor_is_the_flag_only_never_the_setting(tmp_path, capsys):
    """Review P3-3: with RETRIEVAL_BM25_MIN_SCORE above 0 in the environment, the four rows of the D7 line are still
    measured without the floor; the floor is measured only when the flag asks for it."""
    settings, out = offline_settings(tmp_path, retrieval_bm25_min_score=0.5), tmp_path / "report" / "retrieval.md"
    for mode, rerank in FOUR:
        assert cli.cmd_eval_retrieval(settings, eval_args(mode=mode, rerank=rerank, out=str(out))) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["bm25_min_score"] == 0.0 and "bm25_dropped" not in report, mode
    data = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert set(data["results"]["dev"]) == {"dense", "hybrid", "hybrid@36", "hybrid+rerank"}
    assert cli.cmd_eval_retrieval(settings, eval_args(mode="hybrid", bm25_min_score=0.5)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["bm25_min_score"] == 0.5 and "bm25_dropped" in report


def test_the_parser_offers_the_control_and_the_floor(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "cmd_eval_retrieval", lambda settings, args: seen.update(vars(args)) or 0)
    argv = ["eval-retrieval", "--fake", "--mode", "hybrid@36", "--bm25-min-score", "0.4", "--split", "holdout_v090"]
    assert cli.main(argv) == 0
    assert (seen["mode"], seen["bm25_min_score"], seen["split"]) == ("hybrid@36", 0.4, "holdout_v090")


# --- the floor in the service --------------------------------------------------------------------------------------


def test_the_assembly_and_the_request_index_carry_the_floor(settings):
    from merchant_assistant import main
    from merchant_assistant.evaluation.scripted_policy import handler
    from merchant_assistant.llm.scripted import ScriptedLLM
    from merchant_assistant.rag.embed import HashEmbedder

    configured = settings.model_copy(update={"retrieval_bm25_min_score": 0.4})
    orchestrator = main.build_orchestrator(configured, llm=ScriptedLLM(handler), embedder=HashEmbedder())
    assert orchestrator.index.bm25_min_score == 0.4
    offline, _ = offline_orchestrator(configured)
    captured, _ = offline.knowledge_base.capture_active()
    assert captured.bm25_min_score == 0.4 and offline.index.bm25_min_score == 0.4


@pytest.mark.parametrize("rerank", ["on", "off"])
def test_the_knowledge_step_records_what_the_floor_dropped(settings, rerank):
    """The trace of the `knowledge` step gets `bm25_dropped` from the search notes, which the agent passes with the
    reranker on and off (adjustment 1: with explicit RERANK=off, the drop used to happen out of the trace)."""
    from fastapi.testclient import TestClient

    from merchant_assistant.api.app import create_app

    update = {"retrieval_mode": "hybrid", "rerank": rerank, "retrieval_bm25_min_score": 0.5}
    configured = settings.model_copy(update=update)
    orchestrator, _ = offline_orchestrator(configured)
    client = TestClient(create_app(orchestrator, configured))
    headers = merchant_headers(client, "cliente1988")
    message = "Apareceu ADQ 4-91 na maquininha, o que significa?"
    response = client.post("/messages", json={"message": message, "user_id": "cliente1988"}, headers=headers)
    assert response.status_code == 200, response.text
    step = next(s for s in orchestrator.trace(response.json()["request_id"])["steps"] if s["step"] == "knowledge")
    dropped = step["detail"]["bm25_dropped"]
    assert isinstance(dropped, list) and not {h["chunk_id"] for h in step["detail"]["hits"]} & set(dropped)
    assert dropped, "the floor of 0.5 drops at least one BM25-only hit of this question"
    assert ("rerank" in step["detail"]) == (rerank == "on")


def test_without_the_floor_the_knowledge_step_has_no_bm25_note(settings):
    """With the floor at 0 and reranking explicitly off, the trace has no BM25 note or reranker details."""
    from fastapi.testclient import TestClient

    from merchant_assistant.api.app import create_app

    configured = settings.model_copy(update={"retrieval_mode": "hybrid", "rerank": "off"})
    orchestrator, _ = offline_orchestrator(configured)
    client = TestClient(create_app(orchestrator, configured))
    headers = merchant_headers(client, "cliente1988")
    message = "Apareceu ADQ 4-91 na maquininha, o que significa?"
    response = client.post("/messages", json={"message": message, "user_id": "cliente1988"}, headers=headers)
    assert response.status_code == 200, response.text
    step = next(s for s in orchestrator.trace(response.json()["request_id"])["steps"] if s["step"] == "knowledge")
    assert step["detail"]["hits"] and "bm25_dropped" not in step["detail"] and "rerank" not in step["detail"]


# --- eval: the combined ruler of the journeys ---------------------------------------------------------------------

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"


def label(name: str, case_id: str) -> str:
    return next(
        line for line in (SCENARIOS / name).read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line)["id"] == case_id
    )


@pytest.fixture
def project(tmp_path, monkeypatch, settings):
    """A temporary project with one challenge example and two journeys; the scripted runtime in a known place."""
    root = tmp_path / "project"
    scenarios = root / "tests" / "scenarios"
    scenarios.mkdir(parents=True)
    (scenarios / "challenge_examples.jsonl").write_text(label("challenge_examples.jsonl", "EX01") + "\n", "utf-8")
    journeys = [label("business_journeys.jsonl", i) for i in ("V030-PRICE-CONSISTENT", "V030-CONTRACT-TERMINATION")]
    (scenarios / "business_journeys.jsonl").write_text("\n".join(journeys) + "\n", encoding="utf-8")
    for name in ("core_cases.jsonl", "replan.jsonl"):
        (scenarios / name).write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    runtime = tmp_path / "scripted-runtime"
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix="": runtime.mkdir(exist_ok=True) or str(runtime))
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    return tmp_path / "out"


def run_eval(out, name, *extra) -> tuple[dict, str]:
    assert cli.main(["eval", "--scripted", "--no-conversations", "--out", str(out), "--name", name, *extra]) == 0
    return (json.loads((out / f"{name}.json").read_text(encoding="utf-8")),
            (out / f"{name}.md").read_text(encoding="utf-8"))


def test_eval_with_a_judge_rules_by_both_halves_and_lists_the_journeys(project):
    data, text = run_eval(project, "combined", "--judge")
    assert data["config"]["ruler"] == "combined" and data["config"]["judge_config"]["rubric_version"] == "5"
    rows = {row["id"]: row for row in data["cases"]}
    for row in rows.values():
        assert row["passed"] == bool(row["deterministic"] and row["content"])
    assert "expected_claims" in rows["V030-PRICE-CONSISTENT"] and "expected_claims" not in rows["EX01"]
    assert {"deterministic", "content"} <= set(data["summary"]["overall"])
    assert "## Jornadas (régua combinada)" in text and "| Determinístico | Conteúdo (juiz) |" in text
    assert "jornadas aprovadas." in text and "V030-CONTRACT-TERMINATION" in text


def test_eval_rubric_literal_keeps_the_earlier_ruler_with_the_default_judge(project):
    data, text = run_eval(project, "literal", "--judge", "--rubric", "literal")
    assert data["config"]["ruler"] == "literal" and data["config"]["judge_config"]["rubric_version"] == "5"
    for row in data["cases"]:
        assert "deterministic" not in row and row["passed"] == all(row[k] for k in cli_check_keys())
        assert "expected_claims" not in row  # review P3-2: the literal JSON is the one of before task 90
    assert "Determinístico" not in text and "## Jornadas" not in text
    plain, _ = run_eval(project, "no-judge")
    assert plain["config"]["ruler"] == "literal" and "deterministic" not in plain["cases"][0]
    assert not any("expected_claims" in row for row in plain["cases"])


def test_rejudged_answers_follow_the_ruler_and_get_the_journey_claims(project, capsys):
    source, _ = run_eval(project, "source", "--judge", "--rubric", "literal")
    for row in source["cases"]:
        row.pop("expected_claims", None)  # as recorded before task 90
    path = project / "source.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    common = ["eval", "--scripted", "--judge-repeat", "1", "--answers-from", str(path), "--out", str(project)]
    assert cli.main([*common, "--name", "again"]) == 0
    again = json.loads((project / "again.json").read_text(encoding="utf-8"))
    assert again["config"]["ruler"] == "combined"
    rows = {row["id"]: row for row in again["cases"]}
    assert rows["V030-PRICE-CONSISTENT"]["expected_claims"] and "deterministic" in rows["EX01"]
    assert cli.main([*common, "--name", "again-literal", "--rubric", "literal"]) == 0
    literal = json.loads((project / "again-literal.json").read_text(encoding="utf-8"))
    assert literal["config"]["ruler"] == "literal" and all("deterministic" not in r for r in literal["cases"])
    assert not any("expected_claims" in row for row in literal["cases"])


def cli_check_keys():
    from merchant_assistant.evaluation.runner import CHECK_KEYS

    return CHECK_KEYS
