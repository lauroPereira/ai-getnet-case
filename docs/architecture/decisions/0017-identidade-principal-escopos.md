# 0017. Identidade: credencial → JWT → principal → escopos → lojista

## Título

Emitir e validar JWT (RS256, JWKS) no assistente, derivar o lojista do principal do token e verificar escopo e lojista em todo tool call.

## Status

Aceita (v0.7.0, 2026-11-04). Atualizada pela [ADR 0025](0025-identidade-e-operacao.md) (v0.13.0).

## Contexto

Até a v0.6.0, `POST /messages` aceitava o `user_id` do payload como autoridade; a sessão `/v1` existia só para `demo` e `admin`, com token opaco e um lojista fixo da configuração. As ferramentas recebiam o lojista do servidor, nunca do modelo, mas não sabiam quem as chamava nem com que permissão. Faltavam a cadeia credencial → principal autenticado → autorização → lojista e a autorização de cada tool call (RF-76 a RF-79). O responsável escolheu tokens JWT, reconhecíveis como padrão de mercado, em vez de chave sintética trocada por sessão opaca.

## Decisão

- **Emissor próprio** no assistente: `POST /v1/auth/token` (RFC 6749: `password` para os usuários da demo, `client_credentials` para serviços), `POST /v1/auth/revoke`, `/.well-known/jwks.json` e `/.well-known/openid-configuration`. Tokens RS256 no perfil RFC 9068 (`typ=at+jwt`) com `iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, `jti`, `client_id`, `role`, `scope` e, para lojista, `customer_id`. Chave privada gerada no runtime ou lida de arquivo, nunca no Git.
- **Um verificador** (`resolve_credential(token) -> Principal`) para API, MCP e CLI: assinatura, `kid`, emissor, audiência, validade, revogação. Configurar `JWT_ISSUER` e `JWT_JWKS_URL` troca o emissor por um provedor OIDC externo sem mexer nas rotas nem nas ferramentas.
- **Principal** = `principal_id`, `role` (`merchant`, `operator`, `service`, `demo`, `admin`), `customer_id` (só lojista e demo) e `scopes` (tabela na [spec v0.7.0](../../specs/identidade-hitl-v070.md)).
- **Token obrigatório** em `POST /messages` e `/v1/messages`, sem modo aberto; `user_id` opcional e, se divergir, `403 identity_mismatch`. `/v1/sessions` sai.
- **Tool call autorizado:** cada ferramenta declara um escopo; `registry.execute` verifica escopo e lojista antes do allowlist por agente e grava auditoria (principal, ferramenta, escopo, resultado, em nome de quem) em todo call. Quando o operador age sobre um caso, o lojista vem do caso, lido pelo servidor.
- **Limite por principal** em janela de 60 s (`429 rate_limited`).
- Credenciais da demo: usuários e client sintéticos com senhas fictícias guardadas como hash; admin e demo desligados até serem configurados.

```mermaid
flowchart LR
    C["Credencial: usuário e senha ou client credentials (emissor OIDC externo desde a v0.13.0)"] --> E["Emissor: /v1/auth/token"]
    E --> J["JWT RS256 (iss, sub, aud, exp, jti, role, scope, customer_id)"]
    K["JWKS /.well-known/jwks.json"] --> V
    J --> V["Verificador único: resolve_credential"]
    V --> P["Principal: id, papel, escopos"]
    P --> R["Rota: papel"]
    P --> T["Tool call: escopo + lojista + auditoria"]
    P --> L["Lojista do token ou do caso"]
    L --> T
```

## Alternativas consideradas

- **Chave sintética trocada por sessão opaca** (proposta inicial): não adotada: atendia a cadeia pedida, mas é menos reconhecível como autenticação e não demonstra a troca por um provedor externo.
- **Keycloak (OIDC real) no compose:** não adotado: cerca de 1 GB de RAM a mais, subida lenta e mais um serviço para quem sobe a demonstração; o verificador por emissor e JWKS permite usá-lo por configuração.
- **HS256 com segredo compartilhado:** não adotado: sem JWKS, o ticketing precisaria do segredo de assinatura para validar tokens.
- **Authorization code + PKCE na demo:** não adotado nesta versão, por exigir redirecionamento e tela de login; adotado na v0.13.0 ([ADR 0025](0025-identidade-e-operacao.md)).
- **Escopo só por rota:** não adotado: não atende "autorizar cada tool call".

## Consequências

Dependência `pyjwt[crypto]`. Duas quebras documentadas no CHANGELOG: `POST /messages` exige token e `/v1/sessions` dá lugar a `/v1/auth/token`. A demo continua subindo sem edição (senhas fictícias no `.env.example`), e a API avisa quando valores de exemplo estão em uso; exposição externa exige trocá-los. A auditoria cresce uma linha por tool call. Retorno: tag v0.6.0 e migração 0009 descendente.

**Atualização da v0.13.0** ([ADR 0025](0025-identidade-e-operacao.md)): a interface entra por authorization code com PKCE e renova o acesso por refresh rotativo; o `password` fica para o smoke e a CLI. Emissores OIDC externos entram por `OIDC_ISSUERS`, ao lado do emissor próprio, com grupos mapeados para papéis e os escopos do papel; `JWT_JWKS_URL` continua trocando o emissor próprio por um que assine no formato do assistente.

## Data

2026-11-03
