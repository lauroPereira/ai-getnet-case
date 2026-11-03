# Tarefa: identidade por JWT, principal, escopos e auditoria em todo tool call

## Objetivo

O assistente emite e valida JWT; toda mensagem exige token; o lojista vem do principal; cada tool call verifica escopo e lojista e grava auditoria com o principal.

## Especificação relacionada

[Spec v0.7.0, versão 2](../specs/identidade-hitl-v070.md) — seção "Contrato entre os times / Identidade" e decisões D1 a D5, D12, D13; [spec 0.2](../specs/evolucao-pos-feedback.md) RF-76 a RF-79; [plano](../specs/evolucao-pos-feedback-plano.md) decisões 1 a 3; [ADR 0017](../architecture/decisions/0017-identidade-principal-escopos.md).

## Pré-condições

- Branch `codex/v0.7.0-identidade-hitl` (Time A, checkout principal).
- Migração reservada 0009: crie-a aqui com o que a identidade precisa (usuários e clients com hash, `api_principals.scopes`, `revoked_tokens`, `audit_events.principal_id`/`scope`/`on_behalf_of`, `rate_limit_hits`); a 64 acrescenta o resto na mesma migração. Não use 0010.
- Sem chamada paga.

## Arquivos prováveis

`api/identity.py` (novo: emissor, verificador, `Principal`, papéis e escopos), `api/app.py`, `api/v1.py`, `api/schemas.py`, `config.py`, `tools/base.py`, `tools/registry.py`, `tools/domain.py` (só a assinatura de auditoria), `agents/escalation.py` (escopo `handoff:create`), `mcp_server.py`, `cli.py` (`auth token`, smoke), `data/migrations.py`, `pyproject.toml` (`pyjwt[crypto]`), `.env.example`, `docker-compose.yml` (só acréscimos), testes.

## Passos

1. Emissor: chave RS256 (D2), `POST /v1/auth/token` (`password` e `client_credentials`), `POST /v1/auth/revoke`, `/.well-known/jwks.json`, `/.well-known/openid-configuration`, claims e validades do contrato.
2. Verificador único (`resolve_credential(token) -> Principal`): assinatura, `kid`, `iss`, `aud`, `exp`/`nbf` com tolerância, `jti` revogado, `typ`. Aceita JWKS externo por configuração (`JWT_JWKS_URL`, `JWT_ISSUER`).
3. Usuários e client da demo (D1) com hash PBKDF2; aviso na subida com valores de exemplo; `.env.example` com valores fictícios nomeados como tal.
4. Todas as rotas autenticadas usam o verificador. `POST /v1/sessions` e `DELETE /v1/sessions/current` saem (D3). Rotas de admin e demo continuam autorizadas por papel.
5. `POST /messages`: `Authorization: Bearer` obrigatório; `user_id` opcional; divergente → `403 identity_mismatch`; lojista do principal; operador, serviço e admin sem lojista → `403`. `/docs` com o esquema de segurança e o exemplo token + mensagem.
6. `CustomerContext` com `principal_id`, `role`, `scopes`; cada `ToolSpec` declara `scope`; `registry.execute` verifica escopo e lojista antes do allowlist; recusa sem executar; todo call grava auditoria (principal, ferramenta, escopo, resultado; `on_behalf_of` quando houver).
7. Escalation verifica `handoff:create`. Rate limit (D5). Rotas de demo com token e dono (D13).
8. MCP e CLI por `MERCHANT_ASSISTANT_TOKEN` (D12); `merchant-assistant auth token` obtém o token; `smoke` obtém o token sozinho; `ask` continua em processo.

## Critérios de conclusão

- [ ] CA-46: sem token `401`; token adulterado, expirado, revogado, de outro emissor ou sem a audiência `merchant-assistant` → `401`; `user_id` de outro lojista `403 identity_mismatch`; lojista B não lê conversa nem trace de A pelas rotas `/v1` e de demo.
- [ ] CA-46: em uma execução programada com N tool calls há N registros de auditoria com principal, escopo e resultado, inclusive recusas por escopo e por lojista.
- [ ] Token de operador ou de serviço em `POST /messages` → `403`; token de lojista não tem `handoff:operate`.
- [ ] JWKS publicado valida o token emitido com uma biblioteca independente do emissor (teste com `jwt.PyJWKClient` ou equivalente sobre a resposta da rota); troca para JWKS externo coberta por teste com chave gerada no teste.
- [ ] `client_credentials` do `ticketing-demo` emite token com `handoff:integrate` e sem lojista; segredo errado → `401 invalid_client`.
- [ ] Rate limit: a (limite+1)-ésima requisição na janela recebe `429` sem chamada a modelo.
- [ ] MCP recusa token inválido ou de operador e deriva o lojista do token.
- [ ] Nenhuma chave privada ou senha em texto no banco, no log ou no Git.
- [ ] `docker compose config` válido; smoke programado passa com token; suíte estrita com código 0.

## Validação

A preencher pelo Developer.

## Status

```text
em andamento
```
