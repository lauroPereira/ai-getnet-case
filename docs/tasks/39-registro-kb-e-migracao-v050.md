# Tarefa: registro da base e migração0007

## Objetivo

Persistir documentos, rascunhos, versões, ponteiro e eventos sem alterar fontes.

## Especificação relacionada

[Plano v0.5](../specs/base-versionada-v050-plano.md), RF-63–65 e CA-41.

## Pré-condições

Plano/API/migração aprovados. Base nos merges v0.4 registrados; dados sintéticos.

## Arquivos prováveis

`data/migrations.py`, novo registro KB, inicialização e testes de dados.

## Passos

1. Adicionar0007 e bootstrap idempotente da referência preservada.
2. Registrar origem/hash imutáveis e conteúdo congelado por versão.
3. Implementar revisão otimista/eventos e testar0006→0007→0006.

## Critérios de conclusão

- [ ] Tabelas novas isoladas, subida/descida preservam negócios e ledger.
- [ ] Oficial não vira editável; versão publicada imutável.
- [ ] Bootstrap não reconstrói/apaga coleção existente.

## Validação e status

Implementada pelo Developer r1. Migração aditiva `0007_kb_versions`, bootstrap idempotente sem rebuild da coleção e downgrade/upgrade exercitados em SQLite sintético; preservação dos registros legados verificada. QA e revisão independentes pendentes.
