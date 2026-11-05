# QA v0.8.0 r7: holdout `holdout_v080` (momento 10) e amostra de calibração (momento 11), candidato r11

Data: 2026-11-05 (America/Sao_Paulo)  
Tarefa: [74](../tasks/74-correcao-qa-pre-holdout-v080.md). História: [orquestracao-avaliacao-v080.md](../historias/orquestracao-avaliacao-v080.md), versão 1, momentos 10 e 11. Spec: [orquestracao-avaliacao-v080.md](../specs/orquestracao-avaliacao-v080.md) (D10, D12, D14, D16, D17, D19, CA-50, RF-91/92).  
Resultado: **apto.** O holdout rodou uma única vez em cada fase, e os relatórios saíram completos: na variação do assistente, 75 respostas, todas julgadas, sem falha do juiz; na variação do juiz, 75 julgamentos sem falha. O CSV de calibração foi gerado com 24 respostas, sem scores do juiz. O resultado do holdout é reportado à parte e **não decide a aprovação das jornadas** (o CA-51 já foi composto na r6). Nenhuma correção pode sair dele. Nenhuma tarefa de defeito foi aberta.

## Candidato

| Item | Valor |
|---|---|
| Branch | `codex/v0.8.0-replan`. Não houve checkout, pull, reset nem commit |
| Candidato fixado | `1baa7b31ed28724a2536ae33a12f11a4d41c4cf8` ([manifesto r11](v080-candidato-r11.json), fingerprint `d8e536fe…52eb`) |
| HEAD em toda a rodada | `fa3ab8c73546536b5860554311ad1114aa523954` |
| Diff candidato → HEAD | Só `docs/`. Em `src prompts tests data tools` o diff é vazio, conferido no início e pelo seletor antes de cada bloco |
| Árvore rastreada | Limpa antes e depois. Os não rastreados preexistentes `Claude outputs/`, `_tmp/` e `v/` ficaram intactos. Os novos são só os artefatos desta rodada em `docs/evidence/` |

## Lacre do holdout (conferido sem ler o conteúdo)

| Verificação | Resultado |
|---|---|
| Blob Git de `tests/scenarios/holdout_v080.jsonl` em `9057aaa`, no candidato, no HEAD e na árvore | `22dfee8b33a4169587c8d6e6c29f4a1000ffaf9d` nos quatro. O blob foi conferido de novo depois das duas fases |
| SHA-256 do conteúdo com LF | `91aa51588afdf4afccb1ea8f230a47d3d61686004ec599f4c547e7881b4f1bac`, igual ao de `holdout_v080.sha256` (blob LF `244eb173…ea52`, como no manifesto) |
| Linhas, split e IDs | 25 linhas, todas `holdout_v080`. IDs únicos e disjuntos dos 44 de desenvolvimento, verificados em processo pelo seletor, que imprime só a contagem |

## Seed, ambiente e horários (São Paulo, 05/11)

| Evento | Horário |
|---|---|
| Prova da seed: "ontem" = 2026-11-04, com `sale_1988_0001..0003` em 04/11 (09:42, 13:05, 17:30) e `sale_1988_0005` em 03/11. **Seed válida, sem ressemear** | 07:29:36 |
| Suíte estrita | 07:29:30 – 07:45:57 |
| Mock `127.0.0.1:18765` no ar, com saúde comprovada (`mock-health-00`, `mock-health-H0`) | 07:33 e 07:46:25 |
| Fase H1 (`--repeat 3 --judge --split holdout_v080`) | 07:46:35 – 07:59:43 |
| Fase H2 (`--judge-repeat 3 --answers-from` H1) | 08:00:23 – 08:02:55 |
| Mock encerrado (porta recusa conexão) | 08:03:16 |
| Fase K (`eval-calibrate --sample 24`) | 08:04 |

O seletor conferiu antes e depois de cada bloco que "ontem" continuava sendo 2026-11-04 (`same_local_day: true` nos dois). Nenhuma fase cruzou a meia-noite.

- **Pré-condição:** `python tools/scripts/lint_and_tests.py --strict` (venv 3.13.3, `PYTEST_ADDOPTS=--basetemp=.pytest_cache/qa-r7-suite-basetemp`) deu **1997 passed** em 16m01s, com Ruff e skills ok e exit 0. É o mesmo número do manifesto. Log `1811aa1d…e01c`.
- **Ambiente:** `RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime`, `BUDGET_RUNTIME_DIR=data/runtime`, `MOCK_SERVICES_DIR=data/mock-services`, `MOCKS_URL=http://127.0.0.1:18765` e `BUDGET_LIMIT_USD=1.63848922`, todos só no processo.
- **Modelos:** agente OpenAI `gpt-6-luna`; juiz DeepSeek `deepseek-flash`, `judge@3`, independência `different_provider`.
- **Mock:** a saúde foi comprovada com `/openapi.json` 200, `POST /pricing/simulations` (`sale_1988_0001`) 200 com regra `pricing_mock_v1_debit` e taxa 194, e `GET /charges/sale_1988_0001` 200. O log do mock tem 6 simulações: 2 das sondas e 4 dos casos de preço.
- **Escopo:** Docker, navegador e interface não foram usados, porque os momentos 10 e 11 são de CLI.

### Seletor (fora do repositório)

`.pytest_cache/qa-v080-r1/qa-r7-selector.py` (`d8a4b4d9…a5a`) é uma cópia adaptada do seletor da r6. O original ficou intacto (`qa-r6-selector.py`, `946d1a46…fa16`) e foi preservado também como `qa-r6-selector.r6-final.py`, idêntico byte a byte. Ajustes:

1. **Blocos.** Os blocos são `holdout` e `holdout-judge`, e o seletor não filtra IDs: a própria CLI carrega `holdout_v080.jsonl`. Antes, o seletor confere o lacre: hash LF, `.sha256`, blob, 25 linhas e IDs disjuntos. Depois, confere que o relatório tem exatamente os 25 IDs lacrados.
2. **Baselines.** Primário US$1,23848922 e campanha US$0,67628498. Os deltas precisam ser iguais nos dois ledgers.
3. **Gate e cap.** O gate cumulativo da fase H é de US$0,40 (`BUDGET_LIMIT_USD=1.63848922`), e a estimativa precisa caber nele (US$0,36062993 ≤ 0,40). O cap persistido é `[("v080-qa", 1.4)]`, com sidecars 2,0 e 1,4.
4. **Execução única.** Um marcador `<bloco>.executed` é gravado antes da chamada, e o `--run` recusa o bloco se o marcador ou o relatório já existir.
5. **Extrato dos traces sem texto livre.** O extrato não leva o `reason` do `replan`, que poderia parafrasear a pergunta lacrada.

Os dois blocos passaram em dry-run antes de qualquer chamada (`dryrun-holdout*.json`). A análise offline (`qa-r7-tools/analyze_holdout.py`, `f7d142de…c49c`) imprime só IDs e métricas.

## Fase H1: variação do assistente (3 execuções, juiz 1× por resposta)

CLI: `eval --campaign v080-qa --campaign-cap-usd 1.40 --campaign-estimate docs/evidence/v080-custo-estimativa-r3.json --judge --repeat 3 --split holdout_v080 --name v080-r7-1baa7b31-holdout`. O exit foi 0, com stderr vazio. Saíram 75 respostas e 75 julgamentos gravados em `run_evaluations`, todos `completed` e com `judge_input`. **Nenhuma** resposta foi recusada pela guarda de orçamento.

### Checagem determinística por repetição

A rota é medida pelo plano inicial (D16).

| Rep. | Aprovadas | Rota | Status | Ferram. | Valores | Conteúdo | Proibidos | Fontes | Fundam. | Custo agente |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **20/25** | 0,92 | 0,96 | 0,96 | 0,88 | 0,88 | 1,0 | 0,92 | 0,96 | US$0,0456 |
| 2 | **21/25** | 1,0 | 1,0 | 1,0 | 0,96 | 0,84 | 1,0 | 0,96 | 0,96 | US$0,0314 |
| 3 | **21/25** | 0,92 | 0,96 | 0,96 | 0,96 | 0,84 | 1,0 | 0,92 | 1,0 | US$0,0321 |
| Total | **62/75 (0,827)** | 0,947 | 0,973 | 0,973 | 0,933 | 0,853 | 1,0 | 0,933 | 0,973 | US$0,1091 |

Idioma: 1,0. Por idioma: en 31/36, pt 31/39. Latência: p50 7,6 s e p95 14,7 s. Dos 25 casos, 17 passaram nas três repetições, 6 em uma ou duas e 2 em nenhuma.

### Por rota esperada

A rota esperada é a primeira rota aceita do rótulo.

| Rota esperada | Casos | Aprovadas | Checagens abaixo de 1,0 | Rota inicial observada |
|---|---:|---:|---|---|
| `knowledge` | 6 | 18/18 | — | knowledge 15, knowledge_and_support 3 (aceita) |
| `support` | 10 | 21/30 | conteúdo 0,70, fontes 0,867, valores 0,90, rota 0,90, fundam. 0,933, status/ferram. 0,967 | support 25, knowledge 2, knowledge_and_support 2, clarify 1 |
| `knowledge_and_support` | 3 | 6/9 | valores 0,778, rota/status/ferram./conteúdo/fontes 0,889 | knowledge_and_support 8, clarify 1 |
| `general_web` | 2 | 5/6 | conteúdo 0,833 | general_web 6 |
| `human_handoff` | 2 | 6/6 | — | human_handoff 6 |
| `out_of_scope` | 2 | 6/6 | — | out_of_scope 6 |

### Casos com alguma falha (só IDs e checagens)

| ID | Aprovadas | Checagens que falharam | `request_id` (1 / 2 / 3) |
|---|---:|---|---|
| `HV080-PT-SUP-PRICE-LINK-CONSISTENT` | 0/3 | valores, conteúdo e fontes nas 3; fundamentação em 2. O juiz deu mínimo 4 nas três, sem `unsupported_claim` | `req_eval4a122bfa953c`, `req_evalab42c7a16eeb`, `req_eval76f06007adc7` |
| `HV080-EN-SUP-ENABLEMENT-MASTERCARD-DEVICE` | 0/3 | rep. 1: plano `clarify` (rota, status, ferramentas, conteúdo e fontes); reps. 2 e 3: só conteúdo. Juiz 5 nas três | `req_evalc0b832e106ba`, `req_evale21553d59cfe`, `req_eval4d6756c76ea5` |
| `HV080-PT-SUP-CONTRACT-SETTLEMENT` | 1/3 | reps. 1 e 3: plano inicial `knowledge` (rota e conteúdo), com replanejamento para o Support (`plan_hops` 2 e 1) | `req_eval56ffad6e98b0`, `req_evale23390e54476`, `req_evalce16604abc54` |
| `HV080-EN-KS-WIFI-NEW-PASSWORD` | 2/3 | rep. 3: **erro 500 do provedor no Router**, que degradou para `clarify` / `needs_clarification`. Não houve repetição (execução única) | `req_eval605655092003`, `req_evaldd455e1a5a8c`, `req_evalade604499180` |
| `HV080-PT-KS-CREDIT-DECLINE-NOT-DEVICE` | 2/3 | rep. 1: valores | `req_eval18a663a63adb`, `req_eval5fb2f1ca4f85`, `req_evale41c7999904f` |
| `HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD` | 2/3 | rep. 1: valores. O juiz deu mínimo 2, com `unsupported_claim` | `req_evalbc2cc80d35b5`, `req_evalde20628af4a9`, `req_eval35f94f971a99` |
| `HV080-EN-SUP-PRICE-CREDIT-CONDITIONS` | 2/3 | rep. 2: conteúdo | `req_eval504fe0a1ee86`, `req_eval3c93425c7171`, `req_evalbb607f05fe5b` |
| `HV080-PT-WEB-CURITIBA-RAIN` | 2/3 | rep. 2: conteúdo | `req_evala680c3579e73`, `req_eval62443cae9e89`, `req_eval0c41b1a68f63` |

Estas falhas são resultado de medição do holdout. Não são achados para correção (D14 e D17).

### Replanejamento no holdout (CA-49 como observação, rota pelo plano inicial)

O maior `plan_hops` foi **2**, dentro do limite de 3. A distribuição foi: 0 saltos em 73 respostas, 1 em uma e 2 em uma. As 77 decisões de `replan` têm origem; nenhuma ficou sem origem:

| Decisão / origem | Quantidade |
|---|---:|
| `finish` / `rule:complete` | 49 |
| `support` / `rule:plan_pending` | 13 |
| `finish` / `rule:gap_declared` | 11 |
| `support` / `model` | 2 |
| `web` / `model` | 1 |
| `finish` / `model` | 1 |

Caminho executado, à parte (`executed_path`):

| Rota inicial → caminho executado | Respostas |
|---|---:|
| `support` → `customer_support` | 25 |
| `knowledge` → `knowledge` | 15 |
| `knowledge_and_support` → `knowledge → customer_support` | 13 |
| `human_handoff` → `escalation` | 6 |
| `general_web` → `knowledge` | 6 |
| `out_of_scope` (vazio) | 6 |
| `clarify` (vazio) | 2 |
| `knowledge` → `knowledge → customer_support` | 1 |
| `knowledge` → `knowledge → customer_support → web` | 1 |

### Juiz na fase H1

O juiz avaliou cada resposta uma vez: 75 julgamentos, `judge_failed = 0`.

| Rep. | groundedness | factual_correctness | relevance | usefulness | `unsupported_claim` | Todos ≥ 4, sem afirmação sem suporte |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4,56 | 4,52 | 4,80 | 4,68 | 2 | 20/25 |
| 2 | 4,80 | 4,72 | 5,00 | 4,64 | 1 | 23/25 |
| 3 | 4,64 | 4,60 | 4,68 | 4,60 | 3 | 20/25 |
| Total | 4,67 | 4,61 | 4,83 | 4,64 | **6/75 (0,08)** | 63/75 |

Variação do assistente (bloco `variation`, 3 execuções):

| Critério | Média | Desvio | Exata | ±1 |
|---|---:|---:|---:|---:|
| groundedness | 4,67 | 0,15 | 0,867 | 0,960 |
| factual_correctness | 4,61 | 0,18 | 0,880 | 0,933 |
| relevance | 4,83 | 0,25 | 0,773 | 0,960 |
| usefulness | 4,64 | 0,34 | 0,693 | 0,933 |
| `unsupported_claim` (taxa) | 0,08 | — | 0,920 | — |

As médias do juiz por rota esperada foram:

- **support:** 4,87 / 4,83 / 4,83 / 4,63, sem `unsupported_claim`.
- **knowledge:** 4,5 / 4,5 / 4,89 / 4,83, com 3 `unsupported_claim`, todos em `HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION`, que passou 3/3 na checagem determinística.
- **knowledge_and_support:** 4,89 / 4,67 / 4,56 / 4,44, com 1 `unsupported_claim`.
- **general_web:** 3,17 / 3,0 / 4,67 / 4,0, com 2 `unsupported_claim`.
- **human_handoff e out_of_scope:** 5 / 5 / 5 / 4,83, sem `unsupported_claim`.

Sete respostas usaram busca web, e o juiz as avaliou sob a nota de que não tem o texto da busca (`judge_web_note`). Duas delas foram marcadas com `unsupported_claim`. Na variação do assistente, o bloco `by_route` agrupa pela rota observada; os recortes com menos de 10 casos são indicativos (D19).

## Fase H2: variação do juiz (`--judge-repeat 3` sobre a primeira execução)

CLI: `eval --campaign v080-qa --campaign-cap-usd 1.40 --campaign-estimate … --judge-repeat 3 --answers-from qa-r7-results/v080-r7-1baa7b31-holdout.json --name v080-r7-1baa7b31-holdout-judge`. O exit foi 0, com stderr vazio. Foram 25 respostas e **75 julgamentos, sem nenhuma falha do juiz**. Os `request_id` são os mesmos da repetição 1 da H1.

| Critério | Média | Desvio | Exata | ±1 |
|---|---:|---:|---:|---:|
| groundedness | 4,61 | 0,13 | 0,853 | 0,987 |
| factual_correctness | 4,59 | 0,13 | 0,880 | 0,973 |
| relevance | 4,80 | 0,14 | 0,840 | 1,000 |
| usefulness | 4,60 | 0,16 | 0,813 | 1,000 |
| `unsupported_claim` (taxa) | 0,107 | — | 0,973 | — |

Houve 8 julgamentos com `unsupported_claim`: `HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION` 3/3, `HV080-PT-WEB-CURITIBA-RAIN` 3/3 e `HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD` 2/3. Por rota observada:

- **support (7 casos):** concordância exata ≥ 0,81 e ±1 de 1,0.
- **human_handoff, out_of_scope e clarify:** ±1 de 1,0.
- **knowledge (6):** exata 0,778 e ±1 de 1,0.
- **knowledge_and_support (5):** exata entre 0,80 e 0,867 e ±1 a partir de 0,867.
- **general_web (2*):** médias de 2,83 / 2,67 / 4,83 / 3,83, com `unsupported_claim` em 0,5.

O juiz é estável fora da web, como na r6. A web continua sendo a fonte das notas baixas, porque o juiz não recebe o texto da busca.

## Comparação com o desenvolvimento (só referência, não aprovação)

| Recorte | Fonte | Aprovadas (determinística) | groundedness | factual | relevance | usefulness | `unsupported_claim` |
|---|---|---:|---:|---:|---:|---:|---:|
| `holdout_v080`, variação do assistente | r7, `1baa7b3` | 0,827 (62/75) | 4,67 | 4,61 | 4,83 | 4,64 | 0,08 |
| `dev`, variação do assistente | r3, `f8daab03`, 27 casos × 3 | 0,815 (66/81) | 4,54 | 4,60 | 4,81 | 4,54 | 0,16 |
| `holdout` legado, variação do assistente | r3, `f8daab03`, 17 × 3 | 0,922 (47/51) | 4,59 | 4,65 | 4,69 | 4,51 | 0,118 |
| `holdout_v080`, variação do juiz | r7 | — | 4,61 (exata 0,853) | 4,59 (0,880) | 4,80 (0,840) | 4,60 (0,813) | 0,107 |
| `dev`, variação do juiz | r6, composição r3–r6, 27 casos | — | 4,72 (0,877) | 4,73 (0,901) | 4,88 (0,840) | 4,58 (0,753) | 0,037 |
| `holdout` legado, variação do juiz | r6, 17 casos | — | 4,63 (0,824) | 4,57 (0,745) | 4,71 (0,784) | 4,61 (0,765) | 0,098 |

Esta é uma leitura descritiva e não aprova nada.

- **Taxa determinística.** A do `holdout_v080` (0,827) ficou no nível do `dev` da r3 (0,815) e abaixo do `holdout` legado (0,922).
- **Notas do juiz.** Ficaram na mesma faixa do desenvolvimento, de 4,6 a 4,8.
- **Dispersão.** O desvio do assistente foi menor que o do `dev` da r3 (groundedness 0,15 contra 0,34).
- **`unsupported_claim` na variação do juiz.** Foi mais alta que no `dev` da r6 (0,107 contra 0,037), concentrada em três casos pt, dois deles com web ou procedimento.

Ressalvas: a referência `dev` da variação do assistente é a r3, de outro candidato, porque a r4–r6 só reexecutaram subconjuntos. O CA-51 (jornadas) não entra aqui.

## Fase K: amostra de calibração (momento 11)

- **Comando:** `RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime merchant-assistant eval-calibrate --sample 24 --from docs/evidence/v080-all-r3.json`, com exit 0 e stderr vazio. Nenhuma chamada paga: os ledgers ficaram em 3632 / 2016 entradas.
- **Fonte:** [v080-all-r3.json](v080-all-r3.json) é o único relatório da CLI com as 44 respostas de desenvolvimento julgadas: 27 `dev` e 17 `holdout` legado, em 12 estratos de rota × split. Os relatórios r4 a r6 são subconjuntos, e o `v080-judge-repeat-r6.json` é uma composição do harness, sem `cases`. As 44 `request_id` ligam ao primeiro julgamento `cli:eval` gravado no banco do runtime QA, o mesmo `evaluation_id` do relatório. O `holdout_v080` não entra (D17), e a CLI confirma isso.
- **Saída:** [v080-calibracao-amostra.csv](v080-calibracao-amostra.csv) (`52e47417…4d9c`), em UTF-8 com BOM e separador `;`. Tem 11 linhas `#` de instruções, com a rubrica dos quatro critérios, `unsupported_claim` sim/nao e a linha `# amostra: campanha=v080-all-r3; semente=20261104; origem=v080-all-r3.json; sorteadas=24; pedidas=24; elegiveis=44; splits=dev+holdout; rubrica=judge.v3`.
- **Composição:** 24 linhas, sendo 11 `dev` e 13 `holdout` legado. Os **12 estratos estão todos presentes**: knowledge (dev 3, holdout 3), support (dev 3, holdout 2), knowledge_and_support (dev 2, holdout 2), general_web (dev 2, holdout 2), human_handoff (dev 1, holdout 1), out_of_scope (holdout 2) e clarify (holdout 1).
- **Colunas:** as seis do avaliador (`groundedness`, `factual_correctness`, `relevance`, `usefulness`, `unsupported_claim`, `note`) estão vazias. Não há `evaluation_id`, scores nem nome do juiz, e nenhum `HV080`.

**O que o responsável precisa fazer (cerca de 1 h):**

1. Abrir `docs/evidence/v080-calibracao-amostra.csv` na planilha e ler as instruções `#` do topo.
2. Em cada linha, dar de 1 a 5 em `groundedness`, `factual_correctness`, `relevance` e `usefulness` e marcar `sim` ou `nao` em `unsupported_claim`, julgando só a resposta contra a evidência mostrada. `note` é opcional. Não apagar colunas nem as linhas `#`.
3. Salvar como **CSV UTF-8** com o mesmo separador `;`.
4. Importar no banco onde os julgamentos estão, **sem chamada paga**: `RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime merchant-assistant eval-calibrate --import docs/evidence/v080-calibracao-amostra.csv`. A campanha vem da linha `amostra:` (`v080-all-r3`) e o avaliador padrão é `owner`. O relatório sai em `docs/evidence/v080-calibracao.md`, com concordância exata, ±1 e kappa ponderado por critério e a ressalva de amostra pequena (D19).
5. **Preservar** `.pytest_cache/qa-v080-r1/runtime/merchant.sqlite3` até o import. `limpar-ambiente.ps1` só remove diretórios `*-runtime` no topo de `.pytest_cache`, e esse banco não está entre eles, mas não pode ser recriado.

## Custo e ledgers (somente leitura, antes e depois de cada fase)

| Ponto | Primário `data/runtime/budget.sqlite3` (entradas, comprometido) | Campanha `budget-v080-qa.sqlite3` (entradas, comprometido) | Reservas |
|---|---|---|---|
| Antes (07:29 e 07:46) | 3169, US$1,23848922 | 1553, US$0,67628498 | 0 / 0 |
| Depois da H1 (07:59) | 3557, US$1,38318733 | 1941, US$0,82098309 | 0 / 0 |
| Depois da H2 (08:03) e depois da K | 3632, US$1,40251813 | 2016, US$0,84031389 | 0 / 0 |

| Fase | Lançamentos | Delta (igual nos dois ledgers) | Por modelo | Estimativa / gate |
|---|---:|---:|---|---|
| H1, agente ×3 com juiz | 388 | **US$0,14469811** | gpt-6-luna US$0,10911538 (283); deepseek-flash US$0,03556535 (75); text-embedding-3-small US$0,00001738 (30) | — |
| H2, juiz ×3 | 75 | **US$0,01930800** | deepseek-flash US$0,01930800 (75) | — |
| K, CSV | 0 | US$0 | — | — |
| **Total r7** | 463 | **US$0,16402891** | — | estimativa US$0,36062993; gate US$0,40 |

Todos os lançamentos estão `settled`, sem reserva aberta. Sidecars em 2,0 e 1,4, cap persistido `[("v080-qa", 1.4)]`, sem remontagem.

- **Cap `v080-qa` (US$1,40).** O ledger da campanha registra US$0,84031389 comprometidos, com **US$0,55968611 restantes**. Somando o volume Docker da r6 (US$0,02844823, fora do ledger), o consumo efetivo da campanha é US$0,86876212 e **restam US$0,53123788**.
- **Contingência.** O gasto da campanha não passou de US$1,10; portanto **nada** da contingência de US$0,30 foi consumido.
- **Primário (US$2,00).** Restam US$0,59748187, ou US$0,56903364 com o Docker.

## Artefatos (SHA-256)

| Arquivo | SHA-256 |
|---|---|
| [v080-avaliacao-holdout-r7.json](v080-avaliacao-holdout-r7.json) (cópia de `qa-r7-results/v080-r7-1baa7b31-holdout.json`) | `bc009058f292f0752e932221671967d71dfca20628b4c8f5728a6964371a5c0e` |
| [v080-avaliacao-holdout-r7.md](v080-avaliacao-holdout-r7.md) | `bd9ff057b480324af9e7c971f5a46d0a99c508cb03c97645acf29210547a4903` |
| [v080-avaliacao-holdout-judge-repeat-r7.json](v080-avaliacao-holdout-judge-repeat-r7.json) (cópia de `…-holdout-judge.json`) | `8ffff2c19855fc234c0be02cdbda6ab09f3153e37f890b75896821f6b1c3afe7` |
| [v080-avaliacao-holdout-judge-repeat-r7.md](v080-avaliacao-holdout-judge-repeat-r7.md) | `d1097d3a3eaaa1d9f110e96cd14d0ebe01e1d3fd8e6efeeb9166a76d67b5f5d4` |
| [v080-holdout-traces-r7.json](v080-holdout-traces-r7.json) (rota inicial, passos, origem e saltos, sem texto livre) | `bb4c6f507f4ea3c812b679643e2b69d6853a590c21bc817e5c60ec442542fffb` |
| [v080-calibracao-amostra.csv](v080-calibracao-amostra.csv) | `52e474173ad44d5f9fe46283ca6f7af58fadc1da9154825afa039365b81d4d9c` |
| `qa-r7-results/holdout-analysis.json` | `5cc8f47961f29df698e6276978bd6f5d952c59939e59473d252e52187d8f54fe` |
| `qa-r7-results/holdout.stdout.log` / `holdout-judge.stdout.log` (stderr vazios) | `4391882a…96d2` / `c3584276…0330` |
| `qa-r7-results/suite-strict.log` | `1811aa1d56295b4931d0c0a4f6f7f95a967b3e384e07be965182a0a71d0de01c` |
| `qa-r7-selector.py` / `qa-r6-selector.py` (intacto) | `d8a4b4d9…a5a` / `946d1a46…fa16` |

Os nomes das cópias usam o prefixo `v080-avaliacao-` para não colidir com este parecer. Na pasta de evidência e nos logs da rodada, a varredura por `eyJ…` e `sk-…` deu zero ocorrências.

**Atenção ao versionar:** os relatórios da CLI (`v080-avaliacao-holdout-*r7.json/.md`) trazem, por desenho da CLI, a mensagem de cada caso do holdout, a resposta do agente e a justificativa do juiz. Os rótulos não vão junto. Este parecer e o extrato de traces só trazem IDs e métricas. Fica com o Supervisor decidir se essas duas cópias são versionadas como estão.

## Observações

- **O-1.** O erro 500 do provedor no Router (`req_evalade604499180`, `HV080-EN-KS-WIFI-NEW-PASSWORD`, rep. 3) foi absorvido: a resposta saiu como pedido de esclarecimento, sem dado inventado. Pela regra de execução única, essa resposta conta como falha no holdout.
- **O-2.** As notas baixas do juiz continuam concentradas na web: `general_web` teve 2,83 e 2,67 em fundamentação e correção na variação do juiz. É a mesma limitação da r6 (o juiz não tem o texto da busca).
- **O-3.** Em `HV080-PT-SUP-PRICE-LINK-CONSISTENT`, a checagem determinística reprovou as três respostas (valores, conteúdo e fontes), mas o juiz deu mínimo 4. Régua e juiz divergem. Fica como dado para a calibração e para a pergunta sobre o CA-51 em aberto; não leva a nenhum ajuste (D14).
- **O-4.** `general_web` aparece com `executed_path` = `knowledge`, porque a busca web é feita pelo nó de conhecimento. É coerente com o trace, mas pode confundir quem lê só o caminho.

## Limitações

- O holdout foi visto. Pela D17, qualquer rodada de QA depois desta marca "holdout já visto", e este resultado não decide aprovação.
- A comparação com o `dev` usa a variação do assistente da r3 (candidato `f8daab03`) e a do juiz composta na r6. Não há `dev` completo com 3 execuções no candidato r11.
- A amostra de calibração sai de respostas da r3, julgadas com o `judge_input` anterior à T74. O que se calibra é o juiz `judge@3` sobre aquela evidência. Com 24 respostas, concordância e kappa são indicação, não prova (D19).
- O seletor e a análise são harness fora do repositório, com os ajustes registrados acima.
- Docker e interface não fazem parte destes momentos e não foram exercidos.

## O que a história ensinou sobre o próprio roteiro

- Vale o seletor gravar o marcador de execução única **antes** da chamada. Assim, a regra "uma única execução" da D17 deixa de depender de disciplina e passa a ser uma guarda.
- O momento 11 não diz de qual relatório sai a amostra. Na prática só o relatório completo da r3 cobre `dev` e `holdout` legado. O roteiro poderia nomear a fonte e o banco do `--import`.
- O roteiro do momento 10 poderia prever o que fazer com falha transitória do provedor numa execução que não pode ser repetida. Nesta rodada, ela foi contada como resultado.

## Como terminou

O avaliador técnico rodou, uma única vez, as 25 perguntas que ninguém tinha usado para ajustar o assistente, cada uma três vezes. O lojista recebeu resposta certa em 62 das 75 tentativas pela régua literal. Nas perguntas de conhecimento, encaminhamento e fora de escopo, acertou todas. Nas de conta, acertou 21 de 30. Uma vez o provedor do modelo caiu, e o assistente pediu esclarecimento em vez de inventar. O replanejamento nunca passou de dois saltos, e cada decisão tem origem. O juiz de outro provedor avaliou tudo, depois reavaliou três vezes as primeiras respostas, sem falhar nenhuma vez. Fora da web, foi estável. Na web e em três perguntas em português, apontou afirmações sem suporte. A amostra de 24 respostas para o responsável calibrar o juiz está pronta, sem as notas dele. A rodada termina apta, com o mock desligado, os ledgers conferidos, US$0,53 livres no cap e o holdout lacrado e intacto.
