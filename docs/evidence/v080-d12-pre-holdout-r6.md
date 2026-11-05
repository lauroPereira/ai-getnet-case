# QA D12 pré-holdout — v0.8.0 r6 (reteste das seis jornadas, juiz repetido e Docker, candidato r11)

Data: 2026-11-05 (America/Sao_Paulo)  
Tarefa: [74](../tasks/74-correcao-qa-pre-holdout-v080.md), com [78](../tasks/78-regua-literal-ca51-recusa-respostas-corretas-v080.md) (decisão do Supervisor: CA-51 continua medido pela checagem determinística `passed`). História: [orquestracao-avaliacao-v080.md](../historias/orquestracao-avaliacao-v080.md), versão 1, momentos 7, 8 e 9.  
Resultado: **apto para o holdout.** Fase A: CA-51 composto deu **13/13, 12/13 e 12/13**, acima do portão de 12/13 em cada repetição. As duas falhas são só `content_ok`, em respostas corretas recusadas pela redação (falsas recusas da mesma classe P3-7). Fase B: `--judge-repeat 3` sobre as 44 respostas da primeira execução, com 132 julgamentos e nenhuma falha do juiz. Fase C: o smoke Docker passou 10/10, e a pergunta mista replanejou de support para knowledge, com origem `rule:procedure_gap` no trace. Nenhuma tarefa de defeito foi aberta. O holdout não foi lido nem executado.

## Candidato

| Item | Valor |
|---|---|
| Branch | `codex/v0.8.0-replan`. Nesta rodada não houve checkout, pull, reset nem commit |
| Candidato fixado | `1baa7b31ed28724a2536ae33a12f11a4d41c4cf8` ([manifesto r11](v080-candidato-r11.json), fingerprint `d8e536fe…52eb`) |
| HEAD em toda a rodada | `52f15dccffd4ff1ee059d519f3fa489d4ba7c3c1` |
| Diff candidato → HEAD | só `docs/evidence/v080-candidato-r11.json` e `v080-reviewer-t78.md`. Em `src prompts tests data tools` o diff é vazio, conferido no início e pelo seletor antes de cada bloco |
| Revisão | [v080-reviewer-t78.md](v080-reviewer-t78.md), rodada 4: apto para QA, com a lista P3-7 final |
| Delta de produto desde a r5 (`658c70a → 1baa7b3`) | `tests/scenarios/business_journeys.jsonl` (rótulos das seis jornadas da T78) e `tests/unit/evaluation/test_t78_ca51_archived.py`. Produto, prompts, runner e dados sem mudança |
| Holdout `holdout_v080` | não lido nem executado (D17) |
| Árvore rastreada | limpa antes e depois. Os não rastreados `Claude outputs/`, `_tmp/` e `v/` já existiam e ficaram intactos |

## Seed e horários (São Paulo, 05/11)

| Evento | Horário |
|---|---|
| Prova sem custo da seed da r5, feita às 03:50 de 05/11: "ontem" = 2026-11-04, com `sale_1988_0001..0003` em 04/11 (09:42, 13:05, 17:30), `rcv_1988_0001` em 05/11, `rcv_1988_0002` em 06/11 e `sale_1988_0005` em 03/11 (`seed-dates-proof.json`). **Seed válida, sem ressemear** | 06:53 |
| Suíte estrita | 06:53:30 – 07:06:12 |
| Mock `127.0.0.1:18765` no ar, com saúde comprovada | 06:57 e 07:06:55 |
| Fase A, bloco `healthy` | 07:07:04 – 07:10:34 |
| Fase B, cinco blocos `judge-*` | 07:12:03 – 07:16:41 |
| Fase C, `compose up --build` | 07:18:34 – 07:20:05 |
| Fase C, pergunta com replanejamento e smoke | 07:20:41 – 07:22:29 |
| Fase C, `compose down` e conferência final | 07:23 |

O seletor conferiu antes e depois de cada bloco pago que "ontem" = 2026-11-04 e que as três vendas caem nesse dia (`same_local_day: true` nos seis blocos). Na conferência final, às 07:23, a seed continuava igual. Nenhuma fase cruzou a meia-noite.

## Ambiente

- Pré-condição: `python tools/scripts/lint_and_tests.py --strict` (venv 3.13.3, `PYTEST_ADDOPTS=--basetemp=.pytest_cache/qa-r6-suite-basetemp`) deu **1997 passed** em 12m16s, o mesmo número do manifesto, com Ruff e skills ok e exit 0. Log `75e99ffe…ed63`.
- `RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime`, `BUDGET_RUNTIME_DIR=data/runtime`, `MOCK_SERVICES_DIR=data/mock-services`, todos só no processo. Saídas em `.pytest_cache/qa-v080-r1/qa-r6-results/`.
- O mock oficial de preços rodou com a venv em `127.0.0.1:18765`. Saúde comprovada (`mock-health-00.json`, `mock-health-A-healthy.json`): `/openapi.json` 200; `POST /pricing/simulations` (`sale_1988_0001`) 200, com regra `pricing_mock_v1_debit` e taxa 194; `GET /charges/sale_1988_0001` 200. O preflight do seletor repetiu a checagem do OpenAPI. O log do mock tem 17 simulações: 2 das sondas e 15 das cinco jornadas de preço × 3. O mock foi encerrado ao fim da fase A.
- Juiz: DeepSeek `deepseek-flash`, `judge@3`, independência `different_provider`. Agente: OpenAI `gpt-6-luna`.
- Docker 29.8.0 (Docker Desktop), daemon já ativo, projeto `v080qa`, volumes novos. `BUDGET_LIMIT_USD=0.03` só no shell do `up`, como teto do ledger do volume (gate da fase C). `.env.example` intacto.
- O navegador não foi usado, porque nenhum momento desta rodada passa pela interface.

### Seletor de IDs (fora do repositório)

`.pytest_cache/qa-v080-r1/qa-r6-selector.py` (SHA-256 `946d1a46…fa16`) é uma cópia adaptada do seletor da r5. O original ficou intacto (`qa-r5-selector.py`, `b1d6ef4b…f073`) e foi preservado também como `qa-r5-selector.r5-final.py`, idêntico byte a byte. Ajustes, sem enfraquecer nenhuma guarda:

1. **Allowlists.** A fase A tem só as seis jornadas da T78 no bloco `healthy`; o bloco `tool-down` saiu. A fase B tem cinco blocos `judge-r6-healthy` (6), `judge-r5-healthy` (6), `judge-r5-tool-down` (1), `judge-r4` (9) e `judge-r3` (22), com o filtro exato em `load_recorded_answers`. Os grupos são disjuntos e somam os 44 IDs pré-holdout, e o split esperado é conferido.
2. **Baselines:** primário US$1,18620607 e campanha US$0,62400183. Os deltas precisam ser iguais nos dois ledgers.
3. **Cap:** `fixed_budget_cap = [("v080-qa", 1.4)]`, sidecars 1,4 e 2,0. A CLI roda com `--campaign-cap-usd 1.40 --campaign-estimate docs/evidence/v080-custo-estimativa-r3.json`.
4. **Gates por fase (cumulativos sobre a baseline):** `BUDGET_LIMIT_USD` igual a `1.23620607` (A, +0,05) ou `1.32620607` (B, +0,09). O seletor recusa delta acima do gate. A fase C roda fora do seletor, com teto próprio de 0,03 no ledger do volume.
5. **Reserva do holdout:** o seletor recusa se o cap ficaria abaixo de US$0,40 depois do gate da fase e das fases seguintes. Folga no pior caso: US$0,60599817.
6. **HEAD só com diferença em docs** contra `1baa7b3`. A revisão exigida passou a ser `v080-reviewer-t78.md`.
7. **Mesmo dia**, conferido antes e depois de cada bloco.

Ferramentas offline em `qa-r6-tools/`: `analyze_phase_a.py` (`1529f7dd…09cd`) recompõe o CA-51 com o `_checks` do próprio runner; `aggregate_phase_b.py` (`df2df2bf…7f1d`) agrega a variação do juiz; `docker_smoke.py` faz a pergunta e o smoke contra a API do compose; `ledgers.py`, `seed_dates.py` e `mock_health.py` foram copiados da r5. Antes de qualquer chamada, todos os seis blocos passaram em dry-run (`dryrun-*.json`).

## Blocos

| Bloco | Fase | IDs | Janela | Exit | Situação |
|---|---|---|---|---|---|
| `healthy` | A | 6 jornadas × 3 (18 respostas julgadas) | 07:07:04 – 07:10:34 | 0 | Executado; ambiente válido |
| `judge-r6-healthy` | B | 6 (respostas r6, `1baa7b3`) × 3 | 07:12:03 – 07:12:41 | 0 | Executado |
| `judge-r5-healthy` | B | 6 (respostas r5, `658c70a`) × 3 | 07:12:43 – 07:13:21 | 0 | Executado |
| `judge-r5-tool-down` | B | 1 (respostas r5, `658c70a`) × 3 | 07:13:23 – 07:13:32 | 0 | Executado |
| `judge-r4` | B | 9 (respostas r4, `4c3c8a9`) × 3 | 07:13:34 – 07:14:29 | 0 | Executado |
| `judge-r3` | B | 22 (respostas r3, `f8daab0`) × 3 | 07:14:31 – 07:16:41 | 0 | Executado |
| Docker `v080qa` | C | pergunta com replanejamento + smoke de 10 | 07:18:34 – 07:22:29 | 0 | Executado; `down` às 07:23 |

## CA-51: jornadas de negócio, composição r6 + r5 + r4 (rubrica determinística `passed`)

Proveniência e `request_id` (rep. 1 / 2 / 3):

| Jornada | Origem (SHA) | `request_id` |
|---|---|---|
| `V030-PRICE-DIVERGENCE` | r6 `1baa7b3` | `req_eval2a9a520e8a04`, `req_eval4a4498a05609`, `req_evalef301b110b66` |
| `V030-PRICE-CONDITIONS` | r6 `1baa7b3` | `req_eval73bbbfa91a02`, `req_evalc57aeb6421dd`, `req_eval41e172e7349b` |
| `V030-PT-PRICE-CONDITIONS` | r6 `1baa7b3` | `req_evalf47fb521eee7`, `req_evale2593a93f101`, `req_eval98d1d3ff3a1d` |
| `V030-PRICE-INSUFFICIENT` | r6 `1baa7b3` | `req_evalef8cc9809250`, `req_eval6b988a3011c0`, `req_eval9ad0286fd193` |
| `V030-PT-PRICE-INSUFFICIENT` | r6 `1baa7b3` | `req_eval9b0fda2e2e6d`, `req_evalb1515509bbd4`, `req_eval8642fdadae67` |
| `V030-SALE-CANCELLATION` | r6 `1baa7b3` | `req_evalcf3285dbce64`, `req_eval19ea8b2e9042`, `req_eval0274bce22341` |
| `V030-PRICE-CONSISTENT` | r5 `658c70a`, re-pontuada com os rótulos de `1baa7b3` | `req_eval106d6e104368`, `req_evalc7581d2078b6`, `req_evala7d8baa47bf8` |
| `V030-PT-PRICE-CONSISTENT` | r5 `658c70a`, re-pontuada | `req_eval711b66ed4ef3`, `req_eval351d88745112`, `req_evald8c698c058f0` |
| `V030-PT-SALE-CANCELLATION` | r5 `658c70a`, re-pontuada | `req_eval765140cd8d82`, `req_eval8076dab16a6c`, `req_eval7259f5373b13` |
| `V030-PT-PRICE-DIVERGENCE` | r5 `658c70a`, re-pontuada | `req_eval1e6c25f1a7fc`, `req_eval413aa47e7f79`, `req_eval5fff25a14231` |
| `V030-CONTRACT-TERMINATION` | r5 `658c70a`, re-pontuada | `req_eval806717179b08`, `req_evalb19781c3508e`, `req_eval76a72cd66d5e` |
| `V030-ENABLEMENT-PENDING` | r4 `4c3c8a9`, re-pontuada | `req_evale1a89a023f37`, `req_eval3d621c3a935d`, `req_eval91e4a2574e6e` |
| `V030-PT-ENABLEMENT-PENDING` | r4 `4c3c8a9`, re-pontuada | `req_eval59e2475a935e`, `req_eval2337d8f45ad3`, `req_eval012a5d8ed00f` |

A re-pontuação offline (`analyze_phase_a.py`, `_checks` do runner em `1baa7b3`) não mudou nenhum veredito das 21 respostas r5/r4 (`rescored_changes = []`). Nas 18 respostas r6, o veredito ao vivo e o offline coincidem checagem por checagem (`live_vs_offline_mismatch = []`).

| Repetição | Aprovadas (13) | Juiz `judge.v3` (todos ≥ 4, sem afirmação sem suporte) | Falhas (todas só `content_ok`) |
|---:|---:|---:|---|
| 1 | **13/13** | 13/13 | — |
| 2 | **12/13** | 13/13 | `PT-PRICE-CONDITIONS` (`req_evale2593a93f101`) |
| 3 | **12/13** | 13/13 | `PT-PRICE-INSUFFICIENT` (`req_eval8642fdadae67`) |

**Portão de A atingido: CA-51 ≥ 12/13 nas três repetições.** Nas 18 respostas r6, rota, status, idioma, ferramentas, valores, `forbidden_ok`, fontes e fundamentação passaram 18/18. `PRICE-DIVERGENCE` terminou em `handoff` com protocolo `HO-` nas três repetições. `SALE-CANCELLATION` passou 3/3. Nenhuma resposta contém proibição da lista da T78.

### Falhas analisadas contra a lista P3-7

| `request_id` | Jornada | O que a resposta diz | Está correta? | Lista P3-7 | Leitura |
|---|---|---|---|---|---|
| `req_evale2593a93f101` | `PT-PRICE-CONDITIONS` r2 | A cobrança de 04/11 foi registrada "com um plano diferente do usado como referência"; taxa de referência R$ 36,00, cobrada R$ 37,80, líquido R$ 1.162,20; "Essa diferença nas condições, por si só, não comprova que houve erro na cobrança." | Sim: valores conferem com a seed e o mock, e a proposição esperada (condições diferentes) está presente | Mesma classe de "Há uma diferença entre as condições" e "Os planos diferem" (condições PT). A redação "diferença nas condições" / "plano diferente" não está literalmente na lista | **Falsa recusa** pela régua literal (o rótulo aceita "essa diferença entre as condições", não "nas condições"). Não é defeito de produto. Juiz 5/5/5/5, sem `unsupported_claim` |
| `req_eval8642fdadae67` | `PT-PRICE-INSUFFICIENT` r3 | A venda mais recente em 2 parcelas foi em 03/11 (R$ 200,00); "Não foi possível confirmar uma taxa prevista aplicável nem uma cobrança registrada para comparar"; não confirma erro na taxa | Sim: evidência insuficiente, sem afirmar taxa certa nem errada | Fora da lista (que cobre cancelamento, condições e divergência), mas da mesma classe conservadora: paráfrase correta não listada | **Falsa recusa** pela régua literal (o rótulo tem "não havia uma taxa prevista disponível nem uma cobrança registrada para comparar", não "não foi possível confirmar uma taxa prevista aplicável…"). Não é defeito de produto. Juiz 5/5/5/5, sem `unsupported_claim` |

Lado do produto: as duas respostas dizem o que a jornada espera, com valores e datas certos, sem contradição e sem afirmação proibida. Lado da régua: as duas contam contra o CA-51, como manda o critério determinístico, e mesmo assim o portão passou (12/13). Nenhuma `forbidden_ok` falhou, então a lista P3-7 de proibições conservadoras (cancelamento) não foi acionada nesta rodada. Pela regra do complemento do Supervisor (06h30), as duas falsas recusas novas são P3 da régua literal, sem tarefa de defeito. Ficam registradas para o Developer, se a T78 for reaberta.

## CA-49: replanejamento (rota pelo plano inicial, D16)

Composição da r5 (quatro cenários válidos, sem reexecução nesta rodada), com o comportamento conferido em [v080-d12-pre-holdout-r5.md](v080-d12-pre-holdout-r5.md#ca-49--replanejamento-rota-pelo-plano-inicial-d16-caminho-executado-à-parte):

| ID | Origem | `request_id` (1–3) | Check |
|---|---|---|---|
| `REPLAN-ACCOUNT` | r4 `4c3c8a9` | `req_eval3dd86be708a7`, `req_eval7bd24748ff20`, `req_evaldd20496c84f3` | passa 3/3; `plan_hops` 2 |
| `REPLAN-WEB` | r4 `4c3c8a9` | `req_eval982a8d0d8f87`, `req_eval4cac27bc4e28`, `req_evale71386414772` | passa 3/3; `plan_hops` 1 |
| `REPLAN-PROCEDURE` | r5 `658c70a` | `req_eval36bd78485bbd`, `req_eval95bf18cc51a9`, `req_evale1604956aa56` | passa 3/3; `plan_hops` 0 |
| `REPLAN-TOOL-DOWN` | r5 `658c70a` | `req_eval232ee3607615`, `req_evalda8dcd66c2b2`, `req_eval2579e57de617` | passa 3/3; `plan_hops` 1, `HO-` |

**CA-49 apto:** todas as decisões têm `origin`, e o maior `plan_hops` é 2 (limite 3). `replan.jsonl`, o runner e o produto não mudaram entre `658c70a` e `1baa7b3`, por isso as respostas continuam válidas. Nas 18 respostas r6, o maior `plan_hops` foi 1 (`PRICE-DIVERGENCE`, escalate `rule:support_asked_for_human`). As demais terminaram com `finish` / `rule:complete`. A fase C acrescenta um replanejamento ao vivo no candidato r11 (abaixo).

## Proveniência dos 44 IDs pré-holdout e das conversas

| Origem | SHA | IDs |
|---|---|---|
| r6 | `1baa7b31ed28724a2536ae33a12f11a4d41c4cf8` | `V030-PRICE-DIVERGENCE`, `V030-PRICE-CONDITIONS`, `V030-PT-PRICE-CONDITIONS`, `V030-PRICE-INSUFFICIENT`, `V030-PT-PRICE-INSUFFICIENT`, `V030-SALE-CANCELLATION` |
| r5 | `658c70adc69cb956c931737b8a1caf38ed638dd5` | `V030-PRICE-CONSISTENT`, `V030-PT-PRICE-CONSISTENT`, `V030-PT-SALE-CANCELLATION`, `V030-PT-PRICE-DIVERGENCE`, `V030-CONTRACT-TERMINATION`, `REPLAN-PROCEDURE` ([v080-healthy-r5.json](v080-healthy-r5.json)); `REPLAN-TOOL-DOWN` ([v080-tool-down-r5.json](v080-tool-down-r5.json)) |
| r4 | `4c3c8a98ddfc4f7af7bba877177f3479152159b5` | `EX04`, `EX08`, `NOEV`, `UC13`, `UC14`, `REPLAN-ACCOUNT`, `REPLAN-WEB`, `V030-ENABLEMENT-PENDING`, `V030-PT-ENABLEMENT-PENDING` ([v080-healthy-r4.json](v080-healthy-r4.json)); conversas `FU01`–`FU04` ([v080-conversations-r4.json](v080-conversations-r4.json)) |
| r3 | `f8daab03` | `EX01`–`EX03`, `EX05`–`EX07`, `EX09`, `EX10`, `PT01`–`PT10`, `UC12`, `UC16`–`UC18` ([v080-all-r3.json](v080-all-r3.json)) |

O reaproveitamento das origens r3, r4 e r5 segue a análise de impacto da r5. O delta `658c70a → 1baa7b3` só altera rótulos de jornada, que não entram na execução do agente.

## Juiz

**Fase A (variação do assistente, um julgamento por resposta):** `judge_failed = 0` em 18 julgamentos e `unsupported_claim` 0/18. Médias: groundedness 5,0, factual_correctness 5,0, relevance 5,0, usefulness 4,89. Nenhuma resposta usou web.

**Fase B (variação do juiz, `--judge-repeat 3` sobre a primeira execução):** 44 respostas e 132 julgamentos, com **0 falhas do juiz**. Relatório agregado em [v080-judge-repeat-r6.md](v080-judge-repeat-r6.md) / [.json](v080-judge-repeat-r6.json), com proveniência por resposta, por rota e por split.

| Critério | Média | Desvio | Exata | ±1 |
|---|---:|---:|---:|---:|
| groundedness | 4,68 | 0,13 | 0,856 | 0,992 |
| factual_correctness | 4,67 | 0,14 | 0,841 | 0,992 |
| relevance | 4,81 | 0,16 | 0,818 | 0,985 |
| usefulness | 4,59 | 0,22 | 0,758 | 0,985 |
| `unsupported_claim` (taxa) | 0,061 | — | 0,985 | — |

Por origem, a concordância exata ficou em 1,0 nas respostas r6 (usefulness 0,556) e entre 0,90 e 0,91 nas r5. Nas r4 ficou entre 0,78 e 0,85 e nas r3 entre 0,73 e 0,80. Os 8 julgamentos com `unsupported_claim` estão nas respostas `general_web` da r3: `EX02` 3/3, `PT07` 3/3 e `PT02` 2/3, com médias de 2,5 na rota `general_web`. O juiz não tem o texto da busca web (nota `judge_web_note`), e o primeiro julgamento da r3 já tinha marcado as mesmas três (`v080-all-r3.json`). Fora da web, o juiz é estável: nas rotas de support, knowledge e handoff, a concordância ±1 fica em 1,0. Recortes com menos de 10 casos estão marcados com * (D19).

## Fase C: Docker (momento 9)

| Passo | Observado |
|---|---|
| `BUDGET_LIMIT_USD=0.03 docker compose -p v080qa up --build -d` | exit 0; imagens `v080qa-api`, `v080qa-mocks` e `v080qa-ticketing` (363 MB) construídas; `qdrant/qdrant:v1.19.2` já estava presente. `api` (healthy) publicada só em `127.0.0.1:8000` e `ticketing` em `127.0.0.1:8002`; `mocks` e `qdrant` sem porta no host |
| `/ready` | 200: `ready: true`, app 0.8.0, schema 11, 145 chunks, prompts `replan` 2 e `router` 6, `budget_remaining_usd` 0,0293 depois do índice |
| `POST /messages` sem token | 401 |
| Token (`/v1/auth/token`, `cliente1988`, valores fictícios do `.env.example`, nunca impressos) | 200, Bearer |
| Pergunta mista: "Quando vai cair o dinheiro das vendas de ontem e como faço para antecipar esse valor?" | 200, `req_ad9ea35aeec04e1aa754`, rota `support`, `answered`, pt. A resposta traz o Pix de R$ 80,00 creditado em 04/11, o débito de R$ 148,06 previsto para hoje e o crédito de R$ 1.162,20 previsto para 06/11, "ainda não consegui confirmar" se os dois foram creditados, e o caminho no app (Serviços > Antecipação de Vendas, mínimo R$ 50,00), sem pedir a antecipação. 3 fontes |
| Trace (`GET /traces/req_ad9ea35aeec04e1aa754`) | router `support` → support (`get_receivables_schedule`, `get_payout_status` ok) → **`replan` next `knowledge`, origin `rule:procedure_gap`, hops 1, review `incomplete`** → knowledge → `replan` next `finish`, origin `rule:complete`, review `complete` → personality; `plan_hops` 1 |
| `merchant-assistant smoke --url http://127.0.0.1:8000` | **smoke ok**, 10/10 com 200: knowledge ×5, `general_web` ×2, support ×1, `knowledge_and_support` ×2, todos `answered` |
| `docker compose -p v080qa down` | exit 0; contêineres e rede removidos e `docker ps -a` vazio. Ficam os volumes `v080qa_runtime`, `v080qa_ticketing_runtime` e `v080qa_qdrant_storage` e as imagens `v080qa-*`, para a limpeza do Supervisor |

**Momento 9 apto.** Desta vez o Router mandou a pergunta mista só para o Support, e o `replan` buscou o procedimento no Knowledge por regra, como o momento 2 descreve. A observação O-2 da r5, de que o salto não acontecia porque o plano já nascia `knowledge_and_support`, não se repetiu aqui. Evidência em [v080-smoke-r6.json](v080-smoke-r6.json), sem token nem senha (o script recusa gravar se encontrar um dos dois).

## Custo e ledgers (somente leitura, antes e depois de cada fase)

| Ponto | Primário `data/runtime/budget.sqlite3` (entradas, comprometido) | Campanha `budget-v080-qa.sqlite3` (entradas, comprometido) | Volume Docker `v080qa_runtime` | Reservas |
|---|---|---|---|---|
| Antes (06:53) | 2944, US$1,18620607 | 1328, US$0,62400183 | inexistente (volume novo) | 0 / 0 |
| Depois da fase A (07:12) | 3037, US$1,20511104 | 1421, US$0,64290680 | — | 0 / 0 |
| Depois da fase B (07:16) | 3169, US$1,23848922 | 1553, US$0,67628498 | — | 0 / 0 |
| Depois do `up`, só índice (07:20) | sem mudança | sem mudança | 3, US$0,00074292 | 0 |
| Depois do smoke (07:22) e final (07:23) | 3169, US$1,23848922 | 1553, US$0,67628498 | 53, US$0,02844823 (sidecar 0,03) | 0 / 0 / 0 |

| Fase | Lançamentos | Delta | Por modelo | Gate |
|---|---:|---:|---|---|
| A (`healthy`) | 93 | **US$0,01890497** (igual nos dois ledgers) | deepseek-flash US$0,00973272 (18); gpt-6-luna US$0,00917225 (75) | até US$0,05 |
| B (cinco `judge-*`) | 132 | **US$0,03337818** (igual nos dois ledgers) | deepseek-flash US$0,03337818 (132) | até US$0,09 |
| C (Docker, ledger do volume) | 53 | **US$0,02844823** | gpt-6-luna US$0,02770287 (42); embeddings US$0,00074536 (11) | até US$0,03 |
| **Total r6** | 278 | **US$0,08073138** | — | US$0,17 |

Na fase B, o delta por bloco foi: r6 US$0,00461685, r5 healthy US$0,00470277, r5 tool-down US$0,00066555, r4 US$0,00700317 e r3 US$0,01638984. Na fase C, a pergunta com replanejamento custou US$0,00114305; o resto foi o smoke (as duas buscas web, cerca de US$0,0108 cada) e o índice.

Todos os lançamentos estão `settled`, sem reserva aberta. Cap fixo `v080-qa` US$1,40: o ledger de campanha registra US$0,67628498 comprometidos, com **US$0,72371502 restantes**. Somando o delta do volume Docker à campanha, o consumo efetivo é US$0,70473321 e **restam US$0,69526679**, acima da reserva de US$0,40 do holdout (estimativa US$0,36062993). Primário (sidecar 2,00): restam US$0,76151078 no ledger, ou US$0,73306255 com o Docker. Nenhum gasto ficou fora de uma guarda, a campanha não foi remontada e os sidecars ficaram em 2,0 e 1,4.

## Artefatos (SHA-256)

| Arquivo | SHA-256 |
|---|---|
| [v080-healthy-r6.json](v080-healthy-r6.json) | `6853529c530e6a7cc8bdd6c545d5a3a39f47b99406f6e5c823365201e999c596` |
| [v080-healthy-r6.md](v080-healthy-r6.md) | `0004f847fcf5cf871c55f0a72511ea0fb07a8444ea4cddce2c5d85392c4e6b92` |
| [v080-healthy-traces-r6.json](v080-healthy-traces-r6.json) | `7a3908230afaa2f95a39bd43aa0d56f900e1f162783001635afcc8c4ded611a3` |
| [v080-judge-repeat-r6.json](v080-judge-repeat-r6.json) | `8bf4b0b74d2d86af9ef2d55c6bf22c4f7e2b920a989320e0e7f4fd83c1114359` |
| [v080-judge-repeat-r6.md](v080-judge-repeat-r6.md) | `ad9988f6fbeb73d25b7e8d6df9747b3964a4006549d8f884bd6da2fe3bef0226` |
| [v080-smoke-r6.json](v080-smoke-r6.json) | `4c3f252e63e955751675a7bfa6c2acb21b778697e32336e97877f04d9149ecc1` |
| `qa-r6-results/v080-r6-1baa7b31-judge-r6-healthy.json` / `-judge-r5-healthy.json` / `-judge-r5-tool-down.json` | `1f434572…70ed` / `0bbce1cd…eae7` / `63ea4eb0…bbc0` |
| `qa-r6-results/v080-r6-1baa7b31-judge-r4.json` / `-judge-r3.json` | `f2385e53…8e80` / `9a4da74e…547a` |
| Fontes da fase B (conferidas pelo seletor) | r6 `6853529c…c596`; r5 healthy `b50923c2…9dec`; r5 tool-down `979c9fc6…a430`; r4 `41a3b4d5…a230`; r3 `40b4e63e…1833` |
| `qa-r6-results/phase-a-analysis.json` | `b26dc2cc91d4253e7b3658ac8d9ebc3abf3b626d0e0dcfafd2fa5e147d28f706` |
| `qa-r6-results/healthy.stdout.log` | `17cc69df…4ffb` (stderr vazios em todos os blocos) |
| `qa-r6-results/suite-strict.log` | `75e99ffe8ccf6656d535aede2eb1ac071fb78fe3c0be41605fec362bbb62ed63` |
| `qa-r6-selector.py` / `qa-r5-selector.py` (intacto) | `946d1a46…fa16` / `b1d6ef4b…f073` |

Na pasta de evidência, nos logs da rodada e nos logs do compose, a varredura por `eyJ` e `sk-` deu zero ocorrências.

## Observações

- **O-1:** surgiram duas falsas recusas novas, fora da lista P3-7 literal mas da mesma classe ("diferença nas condições" / "plano diferente"; "não foi possível confirmar uma taxa prevista aplicável nem uma cobrança registrada"). Contam contra o CA-51, e o portão passou mesmo assim. A régua literal continua um passo atrás das redações reais.
- **O-2:** no Docker, a pergunta mista seguiu exatamente o momento 2 (support → `replan` por `rule:procedure_gap` → knowledge). Na campanha r4/r5 a mesma pergunta nasceu `knowledge_and_support`. O plano inicial do Router varia entre execuções, e as duas trajetórias dão a resposta certa.
- **O-3:** o ledger do volume Docker chegou a US$0,02844823 de US$0,03 (`/ready` com US$0,0016 restantes). O smoke de 10 exemplos com duas buscas web cabe no gate, mas com pouca folga.
- **O-4:** o `executed_path` não aparece no corpo de `POST /messages` (veio `null`); o caminho executado fica visível no trace. A D16 o pede no runner, no trace e no relatório, o que é atendido.

## Limitações

- O CA-51 é medido pela checagem determinística (decisão do Supervisor). A leitura pelo juiz (13/13 ×3) aparece só como referência.
- Os 22 IDs da r3, os 9 da r4, os 7 da r5 e as 4 conversas da r4 não foram reexecutados no candidato r11. Valem pela análise de impacto: o delta só toca rótulos de jornada.
- Na fase B, as respostas r3 foram julgadas com o `judge_input` gravado na r3 (antes da T74, sem o protocolo de escalada verificável). As respostas `general_web` não têm o texto da busca no input do juiz.
- A interface Streamlit não foi exercida nesta rodada. O Docker cobriu a API, o smoke e o trace por `curl`/HTTP.
- O seletor e as ferramentas são harness fora do repositório, com os ajustes registrados acima.
- O momento 10 (holdout) e o momento 11 (calibração) ficam para despachos próprios.

## O que a história ensinou sobre o próprio roteiro

- Vale manter a prova "ontem = dia anterior" antes de qualquer gasto e antes e depois de cada bloco. Nesta rodada ela permitiu reaproveitar a seed das 03:50 sem ressemear.
- Separar as fases A, B e C por gate cumulativo de `BUDGET_LIMIT_USD`, com teto próprio no volume Docker, deixou cada custo atribuível e auditável nos três ledgers.
- O momento 2 da história ("Support → replan → Knowledge") acontece de verdade, mas não em toda execução. O roteiro poderia aceitar as duas trajetórias, desde que a resposta junte conta e procedimento.
- A régua literal do momento 8 passou por margem de uma jornada em duas repetições. Cada execução real traz paráfrases corretas novas, o que reforça a pergunta, em aberto com o responsável para a v0.9.0, sobre medir o CA-51 pelo juiz ou por uma combinação.

## Como terminou

O lojista que perguntou se a taxa do Pix de ontem estava divergente ouviu que a regra previa zero e foram cobrados R$ 0,75, e recebeu um protocolo de atendimento nas três vezes. Quem perguntou se o crédito de ontem usou condições diferentes ouviu que sim, que a cobrança usou outro plano, com os valores de referência e os cobrados. Quem perguntou pela taxa em duas parcelas ouviu, sem invenção, que não havia como comparar. Quem pediu o status do cancelamento ouviu que ele foi pedido e ainda não foi processado. No Docker, o lojista entrou com token, perguntou quando caía o dinheiro de ontem e como antecipar, e recebeu numa resposta só os valores e as datas da conta e o caminho no app. O avaliador viu no trace o assistente ir ao Suporte, perceber que faltava o procedimento e buscá-lo no Conhecimento, por regra e com um salto. O smoke de dez perguntas passou. O juiz independente reavaliou três vezes as 44 respostas, foi estável fora das buscas web e não falhou nenhuma vez. A rodada termina apta para o holdout, com o mock e o Docker desligados, os três ledgers conferidos, US$0,69526679 livres no cap e o holdout intacto.
