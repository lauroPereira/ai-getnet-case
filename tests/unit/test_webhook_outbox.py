from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from merchant_assistant.api.webhooks import Webhooks
from merchant_assistant.config import Settings
from merchant_assistant.data.db import connect
from merchant_assistant.data.webhook_outbox import enqueue, webhook_targets


def test_outbox_delivers_in_case_order_with_stable_ids(tmp_path):
    settings = Settings(
        _env_file=None, runtime_dir=tmp_path, ticketing_webhook_url="http://ticketing.test/events",
        ticketing_webhook_secret=SecretStr("synthetic-secret"),
    )
    conn = connect(settings.db_path)
    first = enqueue(conn, "handoff.created", {"case_id": "hc_1"}, "hc_1")
    second = enqueue(conn, "handoff.closed", {"case_id": "hc_1"}, "hc_1")
    conn.close()
    received = []

    def receive(request):
        received.append(json.loads(request.content))
        return httpx.Response(200)

    hooks = Webhooks(settings, transport=httpx.MockTransport(receive), sleep=lambda _: None)
    hooks.dispatch_pending()
    assert hooks.wait()
    assert [(item["type"], item["id"]) for item in received] == [
        ("handoff.created", first), ("handoff.closed", second)
    ]
    conn = connect(settings.db_path)
    assert [tuple(row) for row in conn.execute("SELECT status, attempts FROM webhook_outbox ORDER BY rowid")] == [
        ("delivered", 1), ("delivered", 1)
    ]
    conn.close()


def test_failed_first_event_blocks_later_event_and_stays_failed_after_restart(tmp_path):
    settings = Settings(
        _env_file=None, runtime_dir=tmp_path, ticketing_webhook_url="http://ticketing.test/events",
        ticketing_webhook_secret=SecretStr("synthetic-secret"),
    )
    conn = connect(settings.db_path)
    enqueue(conn, "handoff.created", {"case_id": "hc_1"}, "hc_1")
    enqueue(conn, "handoff.closed", {"case_id": "hc_1"}, "hc_1")
    conn.close()
    requests = []

    def unavailable(request):
        requests.append(json.loads(request.content))
        return httpx.Response(503)

    hooks = Webhooks(settings, transport=httpx.MockTransport(unavailable), sleep=lambda _: None)
    hooks.dispatch_pending()
    assert hooks.wait()
    assert len(requests) == 3 and {request["type"] for request in requests} == {"handoff.created"}
    restarted = Webhooks(settings, transport=httpx.MockTransport(unavailable), sleep=lambda _: None)
    restarted.recover_pending_intents()
    assert restarted.wait()
    assert len(requests) == 3
    conn = connect(settings.db_path)
    assert [tuple(row) for row in conn.execute("SELECT status,attempts FROM webhook_outbox ORDER BY rowid")] == [
        ("failed", 3), ("pending", 0)
    ]
    conn.close()


def test_pending_row_with_every_attempt_used_fails_without_a_request(tmp_path):
    settings = Settings(
        _env_file=None, runtime_dir=tmp_path, ticketing_webhook_url="http://ticketing.test/events",
        ticketing_webhook_secret=SecretStr("synthetic-secret"),
    )
    assert settings.webhook_max_attempts == 3
    conn = connect(settings.db_path)
    enqueue(conn, "handoff.created", {"case_id": "hc_1"}, "hc_1")
    conn.execute("UPDATE webhook_outbox SET attempts=3")  # the third attempt was made before a restart
    conn.close()
    requests = []

    def receive(request):
        requests.append(request)
        return httpx.Response(200)

    hooks = Webhooks(settings, transport=httpx.MockTransport(receive), sleep=lambda _: None)
    hooks.dispatch_pending()
    assert hooks.wait()
    assert requests == []
    conn = connect(settings.db_path)
    assert [tuple(row) for row in conn.execute("SELECT status,attempts FROM webhook_outbox")] == [("failed", 3)]
    conn.close()


def test_enqueue_never_replaces_an_existing_intention(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    enqueue(conn, "handoff.created", {"case_id": "hc_1", "summary": "first body"}, "hc_1")
    conn.execute("UPDATE webhook_outbox SET status='delivered', attempts=2")
    before = [tuple(row) for row in conn.execute("SELECT * FROM webhook_outbox")]
    enqueue(conn, "handoff.created", {"case_id": "hc_1", "summary": "a different body"}, "hc_1")
    assert [tuple(row) for row in conn.execute("SELECT * FROM webhook_outbox")] == before
    assert "first body" in before[0][5] and before[0][6:] == (2, "delivered")


def test_destination_without_a_url_gets_no_intention(tmp_path):
    secrets = {"ticketing_webhook_secret": SecretStr("s1"), "conversation_webhook_secret": SecretStr("s2")}
    only_ticketing = Settings(
        _env_file=None, runtime_dir=tmp_path, ticketing_webhook_url="http://ticketing.test/e", **secrets
    )
    nowhere = Settings(_env_file=None, runtime_dir=tmp_path, ticketing_webhook_url="", **secrets)
    both = Settings(
        _env_file=None, runtime_dir=tmp_path, ticketing_webhook_url="http://t.test/e",
        conversation_webhook_url="http://m.test/e", **secrets,
    )
    assert webhook_targets(only_ticketing) == {"ticketing"}
    assert webhook_targets(nowhere) == set() and webhook_targets(both) == {"ticketing", "merchant"}
    conn = connect(tmp_path / "db.sqlite3")
    data = {"case_id": "hc_1", "operator_id": "op_ana", "reply_text": "ok"}
    enqueue(conn, "conversation.replied", data, "a1", webhook_targets(only_ticketing))
    enqueue(conn, "handoff.closed", {"case_id": "hc_1"}, "hc_1", webhook_targets(nowhere))
    enqueue(conn, "conversation.replied", data, "a2", webhook_targets(both))
    queued = [tuple(row) for row in conn.execute("SELECT target FROM webhook_outbox ORDER BY rowid")]
    assert queued == [("ticketing",), ("ticketing",), ("merchant",)]


@pytest.mark.parametrize("name,prefix", [("ticketing", "ticketing_webhook"), ("merchant", "conversation_webhook")])
@pytest.mark.parametrize("url", [None, "", "http://receiver.test/e"])
@pytest.mark.parametrize("secret", [None, "", "   ", "synthetic-secret"])
def test_destination_is_a_target_only_with_a_url_and_a_secret_like_the_delivery(tmp_path, name, prefix, url, secret):
    """Review P3-2 of task 66: an intention for a destination the delivery skips would stay pending for good (and
    keep the 0010 rollback refused). The intention and the delivery read the destination the same way."""
    fields = {f"{prefix}_url": url, f"{prefix}_secret": None if secret is None else SecretStr(secret)}
    settings = Settings(_env_file=None, runtime_dir=tmp_path, **fields)
    deliverable = bool(url) and bool((secret or "").strip())
    assert (name in webhook_targets(settings)) is deliverable
    assert all(Webhooks(settings)._target(name)) is deliverable  # what the dispatcher checks before it sends
    conn = connect(tmp_path / "db.sqlite3")
    enqueue(conn, "conversation.replied", {"case_id": "hc_1", "reply_text": "ok"}, "a1", webhook_targets(settings))
    queued = {row[0] for row in conn.execute("SELECT target FROM webhook_outbox")}
    conn.close()
    assert queued == ({name} if deliverable else set())
