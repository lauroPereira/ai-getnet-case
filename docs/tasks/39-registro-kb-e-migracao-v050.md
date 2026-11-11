# Tarefa: registro da base e migração 0007

## Objetivo

Persistir documentos, rascunhos, versões, ponteiro e eventos sem alterar fontes.

## Especificação relacionada

[Plano v0.5](../specs/base-versionada-v050-plano.md), RF-63–65 e CA-41.

## Pré-condições

Plano, API e migração aprovados; dados sintéticos.

## Arquivos prováveis

`data/migrations.py`, novo registro KB, inicialização e testes de dados.

## Passos

1. Adicionar 0007 e bootstrap idempotente da referência preservada.
2. Registrar origem/hash imutáveis e conteúdo congelado por versão.
3. Implementar revisão otimista/eventos e testar 0006→0007→0006.

## Critérios de conclusão

- [x] Tabelas novas isoladas, subida/descida preservam negócios e ledger.
- [x] Oficial não vira editável; versão publicada imutável.
- [x] Bootstrap não reconstrói/apaga coleção existente.

## Resultado

Migração aditiva `0007_kb_versions` e bootstrap idempotente sem reconstruir a coleção; descida e subida exercitadas em SQLite sintético, com os registros legados preservados. Suíte estrita do backend: 293 testes. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
