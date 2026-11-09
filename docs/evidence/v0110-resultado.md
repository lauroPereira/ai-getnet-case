# Resultado da v0.11.0

## Capacidades

- A avaliação verifica cada afirmação da resposta contra evidências recuperadas e páginas web citadas. O veredito `unsupported_claim` é calculado a partir das marcas por afirmação.
- A calibração compara dois rotuladores, registra divergências e usa rótulos ouro nas comparações do juiz.
- A régua de jornadas combina verificações determinísticas e avaliação de conteúdo.
- A busca híbrida pode reordenar candidatos com um reranker; o controle `hybrid@36` mede a mesma profundidade de fusão sem o modelo.

## Decisões medidas

O responsável avaliou 36 respostas seladas. O segundo rotulador declarado foi um painel de modelos. As 130 propostas de adjudicação foram geradas por `gpt-6.1-sol` ultra e aceitas pelo responsável em lote.

| Candidato | κ do veredito (36 respostas; IC 95%) | Acordo ±1: groundedness / factual correctness / relevance / usefulness | Custo por julgamento |
| --- | ---: | --- | ---: |
| `judge.v3` (base) | 0,538 (−0,04 a 0,89) | 0,944 / 0,917 / 0,972 / 0,917 | US$ 0,000398 |
| `judge.v5` | **0,647** (0,28 a 0,92) | **0,972 / 0,972 / 1,000 / 1,000** | US$ 0,000945 |

`judge.v5` atingiu κ ≥ 0,6 e nenhum critério caiu mais de 0,05 no acordo ±1, então passou a rubrica padrão. `judge.v3` e `judge.v4` continuam selecionáveis com `--rubric v3` e `--rubric v4`. Os prompts congelados `judge_claims.v1` e `judge.v5` foram preservados.

| Split | `hybrid@36` nDCG@6 | `hybrid+rerank` nDCG@6 | Diferença |
| --- | ---: | ---: | ---: |
| Dev (19 perguntas) | 0,974 | 0,981 | +0,007 |
| Holdout (25 perguntas) | 0,907 | 0,972 | +0,065 |

`RERANK=on` passou a configuração padrão com `RETRIEVAL_MODE=hybrid`; `RERANK=off` continua disponível como opção explícita. A tabela completa e as demais métricas estão em [v0.11.0 retrieval](v0110-retrieval.md). A decisão está registrada na [ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md).
