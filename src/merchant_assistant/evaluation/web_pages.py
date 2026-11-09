"""Text of the pages a web-search reply cited, fetched at evaluation time only (spec v0.11.0 D2, task 87).

Never called while the assistant answers a merchant: only the evaluation builds the judge's evidence, after the reply,
and `evidence.use_web_pages` is the one way in. Only https; no redirect to another host; a timeout and a byte cap;
the text goes through the extractor of the snapshots (`rag.collect.extract_text`) and the input mask. Every definitive
outcome (page, HTTP error, refused redirect...) is cached in `<runtime>/web_evidence/<sha256(url)>.json` and read
before any request, so a later judgement sees the same page; a timeout, a connection error, a 429 or a 5xx is not.

The cited URLs come from the web search, content the project does not control (task 87 review P2-2): the host of the
first request and of every redirect is resolved first, and any address that is not global (loopback, private,
link-local, reserved...) is refused (`internal_address`); a redirect must keep the host and the port. Known limit: the
HTTP client resolves the name again when it connects, so a DNS answer that changes between the two lookups
(rebinding) is not caught. A page never stops the evaluation: any unexpected error is an unavailable page."""

from __future__ import annotations

import contextlib
import hashlib
import ipaddress
import json
import socket
import ssl
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx

from merchant_assistant.guardrails.input import mask_sensitive

USER_AGENT = "ai-getnet-case-evaluation/0.1 (+https://github.com/lauroPereira/ai-getnet-case)"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
HTML_TYPES = ("text/html", "application/xhtml+xml")
TEXT_TYPES = (*HTML_TYPES, "text/plain")
# not cached, tried again next time: they say nothing lasting about the page (a missing extractor is fixed by
# installing it); a 429 or a 5xx is not cached either (`_transient`)
TRANSIENT_REASONS = ("timeout", "network_error", "unresolved_host", "fetch_failed", "extractor_unavailable")
# IPv4-compatible (::a.b.c.d) and NAT64 (64:ff9b::a.b.c.d, RFC 6052): judged by the IPv4 address they carry
EMBEDDED_IPV4 = (ipaddress.ip_network("::/96"), ipaddress.ip_network("64:ff9b::/96"))


@dataclass(frozen=True)
class PageText:
    url: str
    title: str
    text: str  # masked
    truncated: bool  # the body passed the byte cap and was read up to it
    fetched_at: str
    http_status: int = 200
    cached: bool = False


@dataclass(frozen=True)
class Unavailable:
    url: str
    reason: str  # not_https, internal_address, http_error, redirect_to_other_domain, invalid_redirect, timeout, ...
    fetched_at: str
    http_status: int | None = None
    cached: bool = False


def cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _origin(url: str) -> tuple[str, int]:
    """Host (without `www.`) and port: a redirect is followed only when both stay the same."""
    parsed = httpx.URL(url)
    return (parsed.host or "").lower().removeprefix("www."), parsed.port or 443


def _is_global(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])  # an IPv6 scope (fe80::1%12) is not part of the address
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    elif ip.version == 6 and any(ip in network for network in EMBEDDED_IPV4):
        ip = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip.is_global


def _decode(body: bytes, charset: str | None) -> str:
    """The body as text; a charset Python does not know (or that is not a text encoding) falls back to UTF-8."""
    try:
        return body.decode(charset or "utf-8", errors="replace")
    except (LookupError, TypeError, ValueError):
        return body.decode("utf-8", errors="replace")


def _transient(result: PageText | Unavailable) -> bool:
    if not isinstance(result, Unavailable):
        return False
    if result.reason == "http_error":
        return result.http_status == 429 or (result.http_status or 0) >= 500
    return result.reason in TRANSIENT_REASONS


def _masked(text: str) -> str:
    return mask_sensitive(text)[0]


class WebPages:
    def __init__(
        self,
        cache_dir: Path,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_bytes: int = DEFAULT_MAX_BYTES,
        verify: bool | ssl.SSLContext = True,
        allow_private: bool = False,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.timeout_seconds = timeout_seconds  # per network operation, and for the whole page
        self.max_bytes = max_bytes
        self.verify = verify
        # only the in-process test server on 127.0.0.1 needs it; `from_settings` never sets it
        self.allow_private = allow_private
        self.requests = 0  # pages actually requested (not served by the cache)

    @classmethod
    def from_settings(cls, settings) -> WebPages | None:
        """None when WEB_EVIDENCE=off: the evidence keeps the note of v0.10.0."""
        if settings.web_evidence != "on":
            return None
        return cls(
            settings.runtime_path / "web_evidence",
            timeout_seconds=settings.web_evidence_timeout_seconds,
            max_bytes=settings.web_evidence_max_bytes,
        )

    def fetch(self, url: str) -> PageText | Unavailable:
        cached = self._read_cache(url)
        if cached is not None:
            return cached
        self.requests += 1
        result = self._fetch(url)
        if not _transient(result):
            # a URL the cache cannot encode (a lone surrogate) or a full disk: the result is returned, not cached
            with contextlib.suppress(OSError, ValueError):
                self._write_cache(result)
        return result

    # --- cache ---------------------------------------------------------------------------------------------------

    def _path(self, url: str) -> Path:
        return self.cache_dir / f"{cache_key(url)}.json"

    def _read_cache(self, url: str) -> PageText | Unavailable | None:
        try:
            record = json.loads(self._path(url).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(record, dict) or record.get("url") != url:
            return None
        common = {"url": url, "fetched_at": record.get("fetched_at", ""), "cached": True}
        if record.get("status") == "ok":
            return PageText(
                title=record.get("title") or "",
                text=record.get("text") or "",
                truncated=bool(record.get("truncated")),
                http_status=record.get("http_status") or 200,
                **common,
            )
        reason = record.get("reason") or "unavailable"
        return Unavailable(reason=reason, http_status=record.get("http_status"), **common)

    def _write_cache(self, result: PageText | Unavailable) -> None:
        record = asdict(result)
        record.pop("cached")
        if isinstance(result, PageText):
            record |= {"status": "ok", "reason": None}
        else:
            record |= {"status": "unavailable", "title": "", "text": "", "truncated": False}
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._path(result.url).write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")

    # --- request -------------------------------------------------------------------------------------------------

    def _fetch(self, url: str) -> PageText | Unavailable:
        now = _now()
        try:
            return self._request(url, now)
        except httpx.TimeoutException:
            return Unavailable(url, "timeout", now)
        except (httpx.HTTPError, OSError):
            return Unavailable(url, "network_error", now)
        except Exception:  # whatever a page or a header does, it is that page's problem, never the campaign's
            return Unavailable(url, "fetch_failed", now)

    def _request(self, url: str, now: str) -> PageText | Unavailable:
        try:
            if httpx.URL(url).scheme != "https":
                return Unavailable(url, "not_https", now)
            origin = _origin(url)
        except (httpx.InvalidURL, TypeError, ValueError):
            return Unavailable(url, "invalid_url", now)
        deadline = time.monotonic() + self.timeout_seconds
        # identity: the byte cap counts what the server sends, never a body inflated after it is read
        headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
        seen: list[httpx.Response] = []  # the response of this hop, as httpx received it
        with httpx.Client(
            headers=headers,
            timeout=self.timeout_seconds,
            follow_redirects=False,
            verify=self.verify,
            event_hooks={"response": [seen.append]},
        ) as client:
            current = url
            for _ in range(MAX_REDIRECTS + 1):
                refused = self._refused_address(url, current, now)
                if refused is not None:
                    return refused
                if time.monotonic() > deadline:
                    return Unavailable(url, "timeout", now)
                seen.clear()
                try:
                    with client.stream("GET", current) as response:
                        if response.is_redirect:
                            try:
                                target = urljoin(current, response.headers.get("location", ""))
                                same = httpx.URL(target).scheme == "https" and _origin(target) == origin
                            except (httpx.InvalidURL, TypeError, ValueError):
                                return Unavailable(url, "invalid_redirect", now, response.status_code)
                            if not same:
                                return Unavailable(url, "redirect_to_other_domain", now, response.status_code)
                            current = target
                            continue
                        return self._page(url, response, now, deadline)
                except httpx.RemoteProtocolError:
                    # httpx parses the Location of a redirect before it hands the response over; one it cannot parse
                    # (`https://127.0.0.1:abc/x`) raises there: the header is broken, not the network
                    if seen and seen[-1].is_redirect:
                        return Unavailable(url, "invalid_redirect", now, seen[-1].status_code)
                    raise
            return Unavailable(url, "too_many_redirects", now)

    def _refused_address(self, url: str, current: str, now: str) -> Unavailable | None:
        """Resolves the host of `current` before it is requested; refuses it when any address is not global."""
        target = httpx.URL(current)
        try:
            infos = socket.getaddrinfo(target.host, target.port or 443, type=socket.SOCK_STREAM)
        except (OSError, UnicodeError):
            return Unavailable(url, "unresolved_host", now)
        addresses = {info[4][0] for info in infos}
        if not addresses:
            return Unavailable(url, "unresolved_host", now)
        if not self.allow_private and not all(_is_global(address) for address in addresses):
            return Unavailable(url, "internal_address", now)
        return None

    def _page(self, url: str, response: httpx.Response, now: str, deadline: float) -> PageText | Unavailable:
        if response.status_code != 200:
            return Unavailable(url, "http_error", now, response.status_code)
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type not in TEXT_TYPES:
            return Unavailable(url, "unsupported_content_type", now, response.status_code)
        if response.headers.get("content-encoding", "identity").strip().lower() not in ("", "identity"):
            return Unavailable(url, "unsupported_content_encoding", now, response.status_code)
        body, truncated = bytearray(), False
        for chunk in response.iter_raw():  # as sent: nothing is decompressed before the cap
            body += chunk
            if len(body) > self.max_bytes:
                del body[self.max_bytes :]
                truncated = True
                break
            if time.monotonic() > deadline:  # a page that trickles in under the per-read timeout
                return Unavailable(url, "timeout", now, response.status_code)
        decoded = _decode(bytes(body), response.charset_encoding)
        if content_type in HTML_TYPES:
            try:
                from merchant_assistant.rag.collect import extract_text

                title, text = extract_text(decoded)
            except ImportError:  # the `ingest` extra is not installed
                return Unavailable(url, "extractor_unavailable", now, response.status_code)
            except Exception:  # a page the extractors cannot read is unavailable, not a crash
                return Unavailable(url, "extraction_failed", now, response.status_code)
        else:
            title, text = "", decoded.strip()
        if not text.strip():
            return Unavailable(url, "empty_text", now, response.status_code)
        return PageText(url, _masked(title), _masked(text), truncated, now, response.status_code)
