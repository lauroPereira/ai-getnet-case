from __future__ import annotations

import json

import httpx
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
    only_ticketing = Settings(_env_file=None, runtime_dir=tmp_path, ticketing_webhook_url="http://ticketing.test/e")
    nowhere = Settings(_env_file=None, runtime_dir=tmp_path, ticketing_webhook_url="")
    both = Settings(
        _env_file=None, runtime_dir=tmp_path, ticketing_webhook_url="http://t.test/e",
        conversation_webhook_url="http://m.test/e",
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
