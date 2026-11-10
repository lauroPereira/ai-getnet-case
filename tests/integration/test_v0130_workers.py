"""v0.13.0 task 99 (spec D4, CA-70): two real API processes over one runtime directory.

Each worker is `two_workers_app.py` under uvicorn on 127.0.0.1 (scripted model, hashing embedder, in-memory Qdrant,
lease of 0.2 s / 1.5 s instead of 5 s / 20 s). The owner of a comparison is killed in the middle of a cell
(`Popen.kill`, TerminateProcess on Windows, as `taskkill /F`); the other worker sees the lease expire, marks the
comparison `interrupted` and resumes only the missing cells. Rate limit, operator actions and outgoing webhooks are
exercised across both processes against a local receiver. No network beyond 127.0.0.1, no cost."""

from __future__ import annotations

import json
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

from merchant_assistant.testing import TEST_USER_PASSWORDS

WORKER = Path(__file__).with_name("two_workers_app.py")
DEMO_KEY = "synthetic-demo-access-key-v0130"  # two_workers_app.DEMO_KEY
RATE_LIMIT = 6  # two_workers_app.RATE_LIMIT_PER_MINUTE
HUMAN = "Quero falar com um atendente"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Worker:
    def __init__(self, settings, tmp_path: Path, name: str, *, hang: Path | None = None, receiver: str = "-"):
        self.port, self.name = free_port(), name
        self.log = (tmp_path / f"{name}.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [
                sys.executable,
                str(WORKER),
                str(settings.runtime_path),
                str(settings.jwt_private_key_path),
                str(self.port),
                str(hang) if hang else "-",
                receiver,
            ],
            stdout=self.log,
            stderr=subprocess.STDOUT,
        )
        self.url = f"http://127.0.0.1:{self.port}"
        self.http = httpx.Client(base_url=self.url, timeout=30)

    def wait_ready(self, timeout: float = 120) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            assert self.process.poll() is None, f"{self.name} exited: {self.output()}"
            try:
                if self.http.get("/health").status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        raise AssertionError(f"{self.name} did not start: {self.output()}")

    def output(self) -> str:
        self.log.flush()
        return Path(self.log.name).read_text(encoding="utf-8", errors="replace")[-4000:]

    def token(self, username: str, password: str) -> dict[str, str]:
        form = {"grant_type": "password", "username": username, "password": password}
        issued = self.http.post("/v1/auth/token", data=form)
        assert issued.status_code == 200, issued.text
        return {"Authorization": f"Bearer {issued.json()['access_token']}"}

    def stop(self) -> None:
        self.http.close()
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=30)
        self.log.close()


@pytest.fixture
def workers(settings, tmp_path):
    started: list[Worker] = []

    def start(name: str, **kwargs) -> Worker:
        worker = Worker(settings, tmp_path, name, **kwargs)
        started.append(worker)
        worker.wait_ready()  # one at a time: each worker seeds the synthetic tables when it starts
        return worker

    yield start
    for worker in started:
        worker.stop()


def until(check, timeout: float = 60, message: str = "condition"):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.1)
    raise AssertionError(f"timed out waiting for {message}")


def ledger(settings) -> dict[str, int]:
    conn = sqlite3.connect(settings.runtime_path / "budget.sqlite3")
    try:
        rows = conn.execute(
            "SELECT request_id, COUNT(*) FROM ledger WHERE status IN ('reserved','settled') GROUP BY request_id"
        )
        return {row[0]: row[1] for row in rows}
    finally:
        conn.close()


def holder_of(settings, comparison_id: str) -> str:
    conn = sqlite3.connect(settings.db_path)
    try:
        return conn.execute("SELECT worker_id FROM comparisons WHERE comparison_id=?", (comparison_id,)).fetchone()[0]
    finally:
        conn.close()


SELECTION = {
    "profiles": [{"profile_id": "reference", "profile_version": 1}, {"profile_id": "hybrid", "profile_version": 1}],
    "scenario_ids": ["SC-RECEIVABLES", "SC-HANDOFF"],
    "repetitions": 1,
    "router_mechanism": "llm",
    "reuse_recorded": False,
}


def test_the_other_worker_resumes_a_comparison_whose_owner_was_killed(settings, tmp_path, workers):
    hang = tmp_path / "hang.txt"
    owner = workers("owner", hang=hang)
    other = workers("other")
    headers = owner.token("demo", DEMO_KEY)  # one issuer key, one database: the token holds in both workers
    estimate = owner.http.post("/v1/comparisons/estimate", headers=headers, json=SELECTION).json()
    created = owner.http.post(
        "/v1/comparisons",
        headers=headers,
        json=SELECTION
        | {
            "confirmed": True,
            "max_cost_usd": estimate["estimated_cost_usd"],
            "expected_estimate_digest": estimate["estimate_digest"],
        },
    )
    assert created.status_code == 202, created.text
    comparison_id = created.json()["comparison_id"]
    path = f"/v1/comparisons/{comparison_id}"

    until(hang.exists, message="the owner to reach its second cell")
    killed_request_id = hang.read_text(encoding="ascii")
    seen = other.http.get(path, headers=headers).json()
    assert seen["state"] == "running"  # the owner's lease is fresh: the other worker leaves it alone
    first = seen["cells"][0]
    assert first["status"] == "completed" and first["request_id"]
    assert seen["cells"][1]["in_flight_request_id"] == killed_request_id
    busy = other.http.post(f"{path}/resume", headers=headers)
    assert busy.status_code == 409 and busy.json()["error"]["code"] == "comparison_running"
    ledger_before = ledger(settings)
    owner_holder = holder_of(settings, comparison_id)

    owner.process.kill()  # the owner dies in the middle of the cell
    owner.process.wait(timeout=30)
    lost = until(
        lambda: (body := other.http.get(path, headers=headers).json())["state"] == "interrupted" and body,
        timeout=30,
        message="the lease to expire",
    )
    assert lost["cells"][0] == first
    assert lost["cells"][1]["interrupted_attempts"] == [{"request_id": killed_request_id, "cost_usd": 0.0}]
    assert [cell["status"] for cell in lost["cells"][1:]] == ["pending"] * 3

    resumed = other.http.post(f"{path}/resume", headers=headers)
    assert resumed.status_code == 202, resumed.text
    assert resumed.json() == {"comparison_id": comparison_id, "state": "running", "resumed_cells": 3}
    done = until(
        lambda: (body := other.http.get(path, headers=headers).json())["state"] != "running" and body,
        timeout=60,
        message="the resumed comparison",
    )
    assert done["state"] == "completed", done["failures"]
    cells = done["cells"]
    assert all(cell["status"] == "completed" for cell in cells)
    assert cells[0]["request_id"] == first["request_id"]  # the finished cell was not run again
    request_ids = [cell["request_id"] for cell in cells]
    assert len(set(request_ids)) == 4 and killed_request_id not in request_ids

    after = ledger(settings)
    assert set(after) == set(request_ids)  # one set of ledger rows per cell; none for the attempt that never called
    assert after[first["request_id"]] == ledger_before[first["request_id"]]  # the first cell was paid once
    holder = holder_of(settings, comparison_id)
    conn = sqlite3.connect(settings.db_path)
    try:
        snapshots = conn.execute(
            "SELECT request_id, COUNT(*) FROM run_snapshots "
            "WHERE json_extract(snapshot, '$.profile_comparison_id')=? GROUP BY request_id",
            (comparison_id,),
        ).fetchall()
    finally:
        conn.close()
    # The lease is another process's now (the pids are of the interpreters themselves; on Windows a virtual
    # environment's launcher has a pid of its own, so they are compared with each other, not with Popen.pid).
    assert holder.rsplit(":", 2)[1] != owner_holder.rsplit(":", 2)[1] and holder != owner_holder
    assert sorted(row[0] for row in snapshots) == sorted(request_ids) and all(row[1] == 1 for row in snapshots)


class Receiver:
    """Local webhook receiver: records every delivery; the first one to the ticketing answers after a pause, so the
    other worker's dispatch meets a delivery still in progress."""

    def __init__(self) -> None:
        self.received: list[tuple[str, str, str]] = []  # (path, event id, event type)
        self.lock = threading.Lock()
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 - the name http.server calls
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                event = json.loads(body)
                with receiver.lock:
                    first = not any(path == self.path for path, _, _ in receiver.received)
                    receiver.received.append((self.path, event["id"], event["type"]))
                if first and self.path == "/ticketing":
                    time.sleep(1.5)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "received"}')

            def log_message(self, *args):  # quiet
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def events(self) -> list[tuple[str, str, str]]:
        with self.lock:
            return list(self.received)

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def receiver():
    server = Receiver()
    yield server
    server.close()


def test_rate_limit_handoffs_and_outbox_hold_across_two_workers(settings, workers, receiver):
    a = workers("a", receiver=receiver.url)
    b = workers("b", receiver=receiver.url)
    merchant = a.token("cliente1988", TEST_USER_PASSWORDS["cliente1988"])
    ana = b.token("op_ana", TEST_USER_PASSWORDS["op_ana"])
    bruno = a.token("op_bruno", TEST_USER_PASSWORDS["op_bruno"])

    handed = a.http.post("/messages", json={"message": HUMAN}, headers=merchant)
    assert handed.status_code == 200 and handed.json()["status"] == "handoff", handed.text
    [case] = b.http.get("/v1/handoffs", headers=ana).json()["cases"]
    case_id = case["case_id"]

    # Two operator actions at once, one in each worker: the case is resumed once.
    results: dict[str, httpx.Response] = {}

    def act(worker: Worker, key: str) -> None:
        results[key] = worker.http.post(
            f"/v1/handoffs/{case_id}/actions", headers=ana, json={"action": "approve", "idempotency_key": key}
        )

    threads = [threading.Thread(target=act, args=(w, k)) for w, k in ((a, "two-workers-a"), (b, "two-workers-b"))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    statuses = sorted(response.status_code for response in results.values())
    assert statuses == [200, 409], {key: response.text for key, response in results.items()}
    refused = next(response for response in results.values() if response.status_code == 409)
    assert refused.json()["error"]["code"] == "already_resumed"

    # Each event reaches each destination once, the creation before the reply, whichever worker sent it.
    until(lambda: len(receiver.events()) >= 3, timeout=60, message="the three deliveries")
    time.sleep(1.5)  # a duplicate from the other worker would arrive by now
    events = receiver.events()
    assert sorted((path, kind) for path, _, kind in events) == [
        ("/merchant", "conversation.replied"), ("/ticketing", "conversation.replied"), ("/ticketing", "handoff.created")
    ]
    assert [kind for path, _, kind in events if path == "/ticketing"] == ["handoff.created", "conversation.replied"]
    assert len({(path, event_id) for path, event_id, _ in events}) == 3
    conn = sqlite3.connect(settings.db_path)
    try:
        outbox = conn.execute("SELECT event, target, status, attempts FROM webhook_outbox ORDER BY rowid").fetchall()
        replies = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE via='operator' AND conversation_id=?", (case["conversation_id"],)
        ).fetchone()[0]
    finally:
        conn.close()
    assert [tuple(row) for row in outbox] == [
        ("handoff.created", "ticketing", "delivered", 1),
        ("conversation.replied", "ticketing", "delivered", 1),
        ("conversation.replied", "merchant", "delivered", 1),
    ]
    assert replies == 1

    # One rate limit per principal and minute, counted in the database whichever worker answers.
    if 60 - datetime.now(UTC).second < 15:  # keep the whole burst inside one window
        time.sleep(60 - datetime.now(UTC).second + 0.5)
    answers = [
        (a if n % 2 else b).http.post(f"/v1/handoffs/{case_id}/claim", headers=bruno).status_code
        for n in range(RATE_LIMIT + 1)
    ]
    assert answers == [409] * RATE_LIMIT + [429]  # claimed by op_ana; the seventh in the minute is refused
