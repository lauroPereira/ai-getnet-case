# Tarefa 96 — Documentação da v0.12.0

## Objetivo

Documentar no produto as capacidades de memória de conversa, ablação do replanejamento, cancelamento com confirmação e a decisão de orquestração.

## Especificação relacionada

[Memória de conversa, ablação do replanejamento e escrita com confirmação — v0.12.0](../specs/memoria-escrita-v0120.md): CA-65, CA-66, CA-67 e CA-75. Plano: [roadmap v0.11.0 a v1.0.0](../specs/roadmap-v0110-v100-plano.md).

## Arquivos prováveis

`README.md`, `CHANGELOG.md`, `pyproject.toml`, `src/merchant_assistant/__init__.py`, tests e `docs/contracts/api-v1.md`.

## Passos

1. Documentar comportamento, configuração, campos de API, escopos e migração no README e no contrato.
2. Resumir as capacidades do produto no changelog e registrar a base da v0.11.0.
3. Alinhar a versão do pacote e da API em 0.12.0 e as asserções ao esquema 14.
4. Manter a descrição da confirmação, dos estados e dos limites das ferramentas de modelo consistente com o código.

## Critérios de conclusão

- README e CHANGELOG descrevem o comportamento v0.12 sem referências de custo desatualizadas.
- Metadados do pacote, `/ready`, migração e testes concordam em app 0.12.0 e schema 14.
- Links documentais funcionais e contrato coerente com a implementação.
