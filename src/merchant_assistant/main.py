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
from merchant_assistant.orchestration.budget import BudgetGuard, CombinedBudgetGuard
from merchant_assistant.orchestration.graph import Orchestrator
from merchant_assistant.rag.embed import Embedder
from merchant_assistant.rag.index import KnowledgeIndex, open_qdrant


def openai_client(settings: Settings):
    from openai import OpenAI

    if not settings.has_openai:
        raise RuntimeError("OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.")
    return OpenAI(api_key=settings.openai_api_key.get_secret_value(), timeout=30, max_retries=0)


def build_orchestrator(
    settings: Settings,
    *,
    llm: LLM | None = None,
    embedder: Embedder | None = None,
    clock: Clock | None = None,
    faults: dict[str, str] | None = None,
    budget: BudgetGuard | CombinedBudgetGuard | None = None,
) -> Orchestrator:
    from merchant_assistant.llm.jev import JevRouter
    from merchant_assistant.llm.openai_llm import OpenAILLM
    from merchant_assistant.mocks.clients import MockServiceClient
    from merchant_assistant.rag.embed import OpenAIEmbedder

    budget = budget or BudgetGuard(settings.runtime_path / "budget.sqlite3", settings.budget_limit_usd)
    client = None
    if llm is None or embedder is None:
        client = openai_client(settings)
    llm = llm or OpenAILLM(client, settings.agent_model)
    embedder = embedder or OpenAIEmbedder(client, settings.embedding_model, settings.embedding_dim, budget=budget)
    index = KnowledgeIndex(
        open_qdrant(settings.qdrant_url, settings.runtime_path / "qdrant"), settings.qdrant_collection, embedder
    )

    def llm_factory(provider: str, model: str) -> LLM:
        if provider == "openai":
            return OpenAILLM(openai_client(settings), model)
        if provider == "deepseek":
            if not settings.deepseek_api_key:
                raise RuntimeError("DEEPSEEK_API_KEY is not configured")
            from openai import OpenAI

            deepseek_client = OpenAI(
                api_key=settings.deepseek_api_key.get_secret_value(),
                base_url="https://api.deepseek.com",
                timeout=30,
                max_retries=0,
            )
            return OpenAILLM(deepseek_client, model)
        if provider == "typesafe" and model == "jev-1.14.0":
            if not settings.typesafe_api_key:
                raise RuntimeError("TYPESAFE_API_KEY is not configured")
            return JevRouter(settings.typesafe_api_key.get_secret_value())
        raise RuntimeError("model provider or identifier is not available")

    from merchant_assistant.rag.kb import KnowledgeBase

    kb = KnowledgeBase(db_path=settings.db_path, index=index, data_dir=settings.data_dir, budget=budget)
    return Orchestrator(
        settings=settings,
        llm=llm,
        index=index,
        knowledge_base=kb,
        clock=clock or SystemClock(settings.timezone),
        budget=budget,
        traces=TraceStore(settings.runtime_path / "traces.sqlite3"),
        faults=faults,
        mock_services=MockServiceClient(settings.mocks_url, timeout=2.0),
        llm_factory=llm_factory,
    )


def create_application() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    return create_app(build_orchestrator(settings), settings)
