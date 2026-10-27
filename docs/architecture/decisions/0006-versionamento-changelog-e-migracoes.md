# 0006. Versionamento SemVer, changelog e migrações reversíveis

## Título

Versionar cada incremento com SemVer, tag no Git, `CHANGELOG.md` e migrações de dados numeradas e reversíveis.

## Status

```text
proposta
```

## Contexto

O núcleo foi entregue e validado (PR #1, commit `29a0088`). Os incrementos alteram contratos e dados e precisam de uma referência reproduzível e de um caminho de retorno. O template exige autorização para tags e publicação.

## Decisão

- Versão do pacote e tag `vX.Y.Z` por incremento; a entrega inicial recebe `v0.1.0` no commit validado.
- `CHANGELOG.md` no formato Keep a Changelog, com seções de funcionalidades, contratos, dados, validação, limitações e retorno.
- Migrações numeradas (`NNNN_nome.py` com `up` e `down`) e tabela `schema_version`; `/ready` informa versão do esquema, da base e dos prompts.
- Retorno: `git checkout vX.Y.Z`, migração `down` até a versão correspondente ou recriação do ambiente sintético.

## Alternativas consideradas

- **Só commits e tarefas:** não dá referência estável para avaliação nem retorno simples.
- **Ferramenta de migração externa (ex.: Alembic):** mais completa, mas pesada para SQLite sintético e poucas tabelas.

## Consequências

Cada versão fica auditável e reversível. Criar tag passa a ser parte de cada liberação, sempre com autorização. Migrações exigem teste de subida e descida.

## Data

2026-10-26
