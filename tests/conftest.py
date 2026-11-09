from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant.api.app import create_app
from merchant_assistant.config import Settings
from merchant_assistant.testing import (
    TEST_TICKETING_SECRET,
    TEST_USER_PASSWORDS,
    offline_orchestrator,
    passwords_setting,
)


@pytest.fixture(scope="session")
def jwt_signing_key_path(tmp_path_factory):
    """One RSA key for the whole run (generated here, never versioned): issuing per test stays fast."""
    from merchant_assistant.api.identity import load_signing_key

    path = tmp_path_factory.mktemp("jwt") / "signing_key.pem"
    load_signing_key(path)
    return path


@pytest.fixture
def settings(tmp_path, jwt_signing_key_path) -> Settings:
    """Settings isolated from the developer's .env: no keys, temporary runtime directory."""
    return Settings(
        _env_file=None,
        openai_api_key=None,
        runtime_dir=tmp_path / "runtime",
        demo_mode=True,
        budget_limit_usd=1.0,
        qdrant_url=":memory:",
        retrieval_min_score=0.05,  # the offline hashing embedder produces lower similarities
        jwt_private_key_path=jwt_signing_key_path,
        demo_user_passwords=SecretStr(passwords_setting(TEST_USER_PASSWORDS)),
        ticketing_client_secret=SecretStr(TEST_TICKETING_SECRET),
        password_hash_iterations=1_000,  # the production default (600 000) is too slow for a test suite
    )


@pytest.fixture(scope="session")
def https_pages(tmp_path_factory):
    """In-process HTTPS server with fixed synthetic pages (task 87): the page fetcher of the evaluation is tested
    against it, so no test leaves the machine. Yields the base URL, the client TLS context and the hits per path."""
    server = LocalPages(tmp_path_factory.mktemp("https-pages"))
    try:
        yield server
    finally:
        server.close()


# --- in-process HTTPS pages (task 87) ------------------------------------------------------------------------------

LONG_TEXT = " ".join(f"Synthetic paragraph {n} about the euro exchange rate." for n in range(400))  # ~20 000 chars
PAGES = {
    "/page": (
        200,
        "text/html; charset=utf-8",
        "<html><head><title>Synthetic FX page</title></head><body><main><h1>Euro today</h1>"
        "<p>1 EUR = R$ 5,57 on 2026-10-26 at 10:00, according to this synthetic page.</p>"
        "<p>Write to ana@example.com for the daily table.</p></main></body></html>",
    ),
    "/long": (200, "text/html; charset=utf-8", f"<html><head><title>Long page</title></head><body><main><p>{LONG_TEXT}"
              "</p></main></body></html>"),
    "/plain": (200, "text/plain; charset=utf-8", "Plain synthetic text: 1 EUR = R$ 5,57."),
    "/pdf": (200, "application/pdf", "%PDF-1.4 synthetic"),
    "/error": (500, "text/html", "<html><body>Internal error</body></html>"),
    "/away": (302, "https://elsewhere.invalid/page", ""),  # a redirect to another host: never followed
    "/same": (302, "/page", ""),  # a redirect inside the same host: followed
    # task 87 round 2
    "/gone": (404, "text/html", "<html><body>Not here</body></html>"),  # definitive: cached
    "/busy": (429, "text/html", "<html><body>Slow down</body></html>"),  # transient: not cached
    "/bogus-charset": (
        200,
        "text/html; charset=bogus-charset",
        "<html><head><title>Odd charset page</title></head><body><main><p>1 EUR = R$ 5,57 under an unknown "
        "charset.</p></main></body></html>",
    ),
    "/bad-location": (302, "https://[", ""),  # a Location the URL parser rejects
    "/other-port": (302, "https://127.0.0.1:1/page", ""),  # same host, another port: never followed
    "/bad-port-location": (302, "https://127.0.0.1:abc/x", ""),  # a Location httpx itself refuses (review r2 P3-8)
}


class LocalPages:
    """A threaded HTTPS server on 127.0.0.1 with a self-signed certificate made for the session."""

    def __init__(self, directory) -> None:
        import contextlib
        import ipaddress
        import ssl
        import threading
        from collections import Counter
        from datetime import UTC, datetime, timedelta
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.x509.oid import NameOID

        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ai-getnet-case test pages")])
        now = datetime.now(UTC)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False)
            .add_extension(
                x509.KeyUsage(True, False, False, False, False, True, False, False, False), critical=True
            )
            .sign(key, hashes.SHA256())
        )
        cert_path, key_path = directory / "cert.pem", directory / "key.pem"
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
            )
        )
        self.hits: Counter = Counter()
        self.accept_encoding: dict[str, str | None] = {}
        hits, accept_encoding = self.hits, self.accept_encoding

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - the name http.server calls
                hits[self.path] += 1
                accept_encoding[self.path] = self.headers.get("Accept-Encoding")
                if self.path in ("/gzip", "/drip"):
                    return self.special()
                if self.path == "/slow":
                    import time

                    time.sleep(1.0)
                status, kind, body = PAGES.get(self.path, (404, "text/html", "<html><body>not found</body></html>"))
                if self.path == "/big":
                    status, kind, body = 200, "text/html", "<html><body><main>" + "<p>big page</p>" * 5000
                self.send_response(status)
                if status in (301, 302):
                    self.send_header("Location", kind)
                else:
                    self.send_header("Content-Type", kind)
                data = body.encode("utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                with contextlib.suppress(OSError):  # the client stopped reading (byte cap, timeout)
                    self.wfile.write(data)

            def special(self):
                import gzip
                import time

                html = "<html><head><title>Special</title></head><body><main><p>special page</p></main></body></html>"
                data = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                if self.path == "/gzip":  # sent compressed although the client asked for identity
                    data = gzip.compress(data)
                    self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                with contextlib.suppress(OSError):
                    if self.path == "/gzip":
                        self.wfile.write(data)
                        return
                    for n in range(0, len(data), 16):  # /drip: each read is fast, the whole page is slow
                        self.wfile.write(data[n : n + 16])
                        self.wfile.flush()
                        time.sleep(0.15)

            def log_message(self, *args):
                pass

        server_tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_tls.load_cert_chain(cert_path, key_path)
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._server.socket = server_tls.wrap_socket(self._server.socket, server_side=True)
        self.base = f"https://127.0.0.1:{self._server.server_address[1]}"
        self.client_tls = ssl.create_default_context(cafile=str(cert_path))
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def url(self, path: str) -> str:
        return self.base + path

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


@pytest.fixture
def offline(settings):
    """Full system with the scripted model: returns (client, orchestrator, llm)."""

    def make(**kwargs):
        orchestrator, llm = offline_orchestrator(settings, **kwargs)
        return TestClient(create_app(orchestrator, settings)), orchestrator, llm

    return make
