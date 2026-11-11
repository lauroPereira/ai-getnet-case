# Tarefa 93 — Ablação do replanejamento

## Objetivo

Medir o ganho do replanejamento no conjunto de casos, com e sem o nó `replan`, por critério e por rota.

## Especificação relacionada

[v0.12.0](../specs/memoria-escrita-v0120.md): D3, CA-66. Plano: [decisão 11](../specs/roadmap-v0110-v100-plano.md).

## Arquivos prováveis

`config.py`, `orchestration/graph.py`, `evaluation/runner.py`, `evaluation/compare.py`, `cli.py` e testes.

## Passos

1. Adicionar `REPLAN=on|off`, mantendo `on` como padrão. Com `off`, usar as arestas fixas da v0.7.0, preservar o plano inicial do Router e manter limites de chamadas e tempo.
2. Gravar a configuração nos relatórios de avaliação e oferecer `eval-compare` sem chamada de modelo.
3. Parear execuções por `case_id` e repetição; comparar critérios e rotas, calcular intervalo bootstrap da diferença e listar decisões `replan` de origem `model` com observação, candidatos e escolha. Separar resultados dos casos com decisão do modelo dos casos só com regras e listar itens sem par.
4. Testar os dois modos, o relatório pareado determinístico e o tratamento de casos sem par com modelo roteirizado.

## Critérios de conclusão

- CA-66 coberto por teste roteirizado e `REPLAN=on` permanece o padrão.
- O modo `off` não executa `replan` nem busca web e mantém os limites da requisição.

## Resultado

`REPLAN=on|off` e `eval-compare` pareado. Em 4 casos pareados: 0 decisões de origem `model` com `REPLAN=off` e 8 com `REPLAN=on`.
Evidência: [resultado da v0.12.0](../evidence/v0120-resultado.md).

## Status

```text
concluída (v0.12.0)
```
