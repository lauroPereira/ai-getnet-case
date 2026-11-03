# Tarefa: regressão integrada e preparação do QA da v0.7.0

## Objetivo

Provar, com modelo programado, a história inteira de ponta a ponta sobre as tarefas 63 a 66b integradas (assistente e ticketing), e deixar a campanha `v070-qa` pronta para o QA.

## Especificação relacionada

[Spec v0.7.0, versão 2](../specs/identidade-hitl-v070.md) (critérios e prova), [história](../historias/identidade-hitl-v070.md), [plano](../specs/evolucao-pos-feedback-plano.md) tarefa 68 e "Estratégia de testes".

## Pré-condições

Tarefas 63 a 66 e 66b com parecer apto; branch do Time B integrada pelo Supervisor na branch da versão. Fechamento do Supervisor (evidência, README, CHANGELOG, ADRs aceitas, merge) fica fora desta tarefa.

## Arquivos prováveis

`tests/integration/` (história programada), `evaluation/` ou `cli.py` só se a regressão real precisar de token, `orchestration/budget.py` só se a campanha de US$0,20 não montar, `pyproject.toml` (versão `0.7.0`), testes.

## Passos

1. Teste de integração programado que percorre os momentos da história com o assistente e o ticketing reais em processo (transporte HTTP de teste entre os dois, sem rede externa) e dois processos para o reinício.
2. Conferir que `eval` sobre os 40 casos e `followup` roda no caminho da versão.
3. Conferir que a campanha `v070-qa` monta com teto de US$0,20 uma única vez combinada com o ledger primário (teste sem rede).
4. Versão do pacote `0.7.0`; `docker compose config` válido com os serviços `api`, `ticketing`, `mocks` e `qdrant`.

## Critérios de conclusão

- [ ] CA-46, CA-47 e CA-48 cobertos pelo teste da história, além dos testes de cada tarefa.
- [ ] Suíte estrita com código 0; nenhuma chamada paga.
- [ ] Campanha `v070-qa` montável com US$0,20 (teste).

## Validação

A preencher pelo Developer.

## Status

```text
pendente
```
