# Tarefa: nó de replanejamento com orçamento de saltos

## Objetivo

Depois de `knowledge` e de `support`, um nó `replan` observa o resultado e decide o próximo passo (concluir, outro especialista, web, escalar ou esclarecer), por regra quando o caso é claro e por `replan.v1` só na ambiguidade, com orçamento de saltos e o motivo no trace.

## Especificação relacionada

[Spec v0.8.0](../specs/orquestracao-avaliacao-v080.md) (rascunho) — D1 a D8; [spec 0.2](../specs/evolucao-pos-feedback.md) RF-86 a RF-88, CA-49, UC-23; [plano](../specs/evolucao-pos-feedback-plano.md) decisões técnicas 9 a 11.

## Pré-condições

Spec v0.8.0 aprovada pelo responsável; v0.7.0 na `main`; branch `codex/v0.8.0-replan` aberta a partir da `main` atualizada no checkout principal (Time A). Não abrir `tests/scenarios/holdout_v080*`.

## Arquivos prováveis

`orchestration/graph.py` (nó e arestas do grafo de atendimento), `orchestration/state.py` (resumo observado, saltos), `orchestration/run.py` e `config.py` (`MAX_PLAN_HOPS`), `agents/replanner.py` (novo: regras e chamada), `prompts/replan.v1.md` (novo), `llm/scripted.py` (política programada), `data/scenarios/catalog.json`, `tests/scenarios/replan.jsonl` (novo), testes.

## Passos

1. Resumo observado por especialista: `evidence_sufficient`, `missing`, `needs_selection`, ferramentas com falha, `escalate`, saltos feitos, especialistas já usados e rota original.
2. Regras da D4 numa função pura, cada uma com nome; `replan.v1` (saída estruturada `next`, `reason`, `review`; esforço `none`, ≤ 80 tokens) só quando nenhuma regra se aplica ou duas se contradizem.
3. Nó `replan` no lugar de `_after_knowledge` e `_after_support`; D5 (cada especialista uma vez) e D6 (`MAX_PLAN_HOPS=3`, no limite `finish` com a lacuna declarada). Grafo de retomada inalterado (D3).
4. Passo de trace `replan` com os campos da D7; `GET /v1/runs/{id}` o mostra sem mudar o contrato existente.
5. Os quatro cenários do RF-88 em `tests/scenarios/replan.jsonl` e no catálogo (`SC-REPLAN-*`), com a política programada; regressão dos 40 casos e das 4 conversas.
6. Proposta da ADR 0019 (replanejamento) com o desenho, as regras e o plano B.

## Critérios de conclusão

- [ ] Cada regra tem teste; o modelo só é chamado na ambiguidade (teste conta as chamadas).
- [ ] Laço forçado (especialistas que nunca resolvem) termina em ≤ 3 saltos sem repetir especialista.
- [ ] Os quatro cenários passam com modelo programado; o trace mostra `next`, `reason`, `review`, `hops` e `origin`.
- [ ] Pergunta simples não ganha chamada a mais (ledger e trace).
- [ ] 40 casos e 4 conversas sem piora contra a v0.7.0 no eval programado, salvo diferença justificada caso a caso.
- [ ] Suíte estrita com código 0; nenhuma chamada paga.

## Validação

A preencher pelo Developer.

## Status

```text
pendente (aguarda aprovação da spec v0.8.0)
```
