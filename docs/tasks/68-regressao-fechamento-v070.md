# Tarefa: regressão integrada e preparação da validação real da v0.7.0

## Objetivo

Provar, com modelo programado, a história inteira de ponta a ponta sobre as tarefas 63 a 66b integradas (assistente e ticketing), e deixar a campanha `v070-qa` pronta para a validação real.

## Especificação relacionada

[Spec v0.7.0, versão 2](../specs/identidade-hitl-v070.md) (critérios e prova), [história](../historias/identidade-hitl-v070.md), [plano](../specs/evolucao-producao-v070-v0100-plano.md) tarefa 68 e "Estratégia de testes".

## Pré-condições

Tarefas 63 a 66 e 66b com revisão apta e integradas. Documentação de fechamento (evidência, README, CHANGELOG, ADRs aceitas, merge) fica fora desta tarefa.

## Arquivos prováveis

`tests/integration/` (história programada), `evaluation/` ou `cli.py` só se a regressão real precisar de token, `orchestration/budget.py` só se a campanha de US$0,20 não montar, `pyproject.toml` (versão `0.7.0`), testes.

## Passos

1. Teste de integração programado que percorre os momentos da história com o assistente e o ticketing reais em processo (transporte HTTP de teste entre os dois, sem rede externa) e dois processos para o reinício.
2. Conferir que `eval` sobre os 40 casos e `followup` roda no caminho da versão.
3. Conferir que a campanha `v070-qa` monta com teto de US$0,20 uma única vez combinada com o ledger primário (teste sem rede).
4. Versão do pacote `0.7.0`; `docker compose config` válido com os serviços `api`, `ticketing`, `mocks` e `qdrant`.

## Critérios de conclusão

- [x] CA-46, CA-47 e CA-48 cobertos pelo teste da história, além dos testes de cada tarefa.
- [x] Suíte estrita com código 0; nenhuma chamada paga.
- [x] Campanha `v070-qa` montável com US$0,20 (teste).

## Resultado

Teste da história com assistente e ticketing reais em processo e dois processos para o reinício; `eval` dos 40 casos e do `followup` no caminho da versão; campanha `v070-qa` montável com US$0,20; versão 0.7.0. Suíte estrita do candidato: 640 testes. Validação real: desafio 10/10, núcleo 17/17, conversas 4/4, campanha de US$0,10140195. Evidência: [resultado da v0.7.0](../evidence/v070-resultado.md).

## Status

```text
concluída (v0.7.0)
```
