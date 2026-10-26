"""Command line: ingest (collect snapshots), index, seed, bootstrap, serve, eval and smoke."""

from __future__ import annotations

import argparse
import json
import sys

from merchant_assistant.config import PROJECT_ROOT, Settings, get_settings


def _openai_client(settings: Settings):
    from openai import OpenAI

    if not settings.has_openai:
        raise SystemExit("OPENAI_API_KEY is required for this command.")
    return OpenAI(api_key=settings.openai_api_key.get_secret_value())


def build_embedder(settings: Settings, *, fake: bool = False, budget=None):
    from merchant_assistant.rag.embed import HashEmbedder, OpenAIEmbedder

    if fake:
        return HashEmbedder()
    on_usage = budget.record_embedding if budget else None
    return OpenAIEmbedder(_openai_client(settings), settings.embedding_model, settings.embedding_dim, on_usage=on_usage)


def cmd_ingest(settings: Settings, args) -> int:
    from merchant_assistant.rag.collect import collect

    results = collect(
        settings.data_dir / "sources" / "public-sources.json",
        settings.data_dir / "snapshots" / "public" / "pages",
        project_root=PROJECT_ROOT,
    )
    failed = [r for r in results if not r.ok]
    for r in results:
        print(f"{'ok ' if r.ok else 'ERR'} {r.chars:>6} {r.url} {r.message}")
    print(f"{len(results) - len(failed)} snapshots written, {len(failed)} failed")
    return 1 if failed else 0


def build_index(settings: Settings, *, fake: bool = False, budget=None) -> dict:
    from merchant_assistant.rag.chunk import chunk_document
    from merchant_assistant.rag.documents import load_all
    from merchant_assistant.rag.index import KnowledgeIndex, open_qdrant

    docs = load_all(settings.data_dir)
    chunks = [c for d in docs for c in chunk_document(d)]
    embedder = build_embedder(settings, fake=fake, budget=budget)
    index = KnowledgeIndex(
        open_qdrant(settings.qdrant_url, settings.runtime_path / "qdrant"), settings.qdrant_collection, embedder
    )
    manifest = index.rebuild(chunks, settings.runtime_path / "index_manifest.json")
    index.client.close()
    return manifest


def cmd_index(settings: Settings, args) -> int:
    print(json.dumps(build_index(settings, fake=args.fake), indent=1))
    return 0


def cmd_eval_retrieval(settings: Settings, args) -> int:
    from merchant_assistant.evaluation.retrieval import evaluate, load_cases
    from merchant_assistant.rag.chunk import chunk_document
    from merchant_assistant.rag.documents import load_all
    from merchant_assistant.rag.index import KnowledgeIndex, open_qdrant

    embedder = build_embedder(settings, fake=args.fake)
    index = KnowledgeIndex(open_qdrant(":memory:", settings.runtime_path), "eval_retrieval", embedder)
    index.rebuild([c for d in load_all(settings.data_dir) for c in chunk_document(d)])
    report = evaluate(index, load_cases(PROJECT_ROOT / "tests" / "scenarios" / "retrieval.jsonl"), k=args.k)
    report["embedding_model"] = embedder.model
    report["embedding_tokens"] = getattr(embedder, "tokens_used", 0)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


def _index_is_current(settings: Settings) -> bool:
    from merchant_assistant.rag.chunk import chunk_document
    from merchant_assistant.rag.documents import load_all
    from merchant_assistant.rag.index import KnowledgeIndex, corpus_hash, open_qdrant

    manifest_path = settings.runtime_path / "index_manifest.json"
    if not manifest_path.exists():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks = [c for d in load_all(settings.data_dir) for c in chunk_document(d)]
    if (
        manifest.get("corpus_hash") != corpus_hash(chunks)
        or manifest.get("embedding_model") != settings.embedding_model
    ):
        return False
    client = open_qdrant(settings.qdrant_url, settings.runtime_path / "qdrant")
    try:
        return KnowledgeIndex(client, settings.qdrant_collection, embedder=None).count() == manifest["chunks"]
    finally:
        client.close()


def cmd_bootstrap(settings: Settings, args) -> int:
    """Seeds the synthetic data (dates relative to today) and builds the index only when needed."""
    from merchant_assistant.data.clock import SystemClock
    from merchant_assistant.data.db import connect
    from merchant_assistant.data.seed import seed
    from merchant_assistant.orchestration.budget import BudgetGuard

    conn = connect(settings.db_path)
    counts = seed(conn, SystemClock(settings.timezone))
    conn.close()
    print(f"seeded synthetic data: {counts}")
    if _index_is_current(settings) and not args.force_index:
        print("knowledge index is current; skipping rebuild")
        return 0
    budget = BudgetGuard(settings.runtime_path / "budget.sqlite3", settings.budget_limit_usd)
    manifest = build_index(settings, budget=budget)
    print(f"knowledge index built: {manifest['chunks']} chunks from {manifest['documents']} documents")
    return 0


def cmd_ask(settings: Settings, args) -> int:
    """Runs one message through the real system in-process (paid)."""
    from merchant_assistant.api.schemas import MessageRequest
    from merchant_assistant.main import build_orchestrator

    orchestrator = build_orchestrator(settings)
    request = MessageRequest(message=args.message, user_id=args.user_id, conversation_id=args.conversation_id)
    response = orchestrator.handle(request, f"req_cli{__import__('uuid').uuid4().hex[:16]}")
    out = response.model_dump()
    if args.trace:
        out["trace"] = orchestrator.trace(response.request_id)
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    return 0


def cmd_smoke(settings: Settings, args) -> int:
    """Sends the 10 challenge examples to a running API and checks status codes and routes."""
    import httpx

    from merchant_assistant.api.schemas import CHALLENGE_EXAMPLES

    failures = 0
    with httpx.Client(base_url=args.url, timeout=120) as client:
        for message in CHALLENGE_EXAMPLES:
            r = client.post("/messages", json={"message": message, "user_id": "cliente1988"})
            ok = r.status_code == 200
            body = r.json() if ok else {}
            failures += not ok
            print(f"{r.status_code} {body.get('route', '-'):22} {body.get('status', '-'):20} {message}")
    print("smoke ok" if not failures else f"smoke failed: {failures}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="merchant-assistant")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="Collect public sources into versioned snapshots (network).")
    p_index = sub.add_parser("index", help="Build the vector index from snapshots and the demo corpus.")
    p_index.add_argument("--fake", action="store_true", help="Use the offline hashing embedder.")
    p_eval = sub.add_parser("eval-retrieval", help="Measure Recall@k on the labeled retrieval set.")
    p_eval.add_argument("--fake", action="store_true")
    p_eval.add_argument("-k", type=int, default=6)
    p_boot = sub.add_parser("bootstrap", help="Seed synthetic data and build the index if needed.")
    p_boot.add_argument("--force-index", action="store_true")
    p_ask = sub.add_parser("ask", help="Run one message through the real system (paid).")
    p_ask.add_argument("message")
    p_ask.add_argument("--user-id", default="cliente1988")
    p_ask.add_argument("--conversation-id", default=None)
    p_ask.add_argument("--trace", action="store_true")
    p_smoke = sub.add_parser("smoke", help="Send the 10 challenge examples to a running API.")
    p_smoke.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args(argv)
    settings = get_settings()
    handlers = {
        "ingest": cmd_ingest,
        "index": cmd_index,
        "eval-retrieval": cmd_eval_retrieval,
        "bootstrap": cmd_bootstrap,
        "ask": cmd_ask,
        "smoke": cmd_smoke,
    }
    return handlers[args.command](settings, args)


if __name__ == "__main__":
    sys.exit(main())
