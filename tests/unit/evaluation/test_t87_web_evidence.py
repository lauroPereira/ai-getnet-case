"""Task 87 (spec v0.11.0 D2, CA-60): the pages a web-search reply cited, fetched for the judge's evidence.

The fetcher runs against the in-process HTTPS server of `conftest.py` (`https_pages`); nothing leaves the machine."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import socket
import tomllib
from types import SimpleNamespace

import pytest

from merchant_assistant.agents.knowledge import WEB_SUMMARY_LIMIT_CHARS, _note_web_search
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.evaluation import evidence
from merchant_assistant.evaluation.web_pages import PageText, Unavailable, WebPages, _is_global, cache_key
from merchant_assistant.rag.collect import extract_text

BODY = {"status": "answered", "route": "general_web", "answer": "1 EUR = R$ 5,57 today."}
# judge.v3.md and judge.v4.md as v0.10.0 shipped them (LF line endings): task 87 describes the new items in
# `evidence_notes`, never in the rubric.
PROMPT_SHA256 = {
    "judge.v3.md": "45d59f0cfebacd6b19cbf7c20532e8d8d409404f77d423e0a2e25216f75152bd",
    "judge.v4.md": "7c416d5d6b3845f7c3ffac9d1cc085a301d7e46ca88ecb7e9a56dea7e5e32e3c",
}


def pages(tmp_path, server, **kwargs) -> WebPages:
    """A fetcher that trusts the test server: it lives on 127.0.0.1, so it needs `allow_private`."""
    return WebPages(tmp_path / "web_evidence", verify=server.client_tls, **{"allow_private": True} | kwargs)


def cached(tmp_path, url: str) -> bool:
    return (tmp_path / "web_evidence" / f"{cache_key(url)}.json").exists()


def web_trace(urls: list[dict], summary: str = "1 EUR = R$ 5,57 (Example FX).", step: str = "knowledge") -> dict:
    detail = {"mode": "web", "web_summary": summary, "web_summary_truncated": False, "web_urls": urls}
    return {"steps": [{"step": step, "status": "ok", "detail": detail}]}


class Stub:
    """A fetcher with fixed answers, for the evidence rules (the real one is tested against the server)."""

    def __init__(self, answers: dict) -> None:
        self.answers, self.asked = answers, []

    def fetch(self, url: str):
        self.asked.append(url)
        return self.answers[url]


def page(url: str, text: str, title: str = "Page title") -> PageText:
    return PageText(url, title, text, False, "2026-11-06T10:00:00+00:00")


def gone(url: str) -> Unavailable:
    return Unavailable(url, "http_error", "2026-11-06T10:00:00+00:00", 500)


# --- the fetcher -----------------------------------------------------------------------------------------------------


def test_an_https_page_is_extracted_masked_and_cached_and_the_cache_is_read_first(tmp_path, https_pages):
    fetcher, url = pages(tmp_path, https_pages), https_pages.url("/page")
    before = https_pages.hits["/page"]
    first = fetcher.fetch(url)
    assert isinstance(first, PageText) and not first.cached and first.title == "Synthetic FX page"
    assert "1 EUR = R$ 5,57" in first.text
    assert "ana@example.com" not in first.text and "[e-mail removed]" in first.text  # masked before it is kept
    record = json.loads((tmp_path / "web_evidence" / f"{cache_key(url)}.json").read_text(encoding="utf-8"))
    assert cache_key(url) == hashlib.sha256(url.encode()).hexdigest()
    assert record["status"] == "ok" and record["fetched_at"] and record["text"] == first.text
    assert record["truncated"] is False and record["url"] == url and record["http_status"] == 200

    again = fetcher.fetch(url)
    other = pages(tmp_path, https_pages).fetch(url)  # another evaluation over the same runtime directory
    assert again.cached and other.cached and again.text == first.text == other.text
    assert https_pages.hits["/page"] == before + 1 and fetcher.requests == 1  # one request for three fetches


def test_a_missing_page_and_a_redirect_to_another_host_are_unavailable_and_cached(tmp_path, https_pages):
    fetcher = pages(tmp_path, https_pages)
    gone = fetcher.fetch(https_pages.url("/gone"))
    away = fetcher.fetch(https_pages.url("/away"))
    assert isinstance(gone, Unavailable) and (gone.reason, gone.http_status) == ("http_error", 404)
    assert isinstance(away, Unavailable) and (away.reason, away.http_status) == ("redirect_to_other_domain", 302)
    for url in (https_pages.url("/gone"), https_pages.url("/away")):
        record = json.loads((tmp_path / "web_evidence" / f"{cache_key(url)}.json").read_text(encoding="utf-8"))
        assert record["status"] == "unavailable" and record["text"] == "" and record["fetched_at"]
    hits = dict(https_pages.hits)
    assert fetcher.fetch(https_pages.url("/away")).cached and dict(https_pages.hits) == hits  # not asked again


def test_a_429_or_a_5xx_is_unavailable_but_not_cached(tmp_path, https_pages):
    """Review P3-1: a busy or failing server says nothing lasting about the page."""
    fetcher = pages(tmp_path, https_pages)
    for path, status in (("/error", 500), ("/busy", 429)):
        url, before = https_pages.url(path), https_pages.hits[path]
        first, again = fetcher.fetch(url), fetcher.fetch(url)
        assert (first.reason, first.http_status) == ("http_error", status) and not again.cached
        assert not cached(tmp_path, url) and https_pages.hits[path] == before + 2


def test_a_redirect_inside_the_same_host_is_followed(tmp_path, https_pages):
    result = pages(tmp_path, https_pages).fetch(https_pages.url("/same"))
    assert isinstance(result, PageText) and result.title == "Synthetic FX page"


def test_only_https_is_fetched(tmp_path, https_pages):
    plain = https_pages.url("/page").replace("https://", "http://")
    before = dict(https_pages.hits)
    result = pages(tmp_path, https_pages).fetch(plain)
    assert isinstance(result, Unavailable) and result.reason == "not_https"
    assert dict(https_pages.hits) == before  # refused before any request
    assert pages(tmp_path, https_pages).fetch("not a url").reason in ("not_https", "invalid_url")


def test_the_byte_cap_the_content_type_and_plain_text(tmp_path, https_pages):
    fetcher = pages(tmp_path, https_pages, max_bytes=2048)
    big = fetcher.fetch(https_pages.url("/big"))
    assert isinstance(big, PageText) and big.truncated and len(big.text) <= 2048
    pdf = fetcher.fetch(https_pages.url("/pdf"))
    assert isinstance(pdf, Unavailable) and pdf.reason == "unsupported_content_type"
    plain = fetcher.fetch(https_pages.url("/plain"))
    assert isinstance(plain, PageText) and plain.text == "Plain synthetic text: 1 EUR = R$ 5,57."


def test_a_timeout_is_not_cached_so_the_page_is_tried_again(tmp_path, https_pages):
    fetcher = pages(tmp_path, https_pages, timeout_seconds=0.2)
    url = https_pages.url("/slow")
    result = fetcher.fetch(url)
    assert isinstance(result, Unavailable) and result.reason == "timeout"
    assert not (tmp_path / "web_evidence" / f"{cache_key(url)}.json").exists()


def test_the_timeout_bounds_the_whole_page_not_only_each_read(tmp_path, https_pages):
    """Review P3-2: /drip sends 16 bytes every 0.15 s, each read well inside 0.3 s, the page in about a second."""
    fetcher = pages(tmp_path, https_pages, timeout_seconds=0.3)
    url = https_pages.url("/drip")
    result = fetcher.fetch(url)
    assert isinstance(result, Unavailable) and result.reason == "timeout" and not cached(tmp_path, url)


def test_a_compressed_body_is_refused_and_identity_is_asked(tmp_path, https_pages):
    """Review P3-2: the byte cap counts what the server sends, so nothing is decompressed."""
    fetcher = pages(tmp_path, https_pages)
    result = fetcher.fetch(https_pages.url("/gzip"))
    assert isinstance(result, Unavailable) and result.reason == "unsupported_content_encoding"
    fetcher.fetch(https_pages.url("/plain"))
    assert https_pages.accept_encoding["/gzip"] == https_pages.accept_encoding["/plain"] == "identity"


# --- review P2-1: a page never stops the evaluation ------------------------------------------------------------------


def test_an_unknown_charset_falls_back_to_utf8(tmp_path, https_pages):
    result = pages(tmp_path, https_pages).fetch(https_pages.url("/bogus-charset"))
    assert isinstance(result, PageText) and result.title == "Odd charset page" and "1 EUR = R$ 5,57" in result.text


def test_a_malformed_location_is_an_unavailable_page(tmp_path, https_pages):
    url = https_pages.url("/bad-location")
    result = pages(tmp_path, https_pages).fetch(url)
    assert isinstance(result, Unavailable) and (result.reason, result.http_status) == ("invalid_redirect", 302)
    assert cached(tmp_path, url)  # the header will not change by asking again


def test_a_location_httpx_refuses_is_an_invalid_redirect_cached_not_a_network_error(tmp_path, https_pages):
    """Review round 2 P3-8: httpx raises RemoteProtocolError on `https://127.0.0.1:abc/x` before handing it over."""
    url = https_pages.url("/bad-port-location")
    fetcher = pages(tmp_path, https_pages)
    result = fetcher.fetch(url)
    assert isinstance(result, Unavailable) and (result.reason, result.http_status) == ("invalid_redirect", 302)
    assert cached(tmp_path, url) and fetcher.fetch(url).cached and https_pages.hits["/bad-port-location"] == 1


def test_a_url_with_a_lone_surrogate_is_unavailable_and_does_not_raise(tmp_path, https_pages, monkeypatch):
    """Review round 2 P3-6: neither the cache key nor the cache file can encode it; the fetch still returns."""

    def no_connection(*args, **kwargs):
        raise AssertionError("connected")

    monkeypatch.setattr(socket, "create_connection", no_connection)
    url = "https://example.com/" + chr(0xD800)
    fetcher = guarded(tmp_path, https_pages)
    first, again = fetcher.fetch(url), fetcher.fetch(url)
    assert isinstance(first, Unavailable) and first.url == url and not first.cached and not again.cached
    assert not list(tmp_path.glob("web_evidence/*.json"))  # nothing written


def test_any_unexpected_error_is_an_unavailable_page_tried_again_later(tmp_path, https_pages, monkeypatch):
    def broken(self, *args):
        raise RuntimeError("a defect while reading the page")

    monkeypatch.setattr(WebPages, "_page", broken)
    url = https_pages.url("/plain")
    result = pages(tmp_path, https_pages).fetch(url)
    assert isinstance(result, Unavailable) and result.reason == "fetch_failed" and not cached(tmp_path, url)
    trace = web_trace([{"title": "Plain", "url": url}], summary="the summary")
    items, notes = evidence.passage_items(trace, {}, pages(tmp_path, https_pages))
    assert [i["kind"] for i in items] == ["web_summary"] and notes == [evidence.WEB_SUMMARY_NOTE]


# --- review P2-2: no internal address ------------------------------------------------------------------------------


def guarded(tmp_path, server) -> WebPages:
    """The fetcher as `from_settings` builds it: internal addresses refused."""
    return WebPages(tmp_path / "web_evidence", verify=server.client_tls)


@pytest.mark.parametrize(
    "url",
    [
        "https://10.255.255.1/",  # private
        "https://192.168.0.10/admin",  # private
        "https://169.254.169.254/latest/meta-data/",  # link-local (cloud metadata)
        "https://[::1]/",  # IPv6 loopback
        "https://[::ffff:127.0.0.1]/",  # IPv4-mapped loopback
        "https://0.0.0.0/",  # unspecified
        "https://[::127.0.0.1]/",  # IPv4-compatible loopback (review round 2 P3-7)
        "https://[64:ff9b::7f00:1]/",  # NAT64 of 127.0.0.1
        "https://[64:ff9b::a9fe:a9fe]/",  # NAT64 of 169.254.169.254
    ],
)
def test_internal_address_literals_are_refused_before_any_connection(tmp_path, https_pages, url, monkeypatch):
    def no_connection(*args, **kwargs):
        raise AssertionError("connected to an internal address")

    monkeypatch.setattr(socket, "create_connection", no_connection)
    result = guarded(tmp_path, https_pages).fetch(url)
    assert isinstance(result, Unavailable) and result.reason == "internal_address" and cached(tmp_path, url)


@pytest.mark.parametrize(
    ("address", "is_global"),
    [
        ("::127.0.0.1", False),
        ("64:ff9b::7f00:1", False),
        ("64:ff9b::a00:1", False),  # 10.0.0.1
        ("64:ff9b::808:808", True),  # NAT64 of 8.8.8.8: a public address stays allowed
        ("2606:4700::1111", True),  # outside both prefixes: what `ipaddress` says
    ],
)
def test_an_ipv6_address_carrying_an_ipv4_one_is_judged_by_the_ipv4(address, is_global):
    assert _is_global(address) is is_global


def test_the_loopback_test_server_is_refused_without_allow_private(tmp_path, https_pages, settings):
    url, before = https_pages.url("/plain"), dict(https_pages.hits)
    result = guarded(tmp_path, https_pages).fetch(url)
    assert isinstance(result, Unavailable) and result.reason == "internal_address"
    assert dict(https_pages.hits) == before  # refused before the request
    assert WebPages.from_settings(settings).allow_private is False  # the evaluation never allows it


def test_a_name_is_resolved_and_refused_when_any_address_is_internal(tmp_path, https_pages, monkeypatch):
    answers = {"intranet.example": ["10.0.0.7"], "mixed.example": ["93.184.216.34", "127.0.0.1"]}

    def resolve(host, port, *args, **kwargs):
        if host not in answers:
            raise socket.gaierror(socket.EAI_NONAME, "unknown name")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port)) for address in answers[host]]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    fetcher = guarded(tmp_path, https_pages)
    assert fetcher.fetch("https://intranet.example/page").reason == "internal_address"
    assert fetcher.fetch("https://mixed.example/page").reason == "internal_address"
    unknown = fetcher.fetch("https://unknown.example/page")
    assert unknown.reason == "unresolved_host" and not cached(tmp_path, "https://unknown.example/page")


def test_every_redirect_is_checked_again_before_it_is_requested(tmp_path, https_pages):
    """The first request is allowed and the redirect is refused: each hop is resolved and checked on its own."""

    class FirstHopOnly(WebPages):
        checks = 0

        @property
        def allow_private(self):
            FirstHopOnly.checks += 1
            return FirstHopOnly.checks == 1

        @allow_private.setter
        def allow_private(self, value):
            pass

    before = https_pages.hits["/page"]
    result = FirstHopOnly(tmp_path / "web_evidence", verify=https_pages.client_tls).fetch(https_pages.url("/same"))
    assert isinstance(result, Unavailable) and result.reason == "internal_address"
    assert FirstHopOnly.checks == 2 and https_pages.hits["/page"] == before  # the redirect target was not asked


def test_a_redirect_to_another_port_of_the_same_host_is_not_followed(tmp_path, https_pages):
    result = pages(tmp_path, https_pages).fetch(https_pages.url("/other-port"))
    assert isinstance(result, Unavailable) and (result.reason, result.http_status) == ("redirect_to_other_domain", 302)


def test_the_settings_turn_the_fetcher_on_or_off(settings):
    on = WebPages.from_settings(settings)
    assert settings.web_evidence == "on" and on is not None
    assert on.cache_dir == settings.runtime_path / "web_evidence"
    assert (on.timeout_seconds, on.max_bytes) == (10.0, 2 * 1024 * 1024)
    tuned = settings.model_copy(update={"web_evidence_timeout_seconds": 3.0, "web_evidence_max_bytes": 4096})
    assert (WebPages.from_settings(tuned).timeout_seconds, WebPages.from_settings(tuned).max_bytes) == (3.0, 4096)
    assert WebPages.from_settings(settings.model_copy(update={"web_evidence": "off"})) is None


# --- the evidence ----------------------------------------------------------------------------------------------------


def test_each_fetched_page_is_a_web_page_item_with_title_and_url():
    url = "https://fx.example/eur"
    stub = Stub({url: page(url, "1 EUR = R$ 5,57. Contact ana@example.com", title="FX page title")})
    trace = web_trace([{"title": "Example FX", "url": url}])
    with evidence.use_web_pages(stub):
        data, truncation = evidence.judge_input("What's the euro rate?", BODY, ["Example FX"], [], trace, {})
    [item] = data["evidence"]
    assert item["kind"] == "web_page" and (item["title"], item["url"]) == ("Example FX", url)
    assert item["label"] == "Example FX"  # the calibration CSV reads the label of every item
    assert "[e-mail removed]" in item["text"] and "ana@example.com" not in item["text"]
    assert data["evidence_notes"] == [evidence.WEB_PAGE_NOTE] and not truncation["truncated"]


def test_a_long_page_is_cut_within_the_common_limit():
    url = "https://fx.example/long"
    stub = Stub({url: page(url, "rate " * 3000)})
    with evidence.use_web_pages(stub):
        data, truncation = evidence.judge_input("q", BODY, [], [], web_trace([{"title": "Long", "url": url}]), {})
    [item] = data["evidence"]
    assert item["kind"] == "web_page" and item.get("cut") and item["text"].endswith(evidence.CUT_MARK)
    assert truncation["truncated"] and truncation["kept_chars"] <= evidence.EVIDENCE_LIMIT_CHARS


def test_an_unavailable_page_gives_the_search_summary_instead_with_its_note():
    ok, broken = "https://fx.example/ok", "https://fx.example/broken"
    stub = Stub({ok: page(ok, "page text"), broken: gone(broken)})
    trace = web_trace([{"title": "OK", "url": ok}, {"title": "Broken", "url": broken}], summary="summary ana@x.io")
    items, notes = evidence.passage_items(trace, {}, stub)
    assert [i["kind"] for i in items] == ["web_page", "web_summary"]
    assert items[1]["text"] == "summary [e-mail removed]" and items[1]["label"] == evidence.WEB_SUMMARY_LABEL
    assert notes == [evidence.WEB_PAGE_NOTE, evidence.WEB_SUMMARY_NOTE]
    assert evidence.WEB_SUMMARY_NOTE.startswith(
        "page unavailable; the search summary written by the assistant is given instead, it is not a page"
    )

    only_broken = web_trace([{"title": "Broken", "url": broken}])
    items, notes = evidence.passage_items(only_broken, {}, stub)
    assert [i["kind"] for i in items] == ["web_summary"] and notes == [evidence.WEB_SUMMARY_NOTE]


def test_without_urls_or_with_web_evidence_off_the_note_stays_as_in_v0100():
    url = "https://fx.example/eur"
    stub = Stub({url: page(url, "text")})
    no_urls = web_trace([])
    assert evidence.passage_items(no_urls, {}, stub) == ([], [evidence.WEB_NOTE])
    with_urls = web_trace([{"title": "Example FX", "url": url}])
    assert evidence.passage_items(with_urls, {}, None) == ([], [evidence.WEB_NOTE])  # WEB_EVIDENCE=off
    with evidence.use_web_pages(None):
        data, _ = evidence.judge_input("q", BODY, [], [], with_urls, {})
    assert data["evidence"] == [] and data["evidence_notes"] == [evidence.WEB_NOTE]
    assert stub.asked == []


def test_the_fetcher_of_a_block_is_removed_when_it_ends_even_on_an_error():
    """Review P3-4: the ContextVar is restored, nested or not, so nothing fetches after the evaluation."""
    outer, inner = Stub({}), Stub({})
    assert evidence._WEB_PAGES.get() is None
    with evidence.use_web_pages(outer):
        with evidence.use_web_pages(inner):
            assert evidence._WEB_PAGES.get() is inner
        assert evidence._WEB_PAGES.get() is outer
    assert evidence._WEB_PAGES.get() is None
    with pytest.raises(RuntimeError), evidence.use_web_pages(outer):
        raise RuntimeError("the run failed")
    assert evidence._WEB_PAGES.get() is None


def test_outside_an_evaluation_block_nothing_is_fetched(monkeypatch):
    def refuse(self, url):
        raise AssertionError("fetched outside use_web_pages")

    monkeypatch.setattr(WebPages, "fetch", refuse)
    trace = web_trace([{"title": "Example FX", "url": "https://fx.example/eur"}])
    data, _ = evidence.judge_input("q", BODY, [], [], trace, {})
    assert data["evidence_notes"] == [evidence.WEB_NOTE]


def test_a_url_cited_by_two_steps_is_fetched_once():
    url = "https://fx.example/eur"
    stub = Stub({url: page(url, "text")})
    first, second = web_trace([{"title": "A", "url": url}]), web_trace([{"title": "A", "url": url}], step="web")
    items, _ = evidence.passage_items({"steps": first["steps"] + second["steps"]}, {}, stub)
    assert [i["kind"] for i in items] == ["web_page"] and stub.asked == [url]


def test_the_report_counts_answers_by_form_of_the_note():
    rows = [
        {"judge_input": {"evidence_notes": [evidence.WEB_PAGE_NOTE]}},
        {"judge_input": {"evidence_notes": [evidence.WEB_PAGE_NOTE, evidence.WEB_SUMMARY_NOTE]}},
        {"judge_input": {"evidence_notes": [evidence.WEB_NOTE]}},
        {"judge_input": {"evidence_notes": []}},
        {"id": "no evidence recorded"},
    ]
    counts = evidence.web_note_counts(rows)
    assert counts == {"answers": 4, "web_page": 2, "web_summary": 1, "no_url": 1}
    assert "2 com página citada" in evidence.web_note_line(counts)


@pytest.mark.parametrize(
    ("chars", "truncated"), [(WEB_SUMMARY_LIMIT_CHARS, False), (WEB_SUMMARY_LIMIT_CHARS + 1, True)]
)
def test_the_search_summary_is_marked_cut_only_past_the_limit(chars, truncated):
    """Review P3-3: 4 000 characters fit; 4 001 are cut to 4 000 and marked."""
    ctx = SimpleNamespace(step_notes={})
    _note_web_search(ctx, "a" * chars, [])
    assert len(ctx.step_notes["web_summary"]) == WEB_SUMMARY_LIMIT_CHARS == 4000
    assert ctx.step_notes["web_summary_truncated"] is truncated


@pytest.mark.parametrize("name", sorted(PROMPT_SHA256))
def test_the_judge_rubrics_v3_and_v4_are_untouched(name):
    raw = (PROJECT_ROOT / "prompts" / name).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == PROMPT_SHA256[name]


def test_the_image_installs_the_extractor_the_web_evidence_uses():
    """Task 91: inside the container `eval` reads the cited pages with `rag.collect.extract_text`, whose libraries
    come with the `ingest` extra; without it every HTML page would be `extractor_unavailable`."""
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r'/venv/bin/pip install "\.\[ingest\]"', dockerfile), "the image does not install the extra"
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requirements = pyproject["project"]["optional-dependencies"]["ingest"]
    extra = {re.split(r"[<>=!~;\[ ]", requirement, maxsplit=1)[0].lower() for requirement in requirements}
    source = inspect.getsource(extract_text)
    assert "import trafilatura" in source and "from bs4 import BeautifulSoup" in source
    assert {"trafilatura", "beautifulsoup4"} <= extra
