# Passagem de papel: revisão da tarefa 81 (reranker, holdout de retrieval e nDCG), rodada 1

- **Papel e responsável:** Reviewer (subagente, contexto frio), 2026-11-05.
- **Objetivo e critérios:** tarefa 81, lida só até "## Validação"; spec `juiz-retrieval-v090.md` D7, D8, D10 e CA-52, mais a linha "Regressão"; história, momentos 5 e 6; P3 abertos de `v090-reviewer-t80.md`.
- **Escopo:** `8c1970b` (holdout e lacre), `2856be1` (`rag/rerank.py`, `prompts/rerank.v1.md`, `rag/index.py`, `config.py`, `agents/knowledge.py`, `scripted_policy.py`), `37dfbf6` (`evaluation/retrieval.py`, `cli.py` no bloco `eval-retrieval`) e `4c27e4a` (`.env.example`). Testes: `test_rerank.py`, `test_retrieval_metrics.py`, `test_v090_rerank.py` e `test_retrieval_holdout_v090.py`.
- **Estado:** **correções necessárias**. Nenhum P1, 3 P2 e P3 registrados.
- **Branch e PR:** `codex/v0.9.0-juiz-retrieval`, sem PR.
- **Base e versão final:** base `fad0eb2`; candidato `4c27e4a` (árvore `0e8822e`); HEAD `632c84a`, que só acrescenta documentação (`git diff 4c27e4a HEAD -- src tests prompts .env.example pyproject.toml` vazio). Não há manifesto `v090-candidato-*.json` desta tarefa: o `r1` existente fixa o experimento do juiz. Por isso fixei o candidato pelos blobs: `rerank.py d8fcbd7`, `index.py d1a5e50`, `retrieval.py b3fef0e`, `cli.py 7871861`, `config.py 4c957a6`, `knowledge.py 8f6a04c`, `scripted_policy.py cdb86a2`, `rerank.v1.md d494f42`, holdout `1a615cf` e lacre `1d5c0eb`. HEAD e árvore de trabalho estavam iguais no início e no fim da revisão (sem alterações locais em `src/`, `tests/` e `prompts/`).
- **Independência:** independente. Não implementei nada e não li `v090-developer.md` nem a Validação ou o Status da tarefa 81.

## Comandos e números

Todas as execuções rodaram em cópias de leitura (`git archive` de `4c27e4a` e `fad0eb2` em `<scratchpad da sessão>`), com o Python do `.venv` do projeto (3.13.3) e `PYTHONPATH` no `src/` da cópia. O módulo carregado foi conferido. Não houve chamada paga, rede, Docker nem Git de escrita, e não toquei em `data/runtime/`, `.pytest_cache/qa-*` nem `.env`.

| Verificação | Resultado |
| --- | --- |
| `pytest` (cópia de `4c27e4a`, basetemp novo dentro da cópia) | **2097 passed, 0 skipped, 0 failed**, 782 s, exit 0. São 2050 da rodada 2 da tarefa 80 mais 47 testes novos |
| `ruff check` (cópia) | All checks passed |
| `validate_structure` e `validate_skills` (cópia) | válidas |
| `checar-caminhos-pessoais.py` (repositório) | limpo, 746 arquivos (antes deste parecer) |

As quatro etapas do `lint_and_tests.py --strict` rodaram separadamente, porque a cópia não tem `.git`.

## O que re-derivei e como

1. **Escopo do diff** (`git diff fad0eb2..4c27e4a --stat`, 15 arquivos). Ficaram **sem mudança** `llm/` (inclusive `anthropic_llm.py`), `evaluation/judge.py`, `evaluation/calibration.py`, `main.py`, os prompts existentes (só entra `rerank.v1.md`), `business_journeys.jsonl`, `holdout_v080.*` e `retrieval.jsonl`. Em `cli.py` muda só o bloco `eval-retrieval`, com o auxiliar `_retrieval_reranker`, a constante do teto e o parser. Em `knowledge.py` entram 6 linhas, todas atrás de `settings.rerank == "on"`. Procurei outro reranker ou verificador de lacre em `src/` (`grep -i rerank`, `sha256`) e não achei: o lacre do `holdout_v080` é conferido só por teste. Não há duplicação.
2. **Equivalência com `RERANK=off`.** `eval --scripted --split all` na base e no candidato: os 40 casos são idênticos em todos os campos, fora `request_id` e duração (`passed` 25/40 nos dois, `model_calls` 123 nos dois). As 4 conversas passam nas duas versões e diferem só no protocolo aleatório `HO-...`. Sonda de trace com `POST /messages` offline sobre as mesmas 40 mensagens: os 31 pares sem 429 do limitador de taxa da sonda, que atingiu só jornadas de suporte, têm resposta, passos e **detalhe do passo `knowledge` idênticos byte a byte** (19 com Knowledge). Com `RETRIEVAL_MODE=hybrid RERANK=on` e o modelo programado, `model_calls` passa de 123 para 138 (+15, um por busca RAG), e o trace traz `rerank: {prompt: rerank@1, candidates: 12, status: ok, order: [...]}`.
3. **Holdout (D8).** O arquivo nasce em `8c1970b` (18:19), junto com o `.sha256` e o teste do lacre, antes de `2856be1` e `37dfbf6` (18:29), que trazem o código que mede. `git diff 8c1970b..HEAD -- tests/scenarios/` sai vazio. São 25 perguntas, 13 em pt, com as quatro categorias (6 de taxa, 6 de produto, 6 de procedimento e 7 de termo exato). O sha256 normalizado `d8381ddd...0d12d` confere com o lacre e com o blob de `8c1970b`. Os 39 `chunk_id` existem no corpo (145 chunks). Nenhum teste lê o arquivo real: o `grep` só acha o teste do lacre, e os testes de split usam um holdout sintético em `tmp_path` com `SCENARIOS` substituído. A ordem dos commits não prova que as perguntas foram escritas sem consultar resultados, só que o lacre veio antes do código de medição. **Não rodei nenhum modo sobre o holdout real.** Li as 25 perguntas e os rótulos contra o texto dos chunks e fiz uma busca por substring de cada resposta no corpo inteiro (notas no P3-12).
4. **nDCG@6.** `dcg` usa ganho linear e desconto `log2(i+2)`. `ndcg_at_k` corta em k e normaliza pelo ideal ordenado. Os valores fixos conferem: perfeito 1,0; `[1,2]` contra `[2,1]` dá 0,859719; relevante em 6º dá 0,356207; em 7º dá 0. No holdout o ganho é o grau (2 ou 1). Em `dev` há um alvo único, ganho 1 só para o primeiro documento relevante, e o nDCG equivale a `1/log2(rank+1)`. **Defensável:** os rótulos de `dev` são por documento ("qualquer um destes"), então não há ideal graduado. A escolha está escrita no cabeçalho do relatório gerado ("nDCG com um alvo só"). Ressalva: em `dev`, nDCG e MRR medem a mesma coisa (posição do primeiro acerto).
5. **Reranker.** O prompt é novo e versionado (`rerank@1`), com o aviso de que as passagens são dados. Rótulos `P1..P12`, `max_output_tokens` 150, `effort` `none` e passagens cortadas em 700 caracteres. Rótulo desconhecido, lista vazia, `LLMError`, `ValidationError`, `BudgetExceeded`, `LimitExceeded` e `incomplete` (via `output_parsed=None` do adaptador OpenAI) mantêm a ordem e anotam `status: failed` com o erro. Menos de 2 candidatos não fazem chamada. No Knowledge o `Meter` é o `RunContext`, então a chamada conta em `max_model_calls`, no teto da requisição e no ledger (confirmado pelo +15 do item 2). `RERANK=on` com `dense` é recusado no `Settings` (`model_validator`), na CLI e no `search`. A exceção do `search` seria engolida pelo Knowledge como `knowledge_unavailable`, mas o `Settings` impede chegar lá, e `capture_active` propaga o modo.
6. **`eval-retrieval`** (cópia descartável, `--fake`, sem chaves no ambiente). Em `dev`: denso R@6 0,632, MRR 0,500, nDCG 0,534, 1,4 ms; híbrido 1,000, 0,789, 0,843, 4,6 ms; híbrido+reranker programado 1,000, 0,765, 0,825, 9,9 ms, com 19 chamadas e 0 falhas. Os números do denso e do híbrido são iguais aos da revisão da tarefa 80. Com a mesma `--out`, `-k 5` é recusado ("use another --out"). A linha D7 sai "indisponível: faltam holdout_v090/...". Nenhum arquivo foi criado no runtime: nem ledger, nem pickle. Com o holdout adulterado (1 byte numa cópia descartável), a CLI com `--rerank on` sem `--fake` foi **recusada pelo lacre antes de qualquer guarda ou cliente**: runtime vazio, exit 1. A regra D7 em `suggest_default` usa `>` estrito nos dois splits, e o reranker só entra se o híbrido também. O teto de US$0,05 é um `BudgetMeter(max_cost_usd=0.05)` acumulado por execução.
7. **Mutação manual** (cópia própria; os 4 arquivos de teste da tarefa). Foram **29 mutantes, 26 mortos e 3 sobreviventes**:

| Mutante | Resultado |
| --- | --- |
| N1 sem desconto; N2 desconto `log2(i+3)`; N3 ganho binário; N5 sem corte @k | mortos |
| N4 ideal sem ordenar em `ndcg_at_k` | sobreviveu: redundante, porque `RetrievalCase.ideal()` já ordena |
| D1 híbrido com `>=`; D2 reranker com `>=`; D3 reranker sem exigir o híbrido; D4 híbrido só em `dev` | mortos |
| R1 rótulo desconhecido aceito; R2 ordem vazia aceita; R3 sem corte de 700; R4 `effort` `low`; R5 15 candidatos; R6 `LLMError` propaga; R7 falha sem nota | mortos |
| S1 lacre não conferido; S2 lacre conferido depois de abrir a guarda; S3 sem contagem "já visto"; S4 mistura de embeddings ou `k` aceita | mortos |
| K1 Knowledge chama o reranker com `off` (no híbrido); K3 Knowledge sem nota no trace | mortos |
| **K2 Knowledge passa `NullMeter()` ao reranker** (chamada paga fora da guarda, do teto da requisição e de `max_model_calls`) | **sobreviveu** |
| C1 CLI liga o reranker sempre no híbrido; C3 CLI aceita `--rerank on` com denso; C4 `Settings` aceita `RERANK=on` com denso | mortos |
| **C2 CLI sem o teto de US$0,05** (`max_cost_usd=None`) | **sobreviveu** |
| I1 `search` ignora o reranker; I2 fusão sem os 12 | mortos |

A cópia de mutação foi restaurada e conferida (`diff -r` sem diferença contra outra cópia de `4c27e4a`).

## Achados

### P1

Nenhum.

### P2 (corrigir antes do QA)

**P2-1. Ligar o reranker muda a fusão, não só a ordem: a comparação híbrido contra híbrido+reranker da D7 fica confundida, e "falha mantém a ordem da fusão" não devolve o resultado do `RERANK=off`.**

- Condição: com reranker, `search` usa `fused_k = max(k, 12)` e `depth = 3 * fused_k` = 36, contra 18 sem reranker. O RRF sobre listas de 36 pode reordenar o top 6 (um item em 19º a 36º nas duas listas soma mais que um item em 1º numa só).
- Impacto: (a) o número de "hybrid+rerank" mistura o efeito do modelo com o da profundidade da fusão, e a D7 decide pelo nDCG@6 estritamente maior; (b) com o modelo falhando (rede, rótulo inválido, orçamento), o Knowledge e o `eval-retrieval` devolvem um top 6 diferente do modo híbrido puro, sem dizer isso. O holdout é medido uma vez por modo. Corrigir depois do QA exigiria remedir e marcaria o holdout como "já visto". Por isso o achado é P2.
- Local: `src/merchant_assistant/rag/index.py:238-246`.
- Reprodução (sonda de profundidade, só em `dev` e em perguntas sintéticas, embeddings de hash): com um reranker identidade (devolve a mesma ordem), `search(q, k=6, mode="hybrid", min_score=0.3)` difere de `search(..., reranker=Identidade)` em 2 de 58 consultas. Em "Como funciona a antecipação de recebíveis na Getnet?", as posições 4 a 6 passam de `duvidas#7, taxas#1, duvidas#6` para `duvidas#6, duvidas#7, taxas#1`. Os testes fixam esse comportamento em vez de detectá-lo: `test_search_with_a_reranker_that_keeps_the_order_returns_the_fusion_top_k` compara com `search(k=12)[:6]`, e `test_knowledge_keeps_the_fusion_order_when_the_reranker_fails` compara só os 3 primeiros.
- Correção sugerida (a escolha é do Developer ou do Supervisor): na falha, devolver `rrf(dense[:3k], lexical[:3k], k)`, igual ao `off`, e reordenar só os 12 candidatos. Outras saídas: fixar a mesma profundidade (36) também para o híbrido sem reranker, o que muda o comportamento revisado na tarefa 80 e exige registrar isso, ou medir no relatório um controle "hybrid@36". O teste de falha deve comparar o top k inteiro com o do modo híbrido.

**P2-2. Falhas do reranker ficam fora do relatório Markdown e da linha D7.**

- Condição: `evaluate` conta `rerank_failures`, e `record_run` guarda o valor no `.json`, mas `render_markdown` não o mostra e `suggest_default` não o considera. A falha pode vir do teto de US$0,05 (`BudgetExceeded` engolido pelo reranker), de timeout, de rótulo inválido ou de `incomplete`.
- Impacto: uma execução real em que parte das consultas caiu na ordem da fusão aparece no `.md` como "hybrid+rerank" com um nDCG que não é do reranker, e a linha "Modo padrão sugerido" decide sobre ele. No holdout, medido uma vez, isso não se refaz sem "já visto".
- Local: `src/merchant_assistant/evaluation/retrieval.py:184-202` (`suggest_default`) e `:204-240` (`render_markdown`).
- Reprodução: `record_run` com `rerank_failures: 3` sai idêntico no `.md` a uma execução com 0 falhas (`render_markdown` não lê a chave).
- Correção sugerida: coluna ou nota de falhas por linha no `.md`, e linha D7 "indisponível" (ou com ressalva explícita) quando `hybrid+rerank` tiver falhas em algum split.

**P2-3. Faltam testes para duas guardas de custo (mutantes sobreviventes).**

- K2: trocar o `meter` do reranker no Knowledge (`agents/knowledge.py:152-153`) por `NullMeter()` passa em todos os testes. A chamada paga sairia da guarda de orçamento, do teto da requisição e de `max_model_calls` (AGENTS.md: "toda chamada paga passa pela guarda de orçamento"). Hoje o código está correto (item 2: +15 `model_calls`), mas nada o protege.
- C2: tirar o teto de US$0,05 do `eval-retrieval` pago (`cli.py:271`) passa em todos os testes.
- Correção sugerida: um teste de integração com `RERANK=on` que confira `model_calls`, `usage_by_agent["rerank"]` e o lançamento no ledger da requisição. Um teste de `_retrieval_reranker(fake=False)` com guarda falsa e cliente que não pode ser chamado, conferindo `max_cost_usd == 0.05`, ou um `BudgetExceeded` depois de o acumulado passar do teto.

### P3 (registrar)

- **P3-10. "Já visto" depende de usar a mesma `--out`, e a nova medição substitui a anterior.** Sem `--out` nada é gravado. Com outra `--out` a contagem recomeça. Ao repetir, `record_run` troca os números da linha e só a contagem lembra a primeira medição. Para um holdout medido "uma vez por modo", melhor seria guardar a primeira medição (ou recusar a repetição sem confirmação) e exigir `--out` no split selado. Vale a mesma disciplina operacional da D1 para o QA.
- **P3-11. `--fake` aceita o holdout real.** Com embeddings de hash, a parte BM25 do híbrido é real, e a saída por caso (`rank`, `top`) expõe resultados do holdout fora da medição oficial. Os testes usam o holdout sintético, então recusar `--fake` no holdout real (ou só suprimir `cases`) não quebra nada.
- **P3-12. Rótulos do holdout que parecem discutíveis** (não editei: o lacre quebraria; ficam como nota para o relatório e para o ADR 0020):
  - `RH090-EN-FEE-REDUCED-PLAN-MONTHLY`: o chunk `pub:site-getnet-com-br-get-ajuda-receba-ja-plano-de-recebimento-reduzido#2-7277015656078541`, sem rótulo, termina com a resposta completa ("5. Existe alguma mensalidade? Não. Você pagará as taxas aplicáveis às transações (MDR) e a taxa de serviço do plano contratado"). Deveria ter grau 1 ou 2. Hoje um modo que o traga em 1º é penalizado.
  - `RH090-PT-EXACT-DOCK-IP`: `get-conta#0` ("através de uma parceria com a Dock IP") tem grau 1, e `pub:site-getnet-com-br-duvidas#16-ee989e26967573f8`, com a mesma frase, tem 0. Rótulo inconsistente.
  - `RH090-PT-PROD-MINESTORE-PLANS`: `pub:site-getnet-com-br-duvidas#21-beea60c04332ea16`, sem rótulo, lista os três planos (Up, Plus e Prime) e diz que só Plus e Prime pagam mensalidade. Responde metade da pergunta.
  - `RH090-EN-PROD-GETNET-SCALE`: grau 1 para `www-getnet-net-en#1`, que diz "access 1.3 million merchants" (diverge de "1.2 million active merchants" do grau 2) e não fala de países. O grau premia uma passagem que leva a um número errado e, no Recall e no MRR, conta como acerto.
  - `RH090-EN-FEE-PLANO-LIGHT-INSTALLMENT`: grau 1 para `duvidas#31`, que só abre o tema ("12 parcelas completas") sem o valor. É generoso.
  - `RH090-PT-FEE-VOUCHER-MDR-CAP` e `RH090-PT-FEE-GETTAP-12X`: o chunk de grau 1 também traz a resposta inteira (3,6% e 15 dias; 12,88%). Grau 2 seria defensável. O efeito é pequeno.
  - Viés geral: várias perguntas repetem o cabeçalho da FAQ ("conciliador da Auttar", "Qr Code Expirado", "fechamento detalhado, venda a venda") e 7 de 25 são de termo exato, o que favorece o BM25. Convém registrar no relatório da D7 que o holdout foi escrito pelo mesmo Developer que conhecia o corpo.
  - Recall@6 e MRR no holdout contam o grau 1 como acerto. Convém dizer isso no cabeçalho do relatório, como já é dito para o nDCG.
- **P3-13. A regra D7 do híbrido usa só o nDCG@6** (Recall e MRR ficam como informação). A spec não fixa a métrica do modo. A escolha é razoável e está na docstring "written before measuring", mas precisa ir para o ADR 0020 como regra prévia.
- **P3-14. `record_run` não confere `bm25_corpus_hash`.** Execuções de `dev` e do holdout feitas com corpos diferentes (depois de um `ingest`) podem entrar na mesma tabela. Basta conferir o hash como já se faz com embeddings e `k`.
- **P3-15. O reranker usa 1 das 8 chamadas de `max_model_calls`** e acrescenta latência ao Knowledge. Com replanner e web, a margem diminui. Para registrar se a D7 ligar o reranker.
- Da tarefa 80: P3-1 (`origin` no trace) segue aberto no trace do Knowledge, porque as linhas do `eval-retrieval` agora trazem `origins`. P3-2 a P3-4, P3-6, P3-7 e P3-9 seguem sem mudança. P3-8 (`min_score` e `no_evidence` no híbrido) continua para a tarefa 82 e o ADR 0020.

## Critérios

| Critério da tarefa 81 | Estado |
| --- | --- |
| Holdout lacrado, conferido por teste, nunca lido por teste de desenvolvimento | **comprovado** (item 3). O guarda `test_no_other_test_reads_the_holdout` procura só o nome literal do arquivo, o que é fraco mas suficiente hoje |
| nDCG@6 com números fixos | **comprovado** (item 4; N1, N2, N3 e N5 mortos) |
| Reranker programado em sucesso, falha e limite de tokens | **comprovado** (itens 5 e 7), com a ressalva do P2-1 sobre o que é "ordem da fusão" |
| `eval-retrieval` nos três modos e dois splits sem rede | **comprovado** em `dev`. No holdout, comprovado pelos testes com o holdout sintético; não rodei no holdout real, por escolha |
| `RERANK=off` sem mudança no Knowledge | **comprovado** (item 2: 40 casos, 4 conversas, 19 traces) |
| Suíte estrita verde | **comprovado** (2097 passed; ruff, caminhos, estrutura e skills) |

Não verificado: chamada real do `gpt-6-luna` com `RerankOrder` em saída estruturada estrita, custo real por consulta e números com embeddings reais (QA, momentos 5 e 6).

## Incidentes da revisão

Nenhum efeito no repositório. A sonda do lacre usou uma chave fictícia numa cópia descartável, e a recusa aconteceu antes de qualquer cliente ser criado. Não repeti a sonda. Os processos em segundo plano (suíte, avaliações e mutantes) terminaram antes deste relato.

## Próxima ação

O Developer corrige P2-1, P2-2 e P2-3 numa rodada 2 da tarefa 81. Depois, o Reviewer re-verifica em contexto novo `rag/index.py`, `evaluation/retrieval.py`, `cli.py`, `agents/knowledge.py` e os testes, e repete a sonda de profundidade e os mutantes K2 e C2. O QA só mede o holdout depois disso. Os P3 vão para a tarefa 82 e o ADR 0020. Os rótulos do P3-12 não podem ser corrigidos sem relacrar o holdout. Como nenhum modo foi medido nele, relacrar agora ainda é possível, mas a decisão é do Supervisor. Não há outra decisão humana pendente.

---

# Passagem de papel: revisão da tarefa 81, rodada 2

- **Papel e responsável:** Reviewer (subagente, contexto frio), 2026-11-05.
- **Objetivo e critérios:** confirmar as correções de P2-1, P2-2 e P2-3 e o relacre do holdout segundo as decisões do Supervisor. Com `RERANK=off`, vale a fusão da tarefa 80 (profundidade 3k). Com `on`, o modelo reordena os 12 primeiros de uma fusão a 36 e o resultado é cortado em k. Qualquer falha ou pulo do reranker devolve o resultado idêntico ao `off`. O Markdown traz a coluna de falhas, e a linha D7 diz "reranker com N falhas em M consultas". Os testes devem matar K2 e C2. `--fake` recusa o holdout real. O relacre acontece uma vez, antes de qualquer medição, e corrige só os sete rótulos do P3-12. Reli a tarefa 81 só até "## Validação", a spec (D7 e D8) e o parecer da rodada 1.
- **Escopo:** `1d05f7d` (relacre), `e0dbbf2` (`rag/index.py`, `rag/rerank.py`, `test_rerank.py`) e `aa68cff` (`cli.py`, `evaluation/retrieval.py`, `test_v090_rerank.py`, `test_retrieval_metrics.py`). Os merges `e31587f` e `54a5fcb`, de README e evidência do juiz, ficam fora.
- **Estado:** **apto para QA**. Nenhum P1 e nenhum P2. Há P3 registrados, e um deles (P3-16) pede decisão do Supervisor antes de o QA medir o holdout.
- **Branch e PR:** `codex/v0.9.0-juiz-retrieval`, sem PR.
- **Base e versão final:** base `4c27e4a`; candidato `aa68cff` (árvore `132a30b`). Blobs: `index.py a27a222`, `rerank.py 89324be`, `retrieval.py 4ca358b`, `cli.py 5587b0b`, `knowledge.py 8f6a04c` (o mesmo da rodada 1), holdout `8efcaf8` e lacre `208f97a`. O HEAD era `4809284` no início e passou a `24b26cd` durante a revisão. Os dois commits só acrescentam documentação (passagem do Developer, Validação da tarefa e ADRs 0020 e 0021): `git diff aa68cff HEAD -- src tests prompts pyproject.toml .env.example` sai vazio. A árvore de trabalho não tem alteração em `src/`, `tests/` e `prompts/`. Em `index.py`, o blob local difere só no fim de linha (CRLF), e `git diff aa68cff` sai vazio.
- **Independência:** independente. Não li `v090-developer.md` nem as seções Validação e Status da tarefa 81.

## Comandos e números

Executei tudo em cópias de leitura (`git archive aa68cff`) em `<scratchpad da sessão>`, com o Python do `.venv` do projeto (3.13.3) e `PYTHONPATH` no `src/` da cópia. Conferi que o módulo carregado era o da cópia. Não houve chamada paga, rede, Docker nem Git de escrita, e não toquei em `data/runtime/`, `.pytest_cache/qa-*`, `.env`, `_tmp/` nem `discovery/`.

| Verificação | Resultado |
| --- | --- |
| `pytest` (cópia de `aa68cff`, basetemp novo) | **2107 passed, 1 skipped, 0 failed**, 731 s, exit 0 (2097 da rodada 1 mais 10 testes novos). O teste pulado é `test_synthetic_v040_script_logs_in_with_passwords`, fora do escopo, porque o basetemp ficou fora de `.pytest_cache`. Rodado depois com basetemp dentro do `.pytest_cache` da cópia: **passed** |
| `ruff check` (os 163 arquivos do `lint_and_tests.py`) | All checks passed |
| `validate_structure` e `validate_skills` (cópia) | válidas |
| `checar-caminhos-pessoais.py` (repositório) | limpo: 749 arquivos antes deste parecer e 749 depois |

As quatro etapas do `--strict` rodaram separadamente, porque a cópia não tem `.git`.

## O que re-derivei e como

1. **Escopo.** `git diff 4c27e4a..aa68cff` em código e testes toca só os 10 arquivos esperados. `agents/knowledge.py`, `config.py`, `scripted_policy.py` e `prompts/` estão **intactos**.
2. **P2-1 (falha igual ao `off`).** `search` agora faz `fusion(k)` sem reranker e, com reranker, `fusion(max(k, 12))`. Se `reorder` devolve `None` (falha ou pulo), refaz `fusion(k)` com o mesmo vetor da consulta. Sonda própria com 64 perguntas: `dev`, mensagens dos cenários e 10 perguntas sintéticas minhas, sem nenhuma do holdout (interseção 0). Cruzei 3 filtros de fonte, `min_score` 0, 0,3 e 0,6, k 3, 6, 12 e 14, e 5 tipos de falha (`LLMError`, rótulo desconhecido, ordem vazia, `BudgetExceeded` e `LimitExceeded` na reserva do `Meter`). Comparei `(chunk_id, score, origin, payload)` contra `off`: **11.520 comparações, 0 divergências** (10.640 `failed` e 880 `skipped`). Com o reranker identidade, o resultado é sempre igual a `fusion(12)[:6]` (64 de 64). Contra o `off`, difere em 2 de 64 com `min_score` 0,3, o mesmo número da rodada 1 (mesmo exemplo da antecipação), e em **29 de 64 com `min_score` 0** (ver P3-16). No Knowledge, `test_knowledge_keeps_the_fusion_order_when_the_reranker_fails` agora compara `detail["hits"]` inteiro com o do modo híbrido.
3. **P2-2 (falhas no relatório e na D7).** De ponta a ponta, rodei `cmd_eval_retrieval` real (`--fake`) nos três modos e nos dois splits, com um holdout sintético lacrado em diretório descartável e o reranker programado falhando em 1 de cada 3 chamadas. O `.json` traz `rerank_failures` 6 em `dev` e 1 no holdout. O `.md` traz `| dev | hybrid+rerank | 19 | … | 6 de 19 |` e `| holdout_v090 | hybrid+rerank | 2 | … | 1 de 2 |`, com o cabeçalho "o modelo reordena os 12 primeiros de uma fusão de profundidade 36, contra 18 do `hybrid`; numa consulta em que o reranker falha, a resposta é a do `hybrid`". A linha D7 sai `RETRIEVAL_MODE=hybrid, RERANK=indisponível (reranker com 7 falhas em 21 consultas; …)`. No holdout com falha, o nDCG do `hybrid+rerank` saiu igual ao do `hybrid` (0,816), coerente com o item 2. Nenhum arquivo foi criado no runtime.
4. **P2-3 (K2 e C2).** `test_the_knowledge_reranker_is_metered_by_the_request` confere `model_calls` (+1 contra o modo híbrido), `models_by_agent["rerank"]` e o lançamento `rerank` no ledger da requisição. `test_paid_reranker_of_eval_retrieval_has_the_cap_per_run` usa um cliente que falha se for chamado e confere o modelo do agente, a constante 0,05, a recusa `BudgetExceeded` (escopo `evaluation`) entre US$0,04 e US$0,05 e o mesmo valor no ledger do projeto. Nenhuma chamada sai.
5. **P3-11 (`--fake` no holdout).** A recusa vem antes de `split_cases`, só quando `SCENARIOS` é o diretório versionado. `test_fake_runs_refuse_the_real_holdout` confere que nem o runtime é criado.
6. **Holdout (relacre).** Entre `4c27e4a` e `1d05f7d` mudam só 7 das 25 linhas. Os 25 ids e as 25 perguntas, categorias e idiomas são idênticos, e 13 perguntas continuam em pt. As mudanças, com o que pedi no P3-12:
   - VOUCHER: `bandeiras#0` passa de 1 para 2. Responde tudo.
   - GETTAP-12X: `get-tap#1` passa de 1 para 2. Responde tudo.
   - REDUCED-PLAN-MONTHLY: entra `reduzido#2` com grau 2. Resposta completa.
   - PLANO-LIGHT: sai `duvidas#31`, que era grau 1 generoso.
   - MINESTORE-PLANS: entra `duvidas#21` com grau 1. Responde metade.
   - GETNET-SCALE: sai `www-getnet-net-en#1`, que trazia o número divergente.
   - DOCK-IP: entra `duvidas#16` com grau 1, consistente com `get-conta#0`.

   Os graus seguem a definição escrita no commit: grau 2 é a resposta inteira, e dois chunks podem tê-lo; grau 1 é parte da resposta. O teste de forma passou de `count(2) == 1` para `>= 1`, de acordo com essa definição. O sha256 normalizado do arquivo é `a23850aa66929eb64047b93697cec6b4b0893bc9f77d259f06d42fd3c46ae393` e confere com o `.sha256`. O blob é o mesmo em `1d05f7d`, `aa68cff` e HEAD. Os `chunk_id` existem no corpo (teste de rótulos verde na suíte).
7. **Holdout não lido nem medido.** `git grep` em `tests/` e `src/` não acha leitor do arquivo real fora do teste do lacre. Os testes de split usam holdout sintético em `tmp_path`, e o `development_questions()` novo lê `retrieval.jsonl` e os cenários por nome (63 perguntas, interseção 0 com o holdout). Não há relatório de `eval-retrieval` nem arquivo `*retrieval*` gerado no repositório, rastreado ou não (fora os diretórios proibidos, que não abri). As menções a `holdout_v090` em `docs/` são de spec, tarefa, história, ADR 0020 ("relacrado uma vez … ainda sem medição") e evidência, sem números medidos. O relacre (19:10) é anterior às correções de código (19:16). **Não rodei nenhum modo sobre o holdout real.**
8. **Mutação manual** (cópia própria, 4 arquivos de teste da tarefa). Foram **18 mutantes, 17 mortos e 1 equivalente**, todos mortos pelo teste que lhes cabe (confirmado com `-rf`). Uma primeira passada deu falsos "mortos" por `FileNotFoundError` do meu basetemp e foi descartada e refeita.

| Mutante | Resultado |
| --- | --- |
| K2 Knowledge passa `NullMeter()` ao reranker | morto (`test_the_knowledge_reranker_is_metered_by_the_request`) |
| C2 sem teto (`max_cost_usd=None`); C2b teto x10; C2c `BudgetMeter` sem o ledger | mortos (`test_paid_reranker_of_eval_retrieval_has_the_cap_per_run`) |
| F1 falha devolve `fusion(12)[:k]`; F3 falha devolve os candidatos (lista em vez de `None`); F4 falha ignora `source_kinds` e `min_score` | mortos (`test_a_failing_reranker_answers_exactly_as_rerank_off_on_every_question` e, no F4, também o teste do Knowledge) |
| F5 candidatos da fusão a k em vez de 12 | morto |
| **F2 pulo (menos de 2 candidatos) devolve a lista em vez de `None`** | **sobreviveu, equivalente**: com 0 ou 1 candidato na fusão a 12, a fusão a k tem o mesmo item com o mesmo score RRF (as 880 consultas puladas do item 2 conferem) |
| D1 D7 ignora falhas; D2 conta falhas só em `dev`; D3 coluna sempre "0 de n"; D4 `record_run` descarta `rerank_failures`; D5 só a partir de 4 falhas | mortos |
| E1 e E2 `evaluate` não conta falhas | mortos (`test_evaluate_passes_the_reranker_and_counts_its_failures`) |
| P1 `--fake` aceita o holdout real | morto |
| H1 cabeçalho com profundidade errada | morto |

A cópia de mutação foi restaurada e conferida (`diff -r` sem diferença contra a cópia do candidato).

## Achados

### P1

Nenhum.

### P2

Nenhum. P2-1, P2-2 e P2-3 da rodada 1 estão **resolvidos** (itens 2 a 4 e 8).

### P3 (registrar)

- **P3-16. Na D7, a comparação `hybrid+rerank` contra `hybrid` continua misturando o modelo com a profundidade, e no `eval-retrieval` o efeito é grande.** Isso segue a decisão do Supervisor e está escrito no cabeçalho do `.md`, por isso não é P2.
  - Condição: o `eval-retrieval` chama `search` sem `min_score` (0,0), e o Knowledge usa 0,30. Com 0,0, só a fusão a 36 muda o top 6 em 29 de 64 perguntas. Em `dev`, com embeddings de hash, um reranker identidade, que não reordena nada, leva o nDCG@6 de 0,843 para **0,858** e o MRR de 0,789 para 0,811. O reranker programado dá 0,825.
  - Impacto: a regra D7 usa `>` estrito. Um reranker inútil passaria em `dev` só pela profundidade, e o número medido no holdout herda o mesmo viés. Com embeddings reais o tamanho é desconhecido.
  - Local: `src/merchant_assistant/rag/index.py:248` e `src/merchant_assistant/evaluation/retrieval.py:110` (`search` sem `min_score`).
  - Reprodução: `evaluate(idx, load_cases(retrieval.jsonl), k=6, mode="hybrid")` com e sem um `Reranker` cujo `ScriptedLLM` devolve os rótulos na ordem recebida.
  - Sugestão, a decidir pelo Supervisor **antes** de o QA medir o holdout: uma linha de controle `hybrid@36`, sem chamada de modelo e de custo zero, em `dev` e no holdout, com a D7 comparando o reranker contra ela. Outra saída é registrar no ADR 0020 que o ganho do reranker inclui o efeito de profundidade.
- **P3-17.** Ficou um comentário desatualizado em `agents/knowledge.py:151` ("a failure keeps the fusion order"); hoje a falha devolve o resultado do `off`. O arquivo ficou intocado de propósito, então o ajuste é só de texto, numa próxima mudança.
- **P3-18.** `Reranker.rerank` só é usado pelos testes; o índice usa `reorder`. Os testes de `rerank` exercitam `reorder` por dentro, então o efeito é nulo. Fica registrado como API sobrando.
- **P3-19.** `rerank_failures` conta só `failed`. O `skipped` (menos de 2 candidatos) não entra na linha D7. Como a resposta é a do `off`, o efeito sobre o número é nulo, e com `min_score` 0 isso quase não ocorre.
- Da rodada 1: P3-11 e P3-12 estão resolvidos (itens 5 e 6). P3-10, P3-13, P3-14 e P3-15 seguem abertos, sem mudança no código (o `record_run` continua sem conferir `bm25_corpus_hash`). Os P3 da tarefa 80 seguem como estavam.

## Critérios

| Critério | Estado |
| --- | --- |
| Falha ou pulo do reranker devolvem o resultado idêntico ao `off` (ids, ordem, scores e origem) | **comprovado** (item 2: 11.520 comparações; mutantes F1, F3 e F4) |
| `on` reordena os 12 primeiros de uma fusão a 36 e corta em k; `off` usa a fusão da tarefa 80 | **comprovado** (item 2; mutante F5). A sonda `RERANK=off` contra `dev` reproduz os números da rodada 1 (híbrido 1,000, 0,789 e 0,843) |
| Coluna de falhas no `.md` e linha D7 com "N falhas em M consultas" e "indisponível" quando há falha | **comprovado** (item 3, de ponta a ponta; mutantes D1 a D5, E1 e E2) |
| Testes matam K2 e C2 | **comprovado** (item 8) |
| `--fake` recusa o holdout real | **comprovado** (item 5; mutante P1) |
| Relacre único, antes de medir, só nos sete rótulos, com as mesmas 25 perguntas e sha `a23850aa…` | **comprovado** (itens 6 e 7) |
| Nenhum modo medido no holdout | **sem evidência de medição** no repositório (item 7). Não é provável por ausência: não abri `data/runtime/` nem `_tmp/` |
| Suíte estrita verde | **comprovado** (2107 passed; o único pulo é de ambiente e passou isolado) |

Não verificado: chamada real do `gpt-6-luna` com `RerankOrder` estrito, custo real por consulta e números com embeddings reais (QA).

## Incidentes da revisão

Nenhum efeito no repositório além deste apêndice. Descartei e refiz a primeira passada de mutação, cujo basetemp tinha o diretório pai inexistente. Os processos em segundo plano (suíte, mutantes e espera) terminaram antes deste relato.

## Próxima ação

O Supervisor decide o P3-16 (controle `hybrid@36` ou registro no ADR 0020) **antes** de o QA medir o holdout, porque depois disso qualquer mudança marca o holdout como "já visto". Depois disso, o QA mede a tarefa 81 com embeddings reais. Os demais P3 vão para a tarefa 82 e para o ADR 0020. Não há decisão humana pendente.
