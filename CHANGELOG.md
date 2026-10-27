# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/). Each release lists features, contract and data changes, validation, limitations and how to return to the previous version.

## [Unreleased] — 0.2.0 (in progress)

Memory, follow-up and MCP ([increments spec](docs/specs/incrementos-pos-nucleo.md), tasks 15–20).

### Added
- Numbered, reversible schema migrations with a `schema_version` table and `merchant-assistant migrate --to N`.
- `/ready` reports the versions in use: app, schema, knowledge index and prompts.

### Data
- Migration 0001 (core tables, unchanged from 0.1.0), 0002 (conversations, messages), 0003 (case attempts).

### Return to 0.1.0
- `git checkout v0.1.0`, then `docker compose down -v && docker compose up --build` (synthetic data is recreated), or `merchant-assistant migrate --to 1` on an existing local database.

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
