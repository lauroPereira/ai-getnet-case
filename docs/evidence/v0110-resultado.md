# Resultado da v0.11.0

## Capacidades

- A avaliação verifica cada afirmação da resposta contra evidências recuperadas e páginas web citadas. O veredito `unsupported_claim` é calculado a partir das marcas por afirmação.
- A calibração compara as notas do responsável com as de um painel de dois modelos, registra as divergências e mede o juiz contra rótulos de referência adjudicados.
- A régua de jornadas combina verificações determinísticas e avaliação de conteúdo.
- A busca híbrida pode reordenar candidatos com um reranker; o controle `hybrid@36` mede a mesma profundidade de fusão sem o modelo.

## Decisões medidas

Os rótulos de referência das 36 respostas seladas combinam as notas do responsável e as de um painel de dois modelos (`claude-opus-5-5` e `gpt-6-luna`); as divergências foram adjudicadas a partir de propostas de um terceiro modelo (`gpt-6.1-sol`), aprovadas pelo responsável. No veredito das seladas, o responsável e o painel concordaram em 31 de 32 respostas (κ 0,871); 43 das 60 respostas tiveram ao menos um campo adjudicado. A regra de decisão foi escrita antes da medição: κ ≥ 0,6 e nenhum critério caindo mais de 0,05 no acordo ±1.

| Candidato | κ do veredito (36 respostas; IC 95%) | Acordo ±1: groundedness / factual correctness / relevance / usefulness | Custo por julgamento |
| --- | ---: | --- | ---: |
| `judge.v3` (base) | 0,538 (−0,04 a 0,89) | 0,944 / 0,917 / 0,972 / 0,917 | US$ 0,000398 |
| `judge.v5` | **0,647** (0,28 a 0,92) | **0,972 / 0,972 / 1,000 / 1,000** | US$ 0,000945 |

`judge.v5` atingiu κ ≥ 0,6 e nenhum critério caiu mais de 0,05 no acordo ±1, então passou a rubrica padrão. `judge.v3` e `judge.v4` continuam selecionáveis com `--rubric v3` e `--rubric v4`. Os prompts congelados `judge_claims.v1` e `judge.v5` foram preservados. O κ é recalculável a partir das planilhas e dos julgamentos versionados, sem chamada a modelo: [calibração](v0110-calibracao.md). O custo por julgamento do `judge.v3` foi medido sobre os 108 julgamentos do banco da campanha; sobre os 60 versionados, é US$ 0,000519.

| Split | `hybrid@36` nDCG@6 | `hybrid+rerank` nDCG@6 | Diferença |
| --- | ---: | ---: | ---: |
| Dev (19 perguntas) | 0,974 | 0,981 | +0,007 |
| Holdout de retrieval (25 perguntas, selado na v0.9.0) | 0,907 | 0,972 | +0,065 |

`RERANK=on` passou a configuração padrão com `RETRIEVAL_MODE=hybrid`; `RERANK=off` continua disponível como opção explícita. A tabela completa e as demais métricas estão em [v0.11.0 retrieval](v0110-retrieval.md). A decisão está registrada na [ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md).

## Validação

| Verificação | Resultado | Registro |
| --- | --- | --- |
| Revisão independente do ajuste do `judge.v5` | Apto; suíte num clone limpo com 2.391 aprovados e 1 pulado; 45 de 53 mutantes detectados | [Parecer](v0110-reviewer-v5i3b.md) |
| Campanha com modelos reais, desenvolvimento (44 casos e 4 conversas, 3 execuções, `judge.v3`, régua combinada) | 113 de 132 respostas aprovadas (régua literal: 121 de 132); 13 de 13 jornadas em cada execução (39 de 39); 4 de 4 conversas; p50 de 7,7 s e p95 de 14,2 s | [v0110-qa.md](v0110-qa.md) |
| Páginas citadas como evidência do juiz | 16 respostas julgadas com a página citada, 3 com o resumo da busca no lugar de uma página indisponível e 6 sem URL gravada | [v0110-qa.md](v0110-qa.md) |
| Holdout da v0.8.0 (25 casos, 3 execuções), rodado de novo para compor a amostra da calibração | 60 de 75 respostas aprovadas (régua literal: 64 de 75); afirmação sem suporte em 0,067 das respostas | [v0110-qa-holdout-v080.md](v0110-qa-holdout-v080.md) |
| Ajuste do `judge.v5` nas 24 respostas da v0.8.0 (conjunto de ajuste, fora das seladas) | 4 de 4 frases genéricas marcadas e 1 falso positivo na iteração 3, com a S04 adjudicada; critério de parada atingido | [v0110-v5-ajuste.md](v0110-v5-ajuste.md) |
| Calibração nas 36 seladas | κ 0,647 do `judge.v5` contra 0,538 do `judge.v3`; nas 60 respostas, 0,628 | [v0110-calibracao.md](v0110-calibracao.md) |

## Gasto

| Item | Gasto (US$) |
| --- | ---: |
| Campanha `v0110-qa` até o fim do ajuste do `judge.v5`: agente, juiz, páginas citadas, afirmações da amostra selada, ajuste e retrieval | 0,72301375 |
| Julgamento das 60 respostas da calibração pelo `judge.v5` (201 julgamentos) | 0,18991808 |
| **Total da campanha `v0110-qa`** (teto US$1,00) | **0,91293183** |

O membro `claude-opus-5-5` do painel de rotulagem custou US$4,02, pago fora do ledger da campanha.
