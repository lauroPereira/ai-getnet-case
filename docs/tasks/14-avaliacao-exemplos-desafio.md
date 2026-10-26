# Tarefa: Avaliação dos exemplos do desafio

## Objetivo

Criar o conjunto rotulado e o executor de avaliação, e produzir o primeiro relatório de qualidade, custo e latência.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): CA-01, CA-02, CA-04, CA-17. [Plano](../specs/assistente-multiagente-lojista-plano.md), seção Estratégia de testes.

## Pré-condições

- Tarefa 13 concluída.

## Arquivos prováveis

- `tests/scenarios/challenge_examples.jsonl`, `tests/scenarios/core_cases.jsonl`
- `src/merchant_assistant/evaluation/`, comando `eval` no CLI
- `docs/evidence/` (relatório da rodada)

## Passos

1. Rotular os 10 exemplos em inglês, as variantes em português e UC-12 a UC-18: rotas aceitas, ferramentas esperadas, fontes esperadas e critérios de resposta.
2. Separar casos de desenvolvimento e casos reservados.
3. Executor com modo programado (sem custo, usado nos testes) e modo real (pago, limitado pela reserva de avaliação).
4. Métricas: acerto de rota, Recall@k, verificação de números, rubrica de aderência e utilidade em amostra (juiz por modelo e revisão humana), completude do encaminhamento, latência p50/p95 e custo.
5. Relatório com configuração, amostra, resultado por caso e limitações, separando medição de meta.

## Critérios de conclusão

- [ ] Relatório gravado em `docs/evidence/`.
- [ ] Custo da rodada real dentro da reserva de avaliação.
- [ ] Defeitos encontrados registrados como tarefas.

## Validação

A preencher na execução.

## Status

```text
pendente
```
