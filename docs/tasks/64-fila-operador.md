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

A preencher pelo Developer.

## Status

```text
pendente
```
