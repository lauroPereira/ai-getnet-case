# Tarefa: correções do QA r1 da v0.6.0

## Objetivo

Corrigir o defeito P1 do toggle JEV e os pontos pequenos que afetam a demonstração, encontrados no [QA r1](../evidence/v060-qa.md), mais o P3-R3-01 pendente da revisão.

## Especificação relacionada

[Spec v0.6.0](../specs/fechamento-v060.md) (A, B, C), CA-32, CA-33, CA-47, CA-48, [tarefa 60](60-correcoes-revisao-v060-r1.md) e o [parecer do Reviewer](../evidence/v060-reviewer.md) (P3-R3-01).

## Pré-condições

Mesmo Developer; sem chamada paga, commit ou push. Contratos aprovados inalterados além do necessário.

## Passos

1. **P1-QA-01:** com `router_mechanism=jev` em `POST /v1/messages`, o Router precisa ser executado pelo adaptador JEV (TypeSafe), não pelo LLM padrão nem pelo do perfil; snapshot, trace, ledger e interface devem registrar o mecanismo e o modelo efetivamente usados. Causa observada: `execute_run` exclui `router` de `agent_models` e o orquestrador só aplica `router_llm` aos nomes presentes nesse dicionário. Vale também para a comparação de perfis com Router JEV. Teste que comprove a chamada ao adaptador JEV e a ausência de chamada LLM do Router.
2. **P3-QA-02:** valores em reais (`R$ 80,00 … R$ 148,06`) não podem virar fórmula no Streamlit; o texto exibido é igual ao gravado.
3. **P3-QA-03:** depois de "Atualizar conversa", o estado do caso mostra a rota e o status da resposta recuperada.
4. **P3-R3-01:** a devolução do limite demo não pode falhar aberta; decidir pelas linhas do ledger do `request_id` ou pelo `model_calls` do contexto da execução, e não devolver quando a informação faltar.
5. Observações do QA, se pequenas: seletor de perfil começa em Referência; nomes dos perfis exibidos em português (Referência, Híbrido, Ajustado); teto do teste da candidata pré-preenchido com a estimativa; `/ready` mostra a coleção da versão ativa; rótulos do gráfico custo × qualidade sem sobreposição; CHANGELOG com 10 cenários.
6. Validação estrita backend e web com código 0; nova seção na passagem do Developer.

## Resíduos da revisão r4 (rodada 5)

[Reviewer rodada 4](../evidence/v060-reviewer.md): apto para QA com dois P3, corrigidos antes do QA focal:

7. P3-R4-01: todo texto exibido com valores em reais aparece literal, inclusive a "Pergunta pendente" e o comentário do avaliador por IA (hoje com `st.write`).
8. P3-R4-02: testes de falha aberta na devolução das células da comparação (decidir pelo trace; ledger ilegível), equivalentes aos da mensagem.

## Critérios de conclusão

- [ ] Toggle JEV executa o adaptador JEV de verdade no envio direto e na comparação; registros coerentes.
- [ ] Cada item com teste que falharia antes, ou justificativa registrada.
- [ ] Nenhuma chamada paga; validação estrita com código 0 nos dois repositórios.

## Validação

Developer, rodada 4 (2026-10-28). Testes novos (cada um falharia no candidato r3):

- **P1-QA-01** — `tests/integration/test_v060_r4.py`:
  - `test_jev_toggle_runs_the_typesafe_adapter_and_no_llm_router` (envio direto). O adaptador JEV, com transporte falso, recebe uma chamada e o Router não faz nenhuma chamada LLM. O ledger do `request_id` tem `router · jev-1.14.0`, e o snapshot, o trace e `models_by_agent` (o que Resultados mostra) registram `jev-1.14.0`.
  - `test_profile_comparison_with_jev_runs_the_adapter_in_every_new_cell` (duas células, duas chamadas JEV, ledger e custo por agente com `jev-1.14.0`).
  - `test_llm_toggle_still_uses_the_profile_router` (sem regressão do LLM).
  - No r3, o Router ia para o LLM e o adaptador nunca era chamado.
  - Correção: `execute_run` passa todos os agentes do perfil, e o orquestrador substitui a entrada `router` por `router_llm`. A comparação só dos Routers não foi tocada.
- **P3-QA-02** — web `tests/test_v060_interface.py::test_reais_are_shown_literally_and_not_as_a_formula`. A conversa escapa o `$` no Markdown, de modo que a tela mostra "R$ 80,00 … R$ 148,06", e o histórico gravado continua igual.
- **P3-QA-03** — web `test_case_state_after_recovery_shows_the_recovered_reply`. Depois de "Atualizar conversa", o estado do caso mostra a rota e o status da resposta recuperada, e o estado vem da conversa.
- **P3-R3-01** — `test_failure_after_paid_calls_without_a_trace_does_not_refund` (falha de persistência depois das chamadas: o contador fica em 1; no r3 voltava a 0), `test_unreadable_ledger_never_refunds` e `test_paid_attempts_reads_reserved_and_settled_rows_only`. Correção: `paid_attempts` conta as linhas `reserved`/`settled` do `request_id` no ledger primário, e só devolve com 0 confirmado. Vale para mensagens e para as células da comparação; nenhuma célula sem `request_id` chegou a iniciar.
- **Observações:**
  - O-1: `test_profile_selector_starts_on_reference_with_portuguese_names`.
  - O-2: `test_candidate_test_cap_is_prefilled_with_the_build_estimate`.
  - O-3: `test_ready_reports_the_active_knowledge_base_version`, com o novo campo `knowledge_base` em `/ready`.
  - O-4: `test_cost_quality_chart_has_no_overlapping_text_labels`; os rótulos foram para a legenda e o tooltip.
  - CHANGELOG corrigido para dez cenários.
- Não alterados, conforme instrução: a rubrica e os prompts do Router (os casos de preço e o `EN-PRICE-CONDITIONS` ficam como limitação) e o estado "QA aprovado" no README/CHANGELOG.

Validação estrita backend: **347 passed**, Ruff "All checks passed!", código 0. Web: **40 passed**, Ruff sem achados, código 0. Nenhuma chamada paga. Detalhes em [v060-developer.md](../evidence/v060-developer.md#rodada-4--2026-10-28).

Developer, rodada 5 (2026-10-28), resíduos da revisão r4:

- **P3-R4-01** (web): o escape de `$` (`literal()`) passou a valer em todo texto livre vindo do usuário ou do backend que é exibido como Markdown: pergunta pendente, comentário do avaliador, mensagens de erro do backend (`explain`), mensagem do cenário, títulos de fontes e mensagens de falha da comparação. Testes em `tests/test_v060_interface.py`:
  - `test_pending_question_is_shown_literally`;
  - `test_evaluator_comment_and_backend_errors_are_shown_literally`.
  No r4, os dois valores em reais viravam fórmula; o texto enviado e o gravado não mudam.
- **P3-R4-02** (backend, só testes): devolução das células da comparação. Testes em `tests/integration/test_v060_r4.py`:
  - `test_comparison_cells_that_failed_after_paid_calls_without_a_trace_are_not_given_back`: duas células falham depois das chamadas pagas, sem trace e com linhas no ledger, e o contador fica em 2. Pega a mutação J5 (decidir pelo trace).
  - `test_comparison_never_gives_back_a_started_cell_when_the_ledger_is_unreadable`: com o ledger ilegível, a célula iniciada continua contada e só a que nunca iniciou é devolvida, de modo que o contador fica em 1. Pega a mutação J7.

Validação estrita backend: **349 passed**, Ruff "All checks passed!", código 0. Web: **42 passed**, Ruff sem achados, código 0. Nenhuma chamada paga. Detalhes em [v060-developer.md](../evidence/v060-developer.md#rodada-5--2026-10-28).

## Status

```text
concluída
```

Revisada (Reviewer, rodadas 1–5) e validada no QA real da v0.6.0 (rodada 2, candidato r5); ver [resultado](../evidence/v060-resultado.md).
