# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/). Each release lists features, contract and data changes, validation, limitations and how to return to the previous version.

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
- **Campaign `v080-qa`**: `eval --campaign v080-qa` reserves every paid call against a fixed one-time campaign ledger and the installation ledger together. Caps above US$0.50 require a verified estimate (`--campaign-estimate`); US$1.40 only continues the mounted campaign after the reviewed contingency transition and never mounts a new one.
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

### Limitations
- The deterministic journey rubric is literal: each real run brings correct paraphrases it refuses (known false refusals are listed in the task 78 review), and a new wrong paraphrase outside the registered list can pass; the independent judge is the extra control. How CA-51 is measured from v0.9.0 is open with the owner.
- The judge does not see the web search text, so `general_web` answers get lower and less stable scores.
- `holdout_v080` has now been seen: any later QA run must mark it as such, and no change may be guided by its result.
- Human calibration rests on 24 answers rated by one person: agreement and kappa are an indication, not proof, and the quadratic kappa is near zero because almost every human score is 5 (ceiling). The judge and the owner never flag the same answer as `unsupported_claim`: the owner flags generic claims inside knowledge answers, the judge flags web answers whose text was not recorded. The sample CSV truncates the evidence the judge saw in full; the full passages were provided in a companion file this time.
- On mixed questions the Router's initial plan varies between runs (Support followed by replanning, or `knowledge_and_support` directly); both give the right answer. Replanning does not run in the operator resume graph.
- The seed dates "yesterday" by the day it ran: a paid QA run needs `bootstrap` on the same local day.

### Return to 0.7.0
- Stop the stack, make sure `calibrations` holds no human scores (or recreate the runtime), run `merchant-assistant migrate --to 10` against the runtime and check out the 0.7.0 release. The prompt loader takes the latest file of each prompt, so 0.7.0 uses `router.v5`, `personality.v4` and `judge.v2` again; `MAX_PLAN_HOPS` and the judge settings are ignored. The budget ledgers stay as they are.

## [0.7.0] — 2026-11-04 (validated: review and real QA apt)

Identity and real human in the loop ([spec](docs/specs/identidade-hitl-v070.md), [story](docs/historias/identidade-hitl-v070.md), [ADR 0017](docs/architecture/decisions/0017-identidade-principal-escopos.md), [ADR 0018](docs/architecture/decisions/0018-interrupcao-retomada-webhooks.md), tasks 63–68 and 66b).

### Breaking changes
- **`POST /messages` requires `Authorization: Bearer <token>`.** The merchant comes from the token; `user_id` in the body is optional and, if it differs, the answer is `403 identity_mismatch`. The evaluator's calls become two: `POST /v1/auth/token` (form encoded, `grant_type=password`, demo user `cliente1988` with the fictitious password of `.env.example`, `client_id=merchant-assistant-cli`) and `POST /messages` with the token. `merchant-assistant smoke` and `merchant-assistant auth token` get the token themselves.
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
- Migration 0009 (widened during the release) and migration 0010 (outbox), both reversible; 0010 refuses to roll back while the outbox holds undelivered events. Schema version 10.
- `/v1` OpenAPI: `/v1/auth/*` and `/v1/handoffs*` added, `/v1/sessions*` removed; the web snapshot was regenerated from the backend.
- Compose: `ticketing` service; `api` waits for a healthy `ticketing`; fictitious demo secrets are filled in so `docker compose up` works without editing `.env.example`.
- The audit table survives the seed that runs on every container start.

### Validation
- Backend strict script **640 tests passed**, web **92 tests passed**, Ruff and skill checks passed. Independent reviews per task (task 66 in five rounds, task 67 in six, task 68 in two), with mutation runs and real cross-process and crash probes. Real QA (candidate r1) apt on the 18 moments of the story through `curl`, the CLI, the web interface, two abrupt API restarts and Docker (smoke with token, ticket cycle and container restart between handoff and action). Real regression: challenge and core cases 27/27, conversations 4/4, business journeys 6/13. QA campaign cost **US$0.10140195** of its US$0.20 cap; project total about US$0.79 of US$5. See the [result record](docs/evidence/v070-resultado.md).

### Limitations
- A delivery that exhausts its three attempts or is refused has no resend yet and holds the later events of the same case and destination. After a crash in the middle of the turn that opens a case, recovery depends on the merchant resending the same message. Cross-process locks were exercised on Windows only.
- The case shows `ticket_id` only after the first operator event from the ticketing (empty while the ticket is in reception). The `reject` resume with a real model can take longer than the ticketing's 3 s wait: the screen shows "envio pendente" and the retry with the same key completes it.
- Business journeys 6/13 by the literal rubric (7/13 in v0.6.0): the English handoff sentence lost the word "human" that one label requires. Planned for v0.8.0 together with the other journey fixes.
- Identity uses the assistant's own issuer and synthetic users; no authorization-code flow, refresh token or external provider runs in the demo.

### Return to 0.6.0
- Stop the stack, make sure the outbox has no undelivered events (or recreate the runtime), run `merchant-assistant migrate --to 8` against the runtime and check out `v0.6.0`; remove `checkpoints.sqlite3`, the lock files and the ticketing database. Databases created during the release while migration 0009 was being widened must be recreated.

## [0.6.0] — 2026-10-28 (validated: review and real QA apt)

Simplification, demonstration and closing ([spec](docs/specs/fechamento-v060.md), [plan](docs/specs/fechamento-v060-plano.md), [ADR 0015](docs/architecture/decisions/0015-recorte-final-v060.md), tasks 54–58). After acceptance, functional expansion ends.

### Added
- Short catalog of ten labeled synthetic scenarios (`data/scenarios/catalog.json`), derived from the evaluation cases and including the documentation-effect question; `GET /v1/scenarios` and optional `scenario_id` in `POST /v1/messages` (validated, message must match, stored in the run snapshot).
- Results data in `GET /v1/runs/{id}`: steps with retrieved passages (chunk id and excerpt), route, prompts used, deterministic checks reusing the existing evaluation checks (scenario labels when present; otherwise only grounding, errors and cross-customer markers, the rest "not evaluated") with critical failures listed one by one, and recorded evaluations.
- On-demand model evaluation of a persisted reply (`POST /v1/runs/{id}/evaluations/estimate` and `POST /v1/runs/{id}/evaluations`): existing `judge` rubric and `JudgeScore`, fixed evaluator from the backend settings, confirmed estimate, budget reservation and separate cost, idempotent unless `repeat=true`, failed attempts recorded without scores. No Evaluation Agent and no new attendance.
- Small profile comparison (`POST /v1/comparisons/estimate`, `POST /v1/comparisons`, `GET /v1/comparisons/{id}`): 2–3 profiles, up to 3 scenarios and 2 repetitions (18 cells), reuse of compatible recorded runs, one captured knowledge-base version, execution in a thread of the API process, domain effects in a temporary copy of the synthetic database, traces and snapshots marked `purpose=comparison`, budget denial stops the remaining cells, interrupted comparisons become `failed` on the next read, exploratory flag when profiles differ in more than one agent, model-judge quality only when every run of a profile was judged with one evaluator.
- Documentation-effect demonstration prepared without cost: V2 text of the fictitious devices document (`data/scenarios/kb-demo-devices-v2.md`), expected difference recorded before editing ([QA preparation](docs/evidence/v060-qa-preparacao.md)) and an integration test V1 → V2 → V1 with a programmed policy.
- Demo session limit of paid actions (`DEMO_SESSION_MESSAGE_LIMIT`, default 20), enforced by the backend with `429 demo_message_limit_reached`: messages, new comparison executions, Router comparisons and AI evaluations count; refusals without a model call (for example a stale comparison `409`, a budget refusal before the first call, or comparison cells skipped by a knowledge-base change, the confirmed cap or a budget refusal) do not count or are given back.
- Web: three areas (Atendimento, Resultados, Administração only for admin), catalog scenarios, Results with checks, evaluations and the two comparison charts plus a table, error messages with the recovery action, optional `LOCK_BACKEND_URL` for a shared interface. Reference, Hybrid and Adjusted are published on new databases.
- Single [demonstration guide](https://github.com/lauroPereira/ai-getnet-case/blob/67736304ef948db41b082aea9b1b1b20c3f912b5/docs/guia-demonstracao.md), [manual test script](https://github.com/lauroPereira/ai-getnet-case/blob/67736304ef948db41b082aea9b1b1b20c3f912b5/docs/roteiro-teste-manual.md) and [video script](https://github.com/lauroPereira/ai-getnet-case/blob/67736304ef948db41b082aea9b1b1b20c3f912b5/docs/roteiro-video.md). Removed from the repository after integration by the owner's decision and replaced by local presentation material; the links point to the integrated version.

### Fixed (task 54)
- R2-01: the persistent ceiling is written with an exact round-trip representation; the first mount never refuses its own value.
- R2-02: the ceiling file is published atomically (temporary file and hard link) and never overwritten.
- R2-03: readiness and per-request capture are read-only once the knowledge-base registry exists.
- R2-05: explicit 30 s timeout in the CLI OpenAI client; R2-08 regressions for `max_retries == 0` in the three real clients and for a legacy manifest with an empty collection.
- R2-07: `BudgetGuard.record` and `record_embedding` (no callers, no reservation) removed.
- Web timeout: 105 s (backend `MAX_REQUEST_SECONDS` 90 + margin) for operations that wait for paid work, 20 s for reads, both configurable; GET recovery preserved. Unstructured gateway errors no longer break the client.
- `BudgetMeter` accepts the `effective_parameters` argument sent by the OpenAI adapter (the paid judge path of `eval --judge` would otherwise fail).
- Strict validation scripts skip `.pytest_cache` and `_tmp`; the web script also skips `.venv*` environments and Ruff is a web test dependency.

### Fixed (review r1, task 60)
- A comparison read never overwrites a final state recorded at the same time (conditional update while `running`).
- On-demand evaluation claims a `running` row atomically: simultaneous requests with the same configuration make one paid call (`409 evaluation_running`); stale claims expire after 10 minutes.
- Comparisons reuse only independent runs (`history_turns = 0`); missing costs stay unknown instead of zero; an agent that used several models in one run keeps one combined cost.
- The catalog covers card-scheme enablement and sale cancellation (10 scenarios).
- Web: transport failures in Administração (build, test, activation, rollback and loads) show the recovery action and discard estimate and confirmations; chart points and table cells (including failed ones) open their runs by GET; Simulado offers only the demo role when `LOCK_BACKEND_URL` is on.

### Fixed (QA r1, task 61)
- The JEV toggle runs the TypeSafe adapter in direct messages and profile comparisons; before, the Router was served by the default LLM while the snapshot said JEV. Snapshot, trace, ledger and Results now agree on the effective Router model.
- The demo-limit refund is decided by the ledger rows of the request and never happens when they cannot be read.
- `/ready` reports the active knowledge-base version and collection (`knowledge_base`).
- Web: amounts in reais are shown literally (no formula), the case state follows a recovered reply, the profile selector starts on Referência with Portuguese names, the candidate test cap is pre-filled with the build estimate and the cost × quality chart keeps its labels in the legend.

### Changed (contracts and data)
- Additive `/v1` routes above; the OpenAPI snapshot in the web project is regenerated (31 paths, 28 client operations). Legacy `POST /messages`, MCP and existing `/v1` behaviour are unchanged.
- Reversible migration 0008 adds `run_evaluations`, `comparisons` and `api_sessions.message_count`; schema version 8. Trace detail gains `purpose`, `scenario_id`, `citations` and passage excerpts; run snapshots gain `scenario_id`, `purpose`, the masked `message` and the `prompt_set`.
- Compose publishes the API only on `127.0.0.1:8000`.
- The approved v0.6.0 QA campaign cap is US$0.50: `FixedBudgetGuard` accepts up to US$0.50 (was US$0.25).
- R2-04 (Qdrant I/O inside `BEGIN IMMEDIATE` during activation) is an accepted risk, without code change.

### Validation
- Backend strict script: **349 tests passed**, Ruff and skill checks passed. Web: **42 tests passed**, Ruff passed, strict script exit 0. Migration 0007 → 0008 → 0007 tested on a synthetic SQLite database. Independent review apt in five rounds; real QA (two rounds, candidate r5) apt on the ten acceptance items through the real UI, ledgers and the packaged Docker stack (API only on loopback, schema 8). Highlights: the edited document changed tool use with a real model (V2 retrieved the new passage first and called `get_contract_snapshot`; the restored V1 did not); JEV toggle confirmed by `jev-1.14.0` ledger rows; recovery with one POST and one GET; on-demand evaluation reused without cost. Real regression: core and challenge cases 27/27, conversations 4/4. QA campaign cost **US$0.08800487** of its US$0.50 cap; project total US$0.68637953 of US$5. See the [result record](docs/evidence/v060-resultado.md).

### Limitations
- Model evaluation is a judge over the persisted reply, not human review. The comparison estimate is an upper bound; comparisons depend on the API process staying up.
- Results shows the runs of the current browser session; no general run listing (`GET /v1/runs` was not approved).
- Public sharing depends on the owner's router, firewall and the absence of CGNAT; the docs describe a tunnel as an alternative. Access from another network was not tested yet.
- Business journeys in the real regression: 7/13 by the literal rubric. Four pricing cases miss only literal wording (tool, amounts and status are right); the English price-conditions question goes to `clarify` with the real Router (the Portuguese one passes). Router and prompts were not changed in v0.6.0.
- The cost × quality chart legend shows profile identifiers (`reference`, `hybrid`, `adjusted`) instead of the Portuguese names.
- `/v1` login against the Docker stack requires `API_DEMO_ACCESS_KEY` and `API_ADMIN_ACCESS_KEY` in `.env`.

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

### Limitations
- An optional probe of the edited fictitious text did not reach Knowledge and remains inconclusive; it was not a published criterion and is not claimed as demonstrated.
- Low-severity review findings (task 46) remain open. The web strict script exits 2 because Ruff is not installed in the web virtual environment; Ruff passed when run externally.
- Real inferences ran in the native environment; the canonical Docker image built for r3 was inspected but not used for provider calls.

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
- Backend strict script: **216 tests passed**, Ruff and skill checks passed; see the Developer r5 passage.
- Web Ruff check/format passed; web pytest: **14 passed**. Independent Reviewer and QA rechecked both directions of Router selection changes; earlier QA covered Simulated/Recorded labels, compatible profile publication, effective parameters and rejection without a version change.
- Synthetic HTTP client flow passed login, profile read, two-router comparison, selected message, run inspection, one-time consumption and authorization/revocation checks. No model-provider HTTP inference was sent.
- Candidate r6, independent passages, installed-image checks and limits are linked from `docs/evidence/v040-resultado.md`.

### Limitations
- CA-32 live JEV request remains pending; no paid/provider inference API call was made. The catalog follows dated official documentation; no provider-account `GET /models` was sent because a free call could not be established from official pricing evidence.
- The owner authorized private PRs and merges with these limits retained. Paid QA is authorized starting in v0.5.0 within the persistent US$5 project ceiling; v0.4.0 did not use that authorization retroactively.
- Docker validation used an incremental installed image and identical backend inputs; a fresh canonical Docker rebuild is not claimed.

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
- The owner approved v0.3.0 for release. Integration and tag execution are tracked in the [central validation record](docs/evidence/v030-resultado.md); this changelog does not claim that PR, merge or tag actions have already occurred.
- The final [Developer r6 passage](docs/evidence/v030-developer-r6.md) records the strict validation: **191 tests**. Independent [Reviewer r6](docs/evidence/v030-reviewer-r6.md) and [QA r6](docs/evidence/v030-qa-r6.md) are apt.
- **40 recorded real HTTP responses** were re-evaluated by deterministic replay of the corrected rubric, with no new model calls; the original answers and holdouts were preserved ([replay report](docs/evidence/v030-real-http-r2-replay.md)). Separately, **4 multi-turn conversations** were repeated live through HTTP and passed **4/4** ([conversation report](docs/evidence/v030-real-conversations-r3.md)).
- The [r1 real evaluation](docs/evidence/v030-real-r1.md) is preserved as historical evidence and is not the final release result.

### Limitations
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

### Limitations
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

### Limitations
- One message per request (no conversation memory); simulated handoff; snapshots fixed on 2026-10-26.
