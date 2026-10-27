# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/). Each release lists features, contract and data changes, validation, limitations and how to return to the previous version.

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
