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

- [x] Relatório gravado em `docs/evidence/`.
- [x] Custo da rodada real dentro da reserva de avaliação.
- [x] Defeitos encontrados registrados. Foram corrigidos na própria tarefa (prompts `support` v3, texto de conta não localizada, verificação do EX03/PT03) e descritos na análise, sem tarefas separadas.

## Validação

2026-10-26: 27 casos rotulados (10 dev, 17 holdout), executor com modo programado e real, três rodadas reais com rubrica por modelo. Última rodada: 27/27 nas verificações automáticas, p50 7,8 s, p95 15,7 s, US$0,051. Ver [análise](../evidence/2026-10-26-avaliacao-analise.md) e [relatório](../evidence/2026-10-26-avaliacao-nucleo.md). Revisão humana de amostra pendente. Revisão não independente.

## Status

```text
concluída
```
