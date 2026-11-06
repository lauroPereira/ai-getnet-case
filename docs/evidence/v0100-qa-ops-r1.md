# Passagem de papel: QA da v0.10.0, momentos 4 a 8 (comparação interrompida e retomada, `/metrics`, regras de alerta), rodada 1

- Papel e responsável: QA (subagente), despachado pelo Supervisor.
- Objetivo e critérios: viver os momentos 4 a 8 da [história](../historias/rubrica-operacao-v0100.md) (versão 1, 2026-11-05) e comprovar CA-58 e CA-59 da [spec](../specs/rubrica-operacao-v0100.md) (D3 a D6).
- Escopo: API local (uvicorn, Qdrant embutido) em runtime isolado novo; `POST /v1/comparisons/estimate`, `POST /v1/comparisons`, `GET /v1/comparisons/{id}`, `POST /v1/comparisons/{id}/resume`, `GET /metrics`, `GET /ready`; `alerts/rules.yml`; fumaça offline. Fora: Docker, navegador, chamadas Anthropic, `eval --judge`.
- Estado: **apto**, com os desvios e as observações abaixo.
- Branch e PR: `codex/v0.10.0-rubrica-operacao`, sem PR. Nada commitado.
- Base e versão final: HEAD `92230de` ("docs: pin the v0.10.0 candidate (r1)"); manifesto [v0100-candidato-r1.json](v0100-candidato-r1.json) (head `c1042a5`, tree `b92dbbc2`). `git diff c1042a5 HEAD` muda só o próprio manifesto. Alterações locais: nenhuma em `src/`, `tests/`, `alerts/` ou `prompts/` (`git status` limpo nesses caminhos).
- Independência: independente quanto ao Developer e aos Reviewers. Li as passagens dos Reviewers das tarefas 84 (rodada 2) e 85 (rodada 1) só para conhecer os limites declarados (P3-4, P3-5). Não li código para julgar, só para achar a regra de orçamento do `start` e o papel exigido pela rota.
- Próxima ação e responsável: Supervisor (resolver as duas perguntas de premissa; tarefa 86 já cobre P3-5 e o README).
- Decisão humana pendente: nenhuma.

## Pré-checagens (sem custo), 00:48 a 00:50 (-03:00)

| Item | Resultado |
| --- | --- |
| HEAD | `92230def992131cdca6bd28bea569c4452f1b647`; `c1042a5^{tree}` = `b92dbbc2b6108ec6790e8064dac4d79da2d15db2`, igual ao manifesto |
| Hashes | **202/202** conferem contra os blobs de `HEAD` (`git show HEAD:<arquivo>`), incluindo `comparisons.py` `7ebaaadb…`, `observability/metrics.py` `0bb721ec…`, `data/migrations.py` `ecb3bc9b…` e `alerts/rules.yml` `f91f6257…`. No worktree a diferença é só fim de linha (CRLF); `git status` limpo |
| Fingerprint | recalculado como sha256 de `"<arquivo>:<sha256>\n"` em ordem: `3094374c516a297e0be96b0585c8cec9e97e8fdab82e1bbbef18491dfa89dff9`, igual ao manifesto |
| `/ready` | `ready: true`, `versions.schema` **12**, `versions.app` **0.9.0**, 145 chunks, `budget_remaining_usd` 0,1993 |
| `GET /metrics` antes de tráfego | `200`, `content-type: text/plain; version=0.0.4; charset=utf-8`; 10 famílias com `# HELP` e `# TYPE`; famílias com rótulo sem amostras; `handoffs_total 0`; histograma todo em 0 (`+Inf` 0, `_sum` 0, `_count` 0); `cost_usd_total{provider="openai"} 0.00074292` (o bootstrap, pago no mesmo ledger); `budget_remaining_usd 0.19925708`; `budget_limit_usd 0.2`. Toda linha passa por uma regex de amostra da exposição 0.0.4 |
| `alerts/rules.yml` | 4 regras (ver momento 7), todas as métricas citadas presentes na saída |

## Ambiente

| Item | Valor |
| --- | --- |
| Runtime | `RUNTIME_DIR=.pytest_cache/qa-v0100-ops/runtime`, novo (não existia) |
| Bootstrap | `.venv/Scripts/merchant-assistant.exe bootstrap` às 00:49:18 (-03:00), `RUNTIME_DIR` acima e `BUDGET_LIMIT_USD=0.20`: dados sintéticos de 06/11 semeados; 145 chunks de 40 documentos; sidecar do ledger isolado com 0,2 |
| API | `.venv/Scripts/python.exe -m uvicorn --factory merchant_assistant.main:create_application --host 127.0.0.1 --port 8765`, com `RUNTIME_DIR`, `BUDGET_LIMIT_USD=0.20` e, a partir da instância A, `MAX_REQUEST_COST_USD=0.03` (ver "Desvios"). `.env` atual para as chaves; `DEMO_MODE` padrão (`false`). Logs em `.pytest_cache/qa-v0100-ops/api-*.log` |
| Token | `merchant-assistant auth token --username cliente1988 --url http://127.0.0.1:8765` (lojista sintético, papel `merchant`, senha fictícia de `DEMO_USER_PASSWORDS`), guardado num arquivo temporário do scratchpad e apagado no fim. Nenhum valor copiado |
| Modelos | `gpt-6-luna` (OpenAI) nos agentes; o perfil `hybrid` usa `deepseek-flash` no Router. Nenhuma chamada Anthropic |

Instâncias da API (o lançador do venv cria um processo filho; o `taskkill` foi sempre no filho, que é o servidor):

| Instância | Lançador | Servidor | Início | Fim |
| --- | --- | --- | --- | --- |
| Pré-checagem | 1164 | 17344 | ≈00:50 | `taskkill /F /PID 17344` antes do momento 4 (sem tráfego pago) |
| A | 8020 | 14872 | 00:52 | **`taskkill /F /PID 14872` às 00:53:50.916**, no meio da comparação |
| B | 15044 | 10448 | 00:54:09 (startup completo 00:54:16) | `taskkill /F /PID 10448` às 00:57:00, depois do momento 6 |

## Momento 4: comparação interrompida

Seleção: perfis `reference` v1 (todos os agentes OpenAI) e `hybrid` v1 (Router DeepSeek) × `SC-RECEIVABLES`, `SC-ENABLEMENT`, `SC-KNOWLEDGE-PRODUCTS`, 1 repetição, `router_mechanism: llm`, `reuse_recorded: true`.

1. `POST /v1/comparisons/estimate` (`req_c45dba222af14ac8aa73`): `200`, 6 células novas, 0 reaproveitadas, `estimated_cost_usd` 0,18 (0,03 por célula), `changes_between_profiles: router`, `execution_mode: real`.
2. `POST /v1/comparisons` com `confirmed: true`, `max_cost_usd: 0.18` e o `estimate_digest` lido (`req_cf5db718fa7d45aa8dbd`, 00:53:39.856): **`202 {comparison_id: pcmp_1e15a4bf5a1d4b219e5b, state: running}`**.
3. `GET` a cada 0,25 s. No primeiro `GET` com `request_id` numa célula, `taskkill /F /PID 14872` (00:53:50.916, código 0).

**Estado lido imediatamente antes do kill:** `running`; 1 de 6 células `completed` (`SC-RECEIVABLES`/`reference`, `req_31a44a546dd14e45b9a1`, US$0,00085582, rota `support`, `answered`); 5 `pending`; `cost_usd` 0,00085582. A segunda célula (`SC-RECEIVABLES`/`hybrid`, `req_9af4a694ec7c4708ac39`) já tinha começado: o ledger ficou com uma linha `reserved` do Router DeepSeek (id 9, US$0,0011067, sem `actual_usd`).

**Depois do reinício (instância B):**

- Log estruturado do startup, antes de "Application startup complete": `{"logger": "merchant_assistant.comparisons", "msg": "comparison interrupted", "comparison_id": "pcmp_1e15a4bf5a1d4b219e5b"}` (03:54:16.423Z).
- `/ready`: `ready: true`, esquema 12, `budget_remaining_usd` 0,1973.
- `GET /v1/comparisons/pcmp_1e15a4bf5a1d4b219e5b` (`req_49e8220b72cb4c17b3e0`): **`state: interrupted`**; `failures: [{code: interrupted, message: "The API process stopped before the comparison ended."}]`; célula 1 preservada com o mesmo `request_id`, custo, duração e rota; célula 2 `pending` com **`interrupted_attempts: [{request_id: req_9af4a694ec7c4708ac39, cost_usd: 0.0011067}]`**; células 3 a 6 `pending`; `cost_usd` **0,00196252** (= 0,00085582 + 0,0011067); `cost_is_estimate: true`.

## Momento 5: retomada

- `POST /v1/comparisons/pcmp_1e15a4bf5a1d4b219e5b/resume` às 00:54:38.779 (`req_10b56f969e384b13b3f9`): **`202 {comparison_id, state: running, resumed_cells: 5}`**.
- Acompanhamento (`GET` a cada 1 s), células com `request_id`: 1 (00:54:38) → 2 (00:54:52) → 3 (00:55:00) → 4 (00:55:06) → 5 (00:55:16) → **6, `completed`** (00:55:24.159).
- Segundo `resume` às 00:55:24.176 (`req_0a4d05aa6cfd4b80ad28`): **`409 comparison_completed`**, "The comparison already completed; nothing to resume.".

Estado final: `completed`, 6 células (o mesmo número da estimativa), todas `completed` e `answered`; `cost_usd` 0,00492469; `cost_is_estimate: true`; `failures` mantém o registro `interrupted`; agregados presentes (`profiles`, `cost_by_agent_model`, `quality_basis`).

Conciliação com `runtime/budget.sqlite3` (somente leitura):

| Célula | `request_id` | Custo da célula | Linhas do ledger (ids) | Soma no ledger |
| --- | --- | ---: | --- | ---: |
| SC-RECEIVABLES / reference | `req_31a44a546dd14e45b9a1` | 0,00085582 | 5 (4 a 8, as mesmas de antes do kill) | 0,00085582 |
| SC-RECEIVABLES / hybrid | `req_6271d5bda0224fbb9a64` | 0,00079317 | 5 (10 a 14) | 0,00079317 |
| SC-ENABLEMENT / reference | `req_8684e7e061a4428dbb47` | 0,00045586 | 4 (15 a 18) | 0,00045586 |
| SC-ENABLEMENT / hybrid | `req_d78b0e6cfc284a0682ec` | 0,00057084 | 4 (19 a 22) | 0,00057084 |
| SC-KNOWLEDGE-PRODUCTS / reference | `req_86714d1d158f42f0a850` | 0,00065217 | 3 (23, 25, 26) | 0,00065217 |
| SC-KNOWLEDGE-PRODUCTS / hybrid | `req_b3702f352b714864a757` | 0,00049013 | 3 (27, 29, 30) | 0,00049013 |
| Tentativa interrompida (célula 2) | `req_9af4a694ec7c4708ac39` | 0,0011067 em `interrupted_attempts` | 1 (9, `reserved`) | 0,0011067 (reserva) |

- Nenhuma célula paga duas vezes: 6 `request_id` distintos, um por célula; a célula concluída antes do kill não ganhou linha nova; a tentativa interrompida continua com uma única linha, e o `resume` rodou a célula 2 com um `request_id` novo.
- Soma das células 0,00381799 + tentativa interrompida 0,0011067 = **0,00492469 = `cost_usd`** (contada uma vez).
- As linhas 24 e 28 são os embeddings das duas perguntas de Knowledge, gravados sem `request_id` (US$0,00000034 cada) e por isso fora do custo das células (ver observação O4).

## Momento 6: `/metrics` depois dos momentos 4 e 5

`GET /metrics` às 00:55:3x (cache de 5 s já vencido): `200`, `text/plain; version=0.0.4`. Trecho (sem `# HELP`):

```text
requests_total{route="knowledge",status="answered"} 2
requests_total{route="support",status="answered"} 4
model_calls_total{agent="customer_support"} 10
model_calls_total{agent="knowledge"} 2
model_calls_total{agent="personality"} 6
model_calls_total{agent="router"} 6
tool_calls_total{tool="get_complaint_history",outcome="ok"} 4
tool_calls_total{tool="get_enablement_requests",outcome="ok"} 2
tool_calls_total{tool="get_payout_status",outcome="ok"} 2
tool_calls_total{tool="get_receivables_schedule",outcome="ok"} 2
tool_calls_total{tool="run_customer_healthcheck",outcome="ok"} 4
# TYPE tool_failures_total counter
handoffs_total 0
replan_total{origin="rule:complete"} 6
request_duration_seconds_bucket{le="5"} 0
request_duration_seconds_bucket{le="10"} 4
request_duration_seconds_bucket{le="20"} 6
request_duration_seconds_bucket{le="+Inf"} 6
request_duration_seconds_sum 53.534
request_duration_seconds_count 6
cost_usd_total{provider="deepseek"} 0.00044595
cost_usd_total{provider="openai"} 0.00411564
budget_remaining_usd 0.19433171
budget_limit_usd 0.2
```

| Verificação | Fonte | Resultado |
| --- | --- | --- |
| `requests_total` por rota e status | `traces.sqlite3`, tabela `requests`: 4 `support/answered`, 2 `knowledge/answered`, os 6 `request_id` das células | igual. A tentativa interrompida não tem linha em `requests` nem em `steps`, e não aparece (O5) |
| `model_calls_total` | linhas `settled` com `request_id` no ledger, por agente: support 10, knowledge 2, personality 6, router 6 (24) | igual |
| `tool_calls_total` | passos `tool:*` em `steps` | igual; nenhuma falha, `tool_failures_total` sem amostras |
| Histograma | durações 10,203; 12,442; 7,816; 6,116; 8,435; 8,522 s | `le="10"` 4, `le="20"` 6, `+Inf` 6 = `_count` 6, `_sum` 53,534 = soma das durações |
| `cost_usd_total` | ledger liquidado: `gpt-6-luna` 0,00337204 + `text-embedding-3-small` 0,0007436 = 0,00411564 (openai); `deepseek-flash` 0,00044595 | igual (inclui o bootstrap; a reserva aberta não entra, porque a métrica é só gasto liquidado) |
| `budget_remaining_usd` | 0,2 − 0,00456159 liquidado − 0,0011067 reservado = 0,19433171; `/ready` 0,1943 | igual (`/ready` arredonda em 4 casas) |
| Formato | regex de linha de amostra 0.0.4 nas duas capturas; cada família com `HELP` e `TYPE`; texto termina em `\n` | sem linha inválida |
| Rótulos | chaves: `route`, `status`, `agent`, `tool`, `outcome`, `origin`, `provider`, `le` | nenhum valor com `req_`, `pcmp_`, lojista, operador, espaço ou texto de mensagem |

Capturas completas (não versionadas): `.pytest_cache/qa-v0100-ops/metrics-0-before.txt` e `metrics-1-after.txt`.

## Momento 7: regras de alerta

`alerts/rules.yml` (sha256 `f91f6257…`, igual ao manifesto): grupo `merchant-assistant`, **4 regras**, todas com `runbook_url` absoluto para a seção `#observability` do README no GitHub.

| Regra | Expressão (métricas) | Métricas existem em `/metrics` |
| --- | --- | --- |
| `BudgetNearLimit` | `budget_remaining_usd < 0.10 * budget_limit_usd` | sim |
| `ToolFailureRateHigh` | `tool_failures_total` / `tool_calls_total`, 15 min, > 0,05 | sim |
| `HandoffRateHigh` | `handoffs_total` / `requests_total`, 1 h, > 0,30 | sim |
| `RequestLatencyP95High` | `histogram_quantile(0.95, … request_duration_seconds_bucket …)` > 20 | sim |

## Momento 8: fumaça offline

`python -m pytest tests/integration/test_v0100_comparison_resume.py tests/integration/test_v0100_metrics.py -q -o addopts="" -p no:cacheprovider` (00:58): **26 passed** em 45 s, exit 0. A suíte estrita não foi rodada por este QA (ver "Desvios").

## Custos

| Ledger (somente leitura) | Antes (00:48) | Depois (00:58) | Delta |
| --- | --- | --- | ---: |
| Projeto `data/runtime/budget.sqlite3` | 3898 linhas, `max(id)` 3898, US$1,44385467 liquidado | idêntico | **US$0** |
| Anthropic `data/runtime/anthropic/budget.sqlite3` | 153 linhas, US$2,858792 | idêntico | **US$0** |
| Isolado `.pytest_cache/qa-v0100-ops/runtime/budget.sqlite3` (sidecar 0,2) | não existia | 30 linhas: 29 `settled` US$0,00456159 + 1 `reserved` US$0,0011067; 0 `claude%` | **US$0,00566829** |

Composição do delta: bootstrap US$0,00074292 (3 lotes de embeddings); comparação liquidada US$0,00381867 (células 0,00381799 + embeddings de consulta 0,00000068); tentativa interrompida US$0,0011067 (reserva que nunca liquidou, contada pelo teto; o valor real cobrado pela DeepSeek, se houve, não é visível). Total bem abaixo do esperado de US$0,15 e do teto de US$0,20.

## Desvios e perguntas de premissa (ao Supervisor)

- **D-1. Teto da fase × estimativa.** Com `MAX_REQUEST_COST_USD` padrão (0,05), a estimativa de 2 × 3 é US$0,30 (`req_607923e942cd42f0991e`, na instância de pré-checagem), e o `start` recusa quando a estimativa passa do restante (`429 installation_budget_exceeded`); com `BUDGET_LIMIT_USD=0.20` o restante era 0,1993. Para não elevar o teto, subi as instâncias A e B com `MAX_REQUEST_COST_USD=0.03` (guarda mais estrita; 6 × 0,03 = 0,18). Nenhum atendimento chegou perto do teto (o maior foi US$0,00086). Pergunta: o plano deve registrar essa combinação para a D6, ou prefere outro teto?
- **D-2. Escopo de administração.** O briefing previa token de admin. A rota aceita `merchant`, `demo` e `admin`; `422 admin_scope_required` só vale para o admin sem lojista sintético configurado. Usei o lojista sintético `cliente1988` (papel `merchant`), sem criar senha de `demo`/`admin`. O token conta no limite demo (6 ações de 20).
- **D-3. Provedores.** Só o perfil `reference` é todo OpenAI. A comparação de dois perfis publicados envolve `hybrid` ou `adjusted`, os dois com DeepSeek no Router, então houve 3 chamadas DeepSeek (US$0,00044595) e a reserva interrompida, também DeepSeek. Nenhuma chamada Anthropic.
- **D-4. Pista livre.** A suíte estrita completa não foi rodada aqui (briefing: os Reviewers já a rodaram, 2148; um agente pesado por vez com um Reviewer ainda ativo). A fumaça offline do momento 8 passou.

## Observações (sem tarefa de defeito)

- **O1.** A reserva da tentativa interrompida fica `reserved` para sempre no ledger: o orçamento restante desconta o teto da reserva (US$0,0011067) e o `cost_usd` da comparação usa esse valor com `cost_is_estimate: true`. É conservador e coerente com o contrato ("custo lido do ledger"); o gasto real da chamada em curso não é conhecido.
- **O2.** Depois do `resume`, o estado final é `completed` e `failures` mantém a entrada `interrupted`. Funciona como histórico, mas uma interface que mostre `failures` ao lado de `completed` pode confundir.
- **O3.** P3-5 (Reviewer t84): `README.md` ainda diz que o reinício marca a comparação como `failed`; o comportamento observado é `interrupted`. Já previsto para a tarefa 86.
- **O4.** Os embeddings da pergunta nas células Knowledge vão ao ledger sem `request_id`, então ficam fora do custo da célula e do `cost_usd` da comparação (US$0,00000068 aqui). Diferença desprezível; aparece em `cost_usd_total`.
- **O5.** A tentativa interrompida não deixa linha em `traces.sqlite3` (o trace é gravado ao fim do atendimento; o passo `input_guard` aparece só no log JSON). Por isso ela não conta em `requests_total` nem no histograma, embora tenha consumido orçamento.
- **O6.** Antes de tráfego, as famílias com rótulo não têm amostras e `cost_usd_total{provider="openai"}` já mostra o bootstrap, porque o bootstrap paga no mesmo ledger. É coerente; "zerado" vale para as famílias de requisição.

## Critérios

- **CA-58: comprovado.** Comparação iniciada pela API, API morta com `taskkill /F` depois da primeira célula e reiniciada no mesmo runtime; `interrupted` com a célula concluída preservada e a tentativa em curso registrada com custo; retomada pela API (`resumed_cells: 5`) até `completed` com as mesmas 6 células; nenhuma célula paga duas vezes (ledger por `request_id`); segundo `resume` recusado com `409 comparison_completed`.
- **CA-59: comprovado.** `/metrics` em texto 0.0.4 válido com `requests_total{route,status}`, `model_calls_total`, `cost_usd_total`, `tool_failures_total`, `handoffs_total` e o histograma `request_duration_seconds`, coerentes com traces e ledger e sem rótulo identificador; `alerts/rules.yml` com 4 regras sobre métricas existentes e `runbook_url` absoluto.
- **Não verificado aqui:** o limite P3-4 (ABA entre dois `resume` concorrentes) e P3-5 (mais de um processo da API no mesmo runtime). Os dois estão declarados pelo Reviewer e ficam fora do fluxo sequencial da D6. Também ficou fora o `retry_failed=true`, porque nenhuma célula falhou.

## Limpeza

As três instâncias da API foram encerradas; nenhum `python.exe` com `uvicorn … 8765` ficou de pé. Não houve Docker nem navegador. O runtime `.pytest_cache/qa-v0100-ops/` fica preservado para auditoria (runtime, logs `api-0-precheck.log`, `api-A.log`, `api-B.log`, `m4-log.json`, `m5-log.json`, `estimate.json`, `get-after-restart.json`, capturas de `/metrics` e `/ready`). O arquivo temporário do token foi apagado.

## Como terminou

O operador abriu uma comparação de dois perfis em três cenários e confirmou a estimativa. Quando a primeira resposta ficou pronta, a API caiu. Ao subir de novo, a comparação apareceu como interrompida: a resposta pronta estava lá, e a resposta que estava em curso aparecia como tentativa interrompida, com o custo dela. Ele pediu para continuar: só as cinco células que faltavam rodaram, a comparação terminou completa e um segundo pedido de retomada foi recusado com clareza. No ledger, cada célula foi paga uma única vez. Em `/metrics` ele viu as seis requisições, as chamadas de modelo, o gasto por provedor e o orçamento restante, tudo batendo com o trace, o ledger e `/ready`, e nenhum rótulo identificava lojista ou requisição. As quatro regras de alerta usam só métricas que existem ali. A história também mostrou que o teto da fase só comporta 2 × 3 se o teto por atendimento for reduzido, o que vale registrar no plano.
