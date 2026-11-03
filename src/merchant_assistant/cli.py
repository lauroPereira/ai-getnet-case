"""Command line: ingest (collect snapshots), index, seed, bootstrap, serve, eval and smoke."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from merchant_assistant.config import PROJECT_ROOT, Settings, get_settings


def _openai_client(settings: Settings):
    from openai import OpenAI

    if not settings.has_openai:
        raise SystemExit("OPENAI_API_KEY is required for this command.")
    return OpenAI(api_key=settings.openai_api_key.get_secret_value(), timeout=30, max_retries=0)


def _budget_guard(settings: Settings):
    from merchant_assistant.orchestration.budget import BudgetGuard

    return BudgetGuard(settings.runtime_path / "budget.sqlite3", settings.budget_limit_usd)


def build_embedder(settings: Settings, *, fake: bool = False, budget=None):
    from merchant_assistant.rag.embed import HashEmbedder, OpenAIEmbedder

    if fake:
        return HashEmbedder()
    if budget is None:  # a paid embedding without the persistent guard must fail before any provider contact
        raise SystemExit("Paid embeddings require the persistent budget guard.")
    return OpenAIEmbedder(_openai_client(settings), settings.embedding_model, settings.embedding_dim, budget=budget)


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


_IMMUTABLE_HINT = (
    "The CLI never replaces or rebuilds an existing collection (published knowledge base versions are immutable); "
    "create a new version through the admin API (POST /v1/kb/versions)."
)


def build_index(settings: Settings, *, fake: bool = False, budget=None) -> dict:
    from merchant_assistant.rag.chunk import chunk_document
    from merchant_assistant.rag.documents import load_all
    from merchant_assistant.rag.index import KnowledgeIndex, open_qdrant

    docs = load_all(settings.data_dir)
    chunks = [c for d in docs for c in chunk_document(d)]
    embedder = build_embedder(settings, fake=fake, budget=budget)
    client = open_qdrant(settings.qdrant_url, settings.runtime_path / "qdrant")
    index = KnowledgeIndex(client, settings.qdrant_collection, embedder)
    try:
        if index.exists():
            raise SystemExit(f"Collection '{settings.qdrant_collection}' already exists. {_IMMUTABLE_HINT}")
        return index.rebuild(chunks, settings.runtime_path / "index_manifest.json")
    finally:
        client.close()


def cmd_index(settings: Settings, args) -> int:
    budget = None if args.fake else _budget_guard(settings)
    print(json.dumps(build_index(settings, fake=args.fake, budget=budget), indent=1))
    return 0


def cmd_eval_retrieval(settings: Settings, args) -> int:
    from merchant_assistant.evaluation.retrieval import evaluate, load_cases
    from merchant_assistant.rag.chunk import chunk_document
    from merchant_assistant.rag.documents import load_all
    from merchant_assistant.rag.index import KnowledgeIndex, open_qdrant

    embedder = build_embedder(settings, fake=args.fake, budget=None if args.fake else _budget_guard(settings))
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


def _collection_exists(settings: Settings) -> bool:
    from merchant_assistant.rag.index import KnowledgeIndex, open_qdrant

    client = open_qdrant(settings.qdrant_url, settings.runtime_path / "qdrant")
    try:
        return KnowledgeIndex(client, settings.qdrant_collection, embedder=None).exists()
    finally:
        client.close()


def _wait_for_qdrant(url: str, attempts: int = 30) -> None:
    import time

    from qdrant_client import QdrantClient

    for attempt in range(attempts):
        try:
            QdrantClient(url=url, timeout=3).get_collections()
            return
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2)


def cmd_bootstrap(settings: Settings, args) -> int:
    """Seeds the synthetic data (dates relative to today) and builds the index only when needed."""
    from merchant_assistant.data.clock import SystemClock
    from merchant_assistant.data.db import connect
    from merchant_assistant.data.seed import seed

    if settings.qdrant_url and settings.qdrant_url != ":memory:":
        _wait_for_qdrant(settings.qdrant_url)
    conn = connect(settings.db_path)
    counts = seed(conn, SystemClock(settings.timezone))
    conn.close()
    print(f"seeded synthetic data: {counts}")
    if _collection_exists(settings):
        if args.force_index:
            raise SystemExit(
                f"Refusing --force-index: collection '{settings.qdrant_collection}' exists. {_IMMUTABLE_HINT}"
            )
        if _index_is_current(settings):
            print("knowledge index is current; skipping rebuild")
        else:
            print(f"knowledge index differs from the current sources and was left untouched. {_IMMUTABLE_HINT}")
        return 0
    manifest = build_index(settings, budget=_budget_guard(settings))
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


def _demo_password(settings: Settings, username: str) -> str | None:
    """The configured password of a synthetic demo user (DEMO_USER_PASSWORDS), for local commands."""
    raw = settings.demo_user_passwords.get_secret_value() if settings.demo_user_passwords else ""
    for item in raw.split(","):
        name, _, password = item.strip().partition(":")
        if name.strip() == username and password.strip():
            return password.strip()
    return None


def request_token(client, username: str, password: str, client_id: str = "merchant-assistant-cli") -> dict:
    """OAuth 2.0 password grant against `POST /v1/auth/token` (form encoded)."""
    data = {"grant_type": "password", "username": username, "password": password, "client_id": client_id}
    return client.post("/v1/auth/token", data=data)


def cmd_auth_token(settings: Settings, args) -> int:
    """Prints an access token for a demo user (for MERCHANT_ASSISTANT_TOKEN). The password is read from
    --password, then from DEMO_USER_PASSWORDS, then from the terminal."""
    import getpass

    import httpx

    password = args.password or _demo_password(settings, args.username) or getpass.getpass("password: ")
    with httpx.Client(base_url=args.url, timeout=30) as client:
        response = request_token(client, args.username, password)
    if response.status_code != 200:
        print(f"token refused: {response.status_code}", file=sys.stderr)
        return 1
    print(response.json()["access_token"])
    return 0


def run_smoke(client, username: str, password: str) -> int:
    """Gets a token for `username`, then sends the 10 challenge examples with it. Returns the number of failures."""
    from merchant_assistant.api.schemas import CHALLENGE_EXAMPLES

    token = request_token(client, username, password)
    if token.status_code != 200:
        print(f"{token.status_code} token refused for {username}")
        return len(CHALLENGE_EXAMPLES)
    print(f"token for {username} (scope: {token.json().get('scope')})")
    headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
    failures = 0
    for message in CHALLENGE_EXAMPLES:
        r = client.post("/messages", json={"message": message}, headers=headers)
        ok = r.status_code == 200
        body = r.json() if ok else {}
        failures += not ok
        print(f"{r.status_code} {body.get('route', '-'):22} {body.get('status', '-'):20} {message}")
    client.post("/v1/auth/revoke", headers=headers)
    return failures


def cmd_smoke(settings: Settings, args) -> int:
    """Gets a merchant token and sends the 10 challenge examples to a running API."""
    import httpx

    password = args.password or _demo_password(settings, args.username)
    if not password:
        raise SystemExit(f"No password for {args.username}: set DEMO_USER_PASSWORDS or pass --password.")
    with httpx.Client(base_url=args.url, timeout=120) as client:
        failures = run_smoke(client, args.username, password)
    print("smoke ok" if not failures else f"smoke failed: {failures}")
    return 1 if failures else 0


def cmd_eval(settings: Settings, args) -> int:
    """End-to-end evaluation. --scripted runs offline at zero cost; otherwise the real system is used (paid)."""
    import tempfile

    from merchant_assistant.evaluation.runner import BudgetMeter, load_cases, run, summarize, write_report

    scenarios = PROJECT_ROOT / "tests" / "scenarios"
    cases = load_cases(
        [scenarios / "challenge_examples.jsonl", scenarios / "core_cases.jsonl", scenarios / "business_journeys.jsonl"]
    )
    if args.split != "all":
        cases = [c for c in cases if c.split == args.split]
    if args.scripted:
        from merchant_assistant.testing import offline_orchestrator

        tmp = Path(tempfile.mkdtemp(prefix="eval-"))
        offline = settings.model_copy(
            update={"runtime_dir": tmp, "qdrant_url": ":memory:", "retrieval_min_score": 0.05}
        )
        orchestrator, _ = offline_orchestrator(offline)
        judge_llm, meter, mode = None, None, "scripted"
    else:
        from merchant_assistant.main import build_orchestrator

        orchestrator = build_orchestrator(settings)
        judge_llm = orchestrator.llm if args.judge else None
        meter, mode = BudgetMeter(orchestrator.budget), "real"
    rows = run(orchestrator, cases, judge_llm=judge_llm, prompts_dir=settings.prompts_dir, judge_meter=meter)
    summary = summarize(rows)
    if meter:
        summary["judge_cost_usd"] = round(meter.cost_usd, 5)
    config = {
        "mode": mode,
        "model": orchestrator.llm.model,
        "embedding": settings.embedding_model,
        "split": args.split,
        "judge": bool(judge_llm),
        "cases": len(cases),
    }
    md, js = write_report(rows, summary, Path(args.out), args.name, config)
    print(json.dumps(summary["overall"], indent=1))
    if not args.no_conversations:
        from merchant_assistant.evaluation.runner import append_conversation_report, run_conversations

        conversations = run_conversations(orchestrator, scenarios / "followup.jsonl")
        append_conversation_report(md, js, conversations)
        print(f"conversations: {sum(c['passed'] for c in conversations)}/{len(conversations)} passed")
    print(f"report: {md}")
    print(f"results: {js}")
    if hasattr(orchestrator, "close"):
        orchestrator.close()
    return 0


def cmd_migrate(settings: Settings, args) -> int:
    """Moves the database schema to a version (default: latest). Use --to to roll back."""
    import sqlite3

    from merchant_assistant.data.migrations import current_version, migrate

    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, isolation_level=None)
    try:
        steps = migrate(conn, args.to)
        for step in steps or ["nothing to apply"]:
            print(step)
        print(f"schema version: {current_version(conn)}")
    finally:
        conn.close()
    return 0


def cmd_mcp(settings: Settings, args) -> int:
    """Serves the support tools over MCP (stdio) for the merchant of MERCHANT_ASSISTANT_TOKEN. Nothing else may write
    to stdout. With the API in Docker, set JWT_ISSUER and JWT_JWKS_URL to the API's so the token verifies here."""
    from merchant_assistant.api.identity import Identity
    from merchant_assistant.data.clock import SystemClock
    from merchant_assistant.data.db import connect
    from merchant_assistant.mcp_server import (
        AccessRefused,
        build_server,
        env_factory_for,
        principal_for_token,
        serve_stdio,
    )
    from merchant_assistant.mocks.clients import MockServiceClient

    token = settings.merchant_assistant_token.get_secret_value() if settings.merchant_assistant_token else None
    conn = connect(settings.db_path)
    try:
        principal = principal_for_token(Identity(settings), conn, token)
    except AccessRefused as exc:
        print(f"mcp: {exc} (set MERCHANT_ASSISTANT_TOKEN; see `merchant-assistant auth token`)", file=sys.stderr)
        return 2
    finally:
        conn.close()
    services = MockServiceClient(settings.mocks_url, timeout=2.0)
    serve_stdio(build_server(env_factory_for(settings.db_path, principal, SystemClock(settings.timezone), services)))
    return 0


def cmd_mcp_demo(settings: Settings, args) -> int:
    """Starts the MCP server as a subprocess, lists the tools, calls two of them and shows the isolation error."""
    import anyio
    from mcp import Client, StdioServerParameters

    if not settings.merchant_assistant_token:
        raise SystemExit("Set MERCHANT_ASSISTANT_TOKEN (see `merchant-assistant auth token`).")
    params = StdioServerParameters(  # the token goes by environment, never on the command line
        command=sys.executable,
        args=["-m", "merchant_assistant.cli", "mcp"],
        env={
            **__import__("os").environ,
            "PYTHONUTF8": "1",
            "MERCHANT_ASSISTANT_TOKEN": settings.merchant_assistant_token.get_secret_value(),
        },
    )
    calls = [
        ("get_receivables_schedule", {"period": "yesterday"}),
        ("find_authorization_events", {"period": "last_7_days"}),
        ("get_payout_status", {"receivable_ids": ["rcv_002_0001"]}),  # belongs to another merchant
    ]

    async def main() -> None:
        async with Client(params) as client:
            listed = await client.list_tools()
            print(f"server tools ({len(listed.tools)}): {', '.join(t.name for t in listed.tools)}")
            for name, arguments in calls:
                result = await client.call_tool(name, arguments)
                payload = json.loads(result.content[0].text)
                if result.is_error:
                    summary = f"error {payload['error']['code']}"
                elif "receivables" in payload:
                    items = [
                        f"{r['net_amount']['display']} on {r['expected_payment_date']}" for r in payload["receivables"]
                    ]
                    summary = f"{payload['count']} receivables: {'; '.join(items)}"
                else:
                    events = payload.get("events", [])
                    latest = events[0]["reason_category"] if events else "-"
                    summary = f"{len(events)} events, latest reason {latest}"
                print(f"call {name}({json.dumps(arguments)}): is_error={result.is_error} -> {summary}")

    anyio.run(main)
    return 0


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
    p_evalx = sub.add_parser("eval", help="End-to-end evaluation over the labeled scenarios.")
    p_evalx.add_argument("--scripted", action="store_true", help="Offline scripted model (zero cost).")
    p_evalx.add_argument("--judge", action="store_true", help="Add a model-graded rubric (paid).")
    p_evalx.add_argument("--split", choices=["all", "dev", "holdout"], default="all")
    p_evalx.add_argument("--out", default=str(PROJECT_ROOT / "docs" / "evidence"))
    p_evalx.add_argument("--name", default="avaliacao")
    p_evalx.add_argument("--no-conversations", action="store_true", help="Skip the multi-turn scenarios.")
    p_migrate = sub.add_parser("migrate", help="Apply or roll back schema migrations.")
    p_migrate.add_argument("--to", type=int, default=None, help="Target schema version (default: latest).")
    sub.add_parser("mcp", help="Serve the support tools over MCP (stdio) for the merchant of MERCHANT_ASSISTANT_TOKEN.")
    sub.add_parser("mcp-demo", help="Run an MCP client against the stdio server (uses MERCHANT_ASSISTANT_TOKEN).")
    p_smoke = sub.add_parser("smoke", help="Get a merchant token and send the 10 challenge examples to a running API.")
    p_smoke.add_argument("--url", default="http://localhost:8000")
    p_smoke.add_argument("--username", default="cliente1988")
    p_smoke.add_argument("--password", default=None, help="Default: DEMO_USER_PASSWORDS.")
    p_auth = sub.add_parser("auth", help="Identity commands.")
    auth_sub = p_auth.add_subparsers(dest="auth_command", required=True)
    p_token = auth_sub.add_parser("token", help="Print an access token for a demo user (password grant).")
    p_token.add_argument("--username", default="cliente1988")
    p_token.add_argument("--password", default=None, help="Default: DEMO_USER_PASSWORDS, then the terminal.")
    p_token.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args(argv)
    settings = get_settings()
    handlers = {
        "ingest": cmd_ingest,
        "index": cmd_index,
        "eval-retrieval": cmd_eval_retrieval,
        "bootstrap": cmd_bootstrap,
        "ask": cmd_ask,
        "smoke": cmd_smoke,
        "eval": cmd_eval,
        "migrate": cmd_migrate,
        "mcp": cmd_mcp,
        "mcp-demo": cmd_mcp_demo,
        "auth": cmd_auth_token,
    }
    return handlers[args.command](settings, args)


if __name__ == "__main__":
    sys.exit(main())
