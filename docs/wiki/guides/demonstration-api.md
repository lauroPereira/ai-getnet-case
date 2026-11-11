# Demonstration API

These `/v1` routes back the Streamlit interface: labeled scenarios, on-demand evaluation of a stored reply and a
small profile comparison, with every paid action behind a confirmed estimate. Each run keeps its steps, checks
and evaluations, so a stored reply is inspected and graded without running the attendance again. The full
contract is in [docs/contracts/api-v1.md](../../contracts/api-v1.md); the summary is in the
[README](../../../README.md#demonstration-api).

## Routes

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
| `POST /v1/comparisons/{id}/resume` | owner | A comparison whose process stopped is `interrupted`, with its finished cells kept; resume runs the missing cells ([operation test](../../evidence/v0100-qa-ops-r1.md): stopped after 1 of 6 cells, resumed 5, `completed`, one ledger line per cell) |

Migration 0008 (reversible) adds `run_evaluations`, `comparisons` and `api_sessions.message_count`. `POST /messages`,
MCP and the existing `/v1` routes keep their behaviour.
