# QA D12 pré-holdout — v0.8.0 r5 (reteste dirigido, candidato r7)

Data: 2026-11-05 (America/Sao_Paulo)  
Tarefa: [74](../tasks/74-correcao-qa-pre-holdout-v080.md), com [75](../tasks/75-rotulo-literal-price-insufficient-v080.md), [76](../tasks/76-encerramento-contrato-pede-esclarecimento-v080.md) e [77](../tasks/77-teto-contingencia-v080-qa.md). História: [orquestracao-avaliacao-v080.md](../historias/orquestracao-avaliacao-v080.md), versão 1, momentos 7, 8 e 9 (e 1 a 4 pela campanha).  
Resultado: **reprovado na fase A**. CA-49 passa: os quatro cenários são válidos, 3/3 cada, com origem em todas as decisões e `plan_hops` ≤ 2. O portão do CA-51 não foi atingido: as jornadas compostas ficaram em **11/13, 8/13 e 10/13**. Todas as falhas são só `content_ok`, ou seja, a régua literal recusou respostas corretas. Como o portão de A falhou, **as fases B e C não foram executadas**. Defeito: [tarefa 78](../tasks/78-regua-literal-ca51-recusa-respostas-corretas-v080.md). O holdout não foi lido nem executado.

## Candidato

| Item | Valor |
|---|---|
| Branch | `codex/v0.8.0-replan` (sem checkout, pull, reset ou commit nesta rodada) |
| Candidato fixado | `658c70adc69cb956c931737b8a1caf38ed638dd5` ([manifesto r7](v080-candidato-r7.json), fingerprint `3316002e…d2`) |
| HEAD em toda a rodada | `3894e3648c4cef402cfb7094e4373f26249eef3f` |
| Diff candidato → HEAD | só `docs/evidence/v080-candidato-r7.json`, `v080-orcamento-contingencia.md` e `v080-reviewer-t75-77.md`. Em `src prompts tests data tools` o diff é vazio, conferido antes de cada bloco pelo seletor |
| Revisão | [v080-reviewer-t75-77.md](v080-reviewer-t75-77.md), rodada 3: apto para QA |
| Holdout `holdout_v080` | não lido nem executado |
| Árvore rastreada | limpa antes e depois. Os não rastreados `Claude outputs/`, `_tmp/` e `v/` preexistiam e ficaram intactos |

## Seed e horários (São Paulo, 05/11)

| Evento | Horário |
|---|---|
| Seed vencida conferida (somente leitura): `sale_1988_0001..0003` datadas 2026-11-03 | 03:49 |
| Backup do runtime antes de ressemear (`merchant`, `traces`, `checkpoints`) em `qa-r5-results/runtime-backup-before-reseed/` (`merchant.sqlite3` `04a04d5a…da30`) | 03:50 |
| `bootstrap` no runtime isolado; a coleção `getnet_kb_v1` existia e o índice estava atual, sem reindexar e sem custo | 03:50:08 – 03:50:10 |
| Prova sem custo: as vendas de "ontem" `sale_1988_0001..0003` ficaram datadas 2026-11-04, os recebíveis `rcv_1988_0001` em 05/11 e `rcv_1988_0002` em 06/11, e `sale_1988_0005` (a mais recente em 2 parcelas) em 03/11 | 03:50 |
| Suíte estrita | 03:48:05 – 03:59:26 |
| Bloco `healthy` | 04:00:24 – 04:07:15 |
| Bloco `tool-down` | 04:08:08 – 04:08:51 |

O seletor reconferiu antes e depois de cada bloco que "ontem" = 2026-11-04 e que as três vendas estão nesse dia (`same_local_day: true` nos dois blocos). Nenhuma fase cruzou a meia-noite.

## Ambiente

- Pré-condição: `python tools/scripts/lint_and_tests.py --strict` (venv 3.13.3, `--basetemp=.pytest_cache/qa-r5-suite-basetemp`) deu **1379 passed** em 10m49s, o mesmo número do manifesto, com Ruff e skills ok e exit 0. Log `288c7ac5…b325`.
- `RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime`, `BUDGET_RUNTIME_DIR=data/runtime`, `MOCK_SERVICES_DIR=data/mock-services`. Saídas em `.pytest_cache/qa-v080-r1/qa-r5-results/`. Gate da fase A no processo: `BUDGET_LIMIT_USD=1.34385079`.
- Mock oficial de preços com a venv em `127.0.0.1:18765`. Saúde comprovada antes do bloco `healthy` (`mock-health-A-healthy.json`): `/openapi.json` 200, `POST /pricing/simulations` (`sale_1988_0001`) 200 com regra `pricing_mock_v1_debit` e taxa 194, `GET /charges/sale_1988_0001` 200. O preflight do seletor repetiu a checagem do OpenAPI. O mock foi encerrado no fim e nenhum processo Python ficou ativo.
- `tool-down`: `MOCKS_URL=http://127.0.0.1:18766` no subprocesso, com conexão recusada comprovada (`mock-health-A-tooldown.json`). No Windows a recusa chega depois de cerca de 2 s, por isso o timeout das sondas foi de 0,7 s para 5 s (ver o seletor).
- Juiz: DeepSeek `deepseek-flash`, `judge@3`, independência `different_provider`. Agente: OpenAI `gpt-6-luna`.
- Docker, navegador, `--judge-repeat` e holdout não foram usados, porque o portão de A não foi atingido.

### Seletor de IDs (fora do repositório)

`.pytest_cache/qa-v080-r1/qa-r5-selector.py` (SHA-256 `b1d6ef4b…f073`) é uma cópia adaptada do seletor da r4. O da r4 ficou intacto (`qa-r4-selector.py`, `4c5e970a…071a`) e foi preservado também como `qa-r4-selector.r4-final.py`, idêntico byte a byte. Ajustes, sem enfraquecer nenhuma guarda:

1. **Allowlist.** Fase A: 12 IDs no bloco `healthy` e `REPLAN-TOOL-DOWN` no bloco `tool-down`. Blocos da fase B preparados (`judge-r5-*`, `judge-r4`, `judge-r3`, com o filtro exato em `load_recorded_answers`), mas não executados. O bloco de conversas foi removido. O seletor confere que os quatro arquivos de cenário contêm exatamente os 44 IDs pré-holdout, com o split esperado.
2. **Baselines:** primário US$1,14385079 e campanha US$0,58164655. Os deltas precisam ser iguais nos dois ledgers.
3. **Cap:** `fixed_budget_cap = [("v080-qa", 1.4)]`, sidecars 1,4 e 2,0; a CLI roda com `--campaign-cap-usd 1.40 --campaign-estimate docs/evidence/v080-custo-estimativa-r3.json`.
4. **Gates por fase (P3-77a):** exige `BUDGET_LIMIT_USD` igual a `1.34385079` (A) ou `1.43385079` (B) e recusa um delta acumulado acima do gate.
5. **Reserva do holdout:** recusa quando o cap ficaria abaixo de US$0,40 depois do gate da fase e das fases seguintes. Folga no pior caso: US$0,49835345.
6. **HEAD só com diferença em docs** contra `658c70a`, com `src prompts tests data tools` limpos. Mantido o ajuste 2 da r4: o filtro só vale em `cmd_eval`, e a revalidação da estimativa vê o conjunto completo. A CLI aceitou a estimativa nos dois blocos.
7. **Mesmo dia:** o dia-base da seed é conferido antes e depois de cada bloco. Os traces passam a ser extraídos por `request_id` logo depois de cada bloco.

A primeira tentativa do bloco `healthy`, às 04:00, parou no preflight do próprio seletor (`UnboundLocalError` de import), antes de abrir qualquer ledger. Os ledgers não mudaram, e o log ficou em `healthy-attempt1-preflight-error.*`. Depois da correção do import, o bloco rodou. A seleção exata aparece no stdout de cada bloco (`case_ids`) e em `config.cases` dos JSON: 12 casos e 36 linhas no `healthy`, 1 caso e 3 linhas no `tool-down`.

## Blocos

| Bloco | IDs | Janela (São Paulo) | Exit | Situação |
|---|---|---|---|---|
| `healthy` | 12 IDs × 3 (36 respostas julgadas) | 04:00:24 – 04:07:15 | 0 | Executado; ambiente válido |
| `tool-down` | `REPLAN-TOOL-DOWN` × 3 (3 julgadas) | 04:08:08 – 04:08:51 | 0 | Executado; falha de conexão real da ferramenta de preços |
| Fase B (`--judge-repeat 3`) | — | — | — | **Não executada** (portão de A) |
| Fase C (smoke Docker) | — | — | — | **Não executada** (portão de A) |

## CA-51 — jornadas de negócio, composição r5 + r4 (rubrica determinística `passed`, a mesma da r3 e da r4)

Proveniência: 11 jornadas com as respostas da r5 (`658c70a`, `v080-healthy-r5.json`). `ENABLEMENT-PENDING` EN/PT vêm da r4 (`4c3c8a9`, `v080-healthy-r4.json`; `req_evale1a89a023f37`, `req_eval3d621c3a935d`, `req_eval91e4a2574e6e`, `req_eval59e2475a935e`, `req_eval2337d8f45ad3`, `req_eval012a5d8ed00f`, todas aprovadas).

| Repetição | Aprovadas (13) | Sem `content_ok` | Juiz `judge.v3` (todos ≥ 4, sem afirmação sem suporte) | r3 | Falhas (todas só `content_ok`) |
|---:|---:|---:|---:|---:|---|
| 1 | **11/13** | 13/13 | 13/13 | 9/13 | `PRICE-DIVERGENCE` (`req_eval531ac9146987`); `PT-PRICE-INSUFFICIENT` (`req_evalaf77a604682c`) |
| 2 | **8/13** | 13/13 | 13/13 | 11/13 | `PRICE-CONDITIONS` (`req_eval64b06f9b7f24`); `PRICE-DIVERGENCE` (`req_evalb84c1106aea3`); `PRICE-INSUFFICIENT` (`req_eval3180af09b4e0`); `SALE-CANCELLATION` (`req_eval932e426373de`); `PT-PRICE-CONDITIONS` (`req_eval45e5804e758a`) |
| 3 | **10/13** | 13/13 | 13/13 | 10/13 | `PRICE-DIVERGENCE` (`req_eval9a0b07470114`); `PRICE-INSUFFICIENT` (`req_evalb8354030edbd`); `PT-PRICE-INSUFFICIENT` (`req_eval025b4ed82d6f`) |

**CA-51 reprovado pela rubrica determinística** nas três repetições. Leitura das falhas, com o texto completo na [tarefa 78](../tasks/78-regua-literal-ca51-recusa-respostas-corretas-v080.md):

- Em todas as 10 respostas a proposição esperada aparece com outra redação. Exemplos: "found a difference… expected fee R$ 0,00, recorded R$ 0,75"; "used different pricing plans"; "no expected fee or recorded charge was available"; "não há evidências suficientes para comparar" (o rótulo só tem o singular); "request to cancel… received, but… not processed yet" (o rótulo exige "requested"). Nenhuma afirma o contrário do esperado. `forbidden_ok` passou em 36/36.
- O juiz deu 5 em todos os critérios dessas respostas (usefulness 4 em uma) e `unsupported_claim = false`.
- **Os defeitos da r4 estão corrigidos no comportamento:** `CONTRACT-TERMINATION` saiu em `human_handoff`, `handoff` e com protocolo `HO-` nas três repetições (`req_eval806717179b08`, `req_evalb19781c3508e`, `req_eval76a72cd66d5e`). A nota `rule` não aparece no trace porque o próprio modelo escolheu encaminhar, e a regra da T76 não precisou atuar. `PRICE-INSUFFICIENT` EN/PT passou 1/3 em cada idioma; as quatro redações da T75 passam, mas surgiram redações novas.
- As jornadas datadas, inválidas na r4, agora usam as vendas certas de 04/11: valores, ferramentas e status passam em 100%. `PRICE-CONSISTENT` EN/PT e `PT-PRICE-DIVERGENCE` e `PT-SALE-CANCELLATION` passaram 3/3.

## CA-49 — replanejamento (rota pelo plano inicial, D16; caminho executado à parte)

| ID | Origem | Rep. | `request_id` | Rota inicial | `executed_path` / decisões `replan` (next, origin, hops) | `plan_hops` | Check |
|---|---|---:|---|---|---|---:|---|
| `REPLAN-ACCOUNT` | r4 `4c3c8a9` | 1–3 | `req_eval3dd86be708a7`, `req_eval7bd24748ff20`, `req_evaldd20496c84f3` | knowledge | knowledge → customer_support → web; support (`model`, 1) → web (`model`, 2) → finish (`rule:gap_declared`) | 2 | passa 3/3 |
| `REPLAN-WEB` | r4 `4c3c8a9` | 1–3 | `req_eval982a8d0d8f87`, `req_eval4cac27bc4e28`, `req_evale71386414772` | knowledge | knowledge → web; web (`rule:evidence_insufficient_web`, 1) → finish (`rule:gap_declared` ou `rule:complete`) | 1 | passa 3/3 |
| `REPLAN-PROCEDURE` | r5 `658c70a` | 1–3 | `req_eval36bd78485bbd`, `req_eval95bf18cc51a9`, `req_evale1604956aa56` | knowledge_and_support | knowledge → customer_support; support (`rule:plan_pending`, 0) → finish (`rule:complete` ou `rule:gap_declared`); `get_receivables_schedule` e `get_payout_status` ok | 0 | passa 3/3 (valores 14806 e 116220, crédito "ainda não confirmado", app) |
| `REPLAN-TOOL-DOWN` | r5 `658c70a` | 1–3 | `req_eval232ee3607615`, `req_evalda8dcd66c2b2`, `req_eval2579e57de617` | support | customer_support → escalation; `simulate_pricing` com erro `TIMEOUT` (porta 18766 recusada); escalate (`rule:support_asked_for_human`, 1) | 1 | passa 3/3, `handoff` com `HO-20261105-…`, sem `SIM-`/"simul" |

**CA-49 apto:** os quatro cenários passam com ambiente válido, cada decisão registra `origin` e o maior `plan_hops` é 2 (limite 3). Nos 39 traces da r5, o maior `plan_hops` foi 1. A falha de `TOOL-DOWN` vem agora da ferramenta de preços indisponível, porque a venda de "ontem" existe. As respostas dizem que a consulta de preços não respondeu e encaminham com protocolo, sem inventar a taxa. Traces em [v080-healthy-traces-r5.json](v080-healthy-traces-r5.json) e [v080-tool-down-traces-r5.json](v080-tool-down-traces-r5.json).

## Reaproveitamento e análise de impacto

- **r4 (`4c3c8a9`), 9 IDs e 4 conversas:** `EX04`, `EX08`, `NOEV`, `UC13`, `UC14`, `REPLAN-ACCOUNT`, `REPLAN-WEB`, `V030-ENABLEMENT-PENDING`, `V030-PT-ENABLEMENT-PENDING`, todos aprovados 3/3 na r4 com ambiente válido, e `FU01`–`FU04` (4/4). O delta `4c3c8a9 → 658c70a` em `src prompts tests/scenarios data` atinge `router.py` (T76), `runner.py` (T75, só medição), `cli.py` e `budget.py` (T77, só orçamento) e dois rótulos de `business_journeys.jsonl` (`PRICE-INSUFFICIENT` EN/PT). Conferência offline da regra da T76 (`router-rule-impact.json`): dos 44 casos e dos 10 turnos de conversa, só `V030-CONTRACT-TERMINATION` casa a regex, e ele foi reexecutado. A re-pontuação das respostas da r3 e da r4 pelo runner novo não muda nenhuma checagem (revisão independente, rodadas 2 e 3: 195 respostas, 1.755 checagens).
- **r3 (`f8daab0`), 22 IDs nunca retestados:** `EX01`–`EX03`, `EX05`–`EX07`, `EX09`, `EX10`, `PT01`–`PT10`, `UC12`, `UC16`–`UC18`. Continuam como base, identificados pelo SHA (`v080-all-r3.json`, `40b4e63e…1833`). Não entram no CA-51 nem no CA-49; entrariam na fase B.

## Juiz (fase A)

`judge_failed = 0` em 39 julgamentos (36 `healthy` + 3 `tool-down`). `unsupported_claim` = 0/39. Nota web: 0 respostas com web. Médias no `healthy`: groundedness 4,97, factual_correctness 4,97, relevance 4,97, usefulness 4,89; `tool-down` 5/5/5/5. As respostas com protocolo de escalada (`CONTRACT-TERMINATION`, `PRICE-DIVERGENCE` EN/PT, `TOOL-DOWN`) não foram marcadas. O juiz independente concorda que as 10 respostas recusadas pela régua literal estão corretas.

## Fases B e C

Não executadas. O despacho condiciona B ao portão de A e C a A e B. Os blocos de B estão prontos no seletor (dry-run `dryrun-judge-r3.json`). A composição dos 44 IDs (r5 13, r4 9, r3 22) está fixada no código, para quando o portão de A for atingido.

## Custo e ledgers (somente leitura, antes e depois de cada bloco)

| Ponto | Primário `data/runtime/budget.sqlite3` (entradas/último ID, comprometido) | Campanha `budget-v080-qa.sqlite3` (entradas/último ID, comprometido) | Reservas |
|---|---|---|---|
| Antes (03:48) | 2733/2733, US$1,14385079 | 1117/1117, US$0,58164655 | 0 / 0 |
| Seed e tentativa parada no preflight | sem mudança | sem mudança | 0 / 0 |
| Depois de `healthy` | 2926/2926, US$1,18377144 | 1310/1310, US$0,62156720 | 0 / 0 |
| Depois de `tool-down` (final) | 2944/2944, US$1,18620607 | 1328/1328, US$0,62400183 | 0 / 0 |

| Bloco | Lançamentos | Delta (igual nos dois ledgers) | Por modelo |
|---|---:|---:|---|
| `healthy` | 193 | US$0,03992065 | deepseek-flash US$0,02090998 (36); gpt-6-luna US$0,01900917 (154); embeddings US$0,00000150 (3) |
| `tool-down` | 18 | US$0,00243463 | deepseek-flash US$0,00104112 (3); gpt-6-luna US$0,00139351 (15) |
| **Fase A (total r5)** | 211 | **US$0,04235528** | — |

Todos os lançamentos estão `settled` e sem reserva aberta. Gate da fase A US$0,20: foram usados US$0,04235528. Cap fixo `v080-qa` US$1,40: comprometidos US$0,62400183, **restam US$0,77599817**, acima da reserva de US$0,40 do holdout (estimativa do holdout US$0,36062993). Primário (sidecar 2,00): restam US$0,81379393. Nenhum gasto ficou fora da guarda, a campanha não foi remontada e os sidecars ficaram em 2,0 e 1,4.

## Artefatos (SHA-256)

| Arquivo | SHA-256 |
|---|---|
| [v080-healthy-r5.json](v080-healthy-r5.json) | `b50923c29d5d609d183a23b1c3de821cb56f3a049d00cdeb21888cf490ae9dec` |
| [v080-healthy-r5.md](v080-healthy-r5.md) | `9ef04c55ecb28ccf60e7ee8248473169fabbc6864bf9d2ff041a68c56c7d63f6` |
| [v080-tool-down-r5.json](v080-tool-down-r5.json) | `979c9fc68f5f8feb0eb7b887e6dd65516792a3ace8bc7052dd8c8062aa41a430` |
| [v080-tool-down-r5.md](v080-tool-down-r5.md) | `67dcf13d9343857c14f16c96d522ff88237ff9bd188f105424c679bab0597b88` |
| [v080-healthy-traces-r5.json](v080-healthy-traces-r5.json) | `099e51b73cdd3854c22d167048de2a34808e1b99923f6d9c07fe49fea4be15bb` |
| [v080-tool-down-traces-r5.json](v080-tool-down-traces-r5.json) | `a6063d27c8afece58587f6892cec87b49cdf878977a678330759effc2eda3546` |
| `qa-r5-results/healthy.stdout.log` / `tool-down.stdout.log` | `7e6b811f…091b` / `1e4009b0…06db` (stderr vazios) |
| `qa-r5-results/suite-strict.log` | `288c7ac5bad6cfbbab950f5a5454a5d93283f943291780ff601261761232b325` |
| `qa-r5-results/phase-a-analysis.json` | `d559c12a859b586084f8b1fa8dd6f5dd202259166c7ce5bfdfe6f7640cecc02a` |
| `qa-r5-results/seed-dates-after.json` / `bootstrap.log` | `34bf0bca…e42a` / `776f8f1c…7947` |
| `qa-r5-selector.py` | `b1d6ef4b…f073` |
| `qa-r5-results/healthy-attempt1-preflight-error.stderr.log` | `9058dab87ee24390e38e1800a34c7f42c1fd0eaa8a9df3c59f535351b6dfa98a` |

Na pasta de evidência e nos logs, a varredura por `eyJ` e `sk-` deu zero ocorrências.

## Observações

- **O-1:** em `TOOL-DOWN`, a conexão recusada aparece como `TIMEOUT` na ferramenta: no Windows a recusa leva cerca de 2 s e o cliente desiste antes. A escalada sai pela regra `support_asked_for_human` e não por uma regra própria de falha de ferramenta. O resultado para o lojista é o esperado (D4).
- **O-2:** em `REPLAN-PROCEDURE`, o Router já planeja `knowledge_and_support`, e o `replan` só segue o plano pendente, com `plan_hops = 0`. O momento 2 da história descreve "Support → replan → Knowledge", mas aqui o salto não acontece porque o plano inicial já cobre as duas partes. O cenário passa nos rótulos.
- **O-3:** `CONTRACT-TERMINATION` foi encaminhado pelo próprio modelo nas três repetições, então a regra da T76 não foi exercida ao vivo nesta rodada.
- **O-4:** `PRICE-DIVERGENCE` EN e PT terminam em `handoff` com protocolo nas três repetições, o que o rótulo aceita.

## Limitações

- A rubrica do CA-51 é a checagem determinística, como na r3 e na r4; a leitura pelo juiz aparece só como referência. A pergunta sobre qual rubrica mede o CA-51 está na tarefa 78.
- As fases B (variação do juiz) e C (smoke Docker, momento 9) não rodaram. CA-50 segue sem prova real nesta rodada.
- Os 22 IDs da r3 e as 4 conversas da r4 não foram reexecutados com o candidato r7 (reaproveitados pela análise de impacto acima).
- O seletor é um harness fora do repositório, com os ajustes registrados acima.
- O runtime de QA foi ressemeado em 05/11. Qualquer fase paga em outro dia precisa de nova seed (regra do manifesto).

## Pergunta ao Supervisor

Qual rubrica mede o CA-51: a checagem determinística `passed`, usada até aqui, a rubrica `judge.v3`, ou a combinação das duas (por exemplo, todas as checagens determinísticas sem `content_ok` mais o juiz)? Na r5 as três leituras dão, por repetição, 11/8/10, 13/13/13 e 13/13/13. A decisão é de critério, não do QA. Se ficar a determinística, a correção é de rótulo ou de cotejo (D15), com reteste só das seis jornadas da tarefa 78.

## O que a história ensinou sobre o próprio roteiro

- A regra nova de ambiente funcionou: com a seed do dia, as jornadas datadas passaram a medir o que deviam (valores, ferramentas e status 100%). Vale fixar no roteiro de QA a prova "ontem = dia anterior ao dia local" antes e depois de cada bloco pago, e não só antes.
- "Ressemear" no roteiro de QA significa `bootstrap` com a coleção existente: sem custo e sem reindexar. Vale manter um backup do runtime antes de ressemear como ponto de retorno.
- O momento 8 ("≥ 12/13 pela rubrica") é ambíguo desde a spec: "a rubrica" da v0.8.0 é a de quatro critérios do juiz, mas as rodadas mediram pela checagem literal. Com respostas reais, a lista literal sempre fica um passo atrás das redações novas.
- O momento 2 supõe que o Router manda só para o Support. Com `router.v6`, a pergunta mista já nasce `knowledge_and_support`, e o replanejamento não salta (O-2).

## Como terminou

O lojista que perguntou pelas vendas de "ontem" recebeu os valores certos de 04/11: o débito de R$ 148,06 cai hoje, o crédito de R$ 1.162,20 cai amanhã e ainda não está confirmado, e a antecipação se faz pelo app. Quem perguntou pela taxa do Pix ouviu que foram cobrados R$ 0,75 onde a regra previa zero e foi encaminhado a um atendente com protocolo. Quem pediu para encerrar o contrato foi direto para um atendente, nas três vezes. Com o serviço de preços fora do ar, o lojista ouviu que a consulta não respondeu, sem taxa inventada, e recebeu um protocolo de atendimento. O avaliador viu cada decisão do replanejamento com motivo e origem, nunca acima de dois saltos. As respostas estavam certas, e o juiz independente concordou, mas a régua literal recusou dez delas por usarem palavras diferentes das listadas. A rodada termina reprovada no portão do CA-51, com o juiz repetido e o Docker por fazer, o mock desligado, os ledgers conferidos e o holdout intacto.
