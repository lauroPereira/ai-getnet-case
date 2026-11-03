# Tarefa: serviço de ticketing da demonstração

## Objetivo

Um sistema de ticketing próprio, separado do assistente, recebe o caso encaminhado, deixa o operador assumir, responder, aprovar ou rejeitar e resolver o ticket, e devolve cada ato ao assistente por webhook assinado com token de serviço.

## Especificação relacionada

[Spec v0.7.0, versão 2](../specs/identidade-hitl-v070.md) — "Contrato entre os times" (Identidade, Webhooks, Serviço de ticketing) e D16; [spec 0.2](../specs/evolucao-pos-feedback.md) RF-81, RF-85, RF-100; [ADR 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).

## Pré-condições

- Time B, worktree `C:\workspace\ai-getnet-case-wt\time-b-v070`, branch `codex/v0.7.0-ticketing` a partir da branch da versão no commit desta spec, com `.venv` próprio.
- Não depende do código do Time A: o assistente aparece nos testes como servidor falso (emissor de JWT com chave gerada no teste, JWKS e endpoint de entrada) seguindo o contrato.
- Arquivos do Time A intocados: `api/`, `orchestration/`, `agents/`, `tools/`, `data/migrations.py`, `cli.py`, `config.py`, `mocks/`. Em `pyproject.toml`, `docker-compose.yml` e `.env.example`, só acréscimos (ver passos).

## Arquivos prováveis

`src/merchant_assistant/ticketing/` (novo: `service.py`, `store.py`, `auth.py`, `webhooks.py`, `outbox.py` ou equivalentes), `tests/unit/test_ticketing_*.py`, `tests/integration/test_ticketing_*.py`, `pyproject.toml` (linha `"pyjwt[crypto]>=2.10",` logo depois de `"mcp>=2.3",`), `docker-compose.yml` (bloco do serviço `ticketing` e volume próprio, sem tocar nos outros blocos), `.env.example` (bloco "Ticketing service" no fim do arquivo).

## Passos

1. Pacote isolado: banco SQLite próprio (`TICKETING_DB_PATH`) com tickets, eventos do ticket, caixa de saída e entregas recebidas; teste de arquitetura que falha se o pacote importar outro módulo do assistente.
2. Receptor `POST /webhooks/assistant`: assinatura com `TICKETING_WEBHOOK_SECRET`, janela de 300 s, `id` repetido sem efeito; `handoff.created` cria o ticket `new` com os dados do caso; `conversation.replied` marca a resposta entregue; `handoff.closed` registra o fechamento.
3. Autenticação da API: JWT de operador validado pelo JWKS de `ASSISTANT_JWKS_URL` (cache, recarga por `kid` desconhecido), `iss` = `ASSISTANT_ISSUER`, `aud` com `ticketing`, escopo `handoff:operate`.
4. API: `GET /tickets?status=`, `GET /tickets/{id}`, `POST /tickets/{id}/assign`, `POST /tickets/{id}/actions`, `POST /tickets/{id}/solve`, com o ciclo `new → open → pending → solved` do contrato. Cada ato chama `POST {ASSISTANT_URL}/v1/integrations/ticketing/events` com assinatura (`ASSISTANT_WEBHOOK_SECRET`) e token `client_credentials` obtido e renovado pelo serviço (`TICKETING_CLIENT_ID`, `TICKETING_CLIENT_SECRET`); a resposta do assistente decide o estado e volta à tela com o mesmo código (`409`, `422`); falha de rede → caixa de saída com novas tentativas e estado "envio pendente".
5. `idempotency_key` da ação vem da tela e é repassada sem alteração.
6. Compose: serviço `ticketing` com a mesma imagem, entrada `uvicorn merchant_assistant.ticketing.service:app --port 8002`, publicado em `127.0.0.1:8002`, volume próprio para o banco, variáveis do contrato com valores fictícios; `.env.example` com o bloco do ticketing.

## Critérios de conclusão

- [ ] CA-47: com o assistente falso em processo, `handoff.created` cria o ticket; assumir, agir e resolver geram os eventos assinados com token de serviço; `conversation.replied` marca a entrega; o ciclo `new → open → pending → solved` aparece no histórico do ticket.
- [ ] CA-48: ação repetida com a mesma `idempotency_key` não gera segundo evento; `409` do assistente volta à API com o mesmo código e não muda o ticket.
- [ ] Assinatura inválida, `t` fora da janela, JWT sem `ticketing` na audiência, de outro emissor, expirado ou sem `handoff:operate` → `401`/`403`.
- [ ] Assistente fora do ar → ato fica pendente, novas tentativas registradas, nenhuma exceção na API.
- [ ] Teste de arquitetura: o pacote não importa o assistente.
- [ ] `docker compose config` válido; suíte estrita com código 0 no worktree.

## Validação

Developer, rodada 1 (2026-11-03), worktree `time-b-v070`, branch `codex/v0.7.0-ticketing`, base `fe9d12b`. Detalhes na [passagem](../evidence/v070-developer-time-b.md).

- Pacote `src/merchant_assistant/ticketing/` (`config`, `signing`, `store`, `auth`, `outbox`, `service`), com banco SQLite próprio em `TICKETING_DB_PATH`. Testes novos: `tests/unit/test_ticketing_units.py` (5) e `tests/integration/test_ticketing_service.py` (26 com parâmetros). Os testes usam um assistente falso que segue o contrato: chave RSA gerada no teste, JWKS, `client_credentials` e `POST /v1/integrations/ticketing/events`, que verifica assinatura, token e escopo `handoff:integrate`.
- CA-47: `test_full_ticket_cycle_with_signed_events_and_service_token` cobre `handoff.created` → `new`, assumir → `open`, `reply` → `pending` com `conversation.replied` recebido durante a própria ação, resolver → `solved` e `handoff.closed` registrado. No histórico, as transições são `new`, `new→open`, `open→pending`, `pending→solved`; há 3 entregas recebidas e 3 enviadas, e um único token de serviço foi emitido.
- CA-48: mesma `idempotency_key` devolve o registro (`replayed: true`) e o assistente recebe um só `ticket.action`. Os erros do assistente `409 claimed_by_other`, `409 already_resumed` e `422 unknown_operator` voltam com o mesmo código e corpo, e o ticket não muda.
- Recusas: assinatura errada ou `t` a ±330 s → `401 invalid_signature`, sem efeito; `id` repetido → `200 duplicate`. JWT sem `ticketing` na audiência, de outro emissor, expirado, adulterado, de chave estranha ou com `typ` errado → `401`; sem `handoff:operate` ou de lojista → `403`; sem token em qualquer rota de operador → `401`. Um `kid` novo recarrega o JWKS.
- Assistente fora do ar: a API devolve `202` com envio pendente e o ticket não muda. As tentativas 2 e 3 vêm depois de 1 s e 2 s e ficam registradas; esgotadas, o envio fica `failed`. Com o assistente de volta, o laço em segundo plano entrega o ato pendente. O token de serviço revogado é renovado uma vez.
- Arquitetura: `test_ticketing_does_not_import_the_assistant` passa.
- `docker compose config --quiet` terminou com código 0, sem `.env` no worktree. Não subi o Docker.
- Suíte estrita: `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v070-b-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` terminou com código 0 e 380 testes aprovados; ruff limpo.
- Nenhuma chamada paga. Não toquei em arquivo do Time A.

## Status

```text
Implementada pelo Developer (rodada 1); aguarda revisão independente e as respostas do Supervisor às 3 perguntas da passagem.
```
