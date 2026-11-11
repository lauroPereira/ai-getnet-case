# Configuration reference

Every setting is an environment variable (or a line in `.env`), and the defaults run the full system with a
single OpenAI key while capping spending at US$1.00 per installation and US$0.05 per request. This reference
lists each variable with its default and what it controls; the summary is in the
[README](../../../README.md#configuration).

## Variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `OPENAI_API_KEY` | — | Required for real calls (agents, embeddings, web search) |
| `AGENT_MODEL` | `gpt-6-luna` | Default model for every agent; the `/v1` model profiles can set another model per agent |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | RAG embeddings |
| `QDRANT_URL` | empty (embedded store) | Compose sets `http://qdrant:6333` |
| `BUDGET_RUNTIME_DIR` | `data/runtime` locally, `/app/runtime` in Docker | Persistent budget ledgers for the `eval` campaigns; keep it pointed at the project budget volume when `RUNTIME_DIR` is isolated for an evaluation run. The API and `bootstrap` write their ledger under `RUNTIME_DIR` |
| `MOCKS_URL` | `http://mocks:8001` | Internal synthetic pricing and charge service; Compose only |
| `BUDGET_LIMIT_USD` | `1.00` | Spending limit for paid calls in this installation's ledger: default US$1.00, maximum US$5.00 per ledger. The first limit recorded with a ledger stays its ceiling; an evaluation campaign carries its own cap |
| `MAX_REQUEST_COST_USD` | `0.05` | Cap per request |
| `MAX_MODEL_CALLS`, `MAX_TOOL_CALLS`, `MAX_REQUEST_SECONDS` | `8`, `8`, `90` | Per-request limits |
| `WEB_SEARCH_MAX_CALLS` | `1` | Searches per general question |
| `REPLAN` | `on` | `off` runs the fixed edges of v0.7.0, without the `replan` and web-search steps (the ablation measured by `eval --replan off` and `eval-compare`) |
| `DEMO_MODE` | `false` in code; `true` in `.env.example` and in compose | Enables `GET /traces/{id}` (token required; merchants see only their own) |
| `TIMEZONE` | `America/Sao_Paulo` | Used to resolve "yesterday", "today" |
| `DEMO_SESSION_MESSAGE_LIMIT` | `20` | Paid actions one demo session may start: messages, new comparison executions, Router comparisons and AI evaluations; refusals and skipped comparison cells without a model call do not count (they are given back); enforced by the backend |
| `EVALUATOR_PROVIDER`, `EVALUATOR_MODEL` | `openai`, `gpt-6-luna` | Fixed on-demand evaluator, independent of the evaluated profile and recorded with every evaluation |
| `JUDGE_PROVIDER`, `JUDGE_MODEL` | `deepseek`, `deepseek-flash` | Independent judge for `eval --judge`; the default uses `judge.v5`, requires `DEEPSEEK_API_KEY` and must differ from the agent model |
| `RERANK` | `on` | Reorders the first 12 hybrid retrieval candidates with one metered model call; set `off` to disable |
| `DEMO_USER_PASSWORDS` | demonstration values in `.env.example` | `user:password` pairs of the synthetic users (`cliente1988`, `cliente_demo_002`, operators `op_ana`, `op_bruno`); stored as PBKDF2 hashes |
| `API_DEMO_PASSWORD`, `API_ADMIN_PASSWORD` | empty (off) | Passwords of the `demo` and `admin` users of the `/v1` interface |
| `JWT_ISSUER`, `JWT_PRIVATE_KEY_PATH`, `JWT_JWKS_URL` | own issuer, key generated in the runtime | Token issuer; `JWT_JWKS_URL` switches verification to an external OIDC issuer |
| `OAUTH_REDIRECT_URIS` | the interface on this host (`http://localhost:8501/`, `http://127.0.0.1:8501/`) | Registered redirect URIs of the public clients for the sign-in by redirect (`<client_id>=<uri>`, exact match, https or http on the loopback); empty turns it off |
| `STREAMLIT_UPSTREAM` | `host.docker.internal:8501` | Where the proxy of `docker compose --profile tunnel up` finds the interface; see [Open the demonstration through a tunnel](interface-and-tunnel.md#open-the-demonstration-through-a-tunnel) |
| `OIDC_ISSUERS` | empty (own issuer only) | External OIDC issuers accepted next to the own issuer, with their `groups` (or another claim named by `groups_claim`) mapped to a role; `docker compose --profile oidc up` starts Dex with synthetic users ([Identity and authorization](../../../README.md#identity-and-authorization)). Use `OIDC_ISSUERS` for a standard OIDC provider; use `JWT_JWKS_URL` to replace the own issuer by one that signs tokens in the assistant's format (`role`, `scope`, `customer_id`) |
| `RATE_LIMIT_PER_MINUTE` | `30` | Requests per principal |
| `API_WORKERS` | `2` (compose) | API worker processes; see [Operations](../../../README.md#operations) |
| `TICKETING_WEBHOOK_URL`, `CONVERSATION_WEBHOOK_URL` and their secrets | Compose values | Signed webhooks to the ticketing service and to the merchant receiver; an empty URL turns a destination off; a URL without a secret is warned at startup |
| `WEBHOOK_MAX_ATTEMPTS`, `WEBHOOK_RETRY_WAITS_S`, `WEBHOOK_TIMEOUT_S` | `3`, `1,2`, `3` | Delivery attempts (total per event and destination, also across restarts) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_OPERATOR_CHAT_ID`, `TELEGRAM_WEBHOOK_URL`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_CLIENT_SECRET` | empty (off) | Operator on Telegram with `docker compose --profile telegram up`; see [Operator on Telegram](../../../README.md#operator-on-telegram) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | empty (off) | Base URL of an OTLP/HTTP collector for the request spans; see [Observability](../../../README.md#observability) |

## Provider keys and what the interface sees

- **Provider keys.** `DEEPSEEK_API_KEY` is required for the default `eval --judge` judge and optional for the
  DeepSeek model profiles (Hybrid: Router; Adjusted: Router and Support). `TYPESAFE_API_KEY` enables the alternative
  Router engine. `POST /messages` needs neither.
- **What the interface sees.** `GET /v1/profiles` reports which profiles and Router engines the configured keys
  allow, never a key value; the web app marks the others as unavailable and names the missing key. It signs in on
  the API's login page (authorization code with PKCE) and never receives a provider key.
