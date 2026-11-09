"""Task 87 (spec v0.11.0 D1, D2, CA-60), end to end and offline: the two web-search steps write the masked search
summary and the cited URLs into the trace; `GET /v1/runs/{id}` shows them; the evaluation (never the merchant's turn)
fetches the cited pages from the in-process HTTPS server of `conftest.py` and gives them to the judge; the recorded
answers of one route are graded again with `eval --judge-repeat --only-route`. Scripted model, no network, no cost."""

from __future__ import annotations

import argparse
import json
import uuid

import pytest

from merchant_assistant import cli
from merchant_assistant import main as service
from merchant_assistant.agents.knowledge import WEB_SUMMARY_LIMIT_CHARS
from merchant_assistant.api.schemas import MessageRequest
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation import evidence
from merchant_assistant.evaluation.runner import load_cases, run, summarize, write_report
from merchant_assistant.evaluation.scripted_judge import scripted_judge
from merchant_assistant.evaluation.scripted_policy import handler as default_handler
from merchant_assistant.evaluation.web_pages import WebPages
from merchant_assistant.llm.base import NullMeter
from merchant_assistant.testing import merchant_headers

SCENARIOS = PROJECT_ROOT / "tests" / "scenarios"
GENERAL_WEB = "What's the euro exchange rate today?"  # EX07: the `knowledge` step in web mode
UNKNOWN_PRODUCT = "A maquininha Get XYZ aceita pagamento por aproximação?"  # REPLAN-WEB: the `web` step of the replan
SENSITIVE = "Contato ana@example.com, CPF 123.456.789-09."
REAL_BUILD = service.build_orchestrator  # kept before any test replaces it
REAL_FROM_SETTINGS = WebPages.from_settings.__func__


def citing(server, paths=("/page", "/gone"), extra: str = ""):
    """The scripted policy, with a web search that cites pages of the local server and returns sensitive data."""

    def handler(call):
        answer = default_handler(call)
        if call.spec.agent == "knowledge" and call.kind == "web" and isinstance(answer, dict):
            first, *rest = answer["text"].split("\n")
            answer = {
                "text": "\n".join([f"{first} {SENSITIVE}{extra}", *rest]),
                "citations": [
                    {"url": server.url(path), "title": f"Synthetic {path} (ana@example.com)"} for path in paths
                ],
            }
        return answer

    return handler


def handle(orchestrator, message):
    request_id = f"req_t87_{uuid.uuid4().hex[:12]}"
    response = orchestrator.handle(MessageRequest(message=message, user_id="cliente1988"), request_id)
    return response.model_dump(), orchestrator.trace(request_id)


def web_detail(trace, step: str) -> dict:
    [detail] = [s["detail"] for s in trace["steps"] if s["step"] == step and s["detail"].get("mode") == "web"]
    return detail


def assert_masked(detail: dict, server, paths=("/page", "/gone")) -> None:
    assert "ana@example.com" not in json.dumps(detail) and "123.456.789-09" not in json.dumps(detail)
    assert "[e-mail removed]" in detail["web_summary"] and "[CPF removed]" in detail["web_summary"]
    assert [u["url"] for u in detail["web_urls"]] == [server.url(path) for path in paths]
    assert all(u["title"].endswith("([e-mail removed])") for u in detail["web_urls"])


@pytest.fixture
def no_fetch(monkeypatch):
    """Fails the test if the page fetcher is called (the merchant's turn never fetches a page)."""

    def refuse(*args, **kwargs):
        raise AssertionError("a page was fetched during the merchant's turn")

    monkeypatch.setattr(WebPages, "fetch", refuse)
    monkeypatch.setattr(WebPages, "_fetch", refuse)


def test_both_web_steps_write_the_masked_summary_and_the_urls(offline, https_pages, no_fetch):
    _, orchestrator, _ = offline(handler=citing(https_pages))
    body, trace = handle(orchestrator, GENERAL_WEB)
    assert body["route"] == "general_web"
    knowledge = web_detail(trace, "knowledge")
    assert_masked(knowledge, https_pages)
    assert knowledge["web_summary"].startswith("1 EUR = R$ 5,57") and knowledge["web_summary_truncated"] is False

    body, trace = handle(orchestrator, UNKNOWN_PRODUCT)
    assert body["agents"] == ["router", "knowledge", "web", "personality"]
    web = web_detail(trace, "web")
    assert_masked(web, https_pages)
    assert web["web_summary"].rstrip().endswith("EVIDENCE: DIRECT")  # what the search returned, as it returned it


def test_a_long_search_summary_is_cut_and_marked(offline, https_pages):
    _, orchestrator, _ = offline(handler=citing(https_pages, extra=" filler" * 1000))
    _, trace = handle(orchestrator, GENERAL_WEB)
    detail = web_detail(trace, "knowledge")
    assert len(detail["web_summary"]) == WEB_SUMMARY_LIMIT_CHARS == 4000 and detail["web_summary_truncated"] is True


def test_the_run_endpoint_shows_the_masked_summary_and_the_turn_never_fetches_a_page(offline, https_pages, no_fetch):
    client, _, _ = offline(handler=citing(https_pages))
    headers = merchant_headers(client)
    for message, step in ((GENERAL_WEB, "knowledge"), (UNKNOWN_PRODUCT, "web")):
        payload = {"message": message, "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm"}
        sent = client.post("/v1/messages", headers=headers, json=payload)
        assert sent.status_code == 200, sent.text
        run_view = client.get(f"/v1/runs/{sent.json()['message']['request_id']}", headers=headers).json()
        [shown] = [s for s in run_view["steps"] if s["step"] == step and s.get("mode") == "web"]
        assert_masked(shown, https_pages)
        assert shown["web_summary_truncated"] is False


def web_cases():
    cases = load_cases([SCENARIOS / "challenge_examples.jsonl", SCENARIOS / "replan.jsonl"])
    return [case for case in cases if case.id in ("EX07", "REPLAN-WEB")]


def test_pages(settings, server) -> WebPages:
    """The fetcher of the evaluation, trusting the test server (127.0.0.1, so `allow_private`)."""
    return WebPages(settings.runtime_path / "web_evidence", verify=server.client_tls, allow_private=True)


test_pages.__test__ = False  # a helper, not a test


def campaign(settings, offline, https_pages, tmp_path, paths=("/page", "/gone")):
    """Two answers of the scripted agent graded by the scripted judge, with the pages fetched for the evidence."""
    _, orchestrator, _ = offline(handler=citing(https_pages, paths=paths))
    judge = scripted_judge(PROJECT_ROOT / "prompts", NullMeter())
    pages = test_pages(settings, https_pages)
    with evidence.use_web_pages(pages):
        rows = run(orchestrator, web_cases(), judge=judge)
    return rows, pages, orchestrator


def test_the_evaluation_gives_the_judge_the_cited_pages_and_reads_them_from_the_cache(
    settings, offline, https_pages, tmp_path
):
    before = dict(https_pages.hits)
    rows, pages, _ = campaign(settings, offline, https_pages, tmp_path)
    by_id = {row["id"]: row for row in rows}
    assert {row["id"] for row in rows} == {"EX07", "REPLAN-WEB"}
    for row in rows:
        given = row["judge_input"]
        page = next(item for item in given["evidence"] if item["kind"] == "web_page")
        assert (page["url"], page["title"]) == (https_pages.url("/page"), "Synthetic /page ([e-mail removed])")
        assert "1 EUR = R$ 5,57" in page["text"] and "ana@example.com" not in page["text"]
        summary = next(item for item in given["evidence"] if item["kind"] == "web_summary")  # /gone is unavailable
        assert "[e-mail removed]" in summary["text"]
        assert given["evidence_notes"] == [evidence.WEB_PAGE_NOTE, evidence.WEB_SUMMARY_NOTE]
        assert row["judge"]["state"] == "completed"
    assert by_id["EX07"]["route"] == "general_web"
    # one request per page for the two answers: the second answer and the second campaign read the cache
    assert https_pages.hits["/page"] - before.get("/page", 0) == 1 and pages.requests == 2
    hits = dict(https_pages.hits)
    campaign(settings, offline, https_pages, tmp_path)
    assert dict(https_pages.hits) == hits
    assert evidence.web_note_counts(rows) == {"answers": 2, "web_page": 2, "web_summary": 2, "no_url": 0}


def test_the_turn_never_fetches_a_page_even_inside_an_evaluation_block(settings, offline, https_pages):
    """Review P3-5: `cmd_eval` runs the turns inside `use_web_pages`; only `judge_input`, after the turn, fetches."""
    _, orchestrator, _ = offline(handler=citing(https_pages))
    pages, before = test_pages(settings, https_pages), dict(https_pages.hits)
    with evidence.use_web_pages(pages):
        for message in (GENERAL_WEB, UNKNOWN_PRODUCT):
            body, _ = handle(orchestrator, message)
            assert body["status"] == "answered"
    assert pages.requests == 0 and dict(https_pages.hits) == before


def test_a_page_with_an_odd_charset_or_a_broken_redirect_does_not_stop_the_campaign(
    settings, offline, https_pages, tmp_path
):
    """Review P2-1: the charset falls back to UTF-8; the broken Location gives the search summary instead."""
    rows, _, _ = campaign(settings, offline, https_pages, tmp_path, paths=("/bogus-charset", "/bad-location"))
    assert {row["id"] for row in rows} == {"EX07", "REPLAN-WEB"}
    for row in rows:
        given = row["judge_input"]
        web = [item for item in given["evidence"] if item["kind"].startswith("web")]  # REPLAN-WEB also has passages
        assert [item["kind"] for item in web] == ["web_page", "web_summary"]
        assert "1 EUR = R$ 5,57" in web[0]["text"]
        assert given["evidence_notes"] == [evidence.WEB_PAGE_NOTE, evidence.WEB_SUMMARY_NOTE]
        assert row["judge"]["state"] == "completed"


def test_the_report_keeps_the_old_web_note_line_only_for_answers_judged_under_it(
    settings, offline, https_pages, tmp_path
):
    """Review P2-4: with the pages fetched, the report no longer says the search text is not recorded."""
    rows, _, orchestrator = campaign(settings, offline, https_pages, tmp_path)
    summary = summarize(rows)
    assert summary["overall"]["judge_web_note"] == {"judged_answers": 2, "answers": 0, "unsupported": 0}
    md, _ = write_report(rows, summary, tmp_path / "out", "pages", {"mode": "scripted"})
    text = md.read_text(encoding="utf-8")
    assert "nota de busca web" not in text and "busca não é gravado" not in text

    judge = scripted_judge(PROJECT_ROOT / "prompts", NullMeter())
    with evidence.use_web_pages(None):  # WEB_EVIDENCE=off: the v0.10.0 note
        old = run(orchestrator, web_cases(), judge=judge)
    md, _ = write_report(old, summarize(old), tmp_path / "out", "note", {"mode": "scripted"})
    text = md.read_text(encoding="utf-8")
    assert "Respostas julgadas sob a nota de busca web: 2 de 2." in text
    assert "com ao menos um passo de busca sem URL gravada no trace (ou avaliadas com `WEB_EVIDENCE=off`)" in text


def test_an_answer_with_pages_in_one_step_and_no_url_in_another_counts_under_the_note(
    settings, offline, https_pages, tmp_path
):
    """Review round 2 P3-9: the step without a URL keeps the v0.10.0 note, so the report line describes that step."""

    fetcher = WebPages(tmp_path / "web_evidence", verify=https_pages.client_tls, allow_private=True)
    detail = {"mode": "web", "web_summary": "summary", "web_summary_truncated": False}
    cited = [{"title": "P", "url": https_pages.url("/page")}]
    trace = {
        "steps": [
            {"step": "knowledge", "status": "ok", "detail": detail | {"web_urls": cited}},
            {"step": "web", "status": "ok", "detail": detail | {"web_urls": []}},
        ]
    }
    items, notes = evidence.passage_items(trace, {}, fetcher)
    assert [item["kind"] for item in items] == ["web_page"]
    assert set(notes) == {evidence.WEB_PAGE_NOTE, evidence.WEB_NOTE}

    rows, _, _ = campaign(settings, offline, https_pages, tmp_path)
    mixed = [dict(rows[0], judge_input=dict(rows[0]["judge_input"], evidence_notes=notes)), *rows[1:]]
    summary = summarize(mixed)
    assert summary["overall"]["judge_web_note"] == {"judged_answers": 2, "answers": 1, "unsupported": 0}
    md, _ = write_report(mixed, summary, tmp_path / "out", "mixed", {"mode": "scripted"})
    text = md.read_text(encoding="utf-8")
    assert "Respostas julgadas sob a nota de busca web: 1 de 2." in text
    assert "com ao menos um passo de busca sem URL gravada no trace" in text and "desse passo o juiz" in text


def real_eval(settings, https_pages, tmp_path, monkeypatch, *, name: str) -> dict:
    """`cmd_eval` in real mode (not `--scripted`): the service's assembly (`main.build_orchestrator`) with the scripted
    model and the hashing embedder behind it, and `WebPages.from_settings` pointed at the in-process server."""
    from merchant_assistant import main
    from merchant_assistant.data.clock import FixedClock
    from merchant_assistant.data.db import connect
    from merchant_assistant.data.seed import seed
    from merchant_assistant.llm.scripted import ScriptedLLM
    from merchant_assistant.mocks.clients import in_process_client
    from merchant_assistant.rag.chunk import chunk_document
    from merchant_assistant.rag.documents import load_all
    from merchant_assistant.rag.embed import HashEmbedder
    from merchant_assistant.testing import DEFAULT_CLOCK

    root = tmp_path / "project"
    scenarios = root / "tests" / "scenarios"
    scenarios.mkdir(parents=True, exist_ok=True)
    for source, case_id in (("challenge_examples.jsonl", "EX07"), ("replan.jsonl", "REPLAN-WEB")):
        lines = (SCENARIOS / source).read_text(encoding="utf-8").splitlines()
        (scenarios / source).write_text(
            "".join(line + "\n" for line in lines if json.loads(line)["id"] == case_id), encoding="utf-8"
        )
    for empty in ("core_cases.jsonl", "business_journeys.jsonl"):
        (scenarios / empty).write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)

    real_build, built = REAL_BUILD, []

    def build(configured, **kwargs):
        clock = FixedClock(DEFAULT_CLOCK)
        llm = ScriptedLLM(citing(https_pages))
        orchestrator = real_build(configured, llm=llm, embedder=HashEmbedder(), clock=clock, **kwargs)
        orchestrator.llm_factory = lambda provider, model: llm
        orchestrator.mock_services = in_process_client()
        conn = connect(configured.db_path)
        seed(conn, clock)
        conn.close()
        orchestrator.index.rebuild([c for d in load_all(configured.data_dir) for c in chunk_document(d)])
        built.append(orchestrator)
        return orchestrator

    real_from_settings, made = REAL_FROM_SETTINGS, []

    def from_settings(cls, configured):
        pages = real_from_settings(cls, configured)
        if pages is not None:
            assert pages.allow_private is False  # as the evaluation builds it
            pages.verify, pages.allow_private = https_pages.client_tls, True  # the test server lives on 127.0.0.1
        made.append(pages)
        return pages

    monkeypatch.setattr(main, "build_orchestrator", build)
    monkeypatch.setattr(WebPages, "from_settings", classmethod(from_settings))
    values = {
        "scripted": False,
        "judge": False,
        "split": "all",
        "out": str(tmp_path / "out"),
        "name": name,
        "no_conversations": True,
        "repeat": 2,  # records the evidence without a judge (no paid judge exists in a test)
        "judge_repeat": None,
        "answers_from": None,
        "include_replan": True,
    }
    assert cli.cmd_eval(settings, argparse.Namespace(**values)) == 0
    assert len(built) == 1 and len(made) == 1
    report = json.loads((tmp_path / "out" / f"{name}.json").read_text(encoding="utf-8"))
    report["markdown"] = (tmp_path / "out" / f"{name}.md").read_text(encoding="utf-8")
    report["pages"] = made[0]
    return report


def test_cmd_eval_in_real_mode_fetches_the_cited_pages_and_reports_them(
    settings, https_pages, tmp_path, monkeypatch
):
    """Review P2-3: the wiring of `cmd_eval` itself (`WebPages.from_settings` and the report)."""
    configured = settings.model_copy(update={"budget_runtime_dir": tmp_path / "budget"})
    report = real_eval(configured, https_pages, tmp_path, monkeypatch, name="real-on")
    assert report["config"]["mode"] == "real" and report["config"]["web_evidence"] == "on"
    assert {row["id"] for row in report["cases"]} == {"EX07", "REPLAN-WEB"} and len(report["cases"]) == 4
    for row in report["cases"]:
        web = [item for item in row["judge_input"]["evidence"] if item["kind"].startswith("web")]
        assert [item["kind"] for item in web] == ["web_page", "web_summary"]
        page = web[0]
        assert page["url"] == https_pages.url("/page") and "1 EUR = R$ 5,57" in page["text"]
    assert report["pages"].requests == 2  # /page and /gone once; the other answers read the cache
    assert report["summary"]["web_evidence"] == {"answers": 4, "web_page": 4, "web_summary": 4, "no_url": 0}
    assert "## Evidência da busca web" in report["markdown"]
    assert "4 com página citada buscada na avaliação" in report["markdown"]
    assert "nota de busca web" not in report["markdown"]

    off = configured.model_copy(update={"web_evidence": "off"})
    report = real_eval(off, https_pages, tmp_path, monkeypatch, name="real-off")
    assert report["config"]["web_evidence"] == "off" and report["pages"] is None
    for row in report["cases"]:
        assert not [item for item in row["judge_input"]["evidence"] if item["kind"].startswith("web")]
        assert row["judge_input"]["evidence_notes"] == [evidence.WEB_NOTE]
    assert report["summary"]["web_evidence"] == {"answers": 4, "web_page": 0, "web_summary": 0, "no_url": 4}
    assert "## Evidência da busca web" in report["markdown"]


def test_the_recorded_web_answers_are_graded_again_by_route(settings, offline, https_pages, tmp_path, capsys):
    rows, _, _ = campaign(settings, offline, https_pages, tmp_path)
    _, report = write_report(rows, summarize(rows), tmp_path / "out", "v0110-campanha", {"mode": "scripted"})
    values = {
        "scripted": True,
        "judge": False,
        "split": "all",
        "out": str(tmp_path / "out"),
        "name": "v0110-rejulgar-web",
        "no_conversations": True,
        "repeat": 1,
        "judge_repeat": 1,
        "answers_from": str(report),
        "only_sample": None,
        "only_route": "general_web",
        "limit": None,
        "rubric": None,
    }
    assert cli.cmd_eval(settings, argparse.Namespace(**values)) == 0
    assert "grading 1 of 2 recorded answers, route general_web." in capsys.readouterr().err
    graded = json.loads((tmp_path / "out" / "v0110-rejulgar-web.json").read_text(encoding="utf-8"))
    assert [row["id"] for row in graded["cases"]] == ["EX07"]
    assert graded["config"]["only_route"] == "general_web" and graded["config"]["selected_answers"] == 1
    assert graded["summary"]["web_evidence"] == {"answers": 1, "web_page": 1, "web_summary": 1, "no_url": 0}
    text = (tmp_path / "out" / "v0110-rejulgar-web.md").read_text(encoding="utf-8")
    assert "## Evidência da busca web" in text and "1 com página citada buscada na avaliação" in text

    with pytest.raises(SystemExit, match="no recorded answer has route 'support'"):
        cli.cmd_eval(settings, argparse.Namespace(**values | {"only_route": "support", "name": "other"}))
