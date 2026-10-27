# Tarefa: Referência da v0.1.0, changelog e migrações

## Objetivo

Fixar a entrega inicial como `v0.1.0`, criar o changelog e a infraestrutura de migrações reversíveis antes de qualquer mudança de dados.

## Especificação relacionada

[Especificação complementar](../specs/incrementos-pos-nucleo.md): RF-38, RF-39, RF-40, CA-27. [Decisão 0006](../architecture/decisions/0006-versionamento-changelog-e-migracoes.md).

## Pré-condições

- Especificação complementar e decisão 0006 aprovadas.
- Autorização do responsável para criar a tag `v0.1.0` na `main` (Q8).

## Arquivos prováveis

- `CHANGELOG.md` (novo)
- `src/merchant_assistant/data/migrations/` (novo), `data/db.py`
- `src/merchant_assistant/orchestration/graph.py` (`readiness` com versões)
- `tests/unit/data/test_migrations.py`

## Passos

1. Criar a tag `v0.1.0` no commit de merge do PR #1, com a autorização registrada.
2. Escrever `CHANGELOG.md` com a v0.1.0 (funcionalidades, contratos, dados, validação, limitações) e a seção "Não publicado".
3. Converter o esquema atual na migração `0001_core` e criar `schema_version`, com `up` e `down`.
4. Expor em `/ready` as versões do pacote, do esquema, do índice e dos prompts.
5. Testar subida e descida das migrações e a recriação do ambiente sintético.

## Critérios de conclusão

- [ ] `git checkout v0.1.0` reproduz a entrega inicial.
- [ ] Migrações sobem e descem sem perda dos dados sintéticos recriáveis.
- [ ] `/ready` mostra as versões.

## Validação

A preencher na execução.

## Status

```text
pendente
```
