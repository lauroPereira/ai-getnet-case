# Tarefa: comparação pequena de perfis com dois gráficos

## Objetivo

Comparar dois ou três perfis publicados sobre poucos cenários explícitos, com dois gráficos e uma tabela rastreáveis até as execuções.

## Especificação relacionada

[Spec v0.6.0, bloco C](../specs/fechamento-v060.md), RF-78, CA-48 e [plano](../specs/fechamento-v060-plano.md) (decisões 4 e 5).

## Pré-condições

Tarefa 55 concluída (cenários, verificações e avaliação). Sem chamada paga.

## Arquivos prováveis

Backend: `api/v1.py`, `data/migrations.py` (`comparisons`), orquestração da comparação, testes. Web: `app.py`, cliente, snapshot OpenAPI, fixtures e testes.

## Passos

1. Tabela `comparisons` na migração 0008.
2. `POST /v1/comparisons/estimate`: células, reusos de execuções compatíveis, novas execuções, fatores fixos, marcação exploratória quando houver mais de uma mudança entre perfis e estimativa.
3. `POST /v1/comparisons` com estimativa confirmada: execução fora da requisição no processo da API, uma versão da base para toda a comparação, efeitos de domínio numa cópia temporária do banco sintético, traces e snapshots marcados com `purpose=comparison`; negação de orçamento interrompe o restante e fica registrada.
4. `GET /v1/comparisons/{id}`: estado, configuração, células, falhas e agregados.
5. Resultados: gráfico custo × qualidade por perfil (duração média e tamanho da amostra), gráfico de custo por agente/modelo com seleção que abre as execuções, tabela cenário/perfil/resultado/duração/custo; Router-only em seção própria; "não avaliado" em vez de zero.
6. Testes de limites, reuso, falha parcial, isolamento (contagens do domínio original inalteradas) e ausência de POST em rerun ou seleção de gráfico.

## Critérios de conclusão

- [ ] Nenhuma conversa, caso, tentativa ou encaminhamento criado no atendimento original.
- [ ] Configurações, versões, repetições, amostra e falhas registradas e exibidas.
- [ ] Qualidade só com os mesmos rótulos e rubrica; sem nota fictícia.
- [ ] Validação estrita backend e web com código 0; nenhuma chamada paga.

## Validação

- Tabela `comparisons` (migração 0008); `POST /v1/comparisons/estimate`, `POST /v1/comparisons` (202, thread do processo da API) e `GET /v1/comparisons/{id}`.
- `test_comparison_limits_and_estimate_have_no_side_effects` (limites 2–3/3/2, 18 células, exploratória, estimativa sem chamada nem linha gravada), `test_comparison_runs_outside_the_request_isolated_and_traceable` (contagens de conversas, mensagens, tentativas, encaminhamentos, casos e auditoria inalteradas; `purpose=comparison` no trace e no snapshot; uma versão da base; reuso integral como gravadas na segunda comparação), `test_model_quality_appears_only_when_every_run_of_a_profile_was_judged`, `test_budget_denial_stops_the_remaining_cells_and_is_recorded`, `test_comparison_requires_confirmation_and_fresh_estimate_and_lost_threads_fail`, `test_demo_comparison_new_executions_count_against_the_session_limit`.
- Interface: `test_comparison_estimate_confirm_run_refresh_and_bar_selection` (dois gráficos Vega-Lite, tabela com "não avaliado" e falha da célula, seleção de barra sem chamada, abrir execuções só por GET) e `test_changed_comparison_selection_invalidates_the_estimate`.

Validação estrita backend (`PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v060-dev-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`): **326 passed**, Ruff "All checks passed!", estrutura e skills válidas, código 0. Web (`.venv-v040/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`): **30 passed**, Ruff sem achados, código 0. Nenhuma chamada paga, chave de provedor ou build Docker. Passagem: [v060-developer.md](../evidence/v060-developer.md).

## Status

```text
concluída
```

Revisada (Reviewer, rodadas 1–5) e validada no QA real da v0.6.0 (rodada 2, candidato r5); ver [resultado](../evidence/v060-resultado.md).
