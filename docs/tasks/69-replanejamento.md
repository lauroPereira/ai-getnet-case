# Tarefa: nó de replanejamento com orçamento de saltos

## Objetivo

Depois de `knowledge` e de `support`, um nó `replan` observa o resultado e decide o próximo passo (concluir, outro especialista, web, escalar ou esclarecer), por regra quando o caso é claro e por `replan.v1` só na ambiguidade, com orçamento de saltos e o motivo no trace.

## Especificação relacionada

[Spec v0.8.0](../specs/orquestracao-avaliacao-v080.md) — D1 a D8; [spec 0.2](../specs/evolucao-pos-feedback.md) RF-86 a RF-88, CA-49, UC-23; [plano](../specs/evolucao-pos-feedback-plano.md) decisões técnicas 9 a 11.

## Pré-condições

Spec v0.8.0 aprovada pelo responsável; v0.7.0 na `main`; branch `codex/v0.8.0-replan` aberta a partir da `main` atualizada no checkout principal (Time A). Não abrir `tests/scenarios/holdout_v080*`.

## Arquivos prováveis

`orchestration/graph.py` (nó e arestas do grafo de atendimento), `orchestration/state.py` (resumo observado, saltos), `orchestration/run.py` e `config.py` (`MAX_PLAN_HOPS`), `agents/replanner.py` (novo: regras e chamada), `prompts/replan.v1.md` (novo), `evaluation/scripted_policy.py` (política programada), `data/scenarios/catalog.json`, `tests/scenarios/replan.jsonl` (novo), testes.

## Passos

1. Resumo observado por especialista: `evidence_sufficient`, `missing`, `needs_selection`, ferramentas com falha, `escalate`, saltos feitos, especialistas já usados e rota original.
2. Regras da D4 numa função pura, cada uma com nome; `replan.v1` (saída estruturada `next`, `reason`, `review`; esforço `none`, ≤ 80 tokens) só quando nenhuma regra se aplica ou duas se contradizem.
3. Nó `replan` no lugar de `_after_knowledge` e `_after_support`; D5 (cada especialista uma vez) e D6 (`MAX_PLAN_HOPS=3`, no limite `finish` com a lacuna declarada). Grafo de retomada inalterado (D3).
4. Passo de trace `replan` com os campos da D7; `GET /v1/runs/{id}` o mostra sem mudar o contrato existente. `route` continua sendo o plano inicial do Router; o caminho executado sai em `executed_path` (D16), no trace e no runner.
5. Os quatro cenários do RF-88 em `tests/scenarios/replan.jsonl` e no catálogo (`SC-REPLAN-*`), com a política programada; regressão dos 40 casos e das 4 conversas.
6. Proposta da ADR 0019 (replanejamento) com o desenho, as regras e o plano B.

## Critérios de conclusão

- [ ] Cada regra tem teste; o modelo só é chamado na ambiguidade (teste conta as chamadas).
- [ ] Laço forçado (especialistas que nunca resolvem) termina em ≤ 3 saltos sem repetir especialista.
- [ ] Os quatro cenários passam com modelo programado; o trace mostra `next`, `reason`, `review`, `hops` e `origin`.
- [ ] Pergunta simples não ganha chamada a mais (ledger e trace).
- [ ] 40 casos e 4 conversas sem piora contra a v0.7.0 no eval programado, salvo diferença justificada caso a caso; `route_ok` medido pelo plano inicial e `executed_path` registrado (D16).
- [ ] Trava da v0.7.0 (D18): `tests/integration/test_v070_story.py`, `test_v070_webhooks.py`, `test_v070_resume*.py` e `test_v070_ticketing_integration.py` verdes sem alteração; o nó `escalation` e o grafo de retomada não mudam.
- [ ] Suíte estrita com código 0; nenhuma chamada paga.

## Validação

Developer (Time A), 2026-11-04, branch `codex/v0.8.0-replan`, base `5134eff` (68b em `c1dd2d5`; código em `686d545`; testes e cenários em `1ba296f`). Scripted, sem chamada paga e sem rede. Passagem completa em [v080-developer.md](../evidence/v080-developer.md).

| Critério | Prova |
| --- | --- |
| Cada regra tem teste; o modelo só é chamado na ambiguidade (conta as chamadas) | `tests/unit/test_replanner_rules.py` (31): uma regra por caso (`complete`, `plan_pending`, `evidence_insufficient_web`, `account_dependent_question`, `procedure_gap`, `tool_failure_no_alternative`, `support_asked_for_human`, `selection_pending`, `specialist_failed`, `gap_declared`), contradições, nenhuma regra, guardas. `test_v080_replan.py::test_no_clear_case_of_the_forty_or_the_four_scenarios_asks_the_model`: os 40 casos, 0 chamadas ao agente `replan` (os 4 cenários afirmam o mesmo); `test_the_model_is_called_only_when_rules_disagree_or_none_applies`: 2 chamadas (ledger e `llm.calls`), `max_output_tokens <= 80`, esforço `none`; `test_simple_question_is_closed_by_rule_without_an_extra_call`: ledger `[router, knowledge, personality]` |
| Laço forçado termina em ≤ 3 saltos sem repetir especialista | `test_forced_loop_specialists_that_never_resolve...` (Support vazio, Knowledge insuficiente, web fora: `support → knowledge → web → finish`, 2 saltos), `test_forced_loop_a_planner_that_always_wants_more...` (modelo pede `web`, `support`, `escalate`: 3 saltos, 3 especialistas distintos), `test_a_specialist_the_planner_asks_for_twice_is_refused[knowledge\|web\|support]`, `test_the_budget_of_changes_of_plan_is_a_setting...[0\|1]`, `test_the_requests_call_limit_still_holds`, `test_a_failing_node_never_loops_the_replanner` |
| Os quatro cenários passam com modelo programado; o trace mostra `next`, `reason`, `review`, `hops`, `origin` | `test_the_four_scenarios_of_rf88_pass...[REPLAN-WEB\|PROCEDURE\|TOOL-DOWN\|ACCOUNT]` (11 checagens do runner por cenário, `agents` na ordem executada, decisões com origem), `test_the_run_endpoint_shows_each_decision_with_its_origin` (`GET /v1/runs/{id}`, cenário do catálogo `SC-REPLAN-WEB` 11/11, campos novos só no passo `replan`), `test_catalog_scenarios_carry_the_message_and_labels_of_replan_jsonl` |
| Pergunta simples não ganha chamada a mais | ledger e `trace["model_calls"] == 3` na pergunta simples; nos 40 casos, total de chamadas 123 na `main` e 123 na branch |
| 40 casos e 4 conversas sem piora contra a `main` | `eval` programado dos mesmos 40 casos + `followup.jsonl` numa cópia por `git archive main` (`bee6ab5`) e na branch (roteiro fora do repositório, sem `.env`): **25/40 e 4/4 nas duas**; os 40 casos e as 4 conversas são **idênticos campo a campo** (rota, status, `agents`, resposta, fontes, ferramentas, checagens, chamadas), depois de normalizar o sufixo aleatório do protocolo `HO-AAAAMMDD-XXXXXX`. Nenhuma diferença a justificar. `route_ok` usa a rota inicial (D16); `agents` traz o caminho executado |
| Trava da v0.7.0 (D18) sem alteração | `test_v070_story`, `test_v070_webhooks`, `test_v070_resume`, `test_v070_resume_r2`, `test_v070_ticketing_integration`, `test_v070_closing`: **94 passed**, arquivos sem alteração (`git diff` vazio). `test_the_review_graph_that_resumes_a_handed_off_case_has_no_replanning`: o grafo de retomada não tem `replan`, `web`, `knowledge` nem `escalation`; `escalation.py` e `build_review_graph` intocados |
| Mutações | numa cópia fora do repositório, 9 mutantes do nó (sem D5, sem orçamento, sem `plan_pending`, modelo sempre, sem limites da requisição, `escalate` sem contar, `complete` ignorando o Support, sem lacuna declarada, web com índice fora) morrem nos testes novos |

```text
pytest tests/unit tests/integration/test_v080_replan.py tests/integration/test_v080_ticket_id.py tests/integration/test_use_cases.py tests/integration/test_evaluation_runner.py tests/integration/test_v060_api.py   (grupo novo e diretamente afetado)  -> 164 passed
pytest 6 arquivos da trava v0.7.0                                                                                                                                         -> 94 passed
pytest tests/unit                                                                                                                                                         -> 278 passed (inclui os 31 novos)
pytest os 14 demais arquivos de tests/integration                                                                                                                         -> 199 passed
ruff check src tests                                                                                                                                                      -> All checks passed
```

Todos os arquivos de `tests/unit` e `tests/integration` rodaram, em grupos, um pytest por vez, cada um com basetemp novo (`.pytest_cache/t69-dev-final-*`). **Não rodei `tools/scripts/lint_and_tests.py --strict`** (fica com o Supervisor). Um teste existente mudou: `test_v060_api.py::test_scenario_catalog_requires_a_session...` esperava 10 cenários no catálogo e agora espera 14 (os 4 `SC-REPLAN-*`, exigidos pela tarefa).

Não verificado aqui: modelos reais (os cenários com `gpt-6-luna` e a taxa de `origin=model` são da campanha `v080-qa`); o cenário `REPLAN-TOOL-DOWN` precisa do serviço de preços fora do ar (parar o `mocks`).

## Status

```text
feito pelo Developer em 2026-11-04; aguarda revisão e QA
```
