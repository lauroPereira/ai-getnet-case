# 0002. Orquestração com LangGraph e estado tipado

## Título

Orquestrar os agentes com LangGraph, comunicando-se por chamadas diretas sobre um estado compartilhado tipado.

## Status

```text
aceita
```

Aceita pelo responsável em 2026-10-26.

## Contexto

O desafio exige pelo menos três agentes e um mecanismo claro de comunicação entre eles (chamadas diretas, fila interna ou eventos). O fluxo mistura etapas determinísticas (guardrail de entrada, prefixo de suporte, verificação de saída, persistência do encaminhamento) e etapas guiadas por modelo (Router, Knowledge, Customer Support, Escalation). A rota combinada precisa que dois especialistas contribuam na mesma requisição, e cada requisição tem limites de chamadas, tempo e custo.

## Decisão

Um grafo LangGraph define nós e transições. Cada agente é uma função que lê e escreve campos de um estado Pydantic tipado; não há fila nem barramento de eventos. O Router decide a rota; as arestas condicionais do grafo aplicam essa decisão depois da validação. Limites e orçamento são verificados antes de cada nó que chama modelo.

## Alternativas consideradas

- **Funções Python encadeadas sem framework:** mais simples, mas reimplementaria transições condicionais, estado e limites de recursão.
- **Fila interna ou eventos:** desacoplamento desnecessário para um único processo; dificulta testes e rastreio.
- **Agentes autônomos que se chamam livremente (ex.: handoffs de SDK de agentes):** menos previsível e mais difícil de limitar e testar.

## Consequências

O caminho de cada requisição é explícito e testável com modelo programado. A dependência do LangGraph fica restrita ao módulo de orquestração, pois os agentes são funções puras sobre o estado. Mudanças de fluxo exigem alterar o grafo e seus testes.

## Data

2026-10-26
