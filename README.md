# Getnet Merchant Assistant — Multi-Agent Support System

▶ Presentation video (46 min): https://github.com/lauroPereira/ai-getnet-case/releases/download/v0.6.0/apresentacao-final.mp4

A multi-agent assistant that answers Getnet merchants over a single HTTP endpoint. A **Router** decides who handles
each message; a **Knowledge Agent** answers from Getnet's official website (RAG) or the web; a **Customer Support
Agent** uses tools over the merchant's (synthetic) account data; an **Escalation Agent** hands the case to a human;
and a **Personality** step writes every final reply in one consistent voice. Built for the *AI Hardcore Engineer —
Multi-Agent Support System* challenge.

```bash
cp .env.example .env          # add your OPENAI_API_KEY
docker compose up --build
TOKEN=$(curl -s localhost:8000/v1/auth/token -d grant_type=password -d username=cliente1988 \
  -d password=cliente1988-fictitious -d client_id=merchant-assistant-cli | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s localhost:8000/messages -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"message": "When will the money from yesterday'"'"'s sales be deposited?"}'
```

Since v0.7.0 `POST /messages` requires a token: the merchant comes from the token, not from the body. The user and password above are fictitious demo values from `.env.example`.

**Status:** v0.10.0, validated by independent reviews and real-model QA at every version. Offline, the backend strict suite passes (**2,147 tests**, Ruff clean). v0.7.0: real human in the loop and JWT identity ([result](docs/evidence/v070-resultado.md)). v0.8.0: replanning (four scenarios 3/3 with real models, at most 2 hops), business journeys **13/13, 12/13 and 12/13** (13/13 by the independent judge), conversations **4/4**, Docker smoke 10/10, sealed holdout run once **62/75**, 24-answer human calibration ([pre-holdout](docs/evidence/v080-d12-pre-holdout-r6.md), [holdout](docs/evidence/v080-holdout-r7.md), [calibration](docs/evidence/v080-calibracao.md)). v0.9.0: hybrid retrieval beats dense on dev and on a sealed retrieval holdout and is the default ([report](docs/evidence/v090-retrieval.md)); a pre-registered judge experiment kept DeepSeek over Claude Opus ([report](docs/evidence/v090-juiz-opus.md)). v0.10.0: a profile comparison survives a real `taskkill` and resumes without paying any cell twice ([QA](docs/evidence/v0100-qa-ops-r1.md)), `GET /metrics` with versioned alert rules, and rubric `judge.v4` measured against the human calibration under a rule written beforehand, v3 kept ([report](docs/evidence/v0100-juiz-v4.md)). The [response to the feedback](#response-to-the-evaluators-feedback) maps each remark of the evaluation to the change and its evidence.

### Where each part of the challenge lives

| Challenge item | Section | Code |
| --- | --- | --- |
| Three or more cooperating agents and how they communicate | [Architecture](#architecture), [Message workflow](#message-workflow) | `orchestration/graph.py`, `orchestration/state.py` |
| Router as entry point and workflow manager | [Architecture](#architecture) | `agents/router.py`, `prompts/router.v6.md` |
| Knowledge Agent: RAG over Getnet's site plus web search | [RAG pipeline](#rag-pipeline) | `rag/`, `agents/knowledge.py` |
| Customer Support Agent with tools | [Support tools and data](#support-tools-and-synthetic-data) | `tools/`, `agents/support.py` |
| HTTP endpoint with a JSON body | [Run it](#run-it), [Message workflow](#message-workflow) | `api/app.py`, `api/schemas.py` |
| Docker | [Run it](#run-it) | `Dockerfile`, `docker-compose.yml` |
| Testing strategy | [Testing and evaluation](#testing-and-evaluation) | `tests/`, `evaluation/` |
| Prompts and use of LLM tools | [How the LLM tools are used](#how-the-llm-tools-are-used) | `prompts/`, `llm/` |
| Bonus: human escalation agent, guardrails, handoff, evaluation and observability | [Guardrails and reliability](#guardrails-and-reliability), [Observability](#observability), [Testing and evaluation](#testing-and-evaluation) | `agents/escalation.py`, `guardrails/`, `observability/` |

Code paths are shortened from `src/merchant_assistant/`; `prompts/`, `tests/`, `Dockerfile` and `docker-compose.yml` are at the repository root. Features built beyond the challenge (an interface, model profiles, an alternative Router engine, a versioned knowledge base, MCP) are described in [Beyond the challenge](#beyond-the-challenge).

## Response to the evaluator's feedback

The V4 evaluation (2026-11-03, 8.6/10) said what separated this case from the top of the ranking. Versions 0.7.0 to 0.10.0 answer every remark except the external access test; what remains is listed under [next steps](#next-steps). Each version went through the same cycle: a specification, tasks, an independent review in a fresh context, QA with real models under a fixed budget cap, and a candidate sealed by hashes before QA ([reports](docs/relatorios/README.md)).

| Dimension (weight, V4 score) | Remark | What changed | Version | Evidence |
| --- | --- | --- | --- | --- |
| Human Oversight & Risk Management (7%, 4.0) | Handoff simulated: a local case with a `SIM-` protocol; no operator queue, no human reply back to the agent, no interrupt and resume | On a handoff the graph pauses at `human_review` (LangGraph `interrupt()`, SQLite checkpoint). A persistent operator queue with claim and idempotent `approve`, `reply` and `reject`; the action resumes the graph and the human reply reaches the merchant in the same conversation, by API and by webhook. A separate ticketing service talks to the assistant only through signed webhooks in both directions | v0.7.0 | [ADR 0018](docs/architecture/decisions/0018-interrupcao-retomada-webhooks.md), [result](docs/evidence/v070-resultado.md), [story QA](docs/evidence/v070-qa.md) |
| Security & Identity (13%, 7.8) | `user_id` was the authority of the payload; no credential → principal → authorization → merchant chain; tool calls not authorized | RS256 JWTs from an own issuer with JWKS; roles and scopes; the merchant comes from the token (`403 identity_mismatch` otherwise); every tool call checks scope and merchant and writes an audit row; revocation, rate limit per principal, MCP with a key | v0.7.0 | [ADR 0017](docs/architecture/decisions/0017-identidade-principal-escopos.md), [result](docs/evidence/v070-resultado.md), [API contract](docs/contracts/api-v040.md) |
| Agentic Reasoning & Orchestration (15%, 8.5) | A predefined combined route; no observe → reconsider → replan → another agent → review loop with a hop limit | A `replan` node after Knowledge, web and Support: named rules first, the model only on ambiguity, a three-hop budget, each specialist at most once, and the origin of every decision in the trace. The four replanning scenarios pass 3/3 with real models and at most 2 hops | v0.8.0 | [ADR 0019](docs/architecture/decisions/0019-replanejamento.md), [pre-holdout QA](docs/evidence/v080-d12-pre-holdout-r6.md) |
| Evaluation & Quality Engineering (14%, 9.0) | No aggregated groundedness, correctness, relevance and usefulness; no independent judge, repeated runs, human calibration or holdout; journeys 7/13 by the literal rubric | `judge.v3` (four criteria plus `unsupported_claim`) by a DeepSeek judge over an OpenAI agent; three agent runs and three judge runs with the agreement reported; dev and holdout separated; the sealed holdout run once (62/75); a 24-answer human calibration (agreement within one point 0.83–1.00, the judge stricter than the human). Journeys 13/13, 12/13 and 12/13 by the deterministic floor and 13/13 by the judge. v0.9.0 added a pre-registered judge experiment: `claude-opus-5-5` over the same 24 human-rated answers agrees more with the human (within one point 0.96 vs 0.83) but still misses 3 of 4 generic claims, so by the rule written beforehand the gap is the rubric and DeepSeek stays the default. v0.10.0 closed the loop: `judge.v4` adds the generic-claim line; re-judged by both models against the same 24 human ratings, DeepSeek's verdict agreement rises 0.67 → 0.79 but it still flags 0 of 4 generic claims, while Opus under v4 flags 2 of 4 without any criterion worsening; by the pre-registered rule v3 stays the default and the gap is rubric and model together | v0.8.0, v0.9.0, v0.10.0 | [campaign](docs/evidence/v080-all-r3.md), [holdout](docs/evidence/v080-holdout-r7.md), [calibration](docs/evidence/v080-calibracao.md), [judge experiment](docs/evidence/v090-juiz-opus.md), [rubric v4](docs/evidence/v0100-juiz-v4.md) |
| Context, Knowledge & RAG (10%, 9.4) | Recall@6 = 1.00 on a small set used during development; no hybrid BM25 + dense, RRF or reranker | BM25 + dense fused by RRF (`RETRIEVAL_MODE`, now `hybrid` by default), a configurable reranker (`rerank.v1`, off by default), nDCG@6 and a sealed 25-question retrieval holdout measured once, last. With real embeddings, nDCG@6 dense → hybrid: 0.868 → 0.974 on dev, 0.880 → 0.921 on the holdout; the default was chosen by a rule written before the measurement | v0.9.0 | [ADR 0020](docs/architecture/decisions/0020-retrieval-hibrido-holdout.md), [report](docs/evidence/v090-retrieval.md), [QA](docs/evidence/v090-qa-retrieval-r1.md) |
| Production Engineering (5%, 9.0) | `/messages` without auth; handoff without human integration; comparison in a thread of the process; external access untested; demo credentials to be configured | `/messages` authenticated and the handoff integrated (v0.7.0); `docker compose up` works without editing `.env.example` (fictitious demo keys); a CI workflow runs the strict suite on every push and pull request; the profile comparison now survives a process kill and resumes from where it stopped (v0.10.0). Still open: the external access test | v0.7.0, CI, v0.10.0 | [workflow](.github/workflows/validate.yml), [result](docs/evidence/v070-resultado.md), [ops QA](docs/evidence/v0100-qa-ops-r1.md) |
| Memory, State & Resilience (8%, 9.0) | A comparison lost on restart is marked failed | The review graph checkpoint and the outbox survive an API restart (v0.7.0). Since v0.10.0 a running comparison whose process dies becomes `interrupted` with its finished cells kept and the in-flight attempt's cost recorded; `POST /v1/comparisons/{id}/resume` runs only the missing cells (real QA: killed after 1 of 6 cells, resumed 5, `completed`, one ledger line per cell). A rolling summary of long conversations remains a next step | v0.7.0, v0.10.0 | [ADR 0018](docs/architecture/decisions/0018-interrupcao-retomada-webhooks.md), [ADR 0022](docs/architecture/decisions/0022-rubrica-v4-operacao-retomavel.md), [ops QA](docs/evidence/v0100-qa-ops-r1.md) |
| Observability, Reliability & Cost (6%, 9.2) | Production next steps only described (OTel, dashboards, alerts) | `GET /metrics` in Prometheus text (requests, model calls, tool calls and failures, handoffs, replan origins, duration histogram, cost per provider, budget) computed from the traces and the ledger, labels from closed sets only; `alerts/rules.yml` with four versioned rules whose metrics a test checks against the endpoint; a two-line `scrape_config` in the README. OTLP and a dashboard remain next steps | v0.10.0 | [Observability](#observability), [ADR 0022](docs/architecture/decisions/0022-rubrica-v4-operacao-retomavel.md) |

---

## Contents

[Response to the feedback](#response-to-the-evaluators-feedback) · 1. [Run it](#run-it) · 2. [Configuration](#configuration) · 3. [Architecture](#architecture) ·
4. [Message workflow](#message-workflow) · 5. [RAG pipeline](#rag-pipeline) · 6. [Support tools and data](#support-tools-and-synthetic-data) ·
7. [How the LLM tools are used](#how-the-llm-tools-are-used) · 8. [Guardrails and reliability](#guardrails-and-reliability) ·
9. [Observability](#observability) · 10. [Testing and evaluation](#testing-and-evaluation) · 11. [Design decisions](#design-decisions) ·
12. [Beyond the challenge](#beyond-the-challenge) · 13. [Limitations and next steps](#limitations-and-next-steps) · 14. [Repository layout](#repository-layout)

---

## Run it

### With Docker (recommended)

Requirements: Docker with Compose v2 and an OpenAI API key.

```bash
cp .env.example .env               # set OPENAI_API_KEY; nothing else is required
docker compose up --build          # API on http://localhost:8000, ticketing on http://127.0.0.1:8002, plus Qdrant and mocks
```

On first start the container seeds the synthetic data (dates relative to *today*) and builds the vector index from
the versioned snapshots (about 37k embedding tokens, ≈ US$0.001). Later starts reuse the index. Startup to healthy:
about 20 s.

Try it (two calls: a token, then the message):

```bash
TOKEN=$(docker compose exec -T api merchant-assistant auth token --url http://localhost:8000)   # cliente1988, demo password
curl -s localhost:8000/messages -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"message": "My card machine won'"'"'t connect to the internet, what should I do?"}'
```

Useful endpoints:

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/auth/token` | OAuth 2.0 token (form encoded): `grant_type=password` for the demo users, `client_credentials` for the ticketing service; returns a JWT (RS256) |
| `POST /messages` | The assistant. Header `Authorization: Bearer <token>`. Body: `{"message": "...", "conversation_id": "conv_..." (optional), "user_id": "..." (optional; must match the token, otherwise `403 identity_mismatch`)}` |
| `GET /health`, `GET /ready` | Liveness; readiness reports index size, database and remaining budget |
| `GET /traces/{request_id}` | Step-by-step trace with a token: merchants see only their own (demo mode, on by default in compose) |
| `GET /.well-known/jwks.json` | Public keys that validate the tokens |
| `GET /docs` | OpenAPI UI with the 10 challenge examples preloaded |

Run the 10 challenge examples against the running API (≈ US$0.03); the command gets the token itself:

```bash
docker compose exec api merchant-assistant smoke --url http://localhost:8000
```

Stop and clean: `docker compose down` (add `-v` to drop the index, traces and budget ledger).

The optional interface, the `/v1` API and the MCP server are described in [Beyond the challenge](#beyond-the-challenge).

### Locally (development)

```bash
uv venv .venv -p 3.13 && uv pip install -e ".[ingest,dev]"   # or: python -m venv .venv && pip install -e ".[ingest,dev]"
merchant-assistant bootstrap                                  # seed data + build the index (embedded Qdrant)
uvicorn --factory merchant_assistant.main:create_application --reload
merchant-assistant ask "Qual a cotação do euro hoje?" --trace  # one message, in process, with its trace
```

### Tests and evaluation

```bash
pytest                                   # backend tests; use tools/scripts/lint_and_tests.py --strict for strict validation
ruff check .
merchant-assistant eval --scripted       # end-to-end evaluation offline (wiring only, zero cost)
merchant-assistant eval --judge          # real evaluation; paid, check the current budget before running
merchant-assistant eval --judge --include-replan --split dev --limit 5 --no-conversations --name v080-cost-sample  # five-case cost sample
merchant-assistant eval-estimate --from docs/evidence/v080-cost-sample.json --out docs/evidence/v080-cost-estimate.json  # D12 estimate; no model call
merchant-assistant eval --campaign v080-qa --include-replan --judge --repeat 3 --split all  # fixed QA cap + installation ledger
merchant-assistant eval --campaign v080-qa --judge-repeat 3 --answers-from docs/evidence/v080-all.json --name v080-all-judge  # judge variation; the agent does not run
merchant-assistant eval --campaign v080-qa --judge --repeat 3 --split holdout_v080  # sealed holdout: once, as the last technical step
merchant-assistant eval-calibrate --sample 24 --from docs/evidence/v080-all-r3.json   # CSV for the owner to rate, without the judge's scores; no model call
merchant-assistant eval-retrieval --mode hybrid --split dev --out docs/evidence/retrieval.md   # Recall@6, MRR, nDCG@6 per mode; --split holdout_v090 once, last
merchant-assistant eval --judge-repeat 3 --answers-from docs/evidence/v080-all-r3.json --only-sample docs/evidence/v080-calibracao-amostra.csv --rubric v4 --name my-run  # re-judge the calibration sample under another rubric or judge
merchant-assistant eval-calibrate --import docs/evidence/v080-calibracao-amostra.csv  # human × judge agreement and kappa; no model call
merchant-assistant eval-retrieval        # Recall@k of the RAG index (≈ US$0.001)
merchant-assistant ingest                # re-collect the official pages into snapshots (network)
```

`eval --judge` uses the independent judge (`JUDGE_PROVIDER`, `JUDGE_MODEL`). `--repeat 3` measures the variation of the assistant (the judge grades each answer once); `--judge-repeat 3 --answers-from` measures the variation of the judge over recorded answers. `--campaign v080-qa` mounts its fixed cap once (US$0.50; US$1.00 or US$1.10 with `--campaign-estimate` and a verified `eval-estimate`). That campaign is already mounted at US$1.40 after the approved contingency: `--campaign-cap-usd 1.40 --campaign-estimate docs/evidence/v080-custo-estimativa-r3.json` only continues it and never mounts a new one.

The seed dates the synthetic sales relative to the day it ran ("yesterday" is the day before the seeding). A paid QA run must run `merchant-assistant bootstrap` (or a container start, which seeds) on the same local day, or the date-dependent cases are invalid.

## Configuration

All settings come from environment variables (or `.env`). Defaults are safe for a reviewer's own key.

| Variable | Default | Meaning |
| --- | --- | --- |
| `OPENAI_API_KEY` | — | Required for real calls (agents, embeddings, web search) |
| `AGENT_MODEL` | `gpt-6-luna` | Default model for every agent; the `/v1` model profiles can set another model per agent |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | RAG embeddings |
| `QDRANT_URL` | empty (embedded store) | Compose sets `http://qdrant:6333` |
| `BUDGET_RUNTIME_DIR` | `data/runtime` locally, `/app/runtime` in Docker | Persistent budget ledgers for the `eval` campaigns; keep it pointed at the project budget volume when `RUNTIME_DIR` is isolated for a QA run. The API and `bootstrap` write their ledger under `RUNTIME_DIR` (so an isolated runtime starts a ledger of its own, capped by `BUDGET_LIMIT_USD`) |
| `MOCKS_URL` | `http://mocks:8001` | Internal synthetic pricing and charge service; Compose only |
| `BUDGET_LIMIT_USD` | `1.00` | Hard cap for all paid calls of this installation (persistent ledger). Accepted range 0–5.00 (absolute project ceiling); the first limit recorded beside a ledger (`budget.sqlite3.limit`, native 1.00 for a ledger that predates it) can never be raised by a later value |
| `MAX_REQUEST_COST_USD` | `0.05` | Cap per request |
| `MAX_MODEL_CALLS`, `MAX_TOOL_CALLS`, `MAX_REQUEST_SECONDS` | `8`, `8`, `90` | Per-request limits |
| `WEB_SEARCH_MAX_CALLS` | `1` | Searches per general question |
| `DEMO_MODE` | `false` (`true` in compose) | Enables `GET /traces/{id}` |
| `TIMEZONE` | `America/Sao_Paulo` | Used to resolve "yesterday", "today" |
| `DEMO_SESSION_MESSAGE_LIMIT` | `20` | Paid actions one demo session may start: messages, new comparison executions, Router comparisons and AI evaluations; refusals and skipped comparison cells without a model call do not count (they are given back); enforced by the backend |
| `EVALUATOR_PROVIDER`, `EVALUATOR_MODEL` | `openai`, `gpt-6-luna` | Fixed on-demand evaluator, independent of the evaluated profile and recorded with every evaluation |
| `JUDGE_PROVIDER`, `JUDGE_MODEL` | `deepseek`, `deepseek-flash` | Independent judge for `eval --judge`; the default requires `DEEPSEEK_API_KEY` and must differ from the agent model |
| `DEMO_USER_PASSWORDS` | fictitious values in `.env.example` | `user:password` pairs of the synthetic users (`cliente1988`, `cliente_demo_002`, operators `op_ana`, `op_bruno`); stored as PBKDF2 hashes |
| `API_DEMO_PASSWORD`, `API_ADMIN_PASSWORD` | empty (off) | Passwords of the `demo` and `admin` users of the `/v1` interface |
| `JWT_ISSUER`, `JWT_PRIVATE_KEY_PATH`, `JWT_JWKS_URL` | own issuer, key generated in the runtime | Token issuer; `JWT_JWKS_URL` switches verification to an external OIDC issuer |
| `RATE_LIMIT_PER_MINUTE` | `30` | Requests per principal |
| `TICKETING_WEBHOOK_URL`, `CONVERSATION_WEBHOOK_URL` and their secrets | Compose values | Signed webhooks to the ticketing service and to the merchant receiver; an empty URL turns a destination off; a URL without a secret is warned at startup |
| `WEBHOOK_MAX_ATTEMPTS`, `WEBHOOK_RETRY_WAITS_S`, `WEBHOOK_TIMEOUT_S` | `3`, `1,2`, `3` | Delivery attempts (total per event and destination, also across restarts) |

`DEEPSEEK_API_KEY` is required for the default `eval --judge` evaluator and optional for the DeepSeek model profiles (Hybrid: Router; Adjusted: Router and Support). `TYPESAFE_API_KEY` enables the alternative Router engine; neither key is needed for `POST /messages`. Every secret in `.env.example` is a fictitious demo value named as such; the API warns at startup when one of them is in use. The web app signs in with a user and password and never receives a provider key.

## Architecture

```mermaid
flowchart LR
    In([POST /messages]) --> G[Input guard<br/>mask PII · block injection]
    G -->|blocked| P
    G --> R{{Router Agent}}
    R -->|knowledge / general_web| K[Knowledge Agent<br/>RAG or web search]
    R -->|support| SP[Case prefix<br/>history + healthcheck]
    R -->|knowledge_and_support| SP
    R -->|human_handoff| SP
    R -->|clarify / out_of_scope / acknowledgement| P
    SP -->|support| S[Customer Support Agent<br/>tool calling]
    SP -->|knowledge_and_support| K
    SP -->|human_handoff| E[Escalation Agent]
    K --> RP{{Replan}}
    W[Web search] --> RP
    S --> RP
    RP -->|knowledge| K
    RP -->|web| W
    RP -->|support| S
    RP -->|escalate| E
    RP -->|finish / clarify| P
    E --> P[Personality<br/>final voice]
    P --> O[Output guard<br/>values must match evidence] --> Out([JSON response])
```

This is the workflow from the challenge diagram (Router → specialists with tools → **Personality** → output), with
the "custom agent" slot filled by the Escalation Agent. After each Knowledge, web-search or Support result, the
replanner can finish, call a different specialist, search the web, escalate or ask a clarifying question. Clear cases
are decided by rules; `replan.v2` is reserved for ambiguous decisions, and at most three plan changes are allowed.
The reported route remains the Router's initial plan; the trace records the path that actually ran.

| Component | Kind | Responsibility |
| --- | --- | --- |
| Router Agent | LLM, structured output | Picks one of the 8 routes below, the language, the support topic and a safety label |
| Knowledge Agent | LLM + RAG / web search | Answers from retrieved official passages (with citations) or one web search; gives the official procedure on combined routes |
| Customer Support Agent | LLM + function calling | Looks up the merchant's data with 9 tools (plus 2 run by code at case opening) and explains it; asks to choose when needed; flags escalation |
| Replanner | Rules + LLM on ambiguity | Reviews specialist evidence after each step and selects the next action within a three-hop limit |
| Escalation Agent | LLM + persistence | Writes the handover summary, opens an idempotent case with an `HO-` protocol and pauses the graph until an operator acts on the ticket ([human in the loop](#identity-and-human-in-the-loop-v070)) |
| Personality | LLM | Turns the agents' structured contributions into one reply, in the merchant's language, without changing facts |
| Input / output guards, case prefix | Deterministic code | Masking and injection blocking; history + healthcheck at case opening; evidence check of values |

**Communication mechanism.** A LangGraph `StateGraph` over a typed Pydantic state. Agents are plain functions that
read the state and return updates (direct calls, no queue). The Router's decision is validated by code and then
applied by conditional edges. A per-request context (passed through the graph config) carries the model client,
tools, budget meter, limits and the trace recorder.

**Routes.**

| Route | When | Path |
| --- | --- | --- |
| `knowledge` | Product and service questions (Get Smart vs Clássica, Pix, antecipação, crediário, Payment Link) | Knowledge (RAG, official pages only) |
| `general_web` | Harmless general questions (weather, exchange rate) | Knowledge (one web search) |
| `support` | Needs the merchant's own data (yesterday's sales) | Prefix → Support |
| `knowledge_and_support` | A problem with an official procedure *and* account data (machine offline, declined sale) | Prefix → Knowledge (procedure) → Support |
| `human_handoff` | Merchant asks for a person | Prefix → Escalation |
| `clarify` | Too vague | Personality asks one question |
| `out_of_scope` | Unsafe, sensitive or injection | Personality declines and says what it can do |
| `acknowledgement` | Reaction to the previous reply with no new request ("it works now", "thanks") | Personality; case state updated |

## Message workflow

Example: *"When will the money from yesterday's sales be deposited?"* (`cliente1988`).

1. **Input guard** masks card numbers (Luhn), CPF/CNPJ, e-mails and credentials, and blocks clear prompt-injection
   patterns before any model call.
2. **Router** returns `{"route": "support", "topic": "receivables", "language": "en", "safety": "none", ...}`.
3. **Case prefix** (no model): `get_complaint_history` and `run_customer_healthcheck` for the topic, once per case.
4. **Customer Support** calls `get_receivables_schedule(period="yesterday")`, then
   `get_payout_status([...ids])`, and returns structured points.
5. **Personality** writes the reply; the **output guard** checks that every amount and date appears in the tool
   results.

```json
{
  "answer": "Yesterday's sales have different payment dates: R$ 80,00 from Pix was credited on October 25, 2026; R$ 148,06 from debit is expected today, October 26, 2026; and R$ 1.162,20 from credit is expected on October 27, 2026. The debit and credit payouts are scheduled, but their credits have not yet been confirmed in your account.",
  "status": "answered",
  "route": "support",
  "agents": ["router", "customer_support", "personality"],
  "language": "en",
  "sources": [
    {"type": "tool", "title": "Receivables schedule (your account)", "observed_at": "..."},
    {"type": "tool", "title": "Payout status (your account)", "observed_at": "..."}
  ],
  "request_id": "req_...",
  "conversation_id": "conv_...",
  "resolution": {"state": "awaiting_customer", "evidence": null},
  "handoff": null
}
```

`status` is one of `answered`, `needs_clarification`, `handoff`, `refused`. `resolution` is separate from the
request status: answering does not close the case. Handoffs add `{"protocol": "HO-…", "reason": "..."}`; replies also carry `via` (`agent`, or `operator` for a human reply).


### Replanning, as it ran

The V4 feedback asked for `agent → observe result → Router reconsiders → replan → different agent → review`, with a
hop limit. Since v0.8.0 a `replan` node runs after Knowledge, web and Support and decides `finish`, `knowledge`,
`web`, `support`, `escalate` or `clarify`; named rules decide the clear cases, `replan.v2` decides only when no rule
applies or two disagree, each specialist runs at most once, and `MAX_PLAN_HOPS=3` bounds the plan changes. Every
decision carries its origin in the trace. A real request from the v0.8.0 QA (`req_eval866ca888dc9d`, 2 hops: the
Router planned `support`, replanning added the official procedure and then the web):

```text
 2 router          2668 ms  route=support
 6 support         7035 ms  (3 tools)
10 replan             0 ms  next=knowledge  origin=rule:procedure_gap           hops=1  "support covered the account part; the how-to part needs the official procedure"
11 knowledge       5199 ms
12 replan             0 ms  next=web        origin=rule:evidence_insufficient_web hops=2  review=incomplete
13 web             5394 ms
14 replan             0 ms  next=finish     origin=rule:complete                 hops=2  review=complete
15 personality     2691 ms
```

Across the whole v0.8.0 QA runtime (400 `replan` steps), 382 decisions came from rules and 18 from the model; the
model decided only ambiguous cases (9 → `support`, 8 → `web`, 1 → `finish`). Rules first is a design choice:
deterministic, free, and auditable by name. The four replanning scenarios passed 3/3 each with real models
(`REPLAN-ACCOUNT` 2 hops, `REPLAN-WEB` 1, `REPLAN-PROCEDURE` 0 extra, `REPLAN-TOOL-DOWN` 1 with an `HO-` protocol
instead of an invented number) ([pre-holdout QA](docs/evidence/v080-d12-pre-holdout-r6.md)).

## Conversations and case follow-up

Since v0.2.0 a conversation carries memory and a case state.

- **Ownership.** `conversation_id` belongs to the merchant that started it; another merchant's token gets
  `404 conversation_not_found`. Without an id, the server creates one and returns it.
- **History.** The last turns (up to 10 messages / 1,200 tokens, masked) go to the Router, Customer Support and
  Personality as data, so "I already did that" is understood in context.
- **Case state.** `in_progress` → `awaiting_customer` after each reply → `resolved` only with evidence
  (`customer_confirmed` when the merchant says it works, or `tool_verified` when a tool shows it) → or `handoff`.
  "Thanks" alone never resolves. The state is returned in `resolution`.
- **Technical follow-up.** Each suggested step is recorded per cycle with the merchant's feedback; steps are never
  repeated; after two failed cycles (or on request) the case goes to a human with the attempts. A case already with
  a human keeps one protocol.
- **Prefix reuse.** History and healthcheck run once per case and topic, refreshed after 30 minutes or when the
  topic changes.

```bash
curl -s localhost:8000/messages -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"message": "Já fiz isso e continua sem conexão", "conversation_id": "conv_..."}'
```

## RAG pipeline

**Ingestion → storage → retrieval → generation.**

1. **Sources.** [`data/sources/public-sources.json`](data/sources/public-sources.json): 32 official pages verified
   by hand on 2026-10-26: `https://www.getnet.net/en/` (required) plus the Brazilian site pages behind the challenge
   examples (card machines, Pix, crediário, Payment Link, antecipação, Wi-Fi setup, machine errors, sales status,
   FAQ). `robots.txt` allows all of them.
2. **Collection** (`merchant-assistant ingest`, explicit, never at startup). HTTP fetch with an identified user
   agent and 1 s delay; extraction with trafilatura and BeautifulSoup, keeping the richer result; removal of
   repeated site boilerplate; pages with too little text fail loudly. Two pages are built by JavaScript (the card
   machine catalogue and the rates table); their rendered text was captured in a browser and is versioned in
   `data/snapshots/public/rendered/`.
3. **Snapshots.** Every page is stored as JSON in `data/snapshots/public/pages/` (URL, title, collection date,
   capture method, content hash, text). The index is always rebuilt from these files, so Docker builds and
   evaluations never depend on the live site.
4. **Demo corpus.** Eight synthetic operating procedures (`data/knowledge-demo/`, `source_kind =
   simulated_internal`) describe how the demo back-ends behave (for example, documented decline codes). They are
   cited as demo procedures, never as official Getnet rules.
5. **Chunking.** Section-aware (Markdown headings or paragraphs), ~1,200 characters with overlap; each chunk keeps
   its title, URL, source kind, collection date and hash. 40 documents → 145 chunks.
6. **Storage.** Qdrant (service in compose, embedded locally, in-memory in tests), `text-embedding-3-small`. The
   index manifest records model, corpus hash and size; bootstrap builds the index only when its collection does not exist and never rebuilds or replaces an existing one (a new knowledge base version is always a new collection, created through the admin API).
7. **Retrieval.** Hybrid by default since v0.9.0: dense top-18 by cosine similarity (minimum score) and BM25 over the
   same chunks, fused by reciprocal rank fusion (`k=60`, dense tie-break) into the top-6; a source-kind filter (official
   pages only for product questions; official + demo procedures for problems) applies to both lists. `RETRIEVAL_MODE=dense`
   restores the v0.8.0 behavior; `RERANK=on` adds a model reordering of the first 12 hits (off by default, see ADR 0020).
8. **Generation.** Numbered passages go to the Knowledge Agent, which must answer only from them, list the passages
   it used and set `evidence_sufficient = false` when they do not cover the question. Citations are built by code
   from the passage numbers.

**Retrieval quality.** Measured with real embeddings on the 19-question development set and, once, on the sealed
25-question holdout `retrieval_holdout_v090` (13 in Portuguese; graded relevance by chunk; written before any mode was
measured; [report](docs/evidence/v090-retrieval.md)):

| Split | Metric | dense | hybrid | hybrid + reranker |
| --- | --- | ---: | ---: | ---: |
| dev (19) | Recall@6 / MRR / nDCG@6 | 0.895 / 0.860 / 0.868 | 1.000 / 0.965 / 0.974 | 1.000 / 0.974 / 0.981 |
| holdout_v090 (25) | Recall@6 / MRR / nDCG@6 | 1.000 / 0.871 / 0.880 | 1.000 / 0.920 / 0.921 | 1.000 / 0.980 / 0.961 |
| holdout_v090 | time per query | 584 ms | 534 ms | 2,392 ms |

The decision rule was written before the measurement (spec D7): hybrid becomes the default if its nDCG@6 is strictly
higher on both splits, which it is. The reranker also improves both splits, but its gain includes the effect of the
deeper fusion and it quadruples latency, so it stays off this version ([ADR 0020](docs/architecture/decisions/0020-retrieval-hibrido-holdout.md)).
English questions retrieve Portuguese content directly, so no query translation is used.

## Support tools and synthetic data

The Support Agent has nine tools, plus two used by code at case opening.

| Tool | Arguments from the model | Returns |
| --- | --- | --- |
| `get_receivables_schedule` | `period` (yesterday, today, last/next 7 days) or dates; filter by sale or payment date | Net/gross amounts, fees, expected payment dates, original and normalized status |
| `get_payout_status` | `receivable_ids` | Payout stage and whether the credit is confirmed |
| `get_device_status` | `device_id` (optional) | Model, connectivity, status, last signal; asks to choose when there are several |
| `find_authorization_events` | `period`, `status`, `limit` (no transaction id needed) | Declines with documented reason and next step; unknown codes stay unknown |
| `get_contract_snapshot` | — | Products, settlement account type and plan |
| `simulate_pricing` | `period`, `payment_type`, `installments`, `sale_date` (optional filters) | Independent pricing rule and charge evidence, compared in integer cents |
| `get_fee_breakdown` | Same bounded sale filters | Read-only recorded charge components |
| `get_enablement_requests` | `scheme` (optional) | Existing protocol, request/activation status and device availability |
| `get_sale_cancellation_context` | `period` | Existing sale cancellation status; no action is executed |
| `get_complaint_history` *(prefix)* | `topic` | Previous cases and attempts |
| `run_customer_healthcheck` *(prefix)* | `topic` | Predefined checks: ok, pending, attention, unknown, unavailable |

- **Customer binding.** The customer comes from the request context (`user_id`), never from model arguments; no tool
  schema contains a customer field. Asking for another merchant's resource returns `FORBIDDEN_RESOURCE`, no data,
  and an audit record. `user_id` identifies a demo scenario and does not prove identity; in production it would come
  from authentication.
- **Synthetic data** (SQLite, seeded at startup): `cliente1988` has three sales from *yesterday* (debit, credit, Pix),
  a Get Smart that went offline three hours ago, a declined transaction today and a previous Wi-Fi case;
  `cliente_demo_002` exists to test isolation. All dates are relative to the clock, so "yesterday" always works.
  Tests use a fixed clock (2026-10-26). Unknown `user_id`s can still ask product questions.
- **Status vocabulary.** Original status names are preserved and mapped by a versioned glossary (for example
  `LOT_DONE` = batch processed, *not* money in the account). The agent only says a credit is confirmed when the
  payout tool says so.
- **Pricing services.** Compose runs an internal `mocks` HTTP service with separate versioned pricing and charge
  fixtures. The app selects sales from the bound merchant's synthetic records; no tool accepts a customer ID or
  requires a sale ID from the merchant. Comparisons require matching customer, transaction, currency, conditions
  and internally consistent component/instalment totals. The four outcomes are consistent, different conditions,
  divergence and insufficient evidence. All values and rules are fictional.
- **Read-only journeys.** A pending card-scheme request reuses its protocol; account activation and device
  availability remain separate facts. Sale cancellation is a lookup. Contract termination goes to an attendant and
  does not call sale tools. No financial, enablement, cancellation or contract action is executed.

## How the LLM tools are used

All calls go through one provider-agnostic interface (OpenAI Responses API in production, a scripted model in
tests), with `store=false`:

- **Structured outputs** (`responses.parse` with Pydantic models) for the Router decision, Knowledge drafts,
  Support results, Escalation summaries and the Personality reply. Invalid outputs fall back to safe paths.
- **Function calling** for the Support Agent: a loop that executes the tools the model requests (several per turn
  when it asks), returns results as `function_call_output`, enforces the per-request tool limit and ends with a
  structured answer.
- **Built-in web search** for general questions, capped at one search per question; sources come from the answer's
  citations or from the search call itself.
- **Reasoning effort** is `none` for Router, Escalation and Personality and `low` for the specialists, to keep cost
  and latency down.
- **Prompts** are versioned files in [`prompts/`](prompts/) (`id` + `version`), and every trace records which
  version ran.
- **Prompt design.** Each prompt states the agent's role and what it may use (routes with examples, tools, numbered
  passages), injects the current date and the case facts the code already checked, lists the rules it must never
  break (no refund promises, no internal IDs asked from the merchant, no gaps filled from outside knowledge) and ends
  in a typed output schema. Retrieved passages, tool results and history are marked as data, not instructions.

## Guardrails and reliability

| Risk | Control |
| --- | --- |
| Sensitive data in messages | Masked before any model call, log or web query (cards with Luhn check, CPF, CNPJ, e-mail, credentials) |
| Prompt injection | Pattern block at input; Router safety label forces `out_of_scope`; retrieved text and tool results are framed as data |
| Unsafe or off-topic requests | Declined with what the assistant *can* do; harmless general questions go to web search |
| Hallucinated values | Output guard: every amount, date and percentage in the reply must appear in this request's evidence (tool results, retrieved passages, web answer). Offending sentences are dropped or a deterministic reply is used |
| Missing evidence | "I couldn't find this in the official sources", never a guess; status stays honest |
| Cross-customer access | Server-side binding, `FORBIDDEN_RESOURCE`, audit log |
| Dependency failure | Every agent catches provider, limit and budget errors; failed tools escalate; human handoff works even if all tools fail |
| Runaway cost or loops | Per-request limits (model calls, tool calls, time, cost) and a persistent installation budget with atomic reservations before each paid call; unknown prices block the call |
| Duplicate handoffs | Idempotency key per conversation, message and reason |

## Observability

- **Structured JSON logs** on stdout: one line per step and per request (`request_id`, route, agents, tools,
  duration, tokens, cost, model, errors). Message text is not logged.
- **Traces** in SQLite (`runtime/traces.sqlite3`): every node and tool call with duration, status, prompt version,
  retrieval hits and guard results. `GET /traces/{request_id}` in demo mode.
- **Budget ledger** (`runtime/budget.sqlite3`): every paid call with reserved and actual cost; `/ready` shows what
  is left.
- **Metrics** (`GET /metrics`, public like `/ready`): Prometheus text format 0.0.4, computed on demand from the `/metrics` is public like `/ready` and carries only aggregated counts; in production, restrict it by network or by a read token.
  traces and the ledger and cached for 5 s, with no Prometheus library. Every label value is checked against a
  closed set in the code (route, status, agent, tool, outcome, replan origin, provider) and anything else becomes
  `other`, so no message text, request id, merchant or operator reaches a label. An empty or locked store does not
  fail the scrape: the last complete read is served again (zeroed families before the first one).

  | Metric | Type | Labels |
  | --- | --- | --- |
  | `requests_total` | counter | `route`, `status` |
  | `model_calls_total` | counter | `agent` |
  | `tool_calls_total` | counter | `tool`, `outcome` |
  | `tool_failures_total` | counter | `tool` |
  | `handoffs_total` | counter | — |
  | `replan_total` | counter | `origin` |
  | `request_duration_seconds` | histogram (1, 2, 5, 10, 20, 30, 60 s, +Inf) | — |
  | `cost_usd_total` | counter (settled spend) | `provider` |
  | `budget_remaining_usd`, `budget_limit_usd` | gauge | — |

- **Alert rules** in [`alerts/rules.yml`](alerts/rules.yml) (Prometheus format, group `merchant-assistant`): budget
  below 10% of the limit, tool failure rate above 5% over 15 min, handoff rate above 30% over 1 h, p95 duration
  above 20 s over 15 min. A test checks that every metric in the rules exists in `/metrics`. `requests_total` and
  the duration histogram also count operator replies delivered to the merchant (`route="human_reply"`) and
  resumed requests, so they are in the denominators of the handoff rate and the p95. To scrape it with a
  local Prometheus, add to `scrape_configs` (and `rule_files: [alerts/rules.yml]`):

  ```yaml
  - job_name: merchant-assistant
    static_configs: [{targets: ["localhost:8000"]}]
  ```

- **Production next steps:** export the same spans to OpenTelemetry/Langfuse (OTLP), dashboards for route mix,
  handoff rate, guard blocks, p95 latency and cost per resolved case, and alerts on retrieval score drift.

## Testing and evaluation

**Strategy.**

| Level | What | Cost |
| --- | --- | --- |
| Unit | Tools (binding, filters, dates, errors), clock and seed, chunking, guards, pricing, budget atomicity, Router rules | 0 |
| Contract | API schemas and error body, agent output schemas, tool schemas without customer fields | 0 |
| Integration (deterministic) | Full graph through HTTP with a **scripted model**, hashing embedder, in-memory Qdrant, seeded data and fixed clock: the 10 examples, Portuguese variants, refusal, injection, masking, handoff idempotency, tool and index failures, unknown user, limits, output guard, traces; multi-turn conversations, ownership, case states, two technical cycles; MCP through an in-process client | 0 |
| Release validation (real) | The 44 labeled cases, 13 business journeys and 4 multi-turn conversations against real models on each release candidate, three runs each, judged by an independent model; sealed holdout run once, last; see the [v0.8.0 evidence](docs/evidence/v080-d12-pre-holdout-r6.md) | Paid and capped (v0.6.0 QA: US$0.088) |
| Retrieval | Recall@6, MRR and nDCG@6 per mode on the development set and, once, on the sealed retrieval holdout | ≈ US$0.003 per configuration (US$0.016 for the six) |
| Docker smoke | Clean build, startup, 10 examples over HTTP | ≈ US$0.03 |

The scripted model follows simple rules for each agent, so the whole system (routing, tool execution, guards,
persistence, tracing) runs without network. It checks the wiring, not answer quality; quality comes from the real
evaluation.

**Validated evidence (v0.8.0 to v0.10.0, real models).** Strict suite **2,147 tests** at v0.10.0 (1,997 at v0.8.0), Ruff clean. The V4 feedback asked for
aggregated groundedness, correctness, relevance and usefulness, an independent judge, repeated runs, a holdout and
human review; this is the main table, from the [campaign](docs/evidence/v080-all-r3.md), the
[holdout](docs/evidence/v080-holdout-r7.md), the [calibration](docs/evidence/v080-calibracao.md) and the
[judge experiment](docs/evidence/v090-juiz-opus.md). The judge is `deepseek-flash` over an OpenAI agent (`judge.v3`,
scores 1–5 against the masked evidence of each answer); "±1" is the share of repeated runs within one point.

| Set (agent runs × judge) | groundedness | factual_correctness | relevance | usefulness | unsupported_claim rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development, 44 cases × 3 runs | 4.56 (±1 0.93) | 4.62 (±1 0.96) | 4.77 (±1 1.00) | 4.53 (±1 0.97) | 0.14 |
| Sealed holdout `holdout_v080`, 25 cases × 3 runs, run once | 4.67 (±1 0.96) | 4.61 (±1 0.93) | 4.83 (±1 0.96) | 4.64 (±1 0.93) | 0.08 |
| Judge repeated 3× on the holdout answers (judge variation) | 4.61 (±1 0.99) | 4.59 (±1 0.97) | 4.80 (±1 1.00) | 4.60 (±1 1.00) | 0.11 |

Deterministic checks on the same runs: replanning scenarios 3/3 each, business journeys **13/13, 12/13, 12/13**
(the two refusals are correct paraphrases the literal floor rejects; the judge gave 13/13), conversations 4/4,
holdout 62/75 by the literal floor.

**Human review of the judge.** The owner rated a stratified sample of 24 answers with the judge's rubric, without
seeing its scores; then the same 24 answers were judged by `claude-opus-5-5` under a decision rule written before
the run (spec D2):

| Agreement with the human (24 answers) | DeepSeek (default judge) | Claude Opus 5.5 |
| --- | ---: | ---: |
| Within one point: groundedness / factual / relevance / usefulness | 0.83 / 0.83 / 1.00 / 0.92 | 0.96 / 0.96 / 1.00 / 0.96 |
| Bias (judge − human), groundedness | −0.33 | −0.17 |
| `unsupported_claim` verdict: exact agreement, kappa | 0.67, −0.20 | 0.88, 0.36 |
| Generic claims the human flagged (4) that the judge flagged | 0 | 1 |
| Self-consistency over 3 repetitions (exact) | 0.76–0.86 | 0.81–1.00 |
| Cost per judgement | US$0.0003 | US$0.0178 |

Both judges are stricter than the human; neither flags the generic claims the human flagged. The pre-registered rule
said that this outcome means the gap is in the rubric, not the model, so DeepSeek stays the default and the rubric
gains a line for generic claims without a source ([next steps](#next-steps)). The quadratic kappa of the 1–5 scores is
near zero because almost every human score is 5 (ceiling effect); the within-one-point agreement is the usable figure.

History: v0.6.0 passed 27/27 core cases and 4/4 conversations with 7/13 journeys under the literal rubric
([v0.6.0 result](docs/evidence/v060-resultado.md)); Recall@6 = 1.00 on 14 development questions, which v0.9.0 replaces
with a sealed retrieval holdout.

## Design decisions

Recorded as ADRs (in Portuguese) in [`docs/architecture/decisions/`](docs/architecture/decisions/):

- **Python 3.13 + FastAPI + Pydantic v2** for strict contracts and OpenAPI out of the box.
- **LangGraph with typed state** so every request follows an explicit, testable path; agents stay plain functions,
  so the framework is confined to one module.
- **Qdrant + versioned snapshots**: reproducible builds and evaluations independent of the live site.
- **Synthetic data in SQLite, tools as domain functions**: testable without network; one place enforces customer
  isolation. The MCP server (v0.2.0) exposes the same functions.
- **OpenAI baseline with a persistent budget guard**: a reviewer needs only one key; spending is capped before it
  happens.

Other choices: a deterministic case prefix (history + healthcheck) instead of letting the model decide; Personality
as a separate, guarded step (from the challenge diagram) so tone changes cannot alter facts; answers in the
merchant's language while code, prompts and this README are in English.

## Beyond the challenge

Later increments built on the same core (graph, agents, tools and guards), each with its own specification, independent review and QA. None of them is needed to evaluate the challenge: `POST /messages` works without them.

| Version | Added | Why |
| --- | --- | --- |
| v0.2.0 | [Conversations and case follow-up](#conversations-and-case-follow-up); MCP server | Multi-turn continuity; the same tools for external agents |
| v0.3.0 | Read-only journeys: pricing disputes with an independent pricing service, card-scheme enablement, sale-cancellation status | The questions where a wrong answer becomes a financial promise |
| v0.4.0 | Authenticated `/v1` API, per-agent model profiles (Reference: all `gpt-6-luna`; Hybrid: Router on DeepSeek; Adjusted: Router and Support on DeepSeek), per-request Router engine (LLM or TypeSafe JEV), Streamlit interface | Controlled configuration and comparison; the same validated Router contract for every engine |
| v0.5.0 | Versioned knowledge base: draft, candidate collection, test, activation and rollback by an administrator | Documentation changes are tested before they apply and can be undone |
| v0.6.0 | Interface with Attendance, Results and Administration; labeled scenarios; deterministic checks and on-demand model evaluation of stored replies; small profile comparison | A demonstrable, auditable closing of the case |
| v0.7.0 | JWT identity with scopes checked on every tool call; real human in the loop: the graph pauses on a handoff, a separate ticketing service and its operator screen work the ticket, and the operator's action resumes the graph | The merchant comes from a verified token, and a human answer reaches the merchant in the same conversation |
| v0.10.0 | `judge.v4` measured against the human calibration with both judges (not promoted by the pre-registered rule); comparison that survives a process kill and resumes; `GET /metrics` and versioned alert rules | The rubric finding of v0.9.0 closed with numbers; two literal remarks of the feedback (comparison lost on restart, alerts only described) answered |
| v0.9.0 | Hybrid retrieval (BM25 + dense, RRF) chosen on a sealed retrieval holdout by a pre-registered rule; optional reranker; Anthropic judge and a pre-registered judge-model experiment against the human calibration | The retrieval remark of the feedback closed with numbers, and the judge choice made by experiment rather than preference |
| v0.8.0 | Replanning after each specialist (rules first, model on ambiguity, three-hop budget, origin in the trace); four-criterion `judge.v3` by an independent judge, repeated runs and a human calibration sample; sealed v0.8.0 holdout | The assistant reacts to what a specialist returned, and answer quality is measured semantically, not only by literal labels |

### Identity and human in the loop (v0.7.0)

**Two breaking changes.** `POST /messages` requires `Authorization: Bearer <token>` (the merchant comes from the token; a different `user_id` in the body gets `403 identity_mismatch`), and `POST /v1/sessions` / `DELETE /v1/sessions/current` were replaced by `POST /v1/auth/token` and `POST /v1/auth/revoke`. The evaluator's two calls are in [Run it](#run-it); `merchant-assistant smoke` and `merchant-assistant auth token` get the token themselves.


**The loop, end to end.** This is the flow the V4 feedback asked for, and the commands that drive it against the
Compose stack (the operator side goes through the same `/v1/handoffs` API the ticketing service and the CLI use):

```text
Merchant message
    ↓
Escalation agent → case HO-… → graph pauses at human_review (LangGraph interrupt(), SQLite checkpoint)
    ↓
Operator (op_ana) claims the case and replies / approves / rejects
    ↓
Command(resume): the reply becomes a turn marked via=operator, delivered on the merchant's next message
    ↓
Merchant message → route human_reply (no model call), GET /v1/conversations/{id} and webhook carry it too
```

```bash
TOKEN=$(docker compose exec -T api merchant-assistant auth token --url http://localhost:8000)          # cliente1988
curl -s localhost:8000/messages -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"message": "Quero falar com um atendente humano"}'            # status "handoff", handoff.protocol "HO-…", conversation_id "conv_…"
OP=$(docker compose exec -T api merchant-assistant auth token --username op_ana --url http://localhost:8000)   # operator
curl -s "localhost:8000/v1/handoffs?state=open" -H "Authorization: Bearer $OP"                      # the case_id
curl -s -X POST localhost:8000/v1/handoffs/<case_id>/claim -H "Authorization: Bearer $OP"
curl -s -X POST localhost:8000/v1/handoffs/<case_id>/actions -H "Authorization: Bearer $OP" -H 'content-type: application/json' \
  -d '{"action": "reply", "text": "Your payout was sent today.", "idempotency_key": "demo-reply-0001"}'
curl -s localhost:8000/messages -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"message": "Any news?", "conversation_id": "<conversation_id>"}'   # route "human_reply", via "operator", the operator's text
```

Repeating the claim is idempotent; repeating the action with the same `idempotency_key` returns the first result; a
second resume of the same case gets `409 already_resumed`. The v0.7.0 story QA walked this sequence with real models
and the ticketing screen ([story QA](docs/evidence/v070-qa.md), moments 6 to 14).

- **Identity** ([ADR 0017](docs/architecture/decisions/0017-identidade-principal-escopos.md)). The assistant issues RS256 JWTs (own issuer, JWKS and discovery; an external OIDC issuer is a configuration change). Roles `merchant`, `operator`, `service`, `demo` and `admin` carry scopes; every tool call checks scope and merchant and writes an audit row with principal, scope and result. Tokens can be revoked; requests are rate-limited per principal and login attempts are limited.

**The identity chain, with where each step lives.** The V4 feedback described the missing chain as
`credential → authenticated principal → authorization → merchant`, with every tool call authorized. Since v0.7.0:

```text
credential               POST /v1/auth/token (password grant for demo users, client_credentials for the ticketing service)
    ↓
authenticated principal  RS256 JWT from the assistant's own issuer; verified on every request (api/identity.py: Identity.verify,
                         principal_from_claims); roles merchant | operator | service | demo | admin with scopes; revocation; rate limit
    ↓
authorization            each tool call checks the required scope (tools/registry.py: access_error); a body user_id that differs
                         from the token gets 403 identity_mismatch (api/app.py); operator endpoints need handoff:operate
    ↓
merchant                 the customer of every tool comes from the token (ToolEnv.customer); no tool schema has a customer field;
                         another merchant's resource returns FORBIDDEN_RESOURCE with no data
    ↓
audit row                every tool call writes principal, tool, scope, result and touched resource (tools/registry.py: write_audit);
                         a call that cannot be audited is not reported as done
```

An external OIDC issuer is a configuration change (`JWT_JWKS_URL`); the demo users and secrets in `.env.example` are
fictitious and no private key is versioned (`JWT_PRIVATE_KEY_PATH` empty: the key is generated at startup).

- **Pause and resume** ([ADR 0018](docs/architecture/decisions/0018-interrupcao-retomada-webhooks.md)). When the Escalation agent opens a case, the end-of-turn state goes to a review graph checkpointed in SQLite that stops at `human_review` with LangGraph `interrupt()`; the attendance path without a handoff reads no checkpoint. An operator's `approve`, `reply` or `reject` resumes it with `Command(resume)`: approve and reply go to Personality, reject re-runs Support once with the operator's instruction. The reply is a turn marked `via=operator`, delivered on the merchant's next message (route `human_reply`, no model call), in `GET /v1/conversations/{id}` and by webhook. It survives an API restart.
- **Queue.** States `open → claimed → answered | rejected → closed`; claim and actions are idempotent (`idempotency_key`), a second resume gets `409 already_resumed`, another operator's claim `409 claimed_by_other`. API (`GET /v1/handoffs`, `POST /v1/handoffs/{id}/claim`, `POST /v1/handoffs/{id}/actions`), CLI (`merchant-assistant operator list|show|act`) and the ticketing service go through the same service.
- **Ticketing service.** A separate service in Compose (own database, published on `127.0.0.1:8002`), with the ticket cycle `new → open → pending → solved` and an operator screen in the web project. It talks to the assistant only through signed webhooks in both directions (HMAC-SHA256 over `timestamp.body`, 300 s window, one secret per direction) and a `client_credentials` token. Incoming events are idempotent by id and a repeated refused event gets the original `409`/`422` back.
- **Durable delivery.** Each outgoing event and destination is written to an outbox (migration 0010) in the same transaction as the change it reports; a dispatcher delivers it with up to three attempts in total, recorded and visible in the case, and recovers pending deliveries when the API starts.

### Demonstration API (v0.6.0)

These additive `/v1` routes back the Streamlit interface:

| Route | Role | Behaviour |
| --- | --- | --- |
| `GET /v1/scenarios` | demo, admin | Short catalog of labeled synthetic scenarios (`data/scenarios/catalog.json`) |
| `POST /v1/messages` + `scenario_id` | demo, admin | Optional; validated against the catalog (message must match) and stored in the run; demo sessions limited by `DEMO_SESSION_MESSAGE_LIMIT` (`429 demo_message_limit_reached`) |
| `GET /v1/runs/{id}` | owner | Adds `steps` (with retrieved passages), `route`, `prompts_used`, deterministic `checks` (scenario labels or label-independent, critical failures listed one by one) and `evaluations` |
| `POST /v1/runs/{id}/evaluations/estimate` | owner | Price of one `judge` call over the persisted reply; no paid call |
| `POST /v1/runs/{id}/evaluations` | owner | Confirmed estimate required; reserves, grades the stored reply with the fixed evaluator and records method, rubric, evaluator, evidence and a separate cost; same configuration returns the existing record unless `repeat=true` |
| `POST /v1/comparisons/estimate` | demo, admin | 2–3 published profiles × up to 3 scenarios × up to 2 repetitions: cells, reused recorded runs, new executions, fixed factors, exploratory flag and an upper-bound estimate |
| `POST /v1/comparisons` | demo, admin | Confirmed estimate required; `202` and execution in a thread of the API process with one knowledge-base version, domain effects in a temporary copy of the synthetic database and traces/snapshots marked `purpose=comparison` |
| `GET /v1/comparisons/{id}` | owner | State, configuration, cells, failures and aggregates for the cost × quality and cost-by-agent/model charts |

Migration 0008 (reversible) adds `run_evaluations`, `comparisons` and `api_sessions.message_count`. Legacy `POST /messages`, MCP and the existing `/v1` behaviour are unchanged. In Compose the API is published only on `127.0.0.1:8000`.

### Streamlit interface

The separate `ai-getnet-case-web` sibling project (see its README) is a Streamlit client of the versioned `/v1` API and, for operators, of the ticketing service. It never reads backend files or receives provider keys. Use **Simulado** or **Gravado** for fixture-only behavior, or select **Real (API)** and sign in with a user and password of that backend: merchants and demo see Attendance and Results, operators see Ticketing, admin also sees Administration. The client reuses one HTTP client per Streamlit session, revokes the token and clears the previous user's state at logout, and sends requests only after explicit actions.

```powershell
# In the web project, with its own Python environment:
python -m pip install -e ".[test]"
$env:BACKEND_API_URL = "http://localhost:8000"
streamlit run app.py
```

For a no-key local HTTP exercise, use the synthetic backend harness with a new runtime directory under `.pytest_cache`, then point `BACKEND_API_URL` to that loopback server. The harness has programmed providers, a fresh isolated SQLite/Qdrant runtime, and no provider credentials; it is not a production configuration. Detailed commands are in the [developer passage](docs/evidence/v040-developer-r1.md).

### MCP server

The Customer Support tools are also available over [MCP](https://modelcontextprotocol.io) (stdio), on top of the
same domain functions, validation, customer isolation, audit log and structured errors. The merchant comes from the
token in `MERCHANT_ASSISTANT_TOKEN`, checked again on every call, never from a tool argument.

```bash
export MERCHANT_ASSISTANT_TOKEN=$(merchant-assistant auth token)   # cliente1988 against a running API
merchant-assistant mcp                            # stdio server (for an MCP client such as Claude Desktop)
merchant-assistant mcp-demo                       # starts the server as a subprocess and calls it as a client
```

The demo lists the support tools, reads yesterday's receivables and recent declines, and shows that a receivable of
another merchant returns `is_error=true` with `FORBIDDEN_RESOURCE`. Example client configuration:

```json
{"mcpServers": {"getnet-merchant-support": {"command": "merchant-assistant", "args": ["mcp"], "env": {"MERCHANT_ASSISTANT_TOKEN": "<token>"}}}}
```

## Limitations and next steps

- The ticketing service is the project's own (Zendesk/Freshdesk-style contract); a commercial ticketing system would be a mapping and configuration change. A delivery that exhausts its three attempts, or that the receiver refuses, has no automatic or manual resend yet and holds the later events of the same case and destination. If the API dies in the middle of the turn that opens a case, the case is completed when the merchant sends the same message again; otherwise it stays open without a ticket. The ticket id appears on the case after the first operator event from the ticketing; it is empty while the ticket is still in reception. The cross-process locks were exercised on Windows only.
- Business journeys are measured by a literal rubric that works as a deterministic floor (route, status, tools, values, forbidden assertions): real runs bring correct paraphrases it refuses (v0.8.0 passed 13/13, 12/13 and 12/13; the judge 13/13 each), and a wrong paraphrase outside the registered list can pass it. Content is checked by the calibrated judge. The handoff sentence and the journey labels were fixed in v0.8.0. The judge does not see the web search text, so `general_web` answers score lower and vary more, and the calibration shows it misses generic claims that a human flags. The human calibration of the judge is [done](docs/evidence/v080-calibracao.md) (24 answers: the judge is the stricter rater, and the two never flag the same answer as unsupported), and the v0.8.0 holdout has been seen once.
- Snapshots fix the site content of 2026-10-26; JavaScript-rendered pages need a browser capture to refresh.
- Troubleshooting steps are identified by the model's short label; informational answers wait for the merchant's
  confirmation before a case is resolved.
- The functional scope was reopened after the feedback ([ADR 0016](docs/architecture/decisions/0016-reabertura-pos-feedback.md)); there is still no Evaluation Agent, improvement-proposal workflow or experiment platform. Model evaluation is a judge over persisted replies, calibrated against a human sample, not human review.
- Profile comparisons are small and run in a thread of the API process. Since v0.10.0 a restart marks a running comparison `interrupted` (finished cells kept) and `POST /v1/comparisons/{id}/resume` finishes it; the thread registry is per process, so the API must run with a single worker (as the compose does), and a narrow ABA race in the resume claim is documented in ADR 0022. The comparison estimate is an upper bound (request cost cap per new execution).
- The Results area lists the runs of the current browser session; there is no general run listing.
- Public sharing depends on the owner's router, firewall and the absence of CGNAT; a tunnel is a documented alternative.
- Sale cancellation is read-only: the assistant reports the status of an existing request; asking it to cancel a
  new sale is not covered.
- Identity uses the assistant's own issuer and synthetic demo users; there is no authorization-code flow, refresh token or external OIDC provider running in the demo.

### Next steps

In order of value for the open remarks; written down so the direction is clear even where it ships later.

1. **Judge: model and rubric together.** `judge.v4` fixed the rubric but the default judge does not apply it; measure `claude-sonnet-5-5` under v4 against the same 24 human ratings as a cost middle ground, and record the web search text so the judge sees it.
2. **Rolling summary** for conversations longer than the ten-message window.
3. **Journey rubric.** Keep the deterministic checks for what is binary (route, status, tools, values, sources, forbidden assertions) and let the judge decide content; add a rubric line for generic claims without a source; record the web search text so the judge sees it.
4. **Calibration tooling.** `eval-calibrate --sample` must carry the full evidence the judge saw (the v0.8.0 CSV truncated it; the full text was supplied in a companion file).
5. **Reranker decision.** Add a no-model control at the same fusion depth (`hybrid@36`) so the reranker's own gain can be measured, then decide `RERANK` by the rule; add a score floor for hits found only by BM25.
6. **Operation.** Optional OTLP export and a dashboard over `/metrics`; a multi-worker-safe comparison registry (today the API runs with one worker).
7. **Optional Anthropic agent provider** with a per-provider ledger and a paired comparison against the OpenAI profile (specification drafted, not merged; the judge adapter of v0.9.0 is the first piece).
8. **Production.** External access test through a tunnel; mapping to a commercial ticketing system; resend of exhausted webhook deliveries.

## Repository layout

```text
src/merchant_assistant/
  api/            FastAPI app and the public contract
  orchestration/  graph, typed state, run context (limits, metering), budget guard
  agents/         router, knowledge, support, escalation, personality
  guardrails/     input masking/injection, output evidence check
  rag/            collection, documents, chunking, embeddings, index
  tools/          domain tools, registry and allowlists
  data/           clock, SQLite schema, seed, status glossary
  llm/            provider interface, OpenAI client, scripted model, prompts, prices
  evaluation/     retrieval and end-to-end evaluation, scripted policy
  observability/  JSON logging, traces
prompts/          versioned prompts (router, knowledge_*, support, escalation, personality, judge)
data/             sources, snapshots, demo corpus (runtime/ is generated and ignored)
tests/            unit, integration, labeled scenarios
docs/             specification, plan, tasks, ADRs, evidence (Portuguese, spec-driven workflow)
```

The project follows a spec-driven workflow from the ai-dev-template (agent roles, skills and validation scripts in
`skills/`, `docs/wiki/agents/` and `tools/scripts/`). The specification is
[docs/specs/assistente-multiagente-lojista.md](docs/specs/assistente-multiagente-lojista.md).

All merchant data in this repository is synthetic. Public content was collected from Getnet's website for retrieval
and is cited with its URL.
