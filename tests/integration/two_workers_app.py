"""One real API worker for the two-process tests of task 99 (`test_v0130_workers.py`, CA-70).

The offline system (scripted model, hashing embedder, in-memory Qdrant) over a runtime directory shared with the other
worker (SQLite database, budget ledger, traces, checkpoints and lock files), served by uvicorn on 127.0.0.1. Nothing
leaves the machine and nothing is paid.

Arguments: <runtime dir> <signing key> <port> <hang marker or -> <receiver base URL or ->. With a hang marker, the
second new comparison execution of this process writes its request id to the marker and then waits forever, like a
worker stopped in the middle of a model call; the test kills the process there. With a receiver, both webhook
destinations point to it.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import uvicorn
from pydantic import SecretStr

from merchant_assistant import comparisons
from merchant_assistant.api import v1
from merchant_assistant.api.app import create_app
from merchant_assistant.config import Settings
from merchant_assistant.testing import (
    TEST_TICKETING_SECRET,
    TEST_USER_PASSWORDS,
    offline_orchestrator,
    passwords_setting,
)

DEMO_KEY = "synthetic-demo-access-key-v0130"
HEARTBEAT_SECONDS, LEASE_SECONDS = 0.2, 1.5  # the production lease (5 s, 20 s) made short for the test
RATE_LIMIT_PER_MINUTE = 6
TICKETING_SECRET = "test-ticketing-webhook-secret-v0130"
CONVERSATION_SECRET = "test-conversation-webhook-secret-v0130"


def main() -> None:
    runtime, key, port, hang, receiver = sys.argv[1:6]
    comparisons.HEARTBEAT_SECONDS, comparisons.LEASE_SECONDS = HEARTBEAT_SECONDS, LEASE_SECONDS
    hooks = {}
    if receiver != "-":
        hooks = {
            "ticketing_webhook_url": f"{receiver}/ticketing",
            "ticketing_webhook_secret": SecretStr(TICKETING_SECRET),
            "conversation_webhook_url": f"{receiver}/merchant",
            "conversation_webhook_secret": SecretStr(CONVERSATION_SECRET),
        }
    settings = Settings(
        _env_file=None,
        openai_api_key=None,
        runtime_dir=Path(runtime),
        jwt_private_key_path=Path(key),
        demo_mode=True,
        budget_limit_usd=1.0,
        qdrant_url=":memory:",
        retrieval_min_score=0.05,
        demo_user_passwords=SecretStr(passwords_setting(TEST_USER_PASSWORDS)),
        ticketing_client_secret=SecretStr(TEST_TICKETING_SECRET),
        password_hash_iterations=1_000,
        api_demo_password=SecretStr(DEMO_KEY),
        rate_limit_per_minute=RATE_LIMIT_PER_MINUTE,
        **hooks,
    )
    orchestrator, _ = offline_orchestrator(settings)
    if hang != "-":
        real, seen = v1.execute_run, []

        def execute_run(*args, **kwargs):
            seen.append(kwargs["request_id"])
            if len(seen) == 2 and not Path(hang).exists():
                Path(hang).write_text(kwargs["request_id"], encoding="ascii")
                threading.Event().wait()  # the test kills the process here
            return real(*args, **kwargs)

        v1.execute_run = execute_run
    uvicorn.run(create_app(orchestrator, settings), host="127.0.0.1", port=int(port), log_level="warning")


if __name__ == "__main__":
    main()
