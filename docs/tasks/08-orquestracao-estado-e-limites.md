# Tarefa: Orquestração, estado e limites

## Objetivo

Montar o grafo com estado tipado e nós provisórios para todas as rotas, a interface de modelo com cliente programado, limites por requisição, guarda de orçamento persistente, prompts versionados e traces por etapa.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RF-05, RF-24, RF-25, RF-26, RF-27, CA-12, CA-15. Decisões [0002](../architecture/decisions/0002-orquestracao-langgraph-estado-tipado.md) e [0005](../architecture/decisions/0005-modelos-openai-e-guarda-de-orcamento.md).

## Pré-condições

- Tarefa 04 concluída; decisões 0002 e 0005 aceitas.

## Arquivos prováveis

- `src/merchant_assistant/orchestration/` (grafo, estado, limites, orçamento)
- `src/merchant_assistant/llm/` (interface, cliente programado, cliente OpenAI, preços)
- `src/merchant_assistant/observability/` (logs, traces)
- `prompts/`
- `tests/integration/test_graph_routes.py`, `tests/unit/test_budget.py`

## Passos

1. Estado tipado com requisição, contexto do cliente, decisão do Router, resultados dos especialistas, encaminhamento, resposta final, orçamento e trace.
2. Grafo com as sete rotas do plano e nós provisórios.
3. Limites de chamadas de modelo, de ferramenta e de tempo total por requisição.
4. Guarda de orçamento: registro persistente em `data/runtime/`, reserva pelo máximo de tokens antes da chamada, liquidação depois, bloqueio sem preço conhecido.
5. Carregador de prompts com `id` e `version`, registrados no trace.
6. Trace por nó (início, duração, tokens, custo, status) e logs JSON com `request_id`; `GET /traces/{request_id}` só em modo demonstração.
7. Ligar o orquestrador ao `POST /messages`.

## Critérios de conclusão

- [ ] Testes com modelo programado percorrem as sete rotas.
- [ ] Limite atingido gera resposta controlada.
- [ ] A reserva impede ultrapassar um teto simulado.
- [ ] O trace mostra cada etapa com duração.

## Validação

A preencher na execução.

## Status

```text
pendente
```
