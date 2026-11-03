"""Ticketing service: isolation from the assistant, webhook signature and settings."""

from __future__ import annotations

import ast
import hashlib
import hmac
from pathlib import Path

from merchant_assistant.ticketing.config import TicketingSettings
from merchant_assistant.ticketing.signing import signature, verify

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "merchant_assistant" / "ticketing"


def test_ticketing_does_not_import_the_assistant():
    """D16: the service talks to the assistant only over HTTP."""
    offenders = []
    for path in sorted(PACKAGE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level > 1:  # relative import that leaves the package
                    offenders.append(f"{path.name}: level {node.level}")
                    continue
                names = [node.module or ""] if node.level == 0 else []
            else:
                continue
            for name in names:
                if name.split(".")[0] == "merchant_assistant" and not name.startswith("merchant_assistant.ticketing"):
                    offenders.append(f"{path.name}: {name}")
    assert offenders == []
    assert {p.name for p in PACKAGE.glob("*.py")} >= {"service.py", "store.py", "auth.py", "outbox.py"}


def test_signature_matches_the_contract_formula():
    body = b'{"id":"evt_1"}'
    header = signature("secret", body, 1_700_000_000)
    expected = hmac.new(b"secret", b"1700000000." + body, hashlib.sha256).hexdigest()
    assert header == f"t=1700000000,v1={expected}"


def test_signature_window_and_tampering():
    body = b"{}"
    header = signature("secret", body, 1_000)
    assert verify("secret", header, body, 1_300, 300)
    assert verify("secret", header, body, 700, 300)
    assert not verify("secret", header, body, 1_301, 300)
    assert not verify("secret", header, b"{ }", 1_000, 300)
    assert not verify("other", header, body, 1_000, 300)
    assert not verify("", header, body, 1_000, 300)
    assert not verify("secret", None, body, 1_000, 300)
    assert not verify("secret", "t=abc,v1=00", body, 1_000, 300)
    assert verify("secret", f"{header},v1=deadbeef", body, 1_000, 300)  # extra signature during secret rotation


def test_settings_from_the_contract_variables():
    settings = TicketingSettings.from_env(
        {
            "TICKETING_DB_PATH": "/data/t.sqlite3",
            "ASSISTANT_URL": "http://api:8000/",
            "ASSISTANT_ISSUER": "http://api:8000",
            "ASSISTANT_JWKS_URL": "http://api:8000/.well-known/jwks.json",
            "TICKETING_WEBHOOK_SECRET": "in",
            "ASSISTANT_WEBHOOK_SECRET": "out",
            "TICKETING_CLIENT_ID": "ticketing-demo",
            "TICKETING_CLIENT_SECRET": "s",
        }
    )
    assert settings.db_path == Path("/data/t.sqlite3") and settings.assistant_url == "http://api:8000"
    assert (settings.inbound_secret, settings.outbound_secret, settings.client_secret) == ("in", "out", "s")
    assert settings.retry_waits_s == (1.0, 2.0) and settings.max_attempts == 3 and settings.request_timeout_s == 3.0
    defaults = TicketingSettings.from_env({"RUNTIME_DIR": "/app/runtime"})
    assert defaults.db_path == Path("/app/runtime/ticketing.sqlite3")
    assert defaults.assistant_jwks_url == "http://127.0.0.1:8000/.well-known/jwks.json"
    assert defaults.inbound_secret == "" and defaults.client_id == "ticketing-demo"


def test_importing_the_service_creates_no_database(tmp_path, monkeypatch):
    import importlib

    monkeypatch.setenv("TICKETING_DB_PATH", str(tmp_path / "lazy" / "t.sqlite3"))
    module = importlib.import_module("merchant_assistant.ticketing.service")
    module.create_app()
    assert not (tmp_path / "lazy").exists()
