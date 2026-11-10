# Tarefa 102a — Mapeamento dos usuários estáticos do Dex

## Objetivo

Permitir que os usuários estáticos do Dex no perfil OIDC recebam os papéis configurados mesmo quando o emissor não inclui a claim `groups`.

## Especificação relacionada

[Identidade e operação — v0.13.0](../specs/identidade-operacao-v0130.md): D2 e CA-68. [ADR 0025](../architecture/decisions/0025-identidade-e-operacao.md).

## Comportamento

- O exemplo do Dex solicita `openid profile email`; cada usuário estático emite `email`, `email_verified: true` e `name`.
- Com `groups_claim` igual a `email`, `OIDC_ISSUERS` mapeia endereços de e-mail completos e exatos a papéis. O valor deve ser uma única string e `email_verified` deve ser exatamente `true`; ausência ou formato inválido não concede papel.
- O identificador do lojista vem da claim `name`, configurada pelo administrador do emissor. Sem `groups_claim: email`, o mapeamento normal de grupos continua igual.
- Usuários sintéticos do exemplo: `cliente1988@lojista.example` como lojista, `op_ana@operador.example` como operadora e `visitante@visitante.example` sem papel autorizado.

## Critérios de conclusão

- O token do Dex decodificado contém e-mail verificado e identificador, e a API mapeia a operadora e o lojista às respectivas permissões.
- O visitante sem papel recebe `403 insufficient_scope`.
- E-mail ausente, não verificado, não textual, em lista ou sem correspondência exata não recebe papel; o mapeamento por `groups` permanece inalterado.
- `.env.example`, documentação da API e README usam a mesma configuração e claims.
