# Tarefa 80 — Retrieval híbrido BM25 + RRF

## Objetivo

Acrescentar busca lexical (BM25) ao índice de conhecimento e fundi-la com a busca densa por RRF, selecionável por `RETRIEVAL_MODE`, sem mudar o resultado do modo denso atual.

## Especificação relacionada

[Juiz Claude e retrieval híbrido v0.9.0](../specs/juiz-retrieval-v090.md): D7, D10, CA-52; especificação 0.2 RF-94. Plano: decisões técnicas 17 a 19 em [evolucao-pos-feedback-plano.md](../specs/evolucao-pos-feedback-plano.md).

## Pré-condições

Tarefa 79 commitada na branch (não precisa estar revisada). `rank-bm25` adicionado a `pyproject.toml`.

## Arquivos prováveis

`src/merchant_assistant/rag/index.py` (`KnowledgeIndex.search(query, k, mode=None)`), `rag/bm25.py` (novo: tokenização, índice, persistência), `rag/kb.py` ou onde o manifesto do índice é escrito (hash do corpus), `config.py` (`retrieval_mode`, só por acréscimo), `cli.py` (`eval-retrieval --mode`), `tests/unit/rag/`, `tests/integration/`.

## Passos

1. **Tokenização.** Minúsculas, remoção de acentos, separação por não alfanuméricos, stopwords curtas pt/en versionadas no módulo; códigos e siglas preservados como tokens (`MDR`, `E-1023`).
2. **Índice BM25.** Construído sobre os mesmos chunks do índice denso ativo, persistido em `runtime/bm25-<hash>.pkl` onde `<hash>` é o sha256 do corpus (ids e textos ordenados); reconstruído quando o hash muda; o manifesto do índice registra o hash e o modo disponível.
3. **Fusão.** RRF com `k=60` sobre os `3×k` primeiros de cada lista; empate resolvido pelo denso; `search(mode="hybrid")` devolve o mesmo tipo de resultado do denso, com `score` e `origin` (`dense`, `bm25`, `both`) por item para o trace.
4. **Modo.** `RETRIEVAL_MODE=dense|hybrid` (padrão `dense` até a decisão D7); `search()` sem `mode` usa a configuração; teste de equivalência: `mode="dense"` devolve exatamente o resultado atual.
5. **CLI.** `eval-retrieval --mode dense|hybrid` mede Recall@6 e MRR no conjunto rotulado atual (`tests/scenarios/retrieval.jsonl`) com embeddings de hash nos testes; a saída diz o modo e o hash do BM25.
6. **Caso que o denso não acha.** Acrescente ao conjunto `dev` de retrieval pelo menos 3 perguntas com termo exato (código, sigla, nome raro) cuja passagem correta exista no corpus; registre na passagem o Recall@6 e o MRR dos dois modos com embeddings de hash (número de referência, não prova real).

## Critérios de conclusão

- `search(mode="dense")` idêntico ao atual em todos os testes existentes; o Knowledge não muda de comportamento com o padrão.
- `search(mode="hybrid")` acha as perguntas de termo exato que o denso não acha, nos testes programados.
- BM25 reconstruído só quando o hash do corpus muda; teste nos dois sentidos.
- `eval-retrieval --mode` roda sem rede; `lint_and_tests.py --strict` verde.

## Validação

(Preenchida pelo Developer.)

## Status

Pendente. Aberta pelo Supervisor em 2026-11-05.
