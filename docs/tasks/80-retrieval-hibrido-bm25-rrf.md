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

Developer, 2026-11-05, commits `5d82fd0` e `c99aa90` na `codex/v0.9.0-juiz-retrieval`. Passagem: [v090-developer.md](../evidence/v090-developer.md), seção "Tarefa 80".

- `rank-bm25>=0.2.2` em `pyproject.toml` (dependência normal) e instalado na `.venv` (`rank-bm25 0.2.2`, via `uv pip install`).
- Testes novos: 17 (`tests/unit/rag/test_bm25_hybrid.py`, 15; `tests/integration/test_v090_hybrid.py`, 2). Cobrem tokenização (acentos, stopwords, `MDR`, `E-1023`, `ADQ 4-91`), equivalência do denso (`search()` e `search(mode="dense")` contra a busca da v0.8.0, nas 19 perguntas, três combinações de `k`, filtro e `min_score`), modo vindo do índice e modo inválido recusado, `RETRIEVAL_MODE` com padrão `dense`, RRF (pontuação, `origin`, desempate pelo denso), filtro de fonte no híbrido, as perguntas de termo exato, BM25 reconstruído só quando o hash muda (nos dois sentidos, por `load_or_build` e pelo índice com `Bm25Index.build` proibido na segunda carga), cache descartado quando a coleção é substituída, `eval-retrieval --mode` sem rede, e o Knowledge respondendo no grafo nos dois modos com o modo mantido na versão ativa.
- Referência com embeddings de hash (não é prova real), 19 perguntas de `dev`: denso Recall@6 0,632 e MRR 0,500; híbrido Recall@6 1,000 e MRR 0,789. Nas 5 de termo exato: denso 0,000/0,000; híbrido 1,000/0,500. Nas 14 anteriores: denso 0,857/0,679; híbrido 1,000/0,893.
- `lint_and_tests.py --strict`: 2028 passed e 1 failed, 2029 no total (2012 da tarefa 79 + 17 novos). A falha é `test_v090_judge.py::test_moment_3_both_judges_against_the_same_human_ratings`, área da tarefa 79, causada por edição em andamento de outro escritor em `cli.py` durante a execução. Ruff sem achados; caminhos pessoais limpos (727 arquivos). No HEAD `7d1039f`, depois dos commits da rodada 2 da tarefa 79, esse arquivo e os testes da tarefa 80 passam (53 passed). Detalhe na passagem.
- Decisões além do texto e limites (`min_score` só na lista densa; `origin` não aparece no trace do Knowledge, que não mudou): na passagem.

**Rodada 2** (correções do [parecer da rodada 1](../evidence/v090-reviewer-t80.md), P2-1 a P2-3), Developer, 2026-11-05, commits `60ab2c8` e `687895c`. Passagem: seção "Tarefa 80 — rodada 2".

- P2-1: o arquivo do BM25 guarda só ids e estatísticas (formato 2); payload, URL, `collected_at` e `source_kind` vêm da leitura atual da coleção ativa; arquivos da rodada 1 são reconstruídos.
- P2-2: temporário único por processo, thread e chamada, com `os.replace`; um construtor por arquivo e por (cliente, coleção) no processo; escrita que falha responde da memória.
- P2-3: testes fixam `k=60`, os `3×k`, o `min_score` só na lista densa, a fiação do `main.py` e que `eval-retrieval --mode hybrid` mede o híbrido. `RETRIEVAL_MODE` comentado no `.env.example`.
- Testes novos: 14 (11 em `test_bm25_hybrid.py`, 3 em `test_v090_hybrid.py`); 12 mutantes manuais numa cópia, todos mortos (M01, M02, M03, M10, M10b, M12 e 6 das regressões de P2-1 e P2-2).
- Referência com hash inalterada: denso R@6 0,632 e MRR 0,500; híbrido 1,000 e 0,789; hash `ca4109c8ccf9…`.
- Suíte estrita: `lint_and_tests.py --strict` com 2050 passed, 0 failed, ruff limpo, caminhos limpos (728 arquivos), exit 0 (detalhe na passagem).

## Status

Rodada 2 implementada pelo Developer em 2026-11-05 (P2-1 a P2-3 fechados; P3 registrados na passagem); aguarda nova rodada de revisão. Critérios da spec não marcados (Supervisor, depois da revisão e do QA).
