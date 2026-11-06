# Passagens do Developer — v0.10.0

## Tarefa 83 — Rubrica `judge.v4` e remedição dos dois juízes (rodada 1)

- **Papel e responsável:** Developer, subagente despachado pelo Supervisor (time único).
- **Objetivo e critérios:** [tarefa 83](../tasks/83-rubrica-judge-v4-remedicao.md); [spec v0.10.0](../specs/rubrica-operacao-v0100.md) D1, D2, CA-57; [história](../historias/rubrica-operacao-v0100.md) momentos 1 a 3; [ADR 0021](../architecture/decisions/0021-juiz-modelo-e-regua.md).
- **Escopo:** prompt novo, código, testes, Validação e Status da tarefa 83 e esta passagem. `prompts/judge.v3.md`, rótulos, cenários, migrações, snapshots e ledger não mudaram.
- **Estado:** implementado; aguarda revisão.
- **Branch e base:** `codex/v0.10.0-rubrica-operacao`, base `0266652` (merge da `main` feito pelo Supervisor, mesma árvore de `ce011b5`). Commits: `1655e80` (prompt `judge.v4` e rubrica selecionável no juiz), `9e66d20` (`--rubric` nas duas CLIs, relatório multi-bloco, testes) e o commit desta passagem. Identidade conferida antes de cada commit: `lauroPereira <lauro.s.pereira@gmail.com>`. Sem push.
- **Independência:** não se aplica (implementação).

### Arquivos

- Novos: `prompts/judge.v4.md`, `tests/unit/evaluation/test_judge_v4.py` (5 testes), `tests/integration/test_v0100_rubric.py` (3 testes, momentos 1 a 3).
- Alterados: `evaluation/judge.py` (`RUBRIC_VERSIONS`, `rubric_version()`, `validate_judge(rubric=)`, `resolve_judge(rubric=)`; `RUBRIC_VERSION` continua `"3"`), `evaluation/scripted_judge.py` (`scripted_judge(rubric=)`), `evaluation/calibration.py` (filtro por rubrica em `judgement_for`, `link`, `_judge_rows`, `judge_executions`, `choose_run`, `judge_runs`; `render_blocks`, `d2_rule`, `GENERIC_SAMPLES`; `import_filled(rubric=, more=)`; tabelas de consistência, custo e tokens extraídas para `_run_tables`, usadas pelos dois relatórios), `cli.py` (`eval --rubric v3|v4`; `eval-calibrate --judge/--judge-run/--rubric` repetíveis), `tests/unit/evaluation/test_judge_v3.py` (ver decisão 7).

### Diff `judge.v3` → `judge.v4`

```diff
--- a/prompts/judge.v3.md
+++ b/prompts/judge.v4.md
@@ -1,6 +1,6 @@
 ---
 id: judge
-version: 3
+version: 4
 ---
@@ -32,9 +32,10 @@ each score:
 unsupported_claim is true only when the reply asserts a fact, amount, date, status or promise that the evidence does
-not support or contradicts. Declining, asking for clarification or saying that something could not be confirmed is
-not an unsupported claim. With no evidence at all and no evidence_notes, a reply that only guides, declines or hands
-over is fine; a reply that states specific facts is an unsupported claim.
+not support or contradicts, or a general claim stated as fact with no source in the evidence (for example 'rates vary
+by contract' or 'approval depends on analysis' when no passage says so). Declining, asking for clarification or saying
+that something could not be confirmed is not an unsupported claim. With no evidence at all and no evidence_notes, a
+reply that only guides, declines or hands over is fine; a reply that states specific facts is an unsupported claim.
```

Além do número da versão, a única mudança de texto é o trecho inserido ", or a general claim stated as fact with no source in the evidence (for example 'rates vary by contract' or 'approval depends on analysis' when no passage says so)"; o resto do parágrafo só foi requebrado em 120 colunas. O teste `test_v4_is_v3_plus_the_one_sentence_and_v3_is_untouched` confere isso com o espaço em branco normalizado e confere também o SHA-256 do `judge.v3.md` (LF) contra o da v0.9.0: `45d59f0c…52bd`, o mesmo de `git show ce011b5:prompts/judge.v3.md`.

### Comandos para o QA (momentos 1 a 3)

```text
# 1. DeepSeek (juiz padrão) sob judge.v4
merchant-assistant eval --judge-repeat 3 --answers-from docs/evidence/v080-all-r3.json \
  --only-sample docs/evidence/v080-calibracao-amostra.csv --rubric v4 --name v0100-juiz-deepseek-v4
# 2. Opus sob judge.v4 (ledger Anthropic)
JUDGE_PROVIDER=anthropic JUDGE_MODEL=claude-opus-5-5 merchant-assistant eval --judge-repeat 3 \
  --answers-from docs/evidence/v080-all-r3.json --only-sample docs/evidence/v080-calibracao-amostra.csv \
  --rubric v4 --name v0100-juiz-opus-v4
# 3. Os quatro blocos num relatório só (O = juiz da campanha original, DeepSeek judge.v3)
merchant-assistant eval-calibrate --import <csv preenchido> --rater lauro \
  --judge deepseek/deepseek-flash --judge-run v0100-juiz-deepseek-v4 --rubric v4 \
  --judge anthropic/claude-opus-5-5 --judge-run v090-juiz-opus-r3 --rubric v3 \
  --judge anthropic/claude-opus-5-5 --judge-run v0100-juiz-opus-v4 --rubric v4 \
  --campaign v0100-juiz-v4 --out docs/evidence/v0100-juiz-v4.md
```

O comando do momento 3 da história com um `--judge` só gera dois blocos (O e o pedido). Os quatro blocos saem de um comando com os três `--judge`. Rodar de novo com o Opus sob a mesma `--campaign` religaria as notas dessa campanha aos julgamentos do Opus. Prefira o comando único.

### Evidência

- Testes novos: **8 passed** (5 em `tests/unit/evaluation/test_judge_v4.py`, 3 em `tests/integration/test_v0100_rubric.py`). As suítes afetadas (`test_v090_judge`, `test_calibration_flow`, `test_eval_campaign`, `tests/unit/evaluation`, `tests/unit/llm`) passaram todas, exit 0.
- **Relatório da v0.9.0 byte a byte.** Pelo critério da tarefa, o relatório da v0.9.0 regenerado tem de sair idêntico. Os `request_id` são aleatórios a cada execução, então gerar o cenário duas vezes não serve de comparação. Fiz assim: montei uma vez o estado (campanha programada, amostra de 24 avaliada e importada, 72 julgamentos `v090-juiz-opus-r3` do Opus programado) com o código de `ce011b5`, extraído por `git archive` no scratchpad. Depois renderizei sobre cópias do mesmo banco, com `now` fixo, o relatório v0.8.0 (sem `--judge`) e o v0.9.0 (`--judge anthropic/claude-opus-5-5 --judge-run v090-juiz-opus-r3`, sem `--rubric`), uma vez com o código de `ce011b5` e outra com o desta branch. `cmp` não acusou diferença: v0.8.0 com SHA-256 `eb9877e8…96e4fc` e v0.9.0 com `e137e67c…31af0` nas duas versões. Os scripts ficaram no scratchpad e não foram versionados. O teste versionado `test_rubric_v3_by_name_is_the_v090_report_and_bad_blocks_are_refused` confere que `--rubric v3` explícito gera o mesmo relatório que a ausência de `--rubric`. O teste existente da v0.9.0 confere o relatório v0.8.0 antes e depois.
- Cobertura programada dos critérios: `eval --judge-repeat 3 --rubric v4` grava 72 julgamentos com `rubric_version` `4` e `evaluator.prompt` `judge@4`, tanto no DeepSeek (o modelo programado atrás da fábrica real) quanto no Opus (SDK real sobre transporte em memória). O Opus recebe o prompt v3 nas 72 chamadas da `r3` e o v4 nas 72 da execução v4. Sem `--rubric`, o julgamento grava `3`. O `eval-calibrate` com três `--judge` gera os quatro blocos (O, A, B, C), a tabela das genéricas com a contagem por bloco e a linha D2 calculada (A contra O e C contra B). As notas da campanha nova ficam ligadas às 24 do bloco A (`rubric_version` `4`). Recusas, todas sem gravar nada: execução nomeada sob outra rubrica, contagem de `--judge-run` ou de `--rubric` diferente da de `--judge`, `--rubric` sem `--judge`, bloco repetido, campanha igual à original, CSV com nota diferente da gravada.
- `.env` não lido. As settings só carregam depois do `parse_args`, e os testes usam `Settings(_env_file=None)` ou a fixture. Nenhuma rede, nenhuma chamada paga.

### Suíte estrita

`python tools/scripts/lint_and_tests.py --strict` (venv da `.venv`) no HEAD `9e66d20`, com `PYTEST_ADDOPTS="--basetemp=<scratchpad da sessão>/suite-bt -p no:cacheprovider"`: **2115 passed, 1 skipped** em 854,50 s; ruff `All checks passed!`; caminhos pessoais: nenhuma ocorrência em 764 arquivos; estrutura e skills válidas; "Validação estrita concluída sem falhas", exit 0, 879 s no total. Log no scratchpad da sessão (não versionado), SHA-256 `f3e2c892…509be4`. O skip não é de teste novo (os 8 novos passaram nas execuções focadas e na suíte). Outra suíte estrita rodava ao mesmo tempo em outro worktree; não houve interferência.

### Decisões tomadas além do texto do plano (todas reversíveis)

1. **`--rubric` vale também em `eval --judge`.** O caminho da campanha usa o mesmo construtor de juiz do `--judge-repeat`. Sem juiz, `--rubric v4` é ignorado com aviso no stderr, como já acontece com `--only-sample`. O padrão continua `v3` nos dois caminhos.
2. **Pareamento dos blocos no `eval-calibrate`.** `--judge`, `--judge-run` e `--rubric` usam `action="append"` e se pareiam pela ordem. Com um `--judge` só, `--judge-run` e `--rubric` são opcionais, como na v0.9.0. Com mais de um, cada `--judge` precisa do seu `--judge-run`, e `--rubric` vem para todos ou para nenhum. Um `str` solto, como no `Namespace` dos testes da v0.9.0, também é aceito. O primeiro bloco é o "pedido": é a ele que as notas da `--campaign` nova ficam ligadas. Os demais só entram no relatório, nada é gravado para eles. Os rótulos são O (original) e A, B, C… (no máximo 8).
3. **Quando sai o relatório multi-bloco.** Ele sai com rubrica diferente de v3 ou com mais de um `--judge`. Com um `--judge` sob v3, o renderizador continua o da v0.9.0, por isso o byte a byte. As três tabelas finais (consistência, custo, tokens) passaram para `_run_tables`, com saída idêntica.
4. **Linha D2.** Cada bloco `judge.v4` é comparado com o bloco `judge.v3` do mesmo juiz, o original primeiro. Sem esse bloco, a linha diz "condições não calculadas". Cada condição mostra os números e "sim/não", e a linha fecha com "Três condições atendidas: sim/não". Ela não diz se a v4 vira padrão. O texto lembra que só o juiz padrão (`deepseek/deepseek-flash`, constante `D2_JUDGE`) decide e que a decisão é da tarefa 86. Tolerância: ±1 com queda de até 0,05 inclusive (com 24 notas, 1 resposta vale 0,042 e passa; 2 valem 0,083 e não passam). "Não cai" é ≥, e veredito igual passa.
5. **Frases genéricas fixadas em `GENERIC_SAMPLES = ("S01", "S13", "S16", "S21")`**, os ids da amostra da v0.8.0 citados na spec e na ADR 0021. Num CSV sem algum deles, a tabela conta "k de n" sobre os presentes e lista os ausentes.
6. **Execução nomeada sob outra rubrica é erro explícito** ("a execução 'X' do juiz Y gravou julgamentos judge.v3, não judge.v4: confira --rubric"), em vez do "não tem julgamento da execução". As mensagens da v0.9.0 sob v3 continuam iguais.
7. **Teste ajustado:** `test_v3_is_the_latest_and_v2_stays_loadable` passou a se chamar `test_v3_is_the_default_and_v2_stays_loadable`. O arquivo mais novo agora é o `judge.v4` (fato novo da spec); o teste fixa a v3 por `RUBRIC_VERSION` e confere que `load_prompt("judge")` sem versão dá `4`. Nenhum outro teste existente mudou.
8. **O juiz programado (`scripted_judge`) não imita a frase nova.** Ele só registra o prompt que recebeu. Os testes de v4 usam handlers próprios que marcam respostas quando o prompt traz a frase da v4.

### Achados e limitações

- **Efeito colateral de um prompt novo (não alterado).** `prompt_versions()` devolve a versão mais nova de cada arquivo, e com isso `judge` passa a aparecer como `"4"` em dois lugares. O primeiro é `Orchestrator.versions()["prompts"]`, onde o padrão da campanha continua v3, de modo que esse número não diz qual rubrica está em uso. O segundo é o contexto `prompt_set` das comparações de perfis: células gravadas antes deste deploy deixam de ser reaproveitadas, o mesmo que acontece com qualquer prompt novo (por exemplo, `router.v6`). Os agentes não usam o juiz. Deixei como está; se o Supervisor quiser, dá para excluir `judge` do `prompt_set` ou mostrar a versão fixada, mas isso fica fora da tarefa.
- **Outro escritor na mesma árvore.** Entre 21:47 e 21:51 apareceram modificações não commitadas que não são minhas em `src/merchant_assistant/api/app.py`, `api/v1.py`, `comparisons.py`, `data/migrations.py` e `tests/unit/data/test_migrations.py` (pelo conteúdo, a tarefa 84), durante a minha suíte estrita (21:36 a 21:50). Não toquei nelas nem as commitei. A suíte coletou e importou os módulos às 21:36; um módulo importado só depois disso pode ter visto a versão alterada. Se o Reviewer quiser certeza, basta rodar de novo a suíte num worktree limpo em `3b180ff` ou depois.
- O relatório real só existe depois do rejulgamento pago (momentos 1 e 2), que é do QA.

### Próxima ação

Reviewer, em contexto novo: revisar `0266652..HEAD` contra a tarefa 83. Depois o QA roda os momentos 1 a 3 com os comandos acima, e o Supervisor aplica a D2 na tarefa 86.

## Tarefa 84 — Comparação retomável após reinício (rodada 1)

- **Papel e responsável:** Developer, subagente despachado pelo Supervisor (time único).
- **Objetivo e critérios:** [tarefa 84](../tasks/84-comparacao-retomavel.md); spec [rubrica-operacao-v0100](../specs/rubrica-operacao-v0100.md) D3, D6, CA-58; história, momentos 4 e 5.
- **Escopo:** `src/merchant_assistant/data/migrations.py` (0012), `src/merchant_assistant/comparisons.py`, `src/merchant_assistant/api/app.py` (`lifespan`), `src/merchant_assistant/api/v1.py` (só a rota nova), `docs/contracts/api-v040.md` (seção "Acréscimos da v0.10.0"), `tests/integration/test_v0100_comparison_resume.py` (novo), `tests/unit/data/test_migrations.py`; asserções de versão em `tests/integration/test_v1_api.py`, `test_use_cases.py`, `test_v070_story.py` e `test_v060_api.py`. Não toquei em `evaluation/`, `cli.py` nem `prompts/`.
- **Estado:** apto para revisão.
- **Branch:** `codex/v0.10.0-rubrica-operacao`, sem push (push é do Supervisor).
- **Base e versão final:** base `f4dfb97` (passagem da tarefa 83); commits `4b6891b` (migração 0012), `b6f7e19` (retomada), `ee7774a` (contrato). A tarefa e esta passagem vão num commit de documentação logo depois. Identidade conferida: `lauroPereira` / e-mail do projeto.
- **Independência:** não-independente (autor). A revisão precisa de contexto novo.

### O que mudou

- **Migração 0012 `comparison_interrupted`:** o `CHECK` da 0008 não aceitava `interrupted`. A tabela é recriada (nova, cópia, drop, rename, índice `comparisons_owner_v060` recriado; nada referencia `comparisons`). O rollback converte `interrupted` em `failed` e restaura o `CHECK`. Esquema 12, reportado em `/ready`.
- **`interrupted`:** no `lifespan` (`comparisons.interrupt_orphans`, com `try/except` como a recuperação do outbox), toda linha `running` sem thread viva neste processo vira `interrupted`, com log `comparison interrupted` e `event={"comparison_id": ...}`. `read()` faz o mesmo e deixa de marcar `failed`. As células não mudam: as concluídas ficam como estão, as pendentes continuam `pending` (antes viravam `skipped`).
- **`POST /v1/comparisons/{id}/resume?retry_failed=false`:** mesmas regras de principal da leitura. Relê `config` e `cells` e pula as células com `request_id`. Com `retry_failed=true`, as células `failed` voltam a `pending`. Verifica orçamento e limite demo só para o que falta (mesmo teto por célula do `estimate`) e roda na thread como `start`, partindo do `cost_usd` e das `failures` gravados: o teto confirmado vale para a comparação inteira e o custo acumula. O estado final continua sendo calculado como hoje. `202 {comparison_id, state, resumed_cells}`.

### Decisões tomadas além do texto do plano (todas reversíveis)

1. **A tentativa em curso fica registrada.** Hoje o `request_id` da célula só vai para o banco quando ela termina. Se o processo morre durante a chamada, o ledger guarda linhas de um `request_id` que nenhuma célula conhece. Agora `_run` grava `in_flight_request_id` na célula antes de chamar `execute_run` e remove esse campo ao terminar. Ao marcar `interrupted`, o campo vira `interrupted_attempts: [{request_id, cost_usd}]`, com o custo lido do ledger (liquidado, ou reservado se nunca foi liquidado), e esse custo entra no `cost_usd`. A célula continua `pending` e roda de novo na retomada, porque não tem resultado. Assim todo `request_id` do ledger aponta para uma célula, e o QA consegue conciliar o ledger antes e depois (CA-58). A tentativa interrompida é o único gasto que não vira resultado; ela fica documentada, não some.
2. **`retry_failed` guarda o histórico:** o `request_id` da falha vai para `previous_request_ids` da célula.
3. **Novos `409`, todos com código próprio:** `comparison_completed`, `comparison_running` (com o thread vivo, outra comparação do principal rodando ou retomada concorrente; a reserva é um `UPDATE ... WHERE state=<anterior>` dentro de `BEGIN IMMEDIATE`), `nothing_to_resume` (por exemplo, `partial` só com falhas e sem `retry_failed`) e `fixed_factors_changed` (base de conhecimento ativa, `prompt_set` ou modo de execução diferentes dos da configuração: misturar células simuladas e reais, ou prompts diferentes, quebraria a comparabilidade). Também `422 admin_scope_required`, como em `POST /v1/comparisons`.
4. **Limite demo sem contar duas vezes:** a célula devolvida no fim de uma execução ganha `demo_refunded`. A retomada conta de novo só essas (as outras já foram contadas no `start`) e nunca devolve uma célula duas vezes. `model_calls` de células terminadas antes não é recalculado.
5. **Retomada de `partial`/`failed` também é aceita** (a tarefa só exige `409` para `running`/`completed`). Células `skipped` (teto, orçamento, base trocada) não têm `request_id` e rodam de novo. A trava de base trocada em `_run` passou a pular só células sem resultado, para não apagar as concluídas.
6. **Teste antigo ajustado ao comportamento novo da spec:** `test_comparison_requires_confirmation_and_fresh_estimate_and_lost_threads_fail` passou a se chamar `..._lost_threads_are_interrupted` e verifica `interrupted` com a célula ainda `pending`. As listas de passos de migração e as asserções `schema == 11` passaram a usar o 12.

### Evidência

- Testes novos: **6** (4 em `tests/integration/test_v0100_comparison_resume.py` e 2 da 0012 em `tests/unit/data/test_migrations.py`). Simulação do `taskkill`: a comparação roda de verdade até a segunda execução nova, e a partir daí nada do thread chega ao banco. Um app novo (orquestrador e modelo programado novos) sobre o mesmo runtime, com `TestClient` em `with`, roda o `lifespan`.
  - interrupção → `interrupted` gravado pelo `lifespan` antes de qualquer GET; célula concluída intacta; 3 `pending`; `interrupted_attempts` com o `request_id` morto. Retomada → `completed`, 4 células. `execute_run` roda só nas 3 que faltavam; todas as chamadas do modelo programado depois do reinício acontecem dentro dessas 3. O ledger da célula concluída e da tentativa interrompida fica igual, entram só os 3 `request_id` novos, e o `cost_usd` é a soma das células mais a tentativa;
  - `409 comparison_running` com o thread vivo (e um app novo no mesmo processo não marca essa comparação), `409 comparison_completed`, `404` ausente ou de outro dono, `401` sem token;
  - `partial` → `409 nothing_to_resume`; `?retry_failed=true` → só a célula falha roda, com `previous_request_ids`, e o estado final é `completed`;
  - orçamento restante abaixo de 3 × teto → `429 installation_budget_exceeded`, exatamente 3 × teto basta; prompts diferentes → `409 fixed_factors_changed`; recusas não mudam o estado.
- Focados: `test_v0100_comparison_resume.py` + `test_migrations.py` + `test_v1_api.py` com **49 passed**. Vizinhos (`test_v060_api`, `test_v060_r2`, `test_v060_r4`, `test_v070_identity_r2`, `test_use_cases`, `test_v070_story`, `test_v070_webhooks`) verdes depois de corrigir a lista de passos da 0006 em `test_v1_api.py`, a única falha da primeira rodada.
- OpenAPI gerado pelo FastAPI: `/v1/comparisons/{comparison_id}/resume` com `retry_failed`, `202`/`409`/`422`, `SessionBearer`; 37 caminhos.
- **Suíte estrita:** `python tools/scripts/lint_and_tests.py --strict` (`.venv`) no HEAD `ee7774a`, com `PYTEST_ADDOPTS="--basetemp=<scratchpad da sessão>/t84/bt -p no:cacheprovider"`: **2121 passed, 1 skipped** em 945,84 s (2115 da tarefa 83 + 6 novos; o skip é o mesmo de antes); ruff `All checks passed!`; caminhos pessoais: nenhuma ocorrência em 766 arquivos; estrutura e skills válidas; "Validação estrita concluída sem falhas", exit 0, 971 s. Log no scratchpad da sessão (não versionado), SHA-256 `ac8a9b6d…df104d83`. Durante a suíte, outro papel rodava pytest e mutação em cópias próprias (`<scratchpad da sessão>/head` e `/mut`), fora desta árvore.
- Nenhuma chamada paga, `.env` não lido, nenhum servidor iniciado. Os processos de espera que eu abri foram encerrados.

### Achados e limitações

- O `taskkill` real (D6, CA-58) é do QA: a simulação prova a lógica, não o comportamento do SQLite e do ledger sob morte abrupta do processo. Se a API morrer entre o `_save` do `in_flight_request_id` e a primeira reserva do ledger, a tentativa aparece com `cost_usd` 0, o que é correto.
- A interface web não muda (decisão da tarefa): `interrupted` e os campos novos das células aparecem como estão. A web ainda não tem botão de retomada; a retomada é pela API.
- Uma janela curta já existente (`start` e `resume` registram o thread antes de `thread.start()`) pode, em tese, fazer uma leitura concorrente marcar `interrupted` uma comparação que acabou de começar. O thread grava o estado final de qualquer forma. Não mexi nisso.
- O `prompt_set` inclui o `judge` (achado da tarefa 83): uma comparação iniciada antes de um prompt novo entrar não pode ser retomada (`409 fixed_factors_changed`), de propósito.

### Próxima ação

Reviewer, em contexto novo: revisar `f4dfb97..HEAD` contra a tarefa 84. Depois, QA da D6 com modelo real (2 perfis × 3 cenários, `taskkill` com a primeira célula concluída, reinício, `resume`, ledger antes e depois). O Supervisor marca o CA-58 depois da revisão e do QA.

## Tarefa 85 — `/metrics` e regras de alerta versionadas (rodada 1)

- **Papel e responsável:** Developer, subagente despachado pelo Supervisor (time único).
- **Objetivo e critérios:** [tarefa 85](../tasks/85-metrics-e-alertas.md); spec [rubrica-operacao-v0100](../specs/rubrica-operacao-v0100.md) D4, D5, CA-59; história, momentos 6 e 7.
- **Escopo:** `src/merchant_assistant/observability/metrics.py` (novo), `src/merchant_assistant/api/app.py` (só acréscimo: import, `app.state.metrics` e rota `GET /metrics`), `alerts/rules.yml` (novo), `tests/integration/test_v0100_metrics.py` (novo), `README.md` (só a seção Observability). Não toquei em `comparisons.py`, `api/v1.py`, `evaluation/`, `prompts/`, `data/migrations.py` nem `docker-compose.yml`.
- **Estado:** apto para revisão.
- **Branch:** `codex/v0.10.0-rubrica-operacao`, sem push.
- **Base e versão final:** base `023dc61`; commits `29add9c` (módulo e rota), `7638f18` (regras e testes), `2a561db` (README), mais um commit de documentação com esta passagem e a tarefa. O `b802c36` (revisão da tarefa 83) entrou na branch no meio do trabalho, sem conflito. Identidade conferida: `lauroPereira` / e-mail do projeto.
- **Independência:** não-independente (autor). A revisão precisa de contexto novo.

### O que mudou

- **`metrics.py`:** consultas agregadas, somente leitura (`mode=ro`), em `traces.sqlite3` e no ledger. Nenhuma biblioteca Prometheus. Formato texto 0.0.4 com `# HELP` e `# TYPE`. `MetricsCollector` guarda um cache de 5 s em processo, com trava e relógio injetável. `collector_for` usa os caminhos do `TraceStore` e do `BudgetGuard` do orquestrador. Com o orquestrador placeholder, usa os padrões do runtime.
- **Métricas:** `requests_total{route,status}` (rota e status do assistente gravados em `requests`; não é a rota HTTP), `model_calls_total{agent}` (soma de `models_by_agent[*].calls` do `detail`), `tool_calls_total{tool,outcome}` e `tool_failures_total{tool}` (passos `tool:*`, `outcome` `ok` ou `error`), `handoffs_total` (`status='handoff'`), `replan_total{origin}` (`detail.origin` dos passos `replan`), `request_duration_seconds` (histograma de `requests.duration_ms`, buckets 1, 2, 5, 10, 20, 30, 60, +Inf), `cost_usd_total{provider}`, `budget_remaining_usd` e `budget_limit_usd`.
- **`GET /metrics`:** público, porque o `/ready` é público (sem `AUTH`, sem token). `Content-Type: text/plain; version=0.0.4; charset=utf-8`.
- **`alerts/rules.yml`:** grupo `merchant-assistant` com 4 regras: `BudgetNearLimit` (`budget_remaining_usd < 0.10 * budget_limit_usd`), `ToolFailureRateHigh` (razão das `rate` em 15 min > 0,05), `HandoffRateHigh` (razão em 1 h > 0,30) e `RequestLatencyP95High` (`histogram_quantile(0.95, …[15m]) > 20`). Cada uma tem `summary`, `description` e `runbook_url: ../README.md#observability`, relativo ao arquivo.
- **README:** a seção Observability ganhou o endpoint, a tabela de métricas, as regras e o `scrape_config` local em duas linhas. A linha de próximos passos agora cita só OTLP, painéis e drift de retrieval.

### Decisões tomadas além do texto do plano (todas reversíveis)

1. **`budget_limit_usd` (gauge) a mais:** a regra "orçamento < 10% do teto" precisa do teto em PromQL. Fixar o número no YAML quebraria quando `BUDGET_LIMIT_USD` mudasse.
2. **`cost_usd_total` conta só o liquidado.** Uma reserva baixa para o valor real ao liquidar. Se o contador incluísse reservas, poderia diminuir, e o Prometheus leria isso como reset. `budget_remaining_usd` desconta liquidado + reservado, como o `BudgetGuard.remaining()` (o teste confere a igualdade).
3. **Provedor pela tabela de preços:** o ledger não tem coluna de provedor. O provedor vem de `prices.json` (`scripted*` → `scripted`; modelo sem preço → `unknown`).
4. **Rótulos de vocabulário fechado:** `tool` só aceita nome registrado em `TOOLS`; qualquer outro vira `other`, porque o modelo pode pedir um nome arbitrário e ele vai para o trace. Os demais valores só passam se casarem com `^[a-z0-9_:.\-]{1,64}$`; senão viram `other`, e valor nulo vira `unknown`. O teste confere cada rótulo contra os literais `Route` e `Status`, `TOOLS`, agentes, `rule:<nome>` e `model`, provedores e buckets.
5. **Banco ausente não é criado:** o scrape abre em `mode=ro` só se o arquivo existir; se não, devolve as famílias zeradas.
6. **Teste de coerência:** extrai os nomes das `expr` com regex, depois de remover `by (...)`, intervalos `[...]`, seletores `{...}` e chamadas de função. Confere os nomes contra as amostras de `/metrics` (o `_bucket` do histograma incluído). Um teste extra fixa o comportamento do extrator.

### Evidência

- Testes novos: **8** em `tests/integration/test_v0100_metrics.py` (formato, valores contra os traces do fluxo programado com 3 rotas, 1 falha de `get_device_status` e 1 encaminhamento, rótulos sem dado pessoal, nome livre → `other`, custo e restante, cache, coerência das regras, extrator).
- Saída real do fluxo programado: `requests_total` 1 em cada uma de `knowledge/answered`, `support/answered` e `knowledge_and_support/handoff`; `tool_failures_total{tool="get_device_status"} 1`; `handoffs_total 1`; `replan_total` com `rule:complete` 2, `rule:plan_pending` 1 e `rule:tool_failure_no_alternative` 1; histograma com `_count 3`; `cost_usd_total{provider="scripted"} 0`; `budget_remaining_usd 1`.
- Focados: `test_v0100_metrics.py` + `test_health.py` com **10 passed**; `test_messages_contract.py`, `test_v1_api.py`, `test_v060_r4.py` e `test_v070_story.py` com **38 passed**; ruff check e format limpos nos arquivos tocados.
- **Suíte estrita:** `python tools/scripts/lint_and_tests.py --strict` (`.venv`) com HEAD `2a561db`: **2132 passed, 1 skipped** em 960,31 s; ruff `All checks passed!`; caminhos pessoais: nenhuma ocorrência em 770 arquivos; estrutura e skills válidas; "Validação estrita concluída sem falhas", exit 0. Log no scratchpad da sessão (não versionado), SHA-256 `aa1e2f43…06381d7c`. **Atenção:** durante a rodada, outro escritor tinha alterações não commitadas na árvore (`cli.py`, `evaluation/calibration.py`, `evaluation/runner.py`, `llm/prompts.py`, `test_eval_campaign.py`, `test_v0100_rubric.py`, `test_judge_v4.py`), aparentemente as correções da tarefa 83, e a coleta incluiu essas alterações. Conta: 2121 + 8 desta tarefa + 3 de lá. Não toquei nesses arquivos nem os adicionei.
- Nenhuma chamada paga, `.env` não lido, nenhum servidor iniciado. Os processos de espera foram encerrados.

### Achados e limitações

- `/metrics` reflete o que está em `traces.sqlite3`. A tabela `requests` também recebe `human_reply` (resposta do operador); essas linhas aparecem em `requests_total{route="human_reply"}` e entram no denominador da regra de encaminhamento.
- `model_calls_total` conta chamadas liquidadas (`usage_by_agent`). Uma reserva que falhou antes de liquidar entra em `requests.model_calls`, mas não aqui.
- A consulta varre as tabelas inteiras a cada 5 s no máximo. Com o volume de demo, isso não pesa. Para volume real, o caminho é o cliente oficial (reversão de D4).
- Fora desta seção do README, a linha 51 (tabela de resposta ao avaliador) ainda diz que `/metrics` e as regras de alerta são próximos passos. `docs/contracts/api-v040.md` não lista a rota nova. Deixei os dois para o fechamento (tarefa 86), porque a tarefa restringe o README à seção Observability.

### Próxima ação

Reviewer, em contexto novo: revisar `023dc61..HEAD` (só os commits da tarefa 85) contra a tarefa 85. Depois, QA do momento 6 (`/metrics` ao vivo depois dos momentos 4 e 5) e do momento 7. O Supervisor marca o CA-59 depois da revisão e do QA.

## Tarefa 83 — rodada 2

- **Papel e responsável:** Developer, subagente despachado pelo Supervisor (time único), 2026-11-05.
- **Objetivo:** fechar o [parecer da rodada 1](v0100-reviewer-t83.md) (P2-1, P2-2; P3-1 a P3-4) com as decisões do Supervisor.
- **Estado:** implementado; aguarda a rodada 2 da revisão.
- **Branch e base:** `codex/v0.10.0-rubrica-operacao`, base `b802c36` (parecer da rodada 1). Commits: `34d7f6a` (código e testes) e o commit desta passagem. Os commits da tarefa 85 (`29add9c`, `7638f18`, `2a561db`, `c7b06d5`) entraram na mesma branch durante a rodada, por outro Developer, sem arquivo em comum. Identidade conferida: `lauroPereira <lauro.s.pereira@gmail.com>`. Sem push.
- **Independência:** não se aplica (implementação).

### Arquivos

- `src/merchant_assistant/cli.py`: `eval --rubric` com `default=None`; o aviso "--rubric is ignored" compara com `None`; docstring de `_eval_rubric`.
- `src/merchant_assistant/evaluation/calibration.py`: `_rubric` delega a `judge.rubric_version` (mesma mensagem em português para rubrica desconhecida); linha "Base: …" na D2 quando o juiz tem mais de um bloco `judge.v3`.
- `src/merchant_assistant/evaluation/runner.py`: a linha da nota de busca web cita `judge.v<rubrica usada>` (de `config.judge_config.rubric_version`; sem juiz configurado, `RUBRIC_VERSION`).
- `src/merchant_assistant/llm/prompts.py`: `prompt_versions()` fixa `judge` na rubrica configurada.
- Testes: `tests/integration/test_v0100_rubric.py` (+1), `tests/unit/evaluation/test_judge_v4.py` (+3), `tests/integration/test_eval_campaign.py` (2 asserções a mais no teste da nota web).
- `docs/tasks/83-rubrica-judge-v4-remedicao.md`: Validação (rodada 2) e Status.

### Como cada item foi fechado

- **P2-1.** O parser do `eval` não tem mais padrão próprio. Os dois comandos resolvem por uma função só, `judge.rubric_version`: `--rubric` explícito, senão `judge.RUBRIC_VERSION` (hoje `"3"`). `calibration._rubric` virou um invólucro que só traduz a exceção. O teste novo `test_through_the_parser_…` chama `cli.main([...])` de verdade: `eval --judge-repeat` com `--rubric v4` e sem `--rubric` (grava `RUBRIC_VERSION`), `eval-calibrate` com `--judge`, `--judge-run` e `--rubric` repetidos (blocos O, A, B, C na ordem) e, com `judge.RUBRIC_VERSION` trocado para `"4"` no teste, `eval-calibrate` sem `--rubric` liga os julgamentos v4 e `eval --scripted --judge-repeat` sem `--rubric` registra `judge@4`. Isso mostra que os dois comandos seguem o mesmo padrão.
- **P2-2.** No mesmo teste, com o Opus tendo só julgamentos v3, `eval-calibrate --judge anthropic/claude-opus-5-5 --rubric v4` sem `--judge-run` é recusado ("não há julgamento do juiz … sob a rubrica judge.v4"), sem calibração gravada e sem relatório.
- **P3-1 (corrigido, mudança pequena).** `prompt_versions()` devolve, para `judge`, a versão de `judge.RUBRIC_VERSION` quando o arquivo existe, e a mais nova para os demais prompts. Com isso, `/ready`, o `prompt_set` dos snapshots e o contexto das comparações voltam a dizer `judge: "3"`, o mesmo valor da `main`. Não toquei em `comparisons.py` nem em `api/v1.py`. O reaproveitamento das comparações gravadas antes da v0.10.0 volta a valer, porque o `prompt_set` é igual ao da `main`. Quando a tarefa 86 trocar `RUBRIC_VERSION`, o `prompt_set` muda uma vez, como já acontece com qualquer prompt novo. A importação de `evaluation.judge` fica dentro da função (`evaluation` depende de `llm.prompts`, e importar no topo criaria ciclo). Continua aberta para a ADR 0022 a decisão de se o `prompt_set` do atendimento deve incluir os prompts de avaliação (o juiz não participa do atendimento, e a avaliação sob demanda usa a `judge.v2`).
- **P3-2.** Teste: o relatório com `judge_config.rubric_version` `"4"` diz "o `judge.v4` não rebaixa"; sem `judge_config`, continua "o `judge.v3`".
- **P3-3.** Fechado como efeito do P2-1: a conversão passou a existir uma vez só. Nada além disso.
- **P3-4.** Quando o juiz de um bloco v4 tem mais de um bloco v3, a linha D2 ganha uma sublinha: "Base: O (execução `legado`), o primeiro bloco `judge.v3` deste juiz; C fica fora desta linha.". Com um bloco v3 por juiz (o comando planejado do QA), o relatório não muda. `_baseline` tem um teste de unidade (original primeiro, depois o primeiro pedido, e `None` sem v3), e o teste de integração confere a sublinha com dois blocos v3 do DeepSeek (O `legado` e C, uma reexecução v3).

### Decisões tomadas além do texto do plano (reversíveis)

1. **"Configuração" é a constante `judge.RUBRIC_VERSION`.** Não criei setting nem variável de ambiente nova (`config.py` não mudou). A precedência fica `--rubric` explícito > `RUBRIC_VERSION` > v3, e hoje os dois últimos coincidem. Se a tarefa 86 quiser `JUDGE_RUBRIC` no ambiente, o lugar é `judge.rubric_version`.
2. **`--rubric v3` explícito no `eval` sem juiz agora também avisa que é ignorado** (antes só `v4` avisava). É consequência de o parser não ter padrão.
3. **Observação para a tarefa 86, sem mudar nada agora:** `calibration` usa `RUBRIC_VERSION` com dois sentidos, "rubrica padrão" e "a v3 da regra D2" (`_baseline`, os candidatos da D2, o sufixo "sob a rubrica" das mensagens). Se a 86 trocar o padrão para `"4"`, esses usos precisam ser revistos para comparar com `"3"` literal.

### Evidência

- Testes focados (`tests/unit/evaluation`, `test_v0100_rubric`, `test_calibration_flow`, `test_eval_campaign`, `test_v090_judge`, `test_v080_journeys`, `test_v0100_comparison_resume`): **329 passed**, exit 0. Os arquivos da tarefa (`test_judge_v4.py` e `test_v0100_rubric.py`) somam 12 testes (8 + 4).
- **Mutantes reaplicados** numa cópia `git archive` no scratchpad, com os arquivos da rodada por cima, `PYTHONPATH` na cópia (módulo carregado conferido) e os 12 testes da tarefa. Base: 12 passed. Todos os mutantes morreram:

| Mutante | Resultado |
| --- | --- |
| M12 `judgement_for` sem o filtro de rubrica | morto (`test_through_the_parser_…`): a recusa do Opus v4 não acontece. No mutante, a importação passa e a CLI só quebra (`TypeError`) ao imprimir o bloco com execução `None`. O teste falharia do mesmo jeito sem a quebra, porque espera `SystemExit`. Fora do mutante, esse caminho não é alcançável |
| M17 `_baseline` pega o último bloco v3 | morto (`test_the_d2_baseline_…` e a sublinha "Base: O") |
| M19 padrão do parser `"v4"` | morto (sem `--rubric` grava 4) |
| M19b padrão do parser `"v3"` fixo (a fonte duplicada da rodada 1) | morto (com `RUBRIC_VERSION` `"4"`, o `eval` ainda registraria `judge@3`) |
| M20 `eval-calibrate --judge` sem `action="append"` | morto (recusa "one --judge takes at most one --judge-run") |
| M21 `_rubric` com padrão próprio | morto (`test_the_default_rubric_has_one_source…` e o teste de integração) |

- Nenhuma chamada paga, nenhuma rede, `.env` não lido (`cli.get_settings` trocado pela fixture nos testes por `cli.main`).

### Suíte estrita

`python tools/scripts/lint_and_tests.py --strict` (venv da `.venv`) no HEAD `c7b06d5`, que inclui `34d7f6a`. Na árvore, só a Validação da tarefa 83 estava fora de commit. A suíte rodou com `PYTEST_ADDOPTS="--basetemp=<scratchpad da sessão>/suite-bt -p no:cacheprovider"` e deu **2133 passed, 1 skipped** em 1145,53 s. Ruff: `All checks passed!`. Caminhos pessoais: nenhuma ocorrência em 770 arquivos. Estrutura e skills válidas. Saída final "Validação estrita concluída sem falhas", exit 0. Log no scratchpad (não versionado), SHA-256 `af9cbd6a…`.

- **Bloqueio de ambiente na primeira tentativa (não é defeito):** passei o `--basetemp` em forma POSIX (`/c/Users/…`) dentro de `PYTEST_ADDOPTS`. O Git Bash não converte variável de ambiente, e o pytest resolveu o caminho para `C:/c/Users/…`, que não existe: 1369 passed e 765 erros de `FileNotFoundError` no `mktemp`, em 78 s. Com o caminho em forma Windows, a suíte passou (números acima).
- **Concorrência:** um `pytest` completo de outro agente (basetemp próprio) rodava ao mesmo tempo. Tentei parar a minha para esperar, mas a parada foi negada pela permissão do ambiente, e as duas rodaram juntas. Por isso o tempo foi de 19 min. As duas só leem a árvore e cada uma tem seu basetemp. Houve 1 skip, como na rodada 1. Não confirmei qual teste foi pulado (o log não traz `-rs`), mas os 12 testes da tarefa passaram nas execuções focadas e nos mutantes de base.

### Próxima ação

Reviewer, rodada 2, em contexto novo: `b802c36..HEAD` restrito aos arquivos acima, reaplicando M12, M19 e M20. Depois, QA dos momentos 1 a 3 com os comandos da rodada 1, que não mudaram.

## Tarefa 84 — rodada 2

- **Papel e responsável:** Developer, subagente despachado pelo Supervisor (time único), 2026-11-05.
- **Objetivo:** fechar o [parecer da rodada 1](v0100-reviewer-t84.md) (P2-1, P2-2, P2-3; P3-1 a P3-3) com as decisões do Supervisor (P2-1 e P2-2 bloqueantes).
- **Estado:** implementado; aguarda a rodada 2 da revisão.
- **Branch e base:** `codex/v0.10.0-rubrica-operacao`, base `5d1ea89` (parecer da rodada 1). Commits `873007c` (OpenAPI da rota), `c097f90` (registro da thread e testes), `205336b` (teste da checagem de vida antiga) e o commit desta passagem. Os commits da tarefa 85 (`ac508ca`, `bed7fe0`, `b9bb1ed`) entraram na branch durante a rodada, de outro papel, sem arquivo em comum. Identidade conferida: `lauroPereira <lauro.s.pereira@gmail.com>`. Sem push.
- **Independência:** não se aplica (implementação).

### Arquivos

- `src/merchant_assistant/comparisons.py`: `_registered`, `_release`, `_interrupt_if_orphan`; ordem de registro em `start` e `resume`; `_run` libera só a própria entrada; condição de P3-1 no laço do `resume`.
- `src/merchant_assistant/api/v1.py`: só o decorador da rota de retomada (`responses` com 404, 409, 422 e 429).
- `tests/integration/test_v0100_comparison_resume.py`: teste de reinício com custo não nulo e 9 testes novos.
- `docs/tasks/84-comparacao-retomavel.md`: Validação (rodada 2) e Status.

### Como cada item foi fechado

- **P2-1.** `_release(id, thread)` remove a entrada só se for aquela thread. `_run` chama `_release(id, threading.current_thread())` no último `finally`, depois de gravar o estado final. Assim, enquanto a linha está `running`, a thread está no registro. O `resume` recusa com `409 comparison_running` quando `_alive(id)`, qualquer que seja o estado gravado: a thread que já gravou `partial` e ainda está saindo bloqueia a retomada até sair. Não há janela em que um `GET` veja `running` sem a thread registrada. Na outra ordem, sem o registro com `running`, o `GET` marcaria `interrupted`.
- **P2-2.** Reivindicação atômica pelo registro. O `start` cria a thread e a registra antes do `INSERT` com `running` (a captura da base de conhecimento passou para antes do `INSERT`). O `resume` registra a thread dentro do `BEGIN IMMEDIATE`, depois do `UPDATE … WHERE state=<lido>` e antes do `COMMIT`. `_registered` trata uma thread registrada e ainda não iniciada (`ident is None`) como viva. A marcação de órfã (`read`, `resume`, `lifespan`) passou para `_interrupt_if_orphan`, que relê a linha e consulta o registro dentro de uma transação `BEGIN IMMEDIATE` própria. Como o `resume` registra antes de efetivar `running` e a thread sai depois de gravar o estado final, a marcação nunca intercala com uma reivindicação. Ordem dos travamentos: quem segura o `_ACTIVE_LOCK` nunca espera o SQLite (o lock só envolve leituras e escritas do dicionário). Então segurar a escrita do SQLite e pedir o `_ACTIVE_LOCK` não trava. Falhas entre o registro e o `thread.start()` liberam a entrada. Se o próprio `start()` falhar, a linha fica `running` sem thread, e a próxima leitura a marca `interrupted`.
- **P2-3.** Teste de reinício: antes do app novo, as linhas `settled` da tentativa morta passam a 0,004 e entra uma `reserved` de 0,002. `interrupted_attempts[0].cost_usd` dá esse valor, e o `cost_usd` fica igual ao anterior mais esse valor. Uma segunda leitura não muda nada, e no fim o `cost_usd` é a soma das células mais a tentativa.
- **P3-1.** Uma célula `failed` é mantida sem `retry_failed`, tenha ou não `request_id`. Uma célula com `request_id` e outro estado também é mantida (condição em uma linha, sem mudar o resto).
- **P3-2.** Testes baratos para os três: M08 (`_mark_interrupted` com a linha já `completed` devolve `False` e não altera nada), M13 e M14 (contagem demo pela tabela `api_sessions`: 4 contadas, 1 devolvida → 3; retomada de uma célula ainda não alcançada → continua 3; `retry_failed` da devolvida → 4).
- **P3-3.** A rota declara `404`, `409`, `422` e `429` com `ErrorBody`, e um teste confere o OpenAPI. A rota irmã de criação continua como estava, fora do escopo.

### Decisões tomadas além do texto do parecer (reversíveis)

1. **Registro primeiro, não marca no banco.** Das duas opções do Supervisor, escolhi o registro em `_ACTIVE` antes de `running` ficar visível. Uma marca de reivindicação no banco não diria se a thread está viva, e a vida da thread já é a fonte de verdade da marcação `interrupted`. O `AND state=?` da reivindicação continua, como segunda defesa contra dois pedidos que leram o mesmo estado. É o que o teste de dois `resume` com barreira exercita.
2. **A marcação de órfã ganhou transação própria.** O pedido de P2-1 e P2-2 não exigia isso, mas sem ela restava uma corrida estreita: uma leitura via `running` da thread antiga, a thread saía, um `resume` reivindicava, e o `UPDATE … WHERE state='running'` da leitura marcava `interrupted` a retomada nova. O teste `test_a_stale_liveness_check_…` mata o mutante que tira a consulta ao registro de dentro da transação.
3. **Teste da identidade do `pop`.** O cenário não acontece mais pela API, porque o `resume` recusa enquanto a thread antiga está registrada. O teste injeta uma thread no registro enquanto a antiga está parada e confere que ela continua lá. O mutante "pop sem identidade" também morre no teste de dois `resume`: o `_release` do pedido recusado tiraria do registro a thread do vencedor.

### Evidência

- Testes da tarefa: `test_v0100_comparison_resume.py` com **13 passed** (4 da rodada 1, um deles ampliado com custo, e 9 novos). Vizinhos `test_v060_r2`, `test_v060_api` e `test_v060_r4` verdes. Ruff check e format limpos nos arquivos tocados.
- **Código da rodada 1 contra os testes novos** (cópia com `comparisons.py` de `5d1ea89`): falham os dois testes de janela (`start` e `resume`), o da thread que sai e o de P3-1. Os demais passam, como esperado: o de dois `resume` simultâneos mira o M12, que o código antigo já cobria pelo `AND state=?`.
- **Mutantes** numa cópia da árvore no scratchpad (`PYTHONPATH` na cópia, `merchant_assistant.__file__` conferido), um por vez, com os testes da tarefa e `test_v060_r2.py`; controle verde:

| Mutante | Resultado |
| --- | --- |
| M02 custo da tentativa não somado | morto (`test_restart_…`) |
| M08 `_mark_interrupted` sem `AND state='running'` | morto (`test_marking_interrupted_never_overwrites_a_final_state`) |
| M12 reivindicação sem `AND state=?` | morto (`test_two_concurrent_resumes_claim_the_comparison_once`) |
| M13 `resume` sem recontar o limite demo | morto (`test_resume_recounts_given_back_cells_…`) |
| M14 devolução sem a marca `demo_refunded` | morto (o mesmo teste) |
| P3-1 desfeito (falha sem `request_id` volta sem `retry_failed`) | morto (`test_a_failed_recorded_cell_…`) |
| `pop` sem conferir a identidade | morto (`test_two_concurrent_resumes_…`) |
| `resume` sem recusar thread viva com estado final | morto (`test_a_leaving_thread_…`) |
| thread registrada e não iniciada tratada como morta | morto (`test_read_and_resume_while_start_is_registering_…`) |
| marcação sem consultar o registro dentro da transação | morto (`test_a_stale_liveness_check_…`, depois de `205336b`) |

- **Suíte estrita:** `python tools/scripts/lint_and_tests.py --strict` (`.venv`) no HEAD `205336b` (com os commits da tarefa 85 que estavam na branch), com `-p no:cacheprovider -rs`: **2147 passed, 1 skipped** em 1049,36 s (o skip é o de sempre, `test_v070_identity_r2.py:277`, que exige basetemp sob `.pytest_cache`); ruff `All checks passed!`; caminhos pessoais: nenhuma ocorrência em 772 arquivos; estrutura e skills válidas; "Validação estrita concluída sem falhas", exit 0. Log no scratchpad da sessão (não versionado), SHA-256 `888851ee…7bbf`. Bloqueio de ambiente, não defeito: o `--basetemp` em `PYTEST_ADDOPTS` perdeu as barras invertidas na passagem pelo Git Bash, e o pytest criou o basetemp como diretório relativo na raiz do repositório (não versionado, 175 diretórios temporários de teste). Removi esse diretório depois da suíte; nada versionado foi afetado.
- Nenhuma chamada paga, nenhuma rede, `.env` não lido, nenhum servidor iniciado.

### Limites

- O `taskkill` real continua com o QA (D6, CA-58). Os testes de concorrência usam threads reais no mesmo processo, sem vários processos.
- Com mais de um processo da API sobre o mesmo banco (vários workers), o registro é por processo: outro processo veria `running` sem thread e marcaria `interrupted`. O projeto roda um processo só. Essa premissa já existia na rodada 1 e não mudou.
- Uma retomada logo depois do fim da thread pode receber `409 comparison_running` por alguns milissegundos (a thread já gravou o estado final e ainda não saiu do registro). A recusa é segura, e o cliente repete.

### Próxima ação

Reviewer, rodada 2, em contexto novo: `5d1ea89..HEAD` restrito a `comparisons.py`, ao decorador da rota em `api/v1.py` e a `test_v0100_comparison_resume.py`, reaplicando M02, M12 e as sondas de P2-1 e P2-2. Depois, o QA da D6 com os comandos da rodada 1, que não mudaram.

## Tarefa 85 — rodada 2

- **Papel e responsável:** Developer, subagente despachado pelo Supervisor (time único), 2026-11-05.
- **Objetivo:** fechar o [parecer da rodada 1](v0100-reviewer-t85.md) (P2-1; P3-1 a P3-6) com as decisões do Supervisor.
- **Estado:** implementado; aguarda a rodada 2 da revisão.
- **Branch e base:** `codex/v0.10.0-rubrica-operacao`, base `ac508ca`. Commits `bed7fe0` (código, teste e regras), `b9bb1ed` (README) e o commit desta passagem e da tarefa. Commits da rodada 2 da tarefa 84 (`c097f90`, `205336b`) entraram no meio, por outro Developer, sem arquivo em comum. Identidade conferida: `lauroPereira <lauro.s.pereira@gmail.com>`. Sem push.
- **Independência:** não se aplica (implementação).

### Arquivos

- `src/merchant_assistant/observability/metrics.py`: conjuntos fechados `ROUTES`, `STATUSES`, `AGENTS`, `REPLAN_RULES`/`ORIGINS`, `TOOL_OUTCOMES` e `_providers()`; `_closed()` no lugar de `_label()` e da regex; `OPEN_TIMEOUT_SECONDS = 1`; leitura de cada banco protegida contra `sqlite3.Error`; `MetricsCollector` guarda a última leitura completa.
- `tests/integration/test_v0100_metrics.py`: +5 testes e `present()` (série obrigatória); vocabulário sem `unknown` em rota e status e com `origin` fechado.
- `alerts/rules.yml`: `runbook_url: https://github.com/lauroPereira/ai-getnet-case#observability` nas quatro regras.
- `README.md` (seção Observability): rótulos fechados com `other`, comportamento com banco ilegível, e a nota do P3-6.

### Como cada item foi fechado

- **P2-1:** cada rótulo sai de um conjunto fechado do código, e qualquer outro valor (inclusive nulo) vira `other`. Rota: `get_args(Route)` + `human_reply`. Status: `get_args(Status)`. Agente: `router`, `knowledge`, `web`, `support`, `customer_support`, `escalation`, `personality`, `replan`, `rerank`, `judge`, `embeddings`. Origem: `model` ou `rule:<nome>`, com os 16 nomes do replanejador (10 regras de `RULES`, mais `planner_unavailable`, `nothing_to_review` e as recusas da guarda `no_repeat`, `unknown_merchant`, `hop_budget`, `request_limits`). Ferramenta: `TOOLS`. Resultado: `ok`/`error`. Provedor: `prices.json` + `scripted` + `unknown`. Teste novo `test_identifier_shaped_values_in_the_traces_come_out_as_other`: grava pelo `TraceStore` a rota `cliente1988`, o status `req_0123456789abcdef0123`, os agentes `op_ana` e `cliente1988`, as origens `cliente1988`, `op_ana` e `rule:conv_7f3a9c`, uma ferramenta `tool:cliente1988` e a rota `op_ana`. Confere que nenhum desses textos aparece na exposição e que as séries saem como `other` com as contagens certas. Teste novo `test_closed_sets_follow_the_names_in_the_code`: os nomes de regra extraídos de `replanner.py` (`Match("…"`, `"rule:…"`, `refusal = ("…"`) são iguais a `REPLAN_RULES`, e todo `agent="…"`/`AGENT = "…"` de `src/` está em `AGENTS`. Um agente ou regra novo quebra a suíte em vez de virar `other` em silêncio.
- **P3-1:** `test_histogram_inf_bucket_counts_requests_above_the_last_bound`, com uma requisição de 61,5 s e outra rápida: `le="60"` = 1, `+Inf` = 2, `_count` = 2, `_sum` ≥ 61,5.
- **P3-2:** `present()` exige a série `cost_usd_total{provider="scripted"}` (antes, uma série ausente lia como 0).
- **P3-3:** `test_unreadable_stores_never_fail_the_scrape` cobre dois casos. Bancos vazios (sem tabela) dão famílias zeradas e `budget_remaining_usd` = teto. Com o banco travado por `BEGIN EXCLUSIVE` de outra conexão, `render` volta em menos de `OPEN_TIMEOUT_SECONDS + 3` com as famílias zeradas, e o coletor devolve a última leitura completa; destravado, conta de novo. `test_metrics_endpoint_answers_200_when_the_trace_store_is_empty`: `GET /metrics` responde 200 com um arquivo de traces vazio.
- **P3-5:** URL absoluta, e o teste de coerência compara a URL exata.
- **P3-6:** nota no README: `requests_total` e o histograma contam também as respostas do operador (`human_reply`) e as retomadas, que entram nos denominadores da taxa de encaminhamento e do p95. Sem filtro na regra (decisão do Supervisor).
- **P3-4:** só registro. `/metrics` segue público como `/ready`; em produção, restringir por rede ou token de leitura. Com o P2-1 fechado, nenhum rótulo traz id.

### Decisões tomadas além do texto do plano (reversíveis)

1. **Última leitura completa em vez de zerar sempre (P3-3).** O Supervisor aceitou as duas saídas. Zerar contadores e depois voltar ao valor real é lido como reset pelo Prometheus, e o `rate()` contaria o total inteiro como aumento, disparando falsos alertas de taxa. Por isso o coletor serve a última exposição em que os dois bancos foram lidos por inteiro e registra um aviso com a idade. Antes da primeira leitura completa, ou chamando `render()` direto, as famílias saem zeradas. Não acrescentei gauge de idade: a idade fica só no log `merchant_assistant.metrics`.
2. **`customer_support` e `embeddings` no conjunto de agentes.** São os nomes reais do código (`agents/support.py`, `mcp_server.py`, `rag/embed.py`), além dos nomes da lista do Supervisor. `web` e `support` ficam no conjunto, embora hoje nenhum código os use como nome de agente.
3. **Nulo vira `other`, não `unknown`, em rota, status, agente e origem.** `unknown` fica só para o provedor de um modelo sem preço, como na rodada 1.
4. **Nomes escritos em `metrics.py`, não importados do replanejador.** Importar `agents.replanner` puxaria o grafo para a camada de métricas. O teste de deriva cobre a divergência.

### Evidência

- Focados: `test_v0100_metrics.py` + `tests/unit/test_health.py` com **15 passed** (13 + 2). `ruff check` e `ruff format --check` limpos nos arquivos tocados.
- Mutantes manuais em `metrics.py`, com restauração conferida por `cmp`: M01 (`+Inf` = último bucket finito), M19 (`scripted` → `unknown`), rota/status sem conjunto fechado, agente sem conjunto, origem sem conjunto, `except` trocado por `KeyError` e coletor sem a última leitura. **7 de 7 mortos.**
- **Suíte estrita:** `python tools/scripts/lint_and_tests.py --strict` (`.venv`), HEAD `b9bb1ed`: **2147 passed, 1 skipped** em 1047,22 s; ruff `All checks passed!`; caminhos pessoais: nenhuma ocorrência em 772 arquivos; estrutura e skills válidas; "Validação estrita concluída sem falhas", exit 0. Log no diretório temporário do usuário (não versionado), SHA-256 `10ed5877…5c429e2`. A árvore tinha, sem commit, a alteração de `test_v0100_comparison_resume.py` da rodada 2 da tarefa 84, depois commitada como `205336b`, e a coleta a incluiu.
- Nenhuma chamada paga, `.env` não lido, nenhum servidor iniciado; o único processo em segundo plano (a suíte) terminou.

### Achados e limitações

- Apareceu na raiz um diretório não rastreado com nome de caminho de scratchpad achatado (`Users…scratchpad suite-bt/`). Parece o `--basetemp` de outro agente, sem separadores. Não é meu e não toquei nele; o Supervisor decide.
- Ainda pendentes para a tarefa 86, como na rodada 1: a linha 51 do README e `docs/contracts/api-v040.md`.

### Próxima ação

Reviewer, rodada 2, em contexto novo: `ac508ca..HEAD`, restrito a `metrics.py`, `test_v0100_metrics.py`, `rules.yml` e README (Observability), reaplicando M01, M19 e a reprodução do P2-1. Depois, QA do momento 6.
