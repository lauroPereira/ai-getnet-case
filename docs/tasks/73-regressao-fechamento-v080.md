# Tarefa: regressão integrada e preparação do QA da v0.8.0

## Objetivo

Provar a história da v0.8.0 com modelo programado sobre as tarefas 69, 70, 71 e 72b integradas e deixar a campanha `v080-qa` pronta e estimada.

## Especificação relacionada

[Spec v0.8.0](../specs/orquestracao-avaliacao-v080.md) (rascunho), critérios e requisitos não funcionais; [história](../historias/orquestracao-avaliacao-v080.md); [plano](../specs/evolucao-pos-feedback-plano.md) tarefa 73 e "Estratégia de testes".

## Pré-condições

Tarefas 69, 70, 71 e 72b com parecer apto; branch do Time B integrada pelo Supervisor na branch da versão. Fechamento do Supervisor (evidência, README, CHANGELOG, ADR 0019 aceita, merge) fica fora desta tarefa.

## Arquivos prováveis

`tests/integration/` (história programada), `evaluation/` só se a campanha não montar, `pyproject.toml` e `__init__.py` (versão `0.8.0`), testes.

## Passos

1. Teste de integração programado dos momentos 1 a 9 da história: quatro cenários de replanejamento, laço evitado, pergunta simples sem chamada a mais, `eval --judge --repeat 3` com juiz programado de "outro provedor", holdout à parte e jornadas.
2. Campanha `v080-qa` montável com teto de US$0,50 uma única vez, combinada com o ledger primário (teste sem rede).
3. Estimador de custo da campanha a partir de N casos medidos (usado pelo QA antes de montar).
4. Versão `0.8.0`; `docker compose config` válido.

## Critérios de conclusão

- [ ] CA-49, CA-50 (parte determinística) e CA-51 (parte programada) cobertos pelo teste da história.
- [ ] Suíte estrita com código 0; nenhuma chamada paga.
- [ ] Campanha `v080-qa` montável com US$0,50 e estimativa reproduzível (teste).

## Validação

A preencher pelo Developer.

## Status

```text
pendente (aguarda aprovação da spec v0.8.0)
```
