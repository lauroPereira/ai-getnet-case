# Tarefa 90 — Retrieval `hybrid@36`, piso BM25 e régua combinada das jornadas

## Objetivo

Medir o ganho próprio do reranker contra um controle na mesma profundidade, dar um piso aos hits só de BM25, e fazer as jornadas passarem pela régua combinada (determinística para o binário, juiz para o conteúdo).

## Especificação relacionada

[Juiz por afirmação, evidência da web e retrieval — v0.11.0](../specs/juiz-retrieval-v0110.md): D7, D8, CA-63, CA-64. Base: `rag/index.py` (`search(mode)`, fusão RRF), `rag/bm25.py`, `rag/rerank.py`, `evaluation/retrieval.py`, `cli.py` (`eval-retrieval`), `evaluation/scripted_policy.py`, `tests/scenarios/business_journeys.jsonl`. [ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md) registra a promoção atual; [ADR 0020](../architecture/decisions/0020-retrieval-hibrido-holdout.md) documenta a escolha inicial do modo híbrido.

## Pré-condições

O conjunto de holdout é selado; `eval-retrieval --fake` deve recusá-lo.

## Arquivos prováveis

`rag/index.py` (modo `hybrid@36`; piso `bm25_min_score` antes da fusão), `config.py` (`RETRIEVAL_BM25_MIN_SCORE`, padrão 0), `evaluation/retrieval.py` e `cli.py` (modo novo; tabela com quatro modos e coluna do piso), `evaluation/scripted_policy.py` (colunas `deterministic` e `content`), `scenarios.py`/rótulos (frases obrigatórias migram para afirmações a conferir), relatório de jornadas, testes.

## Passos

1. **`hybrid@36`.** `search(mode="hybrid@36")`: fusão RRF com profundidade 36 (a mesma que o reranker recebe), corte em `k` sem modelo. `eval-retrieval --mode hybrid@36` aceito nos dois splits; relatório lado a lado `dense | hybrid | hybrid@36 | hybrid+rerank` com Recall@6, MRR e nDCG@6, e a diferença `hybrid+rerank − hybrid@36` como "ganho próprio do reranker".
2. **Piso BM25.** `RETRIEVAL_BM25_MIN_SCORE` (float, padrão 0 = desligado): hit presente só na lista BM25 com score normalizado abaixo do piso é descartado antes da fusão; registrado no trace do passo `knowledge` (`bm25_dropped`). `eval-retrieval --bm25-min-score X` para medir; a tabela ganha a coluna.
3. **Régua combinada.** No relatório de jornadas, `deterministic` = rota, status, ferramentas, valores, fontes e frases proibidas registradas (como hoje, sem as frases obrigatórias); `content` = julgamento do juiz padrão sobre a resposta gravada (≥ 4 em `factual_correctness` e `relevance`, `unsupported_claim` falso); `passed = deterministic and content`; `--rubric literal` mantém a régua antiga para comparação. As frases obrigatórias dos rótulos viram `expected_claims` que o relatório lista ao lado do veredito do juiz (informativo). Rótulos não mudam de conteúdo nesta tarefa; só de campo.
4. **Testes:** `hybrid@36` igual a `hybrid` quando k = 36 e diferente do reranker programado; piso descarta só hits exclusivos do BM25; trace registra; tabela com quatro modos; `--fake` recusado no holdout; régua combinada com juiz programado: paráfrase correta passa, paráfrase com valor errado reprova pelo determinístico, frase genérica reprova pelo conteúdo; `--rubric literal` reproduz o relatório anterior.

## Critérios de conclusão

- Modo `hybrid@36` e piso medíveis nos dois splits; tabela com a coluna do ganho próprio.
- Jornadas com as duas colunas e `passed` combinado; régua literal disponível por flag.
- A configuração padrão é `RETRIEVAL_MODE=hybrid`, `RERANK=on`; `RERANK=off` continua disponível para usar a ordem da fusão.

## Resultado

No holdout, `hybrid@36` teve nDCG@6 0,907 e `hybrid+rerank` 0,972 (+0,065, o ganho próprio do reranker); `RERANK=on` passou a padrão. Jornadas com a régua combinada e a literal disponível por flag.
Evidência: [retrieval da v0.11.0](../evidence/v0110-retrieval.md) e [resultado da v0.11.0](../evidence/v0110-resultado.md).

## Status

```text
concluída (v0.11.0)
```
