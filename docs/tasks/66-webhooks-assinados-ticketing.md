# Tarefa: integração do assistente com o ticketing por webhooks assinados

## Objetivo

O assistente envia os eventos do caso ao ticketing e ao lojista e recebe do ticketing a reivindicação, a ação e a resolução, com assinatura, token de serviço, idempotência e registro de entregas.

## Especificação relacionada

[Spec v0.7.0, versão 2](../specs/identidade-hitl-v070.md) — "Contrato entre os times / Webhooks" e D11; [spec 0.2](../specs/evolucao-pos-feedback.md) RF-84, RF-100; [plano](../specs/evolucao-pos-feedback-plano.md) decisão 6; [ADR 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).

## Pré-condições

Tarefa 65 com a retomada funcionando. O serviço de ticketing é a 66b (Time B, outra branch): aqui ele aparece só como receptor falso nos testes, seguindo o contrato.

## Arquivos prováveis

`api/webhooks.py` (novo: assinatura, envelope, envio com tentativas), `api/integrations.py` ou `api/v1.py` (entrada do ticketing), disparos em `agents/escalation.py` ou no orquestrador e no ponto de retomada, `handoffs.py`, `config.py`, `mocks/service.py` (receptor do lojista), `docker-compose.yml` e `.env.example` (só acréscimos no bloco da API e do `mocks`), testes.

## Passos

1. `webhooks.py`: envelope, cabeçalhos e assinatura do contrato; corpo mascarado; até três tentativas; envio numa thread curta fora da requisição; uma linha de `webhook_deliveries` por tentativa.
2. Saída: `handoff.created` e `handoff.closed` para `TICKETING_WEBHOOK_URL`; `conversation.replied` para `TICKETING_WEBHOOK_URL` e `CONVERSATION_WEBHOOK_URL`. URL vazia → nenhuma entrega, sem erro.
3. Entrada `POST /v1/integrations/ticketing/events`: assinatura com `ASSISTANT_WEBHOOK_SECRET` e janela de 300 s, token com `handoff:integrate`, `id` repetido sem efeito, `operator_id` de operador ativo; `ticket.assigned`/`ticket.action`/`ticket.solved` pelo serviço da fila da 64 (mesmas regras de `409` e idempotência); auditoria com `service:ticketing` em nome do operador; respostas do contrato; `ticket_id` gravado no caso.
4. Entregas visíveis em `GET /v1/handoffs/{id}` e na conversa.
5. `mocks`: `POST/GET /merchant/events` com validação de assinatura (`CONVERSATION_WEBHOOK_SECRET`). O receptor passivo `/ticketing/cases` da versão 1 desta spec não é criado.
6. Compose e `.env.example`: segredos fictícios por sentido, `TICKETING_WEBHOOK_URL=http://ticketing:8002/webhooks/assistant`, `CONVERSATION_WEBHOOK_URL=http://mocks:8001/merchant/events`. O bloco do serviço `ticketing` é da 66b; não o crie.

## Critérios de conclusão

- [ ] CA-47: com receptor falso de ticketing em processo, `handoff.created` chega assinado e com corpo mascarado; `ticket.action` assinado com token de serviço retoma o grafo e gera `conversation.replied` para o ticketing e para o lojista; `ticket.solved` fecha o caso e gera `handoff.closed`.
- [ ] CA-48: `ticket.action` repetido (mesmo `id` ou mesma `idempotency_key`) sem efeito novo; caso já retomado → `409 already_resumed`.
- [ ] Assinatura errada, `t` fora da janela, token sem `handoff:integrate` ou token de operador na entrada → `401`/`403`; nada muda no caso.
- [ ] Receptor fora do ar → três tentativas registradas e nenhuma exceção na requisição do lojista.
- [ ] Corpo de webhook sem segredo, token nem dado de outro lojista (teste).
- [ ] `docker compose config` válido; suíte estrita com código 0.

## Validação

A preencher pelo Developer.

## Status

```text
pendente
```
