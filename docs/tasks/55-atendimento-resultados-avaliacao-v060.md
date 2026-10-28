# Tarefa: Atendimento, Resultados e avaliação sob demanda

## Objetivo

Reorganizar a interface em Atendimento, Resultados e Administração, com catálogo de cenários e avaliação sob demanda de execuções persistidas, sem novo agente.

## Especificação relacionada

[Spec v0.6.0, blocos A e B](../specs/fechamento-v060.md), RF-76, RF-77, CA-47, CA-50 e [plano](../specs/fechamento-v060-plano.md) (decisões 1, 2, 3 e 7).

## Pré-condições

Tarefa 54 concluída. Contratos e migração 0008 aprovados. Sem chamada paga.

## Arquivos prováveis

Backend: `data/scenarios/`, `api/v1.py`, `evaluation/runner.py`, `orchestration/graph.py`, `data/migrations.py`, testes. Web: `app.py`, `src/getnet_web/api.py`, cliente gerado, `openapi-v1.json`, fixtures e testes.

## Passos

1. Catálogo curto de cenários rotulados em `data/scenarios/` e `GET /v1/scenarios`; `scenario_id` opcional em `POST /v1/messages`, gravado no snapshot.
2. Migração 0008 (`run_evaluations`, e o que o limite por sessão exigir, se ainda não feito) reversível.
3. `GET /v1/runs/{id}` acrescenta verificações determinísticas aplicáveis e avaliações registradas.
4. `POST /v1/runs/{id}/evaluations/estimate` e `POST /v1/runs/{id}/evaluations` com o avaliador e a rubrica existentes, estimativa confirmada, reserva, custo separado, idempotência e falhas críticas individuais.
5. Interface em três abas; Administração só para `admin`; perfis Referência, Híbrido e Ajustado publicados para a demonstração; mensagens de erro com ação de recuperação; rótulos real, simulado e gravado preservados.
6. Resultados mostram etapas, ferramentas, modelo efetivo por agente, versões, tokens, duração, custo, fontes e trechos recuperados, verificações (com origem) e avaliações ou "não avaliado".
7. Regenerar cliente e snapshot OpenAPI; testes `AppTest` e de API.

## Critérios de conclusão

- [ ] Nenhum POST, inferência ou publicação em rerun, troca de aba ou navegação.
- [ ] Avaliação de execução persistida não repete o atendimento; custo de avaliação separado; repetição só explícita.
- [ ] Demo não vê nem consegue usar Administração (backend `403`).
- [ ] Migração 0008 sobe e desce em banco sintético; validação estrita backend e web com código 0.

## Validação

- Catálogo `data/scenarios/catalog.json` (8 cenários, um por jornada essencial + D), `GET /v1/scenarios`, `scenario_id` validado e gravado no snapshot: `test_scenario_catalog_requires_a_session_and_lists_labeled_scenarios`, `test_scenario_id_is_validated_and_recorded_in_the_run`.
- `GET /v1/runs/{id}` com etapas, trechos, verificações e avaliações: `test_free_message_only_gets_label_independent_checks`, `test_persisted_checks_list_critical_failures_individually`.
- Avaliação sob demanda: `test_evaluation_grades_the_persisted_reply_once_and_repeats_only_on_request` (uma chamada `judge`, atendimento não repetido, reuso e `repeat=true`, ledger `eval:<id>`), `test_evaluation_requires_confirmation_fresh_estimate_ownership_and_budget`, `test_unknown_evaluator_price_blocks_the_estimate`, `test_failed_evaluation_is_recorded_without_inventing_scores`, `test_evaluation_of_a_run_stored_before_v060_uses_the_conversation_text`.
- Migração 0007 → 0008 → 0007 → 0008 em SQLite sintético: `test_migration_0008_round_trip_on_a_synthetic_database` (sessões e snapshots preservados) e testes de migração existentes atualizados.
- Interface: `test_demo_sees_attendance_and_results_and_admin_also_sees_administration`, `test_catalog_scenario_is_sent_once_with_its_id_and_reruns_do_not_post`, `test_results_show_checks_unevaluated_and_evaluation_needs_explicit_confirmation`, `test_backend_errors_explain_the_recovery_action`; testes existentes de recuperação, comparação de Routers e KB continuam passando. Cliente e `openapi-v1.json` regenerados (31 caminhos, 28 operações).
- Bancos novos publicam Referência, Híbrido e Ajustado; bancos anteriores mantêm o Ajustado como rascunho até a publicação pelo admin (documentado no guia).

Validação estrita backend (`PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v060-dev-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`): **326 passed**, Ruff "All checks passed!", estrutura e skills válidas, código 0. Web (`.venv-v040/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`): **30 passed**, Ruff sem achados, código 0. Nenhuma chamada paga, chave de provedor ou build Docker. Passagem: [v060-developer.md](../evidence/v060-developer.md).

## Status

```text
concluída
```

Revisada (Reviewer, rodadas 1–5) e validada no QA real da v0.6.0 (rodada 2, candidato r5); ver [resultado](../evidence/v060-resultado.md).
