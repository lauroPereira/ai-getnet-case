from __future__ import annotations

import json

import httpx
from pydantic import SecretStr

from merchant_assistant.api.webhooks import Webhooks
from merchant_assistant.config import Settings
from merchant_assistant.data.db import connect
from merchant_assistant.data.webhook_outbox import enqueue


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
    restarted.recover_handoff_closed()
    assert restarted.wait()
    assert len(requests) == 3
    conn = connect(settings.db_path)
    assert [tuple(row) for row in conn.execute("SELECT status,attempts FROM webhook_outbox ORDER BY rowid")] == [
        ("failed", 3), ("pending", 0)
    ]
    conn.close()
