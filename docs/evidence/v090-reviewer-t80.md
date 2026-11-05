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

---

# Rodada 2

- **Papel e responsável:** Reviewer (subagente, contexto frio), 2026-11-05.
- **Objetivo e critérios:** fechar P2-1 a P2-3 da rodada 1 conforme as decisões do Supervisor: o pickle guarda só ids e estatísticas, e payload, URL, `source_kind` e `collected_at` vêm sempre do índice ativo; arquivo temporário único com `os.replace` e trava por coleção; testes para `k=60`, `3×k`, `min_score` só no denso, fiação do `main.py` e `eval-retrieval --mode hybrid`; `RETRIEVAL_MODE` comentado no `.env.example`; Knowledge sem mudança. Critérios da tarefa 80 e D7 da spec.
- **Escopo:** `60ab2c8` (`rag/bm25.py`, `rag/index.py`, `tests/unit/rag/test_bm25_hybrid.py`, `tests/integration/test_v090_hybrid.py`) e `687895c` (`.env.example`). Base da rodada 1: `c99aa90`.
- **Estado:** **apto para QA** (nenhum P1, nenhum P2; P3 registrados).
- **Branch e PR:** `codex/v0.9.0-juiz-retrieval`, sem PR.
- **Base e versão final:** candidato `687895c` (árvore `8308c07`); HEAD `f8f7db4` (árvore `a97d0b4`). Durante a revisão, a branch ganhou `f7ffe2b`, que muda só documentação do QA do juiz (`v090-juiz-opus-sonda.*`, `v090-qa-juiz-r1.md`). `687895c..f8f7db4` muda só documentação (`v090-candidato-r1.json`, `v090-developer.md`, `v090-reviewer-t79.md`, spec, tarefa 80). Blobs no candidato, no HEAD e na árvore de trabalho, no início e no fim da revisão: `bm25.py 17d1cc1`, `index.py ecc0e85`, `main.py 9d1e0ac`, `cli.py 11f89ed`, `kb.py 17ce5d9`, `config.py 8fb7dfe`, `testing.py 93a92fd`, `evaluation/retrieval.py 8d551eb`, `agents/knowledge.py 7bae3a8`, `test_bm25_hybrid.py 939f2c1`, `test_v090_hybrid.py 3f255b8`, `.env.example 4231574`, `pyproject.toml e215232`. No `index.py` da árvore de trabalho só muda o fim de linha (`text=auto`; `git diff` vazio, sha256 sem CR igual). O manifesto `v090-candidato-r1.json` fixa o experimento do juiz, não a tarefa 80; por isso fixei o candidato pelos blobs acima.
- **Independência:** independente. Não implementei nada e não li `v090-developer.md` nem as passagens do Developer no scratchpad compartilhado. Ressalva: um `grep` por `min_score|no_evidence` exibiu três linhas da seção Validação da tarefa 80 (linhas 40, 43 e 49); elas só repetem a lista de correções e não mudaram nenhuma verificação.

## Comandos e números

Cópias de leitura com `git archive` de `f8f7db4`, `c99aa90` e `fee7a78`, mais uma cópia de mutação de `f8f7db4`, em `<scratchpad da sessão>/r2`. Python do `.venv` do projeto (3.13.3, pytest 9.1.1), com `PYTHONPATH` no `src/` da cópia; o módulo carregado foi conferido em cada execução. Nenhuma chamada paga, nenhuma rede, nenhum Docker, nenhum Git de escrita. Não toquei em `data/runtime/`, `.pytest_cache/` nem no `.env` do repositório.

| Verificação | Resultado |
| --- | --- |
| `git diff --stat` de `60ab2c8` e `687895c` | só `rag/bm25.py`, `rag/index.py`, os dois testes e `.env.example`. Em `c99aa90..687895c`, fora disso, só a tarefa 79 e documentação: `cli.py` muda só em `cmd_eval`, `cmd_eval_rejudge`, `cmd_eval_calibrate` e `main` (`7d1039f`), e nada em `cmd_eval_retrieval`. `agents/`, `prompts/`, `main.py`, `config.py`, `kb.py`, `testing.py`, `evaluation/retrieval.py`, `pyproject.toml` e `tests/scenarios/` não mudam |
| `checar-caminhos-pessoais.py` (repositório) | limpo: 729 arquivos no início e 732 depois de gravar este parecer |
| `pytest` (cópia de `f8f7db4`, basetemp em `.pytest_cache/bt` da cópia) | **2050 passed, 0 skipped, 0 failed**, 863 s, exit 0. São 2036 da rodada 1 mais 14 testes novos (11 de unidade e 3 de integração). O teste `test_v070_identity_r2.py:277`, pulado na rodada 1, rodou porque o basetemp ficou dentro do `.pytest_cache` da cópia |
| `ruff check` (cópia) | All checks passed |
| `validate_structure` e `validate_skills` (cópia) | válidas |

Rodei as quatro etapas do `lint_and_tests.py --strict` separadamente, como na rodada 1, porque a cópia não tem `.git`. Incidente sem efeito: a primeira execução do pytest falhou por ambiente (o diretório pai do basetemp não existia na cópia). Criei o diretório e reexecutei; os números acima são dessa segunda execução.

## O que re-derivei e como

1. **Equivalência do denso.** A mesma sonda da rodada 1: 145 chunks, 25 perguntas, 7 combinações de `k`, filtro e `min_score`. `fee7a78 search()` × `f8f7db4 search()` e × `f8f7db4 search(mode="dense")` dão **175/175 idênticos**, com ids, sha256 dos payloads, scores bit a bit (diferença máxima 0) e `origin` sempre `dense`.
2. **`eval-retrieval --fake`** (cópia sem `.env`, 0 token de embedding, nenhum pickle gravado). `--mode dense`: n=19, R@6 0,632, MRR 0,500, termo exato sem acerto em nenhuma das 5 (`None` nas 5). `--mode hybrid`: R@6 1,000, MRR 0,789, ranks do termo exato 2, 4, 1, 4, 2. Hash BM25 `ca4109c8ccf9…`. Idênticos à rodada 1.
3. **Sonda 9 (P2-1).** `v1` com `public_official` e `url=old`; `v2` com o mesmo id e texto, `simulated_internal`, `url=new` e `collected_at` novo, no mesmo diretório e no mesmo cliente. Um só `bm25-*.pkl` para as duas versões. `v2.search("E-1023", mode="hybrid", source_kinds=["public_official"], min_score=0.99)` devolve **`[]`** (na rodada 1, devolvia o item com `url=old`). Com `["simulated_internal"]`, devolve `("p#0", "bm25", "simulated_internal", "https://new", "2026-11-01")`. `v1` continua citando a própria URL. Numa carga fria do arquivo com outros registros, `built=False` e a URL é a atual. O arquivo não contém `https://`, nem `source_kind`, nem o texto (só ids e estatísticas).
4. **Sonda 10 (regra do `min_score`).** Sem mudança, como decidido: `min_score=0.99` dá `[]` no denso e `[("a#0", "bm25", 0.0164)]` no híbrido. Agora a regra está fixada por teste e pela docstring de `search()`.
5. **Sonda 11 (P2-2), Windows.** Com 4 threads, `Barrier` e `load_or_build` de 3 000 registros, repetido 10 vezes: **0 erros**, 1 construção por repetição, nenhum `.tmp` sobrando. O controle em `c99aa90` com a mesma sonda dá `PermissionError` (2 de 4 threads), então a sonda ainda detecta o defeito. Com 4 clientes Qdrant distintos e o mesmo `bm25_dir`, buscando em paralelo: 0 erros, 1 construção (trava pelo caminho), 1 arquivo. Com **4 processos** e partida sincronizada, 8 repetições: 32/32 sem erro, resultado correto, 1 arquivo por diretório e nenhum `.tmp`. Cada processo constrói o seu (3 a 4 construções por repetição): não há trava entre processos, e a gravação atômica com nome único torna isso inofensivo, como diz a docstring de `_write`. No corpus real (145 chunks, `bm25_dir` com pickle), 8 buscas híbridas simultâneas a partir do cache frio, em 5 repetições, terminam com 0 erros, um resultado só, 1 construção por repetição e o `erro-adq-4-91` no top 6.
6. **Leitura do Developer sobre o cache.** Confirmada: os payloads são lidos ao entrar no cache por `(cliente, coleção)`, não a cada busca. Com o `scroll` instrumentado, 3 buscas híbridas e mais um `KnowledgeIndex` novo no mesmo cliente e na mesma coleção fazem 1 leitura. `rebuild(replace_existing=True)` limpa o cache: a busca seguinte relê (2 leituras), acha o termo novo e não acha o antigo. O cache vale porque as coleções publicadas são imutáveis: em `src/`, só o `rebuild` escreve pontos, e nada chama `replace_existing=True` (`kb.py:373` usa `False`). Os limites dessa premissa estão no P3-7.
7. **Mutantes** (testes `tests/unit/rag` e `test_v090_hybrid.py`; M01 e M02 também com `test_eval_campaign.py`). Os 5 sobreviventes da rodada 1 agora **morrem**: M01 (`test_min_score_cuts_the_dense_list_only`), M02 (`test_hybrid_fuses_the_top_3k_of_each_list`), M03 (`test_rrf_uses_k_60_over_ranks_starting_at_1`), M10a sem `mode=` e M10b sem `bm25_dir=` (`test_production_assembly_passes_retrieval_mode_and_runtime_bm25_dir`) e M12 (`test_eval_retrieval_hybrid_report_measures_the_hybrid_search`). Os mutantes novos da rodada 2:

| Mutante | Resultado |
| --- | --- |
| M05: `rebuild` não descarta o cache | morto |
| M17: nome temporário só com o pid (o da rodada 1) | morto |
| M18: `load_or_build` sem trava nem segunda leitura | morto |
| M19: `bm25_index` sem trava por coleção | morto |
| M20b: o arquivo volta a guardar os payloads | morto |
| M20 + M20b: payloads servidos a partir do arquivo (o defeito da rodada 1) | morto (`test_persisted_bm25_takes_payloads_from_the_current_collection`) |
| M21: falha de escrita propaga | morto |
| M24: sem a segunda leitura do cache dentro da trava | morto |
| M20 sozinho | sobreviveu: equivalente, porque o arquivo não tem payloads |
| M22: sem conferir `chunk_ids` na carga | sobreviveu: redundante, porque o hash do nome já fixa os ids |
| M23: sem conferir `format` na carga | sobreviveu: redundante, porque o arquivo da rodada 1 cai na checagem de lista |

São 17 mutantes: 14 mortos e 3 sobreviventes, todos equivalentes ou redundantes. A cópia de mutação foi restaurada e conferida contra a cópia do HEAD (`diff -r` sem diferença, fora `__pycache__`).

## Achados

### P1

Nenhum.

### P2

Nenhum. P2-1, P2-2 e P2-3 da rodada 1 estão **fechados** (itens 3, 5 e 7).

### P3 (registrar)

- **P3-7. O cache em processo pressupõe coleção imutável. Há dois casos fora dessa premissa, nenhum alcançável pelo `src/` atual.** (a) Corrida entre `rebuild(replace_existing=True)` e a primeira construção do BM25: o `rebuild` limpa o cache (`rag/index.py:167-168`), mas não toma a trava de construção (`:194-195`), então uma construção já em curso grava depois o corpus apagado. Reprodução: `load_or_build` atrasado em 1 s, uma busca híbrida numa thread e um `rebuild(replace_existing=True)` com outro corpus 0,3 s depois. Em seguida, `"4-91"` (corpus novo) dá `[]` e `"E-1023"` (corpus apagado) dá `[("a#0", "bm25")]`, com o payload de um ponto que já não existe. (b) Uma alteração de payload no lugar (`set_payload`) ou uma reconstrução por outro cliente ou processo não invalida o cache: o denso cita a URL nova e o item só-BM25 cita a antiga. Hoje só testes e coleções descartáveis usam `replace_existing=True`. Sugestão: o `rebuild` tomar a mesma trava de construção ao limpar o cache, ou o cache guardar o `point_digest`. E registrar a premissa no ADR 0020.
- **P3-8. Regra do `min_score` e limitação do `no_evidence` ainda fora da D7.** Pela decisão do Supervisor, o Knowledge não muda nesta tarefa. A D7 da spec (`juiz-retrieval-v090.md:45`) ainda não diz que, no híbrido, o limiar cosseno vale só para a lista densa, que o `no_evidence` só dispara se o BM25 também não achar nada e que o `score` do trace fica na escala RRF. Levar para a tarefa 82 e o ADR 0020, antes de decidir a D7 pelo híbrido.
- **P3-9. Concorrência entre processos.** Não há trava entre processos: N workers na primeira busca constroem N vezes (só custo de CPU; o resultado e o arquivo ficam corretos, item 5). `_BUILD_LOCKS` guarda uma trava por arquivo e nunca é podado, o que se soma ao P3-4.
- Da rodada 1: o P3-5 fica **parcialmente fechado** (`RETRIEVAL_MODE` agora no `.env.example`, comentado, padrão `dense`; o nome `runtime/bm25.pkl` do plano continua para o ADR). P3-1 a P3-4 e P3-6 seguem registrados, sem mudança nesta rodada.

## Critérios

| Critério da tarefa 80 | Estado |
| --- | --- |
| `search(mode="dense")` idêntico e Knowledge sem mudança no padrão | **comprovado** (175/175; `agents/knowledge.py` sem mudança desde `fee7a78`) |
| Híbrido acha os termos exatos que o denso não acha | **comprovado** com embedder de hash (5/5 contra 0/5) |
| Reconstrução só quando o hash muda, nos dois sentidos | **comprovado**. Agora sem servir metadado velho (sonda 9) e sem erro na concorrência (sonda 11) |
| `eval-retrieval --mode` sem rede, medindo o modo pedido | **comprovado** e protegido por teste (M12 morto) |
| Suíte estrita verde | **comprovado** (2050 passed; ruff, caminhos, estrutura e skills limpos) |

Não verificado (fora do escopo da revisão): embeddings reais, latência por modo e a decisão D7 (QA, tarefas 81 e 82).

## Incidentes da revisão

Nenhum efeito no repositório. Encerrei os processos em segundo plano (suíte e mutantes) antes do relato. Ao montar este texto, um heredoc sem aspas fez o shell tentar executar dois trechos entre crases como comandos (`command not found`, sem efeito). O trecho apagado foi restaurado e o texto foi relido. A árvore vazia `C:/c/` da rodada 1 já foi removida e não foi recriada (os caminhos passados ao Python agora são todos no estilo Windows).

## Próxima ação

A tarefa 80 vai ao QA (momentos 4 e 7 da história, com embeddings reais e com custo autorizado). Os P3-7 a P3-9 vão para as tarefas 81 e 82 e para o ADR 0020. Não há decisão humana pendente nesta revisão.
