# Medição de retrieval (`eval-retrieval`)

Embeddings: `text-embedding-3-small`. k = 6. Relevância: `dev` por documento (qualquer um dos rotulados; nDCG com um alvo só), `holdout_v090` por chunk com grau (2 a passagem correta, 1 também relevante).

`hybrid+rerank`: o modelo reordena os 12 primeiros de uma fusão de profundidade 36, contra 18 do `hybrid`; numa consulta em que o reranker falha, a resposta é a do `hybrid`. `hybrid@36` é o controle: a mesma fusão cortada em k pela ordem do RRF, sem modelo.

Piso BM25: hits achados só pelo BM25 com score (sobre o maior score BM25 da consulta) abaixo do piso saem antes da fusão; `0` é desligado. A coluna Descartados soma esses hits em todas as consultas.

| Split | Configuração | Piso BM25 | n | Recall@6 | MRR | nDCG@6 | Tempo médio (ms) | Execuções | Falhas do reranker | Descartados |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | dense | — | 19 | 0.895 | 0.860 | 0.868 | 438.7 | 1 | — | — |
| dev | hybrid | 0 | 19 | 1.000 | 0.965 | 0.974 | 391.6 | 1 | — | — |
| dev | hybrid@36 | 0 | 19 | 1.000 | 0.965 | 0.974 | 398.4 | 1 | — | — |
| dev | hybrid+rerank | 0 | 19 | 1.000 | 0.974 | 0.981 | 1833.5 | 1 | 0 de 19 | — |
| holdout_v090 | dense | — | 25 | 1.000 | 0.871 | 0.880 | 419.9 | 1 | — | — |
| holdout_v090 | hybrid | 0 | 25 | 1.000 | 0.920 | 0.921 | 501.1 | 1 | — | — |
| holdout_v090 | hybrid@36 | 0 | 25 | 0.960 | 0.913 | 0.907 | 390.6 | 1 | — | — |
| holdout_v090 | hybrid+rerank | 0 | 25 | 1.000 | 1.000 | 0.972 | 1751.6 | 1 | 0 de 25 | — |

Ganho próprio do reranker (`hybrid+rerank` menos `hybrid@36`, mesma profundidade de fusão, sem piso):

| Split | Diferença Recall@6 | Diferença MRR | Diferença nDCG@6 |
| --- | --- | --- | --- |
| dev | +0.000 | +0.009 | +0.007 |
| holdout_v090 | +0.040 | +0.087 | +0.065 |

Holdout de retrieval: usado, lacre `a23850aa6692…` conferido.

Padrão de retrieval decidido na [ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md) (D7): `RETRIEVAL_MODE=hybrid`, `RERANK=on`; `RERANK=off` continua disponível como opção explícita.
