# Tarefa 98 — Emissor OIDC externo

## Objetivo

A API aceita tokens de um emissor OIDC externo configurado (Dex no compose), com mapeamento de grupos para papéis e escopos.

## Especificação relacionada

[v0.13.0](../specs/identidade-operacao-v0130.md): D2, CA-68. Plano: [decisão 15](../specs/roadmap-v0110-v100-plano.md). ADR 0017.

## Pré-condições

Tarefa 97 concluída; migração 0015 e configuração do emissor próprio disponíveis.

## Arquivos prováveis

`api/identity.py` (`OIDC_ISSUERS`, descoberta, JWKS em cache, mapeamento de claims), `config.py`, `docker-compose.yml` (serviço `dex`, perfil `oidc`), `docker/dex/config.yaml` (usuários sintéticos estáticos, valores fictícios), `.env.example`, testes.

## Passos

1. `OIDC_ISSUERS` com um ou mais emissores; descoberta e JWKS com cache e renovação na troca de chave.
2. `groups` → papel; escopos pelo papel; principal com `issuer`.
3. `iss` desconhecido → `401 invalid_issuer`; assinatura, `aud`, `exp` e `nbf` conferidos.
4. Dex por perfil do compose com usuários sintéticos.
5. Testes com emissor falso em processo (chaves geradas no teste): token válido aceito; emissor desconhecido, assinatura errada, `aud` errado e expirado recusados; troca de chave; mapeamento de grupos.

## Critérios de conclusão

- CA-68 (parte do emissor externo) coberto por testes; suíte estrita verde; Dex só por perfil.

## Resultado

Tokens de emissores OIDC configurados aceitos e emissor desconhecido recusado; Dex validado no sistema com Docker.
Evidência: [resultado da v0.13.0](../evidence/v0130-resultado.md).

## Status

```text
concluída (v0.13.0)
```
