"""Application wiring with real dependencies (OpenAI, Qdrant, SQLite). Run with:

uvicorn --factory merchant_assistant.main:create_application
"""

from __future__ import annotations

from fastapi import FastAPI

from merchant_assistant.api.app import create_app
from merchant_assistant.config import Settings, get_settings
from merchant_assistant.data.clock import Clock, SystemClock
from merchant_assistant.llm.base import LLM
from merchant_assistant.observability.logging import configure_logging
from merchant_assistant.observability.traces import TraceStore
from merchant_assistant.orchestration.budget import BudgetGuard
from merchant_assistant.orchestration.graph import Orchestrator
from merchant_assistant.rag.embed import Embedder
from merchant_assistant.rag.index import KnowledgeIndex, open_qdrant


def openai_client(settings: Settings):
    from openai import OpenAI

    if not settings.has_openai:
        raise RuntimeError("OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.")
    return OpenAI(api_key=settings.openai_api_key.get_secret_value(), timeout=45, max_retries=2)


def build_orchestrator(
    settings: Settings,
    *,
    llm: LLM | None = None,
    embedder: Embedder | None = None,
    clock: Clock | None = None,
    faults: dict[str, str] | None = None,
) -> Orchestrator:
    from merchant_assistant.llm.openai_llm import OpenAILLM
    from merchant_assistant.rag.embed import OpenAIEmbedder

    budget = BudgetGuard(settings.runtime_path / "budget.sqlite3", settings.budget_limit_usd)
    client = None
    if llm is None or embedder is None:
        client = openai_client(settings)
    llm = llm or OpenAILLM(client, settings.agent_model)
    embedder = embedder or OpenAIEmbedder(
        client, settings.embedding_model, settings.embedding_dim, on_usage=budget.record_embedding
    )
    index = KnowledgeIndex(
        open_qdrant(settings.qdrant_url, settings.runtime_path / "qdrant"), settings.qdrant_collection, embedder
    )
    return Orchestrator(
        settings=settings,
        llm=llm,
        index=index,
        clock=clock or SystemClock(settings.timezone),
        budget=budget,
        traces=TraceStore(settings.runtime_path / "traces.sqlite3"),
        faults=faults,
    )


def create_application() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    return create_app(build_orchestrator(settings), settings)
