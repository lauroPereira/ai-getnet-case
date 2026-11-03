# Tarefa: fila de operador persistente e idempotente

## Objetivo

O caso encaminhado entra numa fila com estado, operador e eventos; o operador lista, reivindica e registra `approve`, `reply` ou `reject` com idempotência, pela API e pela CLI.

## Especificação relacionada

[Spec v0.7.0](../specs/identidade-hitl-v070.md) (D6, D7, D9, D10, D15), [spec 0.2](../specs/evolucao-pos-feedback.md) RF-80, RF-81, RF-83, RF-85, [plano](../specs/evolucao-pos-feedback-plano.md) decisões 7 e 8, modelo de dados "Migração 0009".

## Pré-condições

- Tarefa 63 com parecer apto ou em revisão sem achado P1 nas sessões e escopos.
- Migração 0009 (reservada à v0.7.0, Time A).

## Arquivos prováveis

`data/migrations.py` (0009), `agents/escalation.py` (protocolo `HO-…`, `thread_id`, estado inicial `open`), `api/v1.py`, `api/schemas.py`, `cases.py`, `cli.py`, testes.

## Passos

1. Migração 0009 completa e reversível: colunas e tabelas do plano, mais `handoff_cases.thread_id` (D6). Sobe e desce em banco sintético com dados.
2. Escalation grava `HO-AAAAMMDD-XXXXXX`, `queue_state=open`, `channel`, `thread_id`; `simulated` sai do payload público.
3. `GET /v1/handoffs?state=`, `GET /v1/handoffs/{id}` (resumo, pergunta pendente, rascunho, conversa mascarada, eventos; o campo de entregas de webhook já existe, vazio até a 66), `POST /v1/handoffs/{id}/claim`, `POST /v1/handoffs/{id}/actions` com `{"action","text","idempotency_key"}`; todas exigem `handoff:operate`.
4. Reivindicação e ação sob `BEGIN IMMEDIATE`; D9 e D10; `handoff_events` com chave de idempotência única. Nesta tarefa a ação registra evento e estado; a retomada do grafo entra na 65 por um ponto único chamado de dentro da ação (deixe a costura explícita).
5. CLI `merchant-assistant operator list|show|act` sobre o mesmo serviço (sem HTTP), com o operador derivado da chave (`--access-key` ou variável de ambiente).
6. Exporte o OpenAPI `/v1` atualizado para o projeto web consumir (o arquivo vive no repositório web; registre na passagem o comando e o hash do JSON gerado, sem escrever no outro repositório).

## Critérios de conclusão

- [ ] CA-47 (parte da fila): caso encaminhado aparece em `GET /v1/handoffs` com estado `open`, protocolo `HO-…`, resumo e rascunho.
- [ ] CA-48: duas ações concorrentes com chaves diferentes → uma vence, a outra `409 already_resumed`; mesma chave → `200` com o mesmo registro e `replayed: true`; teste com threads reais sobre SQLite.
- [ ] `409 claimed_by_other` para o segundo operador; reivindicação repetida pelo mesmo operador é idempotente.
- [ ] CA-46: sessão de lojista recebe `403` nas rotas de fila; operador não vê casos fora da fila.
- [ ] Migração 0009 sobe e desce com dados preservados no sentido de subida.
- [ ] Suíte estrita com código 0.

## Validação

A preencher pelo Developer.

## Status

```text
pendente
```
