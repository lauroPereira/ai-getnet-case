# Tarefa: fila de operador persistente e idempotente

## Objetivo

O caso encaminhado entra numa fila com estado, operador e eventos; a reivindicação e as ações `approve`, `reply` e `reject` são idempotentes, pela API do assistente, pela CLI e (na 66) pelo ticketing, todas pelo mesmo serviço.

## Especificação relacionada

[Spec v0.7.0, versão 2](../specs/identidade-hitl-v070.md) (D6, D7, D9, D10, D14 e a tabela "Ticketing → assistente"), [spec 0.2](../specs/evolucao-pos-feedback.md) RF-80, RF-81, RF-83, RF-85, [plano](../specs/evolucao-pos-feedback-plano.md) decisões 7 e 8, modelo de dados "Migração 0009".

## Pré-condições

- Tarefa 63 com o verificador de token pronto.
- Migração 0009 (reservada à v0.7.0, Time A), acrescentada ao que a 63 criou.

## Arquivos prováveis

`data/migrations.py` (0009), `agents/escalation.py` (protocolo `HO-…`, `thread_id`, estado inicial `open`), `handoffs.py` (novo: serviço da fila), `api/v1.py`, `api/schemas.py`, `cases.py`, `cli.py`, testes.

## Passos

1. Migração 0009 completa e reversível: colunas e tabelas do plano, mais `handoff_cases.thread_id` (D6) e `ticket_id`; sobe e desce em banco sintético com dados.
2. Escalation grava `HO-AAAAMMDD-XXXXXX`, `queue_state=open`, `channel`, `thread_id`; `simulated` sai do payload público.
3. Serviço único da fila (`claim`, `act`, `close`) com `BEGIN IMMEDIATE`, D9, D10 e `handoff_events` com chave de idempotência única; a ação chama um ponto único de retomada, ainda sem grafo (a 65 o implementa).
4. API com token de operador (`handoff:operate`): `GET /v1/handoffs?state=`, `GET /v1/handoffs/{id}` (resumo, pergunta pendente, rascunho, conversa mascarada, eventos, campo de entregas vazio até a 66), `POST /v1/handoffs/{id}/claim`, `POST /v1/handoffs/{id}/actions` (`{"action","text","idempotency_key"}`; mesma chave → `200` com `replayed: true`; caso já retomado → `409 already_resumed`).
5. CLI `merchant-assistant operator list|show|act` sobre o mesmo serviço, com o operador do token (D12).

## Critérios de conclusão

- [ ] CA-47 (fila): caso encaminhado aparece em `GET /v1/handoffs` com estado `open`, protocolo `HO-…`, resumo e rascunho.
- [ ] CA-48: duas ações concorrentes com chaves diferentes → uma vence, a outra `409 already_resumed`; mesma chave → `200` com o mesmo registro e `replayed: true`; teste com threads reais sobre SQLite.
- [ ] `409 claimed_by_other` para o segundo operador; reivindicação repetida pelo mesmo operador é idempotente.
- [ ] CA-46: token de lojista recebe `403` nas rotas de fila.
- [ ] Migração 0009 sobe e desce com dados preservados no sentido de subida.
- [ ] Suíte estrita com código 0.

## Validação

Developer, rodada 1 (2026-11-03). Passagem em [v070-developer.md](../evidence/v070-developer.md), seção "Tarefa 64, rodada 1". Os critérios ficam desmarcados até a revisão e o QA.

| Critério | Evidência determinística |
| --- | --- |
| CA-47 (fila) | `tests/integration/test_v070_handoffs.py::test_escalated_case_enters_the_queue_open_with_protocol_summary_and_draft`: `POST /messages` → `GET /v1/handoffs` com `open`, `HO-AAAAMMDD-XXXXXX`, resumo, rascunho, pergunta pendente, `thread_id` = `request_id` (D6), conversa mascarada, `simulated` fora do payload |
| CA-48 | `test_concurrent_actions_with_different_keys_resume_once` (três threads reais sobre SQLite, três rodadas: uma vence, duas `409 already_resumed`, `resume_count = 1`); `test_concurrent_actions_with_the_same_key_return_the_same_record`; `test_action_is_idempotent_and_a_second_resume_is_refused` (mesma chave → `200` e `replayed: true`; outra chave → `409`; o ponto de retomada é chamado uma vez) |
| `claimed_by_other` e reivindicação idempotente | `test_claim_is_idempotent_and_conflicts_with_another_operator` |
| CA-46 (fila) | `test_merchant_admin_and_anonymous_cannot_use_the_queue` (`403 insufficient_scope` para lojista e admin nas quatro rotas, `401` sem token); `test_queue_calls_are_audited_with_the_operator` |
| Migração 0009 | `tests/unit/data/test_migrations.py::test_queue_part_of_0009_keeps_cases_and_messages` (caso e mensagens anteriores preservados nos dois sentidos, chave de idempotência única, `queue_state` verificado) e `test_identity_migration_0009_round_trip` |
| CLI sobre o mesmo serviço | `test_cli_operator_uses_the_same_service_and_the_token_operator` (operador do token; a API vê o que a CLI fez; token de lojista recusado) |
| Suíte estrita | `lint_and_tests.py --strict` → código 0, **422 passed**, Ruff ok, skills ok |

## Status

```text
pronta para revisão (Developer, rodada 1)
```
