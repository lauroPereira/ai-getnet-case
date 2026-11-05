# 0020. Retrieval híbrido (BM25 + denso com RRF), reranker opcional e holdout de retrieval lacrado

## Título

Acrescentar busca lexical ao índice de conhecimento, fundi-la com a busca densa por RRF e medir os modos num holdout de retrieval lacrado antes de escolher o padrão; reranker só se melhorar nDCG@6 nos dois conjuntos.

## Status

**Proposta** (v0.9.0, 2026-11-05; implementada nas tarefas 80 e 81 da branch `codex/v0.9.0-juiz-retrieval`; a aceitar no fechamento da versão com os números do QA real, tarefa 82). Spec: [juiz-retrieval-v090.md](../../specs/juiz-retrieval-v090.md), D7 e D8.

## Contexto

O avaliador (feedback V4) apontou que o retrieval era só denso (`text-embedding-3-small` + Qdrant, top-6 por cosseno), medido num conjunto de 14 perguntas usado durante o desenvolvimento, sem holdout, sem BM25 + denso, sem RRF e sem reranker (RF-94 a RF-96). Busca densa é boa em paráfrase e fraca em termo exato (código, sigla, nome raro); busca lexical é o oposto. A escolha do modo padrão precisa ser feita com número, num conjunto que ninguém usou para ajustar.

Restrições: o modo denso atual é o que todas as respostas avaliadas da v0.8.0 usaram e não pode mudar de resultado; o Knowledge não muda de comportamento com o padrão; nenhum dado real; custo de avaliação em centavos.

## Decisão

- **Lexical:** BM25 em processo (`rank-bm25`) sobre os mesmos chunks do índice denso ativo; tokenização com minúsculas, sem acentos, stopwords curtas pt/en versionadas, códigos e siglas preservados. O índice é persistido por `sha256` do corpo (`bm25-<hash>.pkl`, só ids e tokens; payload, URL e tipo de fonte vêm sempre do índice ativo) e reconstruído só quando o hash muda; construção concorrente protegida por trava e arquivo temporário único.
- **Fusão:** RRF com `k=60` sobre os `3×k` primeiros de cada lista, desempate pelo denso, `origin` por item (`dense`, `bm25`, `both`). `min_score` vale só para a lista densa.
- **Modo:** `RETRIEVAL_MODE=dense|hybrid`; `search()` sem modo usa a configuração; `mode="dense"` é idêntico à v0.8.0 (175/175 resultados iguais na revisão).
- **Reranker:** `rerank.v1` (prompt versionado) no modelo do agente sobre os 12 primeiros de uma fusão a 36, saída estruturada com a ordem; `RERANK=on|off`, padrão `off`, só com `hybrid`; qualquer falha devolve exatamente o resultado de `off`; medido pelo `Meter` da requisição e contado em `max_model_calls`.
- **Holdout de retrieval:** `tests/scenarios/retrieval_holdout_v090.jsonl`, 25 perguntas (13 pt), passagem correta por `chunk_id` com grau 2 e vizinhas com grau 1, escrito antes de medir qualquer modo e lacrado por `sha256` (relacrado uma vez após a revisão dos rótulos, ainda sem medição). Medido uma vez por configuração, por último; depois disso é "já visto".
- **Métricas:** Recall@6, MRR e nDCG@6 (ganho linear no holdout; alvo único em `dev`), tempo por consulta, falhas do reranker.
- **Regra do padrão (D7, escrita antes da medição):** `hybrid` vira padrão se o nDCG@6 for estritamente maior que o denso em `dev` e no holdout; `RERANK=on` só se o híbrido+reranker for estritamente maior que o híbrido nos dois e não houver falha do reranker. A linha "modo padrão sugerido" do relatório aplica a regra; a decisão é registrada aqui com os números.

## Alternativas consideradas

- **Só denso com embedding maior:** não resolve termo exato e custa mais por consulta; descartado.
- **BM25 no Qdrant (sparse vectors):** exigiria reindexar e mudar o cliente; o índice em processo é suficiente para 145 chunks e reprodutível; descartado nesta versão.
- **Reranker ligado por padrão:** adiciona uma chamada de modelo por pergunta de conhecimento; só se justifica com ganho medido nos dois conjuntos (RF-96); descartado como padrão.
- **Medir no conjunto `dev` apenas:** é o que o avaliador criticou; descartado.

## Consequências

- Positivas: termo exato passa a ser encontrado (com embeddings de hash, 5/5 contra 0/5 do denso); decisão do padrão com holdout e regra prévia; modo denso preservado byte a byte.
- Negativas e limitações: no modo híbrido o atalho "sem evidência" do Knowledge só dispara quando o BM25 também não acha nada, e o `score` do trace muda de escala (RRF); itens achados só pelo BM25 não têm piso de score; os rótulos do holdout foram escritos pelo Developer (IA) e revisados em contexto frio, não por pessoa; 25 perguntas é um conjunto pequeno; o "já visto" só é contado no mesmo arquivo de relatório.
- Resultado da medição real: (a preencher na aceitação, tarefa 82, a partir de `docs/evidence/v090-retrieval.md`).

## Data

2026-11-05 (proposta). Aceitação: (a preencher).
