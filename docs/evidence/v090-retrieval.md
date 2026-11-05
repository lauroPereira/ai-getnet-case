# Medição de retrieval (`eval-retrieval`)

Embeddings: `text-embedding-3-small`. k = 6. Relevância: `dev` por documento (qualquer um dos rotulados; nDCG com um alvo só), `holdout_v090` por chunk com grau (2 a passagem correta, 1 também relevante).

`hybrid+rerank`: o modelo reordena os 12 primeiros de uma fusão de profundidade 36, contra 18 do `hybrid`; numa consulta em que o reranker falha, a resposta é a do `hybrid`.

| Split | Configuração | n | Recall@6 | MRR | nDCG@6 | Tempo médio (ms) | Execuções | Falhas do reranker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | dense | 19 | 0.895 | 0.860 | 0.868 | 457.0 | 1 | — |
| dev | hybrid | 19 | 1.000 | 0.965 | 0.974 | 624.3 | 1 | — |
| dev | hybrid+rerank | 19 | 1.000 | 0.974 | 0.981 | 2641.7 | 1 | 0 de 19 |
| holdout_v090 | dense | 25 | 1.000 | 0.871 | 0.880 | 584.3 | 1 | — |
| holdout_v090 | hybrid | 25 | 1.000 | 0.920 | 0.921 | 533.7 | 1 | — |
| holdout_v090 | hybrid+rerank | 25 | 1.000 | 0.980 | 0.961 | 2391.8 | 1 | 0 de 25 |

Holdout de retrieval: usado, lacre `a23850aa6692…` conferido.

Modo padrão sugerido (regra D7, a decisão é do Supervisor): RETRIEVAL_MODE=hybrid, RERANK=on (reranker com 0 falhas em 44 consultas; nDCG@6: dev: dense 0.868, hybrid 0.974, hybrid+rerank 0.981; holdout_v090: dense 0.880, hybrid 0.921, hybrid+rerank 0.961)
