"""Offline assembly of the full system: seeded SQLite, in-memory index with the hashing embedder and the
scripted model. Used by the test suite and by the zero-cost evaluation mode."""

from __future__ import annotations

from collections.abc import Callable

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
    if with_index:
        index = KnowledgeIndex(
            open_qdrant(":memory:", settings.runtime_path), settings.qdrant_collection, HashEmbedder()
        )
        index.rebuild([c for d in load_all(settings.data_dir) for c in chunk_document(d)])
    llm = ScriptedLLM(handler or default_handler)
    orchestrator = Orchestrator(
        settings=settings,
        llm=llm,
        index=index,
        clock=clock,
        budget=BudgetGuard(settings.runtime_path / "budget.sqlite3", settings.budget_limit_usd),
        traces=TraceStore(settings.runtime_path / "traces.sqlite3"),
        faults=faults,
        mock_services=in_process_client(),
    )
    return orchestrator, llm
