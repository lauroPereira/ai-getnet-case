# Tarefa: correções da revisão r1 da v0.6.0

## Objetivo

Corrigir, antes do QA real, os achados P3 do [parecer r1](../evidence/v060-reviewer.md) que afetam orçamento, integridade ou o aceite, sem ampliar o escopo.

## Especificação relacionada

[Spec v0.6.0](../specs/fechamento-v060.md), [plano](../specs/fechamento-v060-plano.md), tarefas 54–58 e o parecer r1.

## Pré-condições

- Decisões do responsável em 2026-10-27: corrigir antes do QA; o limite por sessão demo conta **toda ação paga** (mensagens, execuções novas de comparação, comparação de Routers e avaliação por IA), e recusa sem inferência (por exemplo `409`) não consome.
- P3-04 (`LOCK_BACKEND_URL` opcional, desligado por padrão) mantido por decisão do responsável; fora desta tarefa.
- Mesmo Developer; sem chamada paga, commit ou push.

## Passos

1. P3-01: marcar comparação interrompida como `failed` só quando ainda estiver `running` (atualização condicional), sem sobrescrever resultado concluído.
2. P3-02: idempotência da avaliação sem corrida (restrição única ou reserva atômica); dois POST simultâneos com a mesma configuração resultam numa única chamada paga.
3. P3-03: limite demo aplicado a toda ação paga, conforme a decisão acima; recusa sem inferência não consome.
4. P3-05: Administração trata falha de transporte (timeout) no build e no teste de candidata sem exceção do Streamlit e sem permitir repetir a ação paga às cegas; o estado é consultado por GET. README do web coerente.
5. P3-06: comparação reaproveita só execuções independentes (sem histórico de conversa).
6. P3-07: células com falha e pontos do gráfico custo × qualidade abrem as execuções correspondentes (CA-48).
7. P3-08: catálogo cobre habilitação de bandeiras e cancelamento de venda, além das jornadas atuais.
8. P3-09: custo ausente não vira zero na agregação (aparece como desconhecido); testes de ativação da base durante a comparação, de reuso com outra versão da base e do caso negativo do bloco D.
9. P3-10: modo simulado não expõe papel admin quando a interface está compartilhada (`LOCK_BACKEND_URL` ligado).
10. Validação estrita backend e web com código 0; nova seção na passagem do Developer.

## Resíduos da revisão r2 (rodada 3)

[Reviewer rodada 2](../evidence/v060-reviewer.md): apto para QA com quatro P3. Mesmo escopo aprovado, antes do QA:

11. P3-R2-01: recusa sem inferência não consome o limite demo também em mensagem com orçamento negado e em células de comparação puladas (mudança da base, teto ou orçamento); código e documentação coerentes.
12. P3-R2-03: teste do consumo do limite no envio que usa a decisão da comparação de Routers.
13. P3-R2-04: interface nunca mostra custo desconhecido como número (avaliação em andamento; barras do gráfico 2 respeitam `cost_unknown`).
14. P3-R2-02: sem correção de código; a migração 0008 não foi publicada. Supervisor conferiu que `data/runtime/merchant.sqlite3` está no esquema 4 e não tem `run_evaluations`; o QA cria runtime novo a partir do candidato.

## Critérios de conclusão

- [ ] Cada item com teste que falharia antes e passa depois, ou justificativa registrada.
- [ ] Contratos aprovados, legado e MCP inalterados além do necessário a estes itens.
- [ ] Nenhuma chamada paga; validação estrita com código 0 nos dois repositórios.

## Validação

Developer, rodada 2 (2026-10-27). Testes novos (cada um falharia no candidato r1, pelo motivo indicado):

- **P3-01** — `tests/integration/test_v060_r2.py::test_reading_a_comparison_never_overwrites_a_final_state_written_concurrently`: a thread grava `completed` entre a leitura e a conferência (`_alive` simulado); o GET devolve e mantém `completed`. Antes, `_save` incondicional gravava `failed`/`interrupted`. Correção: `UPDATE … WHERE state='running'` e releitura da linha.
- **P3-02** — `test_simultaneous_evaluations_with_the_same_configuration_call_the_judge_once` (segunda requisição durante o `judge` bloqueado → `409 evaluation_running`, inclusive com `repeat=true`; uma única chamada `judge`) e `test_a_running_claim_left_by_a_stopped_process_expires`. Antes, as duas requisições chamavam o `judge`. Correção: linha `running` criada em `BEGIN IMMEDIATE` junto com a conferência; migração 0008 (ainda não publicada) aceita `running`; expira em 10 min.
- **P3-03** — `test_stale_router_comparison_does_not_consume_the_demo_limit`, `test_router_comparison_and_evaluation_count_as_paid_actions` (reuso da avaliação não conta; admin sem limite) e `test_budget_refusals_before_any_call_give_the_action_back`. Antes, o 409 consumia, e comparação de Routers e avaliação não contavam. Correção: consumo depois das validações (na mesma transação do consumo da comparação de Routers), contagem em `router/compare` e na avaliação, devolução quando o orçamento recusa antes da primeira chamada.
- **P3-05** — web `tests/test_v060_interface.py::test_kb_transport_failures_never_crash_and_never_allow_a_blind_repeat` (build, teste e ativação com `ReadTimeout`/`ConnectError`: sem exceção, aviso com "recarregue a página", estimativa e confirmações descartadas, nenhuma repetição). Antes, `ReadTimeout` virava exceção do Streamlit. README web atualizado.
- **P3-06** — `test_comparison_reuses_only_runs_without_conversation_history` (segunda mensagem da mesma conversa tem `history_turns=2` e não é reaproveitada). Antes, as duas eram reaproveitadas.
- **P3-07** — web `test_failed_cells_and_chart_points_open_their_runs_by_get` (célula com falha e ponto do perfil abrem as execuções por GET). Antes não havia acesso.
- **P3-08** — catálogo com 10 cenários; `test_scenario_catalog_requires_a_session_and_lists_labeled_scenarios` exige as jornadas de habilitação e cancelamento.
- **P3-09** — (a) `test_activation_during_a_comparison_does_not_change_its_knowledge_base_version` e `test_runs_recorded_on_another_knowledge_base_version_are_not_reused` (cobrem as mutações M7 e M11); (b) `tests/integration/test_v060_doc_effect.py::test_v2_does_not_offer_payment_link_when_the_contract_does_not_list_it` (lojista `cliente_demo_002`); (c) `test_aggregates_keep_unknown_cost_unknown_and_do_not_split_a_combined_agent_cost` e web `test_unknown_cost_is_shown_as_unknown_and_not_plotted_as_zero`. Antes, custo ausente virava 0 e o custo de um agente com dois modelos era duplicado.
- **P3-10** — web `test_shared_interface_offers_only_the_demo_simulated_role`.
- P3-04 fora do escopo (decisão do responsável).

Validação estrita backend: **337 passed**, Ruff "All checks passed!", estrutura e skills válidas, código 0. Web: **34 passed**, Ruff sem achados, código 0. Nenhuma chamada paga. Detalhes em [v060-developer.md](../evidence/v060-developer.md#rodada-2--2026-10-27).

Developer, rodada 3 (2026-10-27), resíduos da revisão r2:

- **P3-R2-01** — `tests/integration/test_v060_r2.py::test_message_refused_by_the_budget_before_any_model_call_does_not_consume`: com a reserva sempre negada, a mensagem volta `503` com zero chamadas e o contador fica em 0; com limite 1, a ação seguinte é atendida. No r2 o contador ia a 1. `test_comparison_cells_without_a_model_call_are_given_back`: só a 1ª célula chega ao modelo, as outras 3 são puladas por negação de orçamento e devolvidas; o contador termina em 1. No r2 ficava em 4. Correção: `messages_v1` devolve a ação quando o trace termina sem chamada ao modelo (`model_calls_made`), inclusive em `RunFailure` e nas exceções. Ao fim, `_run` devolve as células novas sem chamada, gravando `model_calls` por célula, seja a célula pulada por base alterada, teto ou orçamento, seja recusada antes da chamada.
- **P3-R2-03** — `test_using_the_router_decision_consumes_the_demo_limit`: com limite 2, comparar os Routers e usar a decisão esgotam o limite. Esse teste detecta a mutação R11.
- **P3-R2-04** — web `tests/test_v060_interface.py::test_unknown_costs_of_bars_and_running_evaluations_are_never_numbers`. Uma barra com `cost_unknown` sai do gráfico, recebe o rótulo "custo desconhecido" e continua selecionável. A avaliação em andamento mostra "custo da avaliação desconhecido". No r2 apareciam `US$ 0.002000` e `US$ 0.000000`.
- **P3-R2-02** — sem código: a 0008 não foi publicada e o QA cria runtime novo (conferência do Supervisor registrada no item 14).

Validação estrita backend: **340 passed**, Ruff "All checks passed!", código 0. Web: **35 passed**, Ruff sem achados, código 0. Nenhuma chamada paga. Detalhes em [v060-developer.md](../evidence/v060-developer.md#rodada-3--2026-10-27).

## Status

```text
concluída
```

Revisada (Reviewer, rodadas 1–5) e validada no QA real da v0.6.0 (rodada 2, candidato r5); ver [resultado](../evidence/v060-resultado.md).
