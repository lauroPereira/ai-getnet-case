# Tarefa 102 — Documentação e metadados da v0.13.0

## Objetivo

Documentar os contratos e a configuração das funcionalidades v0.13.0 e alinhar a versão do pacote, do aplicativo e dos testes de versão.

## Especificação relacionada

[Identidade e operação — v0.13.0](../specs/identidade-operacao-v0130.md): CA-68 a CA-72; [ADR 0025](../architecture/decisions/0025-identidade-e-operacao.md). Inclui as migrações 0015 e 0016 na cadeia iniciada pela migração 0014 da v0.12.0.

## Pré-condições

Funcionalidades das tarefas 97 a 101 e o mapeamento de usuários estáticos da tarefa 102a disponíveis.

## Arquivos prováveis

`README.md`, `CHANGELOG.md`, `docs/contracts/api-v1.md`, `docs/specs/identidade-operacao-v0130.md`, `docs/architecture/decisions/0025-identidade-e-operacao.md`, `.env.example`, `pyproject.toml`, `src/merchant_assistant/__init__.py` e testes de versão.

## Passos

1. Manter a ADR 0025, a especificação v0.13.0 e o contrato HTTP coerentes com a implementação e com as ADRs 0017, 0018 e 0022.
2. Descrever em inglês no README e no CHANGELOG o login por redirecionamento com PKCE, emissores OIDC configurados, operação com dois workers, recuperação e reenvio de webhooks, Telegram e exportação OTLP opcional.
3. Documentar no `.env.example` as configurações necessárias, com valores fictícios e integrações opcionais desligadas por padrão.
4. Alinhar `pyproject.toml` e `merchant_assistant.__version__` para 0.13.0 e as verificações de `/ready` para aplicativo 0.13.0 e schema 16.
5. Preservar migrações 0014, 0015 e 0016 em sequência e os arquivos selados de calibração e prompts da v0.11.0.

## Critérios de conclusão

- Contratos, especificação, ADR, configurações, README e CHANGELOG descrevem o mesmo comportamento final.
- `/ready` informa aplicativo 0.13.0 e schema 16; os testes preservam a cadeia de migração desde schema 14.
- Links e caminhos versionados são válidos e os hashes dos arquivos selados permanecem idênticos à base v0.12.0.
- Verificações focalizadas e suíte estrita cobrem os contratos e as regressões existentes.

## Resultado

`/ready` informa aplicação 0.13.0 e esquema 16; migrações 0015 e 0016 em sequência após a 0014, nos dois sentidos. Suíte estrita com 2.944 aprovados.
Evidência: [resultado da v0.13.0](../evidence/v0130-resultado.md) e [ADR 0025](../architecture/decisions/0025-identidade-e-operacao.md).

## Status

```text
concluída (v0.13.0)
```
