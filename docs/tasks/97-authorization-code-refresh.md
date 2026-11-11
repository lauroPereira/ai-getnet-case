# Tarefa 97 — Login por redirecionamento e refresh token

## Objetivo

O emissor próprio passa a oferecer authorization code com PKCE e refresh token rotativo, e a interface loga por redirecionamento.

## Especificação relacionada

[v0.13.0](../specs/identidade-operacao-v0130.md): D1, CA-68. Plano: [decisão 14](../specs/roadmap-v0110-v100-plano.md). ADR 0017.

## Pré-condições

Emissor próprio e migração 0014 da v0.12.0 disponíveis. A migração 0015 estende a cadeia sem alterar o contrato existente de `password` e `client_credentials`.

## Arquivos prováveis

`api/identity.py`, `api/v1.py` (rotas de auth, aditivas), `data/migrations.py` (0015), `config.py` (clientes e `redirect_uri` registrados), página de login (HTML simples servido pela API), `.env.example`, testes. O cliente web usa PKCE, valida `state` e `iss` e troca/renova os tokens no servidor.

## Passos

1. Migração 0015 reversível: `auth_codes`, `refresh_tokens`, `api_principals.issuer`.
2. `GET /v1/auth/authorize` com cliente e `redirect_uri` registrados, PKCE S256 obrigatório, `state`; página de login; código de uso único com validade curta, guardado por hash.
3. `POST /v1/auth/token` com `authorization_code` (+ `code_verifier`) e `refresh_token` rotativo; reuso de refresh já usado revoga a família; revogação de refresh e de acesso pela rota existente.
4. `password` continua, marcado como demonstração no `/docs`.
5. Testes: PKCE certo e errado; código reusado; `redirect_uri` divergente; refresh rotativo; reuso revoga a família; expiração; escopos preservados; migração nos dois sentidos; contrato aditivo.

## Critérios de conclusão

- CA-68 (parte do emissor próprio) coberto por testes; suíte estrita verde.

## Resultado

Authorization code com PKCE S256 e refresh token rotativo, com revogação da família no reuso. Validado com 10 logins num navegador real: 10 sessões abertas, nenhum login órfão, código emitido num worker e trocado no outro.
Evidência: [resultado da v0.13.0](../evidence/v0130-resultado.md).

## Status

```text
concluída (v0.13.0)
```
