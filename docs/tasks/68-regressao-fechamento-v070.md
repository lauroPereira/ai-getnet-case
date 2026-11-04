# Tarefa: regressão integrada e preparação do QA da v0.7.0

## Objetivo

Provar, com modelo programado, a história inteira de ponta a ponta sobre as tarefas 63 a 66b integradas (assistente e ticketing), e deixar a campanha `v070-qa` pronta para o QA.

## Especificação relacionada

[Spec v0.7.0, versão 2](../specs/identidade-hitl-v070.md) (critérios e prova), [história](../historias/identidade-hitl-v070.md), [plano](../specs/evolucao-pos-feedback-plano.md) tarefa 68 e "Estratégia de testes".

## Pré-condições

Tarefas 63 a 66 e 66b com parecer apto; branch do Time B integrada pelo Supervisor na branch da versão. Fechamento do Supervisor (evidência, README, CHANGELOG, ADRs aceitas, merge) fica fora desta tarefa.

## Arquivos prováveis

`tests/integration/` (história programada), `evaluation/` ou `cli.py` só se a regressão real precisar de token, `orchestration/budget.py` só se a campanha de US$0,20 não montar, `pyproject.toml` (versão `0.7.0`), testes.

## Passos

1. Teste de integração programado que percorre os momentos da história com o assistente e o ticketing reais em processo (transporte HTTP de teste entre os dois, sem rede externa) e dois processos para o reinício.
2. Conferir que `eval` sobre os 40 casos e `followup` roda no caminho da versão.
3. Conferir que a campanha `v070-qa` monta com teto de US$0,20 uma única vez combinada com o ledger primário (teste sem rede).
4. Versão do pacote `0.7.0`; `docker compose config` válido com os serviços `api`, `ticketing`, `mocks` e `qdrant`.

## Critérios de conclusão

- [ ] CA-46, CA-47 e CA-48 cobertos pelo teste da história, além dos testes de cada tarefa.
- [ ] Suíte estrita com código 0; nenhuma chamada paga.
- [ ] Campanha `v070-qa` montável com US$0,20 (teste).

## Validação

Developer, rodada 1 (2026-11-03). A passagem está em [v070-developer.md](../evidence/v070-developer.md), seção "Tarefa 68". Os critérios ficam desmarcados até a revisão e o QA.

| Critério | Evidência determinística |
| --- | --- |
| CA-46 | `tests/integration/test_v070_story.py::test_story_moments_1_to_15_and_17` (momentos 1 a 5 e 17): sem token `401` sem chamada a modelo; login e claims validadas pelo JWKS; token adulterado e revogado `401`; `user_id` forjado `403 identity_mismatch`; auditoria por tool call (principal, escopo, resultado) com a soma dos `tool_calls` de todas as requisições igual às linhas de auditoria; outro lojista sem dado do primeiro na conversa, no trace, na fila e no ticketing. Expirado, outro emissor e outra audiência: `tests/unit/test_identity.py` (tarefa 63) |
| CA-47 | mesmo teste (momentos 6 a 7, 10 a 15): caso vira ticket `new` com resumo, pergunta, rascunho e conversa mascarada; `reply`, `approve` e `reject` feitos no ticketing real produzem turno `via=operator`, entrega ao lojista (webhook sem `operator_id`) e volta ao ticket; `reject` reexecuta o Support uma vez sob `operator:op_ana` e o lojista do caso; `solve` fecha o caso e o ticketing recebe `handoff.closed`; a outbox durável tem as dez linhas `delivered`, uma tentativa cada |
| CA-48 | mesmo teste (momentos 8, 9, 11): a insistência do lojista não perde a interrupção; `409 claimed_by_other`; resposta perdida no caminho de volta e repetida pela caixa de saída do ticketing (`replayed`, uma retomada só); ação nova `409 already_resumed`. `test_story_moment_16_restart_between_handoff_and_action`: encaminha num processo, ele termina, outro processo age no ticketing sobre o mesmo runtime e checkpoint (`resume_status=done`), mesma chave depois do reinício devolve o registro |
| Eval dos 40 casos e do `followup` no caminho da versão | `tests/integration/test_v070_closing.py::test_eval_cli_runs_the_40_cases_and_the_followup_conversations`; `content_ok` 0,575 → 0,625 (igual à v0.6.0, caso a caso): `UC14` (rótulo `SIM-` → `HO-`, D7) e `V030-CONTRACT-TERMINATION` (linha de reserva em inglês voltou a dizer "human agent"). Investigação e antes/depois na passagem |
| Campanha `v070-qa` montável com US$0,20 (teste) | `test_v070_campaign_cap_mounts_once_at_twenty_cents_combined_with_the_primary_ledger` e `test_a_request_runs_through_the_campaign_guard_and_both_ledgers_record_it` |
| Versão 0.7.0 e compose | `test_package_version_is_0_7_0`; `test_compose_declares_api_ticketing_mocks_and_qdrant_with_the_webhook_contract`; `docker compose config --quiet` numa cópia sem `.env`: código 0, serviços `api`, `mocks`, `qdrant`, `ticketing` |
| Lacunas da revisão da T66 (rodada 5) e P3-2 | `tests/integration/test_v070_webhooks.py` (15 testes novos: guardas de `_complete_interrupted_handoff` e `_has_checkpoint`, filtro de destino da recuperação, regra de canal) e `tests/unit/test_webhook_outbox.py` (`webhook_targets` exige URL e segredo); nove mutantes mortos |
| P3-A, P3-B e P3-C do Time A | `tests/integration/test_v070_review_gaps.py` (7 testes); três mutantes mortos |
| Rodada 2 (parecer da revisão): `SC-HANDOFF` e P3 | Catálogo `SC-HANDOFF` com `HO-` e `must_not_include` `SIM-`/`simul` (também em `UC14`); `test_catalog_scenarios_carry_the_message_and_labels_of_their_source_cases` e `test_handoff_scenario_passes_every_check_through_the_api_with_the_scripted_model` (11 de 11) em `test_v070_closing.py`; aviso na subida de URL de webhook sem segredo (`configuration_warnings`, testes em `test_webhook_outbox.py` e `test_v070_webhooks.py`). Versão do catálogo continua `"1"` (justificativa na passagem) |
| Suíte | Estrita não rodada pelo Developer (fica com o Supervisor). Rodada 1: 242 (unit) + 78 + 81 + 231 (integração) = 632 passed, os 579 da T66 mais 53 novos. Rodada 2: 178 + 89 passed nos conjuntos focados e `--collect-only` com **640 testes** (632 + 8 novos); `ruff check src tests` ok; nenhuma chamada paga; `WinError 5` não ocorreu |

## Status

```text
pronta para revisão (Developer, rodada 2: SC-HANDOFF do catálogo e P3 da revisão)
```
