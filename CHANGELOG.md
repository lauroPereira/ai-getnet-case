# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/). Each release lists features, contract and data changes, validation, notes and how to return to the previous version.

## [Unreleased]

### Changed
- **`401 token_required` says how to get a token.** The challenge's literal payload (`message` + `user_id`, no header) now gets a message that names `POST /v1/auth/token` with the password grant and the demo users of `.env.example`, then the `Authorization: Bearer` header; code, status and `WWW-Authenticate` are unchanged. Covered by `tests/integration/test_token_required_hint.py`.
- **`.env.example` ships `DEMO_MODE=true`** so `GET /traces/{request_id}` works on the documented Compose path (Compose interpolates the copied `.env`; a clean-clone smoke of the README found the 404). The code default stays `false`.
- README: the `/metrics` paragraph, the version table order, the `judge.v4` result table in the human review section and the `DEMO_MODE` rows.

## [0.10.0] — 2026-11-06 (validated: review and real QA)

Judge rubric `judge.v4`, resumable profile comparison, `/metrics` and alert rules ([spec](docs/specs/rubrica-operacao-v0100.md), [story](docs/historias/rubrica-operacao-v0100.md), [ADR 0022](docs/architecture/decisions/0022-rubrica-v4-operacao-retomavel.md), tasks 83–86).

### Added
- **Rubric `judge.v4`** (`prompts/judge.v4.md`, v3 untouched): an unsupported claim also covers a general claim stated as fact with no source in the evidence. `--rubric v3|v4` in `eval --judge-repeat` and `eval-calibrate --import`, resolved once (`--rubric` > configured default > v3); each judgement records the rubric it used. `eval-calibrate` accepts several `--judge`/`--judge-run`/`--rubric` triples and renders one block per (judge, execution, rubric) against the same human ratings, with the generic-claim table and the decision-rule line.
- **Resumable comparison.** A running comparison whose process dies becomes `interrupted` on startup or on read, keeping finished cells and recording the in-flight attempt at its reserved cost (`cost_is_estimate: true`, no trace row); `POST /v1/comparisons/{id}/resume[?retry_failed=true]` runs only the missing cells, reserves only what is left, accumulates `cost_usd` and answers `409 comparison_running | comparison_completed | nothing_to_resume | fixed_factors_changed`. The thread registry is claimed before `running` is visible and each thread releases only itself, so concurrent resumes run each cell once.
- **`GET /metrics`** in Prometheus text (exposition 0.0.4, no new dependency), computed on demand from `traces.sqlite3` and the ledger with a 5 s cache: `requests_total{route,status}`, `model_calls_total{agent}`, `tool_calls_total{tool,outcome}`, `tool_failures_total{tool}`, `handoffs_total`, `replan_total{origin}`, `request_duration_seconds` (histogram), `cost_usd_total{provider}`, `budget_remaining_usd`, `budget_limit_usd`. Every label comes from a closed set in the code (anything else is `other`; a drift test pins the sets); an empty, corrupt or locked store never returns 500 (the last complete reading is served).
- **`alerts/rules.yml`**: four Prometheus rules (budget below 10% of the cap, tool failure rate above 5% in 15 min, handoff rate above 30% in 1 h, p95 duration above 20 s in 15 min) with absolute runbook links; a test checks that every metric they cite exists.

### Changed
- `prompt_versions()` reports the configured judge rubric (v3), not the newest prompt file, so `/ready`, `prompt_set` and comparison reuse are unchanged.
- The `eval` report names the rubric actually used.

### Contract and data
- **Migration 0012** (reversible): `comparisons.state` accepts `interrupted` (table recreated with the wider `CHECK`; downgrade turns `interrupted` into `failed`). Schema version 12.
- New route `POST /v1/comparisons/{comparison_id}/resume`; `GET /v1/comparisons/{id}` may return `interrupted`, `interrupted_attempts` and `previous_request_ids`. New public endpoint `GET /metrics` (same policy as `/ready`). Judgement records gain the rubric used; no other schema change.

### Validation
- Backend strict script **2,148 tests passed**, Ruff and skill checks passed; independent review per task in two rounds ([83](docs/evidence/v0100-reviewer-t83.md), [84](docs/evidence/v0100-reviewer-t84.md), [85](docs/evidence/v0100-reviewer-t85.md)); candidate [r1](docs/evidence/v0100-candidato-r1.json).
- **Rubric experiment** ([report](docs/evidence/v0100-juiz-v4.md), [QA](docs/evidence/v0100-qa-juiz-r1.md)): the same 24 human-rated answers re-judged 3× under `judge.v4` by DeepSeek (US$0.025) and by `claude-opus-5-5` (US$1.37 on the separate Anthropic ledger), 144/144 valid. Decision rule written beforehand (spec D2): DeepSeek v4 vs v3: `unsupported_claim` agreement 0.667 → 0.792, criteria within 0.05, but 0 of 4 generic claims flagged, so v4 is **not** promoted; Opus v4 vs v3: 0.875 → 0.917 and 2 of 4 generic claims flagged (S01, S21) with no criterion worse than 0.05. The gap is rubric and model together.
- **Operation** ([QA](docs/evidence/v0100-qa-ops-r1.md)): real comparison of 2 profiles × 3 scenarios; the API process killed with `taskkill` after 1 of 6 cells; after restart the comparison read `interrupted` with the finished cell intact and the in-flight attempt's reserved cost recorded; `resume` answered `202 {resumed_cells: 5}` and the comparison reached `completed` with one ledger line per cell and `cost_usd` equal to the sum of cells plus the attempt; a second `resume` got `409 comparison_completed`. `/metrics` matched the traces and the ledger (6 requests, 24 model calls, `+Inf` = `_count`, costs per provider equal to the settled ledger, `budget_remaining_usd` equal to `/ready`); no label carried an identifier. Cost US$0.006 in an isolated ledger.

### Notes
- Run the API with one worker (the compose does): the comparison thread registry is per process.
- `/metrics` is public like `/ready` (counts only); restrict it by network or token in production.

### Return to 0.9.0
- Stop the stack, run `merchant-assistant migrate --to 11` against the runtime (any `interrupted` comparison becomes `failed`) and check out the 0.9.0 release. `judge.v4` and `/metrics` leave no data behind that 0.9.0 cannot read.

## [0.9.0] — 2026-11-06 (validated: review and real QA)

Judge model experiment and hybrid retrieval ([spec](docs/specs/juiz-retrieval-v090.md), [story](docs/historias/juiz-retrieval-v090.md), [ADR 0020](docs/architecture/decisions/0020-retrieval-hibrido-holdout.md), [ADR 0021](docs/architecture/decisions/0021-juiz-modelo-e-regua.md), tasks 79–82).

### Added
- **Anthropic judge.** `JUDGE_PROVIDER=anthropic` with `claude-opus-5-5` (also Sonnet and Haiku 5.5 priced, cache read and creation included) through the official SDK: structured output by JSON schema, `refusal` and `max_tokens` become failed judgements (never a score), tokens recorded per judgement. The default judge is unchanged (`deepseek/deepseek-flash`).
- **Judge experiment tooling.** `eval --judge-repeat N --answers-from <report> --only-sample <csv> [--limit K] --name <run>` re-judges the calibration sample only; each judgement stores the execution name. `eval-calibrate --import <csv> --judge <provider>/<model> --judge-run <name> --campaign <new>` compares another judge with the same human ratings, side by side with the original judge, with per-judge consistency, tokens and cost.
- **Hybrid retrieval.** In-process BM25 (`rank-bm25`; accent-free tokens, short pt/en stopword lists, codes and acronyms kept) persisted by corpus hash (`bm25-<hash>.pkl`, ids and tokens only; payloads always from the active index) and fused with the dense search by RRF (`k=60`, `3×k` candidates, dense tie-break, `origin` per hit). `RETRIEVAL_MODE=dense|hybrid`; `dense` is byte-identical to v0.8.0.
- **Reranker (off by default).** `rerank.v1` on the agent model reorders the first 12 hits of the hybrid fusion; `RERANK=on` needs `hybrid`; any failure returns exactly the `RERANK=off` result; metered per request and counted in `MAX_MODEL_CALLS`.
- **Sealed retrieval holdout** `retrieval_holdout_v090` (25 questions, 13 in Portuguese, graded relevance by `chunk_id`), written before any mode was measured, checked by hash in the suite; `eval-retrieval --mode --rerank --split dev|holdout_v090 --out <md>` with Recall@6, MRR, nDCG@6, time per query, reranker failures and the D7 suggestion line; `--fake` refuses the sealed split.

### Changed
- `RETRIEVAL_MODE` defaults to `hybrid` (decision D7, by the numbers below). `.env.example` documents `dense` as the v0.8.0 behavior.
- Five exact-term questions added to the development retrieval set (`tests/scenarios/retrieval.jsonl`); no existing question changed.

### Contract and data
- No migration. `run_evaluations.evaluator` JSON gains `run` (execution name) and `result` gains `usage` (input, output, cache read, cache creation tokens) for judgements made from this version on.
- New settings: `ANTHROPIC_API_KEY` (only with `JUDGE_PROVIDER=anthropic`), `RETRIEVAL_MODE`, `RERANK`. New dependencies: `anthropic`, `rank-bm25`.

### Validation
- Backend strict script **2,107 tests passed** (1 environment-dependent skip), Ruff and skill checks passed. Independent review per task, two rounds each ([79](docs/evidence/v090-reviewer-t79.md), [80](docs/evidence/v090-reviewer-t80.md), [81](docs/evidence/v090-reviewer-t81.md)); final candidate [r2](docs/evidence/v090-candidato-r2.json).
- **Judge experiment** ([report](docs/evidence/v090-juiz-opus.md), [QA](docs/evidence/v090-qa-juiz-r2.md)): `claude-opus-5-5` judged the same 24 calibrated answers 3× (72/72 valid, US$1.34 on a separate Anthropic ledger, cap US$4.00). Against the human: within one point 0.958 / 0.958 / 1.000 / 0.958 (DeepSeek 0.833 / 0.833 / 1.000 / 0.917); `unsupported_claim` agreement 0.875 (0.667); self-consistency 0.81–1.00; but only 1 of the 4 generic claims the human flagged. Under the pre-registered rule (D2) this is a rubric gap, not a model gap: DeepSeek stays the default judge.
- **Retrieval** ([report](docs/evidence/v090-retrieval.md), [QA](docs/evidence/v090-qa-retrieval-r1.md)), real embeddings, holdout measured once per configuration, last:

  | Split | dense | hybrid | hybrid + reranker |
  | --- | --- | --- | --- |
  | dev (19 questions), nDCG@6 | 0.868 | 0.974 | 0.981 |
  | holdout_v090 (25), nDCG@6 | 0.880 | 0.921 | 0.961 |
  | holdout_v090, MRR | 0.871 | 0.920 | 0.980 |
  | time per query (holdout) | 584 ms | 534 ms | 2,392 ms |

  Hybrid is strictly better on both splits, so it became the default. Cost of the six measurements: US$0.016.

### Notes
- `RERANK` stays `off` by default (ADR 0020): the measured gain includes the effect of the deeper fusion (36 instead of 18 candidates), and the reranker quadruples the time per query.
- In hybrid mode the trace `score` is on the RRF scale, and the Knowledge agent's "no evidence" shortcut fires only when BM25 also finds nothing.
- The retrieval holdout (25 questions) was labeled by the Developer, checked by an independent reviewer and sealed before any measurement; it has now been measured, and later runs mark it as seen.
- Use a new execution name for each `eval --judge-repeat` round: a repeated name overwrites its report.
- The Opus judge costs 54× more per judgement than DeepSeek (US$0.0178 vs US$0.00033).

### Return to 0.8.0
- Set `RETRIEVAL_MODE=dense` (and keep `RERANK=off`) for the v0.8.0 behavior without checking out anything; the BM25 file is ignored. No migration to undo; judgements with `run` and `usage` are read by the 0.8.0 code as before.

## [0.8.0] — 2026-11-05 (validated: review, real QA and human calibration)

Adaptive orchestration and semantic evaluation ([spec](docs/specs/orquestracao-avaliacao-v080.md), [story](docs/historias/orquestracao-avaliacao-v080.md), [ADR 0019](docs/architecture/decisions/0019-replanejamento.md), tasks 69–78).

### Added
- **Replanning.** A `replan` node after Knowledge, the new `web` node and Support replaces the fixed edges. It can `finish`, call another specialist (`knowledge`, `web`, `support`), `escalate` or `clarify`. Clear cases are decided by named rules (`complete`, `plan_pending`, `procedure_gap`, `account_dependent_question`, `evidence_insufficient_web`, `tool_failure_no_alternative`, `support_asked_for_human`, `selection_pending`, `gap_declared`, `specialist_failed`); the model (`replan.v2`, which superseded `replan.v1` during the release; no reasoning effort, 80 output tokens) decides only when no rule applies or two disagree. Each specialist runs at most once per request, and a hop budget (`MAX_PLAN_HOPS=3`) caps the changes to the Router's plan; at the limit the reply states what could not be confirmed. Every `replan` step in the trace carries `next`, `reason`, `review`, `hops`, `origin` (`rule:<name>` or `model`) and the observed summary; the request detail keeps `plan_hops`. The operator resume graph of v0.7.0 is unchanged.
- **Rubric `judge.v3`**: `groundedness`, `factual_correctness`, `relevance` and `usefulness` (1–5, a short reason each) plus `unsupported_claim`, judged against the masked evidence of the answer (passages and tool results, up to 6,000 characters, truncation recorded) and, for escalations, the verifiable `HO-` protocol from the trace.
- **Independent judge**: `JUDGE_PROVIDER` / `JUDGE_MODEL` (default DeepSeek `deepseek-flash`, needs `DEEPSEEK_API_KEY`); `eval --judge` refuses before any call when the judge equals the agent or its key is missing. Provider, model and independence are recorded with each evaluation.
- **Repetitions without mixing variations**: `eval --repeat N` runs the agent N times and grades each answer once; `eval --judge-repeat N --answers-from <report>` grades recorded answers N times without running the agent. Reports give mean, deviation, exact and ±1 agreement per criterion, route and split (`dev`, `holdout`, `holdout_v080`), with small slices marked.
- **Human calibration**: `eval-calibrate --sample 24 --from <report>` writes a CSV stratified by route and split, with instructions and without the judge's scores (never from `holdout_v080`); `eval-calibrate --import <csv>` computes exact and ±1 agreement and quadratic weighted kappa per criterion into `docs/evidence/v080-calibracao.md`. No model call.
- `eval-estimate --from <sample>` projects the campaign cost from a measured real sample of at least five cases (agent ×3, judge ×3 over the first run, follow-up conversations), revalidating the source; no model call.
- Migration 0011 (see below); prompts `router.v6` (the interrogative English pricing-conditions question) and `personality.v5` (states the declared gap clearly).
- **Campaign `v080-qa`**: `eval --campaign v080-qa` reserves every paid call against a fixed one-time campaign ledger and the installation ledger together. Caps above US$0.50 require a verified estimate (`--campaign-estimate`).
- Deterministic contract-termination rule in the Router: an explicit request to end the contract (English or Portuguese, new conversation, no service named) goes to `human_handoff` with an `HO-` protocol, recorded as `rule = contract_termination` in the trace.
- `tests/scenarios/replan.jsonl` (four replanning scenarios, `SC-REPLAN-*` in the catalog) and the sealed `holdout_v080` split (25 new cases, about half in Portuguese), checked by hash in the suite.

### Changed
- Development labels of the business journeys (only where the real answer was correct, justified per case) and of `REPLAN-WEB`; the legacy and v0.8.0 holdouts were not edited.
- The runner's content check matches qualified answers (no evidence, refused authorization, conditional or negated states) against the expected proposition and keeps refusing the registered contradictions; typographic apostrophes are normalized.
- The evaluated route is the Router's initial plan (`route_ok` unchanged); the path actually run is reported separately as `executed_path` in the runner, the trace and the report.

### Contract and data
- Migration 0011 (reversible): `run_evaluations.rubric_version`, `scores` (JSON), `repetition` and `unsupported_claim`, rebuilt from existing rows; table `calibrations` for the human scores. Schema version 11. Rolling back refuses while `calibrations` holds human scores.
- New report fields: `executed_path`, `plan_hops`, the assistant-variation and judge-variation blocks, judge provider, model and independence, and a note on answers that used web search. `GET /v1/runs/{id}` shows the `replan` fields only on that step; other steps are unchanged. `POST /messages` keeps `route` as the initial plan.
- New settings: `MAX_PLAN_HOPS`, `JUDGE_PROVIDER`, `JUDGE_MODEL`, `BUDGET_RUNTIME_DIR` (persistent budget ledgers when `RUNTIME_DIR` is isolated for QA).

### Validation
- Backend strict script **1,997 tests passed**, Ruff and skill checks passed. Independent reviews per task, several in multiple rounds.
- Real QA on the final candidate, campaign `v080-qa` ([pre-holdout](docs/evidence/v080-d12-pre-holdout-r6.md), [holdout](docs/evidence/v080-holdout-r7.md)): **CA-49** replanning 4/4 scenarios (3/3 each), every decision with its origin, at most 2 hops. **CA-51** business journeys **13/13, 12/13 and 12/13** by the deterministic rubric (gate 12/13; the two misses are correct answers refused by the literal wording) and 13/13 in all three repetitions by the judge. Follow-up conversations 4/4.
- Repeated judge: 44 development answers × 3, 132 judgments, no judge failure; ±1 agreement 0.985–0.992 per criterion, stable outside `general_web`.
- Docker smoke 10/10; a mixed account-and-procedure question replanned from Support to Knowledge by `rule:procedure_gap`, visible in the trace.
- `holdout_v080`, run once as the last technical step and reported separately (it does not decide approval): **62/75 (0.827)** by the deterministic rubric, judge means 4.6–4.8, judge repeated 3× with no failure. The 24-answer calibration CSV is ready.
- **Human calibration** ([report](docs/evidence/v080-calibracao.md)): the owner rated 24 answers (balanced by route and split) with the judge's rubric and imported them with `eval-calibrate --import`. Exact agreement per criterion 0.58–0.75, within one point 0.83–1.00; the judge is the stricter rater (bias −0.17 to −0.42). `unsupported_claim`: exact agreement 0.67. Evidence localization per claim was AI-assisted in unversioned support material; every score is human.
- Campaign cost **US$0.84** in the campaign ledger (cap US$1.40 after the approved US$0.30 contingency, which was not consumed), plus **US$0.03** in the Docker volume ledger.

### Notes
- The deterministic journey rubric is literal: it refuses some correct paraphrases and can accept a wrong one outside the registered list; the independent judge is the extra control.
- `holdout_v080` has now been seen: any later QA run marks it as such, and no change is guided by its result.
- Human calibration rests on 24 answers rated by one person; the quadratic kappa is near zero because almost every human score is 5 (ceiling), so the within-one-point agreement is the usable figure.
- Replanning does not run in the operator resume graph.
- The seed dates "yesterday" by the day it runs: a paid QA run reseeds the same local day.

### Return to 0.7.0
- Stop the stack, make sure `calibrations` holds no human scores (or recreate the runtime), run `merchant-assistant migrate --to 10` against the runtime and check out the 0.7.0 release. The prompt loader takes the latest file of each prompt, so 0.7.0 uses `router.v5`, `personality.v4` and `judge.v2` again; `MAX_PLAN_HOPS` and the judge settings are ignored. The budget ledgers stay as they are.

## [0.7.0] — 2026-11-04 (validated: review and real QA apt)

Identity and real human in the loop ([spec](docs/specs/identidade-hitl-v070.md), [story](docs/historias/identidade-hitl-v070.md), [ADR 0017](docs/architecture/decisions/0017-identidade-principal-escopos.md), [ADR 0018](docs/architecture/decisions/0018-interrupcao-retomada-webhooks.md), tasks 63–68 and 66b).

### Breaking changes
- **`POST /messages` requires `Authorization: Bearer <token>`.** The merchant comes from the token; `user_id` in the body is optional and, if it differs, the answer is `403 identity_mismatch`. Calls to `POST /messages` become two: `POST /v1/auth/token` (form encoded, `grant_type=password`, demo user `cliente1988` with the fictitious password of `.env.example`, `client_id=merchant-assistant-cli`) and `POST /messages` with the token. `merchant-assistant smoke` and `merchant-assistant auth token` get the token themselves.
- **`POST /v1/sessions` and `DELETE /v1/sessions/current` were replaced** by `POST /v1/auth/token` and `POST /v1/auth/revoke`. The web client was migrated in the same release.
- MCP and the `operator` CLI take the token from `MERCHANT_ASSISTANT_TOKEN`; `mcp --customer` was removed. `GET /traces/{id}` and `GET /conversations/{id}` require a token (owner only, operators for conversations with a case, admin everything).

### Added
- Own JWT issuer (RS256, JWKS, discovery; external OIDC issuer by configuration), synthetic users with PBKDF2 password hashes, `client_credentials` for the ticketing service, revocation, roles and scopes, per-principal rate limit and login attempt limit; every tool call checks scope and merchant and is audited with principal, scope and result.
- Handoff queue (migration 0009): states, events, idempotent claim and actions (`409 claimed_by_other`, `409 already_resumed`), `GET /v1/handoffs`, `GET /v1/handoffs/{id}`, `POST …/claim`, `POST …/actions`, and `merchant-assistant operator list|show|act`.
- Graph interruption and resume: a review graph checkpointed in SQLite stops at `human_review` with `interrupt()` when a case opens; `approve`, `reply` and `reject` resume it with `Command(resume)` (reject re-runs Support once with the operator's instruction); the operator turn is marked `via=operator` and reaches the merchant on the next message (route `human_reply`, no model call), in the conversation and by webhook; resume survives an API restart.
- Ticketing service (separate Compose service and database, `127.0.0.1:8002`) with the ticket cycle `new → open → pending → solved`, operator login through the assistant's JWKS and an outbox of its own; operator Ticketing screen in the web project.
- Signed webhooks in both directions (HMAC-SHA256 over `timestamp.body`, 300 s window, one secret per direction): `handoff.created`, `conversation.replied` (the merchant's copy without `operator_id`) and `handoff.closed` out; `ticket.assigned`, `ticket.action` and `ticket.solved` in, idempotent by event id, with the original `409`/`422` repeated for a repeated refused event.
- Durable delivery (migration 0010): outgoing events are written to an outbox in the same transaction as the change they report and delivered by a dispatcher with three attempts in total per event and destination, also across restarts; pending deliveries are recovered at startup; a turn interrupted between opening a case and recording its event is completed when the merchant resends the same message.
- Merchant event receiver in `mocks` (`POST/GET /merchant/events`, signature checked).

### Changed (contracts and data)
- Handoff protocol `HO-…` instead of `SIM-…`; `simulated` left the payload and the reply no longer says the handoff is simulated. Replies carry `via`.
- Migration 0009 and migration 0010 (outbox), both reversible; 0010 refuses to roll back while the outbox holds undelivered events. Schema version 10.
- `/v1` OpenAPI: `/v1/auth/*` and `/v1/handoffs*` added, `/v1/sessions*` removed; the web snapshot was regenerated from the backend.
- Compose: `ticketing` service; `api` waits for a healthy `ticketing`; fictitious demo secrets are filled in so `docker compose up` works without editing `.env.example`.
- The audit table survives the seed that runs on every container start.

### Validation
- Backend strict script **640 tests passed**, web **92 tests passed**, Ruff and skill checks passed. Independent reviews per task, with mutation runs and real cross-process and crash probes. Real QA (candidate r1) apt on the 18 moments of the story through `curl`, the CLI, the web interface, two abrupt API restarts and Docker (smoke with token, ticket cycle and container restart between handoff and action). Real regression: challenge and core cases 27/27, conversations 4/4, business journeys 6/13 by the literal rubric (13/13, 12/13 and 12/13 in v0.8.0). QA campaign cost **US$0.10140195** of its US$0.20 cap; project total about US$0.79 of US$5. See the [result record](docs/evidence/v070-resultado.md).

### Notes
- A delivery that exhausts its three attempts or is refused holds the later events of the same case and destination.
- The case shows `ticket_id` after the first operator event from the ticketing.
- Identity uses the assistant's own issuer and synthetic demo users.

### Return to 0.6.0
- Stop the stack, make sure the outbox has no undelivered events (or recreate the runtime), run `merchant-assistant migrate --to 8` against the runtime and check out `v0.6.0`; remove `checkpoints.sqlite3`, the lock files and the ticketing database.

## [0.6.0] — 2026-10-28 (validated: review and real QA apt)

Simplification, demonstration and closing ([spec](docs/specs/fechamento-v060.md), [plan](docs/specs/fechamento-v060-plano.md), [ADR 0015](docs/architecture/decisions/0015-recorte-final-v060.md), tasks 54–58). After acceptance, functional expansion ends (reopened in v0.7.0, ADR 0016).

### Added
- Short catalog of ten labeled synthetic scenarios (`data/scenarios/catalog.json`), derived from the evaluation cases and including the documentation-effect question; `GET /v1/scenarios` and optional `scenario_id` in `POST /v1/messages` (validated, message must match, stored in the run snapshot).
- Results data in `GET /v1/runs/{id}`: steps with retrieved passages (chunk id and excerpt), route, prompts used, deterministic checks reusing the existing evaluation checks (scenario labels when present; otherwise only grounding, errors and cross-customer markers, the rest "not evaluated") with critical failures listed one by one, and recorded evaluations.
- On-demand model evaluation of a persisted reply (`POST /v1/runs/{id}/evaluations/estimate` and `POST /v1/runs/{id}/evaluations`): existing `judge` rubric and `JudgeScore`, fixed evaluator from the backend settings, confirmed estimate, budget reservation and separate cost, idempotent unless `repeat=true`, failed attempts recorded without scores. No Evaluation Agent and no new attendance.
- Small profile comparison (`POST /v1/comparisons/estimate`, `POST /v1/comparisons`, `GET /v1/comparisons/{id}`): 2–3 profiles, up to 3 scenarios and 2 repetitions (18 cells), reuse of compatible recorded runs, one captured knowledge-base version, execution in a thread of the API process, domain effects in a temporary copy of the synthetic database, traces and snapshots marked `purpose=comparison`, budget denial stops the remaining cells, interrupted comparisons become `failed` on the next read, exploratory flag when profiles differ in more than one agent, model-judge quality only when every run of a profile was judged with one evaluator.
- Documentation-effect demonstration prepared without cost: V2 text of the fictitious devices document (`data/scenarios/kb-demo-devices-v2.md`), expected difference recorded before editing and an integration test V1 → V2 → V1 with a programmed policy.
- Demo session limit of paid actions (`DEMO_SESSION_MESSAGE_LIMIT`, default 20), enforced by the backend with `429 demo_message_limit_reached`: messages, new comparison executions, Router comparisons and AI evaluations count; refusals without a model call (for example a stale comparison `409`, a budget refusal before the first call, or comparison cells skipped by a knowledge-base change, the confirmed cap or a budget refusal) do not count or are given back.
- Web: three areas (Atendimento, Resultados, Administração only for admin), catalog scenarios, Results with checks, evaluations and the two comparison charts plus a table, error messages with the recovery action, optional `LOCK_BACKEND_URL` for a shared interface. Reference, Hybrid and Adjusted are published on new databases.
- Single [demonstration guide](https://github.com/lauroPereira/ai-getnet-case/blob/67736304ef948db41b082aea9b1b1b20c3f912b5/docs/guia-demonstracao.md), [manual test script](https://github.com/lauroPereira/ai-getnet-case/blob/67736304ef948db41b082aea9b1b1b20c3f912b5/docs/roteiro-teste-manual.md) and [video script](https://github.com/lauroPereira/ai-getnet-case/blob/67736304ef948db41b082aea9b1b1b20c3f912b5/docs/roteiro-video.md). The links point to the version integrated in v0.6.0.

### Fixed
- Budget ceiling written with an exact round-trip value and published atomically; readiness and per-request capture read-only once the knowledge-base registry exists; explicit timeouts (CLI OpenAI client 30 s; web 105 s for paid work, 20 s for reads); `BudgetMeter` accepts `effective_parameters`; strict scripts skip `.pytest_cache` and `_tmp` (task 54).
- A comparison read never overwrites a final state; on-demand evaluation claims its row atomically (one paid call per configuration); comparisons reuse only independent runs and keep unknown costs unknown; the catalog covers enablement and sale cancellation; web recovery actions in Administração and drill-down from charts (task 60).
- The JEV toggle runs the TypeSafe adapter in messages and comparisons, with snapshot, trace, ledger and Results agreeing on the effective Router model; demo-limit refunds are decided by the ledger; `/ready` reports the active knowledge base; web display fixes (task 61).

### Changed (contracts and data)
- Additive `/v1` routes above; the OpenAPI snapshot in the web project is regenerated (31 paths, 28 client operations). Legacy `POST /messages`, MCP and existing `/v1` behaviour are unchanged.
- Reversible migration 0008 adds `run_evaluations`, `comparisons` and `api_sessions.message_count`; schema version 8. Trace detail gains `purpose`, `scenario_id`, `citations` and passage excerpts; run snapshots gain `scenario_id`, `purpose`, the masked `message` and the `prompt_set`.
- Compose publishes the API only on `127.0.0.1:8000`.
- The approved v0.6.0 QA campaign cap is US$0.50: `FixedBudgetGuard` accepts up to US$0.50 (was US$0.25).
- Activation keeps its Qdrant I/O inside the `BEGIN IMMEDIATE` transaction (R2-04, by design).

### Validation
- Backend strict script: **349 tests passed**, Ruff and skill checks passed. Web: **42 tests passed**, Ruff passed, strict script exit 0. Migration 0007 → 0008 → 0007 tested on a synthetic SQLite database. Independent review and real QA (candidate r5) apt on the ten acceptance items through the real UI, ledgers and the packaged Docker stack (API only on loopback, schema 8). Highlights: the edited document changed tool use with a real model (V2 retrieved the new passage first and called `get_contract_snapshot`; the restored V1 did not); JEV toggle confirmed by `jev-1.14.0` ledger rows; recovery with one POST and one GET; on-demand evaluation reused without cost. Real regression: core and challenge cases 27/27, conversations 4/4, business journeys 7/13 by the literal rubric (13/13, 12/13 and 12/13 in v0.8.0). QA campaign cost **US$0.08800487** of its US$0.50 cap; project total US$0.68637953 of US$5. See the [result record](docs/evidence/v060-resultado.md).

### Notes
- The comparison estimate is an upper bound. A comparison whose process stops is marked `failed` (superseded in v0.10.0: `interrupted` and resumable).
- Results shows the runs of the current browser session; there is no general run listing.

### Return to 0.5.0
- Stop the stack and run `merchant-assistant migrate --to 7` against the synthetic runtime before checking out `v0.5.0`; evaluations, comparisons and the session message counter are dropped, all earlier data is kept. Compose of 0.5.0 publishes the API on all interfaces again.

## [0.5.0] — 2026-10-27 (validated candidate r7; approved for Git integration)

Editable, versioned knowledge base ([spec](docs/specs/base-versionada-v050.md), tasks 39–53).

### Added
- Knowledge base registry seeded from the existing public snapshots and fictitious demo corpus. Only `simulated_internal` documents are editable; origin and identity are assigned by the server, and official sources stay read-only.
- Drafts with optimistic revisions and diffs; candidate versions built into their own Qdrant collection with a frozen manifest (documents, hashes, embedding model and dimension) and an explicit test step.
- Explicit activation and rollback with expected-active comparison, integrity check of the collection against its manifest, and an event log with actor, time and evidence.
- Each run captures one identified knowledge base version at its start; the trace and run snapshot record it, and a run in progress finishes on that version even if another one is activated.
- Embedding batches (build and test) reserve budget before the provider call and settle once afterwards; unknown cost keeps the reservation. Estimates and confirmed caps are required before a build or test.
- Persistent per-ledger ceiling in `<ledger>.limit`, written once on first use (1.00 for a ledger that predates it, 5.00 absolute maximum); a later configuration can never raise it.
- Streamlit administration for documents, editor and diff, estimate and confirmation, build, test, activation and rollback; confirmations are reset when the confirmed cap changes.
- Manual conversation recovery in the web client: a transport failure after `POST /v1/messages` keeps the question pending and offers a GET-only refresh, never an automatic resend.

### Changed (contracts and data)
- Additive `/v1/kb/*` routes (documents, drafts, diff, version estimate, build, list, detail, test, activate, rollback), admin-only for writes; OpenAPI snapshot 0.5.0 in the web project. Legacy `POST /messages` and MCP are unchanged.
- Reversible migration 0007 adds `kb_documents`, `kb_drafts`, `kb_versions`, `kb_state` and `kb_events`; schema version 7. `bootstrap`/`index` never rebuild or replace an existing collection.

### Validation
- Backend strict script: **293 tests passed** (Reviewer r2); web: **20 tests passed** with external Ruff. Independent reviews and three real QA rounds are linked from the [result record](docs/evidence/v050-resultado.md).
- Real QA covered embeddings, baseline build, the full draft → candidate → test → activation → rollback cycle in the UI, 403/409/429 protections, concurrent version capture, a real DeepSeek/JEV Router comparison and conversation recovery with a single POST.
- Paid calls in this version: **US$0.00553883**; project total US$0.59837466 of US$5.

### Return to 0.4.0
- Stop the stack and run `merchant-assistant migrate --to 6` against the synthetic runtime before checking out `v0.4.0`. Knowledge base tables are dropped; Qdrant collections are kept and the reference collection keeps working.

## [0.4.0] — 2026-10-27 (approved for Git integration)

### Added
- Reversible migration 0006 for model profiles, immutable published versions, API principals and sessions, router comparisons and run snapshots.
- Authenticated `/v1` API with opaque 60-minute session tokens stored only as SHA-256 digests, backend-enforced roles/ownership, revocation and atomic one-time comparison consumption.
- Reference, Hybrid and Adjusted profiles validated against a dated provider catalog; JEV System One adapter is Router-only and has no silent provider fallback.
- Separate Streamlit client, generated route map from the OpenAPI snapshot, Simulated and Recorded fixtures, and explicit Real (API) HTTP mode.
- Peak-conservative DeepSeek estimates and per-run price basis; trace values label cost as an estimate.
- Per-agent `max_output_tokens` for supported OpenAI/DeepSeek models, bounded by the agent's existing cap and applied identically to budget reservation and provider payload. Profile versions and run snapshots retain configured/effective values.
- JEV's internal 80-token reservation estimate is excluded from effective-parameter maps because System One's request contract does not accept that parameter; comparison and reused-run snapshots preserve the distinction.
- Changing the selected Router after a comparison discards the stale result. A new comparison requires an explicit click; the valid decision is consumed once with its original method and identifier.

### Changed (contracts and data)
- Backend package reports version 0.4.0; schema version 6 is reversible to version 5 while preserving prior business data.
- `/v1` endpoints and Bearer security are described by `ai-getnet-case-web/openapi-v1.json`. Session revocation returns an empty 204 response; subsequent unauthorized requests on the same keep-alive connection receive a complete 401 response. Legacy `POST /messages` remains unchanged.

### Validation
- Backend strict script: **216 tests passed**, Ruff and skill checks passed.
- Web Ruff check/format passed; web pytest: **14 passed**. Independent Reviewer and QA rechecked both directions of Router selection changes; earlier QA covered Simulated/Recorded labels, compatible profile publication, effective parameters and rejection without a version change.
- Synthetic HTTP client flow passed login, profile read, two-router comparison, selected message, run inspection, one-time consumption and authorization/revocation checks.
- Candidate r6, review and QA are linked from the [result record](docs/evidence/v040-resultado.md).

### Notes
- Validated with scripted models; real-model QA starts in 0.5.0.

## [0.3.0] — 2026-10-27 (validated; approved for release)

### Added
- Internal `mocks` HTTP service with separate synthetic pricing rules and recorded charge fixtures; no public port.
- Read-only fee comparison, card-scheme enablement and sale cancellation tools, shared through the domain and MCP.
- Reversible migration 0005 for contract pricing context, enablement requests and sale cancellation records.
- Versioned Router and Support prompts, including filters for identifiable fee comparisons and recent authorization history; deterministic business-journey cases.

### Changed (contracts)
- `get_contract_snapshot` additively includes the merchant's synthetic pricing plan and rule version.
- Support tool schemas add four tools; price tools expose bounded sale filters and never accept a customer identifier.
- `POST /messages` retains its v0.2.0 request and response contract.

### Data
- New `contract_pricing_context`, `enablement_requests` and `sale_cancellations` tables; downgrade 0005 → 0004 preserves earlier tables and rows.
- Independent synthetic service fixtures live in `data/mock-services/`.

### Validation
- The owner approved v0.3.0 for release ([central validation record](docs/evidence/v030-resultado.md)).
- Strict validation: **191 tests**. Independent [Reviewer r6](docs/evidence/v030-reviewer-r6.md) and [QA r6](docs/evidence/v030-qa-r6.md) are apt.
- **40 recorded real HTTP responses** scored with the corrected rubric, with no new model calls ([report](docs/evidence/v030-real-http-r2-replay.md)). Separately, **4 multi-turn conversations** were repeated live through HTTP and passed **4/4** ([conversation report](docs/evidence/v030-real-conversations-r3.md)).

### Notes
- Pricing values, rules, protocols and cancellation statuses are fictitious and not Getnet terms.
- No fee adjustment, refund, enablement, sale cancellation or contract termination is executed.

### Return to 0.2.0
- Stop the stack and run `merchant-assistant migrate --to 4` against the synthetic runtime before checking out `v0.2.0`; pricing and cancellation journey data is dropped with migration 0005.

## [0.2.0] — 2026-10-26

Memory, follow-up and MCP ([increments spec](docs/specs/incrementos-pos-nucleo.md), tasks 15–20).

### Added
- Conversations owned by one merchant: short history (up to 10 messages / 1,200 tokens) given to Router, Customer
  Support and Personality; the case prefix (history + healthcheck) is reused for 30 minutes on the same topic.
- Case states `in_progress`, `awaiting_customer`, `resolved`, `handoff`; resolution only with evidence
  (`customer_confirmed` or `tool_verified`). Thanks or silence never resolve.
- Technical follow-up: steps recorded per cycle, never repeated, handoff with the attempts after two cycles or on
  request; a case already with a human reuses its protocol.
- MCP server for the support tools (`merchant-assistant mcp --customer <id>`, stdio, official `mcp` SDK 2.3) and
  `mcp-demo`.
- Numbered, reversible migrations (`merchant-assistant migrate --to N`); `/ready` reports app, schema, index and
  prompt versions; `GET /conversations/{id}` in demo mode.
- Multi-turn scenarios in the evaluation (`tests/scenarios/followup.jsonl`).

### Changed (contracts)
- `route` gains `acknowledgement` (a reaction to the previous reply with no new request).
- `resolution.evidence` is `customer_confirmed` or `tool_verified` when the case is resolved.
- `POST /messages` answers `404 conversation_not_found` for a conversation of another merchant. A new
  client-supplied `conversation_id` still starts a conversation.
- Prompts: `router` v2, `support` v5, `personality` v3. Provider calls never wait longer than the request's
  remaining time budget (30 s per call, one retry).

### Data
- Migrations 0002 (conversations, messages), 0003 (case attempts), 0004 (`conversation_id` on handoff cases).

### Validation
- 141 offline tests; strict template validation.
- Real regression: 27/27 core cases, 4/4 multi-turn conversations, p50 7.0 s, p95 13.4 s
  ([report](docs/evidence/2026-10-26-regressao-v020.md)).
- Docker clean start healthy in 18 s; smoke 10/10; MCP demo inside the container.

### Notes
- Troubleshooting steps are identified by the short label the model gives, not by a procedure step id.
- Informational answers stay `awaiting_customer` until the merchant confirms (no automatic informational
  resolution).
- The installation budget ledger lives in the runtime volume; `docker compose down -v` resets it (the project-wide
  record is `docs/evidence/orcamento.md`).

### Return to 0.1.0
- `git checkout v0.1.0` and `docker compose down -v && docker compose up --build`, or keep the data and run
  `merchant-assistant migrate --to 1` before checking out `v0.1.0`.

## [0.1.0] — 2026-10-26

Core delivery of the challenge (slices 0 and 1). Tag `v0.1.0` on commit `29a0088`.

### Added
- `POST /messages` with Router, Knowledge (RAG over 32 official pages + web search), Customer Support (5 tools over synthetic data plus history and healthcheck at case opening), Escalation (simulated, idempotent handoff) and Personality.
- LangGraph orchestration with typed state, per-request limits, persistent budget guard, step traces and JSON logs.
- Input guard (masking, injection blocking), refusal of unsafe requests, output guard on amounts, dates and percentages.
- Docker Compose (API + Qdrant) with seed and index built on first start; `smoke`, `eval`, `eval-retrieval`, `ingest`, `index`, `bootstrap` and `ask` commands.

### Validation
- 112 offline tests; Recall@6 = 1.0 (English and Portuguese); real evaluation 27/27 automated checks; Docker clean build and smoke 10/10.

### Notes
- One message per request (conversation memory since v0.2.0); simulated handoff (human in the loop since v0.7.0); snapshots fixed on 2026-10-26.
