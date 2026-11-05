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


V080_QA_CAMPAIGN = "v080-qa"
V080_QA_CAP_USD = 0.50
V080_QA_MAX_CAP_USD = 1.00
V080_QA_EXCEPTIONAL_CAP_USD = 1.10
V080_QA_CONTINGENCY_CAP_USD = 1.40  # 2026-11-05 contingency (task 77): continues the mounted v080-qa campaign only
V080_HOLDOUT_CASE_COUNT = 25  # sealed 72a metadata; estimate uses the count without opening the holdout JSONL


def _evaluation_budget_runtime_path(settings: Settings) -> Path:
    try:
        return settings.budget_runtime_path
    except ValueError as exc:
        raise SystemExit(f"eval: {exc}") from None


def _has_persisted_v080_cap(path: Path, cap_usd: float) -> bool:
    """Return true only for the exact cap mounted earlier with its persistent ceiling sidecar."""
    import sqlite3

    if not path.is_file():
        return False
    try:
        ceiling = float(Path(f"{path}.limit").read_text(encoding="ascii").strip())
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            rows = conn.execute("SELECT cap_id,limit_usd FROM fixed_budget_cap").fetchall()
        finally:
            conn.close()
    except (OSError, ValueError, sqlite3.Error):
        return False
    return ceiling == cap_usd and rows == [(V080_QA_CAMPAIGN, cap_usd)]


def _path_entry_exists(path: Path) -> bool:
    """Detect files and links, including dangling links that Path.exists() follows."""
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _evaluation_budget_guard(
    settings: Settings,
    campaign_id: str | None = None,
    *,
    campaign_cap_usd: float = V080_QA_CAP_USD,
    estimate_report: str | Path | None = None,
):
    """Return the installation ledger, optionally combined with the one-time v0.8.0 QA cap."""
    if campaign_id is None:
        if campaign_cap_usd != V080_QA_CAP_USD or estimate_report is not None:
            raise SystemExit("eval: --campaign-cap-usd and --campaign-estimate require --campaign v080-qa.")
        from merchant_assistant.orchestration.budget import BudgetGuard

        return BudgetGuard(
            _evaluation_budget_runtime_path(settings) / "budget.sqlite3", settings.budget_limit_usd
        )
    if campaign_id != V080_QA_CAMPAIGN:
        raise SystemExit(f"eval: unsupported campaign {campaign_id!r}; the only fixed campaign is {V080_QA_CAMPAIGN}.")
    if campaign_cap_usd == V080_QA_CAP_USD:
        cap_ceiling_usd = V080_QA_CAP_USD
    elif campaign_cap_usd == V080_QA_MAX_CAP_USD:
        if estimate_report is None:
            raise SystemExit("eval: a USD 1.00 v080-qa cap requires --campaign-estimate from the measured cost report.")
        estimate = _verified_v080_campaign_estimate(Path(estimate_report))
        if isinstance(estimate, bool) or not isinstance(estimate, (int, float)) or not 0.50 < estimate <= 1.00:
            raise SystemExit(
                "eval: USD 1.00 is allowed only when the measured campaign estimate is "
                "above USD 0.50 and at most USD 1.00."
            )
        cap_ceiling_usd = V080_QA_MAX_CAP_USD
    elif campaign_cap_usd == V080_QA_EXCEPTIONAL_CAP_USD:
        if estimate_report is None:
            raise SystemExit(
                "eval: a USD 1.10 v080-qa cap requires --campaign-estimate from the measured cost report."
            )
        estimate = _verified_v080_campaign_estimate(Path(estimate_report))
        if (
            isinstance(estimate, bool)
            or not isinstance(estimate, (int, float))
            or not 1.00 < estimate <= V080_QA_EXCEPTIONAL_CAP_USD
        ):
            raise SystemExit(
                "eval: USD 1.10 is allowed only when the measured campaign estimate is "
                "above USD 1.00 and at most USD 1.10."
            )
        cap_ceiling_usd = V080_QA_EXCEPTIONAL_CAP_USD
    elif campaign_cap_usd == V080_QA_CONTINGENCY_CAP_USD:
        if estimate_report is None:
            raise SystemExit("eval: a USD 1.40 v080-qa cap requires --campaign-estimate from the measured cost report.")
        estimate = _verified_v080_campaign_estimate(Path(estimate_report))
        if (
            isinstance(estimate, bool)
            or not isinstance(estimate, (int, float))
            or not 1.00 < estimate <= V080_QA_EXCEPTIONAL_CAP_USD
        ):
            raise SystemExit(
                "eval: USD 1.40 continues only the v080-qa campaign whose verified estimate is "
                "above USD 1.00 and at most USD 1.10."
            )
        cap_ceiling_usd = V080_QA_CONTINGENCY_CAP_USD
    else:
        raise SystemExit("eval: --campaign-cap-usd must be 0.50, 1.00, 1.10 or 1.40.")

    from merchant_assistant.orchestration.budget import (
        CombinedBudgetGuard,
        FixedBudgetGuard,
    )

    budget_dir = _evaluation_budget_runtime_path(settings)
    from merchant_assistant.orchestration.budget import BudgetGuard

    campaign_path = budget_dir / f"budget-{V080_QA_CAMPAIGN}.sqlite3"
    if campaign_cap_usd == V080_QA_CONTINGENCY_CAP_USD:  # checked before any ledger is opened for writing
        if _has_persisted_v080_cap(campaign_path, V080_QA_EXCEPTIONAL_CAP_USD):
            raise SystemExit(
                "eval: the v080-qa campaign is still fixed at USD 1.10; apply the reviewed contingency "
                "transition before using USD 1.40."
            )
        if not _has_persisted_v080_cap(campaign_path, V080_QA_CONTINGENCY_CAP_USD):
            raise SystemExit(
                "eval: USD 1.40 only continues the v080-qa campaign already mounted; no matching persisted "
                "v080-qa cap and ceiling sidecar were found, so nothing was mounted."
            )
    primary = BudgetGuard(budget_dir / "budget.sqlite3", settings.budget_limit_usd)
    if campaign_cap_usd == V080_QA_EXCEPTIONAL_CAP_USD:
        persisted_cap_matches = _has_persisted_v080_cap(campaign_path, campaign_cap_usd)
        campaign_sidecar = Path(f"{campaign_path}.limit")
        if (
            (_path_entry_exists(campaign_path) or _path_entry_exists(campaign_sidecar))
            and not persisted_cap_matches
        ):
            raise SystemExit(
                "eval: a pre-existing v080-qa database or ceiling sidecar does not match "
                "the fixed USD 1.10 cap; refusing to mount."
            )
        if not persisted_cap_matches and campaign_cap_usd > primary.remaining():
            raise SystemExit(
                "eval: the USD 1.10 v080-qa cap does not fit in the remaining primary budget; "
                "the campaign cap was not mounted."
            )
    campaign = FixedBudgetGuard(
        campaign_path,
        campaign_cap_usd,
        cap_id=V080_QA_CAMPAIGN,
        cap_ceiling_usd=cap_ceiling_usd,
    )
    if campaign_cap_usd == V080_QA_CONTINGENCY_CAP_USD:
        primary_ceiling = float(Path(f"{primary.path}.limit").read_text(encoding="ascii").strip())
        if primary_ceiling - primary.spent() + 1e-12 < campaign.remaining():
            raise SystemExit(
                "eval: the persisted primary ceiling does not cover the rest of the USD 1.40 v080-qa cap; "
                "apply the reviewed contingency transition to both ledgers first."
            )
    return CombinedBudgetGuard(primary, campaign)


def _eval_budget_for_args(settings: Settings, args):
    return _evaluation_budget_guard(
        settings,
        getattr(args, "campaign", None),
        campaign_cap_usd=getattr(args, "campaign_cap_usd", V080_QA_CAP_USD),
        estimate_report=getattr(args, "campaign_estimate", None),
    )


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
    mode = getattr(args, "mode", None) or settings.retrieval_mode
    index = KnowledgeIndex(open_qdrant(":memory:", settings.runtime_path), "eval_retrieval", embedder)
    manifest = index.rebuild([c for d in load_all(settings.data_dir) for c in chunk_document(d)])
    report = evaluate(
        index, load_cases(PROJECT_ROOT / "tests" / "scenarios" / "retrieval.jsonl"), k=args.k, mode=mode
    )
    report["mode"] = mode
    report["bm25_corpus_hash"] = manifest["bm25_corpus_hash"]  # BM25 kept in memory, like this Qdrant
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


def _eval_judge(
    settings: Settings,
    *,
    scripted: bool,
    agent_model: str | None = None,
    agent_provider: str | None = None,
    validated_plan=None,
):
    """The campaign judge (`eval --judge`): the scripted stand-in offline, otherwise the configured independent
    evaluator, or a refusal that leaves before anything is built or called (spec v0.8.0 D11)."""
    from merchant_assistant.evaluation import judge as judge_module

    if scripted:
        from merchant_assistant.evaluation.scripted_judge import scripted_judge

        judge = scripted_judge(settings.prompts_dir, None)
        agent = ("scripted", agent_model or "scripted-v1")
    else:
        agent = (agent_provider or judge_module.AGENT_PROVIDER, agent_model or settings.agent_model)
        try:
            return judge_module.resolve_judge(settings, agent=agent, validated=validated_plan)
        except judge_module.JudgeRefused as exc:
            raise SystemExit(f"eval: {exc}") from None
    try:
        judge_module.check_independence(agent, (judge.provider, judge.model))
    except judge_module.JudgeRefused as exc:
        raise SystemExit(f"eval: {exc}") from None
    return judge


def _eval_judge_preflight(
    settings: Settings, *, agent_model: str | None = None, agent_provider: str | None = None
):
    """Validate paid-judge configuration before opening the persistent budget ledger."""
    from merchant_assistant.evaluation import judge as judge_module

    agent = (agent_provider or judge_module.AGENT_PROVIDER, agent_model or settings.agent_model)
    try:
        return judge_module.validate_judge(settings, agent=agent)
    except judge_module.JudgeRefused as exc:
        raise SystemExit(f"eval: {exc}") from None


def _report_name(args, answers_split: str | None = None) -> str:
    """The report name: `--name`, or a default that never overwrites another kind of report (a holdout run is not the
    development run, a judge-only run is not the run it grades, and the judge's report on the holdout answers is not
    the one on the development answers: `answers_split` is the split the recorded answers belong to)."""
    if getattr(args, "name", None):
        return args.name
    if getattr(args, "judge_repeat", None) is not None:
        return "avaliacao-juiz" + ("" if answers_split in (None, "all") else "-" + answers_split.replace("_", "-"))
    return "avaliacao-holdout-v080" if args.split == "holdout_v080" else "avaliacao"


def _store_judgements(db_path, judge, rows, persist) -> None:
    from merchant_assistant.data.db import connect

    conn = connect(db_path)
    try:
        print(f"judgements stored in run_evaluations: {persist(conn, judge, rows)}")
    finally:
        conn.close()


def cmd_eval(settings: Settings, args) -> int:
    """End-to-end evaluation. --scripted runs offline at zero cost; otherwise the real system is used (paid).
    --repeat N runs the agent N times (variation of the assistant); --judge-repeat N grades recorded answers again
    (variation of the judge, `cmd_eval_rejudge`)."""
    import tempfile

    from merchant_assistant.evaluation import aggregate
    from merchant_assistant.evaluation.runner import (
        BudgetMeter,
        load_cases,
        persist_judgements,
        run,
        summarize,
        write_report,
    )

    if getattr(args, "campaign", None) is None and (
        getattr(args, "campaign_cap_usd", V080_QA_CAP_USD) != V080_QA_CAP_USD
        or getattr(args, "campaign_estimate", None) is not None
    ):
        raise SystemExit("eval: --campaign-cap-usd and --campaign-estimate require --campaign v080-qa.")
    if getattr(args, "judge_repeat", None) is not None:
        return cmd_eval_rejudge(settings, args)
    repeat = getattr(args, "repeat", 1)
    if repeat < 1:
        raise SystemExit("eval: --repeat must be at least 1.")
    scenarios = PROJECT_ROOT / "tests" / "scenarios"
    case_files = [
    scenarios / name
    for name in ("challenge_examples.jsonl", "core_cases.jsonl", "business_journeys.jsonl")
]
    if getattr(args, "include_replan", False):
        case_files.insert(0, scenarios / "replan.jsonl")
    cases = load_cases(case_files)
    if args.split == "holdout_v080":  # reported apart (D14): never part of `all`, and without the dev conversations
        cases = load_cases([scenarios / "holdout_v080.jsonl"])
    elif args.split != "all":
        cases = [c for c in cases if c.split == args.split]
    case_limit = getattr(args, "limit", None)
    if case_limit is not None:
        if case_limit < 1:
            raise SystemExit("eval: --limit must be at least 1.")
        cases = cases[:case_limit]
    judge_plan = _eval_judge_preflight(settings) if args.judge and not args.scripted else None
    budget = (
        _eval_budget_for_args(settings, args)
        if not args.scripted or getattr(args, "campaign", None) is not None
        else None
    )
    judge = _eval_judge(settings, scripted=args.scripted, validated_plan=judge_plan) if args.judge else None
    if args.scripted:
        from merchant_assistant.testing import offline_orchestrator

        tmp = Path(tempfile.mkdtemp(prefix="eval-"))
        offline = settings.model_copy(
            update={"runtime_dir": tmp, "qdrant_url": ":memory:", "retrieval_min_score": 0.05}
        )
        orchestrator, _ = offline_orchestrator(offline)
        if budget is not None:
            orchestrator.budget = budget
        mode, agent_provider, db_path = "scripted", "scripted", offline.db_path
    else:
        from merchant_assistant.main import build_orchestrator

        orchestrator = build_orchestrator(settings, budget=budget)
        mode, agent_provider, db_path = "real", "openai", settings.db_path
    if judge is not None:
        judge.meter = BudgetMeter(orchestrator.budget)
    rows = run(orchestrator, cases, judge=judge, repeat=repeat, keep_evidence=repeat > 1)
    summary = summarize(rows)
    if judge is not None and repeat > 1:
        summary["variation"] = aggregate.variation(rows, "assistant", repeat)
    config = {
        "mode": mode,
        "model": orchestrator.llm.model,
        "agent_provider": agent_provider,
        "embedding": settings.embedding_model,
        "split": args.split,
        "judge": bool(judge),
        "judge_config": judge.config() if judge else None,
        "repeat": repeat,
        "limit": case_limit,
        "include_replan": bool(getattr(args, "include_replan", False)),
        "campaign": getattr(args, "campaign", None),
        "campaign_cap_usd": getattr(args, "campaign_cap_usd", V080_QA_CAP_USD)
        if getattr(args, "campaign", None)
        else None,
        "cases": len(cases),
    }
    md, js = write_report(rows, summary, Path(args.out), _report_name(args), config)
    print(json.dumps(summary["overall"], indent=1))
    if judge is not None:
        _store_judgements(db_path, judge, rows, persist_judgements)
    if not args.no_conversations and args.split != "holdout_v080" and case_limit is None:
        from merchant_assistant.evaluation.runner import append_conversation_report, run_conversations

        conversations = run_conversations(orchestrator, scenarios / "followup.jsonl")
        append_conversation_report(md, js, conversations)
        print(f"conversations: {sum(c['passed'] for c in conversations)}/{len(conversations)} passed")
    print(f"report: {md}")
    print(f"results: {js}")
    if hasattr(orchestrator, "close"):
        orchestrator.close()
    return 0


def cmd_eval_rejudge(settings: Settings, args) -> int:
    """`eval --judge-repeat N --answers-from <report.json>`: the answers recorded by an earlier campaign (its first
    execution) graded N times, without running the agent. Variation of the judge alone (spec v0.8.0 D12)."""
    import tempfile

    from merchant_assistant.evaluation import aggregate
    from merchant_assistant.evaluation.runner import (
        BudgetMeter,
        load_recorded_answers,
        persist_judgements,
        rejudge,
        summarize,
        write_report,
    )

    if getattr(args, "campaign", None) is None and (
        getattr(args, "campaign_cap_usd", V080_QA_CAP_USD) != V080_QA_CAP_USD
        or getattr(args, "campaign_estimate", None) is not None
    ):
        raise SystemExit("eval: --campaign-cap-usd and --campaign-estimate require --campaign v080-qa.")
    if not args.answers_from:
        raise SystemExit("eval: --judge-repeat needs --answers-from <report.json> (a campaign that recorded answers).")
    if getattr(args, "repeat", 1) > 1:
        raise SystemExit(
            "eval: --repeat (variation of the assistant) and --judge-repeat (variation of the judge) are not "
            "combined: run the first, then grade its recorded answers with the second."
        )
    if args.judge_repeat < 1:
        raise SystemExit("eval: --judge-repeat must be at least 1.")
    if getattr(args, "split", "all") != "all":
        print("eval: --split is ignored with --judge-repeat; the cases are the recorded answers.", file=sys.stderr)
    try:
        rows, source = load_recorded_answers(Path(args.answers_from))
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"eval: {exc}") from None
    rows, selection = _select_recorded_answers(rows, args)
    splits = {row["split"] for row in rows}
    name = _report_name(args, next(iter(splits)) if len(splits) == 1 else None)
    if (Path(args.out) / f"{name}.json").resolve() == Path(args.answers_from).resolve():
        raise SystemExit(f"eval: the report {name}.json would overwrite the answers being graded; use another --name.")
    judge_plan = (
        _eval_judge_preflight(
            settings, agent_model=source.get("model"), agent_provider=source.get("agent_provider")
        )
        if not args.scripted
        else None
    )
    budget = _eval_budget_for_args(settings, args) if not args.scripted else None
    judge = _eval_judge(
        settings,
        scripted=args.scripted,
        agent_model=source.get("model"),
        agent_provider=source.get("agent_provider"),
        validated_plan=judge_plan,
    )
    if args.scripted:
        db_path, mode = Path(tempfile.mkdtemp(prefix="eval-")) / "merchant.sqlite3", "scripted"
    else:
        judge.meter = BudgetMeter(budget, request_id="eval-judge-repeat")
        db_path, mode = settings.db_path, "real"
    graded = rejudge(rows, judge, args.judge_repeat)
    summary = summarize(graded)
    summary["variation"] = aggregate.variation(graded, "judge", args.judge_repeat)
    config = {
        "mode": mode,
        "model": source.get("model"),
        "agent_provider": source.get("agent_provider", "openai"),
        "embedding": source.get("embedding", settings.embedding_model),
        "split": source.get("split"),
        "judge": True,
        "judge_config": judge.config(),
        "repeat": 1,
        "judge_repeat": args.judge_repeat,
        "answers_from": Path(args.answers_from).name,
        **selection,
        "campaign": getattr(args, "campaign", None),
        "campaign_cap_usd": getattr(args, "campaign_cap_usd", V080_QA_CAP_USD)
        if getattr(args, "campaign", None)
        else None,
        "cases": len(graded),
    }
    md, js = write_report(graded, summary, Path(args.out), name, config)
    print(json.dumps(summary["overall"], indent=1))
    _store_judgements(db_path, judge, graded, persist_judgements)
    print(f"report: {md}")
    print(f"results: {js}")
    return 0


def _select_recorded_answers(rows: list[dict], args) -> tuple[list[dict], dict]:
    """`--only-sample <csv>` keeps the recorded answers whose request_id is in the calibration CSV, in the order of the
    CSV (spec v0.9.0 D1); `--limit K` then keeps the first K (the probe). Returns the rows and what was filtered, which
    goes into the report's configuration."""
    only, limit = getattr(args, "only_sample", None), getattr(args, "limit", None)
    if limit is not None and limit < 1:
        raise SystemExit("eval: --limit must be at least 1.")
    if only is None and limit is None:
        return rows, {}
    selection: dict = {"recorded_answers": len(rows)}
    if only is not None:
        from merchant_assistant.evaluation import calibration

        try:
            wanted = calibration.sample_request_ids(Path(only))
        except calibration.CalibrationError as exc:
            raise SystemExit(f"eval: --only-sample: {exc}") from None
        by_id = {row["request_id"]: row for row in rows}
        missing = [request_id for request_id in wanted if request_id not in by_id]
        if missing:
            raise SystemExit(
                f"eval: --only-sample: {len(missing)} of the {len(wanted)} request ids of {Path(only).name} are not "
                f"among the recorded answers (for example {missing[0]}); use the report the sample was drawn from."
            )
        rows = [by_id[request_id] for request_id in wanted]
        selection |= {"only_sample": Path(only).name, "only_sample_ids": len(wanted)}
    if limit is not None:
        rows = rows[:limit]
        selection["limit"] = limit
    selection["selected_answers"] = len(rows)
    print(
        f"eval: grading {len(rows)} of {selection['recorded_answers']} recorded answers"
        + (f" ({selection['only_sample_ids']} request ids in {selection['only_sample']})" if only else "")
        + (f", --limit {limit}" if limit is not None else "")
        + ".",
        file=sys.stderr,
    )
    return rows, selection


def cmd_eval_estimate(settings: Settings, args) -> int:
    """Estimate all v0.8.0 splits from a report with five measured first-run cases.

    No model is called.
    """
    source = Path(args.source)
    try:
        source_bytes = source.read_bytes()
    except OSError as exc:
        raise SystemExit(f"eval-estimate: cannot read report: {exc}") from None
    try:
        output = _build_v080_campaign_estimate(source.name, source_bytes)
    except ValueError as exc:
        raise SystemExit(f"eval-estimate: {exc}") from None

    output_path = getattr(args, "out", None)
    if output_path is not None:
        destination = Path(output_path)
        if source.resolve() == destination.resolve():
            raise SystemExit("eval-estimate: --out must differ from the measured source report.")
        rendered = json.dumps(output, indent=1, ensure_ascii=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered + "\n", encoding="utf-8")
        output["estimate_file"] = str(destination)
    print(json.dumps(output, indent=1, ensure_ascii=False))
    return 0


def _build_v080_campaign_estimate(source_name: str, source_bytes: bytes) -> dict:
    """Validate one measured report and deterministically build its complete estimate artifact."""
    from collections import Counter

    from merchant_assistant.evaluation.campaign import estimate_campaign_cost
    from merchant_assistant.evaluation.runner import load_cases

    try:
        report = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot parse measured source report: {exc}") from None
    config = report.get("config") if isinstance(report, dict) else None
    rows = report.get("cases") if isinstance(report, dict) else None
    if not isinstance(config, dict) or not config.get("judge") or not isinstance(rows, list):
        raise ValueError("source must be an eval report with judge measurements.")
    judge_config = config.get("judge_config")
    if (
        config.get("mode") != "real"
        or config.get("agent_provider") == "scripted"
        or not isinstance(judge_config, dict)
        or not isinstance(judge_config.get("provider"), str)
        or not isinstance(judge_config.get("model"), str)
        or judge_config.get("provider") == "scripted"
        or judge_config.get("model") == "scripted-judge-v3"
        or not isinstance(config.get("agent_provider"), str)
        or not isinstance(config.get("model"), str)
        or (config.get("agent_provider"), config.get("model"))
        == (judge_config.get("provider"), judge_config.get("model"))
    ):
        raise ValueError(
            "use a real paid sample with an independent judge; scripted reports cannot set the QA cap."
        )
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("report contains an invalid case row.")
    if (
        isinstance(config.get("repeat", 1), bool)
        or config.get("repeat", 1) != 1
        or any(row.get("repetition", 1) != 1 for row in rows)
    ):
        raise ValueError("use the single-run five-case measurement, not a repeated campaign report.")
    first_rows = rows
    if not first_rows:
        raise ValueError("report has no first-run measurements.")
    for row in first_rows:
        judge_row = row.get("judge")
        if not isinstance(judge_row, dict) or judge_row.get("state") != "completed":
            raise ValueError(f"case {row.get('id', '?')} has an incomplete judge result.")
        if (
            judge_row.get("provider") != judge_config["provider"]
            or judge_row.get("model") != judge_config["model"]
            or not isinstance(judge_row.get("scores"), dict)
            or not {"groundedness", "factual_correctness", "relevance", "usefulness"} <= set(judge_row["scores"])
        ):
            raise ValueError(
                f"case {row.get('id', '?')} has an incomplete or inconsistent judge result."
            )

    scenarios = PROJECT_ROOT / "tests" / "scenarios"
    all_cases = load_cases(
        [
            scenarios / "challenge_examples.jsonl",
            scenarios / "core_cases.jsonl",
            scenarios / "business_journeys.jsonl",
            scenarios / "replan.jsonl",
        ]
    )
    case_counts = dict(Counter(case.split for case in all_cases))
    case_counts["holdout_v080"] = V080_HOLDOUT_CASE_COUNT
    followup_path = scenarios / "followup.jsonl"
    try:
        followups = [
            json.loads(line)
            for line in followup_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read follow-up scenarios: {exc}") from None
    if any(not isinstance(row, dict) or not isinstance(row.get("turns"), list) for row in followups):
        raise ValueError("follow-up scenarios have an invalid format.")
    try:
        projection = estimate_campaign_cost(
            rows,
            case_counts,
            followup_conversations=len(followups),
            followup_turns=sum(len(row["turns"]) for row in followups),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from None
    if projection["measured_agent_cost_usd"] <= 0 or projection["measured_first_judge_cost_usd"] <= 0:
        raise ValueError("both measured agent and completed judge costs must be positive.")
    estimated_cost = projection["estimated_cost_usd"]
    recommended_cap = (
        0.50
        if estimated_cost <= 0.50
        else 1.00
        if estimated_cost <= 1.00
        else V080_QA_EXCEPTIONAL_CAP_USD
        if estimated_cost <= V080_QA_EXCEPTIONAL_CAP_USD
        else None
    )
    output = {
        "estimate_format_version": 1,
        "campaign": V080_QA_CAMPAIGN,
        "campaign_cap_usd": recommended_cap,
        "requires_supervisor_decision": estimated_cost > V080_QA_EXCEPTIONAL_CAP_USD,
        "source_report": source_name,
        "agent_model": config.get("model"),
        "judge": config.get("judge_config"),
        **projection,
    }
    output["within_campaign_cap"] = recommended_cap is not None
    return output


def _verified_v080_campaign_estimate(estimate_path: Path) -> float:
    """Revalidate the measured report and full projection before accepting a USD 1.00 cap."""
    try:
        artifact = json.loads(estimate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"eval: cannot read --campaign-estimate: {exc}") from None
    if not isinstance(artifact, dict):
        raise SystemExit("eval: --campaign-estimate must be the complete output of eval-estimate.")
    source_name = artifact.get("source_report")
    if (
        not isinstance(source_name, str)
        or not source_name
        or Path(source_name).name != source_name
        or "/" in source_name
        or "\\" in source_name
        or ":" in source_name
    ):
        raise SystemExit("eval: --campaign-estimate has no safe measured source-report reference.")
    try:
        source_bytes = (estimate_path.parent / source_name).read_bytes()
    except OSError as exc:
        raise SystemExit(f"eval: cannot read measured source report beside --campaign-estimate: {exc}") from None
    try:
        expected = _build_v080_campaign_estimate(source_name, source_bytes)
    except ValueError as exc:
        raise SystemExit(f"eval: --campaign-estimate source is invalid: {exc}") from None
    if artifact != expected:
        raise SystemExit("eval: --campaign-estimate was altered or does not match the validated source projection.")
    return expected["estimated_cost_usd"]


def cmd_eval_calibrate(settings: Settings, args) -> int:
    """`eval-calibrate`: `--sample` writes the CSV the owner rates, without the judge's scores; `--import` reads it
    back, stores the ratings in `calibrations` and measures the agreement with the judge (spec v0.8.0 D10, D19). No
    model is called."""
    from merchant_assistant.evaluation import calibration

    size, filled = getattr(args, "sample", None), getattr(args, "import_csv", None)
    if (size is None) == (filled is None):
        raise SystemExit("eval-calibrate: choose --sample N --from <report.json>, or --import <csv>.")
    if size is not None and getattr(args, "judge", None):
        raise SystemExit("eval-calibrate: --judge is used with --import (the sample never shows a judge's scores).")
    evidence_dir = PROJECT_ROOT / "docs" / "evidence"
    try:
        if size is not None:
            if not args.source:
                raise SystemExit("eval-calibrate: --sample needs --from <report.json> (a campaign with --judge).")
            seed = calibration.DEFAULT_SEED if args.seed is None else args.seed
            split = getattr(args, "split", "development")
            rows, meta = calibration.make_sample(Path(args.source), size, seed, args.campaign, split)
            out = Path(args.out) if args.out else evidence_dir / "v080-calibracao-amostra.csv"
            calibration.write_csv(out, rows, meta, delimiter=args.delimiter)
            print(
                f"sample: {len(rows)} answers of {meta['eligible']} eligible, seed {seed}, campaign {meta['campaign']}"
            )
            print(f"csv: {out}")
            if meta["left_out"]:
                left = ", ".join(f"{name} {count}" for name, count in sorted(meta["left_out"].items()))
                print(
                    f"eval-calibrate: judged answers left out of the sample (only {meta['splits']} are drawn; the "
                    f"holdout_v080 is never sampled, D17): {left}.",
                    file=sys.stderr,
                )
            if len(rows) < calibration.DEFAULT_SAMPLE:
                print(
                    f"eval-calibrate: the sample has {len(rows)} answers; RF-91 asks for at least "
                    f"{calibration.DEFAULT_SAMPLE}.",
                    file=sys.stderr,
                )
            return 0
        if not settings.db_path.exists():
            raise SystemExit(f"eval-calibrate: no database at {settings.db_path}: the judgements are stored there.")
        from merchant_assistant.data.db import connect

        conn = connect(settings.db_path)
        try:
            result = calibration.import_filled(
                conn, Path(filled), rater=args.rater, campaign=args.campaign, judge=getattr(args, "judge", None)
            )
        finally:
            conn.close()
        out = Path(args.out) if args.out else evidence_dir / "v080-calibracao.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result["report"], encoding="utf-8")
        counts = result["counts"]
        withdrawn = f", {len(result['removed'])} removed" if result["removed"] else ""
        print(
            f"calibrations: {counts['created']} stored, {counts['updated']} updated, {len(result['skipped'])} skipped"
            f"{withdrawn} (campaign {result['meta']['campaign']}, rater {result['rater']})"
        )
        if result.get("comparison"):
            compared = result["comparison"]
            print(
                f"judges: {compared['judge']} (campaign {compared['campaign']}) beside {compared['original_judge']} "
                f"(campaign {compared['original_campaign']}), {result['analysis']['n']} human ratings"
            )
        if result["outside"]:
            print(
                f"eval-calibrate: {len(result['outside'])} rating(s) of this campaign and rater are in the database "
                f"but not in this file ({', '.join(result['outside'])}); they stay as they are.",
                file=sys.stderr,
            )
        print(f"report: {out}")
        return 0
    except calibration.CalibrationError as exc:
        shown = exc.messages[: calibration.MAX_REPORTED_ERRORS]
        more = len(exc.messages) - len(shown)
        lines = [f"eval-calibrate: {shown[0]}", *shown[1:], *([f"(+{more} more)"] if more else [])]
        raise SystemExit("\n".join(lines)) from None


def cmd_migrate(settings: Settings, args) -> int:
    """Moves the database schema to a version (default: latest). Use --to to roll back."""
    import sqlite3

    from merchant_assistant.data.migrations import RollbackRefused, current_version, migrate

    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, isolation_level=None)
    try:
        steps = migrate(conn, args.to)
        for step in steps or ["nothing to apply"]:
            print(step)
        print(f"schema version: {current_version(conn)}")
    except RollbackRefused as exc:
        raise SystemExit(f"migrate: {exc}") from None
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
    identity = Identity(settings)
    factory = env_factory_for(settings.db_path, principal, SystemClock(settings.timezone), services)
    serve_stdio(build_server(factory, authorize=lambda conn: principal_for_token(identity, conn, token)))
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


def _operator_principal(settings: Settings, conn):
    """The operator of MERCHANT_ASSISTANT_TOKEN (spec D12), verified like on the API."""
    from merchant_assistant.api.identity import HANDOFF_OPERATE, Identity, InvalidToken

    token = settings.merchant_assistant_token.get_secret_value() if settings.merchant_assistant_token else ""
    try:
        principal, _ = Identity(settings).verify(token, conn)
    except InvalidToken:
        raise SystemExit("operator: MERCHANT_ASSISTANT_TOKEN is missing, invalid or expired.") from None
    if principal.role != "operator" or not principal.has(HANDOFF_OPERATE):
        raise SystemExit("operator: the token is not an operator token (handoff:operate).")
    return principal


def operator_orchestrator(settings: Settings):
    """Orchestrator used by `operator act` to resume the flow (the real system; replaced in tests)."""
    from merchant_assistant.main import build_orchestrator

    return build_orchestrator(settings)


def cmd_operator(settings: Settings, args) -> int:
    """Operator queue in-process over the same service as the API (`handoffs`)."""
    import uuid

    from merchant_assistant import handoffs
    from merchant_assistant.data.db import connect

    conn = connect(settings.db_path)
    try:
        principal = _operator_principal(settings, conn)
        operator_id = principal.principal_id.split(":", 1)[1]
        if args.operator_command == "list":
            result = {"cases": handoffs.list_cases(conn, args.state, actor=principal.principal_id)}
        elif args.operator_command == "show":
            result = handoffs.get_case(conn, args.case_id, actor=principal.principal_id)
        else:
            key = args.idempotency_key or f"cli-{uuid.uuid4().hex[:20]}"
            from merchant_assistant.api.webhooks import Webhooks

            orchestrator = operator_orchestrator(settings)  # resumes the flow in-process (paid model calls)
            webhooks = Webhooks(settings)  # conversation.replied to the ticketing and the merchant, as in the API
            try:
                result = handoffs.act(
                    conn,
                    args.case_id,
                    operator_id,
                    args.action,
                    args.text,
                    key,
                    actor=principal.principal_id,
                    resume=webhooks.resume_point(orchestrator.resume_handoff),
                )
            finally:
                attempts = settings.webhook_max_attempts
                webhooks.wait(timeout=settings.webhook_timeout_s * attempts + sum(settings.webhook_waits))
                if hasattr(orchestrator, "close"):
                    orchestrator.close()
    except handoffs.HandoffError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}), file=sys.stderr)
        return 1
    finally:
        conn.close()
    print(json.dumps(result, indent=1, ensure_ascii=False, default=str))
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
    p_eval.add_argument("--mode", choices=["dense", "hybrid"], default=None, help="Default: RETRIEVAL_MODE.")
    p_boot = sub.add_parser("bootstrap", help="Seed synthetic data and build the index if needed.")
    p_boot.add_argument("--force-index", action="store_true")
    p_ask = sub.add_parser("ask", help="Run one message through the real system (paid).")
    p_ask.add_argument("message")
    p_ask.add_argument("--user-id", default="cliente1988")
    p_ask.add_argument("--conversation-id", default=None)
    p_ask.add_argument("--trace", action="store_true")
    p_evalx = sub.add_parser("eval", help="End-to-end evaluation over the labeled scenarios.")
    p_evalx.add_argument("--scripted", action="store_true", help="Offline scripted model (zero cost).")
    p_evalx.add_argument(
        "--judge",
        action="store_true",
        help="Add the model-graded rubric judge.v3 (paid). The judge is set by JUDGE_PROVIDER and JUDGE_MODEL "
        "(default deepseek/deepseek-flash), which need DEEPSEEK_API_KEY (anthropic/claude-opus-5-5 needs "
        "ANTHROPIC_API_KEY). Refused, before any call, when the judge equals the agent or its key is missing.",
    )
    p_evalx.add_argument("--split", choices=["all", "dev", "holdout", "holdout_v080"], default="all")
    p_evalx.add_argument(
        "--include-replan", action="store_true", help="Include the four v0.8.0 replanning scenarios in this evaluation."
    )
    p_evalx.add_argument(
        "--repeat", type=int, default=1, help="Run the agent N times per case; the judge grades each answer once."
    )
    p_evalx.add_argument(
        "--judge-repeat",
        type=int,
        default=None,
        help="Grade the answers recorded by --answers-from N times; the agent does not run.",
    )
    p_evalx.add_argument(
        "--answers-from", default=None, help="Report JSON of an earlier campaign (used with --judge-repeat)."
    )
    p_evalx.add_argument(
        "--only-sample",
        default=None,
        help="With --judge-repeat: grade only the answers whose request_id is in this calibration CSV, in its order.",
    )
    p_evalx.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run at most N cases for a measured cost sample; follow-up conversations are skipped. With "
        "--judge-repeat: grade at most N recorded answers (after --only-sample).",
    )
    p_evalx.add_argument(
        "--campaign",
        choices=[V080_QA_CAMPAIGN],
        default=None,
        help="Reserve every paid call against the one-time v080-qa cap as well as the installation ledger.",
    )
    p_evalx.add_argument(
        "--campaign-cap-usd",
        type=float,
        choices=[V080_QA_CAP_USD, V080_QA_MAX_CAP_USD, V080_QA_EXCEPTIONAL_CAP_USD, V080_QA_CONTINGENCY_CAP_USD],
        default=V080_QA_CAP_USD,
        help=(
            "Fixed cap for v080-qa (USD 1.00 requires a verified estimate above USD 0.50; "
            "USD 1.10 and 1.40 require one above USD 1.00; each needs --campaign-estimate). USD 1.40 only continues "
            "the mounted campaign after the reviewed contingency transition and never mounts a new one."
        ),
    )
    p_evalx.add_argument(
        "--campaign-estimate",
        default=None,
        help="Measured eval-estimate JSON; required for a USD 1.00, 1.10 or 1.40 cap.",
    )
    p_evalx.add_argument("--out", default=str(PROJECT_ROOT / "docs" / "evidence"))
    p_evalx.add_argument(
        "--name",
        default=None,
        help="Report name (default: avaliacao, avaliacao-holdout-v080 or, with --judge-repeat, avaliacao-juiz with "
        "the split of the answers appended, for example avaliacao-juiz-holdout-v080).",
    )
    p_evalx.add_argument("--no-conversations", action="store_true", help="Skip the multi-turn scenarios.")
    p_estimate = sub.add_parser(
        "eval-estimate", help="Project the v0.8.0 campaign cost from a five-case measured eval report (no model call)."
    )
    p_estimate.add_argument("--from", dest="source", required=True, help="Measured eval report JSON.")
    p_estimate.add_argument("--out", default=None, help="Optional JSON output path for the measured estimate.")
    p_calibrate = sub.add_parser(
        "eval-calibrate",
        help="Human calibration of the judge: --sample writes the CSV to rate, --import measures the agreement.",
    )
    p_calibrate.add_argument("--sample", type=int, default=None, help="Draw N answers (at least 24) into a CSV.")
    p_calibrate.add_argument("--from", dest="source", default=None, help="Campaign report JSON (used with --sample).")
    p_calibrate.add_argument("--import", dest="import_csv", default=None, help="The CSV the owner filled in.")
    p_calibrate.add_argument("--seed", type=int, default=None, help="Seed of the draw (default 20261104).")
    p_calibrate.add_argument("--campaign", default=None, help="Campaign name (default: the report name).")
    p_calibrate.add_argument(
        "--split",
        choices=["development", "dev", "holdout"],
        default="development",
        help="Splits the sample is drawn from (default development: dev and holdout). The holdout_v080 is never "
        "sampled.",
    )
    p_calibrate.add_argument("--rater", default="owner", help="Who rated, stored with the ratings (with --import).")
    p_calibrate.add_argument(
        "--judge",
        default=None,
        help="With --import: compare the ratings with this judge (<provider>/<model>, e.g. anthropic/claude-opus-5-5) "
        "instead of the first judgement of any judge, under a new --campaign; the report adds the original campaign's "
        "judge side by side and each judge's consistency between repetitions.",
    )
    p_calibrate.add_argument(
        "--delimiter",
        choices=[";", ","],
        default=";",
        help="CSV separator (default ';', which a pt-BR spreadsheet opens; --import accepts ';', ',' and tab).",
    )
    p_calibrate.add_argument(
        "--out",
        default=None,
        help="Output file: the CSV (default docs/evidence/v080-calibracao-amostra.csv) or, with --import, the "
        "report (default docs/evidence/v080-calibracao.md).",
    )
    p_migrate = sub.add_parser("migrate", help="Apply or roll back schema migrations.")
    p_migrate.add_argument("--to", type=int, default=None, help="Target schema version (default: latest).")
    sub.add_parser("mcp", help="Serve the support tools over MCP (stdio) for the merchant of MERCHANT_ASSISTANT_TOKEN.")
    sub.add_parser("mcp-demo", help="Run an MCP client against the stdio server (uses MERCHANT_ASSISTANT_TOKEN).")
    p_smoke = sub.add_parser("smoke", help="Get a merchant token and send the 10 challenge examples to a running API.")
    p_smoke.add_argument("--url", default="http://localhost:8000")
    p_smoke.add_argument("--username", default="cliente1988")
    p_smoke.add_argument("--password", default=None, help="Default: DEMO_USER_PASSWORDS.")
    p_operator = sub.add_parser("operator", help="Operator queue (uses an operator MERCHANT_ASSISTANT_TOKEN).")
    operator_sub = p_operator.add_subparsers(dest="operator_command", required=True)
    p_list = operator_sub.add_parser("list", help="List handoff cases.")
    p_list.add_argument("--state", choices=["open", "claimed", "answered", "rejected", "closed"], default=None)
    p_show = operator_sub.add_parser("show", help="Show one case.")
    p_show.add_argument("case_id")
    p_act = operator_sub.add_parser("act", help="approve, reply or reject a case.")
    p_act.add_argument("case_id")
    p_act.add_argument("--action", choices=["approve", "reply", "reject"], required=True)
    p_act.add_argument("--text", default=None, help="Reply text (reply) or instruction (reject).")
    p_act.add_argument("--idempotency-key", default=None, help="Reuse it to retry the same action safely.")
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
        "eval-estimate": cmd_eval_estimate,
        "eval-calibrate": cmd_eval_calibrate,
        "migrate": cmd_migrate,
        "mcp": cmd_mcp,
        "mcp-demo": cmd_mcp_demo,
        "auth": cmd_auth_token,
        "operator": cmd_operator,
    }
    return handlers[args.command](settings, args)


if __name__ == "__main__":
    sys.exit(main())
