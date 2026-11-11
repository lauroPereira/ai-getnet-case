# Resultado da v0.9.0

Experimento do juiz e retrieval híbrido. Spec: [juiz-retrieval-v090.md](../specs/juiz-retrieval-v090.md); história: [juiz-retrieval-v090.md](../historias/juiz-retrieval-v090.md); ADRs [0020](../architecture/decisions/0020-retrieval-hibrido-holdout.md) e [0021](../architecture/decisions/0021-juiz-modelo-e-regua.md).

## Capacidades

- Juiz Anthropic opcional (`JUDGE_PROVIDER=anthropic`, `claude-opus-5-5`) com saída estruturada por esquema JSON; recusa e limite de tokens viram julgamento falho, nunca nota, e cada julgamento grava os tokens usados.
- `eval --judge-repeat N --only-sample <csv> --name <execução>` julga de novo só a amostra de calibração; `eval-calibrate --judge --judge-run` compara outro juiz com as mesmas notas humanas, lado a lado com o juiz original, com consistência, tokens e custo.
- Busca híbrida: BM25 em processo, fundido à busca densa por RRF; `RETRIEVAL_MODE=dense|hybrid`, com `dense` idêntico à v0.8.0.
- Reranker opcional (`RERANK=on`) sobre os 12 primeiros resultados da fusão; qualquer falha devolve o resultado sem reranker.
- Holdout de retrieval selado `retrieval_holdout_v090` (25 perguntas, 13 em português, relevância graduada por chunk) e `eval-retrieval` com Recall@6, MRR, nDCG@6 e tempo por consulta.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte estrita | 2.107 testes aprovados (1 pulado por ambiente), Ruff e skills limpos; candidato final [r2](v090-candidato-r2.json) |
| Revisão independente | Tarefas 79, 80 e 81 aptas ([79](v090-reviewer-t79.md), [80](v090-reviewer-t80.md), [81](v090-reviewer-t81.md)) |
| Experimento do juiz (24 respostas calibradas, 3 julgamentos cada) | `claude-opus-5-5`: 72 de 72 julgamentos válidos; acordo ±1 com o humano de 0,958 / 0,958 / 1,000 / 0,958, contra 0,833 / 0,833 / 1,000 / 0,917 do DeepSeek; acordo no veredito 0,875, contra 0,667; 1 das 4 frases genéricas marcada ([relatório](v090-juiz-opus.md), [validação](v090-qa-juiz-r2.md)) |
| Retrieval com embeddings reais | nDCG@6 em dev 0,868 / 0,974 / 0,981 (dense / hybrid / hybrid + reranker); no holdout 0,880 / 0,921 / 0,961, com MRR 0,871 / 0,920 / 0,980 e 584 / 534 / 2.392 ms por consulta ([retrieval](v090-retrieval.md), [validação](v090-qa-retrieval-r1.md)) |
| Modo híbrido pela API | Três perguntas reais com o padrão novo (sem evidência nas páginas, fora de domínio, termo exato), todas conformes; na pergunta sem evidência, o assistente declarou a lacuna e não inventou valor, prazo nem condição ([validação](v090-qa-hybrid-r1.md)) |

## Gasto

| Item | US$ |
| --- | ---: |
| Juiz `claude-opus-5-5`, ledger Anthropic separado (teto US$4,00) | 1,340532 |
| Seis medições de retrieval | 0,01618986 |
| Modo híbrido pela API, ledger isolado | 0,02404412 |
| **Total** | **1,38076598** |

## Decisão

- **Retrieval** ([ADR 0020](../architecture/decisions/0020-retrieval-hibrido-holdout.md)): o híbrido foi melhor nos dois splits e passou a padrão. O reranker ficou desligado por padrão, porque o ganho medido incluía o efeito da fusão mais profunda (36 candidatos em vez de 18) e o tempo por consulta quadruplicava; na v0.11.0, o controle `hybrid@36` na mesma profundidade levou ao `RERANK=on` ([v0110-resultado.md](v0110-resultado.md)).
- **Juiz** ([ADR 0021](../architecture/decisions/0021-juiz-modelo-e-regua.md)): pela regra escrita antes (D2), a diferença nas frases genéricas é de rubrica, não de modelo, e o DeepSeek continuou como juiz padrão. O Opus custa 54 vezes mais por julgamento (US$0,0178 contra US$0,00033).
