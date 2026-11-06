# Passagens do Developer — v0.10.0

## Tarefa 83 — Rubrica `judge.v4` e remedição dos dois juízes (rodada 1)

- **Papel e responsável:** Developer, subagente despachado pelo Supervisor (time único).
- **Objetivo e critérios:** [tarefa 83](../tasks/83-rubrica-judge-v4-remedicao.md); [spec v0.10.0](../specs/rubrica-operacao-v0100.md) D1, D2, CA-57; [história](../historias/rubrica-operacao-v0100.md) momentos 1 a 3; [ADR 0021](../architecture/decisions/0021-juiz-modelo-e-regua.md).
- **Escopo:** prompt novo, código, testes, Validação e Status da tarefa 83 e esta passagem. `prompts/judge.v3.md`, rótulos, cenários, migrações, snapshots e ledger não mudaram.
- **Estado:** implementado; aguarda revisão.
- **Branch e base:** `codex/v0.10.0-rubrica-operacao`, base `ce011b5`. Commits: `1655e80` (prompt `judge.v4` e rubrica selecionável no juiz), `9e66d20` (`--rubric` nas duas CLIs, relatório multi-bloco, testes) e o commit desta passagem. Identidade conferida antes de cada commit: `lauroPereira <lauro.s.pereira@gmail.com>`. Sem push.
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
- O relatório real só existe depois do rejulgamento pago (momentos 1 e 2), que é do QA.

### Próxima ação

Reviewer, em contexto novo: revisar `ce011b5..HEAD` contra a tarefa 83. Depois o QA roda os momentos 1 a 3 com os comandos acima, e o Supervisor aplica a D2 na tarefa 86.
