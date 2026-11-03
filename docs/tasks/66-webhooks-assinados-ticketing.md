# Tarefa: webhooks assinados e receptores de ticketing e do lojista

## Objetivo

O caso criado vai ao ticketing e a resposta pronta vai ao lojista por webhooks assinados, com tentativas e registro consultável; o `mocks` da demo recebe os dois.

## Especificação relacionada

[Spec v0.7.0](../specs/identidade-hitl-v070.md) (D11, D12), [spec 0.2](../specs/evolucao-pos-feedback.md) RF-84, RF-100, [plano](../specs/evolucao-pos-feedback-plano.md) decisão 6, [ADR 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).

## Pré-condições

Tarefa 65 com a retomada funcionando (o evento `conversation.replied` nasce dela).

## Arquivos prováveis

`api/webhooks.py` (novo), `agents/escalation.py` ou o orquestrador (disparo de `handoff.created`), ponto de retomada (disparo de `conversation.replied`), `api/v1.py` (`webhook_url` na sessão, entregas em `GET /v1/handoffs/{id}` e na conversa), `config.py`, `mocks/service.py`, `docker-compose.yml`, `.env.example`, testes.

## Passos

1. `webhooks.py`: corpo JSON mascarado (sem texto integral de dados sensíveis; protocolo, caso, conversa, evento, carimbo, id de entrega), assinatura e cabeçalhos de D11, três tentativas com esperas configuráveis, timeout por tentativa, entrega numa thread curta fora da requisição, uma linha de `webhook_deliveries` por tentativa.
2. `handoff.created` para `HANDOFF_WEBHOOK_URL`; `conversation.replied` para a `webhook_url` da sessão do lojista (D12) ou `CONVERSATION_WEBHOOK_URL`. URL vazia → nenhuma entrega, sem erro.
3. Entregas visíveis em `GET /v1/handoffs/{id}` e na conversa.
4. `mocks`: `POST/GET /ticketing/cases` e `POST/GET /merchant/events`, validando a assinatura (`401 invalid_signature`) e ignorando entrega repetida pelo id.
5. Compose: `WEBHOOK_SIGNING_SECRET` (fictício, igual nos dois serviços), `HANDOFF_WEBHOOK_URL=http://mocks:8001/ticketing/cases`, `CONVERSATION_WEBHOOK_URL=http://mocks:8001/merchant/events`, `WEBHOOK_ALLOWED_HOSTS=mocks`. Só acréscimos ao compose e ao `.env.example`.

## Critérios de conclusão

- [ ] CA-47: em teste de integração com o `mocks` em processo, o caso criado aparece em `GET /ticketing/cases` com assinatura válida e a resposta retomada aparece em `GET /merchant/events`; as entregas aparecem no caso e na conversa.
- [ ] Assinatura errada → `401` no receptor e entrega registrada como falha; receptor fora do ar → três tentativas registradas e nenhuma exceção na requisição do lojista.
- [ ] `webhook_url` de host não permitido → `422 webhook_host_not_allowed`.
- [ ] Corpo do webhook não contém a chave de sessão, segredo nem dado de outro lojista (teste).
- [ ] `docker compose config` válido; suíte estrita com código 0.

## Validação

A preencher pelo Developer.

## Status

```text
pendente
```
