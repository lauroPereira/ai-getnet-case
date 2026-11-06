# Passagem de papel: revisão da tarefa 85 (`/metrics` e regras de alerta), rodada 1

- **Papel e responsável:** Reviewer (subagente, contexto frio), 2026-11-05.
- **Objetivo e critérios:** tarefa 85, lida só até "## Validação"; spec `rubrica-operacao-v0100.md` D4, D5 e CA-59; história `rubrica-operacao-v0100.md`, momentos 6 e 7.
- **Escopo:** `29add9c` (`observability/metrics.py` novo, `api/app.py` por acréscimo), `7638f18` (`alerts/rules.yml` novo, `tests/integration/test_v0100_metrics.py` novo) e `2a561db` (README, seção Observability). Base `023dc61`.
- **Estado:** **correções necessárias**. Nenhum P1, 1 P2 (rótulos sem vocabulário fechado na camada de métricas) e 6 P3.
- **Branch e PR:** `codex/v0.10.0-rubrica-operacao`, sem PR.
- **Base e versão final:** revisei o export de `c7b06d5` (`git archive`). Não há manifesto `v0100-candidato-*.json`, então fixei o candidato pelos blobs: `metrics.py c8c81af`, `app.py 978e2c2`, `rules.yml a24fc67`, `test_v0100_metrics.py 6d59e71`, `README.md 705d206`. No fim, os mesmos blobs. O HEAD avançou para `5d1ea89` durante a revisão (`2230603`, `5d1ea89`), mas os dois commits só mexem em `docs/` (`git diff --stat c7b06d5 HEAD -- src alerts tests README.md` sai vazio). O export ficou idêntico a um `git archive c7b06d5` novo (`diff -rq`, desconsiderando só os caches).
- **Independência:** independente. Não implementei nada e não li `v0100-developer.md` nem a Validação ou o Status da tarefa 85.

## Comandos e números

Tudo rodou em cópias de leitura em `<scratchpad da sessão>`, com o Python do `.venv` do projeto e `PYTHONPATH` no `src/` da cópia. Conferi que o módulo carregado era o da cópia, porque o `.venv` tem instalação editável apontando para a árvore de trabalho. Não houve chamada paga, rede, Docker nem Git de escrita. Não toquei em `data/runtime/`, `.pytest_cache/qa-*` nem `.env`.

| Verificação | Resultado |
| --- | --- |
| `pytest` (export de `c7b06d5`) | **2133 passed, 1 skipped, 0 failed**, 1136 s, exit 0. O skip é anterior à tarefa: `test_v070_identity_r2.py:277` só roda com `--basetemp` do projeto |
| `ruff check` (arquivos que `lint_and_tests.py` lista) | All checks passed |
| `validate_structure` e `validate_skills` | válidas |
| `checar-caminhos-pessoais.py` (os 770 arquivos rastreados de `c7b06d5`, passados como argumento) | rc 0, nenhuma ocorrência |

As quatro etapas do `lint_and_tests.py --strict` rodaram separadas, porque a cópia não tem `.git` e o verificador de caminhos chama `git ls-files`. A chamada direta do `--strict` no export falhou só nesse ponto (`git ls-files` rc 128), e não é achado.

## O que re-derivei e como

1. **Escopo do diff.** `git diff 023dc61..2a561db --stat` lista 6 arquivos. Um deles é `v0100-reviewer-t83.md`, de `b802c36`, que não faz parte da tarefa. Por commit, os três do candidato tocam só `metrics.py`, `app.py`, `rules.yml`, o teste e o README. `app.py` muda só por acréscimo: um import de `Response`, `import metrics`, `app.state.metrics = collector_for(...)` e a rota `GET /metrics`. Nada mudou em `evaluation/`, `comparisons.py`, `v1.py`, prompts ou rótulos; essas mudanças do intervalo `023dc61..c7b06d5` são de `34d7f6a`, da tarefa 83. Não entrou dependência nova: `pyproject.toml` ficou intacto e o `yaml` do teste já era importado por `test_v070_closing.py` e `test_v080_story.py`. Também procurei mecanismo equivalente pré-existente com `git grep -i` por "prometheus", "/metrics" e "text/plain; version" em `src`, `tests`, compose e Dockerfile, e por arquivos com metric, alert ou stats no nome. Não há outro.
2. **Formato**, conferido na saída do meu fluxo, mais abaixo:
   - `Content-Type` é exatamente `text/plain; version=0.0.4; charset=utf-8`.
   - Cada família tem um `# HELP` e um `# TYPE`, nessa ordem e antes das amostras. Famílias sem amostra saem só com HELP/TYPE, o que é válido.
   - No histograma, os `_bucket` são cumulativos (`le` 1, 2, 5, 10, 20, 30, 60 e `+Inf`), `+Inf` é igual a `_count` e há `_sum`.
   - Os valores de rótulo passam por `_escape` (barra invertida, aspas, quebra de linha). Uma rota com aspas, chave e quebra de linha, tentando fechar o rótulo e abrir uma amostra falsa, virou `other`.
3. **Valores contra o trace e o ledger.** Meu fluxo programado, diferente do fluxo do teste, tem 5 mensagens pelo `POST /messages` com token de lojista e a falha `simulate_pricing: UNAVAILABLE`:
   - taxa do débito: `support`/`handoff`, falha de ferramenta, encaminhamento e replanejamento `rule:tool_failure_no_alternative`;
   - "Get XYZ": `knowledge`, com `rule:evidence_insufficient_web`;
   - Clássica × Smart: `knowledge`;
   - recebíveis e antecipação: `support`, com `rule:procedure_gap`;
   - injeção: `out_of_scope`/`refused`.

   Recalculei cada família direto do SQLite e as 34 comparações bateram:
   - `requests_total` (4 séries), `handoffs_total` 1;
   - `tool_calls_total` (5 séries) e `tool_failures_total{tool="simulate_pricing"}` 1;
   - `model_calls_total` por agente: soma 17, igual a `SUM(model_calls)` da tabela `requests`;
   - `replan_total` (4 origens);
   - os 8 buckets, `_count` e `_sum`;
   - `cost_usd_total{provider="scripted"}` 0, com 17 linhas `scripted-v1` liquidadas no ledger;
   - `budget_remaining_usd` igual a `BudgetGuard.remaining()` e a `/ready`, e `budget_limit_usd` igual a `limit_usd`.

   Para o ledger, montei um banco sintético com uma reserva liquidada do `gpt-6-luna`, uma reservada do `claude-opus-5-5`, uma liquidada pelo valor reservado de `some-new-model` e uma cancelada do `deepseek-flash`. A saída foi `openai` 0,015, `anthropic` 0, `unknown` 0,01 e `deepseek` 0, com remaining 0,925 igual a `remaining()`. Depois de liquidar a Anthropic por 0,04, ela passou a 0,04 e remaining a 0,935. O custo conta só o liquidado, nunca diminui e os provedores saem do `prices.json`.
4. **Privacidade e injeção.** Injetei pelo `TraceStore`:
   - tool `tool:cliente1988` → `other`;
   - origem com espaços → `other`;
   - agente `Router Agent!` → `other`.

   Mas `route="cliente1988"`, `status="req_0123456789abcdef0123"`, agente `op_ana` e origens `cliente1988` e `rule:conv_7f3a9c` **viraram rótulos**. Ver P2-1. No fluxo pela API, nenhum rótulo trouxe texto, `request_id`, `conversation_id`, lojista ou operador.
5. **Operação:**
   - Banco ausente: famílias zeradas, remaining = teto, nenhum arquivo ou diretório criado.
   - Com os bancos marcados como somente leitura, o scrape funciona e não altera mtime nem tamanho dos arquivos, sem criar journal (`mode=ro`).
   - O cache de 5 s está coberto por teste: 4,9 s devolvem o texto antigo e 5,0 s, o novo.
   - Banco presente mas sem tabela, ou travado por outro processo: `/metrics` responde 500. Ver P3-3.
   - `/metrics` é público, como `/ready`. Avaliação em P3-4.
6. **Regras.** O YAML carrega com grupo `merchant-assistant` e quatro regras:
   - `BudgetNearLimit`: `budget_remaining_usd < 0.10 * budget_limit_usd`;
   - `ToolFailureRateHigh`: `sum(rate(tool_failures_total[15m])) / sum(rate(tool_calls_total[15m])) > 0.05`;
   - `HandoffRateHigh`: `sum(rate(handoffs_total[1h])) / sum(rate(requests_total[1h])) > 0.30`;
   - `RequestLatencyP95High`: `histogram_quantile(0.95, sum by (le) (rate(request_duration_seconds_bucket[15m]))) > 20`.

   Todas têm `summary`, `description` e `runbook_url`, e o PromQL é sintaticamente plausível (não há `promtool` offline). Os nomes citados existem na saída. O README tem a seção `## Observability`, com a tabela de métricas e o `scrape_config` de duas linhas.
7. **Mutação manual:** 19 mutantes mais 1 controle, sobre cópias de `metrics.py`, `app.py` e `rules.yml`, contra `test_v0100_metrics.py`. **16 mortos, 3 sobreviventes**, um deles equivalente.

| Mutante | Resultado |
| --- | --- |
| M01 `+Inf` = último bucket finito | **sobreviveu** (P3-1) |
| M02 `+Inf` = `_count + 1` | morto |
| M03 rótulo sem sanitizar | morto |
| M04 tool sem conferir o registro | morto |
| M05 `cost_usd_total` incluindo reservas | morto |
| M06 remaining sem as reservas | morto |
| M07 regra citando `tool_attempts_total` | morto (teste de coerência) |
| M08 regra citando `request_latency_seconds_bucket` | morto (teste de coerência) |
| M09 buckets não cumulativos | morto |
| M10 sem cache | morto |
| M11 handoff contando toda requisição | morto |
| M12 Content-Type sem `version` | morto |
| M13 chamadas de modelo por linha, não por `calls` | morto |
| M14 todo resultado de ferramenta `ok` | morto |
| M15 scrape criando banco ausente | morto |
| M16 `TYPE` antes de `HELP` | morto |
| M17 `_escape` removido | sobreviveu, **equivalente**: a sanitização já impede aspas, barra e quebra de linha |
| M18 rota devolvendo `application/json` | morto |
| M19 modelo `scripted*` mapeado para `unknown` | **sobreviveu** (P3-2) |
| M20 controle sem mudança | passou, como esperado |

## Achados

### P1

Nenhum.

### P2

**P2-1. Rota, status, agente e origem de replanejamento não usam vocabulário fechado na camada de métricas.**

- **Condição:** `_label` (`src/merchant_assistant/observability/metrics.py:23` e `:29`), usado em `:98`, `:109` e `:124`, aceita qualquer identificador que case com `^[a-z0-9_:.\-]{1,64}$`. Só a ferramenta é conferida contra um conjunto fechado (`TOOLS`).
- **Impacto:** a garantia da D4 ("sem rótulo com id de lojista") e o que o README promete ("Labels come from closed sets in the code (route, status, agent, tool, outcome, replan origin, provider)", `README.md:442`) dependem só da tipagem a montante. Hoje ela é `Route`/`Status` como `Literal` em `MessageResponse`, chaves de agente fixadas no código e origens `rule:<nome>`, então o caminho não é alcançável pela API. Por isso é P2, não P1. Mas qualquer valor com forma de identificador que chegue ao trace (lojista, `request_id`, operador) vira série, e a cardinalidade fica sem limite. O teste de injeção (`tests/integration/test_v0100_metrics.py:183`) usa só `"Free text route"`, que já falha na regex. O teste de vocabulário (`:152`) confere apenas a saída do fluxo, não a camada.
- **Reprodução:** gravar com `TraceStore.save` um request com `route="cliente1988"`, `status="req_0123456789abcdef0123"`, `detail.models_by_agent={"op_ana": {"calls": 2}}` e um passo `replan` com `origin="cliente1988"`. `metrics.render(...)` devolve `requests_total{route="cliente1988",status="req_0123456789abcdef0123"} 1`, `model_calls_total{agent="op_ana"} 2` e `replan_total{origin="cliente1988"} 1`.
- **Correção sugerida:** mapear para conjuntos fechados, com `other` para o que ficar fora:
  - rota: `get_args(Route)` mais `human_reply`;
  - status: `get_args(Status)`;
  - agente: o conjunto de agentes do código;
  - origem: `model` ou `rule:` mais um nome conhecido do replanejador.

  Acrescentar ao teste de injeção valores com forma de identificador.

### P3

- **P3-1. O teste não distingue `+Inf` de `_count` nem cobre o bucket de 60 s.**
  - **Condição:** as duas comparações valem 3 (`test_v0100_metrics.py:136-137`), e toda duração do fluxo fica abaixo de 1 s.
  - **Impacto:** o mutante M01, `+Inf` igual ao último bucket finito (`metrics.py:139`), sobrevive. Ele erraria para qualquer requisição acima de 60 s.
  - **Correção sugerida:** um trace sintético com `duration_ms` acima de 60 000.
- **P3-2. A asserção do provedor `scripted` é vazia.**
  - **Condição:** `value()` devolve 0,0 quando a série não existe (`test_v0100_metrics.py:75`), então `cost_usd_total{provider="scripted"} == 0` (`:147`) passa sem a série.
  - **Impacto:** M19 sobrevive.
  - **Correção sugerida:** conferir que a série existe.
- **P3-3. Store presente mas ilegível ou travado gera 500.**
  - **Condição:** um arquivo vazio dá `no such table: requests`. Uma transação `EXCLUSIVE` aberta por outro processo dá `database is locked` depois de cerca de 7 s, com `timeout=5` em cada banco (`metrics.py:54-62`). O erro não é guardado no cache, então cada scrape tenta de novo.
  - **Impacto:** é aceitável para um endpoint de operação, porque o Prometheus marca `up=0`, mas não degrada para famílias zeradas.
  - **Encaminhamento:** registrar como decisão, ou tratar com log.
- **P3-4. `/metrics` é público, como `/ready` (`api/app.py:197-201`).**
  - **Avaliação:** aceitável. São só contagens agregadas, o orçamento restante já aparece em `/ready` e nenhum rótulo traz id, desde que P2-1 seja corrigido.
  - **Recomendação:** em produção, restringir por rede ou por token de leitura. Vale uma linha no README.
- **P3-5. `runbook_url` relativo.**
  - **Condição:** `../README.md#observability` (`alerts/rules.yml:16` e nas demais regras).
  - **Impacto:** resolve navegando no repositório, mas não é clicável no Alertmanager.
  - **Correção sugerida:** URL absoluta quando o repositório for público.
- **P3-6. Denominadores das regras incluem requisições que não são do assistente.**
  - **Condição:** `requests_total` e o histograma (`metrics.py:97` e `:127`) contam também as entregas do operador (`route="human_reply"`) e as retomadas (`req_resume_*`).
  - **Impacto:** a taxa de encaminhamento e o p95 (`rules.yml:29` e `:40`) ficam diluídos.
  - **Encaminhamento:** documentar ou filtrar por rota.

Observações sem achado:

- `collector_for` usa o ledger `primary` de um `CombinedBudgetGuard`, enquanto `/ready` usaria `min()`. Hoje o guard combinado só existe na CLI (`cli.py:184`), não na API.
- O scrape relê a tabela inteira a cada 5 s, o que é adequado à escala do projeto.

## Critérios

- **Comprovados:**
  - `/metrics` em texto 0.0.4 válido, com as seis famílias do CA-59 e coerente com o trace e o ledger;
  - `cost_usd_total` só com o liquidado;
  - `budget_remaining_usd` igual a `remaining()`;
  - cache de 5 s;
  - scrape somente leitura, sem criar banco;
  - quatro regras sobre métricas existentes, testadas por coerência;
  - README;
  - suíte estrita verde e caminhos pessoais limpos;
  - `app.py` só por acréscimo;
  - sem dependência nova.
- **Parcial:** "sem dado pessoal nos rótulos" vale pela API, mas não é garantido pela camada de métricas (P2-1).
- **Não verificado:** Prometheus real e `promtool check rules`, por falta de rede e de binário. O `/metrics` ao vivo fica para o QA (tarefa 86).

## Próxima ação

Developer corrige P2-1 e, de preferência, P3-1 e P3-2, que são acréscimos baratos de teste. Os demais P3 ficam a critério, registrados aqui. Depois, nova rodada do Reviewer, restrita a `metrics.py`, ao teste e ao README. Nenhuma decisão humana pendente.

---

# Rodada 2

- **Papel e responsável:** Reviewer (subagente, contexto frio), 2026-11-06.
- **Objetivo e critérios:** confirmar as correções da rodada 1 (P2-1, P3-1 a P3-6) contra as decisões do Supervisor para a rodada 2. A tarefa 85 foi lida só até "## Validação". Spec `rubrica-operacao-v0100.md`, D4, D5 e CA-59.
- **Escopo:** `bed7fe0` (`observability/metrics.py`, `tests/integration/test_v0100_metrics.py`, `alerts/rules.yml`) e `b9bb1ed` (README, seção Observability). Base revisada na rodada 1: `2a561db`.
- **Estado:** **apto para QA**. Nenhum P1 e nenhum P2. P2-1, P3-1, P3-2, P3-3, P3-5 e P3-6 estão resolvidos, P3-4 continua registrado e há 3 P3 novos (P3-7 a P3-9), nenhum bloqueante.
- **Branch e PR:** `codex/v0.10.0-rubrica-operacao`, sem PR.
- **Base e versão final:** revisei o export limpo de `0b1a637` (`git archive`). Os blobs são:
  - `metrics.py 55eaf60`;
  - `test_v0100_metrics.py 3fc6fe1`;
  - `rules.yml 3c1590f`;
  - `README.md f46b22e`;
  - `app.py 978e2c2`, igual à rodada 1.

  Durante a revisão, o HEAD avançou para `0dc2770` (`c1042a5`, `92230de`, `0dc2770`). Esses commits só mexem em `docs/`: `git diff --stat 0b1a637 HEAD -- src alerts tests README.md` sai vazio. O manifesto `v0100-candidato-r1.json` (fixado em `92230de`, com head `c1042a5`) traz sha256 de `rules.yml`, `app.py`, `metrics.py` e do teste que batem com os blobs de `0b1a637`. Ele hasheia o conteúdo LF do blob; o `git archive` desta máquina sai em CRLF por causa do `autocrlf` global, e `git hash-object` devolve os mesmos blobs. O README não está no manifesto e foi conferido pelo blob. No fim da revisão, os blobs eram os mesmos.
- **Independência:** independente. Não implementei nada e não li `v0100-developer.md` nem a Validação ou o Status da tarefa 85. Do manifesto, li cabeçalho e hashes só depois de ter os meus números.

## Comandos e números (rodada 2)

Tudo rodou em cópias de leitura em `<scratchpad da sessão>`: um export para a suíte e outro export para mutações e sondas. Usei o Python do `.venv` com `PYTHONPATH` no `src/` de cada cópia, conferindo que o módulo carregado era o da cópia, e `--basetemp` em forma Windows passado como argumento, com `.pytest_cache` criado antes. Não houve chamada paga, rede, Docker nem Git de escrita. Não toquei em `data/runtime/`, `.pytest_cache/qa-*` nem `.env`.

| Verificação | Resultado |
| --- | --- |
| `pytest` (export de `0b1a637`) | **2147 passed, 1 skipped, 0 failed**, 1014 s, rc 0. O skip é anterior à tarefa: `test_v070_identity_r2.py:277` só roda com o `--basetemp` do projeto |
| `ruff check` (os 168 arquivos que `lint_and_tests.py` lista) | All checks passed |
| `validate_structure` e `validate_skills` | válidas |
| `checar-caminhos-pessoais.py` (os 780 arquivos rastreados de `0b1a637`, passados como argumento) | rc 0, nenhuma ocorrência |
| Mutação manual (23 mutantes mais 1 controle, contra `test_v0100_metrics.py`) | **23 mortos, 0 sobreviventes**. O controle passou |
| Sondas próprias (3 testes, só na cópia de mutação) | passaram. Detalhes abaixo |

As quatro etapas do `--strict` rodaram separadas, porque o export não tem `.git`. É o mesmo motivo da rodada 1.

## O que re-derivei e como (rodada 2)

1. **Escopo.** `git show --stat` confirma que `bed7fe0` toca só `metrics.py`, `rules.yml` e o teste, e que `b9bb1ed` toca só o README. Os demais arquivos de `2a561db..b9bb1ed` são das tarefas 83 e 84. `app.py` não mudou. Não entrou dependência nova: os imports novos são `logging`, `typing.get_args` e `api.schemas`, e a suíte e o app sobem sem import circular.
2. **Conjuntos fechados contra a fonte.**
   - Agentes: os 11 `CallSpec(` de `src/` têm `agent=` literal e dão 9 nomes: `router`, `knowledge`, `customer_support`, `escalation`, `personality`, `replan`, `judge`, `rerank` e `embeddings`, este último via `reserve` direto e também no `AGENT` do MCP. Todos estão em `AGENTS`.
   - Origens: só `agents/replanner.py` produz origem: `rule:planner_unavailable`, `rule:{name}` das recusas, `rule:nothing_to_review` e `rule:{m.rule}`. As 16 regras são iguais a `REPLAN_RULES`.
   - Rota, status, ferramenta e provedor: `ROUTES = get_args(Route) + human_reply`, `STATUSES = get_args(Status)`, `TOOLS`, e `prices.json` mais `scripted` e `unknown`.
   - Desvio: `_closed` devolve o membro do conjunto ou `other`, nunca o valor cru.
3. **Injeção pelo `TraceStore`, lida pela rota HTTP.** Gravei 7 identificadores (`cliente1988`, `op_ana`, `req_feedbeefcafe0001`, `conv_9b2d`, `lojista42`, `Ana Souza`, `op-joao`) como rota, status, chave de `models_by_agent`, origem, `rule:<id>` e `tool:<id>`, além de uma linha do ledger com modelo `cliente1988`.
   - `GET /metrics` respondeu 200 e **nenhum identificador apareceu**.
   - Tudo isso virou `other`: `requests_total{route="other",status="other"} 7`, `model_calls_total{agent="other"} 7`, `tool_failures_total{tool="other"} 14` e `replan_total{origin="other"} 14`. O custo foi para `provider="unknown"`.
   - Os valores legítimos se mantiveram: `knowledge`/`answered` 1 e `origin="model"` 7.
4. **Banco travado por outro processo.** Um subprocesso abriu `BEGIN EXCLUSIVE` e segurou a transação por 6 s, depois de um `POST /messages` real com o modelo programado.
   - Trace travado: 200 em 1,47 s, com texto idêntico à última leitura completa.
   - Ledger travado: 200 em 1,52 s, também idêntico.
   - Trace travado antes da primeira leitura: 200 com as famílias zeradas e válidas (`handoffs_total 0`).
   - Ledger travado antes da primeira leitura: ver P3-8.
5. **Banco vazio ou corrompido.** Arquivo vazio, 8 KiB aleatórios e só o cabeçalho SQLite responderam 200, com `text/plain; version=0.0.4` e as 33 linhas de todas as famílias. Uma linha com tipo inválido gerou exceção: ver P3-7.
6. **Regras.** As `expr` não mudaram. Uma checagem por tokens, no lugar do `promtool`, confirmou:
   - parênteses balanceados;
   - todo `rate(` com intervalo;
   - intervalos só depois de nome de métrica;
   - métricas citadas existentes.

   O `runbook_url` é absoluto nas 4 regras (`https://github.com/lauroPereira/ai-getnet-case#observability`). O repositório ainda é privado, então o link só resolve para quem tem acesso.
7. **README.** Documenta os conjuntos fechados com `other`, o banco ilegível (última leitura completa, zerado antes da primeira) e os denominadores que incluem `human_reply` e as retomadas.
8. **Mutação**, com os arquivos restaurados ao blob original depois de cada mutante:

| Mutante | Resultado (teste que matou) |
| --- | --- |
| M01 `+Inf` = último bucket finito | morto (`test_histogram_inf_bucket_counts_requests_above_the_last_bound`) |
| M19 `scripted` → `unknown` | morto (`test_values_match_the_recorded_traces`, via `present`) |
| M03 `_closed` devolve o valor cru (rótulo sem sanitizar) | morto (identificadores e texto livre) |
| M21 a M25 rota, status, agente, origem ou ferramenta fora do conjunto fechado, um por vez | todos mortos (`test_identifier_shaped_values_in_the_traces_come_out_as_other`) |
| M26 e M27 `except` estreitado no trace e no ledger | mortos (banco vazio e endpoint 200) |
| M28 nunca servir a última leitura completa | morto |
| M29 leitura incompleta marcada como completa | morto |
| M30 timeout de abertura de 30 s | morto (limite de tempo do teste) |
| M31 `ROUTES` sem `human_reply` | morto (teste de deriva) |
| M32 `REPLAN_RULES` sem `procedure_gap` | morto (teste de deriva) |
| M33 `AGENTS` sem `rerank` | morto (teste de deriva) |
| M34 `AGENTS` sem `router` | morto |
| M35 todo resultado de ferramenta `ok` | morto |
| M37 última leitura completa nunca guardada | morto |
| M39 custo incluindo as reservas | morto |
| D1 regra renomeada numa cópia de `replanner.py` | morto (teste de deriva) |
| D2 agente renomeado numa cópia de `rerank.py` | morto (teste de deriva) |
| D3 regra nova acrescentada em `replanner.py` | morto (teste de deriva) |
| M00 controle sem mudança | passou |

## Achados (rodada 2)

### P1

Nenhum.

### P2

Nenhum. **P2-1 resolvido:** a camada de métricas fecha os sete conjuntos. Os mutantes M03 e M21 a M25 morrem, e a sonda 3 não vaza nenhum identificador.

### Situação dos P3 da rodada 1

- **P3-1 resolvido.** M01 morre.
- **P3-2 resolvido.** M19 morre, com `present`.
- **P3-3 resolvido.** Ver as sondas 4 e 5 e os mutantes M26 a M30 e M37. Os resíduos estão em P3-7 e P3-8.
- **P3-4 continua registrado.** O README diz "public like `/ready`", mas não traz a linha sobre restringir em produção. Não bloqueia; cabe na leitura final do README (bloco E).
- **P3-5 resolvido.** A URL é absoluta e só resolve para quem tem acesso enquanto o repositório for privado.
- **P3-6 resolvido** por documentação (`README.md:461-463`).

### P3 novos

- **P3-7. Linha com tipo inválido derruba o scrape.**
  - **Condição:** `seconds = duration_ms / 1000` (`metrics.py:171`) recebe texto, e só `sqlite3.Error` é capturado (`metrics.py:119` e `:192`).
  - **Impacto:** `TypeError` e 500. O `TraceStore` grava sempre inteiro, então o caso só aparece com adulteração manual do banco. O README promete "empty or locked", o que é exato, mas a docstring do módulo diz "empty, corrupt or locked".
  - **Reprodução:** gravar o texto `abc` em `requests.duration_ms` (`UPDATE` direto no banco) e chamar `GET /metrics`, que levanta `TypeError`, divisão de `str` por `int`. O mesmo com `calls` em texto não falha, porque o `SUM` do SQLite devolve 0.
  - **Sugestão:** `CAST(duration_ms AS REAL)` no SQL, ou registrar.
- **P3-8. Ledger ilegível antes da primeira leitura completa mostra o orçamento inteiro.**
  - **Condição:** `_build_ledger_families(None)` emite `budget_remaining_usd = limit` (`metrics.py:213`).
  - **Impacto:** nessa janela, o gauge mostra o orçamento cheio e `BudgetNearLimit` não dispara. É transitório: o busy timeout é de 1 s, as transações do `BudgetGuard` são curtas, uma nova tentativa vem a cada 5 s, e depois da primeira leitura completa vale a última. A sonda não distingue os valores porque o modelo programado custa 0.
  - **Sugestão:** omitir a amostra de remaining quando o ledger não foi lido, ou documentar.
- **P3-9. `AGENTS` tem dois nomes que não são agentes, e o teste de deriva compara só numa direção.**
  - **Condição:** `web` e `support` (`metrics.py:37`) são chaves de seleção de modelo (`llm_for("support")`, `SPECIALISTS`), e nenhum `CallSpec` usa esses nomes. O teste de deriva confere `agents <= metrics.AGENTS` (`test_v0100_metrics.py:255`), não igualdade, como o Supervisor pediu.
  - **Impacto:** inofensivo para a privacidade, porque o conjunto continua fechado. Mas entradas mortas e agentes removidos não são detectados.
  - **Sugestão:** remover os dois nomes e usar igualdade, ou registrar.

Observação sem achado: o teste de banco travado do repositório usa uma segunda conexão no mesmo processo (`test_v0100_metrics.py:294`). Repeti o cenário com outro processo (sonda 4) e o comportamento foi o mesmo.

## Critérios (rodada 2)

- **Comprovados:**
  - CA-59: texto 0.0.4 válido com as famílias exigidas, coerente com o trace;
  - D4, "sem rótulo com id de lojista", agora garantido pela camada de métricas, não só pela API;
  - banco vazio, corrompido ou travado sem 500, servindo a última leitura completa ou o zerado antes da primeira;
  - D5: quatro regras sobre métricas existentes, com `runbook_url` absoluto;
  - teste de deriva efetivo (D1 a D3 morrem);
  - suíte estrita verde e caminhos pessoais limpos.
- **Não verificado:** `promtool check rules` e Prometheus real, por falta de binário e de rede. O `/metrics` ao vivo fica para o QA (tarefa 86).

## Próxima ação (rodada 2)

QA da tarefa 85, com `/metrics` ao vivo, no fechamento (tarefa 86). P3-4 e P3-7 a P3-9 ficam a critério do Developer e do Supervisor, registrados aqui; nenhum bloqueia. Nenhuma decisão humana pendente.
