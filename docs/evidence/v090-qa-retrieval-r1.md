# Passagem de papel: QA v0.9.0, retrieval com embeddings reais (momentos 4 a 7), rodada 1

- **Papel e responsável:** QA (subagente, contexto novo), 2026-11-05, de 22:55 a 23:01 UTC.
- **Objetivo e critérios:** CA-52 (tabela denso × híbrido × híbrido+reranker em `dev` e no holdout de retrieval lacrado, com Recall@6, MRR e nDCG@6, e decisão registrada) e a regressão da história [juiz-retrieval-v090.md](../historias/juiz-retrieval-v090.md), versão 1, momentos 4 a 7. Spec [juiz-retrieval-v090.md](../specs/juiz-retrieval-v090.md), D7, D8 e "Orçamento"; [ADR 0020](../architecture/decisions/0020-retrieval-hibrido-holdout.md).
- **Escopo:** CLI `merchant-assistant eval-retrieval`, nos três modos e nos dois splits; ledger do projeto `data/runtime/budget.sqlite3`; relatório `docs/evidence/v090-retrieval.md` e `.json`.
- **Estado:** **apto**, com as limitações abaixo.
- **Branch e PR:** `codex/v0.9.0-juiz-retrieval`, sem PR. Nada foi commitado.
- **Base e versão final:** HEAD `d7775ff` (`git rev-parse HEAD`). O manifesto [v090-candidato-r2.json](v090-candidato-r2.json) fixa `f611480`. `git diff --stat f611480 d7775ff` mostra só o próprio manifesto, e `git diff aa68cff d7775ff -- src tests prompts pyproject.toml` vem vazio. Os 195 arquivos do manifesto foram recalculados sobre `git show HEAD:<path>` e os 195 conferem. O fingerprint `2811389fedeb82b713a2df714e25f0ce71a1450745c1969b9087ca02279e448b` também recalcula: sha256 das linhas `path:sha256\n`, em ordem. `git status` mostra `src/`, `tests/` e `prompts/` limpos, e só os não rastreados de sempre.
- **Independência:** independente. O contexto era novo e eu não escrevi nem revisei o código.

## Pré-checagens (sem custo)

| Checagem | Resultado |
| --- | --- |
| HEAD | `d7775ffa47ede20a3c67ad531f4292d5aca423de` |
| Fingerprint e arquivos do manifesto | 195 de 195 conferem; fingerprint `2811389f…` reproduzido |
| Lacre do holdout | `tests/scenarios/retrieval_holdout_v090.sha256` = `a23850aa66929eb64047b93697cec6b4b0893bc9f77d259f06d42fd3c46ae393`. O sha256 do `.jsonl` na árvore e o de `git show HEAD:` são iguais a ele. Conferido sem abrir as perguntas |
| `eval-retrieval --help` | mostra `--mode {dense,hybrid}`, `--rerank {on,off}`, `--split {dev,holdout_v090}`, `--out` e também `--fake` e `-k` |
| `eval-retrieval --fake --split holdout_v090 --mode dense` | recusado com exit 1 e a mensagem "--fake does not run on the sealed holdout_v090; it is measured once per mode with the real embeddings (D8)". Nenhum relatório foi criado (`docs/evidence/v090-retrieval*` não existia antes da primeira execução real) |
| Padrões em `src/merchant_assistant/config.py` | `retrieval_mode = "dense"`, `rerank = "off"` |
| Ledger antes | `max(id)` 3632, US$1,40251813 liquidados, 3632 linhas `settled`, 0 linhas `claude%`; sidecar `budget.sqlite3.limit` = 2.0 |

## Ambiente e orçamento

- CLI do venv do projeto (`.venv\Scripts\merchant-assistant.exe`, instalação editável de `src/`), chaves lidas do `.env` pela própria aplicação; nenhum valor copiado. Sem Docker, sem navegador, sem Anthropic.
- O `eval-retrieval` real monta o índice em memória: Qdrant `:memory:`, BM25 em memória e `rebuild` sem manifesto. A única escrita em `data/runtime/` são as linhas do ledger `RUNTIME_DIR/budget.sqlite3`, que é o ledger do projeto.
- O `BUDGET_LIMIT_USD` padrão (1,00) fica abaixo do gasto acumulado (1,4025), então toda execução foi feita com `BUDGET_LIMIT_USD=1.50251813`. Esse valor é o gasto antes da fase mais o teto de QA do plano (US$0,10) e funciona como guarda dura da fase. Ele fica abaixo do sidecar persistido de US$2,00, que não foi alterado. O reranker tem, além disso, o teto próprio de US$0,05 por execução (`RERANK_EVAL_CAP_USD`).

## Comandos (na ordem executada; cada um uma única vez)

Todos rodaram com o prefixo `BUDGET_LIMIT_USD=1.50251813` e `--out docs/evidence/v090-retrieval.md`.

| # | Momento | Comando | Início (UTC) | Exit | Duração |
| --- | --- | --- | --- | --- | --- |
| — | 7 | `python -m pytest tests/unit/rag tests/integration/test_v090_hybrid.py tests/integration/test_v090_rerank.py` (basetemp novo fora do repositório) | 22:55 | 0 | **74 passed** em 16,6 s |
| 1 | 4/5 | `eval-retrieval --mode dense --split dev` | 22:56:05 | 0 | 19 s |
| 2 | 4/5 | `eval-retrieval --mode hybrid --split dev` | 22:56:42 | 0 | 20 s |
| 3 | 5 | `eval-retrieval --mode hybrid --rerank on --split dev` | 22:57:12 | 0 | 58 s |
| 4 | 6 | `eval-retrieval --mode dense --split holdout_v090` | 22:58:27 | 0 | 22 s |
| 5 | 6 | `eval-retrieval --mode hybrid --split holdout_v090` | 22:59:00 | 0 | 21 s |
| 6 | 6 | `eval-retrieval --mode hybrid --rerank on --split holdout_v090` | 22:59:31 | 0 | 66 s |

O holdout só foi medido depois do `dev` completo, uma vez por configuração. Nenhum comando falhou e nenhum foi repetido. A saída JSON completa de cada execução (com o resultado por pergunta) ficou em `<scratchpad da sessão>`. O relatório acumulado está em [v090-retrieval.md](v090-retrieval.md) e [v090-retrieval.json](v090-retrieval.json). As duas tabelas a seguir resumem o que foi medido.

## Resultados

| Split | Configuração | n | Recall@6 | MRR | nDCG@6 | ms/consulta | Tokens de embedding | Falhas do reranker | Custo (ledger) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | dense | 19 | 0,895 | 0,860 | 0,868 | 457,0 | 37.408 | — | US$0,00074816 |
| dev | hybrid | 19 | 1,000 | 0,965 | 0,974 | 624,3 | 37.408 | — | US$0,00074816 |
| dev | hybrid+rerank | 19 | 1,000 | 0,974 | 0,981 | 2.641,7 | 37.408 | 0 de 19 | US$0,00574136 |
| holdout_v090 | dense | 25 | 1,000 | 0,871 | 0,880 | 584,3 | 37.698 | — | US$0,00075396 |
| holdout_v090 | hybrid | 25 | 1,000 | 0,920 | 0,921 | 533,7 | 37.698 | — | US$0,00075396 |
| holdout_v090 | hybrid+rerank | 25 | 1,000 | 0,980 | 0,961 | 2.391,8 | 37.698 | 0 de 25 | US$0,00744426 |

- **Reranker (`gpt-6-luna`):**
  - `dev`: 19 chamadas, 45.842 tokens de entrada e 818 de saída, US$0,004993.
  - holdout: 25 chamadas, 61.078 tokens de entrada e 1.165 de saída, US$0,00669.
  - Os dois ficaram muito abaixo do teto de US$0,05 por execução.
- **Por idioma, nDCG@6:**
  - `dev` en: 0,800 no denso, 0,950 no híbrido e 1,000 com reranker.
  - `dev` pt: 0,944, 1,000 e 0,959.
  - holdout en: 0,861, 0,892 e 0,990.
  - holdout pt: 0,897, 0,948 e 0,934.
- **Holdout por categoria, nDCG@6 (denso / híbrido / híbrido+reranker):**
  - `exact_term` (7): 0,991 / 0,991 / 0,966.
  - `fee` (6): 0,978 / 0,975 / 0,900.
  - `procedure` (6): 0,666 / 0,809 / 0,977.
  - `product` (6): 0,865 / 0,898 / 1,000.
- **Hash do corpo BM25:** `ca4109c8…25a98`, o mesmo nas seis execuções.
- O relatório diz "Holdout de retrieval: usado, lacre `a23850aa6692…` conferido". O JSON de cada execução do holdout traz `{"sha256": "a23850aa…ae393", "seal": "ok", "used": true}`.

## Momento a momento

**Momento 4, termo exato (CA-52).** São 5 perguntas `EXACT` em `dev`; a tabela mostra a posição da passagem certa.

| Pergunta | dense | hybrid | hybrid+rerank |
| --- | --- | --- | --- |
| R-EXACT-SP630-pt | 3 | 1 (`both`) | 1 |
| R-EXACT-SP630-en | **fora do top 6** | 3 (`both`) | 1 |
| R-EXACT-ADQ491-en | 1 | 1 (`both`) | 1 |
| R-EXACT-ADQ491-pt | 1 | 1 (`both`) | 1 |
| R-EXACT-D30-en | **fora do top 6** | 1 (`both`) | 1 |

O híbrido acha as 5, e o denso erra 2. O resultado esperado da história ("o denso erra, o híbrido acerta") se confirma nas duas perguntas que o denso não acha. Com embeddings reais, porém, o quadro não é igual ao do hash: o denso real acha 3 de 5, contra 0 de 5 com embeddings de hash, como registrado no ADR 0020. No holdout, a categoria `exact_term` fica empatada entre denso e híbrido (nDCG@6 de 0,991 nos dois). A parte "o Knowledge responde com a passagem certa no modo híbrido", com resposta e trace pela API, ficou fora do roteiro desta fase e **não foi verificada** (ver limitações).

**Momento 5, reranker em `dev`.** O nDCG@6 sobe de 0,974 para 0,981, sem nenhuma falha em 19 consultas. O custo é o tempo médio, que passa de 624 para 2.642 ms por consulta (cerca de 4×).

**Momento 6, holdout por último.** O lacre foi conferido. Houve uma execução por configuração, e a tabela das três configurações está no relatório com o sha.

**Momento 7, regressão.** A fumaça dos testes de `rag/` e das integrações v0.9.0 deu 74 passed. O padrão continua `RETRIEVAL_MODE=dense` e `RERANK=off` em `config.py`. Não rodei a suíte estrita: o Supervisor indicou a do Reviewer, sobre o código idêntico `aa68cff`, com 2107 passed e 1 skipped.

## Regra D7 (aplicada literalmente; a decisão é do Supervisor)

A linha do relatório diz: "Modo padrão sugerido (regra D7, a decisão é do Supervisor): RETRIEVAL_MODE=hybrid, RERANK=on (reranker com 0 falhas em 44 consultas; nDCG@6: dev: dense 0.868, hybrid 0.974, hybrid+rerank 0.981; holdout_v090: dense 0.880, hybrid 0.921, hybrid+rerank 0.961)".

- **`dense` × `hybrid`:** em `dev`, 0,974 > 0,868; no holdout, 0,921 > 0,880. O nDCG@6 é estritamente maior nos dois splits, então pela D7 a regra dá **`RETRIEVAL_MODE=hybrid`**.
- **Reranker (só registro):** em `dev`, 0,981 > 0,974; no holdout, 0,961 > 0,921, com 0 falhas em 44 consultas. A linha do relatório sugere `RERANK=on` porque aplica a regra original. A decisão desta versão já é **`off`** pelo ADR 0020 (P3-16): a comparação mistura o modelo com a profundidade da fusão (36 contra 18), e o relatório não traz a linha de controle `hybrid@36`. No holdout, o reranker piorou `fee` (0,975 → 0,900) e `exact_term` (0,991 → 0,966) e melhorou `procedure` e `product`.

## Custo (ledger do projeto, `data/runtime/budget.sqlite3`, somente leitura antes e depois)

| | Valor |
| --- | --- |
| Antes | `max(id)` 3632, US$1,40251813 |
| Depois | `max(id)` 3826, US$1,41870799, todas as linhas `settled` |
| Delta | **US$0,01618986** em 194 lançamentos (ids 3633 a 3826): 150 `embeddings`/`text-embedding-3-small` (US$0,004506) e 44 `rerank`/`gpt-6-luna` (US$0,011683) |
| Por execução | 1: 0,00074816 · 2: 0,00074816 · 3: 0,00574136 · 4: 0,00075396 · 5: 0,00075396 · 6: 0,00744426 |
| Lançamentos `claude%` | 0 antes e 0 depois |
| Contra o plano | 16% dos US$0,10 de QA da v0.9.0; longe do alerta de US$0,15 e da guarda dura da fase |

Ledger Anthropic (`data/runtime/anthropic`): não foi tocado nesta fase.

## Critérios comprovados e não verificados

- **Comprovados:**
  - CA-52: a tabela dos três modos nos dois splits com Recall@6, MRR e nDCG@6, o holdout lacrado medido uma vez por configuração e por último, o sha no relatório e a linha D7 com os números.
  - A recusa do `--fake` no holdout.
  - O padrão denso e com reranker desligado em `config.py`.
  - A fumaça de regressão de `rag/` e da v0.9.0.
  - Nenhum lançamento Anthropic no ledger do projeto.
- **Não verificados nesta fase:**
  - A resposta do Knowledge pela API em modo híbrido para uma pergunta de termo exato (momento 4, segunda metade; trace).
  - A suíte estrita, os 44 casos e as 4 conversas offline. Para estes valem a suíte do Reviewer e a evidência anterior.

## Achados e limitações

- **Observação 1.** A linha "Modo padrão sugerido" do relatório diz `RERANK=on`. O ADR 0020 fixa `off` nesta versão. Quem ler só [v090-retrieval.md](v090-retrieval.md) (por exemplo, o avaliador) vê uma sugestão que a versão não segue. A aceitação do ADR, o README ou o CHANGELOG da tarefa 82 devem explicar a divergência. Não é defeito: a linha cumpre o que a spec pede (aplicar a regra escrita antes) e diz que a decisão é do Supervisor.
- **Observação 2.** Com embeddings reais, o denso acha 3 das 5 perguntas `EXACT` de `dev`, não 0 de 5 como com hash. No holdout, a categoria `exact_term` empata entre denso e híbrido (0,991). O ganho do híbrido no holdout vem de `procedure` (0,666 → 0,809) e `product` (0,865 → 0,898). Se o README ou o ADR repetirem "5/5 contra 0/5", deve ficar claro que esse número é do hash.
- **Observação 3.** O `.json` acumulado guarda só os agregados por split e idioma, sem resultado por pergunta e sem categoria do holdout. A tabela por pergunta acima saiu da saída padrão de cada execução.
- **Limitações:**
  - O holdout tem 25 perguntas, foi escrito pelo Developer (IA) e Recall@6 e MRR contam grau 1 como acerto (P3-12). Por isso o Recall@6 do holdout fica em 1,000 nos três modos e não discrimina; a diferença aparece em MRR e nDCG@6.
  - O holdout agora é "já visto" (P3-10).
  - Os tempos por consulta incluem a rede até a OpenAI e variam entre execuções. O denso no holdout (584 ms) saiu mais lento que o híbrido (534 ms).
  - A segunda metade do momento 4 (Knowledge pela API) não foi vivida, pelo roteiro desta fase.

Tarefas de defeito: nenhuma.

## Como terminou

O avaliador técnico pediu à CLI três maneiras de buscar, primeiro nas perguntas de desenvolvimento e depois, uma única vez, no conjunto lacrado. A busca híbrida achou as cinco perguntas de código e sigla, e a densa perdeu duas delas. No conjunto que ninguém tinha usado, a híbrida ficou à frente da densa no nDCG@6 (0,921 contra 0,880). Pela regra escrita antes, isso aponta o híbrido como modo padrão. O reranker melhorou um pouco mais, mas quadruplicou o tempo por consulta e fica desligado nesta versão por decisão já tomada. Tudo custou cerca de 1,6 centavo de dólar. Para o lojista nada mudou: o padrão continua denso até o Supervisor decidir.

## Próxima ação e responsável

O Supervisor decide `RETRIEVAL_MODE` pela D7, com os números acima, e registra a aceitação do ADR 0020 e a explicação da linha `RERANK=on` na tarefa 82. Se quiser fechar o momento 4 por inteiro, despacha uma pergunta de termo exato pela API com `RETRIEVAL_MODE=hybrid`, em runtime isolado.

## Decisão humana pendente

Nenhuma do QA. O modo padrão é decisão do Supervisor dentro da autorização por versão.
