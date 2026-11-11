# Tarefa: regressão integrada e preparação da campanha real da v0.8.0

## Objetivo

Provar a história da v0.8.0 com modelo programado sobre as tarefas 69, 70, 71 e 72b integradas e deixar a campanha `v080-qa` pronta e estimada.

## Especificação relacionada

[Spec v0.8.0](../specs/orquestracao-avaliacao-v080.md), critérios e requisitos não funcionais; [história](../historias/orquestracao-avaliacao-v080.md); [plano](../specs/evolucao-producao-v070-v0100-plano.md) tarefa 73 e "Estratégia de testes".

## Pré-condições

Tarefas 69, 70, 71 e 72b com revisão apta e integradas. Documentação de fechamento (evidência, README, CHANGELOG, ADR 0019 aceita, merge) fica fora desta tarefa.

## Arquivos prováveis

`tests/integration/` (história programada), `evaluation/` só se a campanha não montar, `pyproject.toml` e `__init__.py` (versão `0.8.0`), testes.

## Passos

1. Teste de integração programado dos momentos 1 a 8 da história: quatro cenários de replanejamento, laço evitado, pergunta simples sem chamada a mais, `eval --judge --repeat 3` e `--judge-repeat 3` com juiz programado de "outro provedor" e jornadas. O relatório separado por split é provado com um split sintético do teste; o `holdout_v080` real só roda na campanha real (D17).
2. Campanha `v080-qa` montável com teto de US$0,50 uma única vez, combinada com o ledger primário (teste sem rede).
3. Estimador de custo da campanha a partir de N casos medidos (usado antes de montar), com as duas etapas da D12 (agente 3 vezes; juiz 3 vezes sobre a primeira execução).
4. Roteiro da campanha real com o holdout como último passo técnico (D17).
5. Versão `0.8.0`; `docker compose config` válido.

## Critérios de conclusão

- [x] CA-49, CA-50 (parte determinística) e CA-51 (parte programada) cobertos pelo teste da história.
- [x] Suíte estrita com código 0; nenhuma chamada paga.
- [x] Campanha `v080-qa` montável com US$0,50 e estimativa reproduzível (teste).

## Resultado

Teste da história programado e campanha `v080-qa` estimável e montável; suíte estrita do candidato final: 1.997 testes. Pré-holdout: CA-49 com os quatro cenários 3/3; CA-51 13/13 nas três execuções pelo juiz e 13/13, 12/13 e 12/13 pela checagem determinística; smoke Docker 10/10. Holdout `holdout_v080` uma única vez: 62/75 (0,827). Campanha de US$0,84, mais US$0,03 do volume Docker. Evidência: [validação pré-holdout](../evidence/v080-d12-pre-holdout-r6.md), [holdout](../evidence/v080-holdout-r7.md) e [calibração](../evidence/v080-calibracao.md).

## Status

```text
concluída (v0.8.0)
```
