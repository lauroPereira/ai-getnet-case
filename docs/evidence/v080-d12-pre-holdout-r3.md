# QA D12 pré-holdout — v0.8.0 r3

Data: 2026-11-04  
Candidato: `f8daab03c9c33a204edd7d38a009dd6345a93723`  
Relatório completo: [v080-all-r3.json](/C:/workspace/ai-getnet-case/docs/evidence/v080-all-r3.json)  
Relatório legível: [v080-all-r3.md](/C:/workspace/ai-getnet-case/docs/evidence/v080-all-r3.md)

## Resultado e portões

A primeira fase D12 executou 44 casos três vezes (132 respostas julgadas) e quatro conversas com dez turnos. Terminou com exit code 0. **CA-51 não atingiu o mínimo de 12/13 em nenhuma repetição; por isso, a fase `judge-repeat` não foi iniciada.** O holdout `holdout_v080` não foi lido nem executado. O mock, Docker e smoke foram encerrados ou não iniciados conforme a autorização desta passagem.

| Repetição do agente | Casos aprovados | Conteúdo | Status | Demais checks determinísticos |
|---|---:|---:|---:|---:|
| 1 | 36/44 | 36/44 | 43/44 | 44/44 cada |
| 2 | 39/44 | 39/44 | 43/44 | 44/44 cada |
| 3 | 38/44 | 39/44 | 42/44 | 44/44 cada |

Os demais checks são rota, idioma, ferramentas, valores, assertivas proibidas, fontes e grounding. Os IDs que reprovaram ao menos um check por repetição foram:

| Repetição | IDs e checks reprovados |
|---|---|
| 1 | `REPLAN-PROCEDURE` (conteúdo), `REPLAN-TOOL-DOWN` (status e conteúdo), `EX08` (conteúdo), `NOEV` (conteúdo), `V030-PRICE-CONDITIONS` (conteúdo), `V030-PRICE-DIVERGENCE` (conteúdo), `V030-PT-PRICE-INSUFFICIENT` (conteúdo), `V030-PT-SALE-CANCELLATION` (conteúdo) |
| 2 | `REPLAN-WEB` (conteúdo), `REPLAN-TOOL-DOWN` (status e conteúdo), `NOEV` (conteúdo), `V030-PRICE-DIVERGENCE` (conteúdo), `V030-PT-PRICE-INSUFFICIENT` (conteúdo) |
| 3 | `REPLAN-TOOL-DOWN` (status e conteúdo), `UC13` (status), `NOEV` (conteúdo), `V030-PRICE-CONDITIONS` (conteúdo), `V030-PRICE-INSUFFICIENT` (conteúdo), `V030-PT-PRICE-CONSISTENT` (conteúdo) |

## CA-49 — replanejamento

| ID | Repetição 1 | Repetição 2 | Repetição 3 | Leitura |
|---|---|---|---|---|
| `REPLAN-ACCOUNT` | passa | passa | passa | Caso válido nesta rodada |
| `REPLAN-PROCEDURE` | falha `content_ok` | passa | passa | Falha isolada na repetição 1 |
| `REPLAN-WEB` | passa | falha `content_ok` | passa | Falha isolada na repetição 2 |
| `REPLAN-TOOL-DOWN` | falha status/conteúdo | falha status/conteúdo | falha status/conteúdo | **Inválido para CA-49:** o mock de preços estava saudável; a tarefa 69 exige indisponibilidade para este cenário. As três respostas foram `answered` sem erro de ferramenta. |

Os três casos com ambiente válido passaram 2/3, 2/3 e 3/3 por repetição. CA-49 também exige trace de cada decisão e limite de três saltos. O relatório do runner não preserva `trace.detail.plan_hops` ou `origin`; não há `run_snapshots` para esses request IDs e `messages.meta` está vazio. Assim, os saltos e as origens não puderam ser certificados nesta execução. Não atribuo as falhas de `REPLAN-TOOL-DOWN` a defeito de produto; a condição prevista para esse caso não foi montada.

## CA-51 — jornadas de negócio

| Repetição | Aprovadas | Mínimo | IDs que falharam `content_ok` |
|---|---:|---:|---|
| 1 | 9/13 | 12/13 | `V030-PRICE-CONDITIONS`, `V030-PRICE-DIVERGENCE`, `V030-PT-PRICE-INSUFFICIENT`, `V030-PT-SALE-CANCELLATION` |
| 2 | 11/13 | 12/13 | `V030-PRICE-DIVERGENCE`, `V030-PT-PRICE-INSUFFICIENT` |
| 3 | 10/13 | 12/13 | `V030-PRICE-CONDITIONS`, `V030-PRICE-INSUFFICIENT`, `V030-PT-PRICE-CONSISTENT` |

As simulações de preço usadas nessas jornadas concluíram sem `UNAVAILABLE` nem erro de ferramenta. `V030-PRICE-DIVERGENCE` falhou conteúdo nas repetições 1 e 2 e passou na 3; seu retry válido anterior também falhou `content_ok`. `V030-PT-PRICE-INSUFFICIENT` falhou nas repetições 1 e 2 e passou na 3. O sinal anterior de rota/status de `V030-CONTRACT-TERMINATION` não se repetiu: os três D12 passaram rota e status; o juiz marcou `unsupported_claim` nas repetições 1 e 3.

As conversas passaram 3/4. `FU01` falhou `route_ok` em um turno; `FU02`–`FU04` passaram.

## Juiz

Os 132 julgamentos da variação do agente foram concluídos; `judge_failed=0`. O campo global `unsupported_claim_rate` é **19/132 = 14,4%** (8/44, 5/44 e 6/44 nas repetições 1, 2 e 3). O campo distinto `judge_web_note` cobre 24 respostas com nota web, das quais 9 foram marcadas: **9/24 = 37,5%**. Os escores médios foram groundedness 4,56, factual correctness 4,62, relevance 4,77 e usefulness 4,53.

## Custo e ambiente

O cap único `v080-qa` foi montado às 22:47:32 UTC com limite de US$1,10. A execução terminou por volta de 23:11:57 UTC, aproximadamente 24m25s depois. O cap permanece montado e não foi resetado.

| Ledger / fase | Antes | Depois | Delta |
|---|---:|---:|---:|
| Ledger primário `data/runtime/budget.sqlite3` | ID 1616, US$0,56220424 | ID 2346, US$0,94504185 | US$0,38283761 |
| Ledger da campanha `budget-v080-qa.sqlite3` | cap US$1,10 | US$0,38283761 gasto | US$0,71716239 restantes |

Reservas abertas: zero nos dois ledgers. Restam US$0,75495815 no limite primário de US$1,70. Por modelo, o delta foi OpenAI gpt-6-luna US$0,31737488, embeddings OpenAI US$0,00001834 e juiz DeepSeek US$0,06544439. O relatório arredonda o custo dos casos para US$0,31213, juiz para US$0,06544 e conversas para US$0,005244; o ledger é a fonte do total liquidado.

Sessão da avaliação: exec `99353`, exit code 0; stdout capturado em `.pytest_cache/qa-v080-r1/v080-all-r3.stdout.log` e stderr vazio em `.pytest_cache/qa-v080-r1/v080-all-r3.stderr.log`. O mock oficial foi executado pela venv na sessão `8116`, PID `19664`; checks locais de OpenAPI e fixtures retornaram HTTP 200. O processo recebeu Ctrl+C após a fase e encerrou com shutdown completo. Nenhum gasto ficou fora da guarda.

SHA-256 do JSON de resultados: `40b4e63e21ea967e0ae60a8cc319b0aa90edead329da971930d4ac66306f1833`. SHA-256 do Markdown de resultados: `299288dd4fed7cb653d7fac84f5dee504db081604bf53eae092df73b64562c60`. SHA-256 do stdout: `5110a269a673909ca0d2b168d57ad2e8af9a63b190f99c8de715c0dcff779582`; stderr vazio.

## Próximo reteste dirigido

Corrigir e repetir primeiro as jornadas CA-51 abaixo de 12/13. Para CA-49, executar `REPLAN-TOOL-DOWN` somente com o mock de preços indisponível, como pede a tarefa 69, e capturar `hops`/`origin` no mesmo momento em que a trace existe. Depois, repetir a regressão de desenvolvimento antes de avaliar a fase de variação do juiz. Este parecer não autoriza uma nova rodada paga, uma nova montagem de cap ou o holdout.
