# Passagem de papel: revisão da tarefa 80 (retrieval híbrido BM25 + RRF), rodada 1

- **Papel e responsável:** Reviewer (subagente, contexto frio), 2026-11-05.
- **Objetivo e critérios:** tarefa 80; spec `juiz-retrieval-v090.md` D7, D10, CA-52 (parte determinística) e a linha "Regressão"; história, momentos 4 e 7; plano, decisões técnicas 17 a 19. Lidos só até "## Validação" da tarefa; não li a Validação, o Status nem `v090-developer.md`.
- **Escopo:** `5d82fd0` e `c99aa90` (`rag/bm25.py`, `rag/index.py`, `rag/kb.py`, `config.py`, `main.py`, `testing.py`, `evaluation/retrieval.py`, `cli.py` no bloco `eval-retrieval`, `pyproject.toml`, `tests/scenarios/retrieval.jsonl`, `tests/unit/rag/test_bm25_hybrid.py`, `tests/integration/test_v090_hybrid.py`).
- **Estado:** **correções necessárias** (nenhum P1; 3 P2; P3 registrados).
- **Branch e PR:** `codex/v0.9.0-juiz-retrieval`, sem PR.
- **Base e versão final:** base `fee7a78`; candidato `c99aa90` (árvore `e4a0fdb`); suíte no HEAD `94df63c` (árvore `1c7bb20`). Blobs dos arquivos da tarefa 80 idênticos entre `c99aa90` e `94df63c`; `cli.py` muda só nos blocos da tarefa 79 (nada em `eval-retrieval`). Durante a revisão a branch ganhou `4a9f263` e `216c66c`, **só documentação** (tarefa 79, história e passagem do Developer); `src/`, `tests/` e `pyproject.toml` da árvore de trabalho iguais a `94df63c` no início e no fim. Alterações locais de outro escritor em `docs/tasks/79-...md` e `docs/evidence/v090-developer.md` ignoradas.
- **Independência:** independente. Não implementei nada; não recebi passagem nem diagnóstico. Uma passagem do Developer da tarefa 80 existe no scratchpad compartilhado e **não foi lida**.

## Comandos e números

Tudo em cópias de leitura (`git archive` de `fee7a78`, `c99aa90` e `94df63c` em `<scratchpad da sessão>`, conferidas contra `git ls-tree`: 0 arquivo a mais ou a menos, conteúdo igual ao blob, a menos de CR), com `PYTHONPATH` apontando para o `src/` da cópia (o módulo carregado foi conferido em cada execução). Nenhuma chamada paga, nenhuma rede, nenhum Docker, nenhum Git de escrita.

| Verificação | Resultado |
| --- | --- |
| `checar-caminhos-pessoais.py` (repositório e cópia do HEAD) | limpo, 727 arquivos |
| `pytest` (cópia de `94df63c`, `--basetemp` novo) | **2035 passed, 1 skipped**, 17min40s, exit 0. O skip é `test_v070_identity_r2.py:277` (só roda com basetemp dentro de `.pytest_cache`; efeito do basetemp fora do repositório) |
| `ruff check` nos 727 arquivos rastreados | All checks passed |
| Estrutura e skills (`validate_structure`, `validate_skills` do `lint_and_tests.py`) | válidas |

`lint_and_tests.py --strict` não roda inteiro numa cópia sem `.git` (o verificador de caminhos chama `git ls-files`); executei as quatro etapas dele separadamente, com os mesmos comandos.

## O que re-derivei e como

1. **Escopo do diff.** `git diff --name-only fee7a78..94df63c`: `agents/knowledge.py`, `prompts/`, `business_journeys.jsonl`, `holdout_v080.*`, `orchestration/budget.py` e as guardas **não mudaram**. Em `retrieval.jsonl` entram só 5 linhas novas, e as 14 antigas ficam intactas.
2. **Equivalência do denso (critério 1, momento 7).** A sonda própria monta a coleção em memória com o embedder de hash sobre os 145 chunks. São 25 perguntas (as 19 do conjunto, mais vazia, só stopwords, `MDR`, `E-1023`, ruído e uma pt), cada uma com 7 combinações: `k` 1, 6 e 500 (maior que o corpus), filtros `None`, `public_official`, `simulated_internal` e os dois, `min_score` 0, 0,05, 0,1, 0,3 e 0,9. Com a mesma sequência de chamadas, `fee7a78 search()` × `c99aa90 search()` e × `c99aa90 search(mode="dense")` dão **175/175 idênticos**: ids, ordem, sha256 dos payloads, scores bit a bit e `origin` sempre `dense`. Controle: o Qdrant em memória varia na 8ª casa entre consultas idênticas repetidas no mesmo processo, **igual na base e no candidato** (6 trocas de ordem e 44 de score em 38×3 repetições, nos dois). Isso explica o `approx` no teste do Developer e não é efeito da mudança.
3. **44 respostas offline (`eval --scripted --split all`).** Base × candidato denso: os 40 casos têm rota, status, fontes, agentes e caminho iguais. As respostas diferem só no ID aleatório de encaminhamento (`HO-...`, 4 casos) e na latência; `passed` 0,625 nos dois e 4/4 conversas nos dois. No candidato híbrido: 0,65 (26/40), 11 respostas ou fontes mudam e as conversas ficam 4/4. `NOEV` falha nos três (o modelo programado concatena passagens, então não mede o portão de evidência).
4. **`eval-retrieval --fake`, sem rede e sem chave (0 tokens de embedding, nenhum pickle gravado).** Base com 14 casos: R@6 0,857 e MRR 0,679. Candidato `--mode dense`: n=19, R@6 0,632, MRR 0,500; termo exato 0/5; os 14 antigos são idênticos linha a linha à base. `--mode hybrid`: R@6 1,000, MRR 0,789; termo exato 5/5 com MRR 0,500 (ranks 2, 4, 1, 4, 2); antigos R@6 1,000 e MRR 0,893. Hash BM25 `ca4109c8ccf9…`. O resultado vem do embedder de hash e serve de referência, não de prova.
5. **Perguntas `EXACT-TERM`.** Conferido por chunk: `sp630` só ocorre em `todas-as-maquininhas#3` ("…você irá receber é o SP630…"); `4-91` só em `erro-adq-4-91`; `d30` em `todas-as-maquininhas#1` e `#2` ("Taxas mediante recebimento em D30"). O critério de relevância continua por documento, como antes.
6. **Caminho de produção executado (`main.build_orchestrator`)**, offline, com LLM programado, hash e Qdrant em memória, e `POST /messages` com "Apareceu ADQ 4-91…". Com `RETRIEVAL_MODE=hybrid`, `index.mode` é `hybrid`, o trace traz scores na escala RRF (cerca de 0,03) com `erro-adq-4-91` em 2º, e `runtime/bm25-<hash>.pkl` é criado com o mesmo hash do manifesto. Com `dense`, os scores ficam na escala cosseno, nenhum pickle é criado e o ADQ aparece em 6º.
7. **Modo.** `Settings.retrieval_mode` é `Literal`, com padrão `dense`; valor inválido é recusado no `Settings`, no `KnowledgeIndex(mode=)` e no `search(mode=)`. `capture_active` e `testing.py` propagam o modo (os mutantes M11 e M11b morrem).
8. **Sondas do item 8** (todas no candidato):

| Sonda | Resultado |
| --- | --- |
| Pergunta só com stopwords (`o que é a de`) | tokens `[]`; o híbrido devolve só a lista densa, `origin=dense` |
| Corpus vazio | `rebuild([])` funciona; híbrido e denso devolvem `[]` |
| Chunk sem tokens | entra só pelo denso. Corpus todo sem tokens: `bm25=None`, só o denso |
| Empate total no RRF | ordem pelo rank denso; no BM25, empate pelo `chunk_id` |
| `k` maior que o corpus | devolve o corpus inteiro, sem erro |
| Mesmos pares em outra ordem | mesmo hash; textos trocados entre ids mudam o hash; A→B→A recarrega A sem reconstruir |
| Pickle corrompido ou objeto estranho | reconstruído e regravado |
| Tokenização | `MDR`→`mdr`, `E-1023`→`e-1023`, `ação`→`acao`, `D30`→`d30`, `SP630`→`sp630`, `Wi-Fi`→`wi`,`fi`, `D+1`→`d`,`1` |

Mutação manual (cópia própria de `c99aa90`; `tests/unit/rag` e `test_v090_hybrid.py`; M01 e M02 também com `test_eval_campaign.py`). Foram **16 mutantes, 10 mortos e 6 sobreviventes**:

| Mutante | Resultado |
| --- | --- |
| M01: híbrido ignora `min_score` | **sobreviveu** |
| M02: profundidade `k` em vez de `3×k` | **sobreviveu** |
| M03: `RRF_K=1` | **sobreviveu** (o teste usa a própria constante) |
| M04: desempate pelo BM25 | morto |
| M05: `rebuild` sem descartar o cache | morto |
| M06: sempre reconstrói | morto |
| M07: hash dependente da ordem | morto |
| M08: BM25 sem filtro de `source_kind` | morto |
| M09: BM25 devolve chunks sem o termo | morto |
| M10: `main.py` sem `mode=` e `bm25_dir=` | **sobreviveu** (nenhum teste monta `build_orchestrator` com o modo) |
| M11 e M11b: `capture_active` e `testing.py` sem modo | mortos |
| M12: `cmd_eval_retrieval` não passa `mode` ao `evaluate` | **sobreviveu** |
| M13: padrão `hybrid` | morto |
| M14: `origin` trocado | morto |
| M15: aceita o pickle sem conferir o hash interno | sobreviveu (redundante com o nome do arquivo) |

## Achados

### P1

Nenhum.

### P2 (corrigir antes do QA)

**P2-1. O pickle do BM25 devolve payloads obsoletos: o hash cobre só `(chunk_id, text)`, mas o arquivo guarda e serve o payload inteiro.**

- Condição: duas construções com os mesmos ids e textos e metadados diferentes (`url`, `collected_at`, `procedure_id`, `source_kind`) no mesmo `bm25_dir`. Exemplo: snapshot recoletado com o mesmo conteúdo e `bootstrap --force-index` no runtime do serviço. A segunda coleção carrega o pickle antigo.
- Impacto: no modo híbrido, um item vindo só do BM25 sai com URL e data de coleta antigas (o cabeçalho da passagem mostra `collected …`), e o filtro `source_kinds` é avaliado sobre o `source_kind` antigo. Hoje o prefixo do `doc_id` amarra o tipo, por isso o desvio do filtro é teórico, mas a citação com metadado velho não é.
- Local: `src/merchant_assistant/rag/bm25.py:51-60` (hash), `:70-73` (guarda os payloads), `:95-105` (carga). Uso em `rag/index.py:185-204` e `:63-83` (o RRF usa `payload` do BM25 para os itens `bm25`).
- Reprodução: sonda 9. A coleção `v1` tem `public_official` e `url=old`; a `v2`, com o mesmo id e texto, tem `simulated_internal` e `url=new`, no mesmo diretório e no mesmo cliente. `v2.search("E-1023", mode="hybrid", source_kinds=["public_official"], min_score=0.99)` devolve `[("p#0", "bm25", "public_official", "https://old…")]`. Sem persistência, o resultado é `[]`.
- Correção sugerida: `bm25_index()` já percorre a coleção inteira a cada falta de cache. Guarde no pickle só ids e tokens, e junte os payloads da leitura atual; ou ponha o payload canônico no hash.

**P2-2. A primeira construção concorrente do BM25 no mesmo processo falha (arquivo temporário com o mesmo nome).**

- Condição: `RETRIEVAL_MODE=hybrid` e várias requisições simultâneas na primeira busca de uma coleção (início do serviço ou ativação de versão). Todas as threads usam `bm25-<hash>.<pid>.tmp`, e não há trava por coleção em `bm25_index()`.
- Impacto: no Windows, 3 de 4 threads recebem `PermissionError [WinError 32]`. A exceção sobe de `search()`, o Knowledge a captura e a requisição sai `knowledge_unavailable`. No Linux, a escrita intercalada pode gerar pickle corrompido ou `FileNotFoundError` no segundo `os.replace`.
- Local: `rag/bm25.py:108-115` e `rag/index.py:185-204`.
- Reprodução: sonda 11, com 4 threads, `threading.Barrier`, `bm25.load_or_build(big, dir)`: `errors = 3× PermissionError`. Depois, a carga funciona.
- Correção sugerida: nome temporário único por chamada (uuid ou id da thread), trava por `(cliente, coleção)` na construção e, se a escrita falhar, devolver o índice em memória mesmo assim.

**P2-3. Faltam testes para comportamentos declarados (mutantes sobreviventes).**

- M12: o relatório de `eval-retrieval --mode hybrid` pode medir o denso e dizer "hybrid". É a ferramenta da decisão D7 e do CA-52.
- M10: a fiação de produção `main.py` (`mode=`, `bm25_dir=`) não tem teste. Hoje está correta (item 6 acima), mas nada a protege.
- M02 e M03: os `3×k` e o `k=60` da tarefa não estão fixados.
- M01: a decisão de aplicar `min_score` só à lista densa não está fixada. Avaliação da decisão: **defensável**. O limiar cosseno não se aplica à escala do BM25 nem à do RRF, e filtrar o BM25 por ele anularia o ganho do termo exato. A consequência, porém, precisa ser explícita. No híbrido, o atalho `no_evidence` do Knowledge (`agents/knowledge.py:168`) só dispara se o BM25 também não achar token nenhum; o `score` do trace (`knowledge.py:162`) muda de escala (cerca de 0,03 contra o limiar 0,30); e um item só-BM25 nunca é cortado (sonda 10: `min_score=0.99` dá `[]` no denso e `[("a#0", "bm25", 0.0164)]` no híbrido).
- Correção sugerida: testes que matem M01, M02, M03, M10 e M12: números fixos do RRF com `k=60`; um item no rank denso entre `k` e `3k` que entra pela fusão; `min_score` cortando o denso e não o BM25; `build_orchestrator` com `retrieval_mode="hybrid"` e `bm25_dir`; `rows` do `eval-retrieval` diferentes entre os modos para as `EXACT-TERM`. Registrar a regra do `min_score` para o ADR 0020 e a decisão D7 (tarefa 82).

### P3 (registrar)

- **P3-1. `origin` não chega ao trace nem ao `eval-retrieval`.** O passo `knowledge` grava `doc`, `score`, `chunk_id` e `excerpt`; as linhas do `eval-retrieval` não têm `origin`. A tarefa pede `origin` "para o trace", e a evidência do momento 4 é o trace. Com `knowledge.py` fora do escopo desta tarefa, fica para a 81 ou a 82: campo aditivo em `hits`.
- **P3-2. A chave de persistência não inclui a versão do tokenizador nem os parâmetros (`STOPWORDS`, `tokenize`, `k1`, `b`).** Se o tokenizador mudar, o mesmo corpus carrega o pickle antigo, com tokens de outra regra. Sugestão: constante de versão no hash ou no nome do arquivo.
- **P3-3. Tokenização de códigos.** Hífen não ASCII (U+2011, travessão) parte `4‑91` em `4` e `91`, que não casam com o `4-91` indexado. `E1023` e `E 1023` (`e` é stopword) não casam com `e-1023`. Considerar indexar também as partes do código.
- **P3-4. Crescimento.** Um `bm25-<hash>.pkl` por corpus no runtime, nunca podado, e o cache em processo guarda o BM25 de toda coleção já consultada pelo cliente.
- **P3-5. Documentação.** `RETRIEVAL_MODE` ausente de `.env.example`. A decisão 17 do plano diz `runtime/bm25.pkl`, e a tarefa e o código usam `bm25-<hash>.pkl` (alinhar no ADR 0020). O manifesto das versões da KB (exposto em `/v1`) ganha `bm25_corpus_hash` e `retrieval_modes`: mudança aditiva e compatível.
- **P3-6.** `pickle.load` lê só o runtime do próprio serviço, o que é aceitável. Registrar no ADR que o diretório é confiável.

## Critérios

| Critério da tarefa | Estado |
| --- | --- |
| `search(mode="dense")` idêntico e Knowledge sem mudança no padrão | **comprovado** (itens 2 e 3) |
| Híbrido acha os termos exatos que o denso não acha | **comprovado** com embedder de hash (5/5 contra 0/5) |
| Reconstrução só quando o hash muda, nos dois sentidos | **comprovado** (testes, A→B→A e sondas), com a ressalva do P2-1 sobre o que o hash cobre |
| `eval-retrieval --mode` sem rede | **comprovado**; o rótulo do modo não tem teste que o amarre ao número (P2-3, M12) |
| Suíte estrita verde | **comprovado** (2035/1 skip, ruff, caminhos, skills) |

Não verificado: `eval-retrieval` com embeddings reais e a decisão D7 (QA, tarefas 81 e 82); latência por modo.

## Incidentes da revisão (sem efeito no repositório)

- Um `--out` com caminho POSIX passado ao Python do Windows criou uma árvore de diretórios **vazia** na raiz do disco, `C:/c/` (espelho do caminho do scratchpad). Os 4 relatórios foram movidos para o scratchpad. A remoção da árvore foi barrada pela checagem de segurança da ferramenta e **fica para o responsável apagar `C:/c/`**, que está vazia.
- Um `grep -l` listou nomes de arquivos em `data/runtime/` (sem ler conteúdo e sem escrever). Não voltei a tocar no diretório.
- Encerrei com `taskkill` só os meus processos de mutação (filtrados pela linha de comando `mutate80`). A cópia de mutação foi restaurada e conferida contra `c99aa90`.

## Próxima ação

O Developer corrige P2-1, P2-2 e P2-3 numa rodada 2 da tarefa 80. Depois, o Reviewer re-verifica em contexto novo os arquivos afetados (`rag/bm25.py`, `rag/index.py` e os testes) e repete as sondas 9, 10 e 11 e os mutantes M01, M02, M03, M10 e M12. Os P3 vão para as tarefas 81 e 82 ou ficam registrados. Nenhuma decisão humana pendente nesta revisão, além de apagar a árvore vazia `C:/c/`.
