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

Developer, rodada 1 (2026-11-03). A passagem está em [v070-developer.md](../evidence/v070-developer.md), seção "Tarefa 66, rodada 1". Os critérios ficam desmarcados até a revisão e o QA.

| Critério | Evidência determinística (`tests/integration/test_v070_webhooks.py`, salvo indicação) |
| --- | --- |
| CA-47 (receptor falso em processo) | `test_handoff_created_reaches_the_ticketing_signed_and_masked`: assinatura com `TICKETING_WEBHOOK_SECRET`, cabeçalhos, envelope, campos do contrato, cartão mascarado no `transcript`. `test_ticketing_events_resume_reply_and_close[approve\|reply\|reject]`: `ticket.assigned` → `claimed`; `ticket.action` assinado e com token de serviço retoma o grafo e emite `conversation.replied` ao ticketing e ao lojista (mesmo evento, cada um assinado com o seu segredo); `ticket.solved` → `closed` e `handoff.closed`; `ticket_id` gravado; auditoria `service:ticketing` em nome de `operator:op_ana` |
| CA-47 (serviço de ticketing real da 66b) | `tests/integration/test_v070_ticketing_integration.py::test_case_becomes_a_ticket_worked_on_the_ticketing_and_closed[approve\|reply\|reject]`: assistente, `merchant_assistant.ticketing` (sem alteração) e `mocks` em processo, com transporte HTTP de teste por host (`testing.AppTransport`). Cobre `handoff.created` → ticket `new` → `assign` (`open`; `op_bruno` recebe `409 claimed_by_other` repassado) → `actions` (`pending`; `reply_text` e `reply_delivered_at` no ticket; evento no receptor do lojista) → repetição idêntica (`replayed`) e outra chave (`409 already_resumed`) → próxima mensagem `human_reply` → `solve` (`solved`, `closed_by`) → entregas registradas nos dois lados |
| CA-48 | `test_repeated_event_id_or_key_has_no_new_effect_and_a_second_resume_conflicts`: mesmo `id` → `replayed`; outro `id` com a mesma `idempotency_key` → `replayed`; outra chave → `409 already_resumed`; mesma chave com outro texto → `409 idempotency_conflict`; uma retomada só. `test_failed_resume_is_503_and_the_ticketing_retry_of_the_same_event_resumes` (D26: `503` não fica guardado como resposta do evento) |
| `401`/`403` sem mudar o caso | `test_bad_signature_window_token_or_scope_change_nothing`: segredo errado, segredo do outro sentido, `t` 310 s fora da janela nos dois sentidos, corpo adulterado, sem token, token inválido, token de operador e de lojista. Caso, eventos e `webhook_inbox` intactos. Sem `ASSISTANT_WEBHOOK_SECRET` → `503 webhook_not_configured`. `test_unknown_operator_case_event_and_payload`: `422 unknown_operator` auditado, `404 case_not_found`, `422 unknown_event`, `400 invalid_payload` e `422 invalid_idempotency_key`, sem efeito. `test_signature_window_is_300_seconds` |
| Receptor fora do ar | `test_receiver_down_gets_three_recorded_attempts_without_breaking_the_request`: três linhas `error`/`ConnectError`, esperas 1 s e 2 s, requisição do lojista `200`; `503` → três tentativas; `404` → uma, final |
| Corpo sem segredo, token nem outro lojista | Asserções em `test_handoff_created_reaches_the_ticketing_signed_and_masked` e em `test_ticketing_events_resume_reply_and_close`: nenhum dos segredos, `Bearer` ou `eyJ`; nenhum dado de `cliente_demo_002` nem do caso dele |
| Entregas visíveis | `GET /v1/handoffs/{id}` → `deliveries` (`test_case_detail_shows_deliveries_of_every_event`); `GET /v1/conversations/{id}` → `webhook_deliveries` ao lojista; o turno do operador continua sem `delivered_at` (D24) |
| URL vazia | `test_turn_without_handoff_sends_nothing_and_empty_urls_send_nothing` |
| Receptor do lojista no `mocks` | `test_mocks_merchant_receiver_checks_the_signature_and_ignores_repeated_ids`; `test_assistant_delivers_to_the_mocks_merchant_receiver` (assinatura de um lado validada pelo outro) |
| Migração 0009 | `tests/unit/data/test_migrations.py`: `webhook_inbox` e as colunas `event_id`/`error` sobem e descem com a 0009 |
| Migração 0010 (rodada 4) | `tests/unit/data/test_migrations.py`: a descida recusa com erro claro e sem alterar nada enquanto a outbox tiver linha não entregue (`pending`, `rejected`, `failed`); com tabela vazia ou só `delivered` a descida segue e a 0010 sobe de novo. Passagem: [v070-developer.md](../evidence/v070-developer.md), seção "Tarefa 66, rodada 4 (descida da 0010)" |
| Queda no meio do turno, rodada 5 (P2-1) | `tests/integration/test_v070_webhooks.py`: `test_case_of_a_turn_that_died_is_completed_when_the_message_is_sent_again[before_checkpoint\|after_checkpoint]` (subprocesso encerrado entre o `INSERT` do caso e a transação final; o reenvio da mesma mensagem salva o fluxo, enfileira e entrega `handoff.created` uma vez e a ação do operador é aceita) e `test_case_of_a_turn_whose_outbox_write_failed_is_completed_when_the_message_is_sent_again`. Teto de tentativas (P2-2): `tests/unit/test_webhook_outbox.py::test_pending_row_with_every_attempt_used_fails_without_a_request`. P3: exclusão entre processos (caso e entrega), `enqueue` sem substituir, destino sem URL, recuperação que não impede a subida, `api` depende do `ticketing` no compose. Passagem: seção "Tarefa 66, rodada 5" |
| `docker compose config` | Válido (código 0) numa cópia do compose sem `.env` |
| Suíte estrita | Antes do commit: 1 falha de teste meu (sombreamento de variável), corrigida; 523 passed. Suíte completa com código 0 na passagem (rodada 2 da 65, mesma base) |

## Status

```text
pronta para revisão (Developer, rodada 5: queda no meio do turno e P3)
```
