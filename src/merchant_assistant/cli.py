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


RERANK_EVAL_CAP_USD = 0.05  # task 81: reranker calls of one paid eval-retrieval run (about 0.0003 each)


def _retrieval_reranker(settings: Settings, *, fake: bool, budget):
    """The reranker of `eval-retrieval --rerank on`: the agent model through the budget meter, or the programmed
    model offline. Both go through a `CountingMeter` for the report."""
    from merchant_assistant.evaluation.retrieval import CountingMeter
    from merchant_assistant.llm.prompts import load_prompt
    from merchant_assistant.rag.rerank import Reranker

    if fake:
        from merchant_assistant.evaluation.scripted_policy import handler
        from merchant_assistant.llm.scripted import ScriptedLLM

        llm, inner = ScriptedLLM(handler), None
    else:
        from merchant_assistant.evaluation.runner import BudgetMeter
        from merchant_assistant.llm.openai_llm import OpenAILLM

        llm = OpenAILLM(_openai_client(settings), settings.agent_model)
        inner = BudgetMeter(budget, request_id="eval-retrieval-rerank", max_cost_usd=RERANK_EVAL_CAP_USD)
    return Reranker(llm, load_prompt(settings.prompts_dir, "rerank")), CountingMeter(inner)


def cmd_eval_retrieval(settings: Settings, args) -> int:
    from datetime import UTC, datetime

    from merchant_assistant.evaluation import retrieval
    from merchant_assistant.evaluation.retrieval import SealError, evaluate, record_run, render_markdown, split_cases
    from merchant_assistant.rag.chunk import chunk_document
    from merchant_assistant.rag.documents import load_all
    from merchant_assistant.rag.index import KnowledgeIndex, open_qdrant

    mode = getattr(args, "mode", None) or settings.retrieval_mode
    rerank = (getattr(args, "rerank", None) or (settings.rerank if mode == "hybrid" else "off")) == "on"
    split = getattr(args, "split", None) or "dev"
    # task 90, review P3-3: the floor here is the flag only, never RETRIEVAL_BM25_MIN_SCORE, so the four rows of the
    # D7 line are always measured without it and a row with the floor is always asked for
    given = getattr(args, "bm25_min_score", None)
    floor = given if given is not None else 0.0
    if rerank and mode != "hybrid":
        raise SystemExit("eval-retrieval: --rerank on runs after the hybrid fusion; use --mode hybrid.")
    if not 0 <= floor <= 1:
        raise SystemExit("eval-retrieval: --bm25-min-score is a fraction of the best BM25 score, from 0 to 1.")
    if floor > 0 and mode == "dense":
        raise SystemExit("eval-retrieval: --bm25-min-score filters the BM25 list of a fusion; use a hybrid mode.")
    if args.fake and split in retrieval.SEALED_SPLITS and retrieval.SCENARIOS == retrieval.PROJECT_SCENARIOS:
        # review P3-11: offline runs would show holdout results (the BM25 half is real) outside the measurement
        raise SystemExit(f"eval-retrieval: --fake does not run on the sealed {split}; it is measured once per mode "
                         "with the real embeddings (D8).")
    try:  # before any paid call: a holdout whose content no longer matches its seal is never measured
        cases, digest = split_cases(split)
    except SealError as exc:
        raise SystemExit(f"eval-retrieval: {exc}") from None
    budget = None if args.fake else _budget_guard(settings)
    embedder = build_embedder(settings, fake=args.fake, budget=budget)
    reranker, meter = _retrieval_reranker(settings, fake=args.fake, budget=budget) if rerank else (None, None)
    index = KnowledgeIndex(
        open_qdrant(":memory:", settings.runtime_path), "eval_retrieval", embedder, bm25_min_score=floor
    )
    manifest = index.rebuild([c for d in load_all(settings.data_dir) for c in chunk_document(d)])
    report = evaluate(index, cases, k=args.k, mode=mode, reranker=reranker, meter=meter)
    report["split"] = split
    report["mode"] = mode
    report["rerank"] = rerank
    report["measured_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    if digest is not None:  # D8: the report says the sealed holdout was used
        report["holdout"] = {"split": split, "sha256": digest, "seal": "ok", "used": True}
    if meter is not None:
        report["rerank_usage"] = meter.summary()
    report["bm25_corpus_hash"] = manifest["bm25_corpus_hash"]  # BM25 kept in memory, like this Qdrant
    report["embedding_model"] = embedder.model
    report["embedding_tokens"] = getattr(embedder, "tokens_used", 0)
    out = getattr(args, "out", None)
    if out:  # accumulated table of every split and configuration measured into this report, plus the D7 line
        out = Path(out)
        data_path = out.with_suffix(".json")
        previous = json.loads(data_path.read_text(encoding="utf-8")) if data_path.is_file() else None
        try:
            table = record_run(previous, report)
        except ValueError as exc:
            raise SystemExit(f"eval-retrieval: {exc}") from None
        out.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text(json.dumps(table, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        out.write_text(render_markdown(table), encoding="utf-8")
        print(render_markdown(table), file=sys.stderr)
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
    rubric: str | None = None,
):
    """The campaign judge (`eval --judge`): the scripted stand-in offline, otherwise the configured independent
    evaluator, or a refusal that leaves before anything is built or called (spec v0.8.0 D11). `rubric` is the stored
    version of the rubric (`--rubric`, spec v0.11.0 D6(g); `judge.v5` when `None`)."""
    from merchant_assistant.evaluation import judge as judge_module

    if scripted:
        from merchant_assistant.evaluation.scripted_judge import scripted_judge

        judge = scripted_judge(settings.prompts_dir, None, rubric=rubric)
        agent = ("scripted", agent_model or "scripted-v1")
    else:
        agent = (agent_provider or judge_module.AGENT_PROVIDER, agent_model or settings.agent_model)
        try:
            return judge_module.resolve_judge(settings, agent=agent, validated=validated_plan, rubric=rubric)
        except judge_module.JudgeRefused as exc:
            raise SystemExit(f"eval: {exc}") from None
    try:
        judge_module.check_independence(agent, (judge.provider, judge.model))
    except judge_module.JudgeRefused as exc:
        raise SystemExit(f"eval: {exc}") from None
    return judge


def _eval_judge_preflight(
    settings: Settings,
    *,
    agent_model: str | None = None,
    agent_provider: str | None = None,
    rubric: str | None = None,
):
    """Validate paid-judge configuration before opening the persistent budget ledger."""
    from merchant_assistant.evaluation import judge as judge_module

    agent = (agent_provider or judge_module.AGENT_PROVIDER, agent_model or settings.agent_model)
    try:
        return judge_module.validate_judge(settings, agent=agent, rubric=rubric)
    except judge_module.JudgeRefused as exc:
        raise SystemExit(f"eval: {exc}") from None


LITERAL_RULER = "literal"  # `eval --rubric literal` (task 90, D8): the journeys' literal ruler, judge at its default


def _eval_rubric(args) -> str:
    """The stored version of `--rubric`: the one named, else the configured default (`judge.RUBRIC_VERSION`, v5 under
    spec v0.11.0 D6(g)). `eval-calibrate` resolves through the same `judge.rubric_version`. `--rubric literal` names
    the ruler, not a rubric: the judge, if any, keeps the default one."""
    from merchant_assistant.evaluation import judge as judge_module

    choice = getattr(args, "rubric", None)
    try:
        return judge_module.rubric_version(None if choice == LITERAL_RULER else choice)
    except judge_module.JudgeRefused as exc:
        raise SystemExit(f"eval: {exc}") from None


def _eval_ruler(args, judged: bool) -> str:
    """The ruler of `passed` (spec v0.11.0 D8): `combined` when a judge grades the answers, `literal` with
    `--rubric literal` or without a judge (the content half needs a judgement)."""
    return "literal" if getattr(args, "rubric", None) == LITERAL_RULER or not judged else "combined"


def _report_name(args, answers_split: str | None = None, replan: str | None = None) -> str:
    """The report name: `--name`, or a default that never overwrites another kind of report (a holdout run is not the
    development run, a judge-only run is not the run it grades, and the judge's report on the holdout answers is not
    the one on the development answers: `answers_split` is the split the recorded answers belong to; a run without
    replanning is not the run with it: `replan` is the setting in force, `REPLAN` or `--replan`)."""
    if getattr(args, "name", None):
        return args.name
    if getattr(args, "judge_repeat", None) is not None:
        return "avaliacao-juiz" + ("" if answers_split in (None, "all") else "-" + answers_split.replace("_", "-"))
    name = "avaliacao-holdout-v080" if args.split == "holdout_v080" else "avaliacao"
    return name + ("-replan-off" if (replan or getattr(args, "replan", None)) == "off" else "")  # task 93


def _store_judgements(db_path, judge, rows, persist, run: str) -> None:
    """Stores the judgements under the execution name `run` (the report name), so a comparison can tell one execution
    of a judge from another on the same answers (spec v0.9.0 D1)."""
    from merchant_assistant.data.db import connect

    conn = connect(db_path)
    try:
        print(f"judgements stored in run_evaluations: {persist(conn, judge, rows, run=run)} (execution {run})")
    finally:
        conn.close()


def cmd_eval(settings: Settings, args) -> int:
    """End-to-end evaluation. --scripted runs offline at zero cost; otherwise the real system is used (paid).
    --repeat N runs the agent N times (variation of the assistant); --judge-repeat N grades recorded answers again
    (variation of the judge, `cmd_eval_rejudge`)."""
    import tempfile

    from merchant_assistant.evaluation import aggregate, evidence
    from merchant_assistant.evaluation.runner import (
        BudgetMeter,
        apply_ruler,
        load_cases,
        persist_judgements,
        run,
        summarize,
        write_report,
    )
    from merchant_assistant.evaluation.web_pages import WebPages

    if getattr(args, "campaign", None) is None and (
        getattr(args, "campaign_cap_usd", V080_QA_CAP_USD) != V080_QA_CAP_USD
        or getattr(args, "campaign_estimate", None) is not None
    ):
        raise SystemExit("eval: --campaign-cap-usd and --campaign-estimate require --campaign v080-qa.")
    if getattr(args, "judge_repeat", None) is not None:
        if getattr(args, "replan", None):
            print("eval: --replan is ignored with --judge-repeat: the agent does not run.", file=sys.stderr)
        return cmd_eval_rejudge(settings, args)
    # task 93 (D3): the ablation of the replanning; the configuration of the campaign records it
    settings = settings.model_copy(update={"replan": getattr(args, "replan", None) or settings.replan})
    if getattr(args, "claims_from", None):
        raise SystemExit("eval: --claims-from goes with --judge-repeat and --rubric v5 (it grades recorded answers).")
    if getattr(args, "only_route", None):
        print("eval: --only-route is ignored without --judge-repeat: it selects recorded answers.", file=sys.stderr)
    if getattr(args, "only_sample", None):
        print(
            "eval: --only-sample is ignored without --judge-repeat: this runs the agent over the whole selection of "
            "cases, not the sample.",
            file=sys.stderr,
        )
    repeat = getattr(args, "repeat", 1)
    if repeat < 1:
        raise SystemExit("eval: --repeat must be at least 1.")
    rubric = _eval_rubric(args)
    if not args.judge and getattr(args, "rubric", None) not in (None, LITERAL_RULER):
        print("eval: --rubric is ignored without --judge or --judge-repeat: no judge runs.", file=sys.stderr)
    ruler = _eval_ruler(args, bool(args.judge))
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
    judge_plan = _eval_judge_preflight(settings, rubric=rubric) if args.judge and not args.scripted else None
    budget = (
        _eval_budget_for_args(settings, args)
        if not args.scripted or getattr(args, "campaign", None) is not None
        else None
    )
    judge = (
        _eval_judge(settings, scripted=args.scripted, validated_plan=judge_plan, rubric=rubric) if args.judge else None
    )
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
    # task 87 (D2): the pages a web-search reply cited are fetched for the judge's evidence, after each reply and never
    # in the turn; the scripted run stays offline (its citations are example.com placeholders).
    pages = None if args.scripted else WebPages.from_settings(settings)
    with evidence.use_web_pages(pages):
        rows = run(orchestrator, cases, judge=judge, repeat=repeat, keep_evidence=repeat > 1)
    apply_ruler(rows, ruler)
    summary = summarize(rows)
    _note_web_evidence(summary, rows)
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
        "replan": settings.replan,
        "web_evidence": "on" if pages is not None else "off",
        "ruler": ruler,
        "campaign": getattr(args, "campaign", None),
        "campaign_cap_usd": getattr(args, "campaign_cap_usd", V080_QA_CAP_USD)
        if getattr(args, "campaign", None)
        else None,
        "cases": len(cases),
    }
    name = _report_name(args, replan=settings.replan)
    md, js = write_report(rows, summary, Path(args.out), name, config)
    _append_web_evidence(md, summary)
    print(json.dumps(summary["overall"], indent=1))
    if judge is not None:
        _store_judgements(db_path, judge, rows, persist_judgements, name)
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


def _note_web_evidence(summary: dict, rows: list[dict]) -> None:
    """Answers per form of the web note (task 87), in the JSON summary of the report."""
    from merchant_assistant.evaluation import evidence

    counts = evidence.web_note_counts(rows)
    if counts["answers"]:
        summary["web_evidence"] = counts


def _append_web_evidence(md: Path, summary: dict) -> None:
    from merchant_assistant.evaluation import evidence

    if "web_evidence" in summary:
        line = evidence.web_note_line(summary["web_evidence"])
        section = f"\n## Evidência da busca web\n\n{line}\n"
        md.write_text(md.read_text(encoding="utf-8") + section, encoding="utf-8")


def cmd_eval_compare(settings: Settings, args) -> int:
    """`eval-compare --a <report> --b <report>` (task 93, D3): the two reports paired by case and repetition, by
    criterion and route, with the bootstrap interval of the difference and the decisions of the `replan` step by
    origin. Reads the two JSON reports only: no model call, no settings used."""
    from merchant_assistant.evaluation.compare import write

    md, js, data = write(Path(args.a), Path(args.b), Path(args.out), args.name, seed=args.seed)
    passed = data["by_criterion"].get("passed")
    if passed:
        print(f"pairs: {data['pairs']}; passed A {passed['a']:.3f}, B {passed['b']:.3f}, B - A {passed['diff']:+.3f}")
    else:
        print(f"pairs: {data['pairs']}")
    unpaired = data["unpaired"]
    if unpaired["a_only"] or unpaired["b_only"]:
        print(f"unpaired: {len(unpaired['a_only'])} only in A, {len(unpaired['b_only'])} only in B")
    print(f"report: {md}")
    print(f"results: {js}")
    return 0


def cmd_eval_rejudge(settings: Settings, args) -> int:
    """`eval --judge-repeat N --answers-from <report.json>`: the answers recorded by an earlier campaign (its first
    execution) graded N times, without running the agent. Variation of the judge alone (spec v0.8.0 D12)."""
    import tempfile

    from merchant_assistant.evaluation import aggregate
    from merchant_assistant.evaluation.runner import (
        BudgetMeter,
        apply_ruler,
        load_cases,
        load_recorded_answers,
        mark_journeys,
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
    rubric = _eval_rubric(args)
    if getattr(args, "split", "all") != "all":
        print("eval: --split is ignored with --judge-repeat; the cases are the recorded answers.", file=sys.stderr)
    try:
        rows, source = load_recorded_answers(Path(args.answers_from))
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"eval: {exc}") from None
    rows, selection = _select_recorded_answers(rows, args)
    given_claims = _claims_from(args, rows, rubric)
    if given_claims is not None:
        selection["claims_from"] = [Path(path).name for path in _listed_args(args.claims_from)]
    splits = {row["split"] for row in rows}
    name = _report_name(args, next(iter(splits)) if len(splits) == 1 else None)
    if (Path(args.out) / f"{name}.json").resolve() == Path(args.answers_from).resolve():
        raise SystemExit(f"eval: the report {name}.json would overwrite the answers being graded; use another --name.")
    judge_plan = (
        _eval_judge_preflight(
            settings, agent_model=source.get("model"), agent_provider=source.get("agent_provider"), rubric=rubric
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
        rubric=rubric,
    )
    if args.scripted:
        db_path, mode = Path(tempfile.mkdtemp(prefix="eval-")) / "merchant.sqlite3", "scripted"
    else:
        judge.meter = BudgetMeter(budget, request_id="eval-judge-repeat")
        db_path, mode = settings.db_path, "real"
    graded = rejudge(rows, judge, args.judge_repeat, given_claims)
    ruler = _eval_ruler(args, True)
    mark_journeys(graded, load_cases([PROJECT_ROOT / "tests" / "scenarios" / "business_journeys.jsonl"]))
    apply_ruler(graded, ruler)
    summary = summarize(graded)
    _note_web_evidence(summary, graded)
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
        "ruler": ruler,
        "campaign": getattr(args, "campaign", None),
        "campaign_cap_usd": getattr(args, "campaign_cap_usd", V080_QA_CAP_USD)
        if getattr(args, "campaign", None)
        else None,
        "cases": len(graded),
    }
    md, js = write_report(graded, summary, Path(args.out), name, config)
    _append_web_evidence(md, summary)
    print(json.dumps(summary["overall"], indent=1))
    _store_judgements(db_path, judge, graded, persist_judgements, name)
    print(f"report: {md}")
    print(f"results: {js}")
    return 0


def _claims_from(args, rows: list[dict], rubric: str) -> dict[str, tuple[list[dict], str]] | None:
    """`--claims-from <sample-claims.csv>` (repeatable, task 89 round 2): the claims of calibration samples, so that a
    judge.v5 judgement grades the very claims the raters mark (paired by number). Every file is read and its SHA-256
    checked, and every answer to grade must have its list, before any call; None without the option."""
    paths = [Path(path) for path in _listed_args(getattr(args, "claims_from", None))]
    if not paths:
        return None
    from merchant_assistant.evaluation import calibration
    from merchant_assistant.evaluation import calibration_packets as packets

    if rubric != "5":
        raise SystemExit("eval: --claims-from needs --rubric v5 (only judge.v5 judges a list of claims).")
    found: dict[str, tuple[list[dict], str]] = {}
    for path in paths:
        try:
            read = packets.read_claims(calibration._read_text(path), calibration.META_KEYS)
        except (packets.ClaimsError, calibration.CalibrationError) as exc:
            raise SystemExit(f"eval: --claims-from {path.name}: {exc}") from None
        problems = packets.verify_claims(read, path.name)
        if problems:
            raise SystemExit(f"eval: --claims-from {problems[0]}")
        origin = f"{calibration.CLAIMS_FROM_SAMPLE}{path.name}#{read.meta['claims_sha256'][:12]}"
        for request_id, answer in read.answers.items():
            listed = [
                {"n": claim.n, "kind": claim.kind, "text": " ".join(claim.text.split())}
                for claim in sorted(answer.claims, key=lambda claim: claim.n)
            ]
            if request_id in found and found[request_id][0] != listed:
                raise SystemExit(
                    f"eval: --claims-from: the request {request_id} has different claims in two files; give one list."
                )
            found.setdefault(request_id, (listed, origin))
    missing = [row["request_id"] for row in rows if row["request_id"] not in found]
    if missing:
        raise SystemExit(
            f"eval: --claims-from: {len(missing)} of the {len(rows)} answers to grade have no claims in "
            f"{', '.join(path.name for path in paths)} (for example {missing[0]}); select them with --only-sample or "
            "give their sample's claims CSV. No call was made."
        )
    names = ", ".join(path.name for path in paths)
    print(f"eval: judging the claims of {names} ({len(rows)} answers, no listing call)")
    return found


def _select_recorded_answers(rows: list[dict], args) -> tuple[list[dict], dict]:
    """`--only-sample <csv>` keeps the recorded answers whose request_id is in the calibration CSV, in the order of the
    CSV (spec v0.9.0 D1); `--only-route R` keeps those the Router sent to route R (task 87: the web answers again with
    the pages); `--limit K` then keeps the first K (the probe). Returns the rows and what was filtered, which goes into
    the report's configuration."""
    only, limit = getattr(args, "only_sample", None), getattr(args, "limit", None)
    route = getattr(args, "only_route", None)
    if limit is not None and limit < 1:
        raise SystemExit("eval: --limit must be at least 1.")
    if only is None and limit is None and route is None:
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
    if route is not None:
        rows = [row for row in rows if row.get("route") == route]
        if not rows:
            raise SystemExit(f"eval: --only-route: no recorded answer has route {route!r}.")
        selection["only_route"] = route
    if limit is not None:
        rows = rows[:limit]
        selection["limit"] = limit
    selection["selected_answers"] = len(rows)
    print(
        f"eval: grading {len(rows)} of {selection['recorded_answers']} recorded answers"
        + (f" ({selection['only_sample_ids']} request ids in {selection['only_sample']})" if only else "")
        + (f", route {route}" if route is not None else "")
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
    from merchant_assistant.evaluation import calibration_packets as packets_module

    if getattr(args, "merge_panel", None) or getattr(args, "sample_csv", None):
        return _merge_panel(args)
    size, filled = getattr(args, "sample", None), getattr(args, "import_csv", None)
    raters = _calibrate_raters(args)
    two = any(len(entry) > 1 for entry in raters) or getattr(args, "adjudication", None) is not None
    if two and filled:
        raise SystemExit(
            "eval-calibrate: give the files with --rater <name> <sample.csv> [<sample-claims.csv>], not with --import."
        )
    if two and len(raters) == 1 and len(raters[0]) == 2 and getattr(args, "adjudication", None) is None:
        filled, two = raters[0][1], False  # one rater, one file, no claims: the v0.8.0 import, unchanged
    if two and filled is None:
        filled = ""
    if two and getattr(args, "campaign", None):
        raise SystemExit("eval-calibrate: with --rater files, each sample brings its campaign; leave out --campaign.")
    if (size is None) == (filled is None):
        raise SystemExit("eval-calibrate: choose --sample N --from <report.json>, or --import <csv>.")
    if size is None and not two and not filled:
        raise SystemExit("eval-calibrate: --import needs the CSV (or --rater <name> <sample.csv> ...).")
    if size is not None and (len(raters) > 1 or len(raters[0]) > 1 or getattr(args, "adjudication", None)):
        raise SystemExit("eval-calibrate: --rater and --adjudication are used with --import.")
    sample_only = ("exclude", "enrich", "packets", "seal", "scripted")
    if size is None and any(getattr(args, key, None) for key in sample_only):
        raise SystemExit("eval-calibrate: --exclude, --enrich, --packets, --seal and --scripted go with --sample.")
    if size is not None and getattr(args, "judge", None):
        raise SystemExit("eval-calibrate: --judge is used with --import (the sample never shows a judge's scores).")
    if getattr(args, "judge_run", None) and not getattr(args, "judge", None):
        raise SystemExit("eval-calibrate: --judge-run is used with --judge (it picks the execution of that judge).")
    majority = bool(getattr(args, "judge_majority", False))
    if majority and not getattr(args, "judge", None):
        raise SystemExit("eval-calibrate: --judge-majority is used with --judge (the majority of that judge's votes).")
    if majority and two:
        raise SystemExit(
            "eval-calibrate: --judge-majority compares one rater with the judge (--import <csv>); with two raters "
            "each block still brings the judgement of repetition 1."
        )
    blocks = _calibrate_blocks(args)
    evidence_dir = PROJECT_ROOT / "docs" / "evidence"
    try:
        if size is not None:
            if not args.source:
                raise SystemExit("eval-calibrate: --sample needs --from <report.json> (a campaign with --judge).")
            seed = calibration.DEFAULT_SEED if args.seed is None else args.seed
            split = getattr(args, "split", "development")
            enrich = [r for r in (getattr(args, "enrich", None) or "").split(",") if r.strip()]
            exclude = [Path(path) for path in getattr(args, "exclude", None) or []]
            sources = [Path(path) for path in _listed_args(args.source)]
            sealing = bool(getattr(args, "seal", False))
            drawn, meta = calibration.draw(
                sources, size, seed, args.campaign, split, exclude=exclude, enrich=enrich, exact=sealing
            )
            rows = calibration.sample_rows(drawn)
            out = Path(args.out) if args.out else evidence_dir / "v080-calibracao-amostra.csv"
            packed = None
            if getattr(args, "packets", False) or sealing:
                packed = _calibration_packets(settings, args, out, rows, drawn, meta)
            else:
                calibration.write_csv(out, rows, meta, delimiter=args.delimiter)
            print(
                f"sample: {len(rows)} answers of {meta['eligible']} eligible, seed {seed}, campaign {meta['campaign']}"
            )
            if meta.get("excluded") is not None:
                print(f"excluded: {meta['excluded']} answers already calibrated (request id)")
            if meta.get("enriched"):
                print(f"enriched: {meta['enriched']} of {len(rows)} in the routes {', '.join(enrich)}")
            print(f"csv: {out}")
            if packed:
                print(f"claims: {packed['claims']} ({meta['claims']})")
                print(f"packets: {packed['folder']}")
                if packed.get("seal"):
                    print(f"seal: {packed['digest']} in {packed['seal']}")
            if meta["left_out"]:
                left = ", ".join(f"{name} {count}" for name, count in sorted(meta["left_out"].items()))
                print(
                    f"eval-calibrate: judged answers left out of the sample (only {meta['splits']} are drawn; the "
                    f"holdout_v080 is never sampled, D17, unless --split all): {left}.",
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
        if two:
            try:
                result = calibration.import_raters(
                    conn,
                    [
                        calibration.RaterFiles(name, Path(e[1]), Path(e[2]) if len(e) > 2 else None, kind)
                        for e in raters
                        for name, kind in [_rater_entry(e[0])]
                    ],
                    adjudication=Path(args.adjudication) if getattr(args, "adjudication", None) else None,
                    blocks=blocks,
                    seal_path=PROJECT_ROOT / packets_module.SEAL_FILE,
                )
            finally:
                conn.close()
            out = Path(args.out) if args.out else evidence_dir / "v0110-calibracao.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(result["report"], encoding="utf-8")
            for group, counts in result["stored"].items():
                print(f"calibrations {group}: {counts['created']} stored, {counts['updated']} updated")
            sealed, every = result["scopes"][0][1], result["scopes"][1][1]
            print(
                f"answers: {every['n']} rated, {every['both']} by both raters, {every['gold']} with a gold label, "
                f"{sealed['n']} sealed; adjudicated: {len(result['adjudicated'])}"
            )
            print(f"report: {out}")
            return 0
        try:
            result = calibration.import_filled(
                conn,
                Path(filled),
                rater=_rater_name(args),
                campaign=args.campaign,
                judge=blocks[0][0] if blocks else None,
                judge_run=blocks[0][1] if blocks else None,
                rubric=blocks[0][2] if blocks else None,
                more=blocks[1:],
                majority=majority,
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
                f"judges: {compared['judge']} (campaign {compared['campaign']}, execution {compared['judge_run']}) "
                f"beside {compared['original_judge']} (campaign {compared['original_campaign']}, execution "
                f"{', '.join(compared['original_runs'])}), {result['analysis']['n']} human ratings"
            )
            for block in compared.get("blocks", []):
                print(
                    f"block {block['label']}: {block['judge']} judge.v{block['rubric']} "
                    f"(execution {', '.join(block['runs'])})"
                )
            if compared.get("majority"):
                print("verdict of each compared block: the majority of its completed judgements of each answer")
        if result["outside"]:
            print(
                f"eval-calibrate: {len(result['outside'])} rating(s) of this campaign and rater are in the database "
                f"but not in this file ({', '.join(result['outside'])}); they stay as they are.",
                file=sys.stderr,
            )
        print(f"report: {out}")
        return 0
    except calibration.CalibrationError as exc:
        # with two raters every divergence that needs an adjudication is listed, so one pass shows them all
        shown = exc.messages if two else exc.messages[: calibration.MAX_REPORTED_ERRORS]
        more = len(exc.messages) - len(shown)
        lines = [f"eval-calibrate: {shown[0]}", *shown[1:], *([f"(+{more} more)"] if more else [])]
        raise SystemExit("\n".join(lines)) from None


def _merge_panel(args) -> int:
    """`eval-calibrate --merge-panel <member1-claims.csv> <member2-claims.csv> --sample-csv <a.csv> <b.csv> --out
    <panel.csv>` (task 89 round 4, spec v0.11.0 D6(c)): the panel's label is the agreement of its two members. The
    sample CSVs are required and --out may not exist (round 5). No database, no model call."""
    from merchant_assistant.evaluation import calibration
    from merchant_assistant.evaluation import calibration_packets as packets_module

    claims, samples = getattr(args, "merge_panel", None), getattr(args, "sample_csv", None)
    if not claims:
        raise SystemExit("eval-calibrate: --sample-csv goes with --merge-panel <claims1.csv> <claims2.csv>.")
    others = (
        "sample",
        "import_csv",
        "rater",
        "adjudication",
        "judge",
        "judge_run",
        "rubric",
        "judge_majority",
        "exclude",
        "enrich",
    )
    if any(getattr(args, key, None) not in (None, False, []) for key in (*others, "packets", "seal")):
        raise SystemExit(
            "eval-calibrate: --merge-panel only joins the files of the two panel members; run --import afterwards."
        )
    if not samples:
        raise SystemExit(
            "eval-calibrate: --merge-panel needs --sample-csv <member1.csv> <member2.csv>, the sample CSVs of the two "
            "members in the order of their claims CSVs."
        )
    if not getattr(args, "out", None):
        raise SystemExit("eval-calibrate: --merge-panel needs --out <panel.csv> (the claims go to <panel>-claims.csv).")
    try:
        result = calibration.merge_panel(
            [Path(path) for path in claims],
            [Path(path) for path in samples],
            Path(args.out),
            seal_path=PROJECT_ROOT / packets_module.SEAL_FILE,
        )
    except calibration.CalibrationError as exc:
        raise SystemExit("\n".join(["eval-calibrate: " + exc.messages[0], *exc.messages[1:]])) from None
    for number, member in enumerate(result["members"], start=1):
        rated = f"{member['rated']} answers rated, "
        share = f" ({member['in_agreement'] / member['marked']:.0%})" if member["marked"] else ""
        print(
            f"member {number} ({member['claims'].name}): {rated}{member['marked']} claims marked; the same mark as "
            f"the other member on {member['in_agreement']}{share}"
        )
    print(f"panel claims: {result['claims']} ({result['claims_written']} marks of {result['claims_compared']} claims "
          "both members marked; blank where they differ)")
    print(
        f"panel sample: {result['sample']} ({result['scores_agreed']} of {result['scores_compared']} scores and "
        f"{result['verdicts_agreed']} of {result['both_rated']} verdicts in agreement; blank where they differ)"
    )
    if result["blank"]:
        print(
            f"left blank (not rated by the panel: one member did not rate it, or they agree on no score nor verdict): "
            f"{len(result['blank'])} answers"
        )
    return 0


def _calibrate_raters(args) -> list[list[str]]:
    """`--rater`: a name (`--rater lauro`, as before v0.11.0, or a string in a namespace built by hand), or one entry
    per `--rater <name> <sample.csv> [<sample-claims.csv>]` (task 89). Without it, the rater is `owner`."""
    value = getattr(args, "rater", None)
    if value is None:
        return [["owner"]]
    if isinstance(value, str):
        return [[value]]
    entries = [[value] if isinstance(value, str) else list(value) for value in value]
    for entry in entries:
        if not 1 <= len(entry) <= 3:
            raise SystemExit("eval-calibrate: --rater takes <name> [<sample.csv> [<sample-claims.csv>]].")
    if len(entries) > 1 and any(len(entry) == 1 for entry in entries):
        raise SystemExit("eval-calibrate: with more than one --rater, each one names its files.")
    return entries


def _rater_entry(token: str) -> tuple[str, str | None]:
    """`<name>`, `<name>:human` or `<name>:model:<models>` (spec v0.11.0 D4, Q22): the name and the declared kind."""
    from merchant_assistant.evaluation import calibration

    try:
        return calibration.parse_rater(token)
    except calibration.CalibrationError as exc:
        raise SystemExit(f"eval-calibrate: {exc.messages[0]}") from None


def _rater_name(args) -> str:
    """The rater of the one-rater import (the v0.8.0 calibration): a human one, with or without `:human`."""
    from merchant_assistant.evaluation import calibration

    name, kind = _rater_entry(_calibrate_raters(args)[0][0])
    if calibration.is_model(kind):
        raise SystemExit(
            "eval-calibrate: a model rater (a declared panel) is imported beside a human one, in the two-rater "
            "calibration; the one-rater import is the human calibration of v0.8.0."
        )
    return name


def _calibration_packets(settings: Settings, args, out: Path, rows, drawn, meta) -> dict:
    """`--packets` (and `--seal`, task 89): the claims of each answer (recorded by a judge.v5 judgement, else listed by
    one `judge_claims.v1` call per answer, through the budget guard; `--scripted` uses the scripted judge, for tests),
    then the sample CSV, the claims CSV (with the SHA-256 of its claims in the sample line) and one packet per answer;
    with `--seal`, the seal in `tests/scenarios/calibration_v0110.sha256`: the hash of the sample, of its identity and
    of every file written. An existing seal of another sample is refused before any claim is listed (its identity
    line), and a seal whose lines would change before anything is written."""
    from merchant_assistant.evaluation import calibration
    from merchant_assistant.evaluation import calibration_packets as packets

    seal_path = PROJECT_ROOT / packets.SEAL_FILE
    sealing = getattr(args, "seal", False)
    identity = packets.identity_digest(rows)
    existing = packets.read_seal_lines(seal_path) if sealing else None
    if existing is not None and existing.get(packets.IDENTITY_LINE) != identity:
        raise SystemExit(
            f"eval-calibrate: {packets.SEAL_FILE.as_posix()} already seals another sample (its answers are not these); "
            "a sealed sample does not change. Nothing was listed or written."
        )
    claims: dict[str, list[dict]] = {}
    origins: dict[str, str] = {}
    for row in drawn:
        listed = packets.recorded_claims(row)
        if listed is not None:
            claims[row["request_id"]], origins[row["request_id"]] = listed, packets.RECORDED
    missing = [row for row in drawn if row["request_id"] not in claims]
    judge_name = None
    if missing:
        config = json.loads(Path(_listed_args(args.source)[0]).read_text(encoding="utf-8")).get("config", {})
        scripted = getattr(args, "scripted", False)
        plan = (
            None
            if scripted
            else _eval_judge_preflight(
                settings, agent_model=config.get("model"), agent_provider=config.get("agent_provider"), rubric="5"
            )
        )
        budget = None if scripted else _evaluation_budget_guard(settings)
        judge = _eval_judge(
            settings,
            scripted=scripted,
            agent_model=config.get("model"),
            agent_provider=config.get("agent_provider"),
            validated_plan=plan,
            rubric="5",
        )
        if budget is not None:
            from merchant_assistant.evaluation.runner import BudgetMeter

            judge.meter = BudgetMeter(budget, request_id="eval-calibrate-claims")
        judge_name = f"{judge.provider}/{judge.model}"
        for row in missing:
            try:
                claims[row["request_id"]] = packets.list_claims(judge, row["judge_input"])
            except Exception as exc:  # nothing is written: the sample needs the claims of every answer
                raise SystemExit(
                    f"eval-calibrate: the claims of {row['request_id']} could not be listed "
                    f"({type(exc).__name__}); nothing was written."
                ) from None
            origins[row["request_id"]] = packets.LISTED
    recorded = sum(origin == packets.RECORDED for origin in origins.values())
    meta["claims"] = "+".join(
        part
        for part in (
            f"{packets.RECORDED}-{recorded}" if recorded else "",
            f"{packets.LISTED}-{judge_name.replace('/', '.')}-{len(missing)}" if missing else "",
        )
        if part
    )
    claim_rows = packets.claims_rows(rows, claims)
    digest = packets.seal_digest(packets.seal_entries(rows, claim_rows))
    meta["claims_sha256"] = packets.rows_digest(claim_rows)
    if sealing:
        meta["seal"] = packets.SEAL_NAME
    stamp = calibration.sample_stamp(rows, meta)
    files = {out: calibration.csv_bytes(rows, meta, delimiter=args.delimiter)}
    files |= packets.packet_files(
        out, rows, drawn, claims, origins, meta | {"drawn": len(rows)}, stamp, delimiter=args.delimiter
    )
    text = None
    if sealing:
        listed = [(path.relative_to(out.parent).as_posix(), packets.file_digest(data)) for path, data in files.items()]
        text = packets.seal_text(digest, identity, listed, meta | {"drawn": len(rows)})
        if existing is not None and existing != packets.seal_lines(text):
            raise SystemExit(
                f"eval-calibrate: {packets.SEAL_FILE.as_posix()} already seals this sample with other claims or files; "
                "a sealed sample does not change. Nothing was written."
            )
    packets.write_files(files)
    result = {"claims": packets.claims_path(out), "folder": packets.packets_dir(out), "digest": digest}
    if text is not None:
        seal_path.parent.mkdir(parents=True, exist_ok=True)
        seal_path.write_text(text, encoding="utf-8", newline="\n")
        result["seal"] = seal_path
    return result


def _listed_args(value) -> list:
    """An option given once (a string, as before v0.10.0) or repeated (`action="append"`), as a list."""
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def _calibrate_blocks(args) -> list[tuple[str, str | None, str | None]]:
    """`--judge`, `--judge-run` and `--rubric` of `eval-calibrate --import`, paired in order (spec v0.10.0, task 83):
    one block per `--judge`. With one judge, `--judge-run` and `--rubric` may be left out; with more, every judge
    needs its `--judge-run`. If `--rubric` is omitted, use the configured default (`judge.v5`); otherwise, give one
    value per judge."""
    judges, runs, rubrics = (_listed_args(getattr(args, key, None)) for key in ("judge", "judge_run", "rubric"))
    if rubrics and not judges:
        raise SystemExit("eval-calibrate: --rubric is used with --judge (the rubric of that judge's judgements).")
    if not judges:
        return []
    if len(judges) == 1:
        if len(runs) > 1 or len(rubrics) > 1:
            raise SystemExit("eval-calibrate: one --judge takes at most one --judge-run and one --rubric.")
        return [(judges[0], runs[0] if runs else None, rubrics[0] if rubrics else None)]
    if len(runs) != len(judges):
        raise SystemExit(
            f"eval-calibrate: {len(judges)} --judge need {len(judges)} --judge-run, in the same order "
            f"(got {len(runs)})."
        )
    if rubrics and len(rubrics) != len(judges):
        raise SystemExit(
            f"eval-calibrate: --rubric is given for every --judge or for none (got {len(rubrics)} for "
            f"{len(judges)} judges)."
        )
    return list(zip(judges, runs, rubrics or [None] * len(judges), strict=True))


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
    p_eval = sub.add_parser(
        "eval-retrieval", help="Measure Recall@k, MRR, nDCG@k and time per query on a labeled retrieval split."
    )
    p_eval.add_argument("--fake", action="store_true")
    p_eval.add_argument("-k", type=int, default=6)
    p_eval.add_argument(
        "--mode",
        choices=["dense", "hybrid", "hybrid@36"],
        default=None,
        help="Default: RETRIEVAL_MODE. hybrid@36 is the reranker's control: the fusion the reranker reads (depth 36) "
        "cut to k without a model.",
    )
    p_eval.add_argument(
        "--bm25-min-score",
        type=float,
        default=None,
        help="Drop, before the fusion, the hits only BM25 found whose BM25 score over the query's best is below this "
        "(0 to 1; default 0 = off; RETRIEVAL_BM25_MIN_SCORE is not read here). Measured as a configuration of its own.",
    )
    p_eval.add_argument(
        "--rerank", choices=["on", "off"], default=None, help="Rerank the hybrid top 12 (default: RERANK)."
    )
    p_eval.add_argument(
        "--split",
        choices=["dev", "holdout_v090"],
        default="dev",
        help="dev (retrieval.jsonl) or the sealed retrieval holdout (refused when its seal does not match).",
    )
    p_eval.add_argument(
        "--out",
        default=None,
        help="Markdown report (and .json beside it) that accumulates every split and configuration measured, "
        "with the D7 suggested default.",
    )
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
        help="Add the model-graded rubric judge.v5 by default (or the one --rubric names; paid). The judge is set by "
        "JUDGE_PROVIDER and JUDGE_MODEL "
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
        "--rubric",
        choices=["v3", "v4", "v5", LITERAL_RULER],
        default=None,
        help="Rubric of the judge with --judge or --judge-repeat: v3; v4, which also flags a general claim stated "
        "as fact with no source (spec v0.10.0 D1); or v5, two calls per judgement that list the claims of the reply "
        "and judge each one, the verdict computed from them (spec v0.11.0 D3). Left out, the default is judge.v5; use "
        "v3 to select the earlier single-call judge. Each judgement records the version. With a judge, an answer "
        "passes by the combined ruler "
        "(spec v0.11.0 D8: the deterministic checks without the required phrases, and the judge's content floor); "
        "literal keeps the earlier ruler (every deterministic check, required phrases included) with the default "
        "rubric.",
    )
    p_evalx.add_argument(
        "--only-sample",
        default=None,
        help="With --judge-repeat: grade only the answers whose request_id is in this calibration CSV, in its order.",
    )
    p_evalx.add_argument(
        "--claims-from",
        action="append",
        default=None,
        help="With --judge-repeat and --rubric v5: grade the claims of this calibration claims CSV "
        "(eval-calibrate --packets) instead of listing them, paired by number with the sample; repeatable. Every "
        "answer graded needs its list.",
    )
    p_evalx.add_argument(
        "--only-route",
        default=None,
        help="With --judge-repeat: grade only the recorded answers of this route (for example general_web).",
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
    p_evalx.add_argument(
        "--replan",
        choices=["on", "off"],
        default=None,
        help="Default: REPLAN (on). off is the ablation of the replanning: the fixed edges of v0.7.0, without the "
        "replan and web steps (the Router's initial plan; knowledge then support on the combined route; escalation "
        "when the Support asks for a human; the request limits hold). The configuration of the report records it, "
        "and the default name gets -replan-off.",
    )
    p_compare = sub.add_parser(
        "eval-compare",
        help="Pair two eval reports by case and repetition, by criterion and route, with a bootstrap interval of the "
        "difference and the replanning decisions by origin (no model call).",
    )
    p_compare.add_argument("--a", required=True, help="Report JSON of side A (for the ablation: REPLAN=off).")
    p_compare.add_argument("--b", required=True, help="Report JSON of side B (for the ablation: REPLAN=on).")
    p_compare.add_argument("--out", default=str(PROJECT_ROOT / "docs" / "evidence"))
    p_compare.add_argument("--name", default="comparacao-replan", help="Report name (.md and .json).")
    p_compare.add_argument("--seed", type=int, default=93, help="Seed of the bootstrap (default 93).")
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
    p_calibrate.add_argument(
        "--from",
        dest="source",
        action="append",
        default=None,
        help="Campaign report JSON (used with --sample). Repeatable: the reports of one campaign (the development run "
        "and the holdout_v080 run) are drawn together.",
    )
    p_calibrate.add_argument(
        "--import",
        dest="import_csv",
        nargs="?",
        const="",
        default=None,
        help="The CSV the owner filled in; with two raters, --import alone and the files in --rater.",
    )
    p_calibrate.add_argument("--seed", type=int, default=None, help="Seed of the draw (default 20261104).")
    p_calibrate.add_argument("--campaign", default=None, help="Campaign name (default: the report name).")
    p_calibrate.add_argument(
        "--split",
        choices=["development", "dev", "holdout", "all"],
        default="development",
        help="Splits the sample is drawn from (default development: dev and holdout; all adds the holdout_v080, for "
        "the v0.11.0 sample, which measures the judge and not the agent).",
    )
    p_calibrate.add_argument(
        "--rater",
        nargs="+",
        action="append",
        default=None,
        metavar="NAME[:KIND] [CSV [CLAIMS_CSV]]",
        help="Who rated (default owner), stored with the ratings (with --import). Task 89: repeat --rater "
        "<name>:human|model:<models> <sample.csv> [<sample-claims.csv>] for two raters, each with its kind (human, or "
        "model:<models> for a declared panel, e.g. painel:model:claude-opus+gpt-5); with the claims CSV the verdict "
        "is computed from the marks. One rater with one CSV is the v0.8.0 import, a human one.",
    )
    p_calibrate.add_argument(
        "--adjudication",
        default=None,
        help="With two raters: CSV with request_id, gold_verdict, gold_scores (criterion=value), reason and, "
        "optionally, gold_claims (n=mark); required wherever the raters diverge.",
    )
    p_calibrate.add_argument(
        "--merge-panel",
        nargs=2,
        default=None,
        metavar=("MEMBER1_CLAIMS_CSV", "MEMBER2_CLAIMS_CSV"),
        help="Join the files of the two members of a panel of models (same sample, checked by the SHA-256 of the "
        "claims and the identity of the answers) into the panel's: a mark, a score or the verdict where both gave "
        "the same, blank where they differ. Needs --sample-csv. Writes --out <panel.csv> and <panel>-claims.csv, "
        "neither of which may exist, for --import --rater <name>:model:<model1>+<model2>.",
    )
    p_calibrate.add_argument(
        "--sample-csv",
        nargs=2,
        default=None,
        metavar=("MEMBER1_CSV", "MEMBER2_CSV"),
        help="With --merge-panel (required): the sample CSVs of the two members, in the same order as their claims "
        "CSVs.",
    )
    p_calibrate.add_argument(
        "--exclude",
        action="append",
        default=None,
        help="With --sample: a calibration CSV whose answers (request_id) stay out. Repeatable.",
    )
    p_calibrate.add_argument(
        "--enrich",
        default=None,
        help="With --sample: comma-separated routes that hold at least half of the sample (e.g. "
        "knowledge,knowledge_and_support); a draw short of the size asked for is refused.",
    )
    p_calibrate.add_argument(
        "--packets",
        action="store_true",
        help="With --sample: also write <stem>-claims.csv and one <id>.md packet per answer in <stem>-pacotes/. "
        "Claims come from recorded judge.v5 judgements, else from one judge_claims.v1 call per answer (paid, "
        "through the budget guard).",
    )
    p_calibrate.add_argument(
        "--seal",
        action="store_true",
        help="With --sample (implies --packets): write the SHA-256 of the sample, of its identity and of every file "
        "written to tests/scenarios/calibration_v0110.sha256; --import refuses that sample if its hash changes. A draw "
        "short of the size asked for, or a seal of another sample, is refused before any claim is listed.",
    )
    p_calibrate.add_argument(
        "--scripted",
        action="store_true",
        help="With --packets: list the claims with the scripted judge (offline, for tests; not for a real sample).",
    )
    p_calibrate.add_argument(
        "--judge",
        action="append",
        default=None,
        help="With --import: compare the ratings with this judge (<provider>/<model>, e.g. anthropic/claude-opus-5-5) "
        "instead of the first judgement of any judge, under a new --campaign; the report adds the original campaign's "
        "judge side by side and each judge's consistency between repetitions. Repeat it (each with its --judge-run "
        "and, if any, --rubric, in the same order) for one block per judge, execution and rubric.",
    )
    p_calibrate.add_argument(
        "--judge-run",
        action="append",
        default=None,
        help="With --judge: the execution of that judge to compare (the --name of the eval that graded, e.g. "
        "v090-juiz-opus-r3). Required when the judge has more than one execution on the sample's answers (the probe "
        "and the repetitions, say), and for every --judge when there is more than one.",
    )
    p_calibrate.add_argument(
        "--rubric",
        action="append",
        choices=["v3", "v4", "v5"],
        default=None,
        help="With --judge: the rubric of that judge's judgements (configured default v5 when left out). With v3, v4, "
        "v5 or more than one --judge, the report has one block per judge beside the original, the table of the four "
        "claims with no source and the D2 line.",
    )
    p_calibrate.add_argument(
        "--judge-majority",
        action="store_true",
        help="With --import and --judge: compare each judge by the majority of its completed judgements of each answer "
        "in the execution (eval --judge-repeat 3), not by the first: unsupported_claim is yes when more than half say "
        "yes, each score is the median, the claim marks are those of the first judgement with the majority's verdict. "
        "An even number of judgements of an answer is refused (judge it once more under the same --name).",
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
        "eval-compare": cmd_eval_compare,
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
