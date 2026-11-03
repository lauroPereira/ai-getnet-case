"""Offline assembly of the full system: seeded SQLite, in-memory index with the hashing embedder and the
scripted model. Used by the test suite and by the zero-cost evaluation mode."""

from __future__ import annotations

from collections.abc import Callable

import httpx

from merchant_assistant.config import Settings
from merchant_assistant.data.clock import Clock, FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import seed
from merchant_assistant.llm.scripted import ScriptedCall, ScriptedLLM
from merchant_assistant.mocks.clients import in_process_client
from merchant_assistant.observability.traces import TraceStore
from merchant_assistant.orchestration.budget import BudgetGuard
from merchant_assistant.orchestration.graph import Orchestrator
from merchant_assistant.rag.chunk import chunk_document
from merchant_assistant.rag.documents import load_all
from merchant_assistant.rag.embed import HashEmbedder
from merchant_assistant.rag.index import KnowledgeIndex, open_qdrant

DEFAULT_CLOCK = "2026-10-26T10:00:00"


def offline_orchestrator(
    settings: Settings,
    *,
    handler: Callable[[ScriptedCall], object] | None = None,
    clock: Clock | None = None,
    faults: dict[str, str] | None = None,
    with_index: bool = True,
) -> tuple[Orchestrator, ScriptedLLM]:
    from merchant_assistant.evaluation.scripted_policy import handler as default_handler

    clock = clock or FixedClock(DEFAULT_CLOCK)
    conn = connect(settings.db_path)
    seed(conn, clock)
    conn.close()
    index = None
    budget = BudgetGuard(settings.runtime_path / "budget.sqlite3", settings.budget_limit_usd)
    if with_index:
        index = KnowledgeIndex(
            open_qdrant(":memory:", settings.runtime_path), settings.qdrant_collection, HashEmbedder()
        )
        index.rebuild([c for d in load_all(settings.data_dir) for c in chunk_document(d)])
    from merchant_assistant.rag.kb import KnowledgeBase

    knowledge_base = (
        KnowledgeBase(db_path=settings.db_path, index=index, data_dir=settings.data_dir, budget=budget)
        if index
        else None
    )
    llm = ScriptedLLM(handler or default_handler)
    orchestrator = Orchestrator(
        settings=settings,
        llm=llm,
        index=index,
        clock=clock,
        budget=budget,
        traces=TraceStore(settings.runtime_path / "traces.sqlite3"),
        faults=faults,
        mock_services=in_process_client(),
        knowledge_base=knowledge_base,
    )
    return orchestrator, llm


# v0.7.0 identity: synthetic credentials used only by the test suite (never in .env.example or compose).
TEST_USER_PASSWORDS = {
    "cliente1988": "test-password-cliente1988",
    "cliente_demo_002": "test-password-cliente-demo-002",
    "op_ana": "test-password-op-ana",
    "op_bruno": "test-password-op-bruno",
}
TEST_TICKETING_SECRET = "test-ticketing-client-secret"


def passwords_setting(passwords: dict[str, str]) -> str:
    return ",".join(f"{user}:{password}" for user, password in passwords.items())


def token_headers(client, principal) -> dict[str, str]:
    """Authorization header with a token the app's issuer signs for an already authenticated principal
    (`api.identity.Principal`); the login itself is covered by the `/v1/auth/token` tests."""
    token = client.app.state.identity.issue(principal, "test-client")["access_token"]
    return {"Authorization": f"Bearer {token}"}


def password_token(client, username: str, password: str) -> str:
    """Access token through `POST /v1/auth/token` (password grant)."""
    response = client.post(
        "/v1/auth/token", data={"grant_type": "password", "username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def password_headers(client, username: str, password: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {password_token(client, username, password)}"}


def merchant_headers(client, customer_id: str = "cliente1988") -> dict[str, str]:
    """One merchant token per test client and merchant (cached on the client)."""
    from merchant_assistant.api.identity import Principal

    cache = client.__dict__.setdefault("_merchant_tokens", {})
    if customer_id not in cache:
        cache[customer_id] = token_headers(client, Principal.merchant(customer_id))
    return cache[customer_id]


def key_token(client, password: str) -> str:
    """Token of the `demo` or `admin` user whose configured password is `password` (v0.6.0 tests used access keys)."""
    settings = client.app.state.settings
    admin = settings.api_admin_password.get_secret_value() if settings.api_admin_password else None
    return password_token(client, "admin" if password == admin else "demo", password)


class AppTransport(httpx.BaseTransport):
    """Test transport between in-process services: each host is one ASGI app behind a
    `fastapi.testclient.TestClient`. The answer is read in full, so a plain `httpx.Client` can use it."""

    def __init__(self, apps: dict) -> None:
        self.apps = apps  # host -> TestClient

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self.apps[request.url.host]._transport.handle_request(request)
        content = response.read()
        return httpx.Response(response.status_code, headers=response.headers, content=content, request=request)
