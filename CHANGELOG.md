# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/). Each release lists features, contract and data changes, validation, limitations and how to return to the previous version.

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
