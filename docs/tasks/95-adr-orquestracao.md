# Tarefa 95 — ADR 0024: desenho da orquestração

## Objetivo

Registrar por que a orquestração usa um grafo com plano inicial do Router e replanejamento por regras nomeadas, em vez de um supervisor com especialistas como ferramentas, incluindo tradeoffs e a condição para rever a escolha.

## Especificação relacionada

[v0.12.0](../specs/memoria-escrita-v0120.md): D4, CA-75. Plano: [decisão 12](../specs/roadmap-v0110-v100-plano.md). Base: ADR 0002, ADR 0019, `agents/replanner.py`, `orchestration/graph.py`.

## Arquivos prováveis

`docs/architecture/decisions/0024-desenho-da-orquestracao.md` e o índice de decisões.

## Passos

1. Descrever o grafo, limites de escopo e saltos, origem de cada decisão e garantias estruturais.
2. Comparar com um supervisor em laço de function calling, registrando ganhos e perdas de cada desenho.
3. Definir a condição de revisão ligada aos resultados pareados da tarefa 93 e incluir um diagrama dos dois desenhos.

## Critérios de conclusão

- ADR 0024 aceita e índice atualizado.
- Decisão e condição de revisão correspondem às capacidades e limites implementados.

## Resultado

[ADR 0024](../architecture/decisions/0024-desenho-da-orquestracao.md) aceita, com a comparação dos dois desenhos e a condição de revisão.

## Status

```text
concluída (v0.12.0)
```
