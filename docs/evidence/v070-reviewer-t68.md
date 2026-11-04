# Revisão independente da T68 — rodada 1

- **Candidato:** `861a80ff4cfef80c20b2cc3a97d9666583608f48` (código igual a `f536d9d`), branch `codex/v0.7.0-identidade-hitl`, worktree destacado `C:\workspace\ai-getnet-case-wt\review-a2`; HEAD e `git status` iguais antes e depois. Diff `6876adc..f536d9d`, 13 arquivos.
- **Independência:** subagente `reviewer` (sonnet/xhigh) em contexto frio; leu a tarefa até "Validação" e não leu as passagens do Developer. Um `grep` devolveu incidentalmente a linha da tabela de Validação com o nome de dois testes; o Reviewer declara não ter usado a linha, porque já tinha lido e mutado esses testes. Gravado pelo Supervisor a partir do relatório do Reviewer.
- **Parecer:** **correções necessárias** — 1 P2, nenhum P1; fora ele, apta para QA.

## Achado

**P2-1 — `SC-HANDOFF` do catálogo de cenários ainda exige `SIM-`.** `data/scenarios/catalog.json:208-212` (`source_case: "UC14"`, `must_include_any: [["SIM-"]]`), intocado desde a v0.6.0. A tarefa trocou o rótulo de UC14 em `tests/scenarios/core_cases.jsonl` para `HO-` (D7), mas não o cenário irmão, que alimenta os checks da bancada (`scenarios.as_case` → `evaluation.runner`). Toda execução com `scenario_id=SC-HANDOFF` (`/v1/messages`, `/v1/runs/{id}`, comparações) reporta `content_ok=false` e `passed 10/11` para um handoff correto; na v0.6.0 era 11/11. Reproduzido pela API com modelo programado e pelo runner sobre o catálogo inteiro (v0.6.0 × candidato: só `SC-HANDOFF` muda). Nenhum teste afirma os checks de `SC-HANDOFF`.

## P3

1. O rótulo de UC14 (`HO-`, sem distinção de maiúsculas) poderia acrescentar `must_not_include` para `SIM-` e "simul"; a ausência de texto de simulação já é coberta por outros testes.
2. Destino com URL e sem segredo agora não gera intenção, sem aviso de configuração (`data/webhook_outbox.py:28-31`); sugestão: aviso na subida. O compose traz os segredos padrão.
3. `README.md:214` ainda mostra `{"protocol": "SIM-…", "simulated": true}` (fechamento do Supervisor).
4. `strip` do segredo repetido em três lugares (`api/identity.py:180`, `api/integrations.py:42`, `data/webhook_outbox.py:25`).

## Comprovado por execução

- **Eval programado × v0.6.0:** `eval --scripted` (40 casos e followup) em cópias da tag `v0.6.0` e do candidato: `passed 0,625`, `content_ok 0,625`, os demais checks 1,0, custo 0, conversas 4/4 nos dois. Os mesmos 15 casos falham `content_ok` nos dois (limite da política programada). Caso a caso, só a resposta difere em 4 casos e 2 turnos, e só na linha de encaminhamento (D7: sem "simulated", `SIM-` → `HO-`). O novo rótulo de UC14 e a linha em inglês com "human" são justificados pela D7 e mantêm o rigor: mutantes com o rótulo antigo, com o prefixo `SIM-` de volta ou com a linha da T66 sem "human" falham.
- **História:** ticketing real e `mocks` em processo; momentos 1 a 15 e 17 num teste, o 16 com subprocesso real e uma API nova sobre o mesmo runtime e checkpoint; CA-46/47/48 nas asserções. Três execuções estáveis. Mutação: 20 mutantes no produto, 18 pegos pela história; S05 e S18 pegos pelos testes das tarefas; reinício isolado pega checkpoint em memória e caminho diferente por processo.
- **Fechamento:** `cmd_eval` em processo com os 40 casos e as 4 conversas; campanha `v070-qa` com US$0,20 montada uma vez e combinada com o ledger primário (US$0,69 de US$5,00), recusa acima do teto sem tocar o primário, remontagem mantém o gasto, uma requisição real passa pelo guard combinado; versão 0.7.0. Mutantes E1, E2, K1–K6 mortos. `docker compose config --quiet` numa cópia sem `.env`: código 0 com `api`, `mocks`, `qdrant` e `ticketing`; `webhook_targets` reais dão os dois destinos.
- **Lacunas da T66 r5:** os testes novos matam G0–G6, N09 e os mutantes de `webhook_targets`; `target_config` é o mesmo do despachante (24 combinações testadas).
- **P3-A/B/C das T63/T64:** `authorize` por chamada no MCP, auditoria de `LIMIT_REACHED` e `operator_forbidden` mantido e coberto; mutantes A1, B1 e C1 mortos.
- **Contrato:** OpenAPI do assistente, do ticketing e do `mocks` iguais aos de `6876adc`, exceto `info.version` (0.6.0 → 0.7.0).
- **Testes:** 156 passed nos arquivos pertinentes; Ruff limpo. Suíte estrita (Supervisor, neste candidato): **632 passed**, código 0.

## Não comprovado

Docker em execução e o momento 18 (QA); modelo real; `ask` por execução; MCP por stdio real; migrações (não tocadas pela tarefa).
