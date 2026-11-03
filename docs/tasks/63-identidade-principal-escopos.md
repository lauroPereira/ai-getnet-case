# Tarefa: identidade por principal, escopos e auditoria em todo tool call

## Objetivo

Toda mensagem exige sessão; o lojista vem do principal autenticado; cada tool call verifica escopo e lojista e grava auditoria com o principal.

## Especificação relacionada

[Spec v0.7.0](../specs/identidade-hitl-v070.md) (D1 a D5, D13, D14), [spec 0.2](../specs/evolucao-pos-feedback.md) RF-76 a RF-79, [plano](../specs/evolucao-pos-feedback-plano.md) decisões 1 a 3, [ADR 0017](../architecture/decisions/0017-identidade-principal-escopos.md).

## Pré-condições

- Branch `codex/v0.7.0-identidade-hitl` (Time A, checkout principal).
- Migração 0009 é da 64. Se esta tarefa precisar de coluna nova (`audit_events.principal_id`, `scope`; `api_principals.scopes`; `rate_limit_hits`), crie a migração 0009 aqui com essas partes e deixe a 64 acrescentar o resto na mesma migração. Número reservado: 0009 (não use 0010).
- Sem chamada paga.

## Arquivos prováveis

`api/identity.py` (novo), `api/app.py`, `api/v1.py`, `api/schemas.py`, `config.py`, `tools/base.py`, `tools/registry.py`, `tools/domain.py` (só a assinatura de auditoria), `agents/escalation.py` (escopo `handoff:create`), `mcp_server.py`, `cli.py` (smoke), `data/migrations.py`, `.env.example`, `docker-compose.yml` (só acréscimos), testes.

## Passos

1. `api/identity.py`: `Principal(principal_id, role, customer_id, scopes)`, tabela papel → escopos (D3) e `resolve_credential(credential) -> Principal | None`, único ponto de troca por OIDC. `POST /v1/sessions` passa a usá-lo e devolve `role`, `customer_id`, `scopes`.
2. Configuração: `MERCHANT_ACCESS_KEYS` e `OPERATOR_ACCESS_KEYS` (D1), validação na subida (≥ 24 caracteres, sem repetição entre papéis), aviso quando chave de exemplo está em uso; `.env.example` com valores fictícios nomeados como tal.
3. `POST /messages`: exige `Authorization: Bearer` (mesma sessão do `/v1`); `user_id` opcional; divergente → `403 identity_mismatch`; lojista do principal. `401` sem sessão. `/docs` com o exemplo de sessão (esquema de segurança visível e exemplo de duas chamadas).
4. `CustomerContext` com `principal_id`, `role`, `scopes`; `registry.execute` verifica escopo da ferramenta (cada `ToolSpec` declara `scope`) e lojista antes do allowlist por agente; recusa → erro estruturado `FORBIDDEN_SCOPE` (ou equivalente) sem executar. Todo call, aceito ou recusado, grava `audit_events` com principal, ferramenta, escopo e resultado.
5. Escalation verifica `handoff:create` antes de gravar o caso.
6. Rate limit por principal (D5) com `429 rate_limited` e `Retry-After`, antes de qualquer chamada a modelo.
7. Rotas de demo `GET /traces/{id}` e `GET /conversations/{id}` com sessão e dono (D14).
8. MCP: `--access-key` ou `MERCHANT_ASSISTANT_ACCESS_KEY`; `--customer` removido (D13).
9. `merchant-assistant smoke` cria a sessão sozinho; CLI `ask` continua em processo.

## Critérios de conclusão

- [ ] CA-46: sem sessão `401`; `user_id` de outro lojista `403 identity_mismatch`; lojista B não lê conversa nem trace de A pelas rotas `/v1` e de demo (testes de integração).
- [ ] CA-46: em uma execução programada com N tool calls há N registros de auditoria com principal, escopo e resultado, inclusive para recusas por escopo e por lojista.
- [ ] Sessão de operador em `POST /messages` → `403` (operador não tem lojista próprio; só age sobre o lojista de um caso reivindicado), e sessão de lojista não tem `handoff:operate`.
- [ ] Rate limit: a (limite+1)-ésima requisição na janela recebe `429` sem chamada a modelo (relógio fixo).
- [ ] MCP recusa chave inválida ou de operador; deriva o lojista da chave.
- [ ] `docker compose config` válido com as chaves do exemplo; smoke programado passa com sessão.
- [ ] Suíte estrita com código 0; nenhuma chamada paga.

## Validação

A preencher pelo Developer.

## Status

```text
pendente
```
