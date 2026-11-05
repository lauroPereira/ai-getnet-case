# Passagem de papel: revisão independente da tarefa 79 (juiz Anthropic e experimento de calibração), v0.9.0

## Rodada 1 — candidato `c0045a5` (2026-11-05)

- **Papel e responsável:** Reviewer nativo, contexto frio; sem a passagem do Developer (`docs/evidence/v090-developer.md` não lida), sem o diagnóstico do Supervisor; tarefa lida só até "## Validação".
- **Objetivo e critérios:** spec `juiz-retrieval-v090.md` D1 a D5, D10, RF-108, CA-56; tarefa 79 (passos 1 a 7 e critérios de conclusão); história `juiz-retrieval-v090.md`, momentos 1 a 3.
- **Escopo:** `ffe9803` e `c0045a5` sobre a base `4cdb143` (16 arquivos, +1068/−48). `2ea993f`, `db88c6c` e `9f12c82` são só documentação; `src/`, `tests/`, `pyproject.toml` e `.env.example` são iguais entre `c0045a5` e o HEAD.
- **Estado:** **correções necessárias** (nenhum P1; três P2).
- **Branch e PR:** `codex/v0.9.0-juiz-retrieval`, HEAD `9f12c8231891bed2483ff679159c68f730529fb6`; sem PR.
- **Base e versão final:** base `4cdb143`, candidato `c0045a5819464698472f61d156e96d24ffafea1e`. Não há manifesto `v090-candidato-rN.json`, então o candidato foi conferido por SHA: sha256 dos 13 arquivos de código e configuração do diff gravado antes e conferido depois da revisão, sem diferença. Árvore sem alteração rastreada nos dois momentos.
- **Independência:** independente (contexto novo; não implementei nem recebi as conclusões do implementador).

### Comandos e números

| Verificação | Resultado |
| --- | --- |
| `python tools/scripts/lint_and_tests.py --strict` no HEAD (`PYTEST_ADDOPTS=--basetemp=.pytest_cache/rev-t79-<ts> -p no:cacheprovider`) | **2012 passed**, 0 skipped, 0 failed, em 1043 s; Ruff "All checks passed"; skills válidas; exit 0 |
| `checar-caminhos-pessoais.py` (dentro da suíte) | nenhuma ocorrência em 723 arquivos |
| Testes novos isolados numa cópia `git archive c0045a5` (`<scratchpad da sessão>`) | 15 passed |
| Mutação manual (15 pontos, cópia separada) | 14 mortos, 1 sobrevivente (P2-1) |
| Diff fora do escopo (`prompts`, `data`, `tests/scenarios`, `data/` do pacote, `orchestration`, `guardrails`, migrações, `.github`) | vazio |
| Mecanismo equivalente pré-existente (`git grep -i` por anthropic e claude em `4cdb143`, `src` e `tests`) | nenhum; `profiles.CATALOG` sem Anthropic (agentes não podem escolher Claude) |

### O que foi re-derivado e como

1. **API do SDK instalado (`anthropic` 2.5.0, na `.venv`).** Li o pacote. `Messages.create` aceita `output_config: OutputConfigParam` (`format: JSONOutputFormatParam{type: "json_schema", schema}`, `effort`) e `timeout`. `StopReason` inclui `refusal`, `max_tokens` e `model_context_window_exceeded`. `Usage` tem `input_tokens`, `output_tokens`, `cache_read_input_tokens` e `cache_creation_input_tokens`, os dois últimos opcionais. `transform_schema` é exportado pelo pacote. `httpx2` é dependência declarada do `anthropic`. O provedor programado (`scripted_anthropic.py`) é o cliente real do SDK sobre `httpx2.MockTransport`, e o corpo serializado confere com D3: `system`, uma mensagem de usuário, `max_tokens` 2000, `output_config.format` e nem `thinking` nem `effort`.
2. **Esquema estrito serializado de `JudgeScoreV3`:** `type: object`, `additionalProperties: false`, os nove campos em `required`, critérios `integer` e veredito `boolean`. A faixa de 1 a 5 é conferida pelo validador Pydantic.
3. **Sondas no adaptador** (`<scratchpad da sessão>/probes/probe_unit.py`, rede bloqueada):

   | Sonda | Resultado |
   | --- | --- |
   | Nota 0 ou 6; campo faltando; texto vazio só com pensamento; dois blocos de texto | `LLMError` e acerto no meter |
   | `refusal`, `max_tokens` ou `model_context_window_exceeded`, mesmo com JSON válido | `LLMError` |
   | HTTP 529 e falha de conexão | `LLMError`, `settle(None)` (fica o valor reservado) |
   | Campo extra; "4" como string; "yes" como booleano | aceitos pela coerção do Pydantic; o esquema estrito impede isso na API real (P3-4) |
   | `usage` ausente ou nulo | `AttributeError` fora do `try`, reserva **não** acertada (P3-1) |
4. **Preços** (`pricing.cost` com 1M de cada tipo):

   | Modelo | Entrada | Cache lido | Cache criado | Saída |
   | --- | --- | --- | --- | --- |
   | Opus 5.5 | 4,00 | 0,20 | 5,00 | 20,00 |
   | Sonnet 5.5 | 2,00 | 0,20 | 2,50 | 10,00 |
   | Haiku 5.5 | 0,10 | 0,01 | 0,125 | 0,50 |

   Pensamento entra em `output_tokens`, que na API é o total cobrado. Nenhum preço existente mudou (o diff de `prices.json` só acrescenta). O custo OpenAI fica igual porque `cache_creation_tokens` é 0. O campo novo de `Usage` foi acrescentado no fim, então os usos posicionais continuam válidos. A reserva por julgamento Opus (3.500 de entrada e 2.000 de saída) é de US$0,054.
5. **Independência (D4).** `JUDGE_PROVIDERS` inclui `anthropic`. `_has_key` lê `ANTHROPIC_API_KEY`. Agente `openai/gpt-6-luna` com juiz Anthropic dá `different_provider` (também no `evaluator` gravado). O padrão de `config.py` continua `deepseek/deepseek-flash`. Sem a chave, ou com modelo sem preço, a recusa vem antes de qualquer chamada (0 requisições).
6. **v0.8.0 byte a byte, sobre dados reais.** Copiei o banco do runtime de QA `.pytest_cache/qa-v080-r1/runtime/merchant.sqlite3` (sha256 `ab3fc701…e3d6`, original não tocado) para `<scratchpad da sessão>`. Rodei `import_filled` sem `--judge`, com o código de `4cdb143` numa cópia e com o de `c0045a5` noutra, mesmo `now` e rater `lauro`: os relatórios saem **idênticos byte a byte**. Contra `docs/evidence/v080-calibracao.md`, a única diferença é o parágrafo escrito à mão. A tabela `calibrations` fica igual antes e depois.
7. **Momentos 1 a 3 sobre a cópia do banco real e os artefatos versionados**, com o provedor programado e rede bloqueada (`probe_e2e.py`):

   | Passo | Resultado |
   | --- | --- |
   | Sonda (`--judge-repeat 1 --only-sample v080-calibracao-amostra.csv --limit 3`) | 3 chamadas; corpo enviado == `judge_input` gravado em `v080-all-r3.json` |
   | `--judge-repeat 3` | 72 julgamentos na ordem do CSV; relatório "Respostas julgadas: 24 de 44 gravadas, filtradas pelos 24 request_id…" |
   | Ledger Anthropic próprio | 75 lançamentos `settled`, só `claude-opus-5-5`; ledger do projeto não criado |
   | `eval-calibrate --import --judge anthropic/claude-opus-5-5 --campaign v090-juiz-opus --rater lauro` | relatório com A e B lado a lado; campanha `v080-all-r3` intacta (hash das 24 linhas igual); ligações: `v080-all-r3`→deepseek 24, `v090-juiz-opus`→anthropic 24 |

   O mesmo passou pela linha de comando real (`cli.main`, `--scripted` e `eval-calibrate` com `RUNTIME_DIR` na cópia), sem `.env` no diretório e sem chaves no ambiente.
8. **Bordas da CLI** (`probe_cli.py`):

   | Entrada | Resultado |
   | --- | --- |
   | CSV com `request_id` repetido; `request_id` inexistente; sem cabeçalho; arquivo ausente | recusa, 0 chamadas |
   | CSV em ordem inversa com `--limit 2` | ordem do CSV, 2 julgados |
   | `--limit 100` | 24 julgados |
   | `--judge` sem `--campaign`; `--campaign` igual à original; `--judge` com `--sample` | recusa |
   | `--judge anthropic/` ou `a/b/c` | recusa |
   | `--judge` com par sem julgamento (`anthropic/claude-unknown-9`) | recusa ("não há julgamento do juiz …") |

### Achados

**P1:** nenhum.

**P2 (corrigir antes do QA):**

- **P2-1. Teste do `refusal` não prende o critério "refusal nunca vira nota".**
  - Condição: `tests/unit/llm/test_anthropic_judge.py:67-74` e `tests/integration/test_v090_judge.py:157-180` usam `refusal` sempre com texto vazio.
  - Impacto: o mutante que tira `refusal` de `FAILED_STOPS` (`src/merchant_assistant/llm/anthropic_llm.py:29`) **sobrevive**. A falha continua acontecendo pelo ramo "empty text", cuja mensagem também casa `stop_reason=refusal`. Uma recusa com JSON válido no bloco de texto viraria nota sem nenhum teste falhar.
  - Reprodução: `FAILED_STOPS = {"max_tokens", "model_context_window_exceeded"}` e rodar os dois arquivos: 15 passed.
  - Correção sugerida: caso `refusal` com JSON válido de `FIXED_JUDGEMENT`, exigindo `LLMError` (o mesmo para `max_tokens` com JSON completo).
- **P2-2. O relatório de dois juízes mistura a sonda com as 3 repetições, e o teste do momento 3 não exercita essa sequência.**
  - Condição: `judge_runs` (`src/merchant_assistant/evaluation/calibration.py:652`) soma todos os julgamentos `judge.v3` do juiz sobre os request_ids, de qualquer execução. `judgement_for` (`:466`) usa o primeiro por `created_at`.
  - Impacto: na sequência real de D1 (sonda de 3 e depois 72 julgamentos no mesmo banco), a reprodução mostra para A **75 julgamentos e 81 pares**, não 72 e 72. Nas 3 primeiras amostras, a coluna A da concordância usa o julgamento da sonda, não a repetição 1 da rodada r3. Para B, os 72 julgamentos DeepSeek dessas respostas misturam a campanha original (16 respostas com 4 julgamentos) e uma rodada posterior, e 8 respostas ficam com 1 julgamento. Isso diverge de D1 e de CA-56 ("consistência … entre as repetições"; "72 (ou 24) julgamentos") e alimenta a regra D2(c). O texto "Todos os julgamentos `judge.v3` … sobre estas respostas" não diz que a sonda nem outras rodadas entram. `test_moment_3_both_judges_against_the_same_human_ratings` (`tests/integration/test_v090_judge.py:194`) roda só a r3, por isso afirma 72.
  - Reprodução: `<scratchpad da sessão>/probes/probe_e2e.py` (sonda, r3 e `--judge`) gera a linha "A `anthropic/claude-opus-5-5` | 24 | 75 | 0 | groundedness | … | 81".
  - Correção sugerida: escopar cada juiz a uma execução declarada (por exemplo, os `evaluation_id` do relatório da r3), ou pelo menos dizer no relatório, por juiz, de quais execuções vêm os julgamentos e quantos são da sonda. O teste do momento 3 deve rodar a sonda antes.
- **P2-3. O uso de tokens da chamada paga não é gravado em lugar nenhum.**
  - Condição: `_usage` (`anthropic_llm.py:45-56`) calcula entrada, saída, cache lido e cache criado, mas o registro do julgamento (`Judge.evaluate`), o relatório JSON e Markdown e o ledger (`id, at, request_id, agent, model, reserved_usd, actual_usd, status`) guardam só custo.
  - Impacto: o momento 1 da história espera "`usage` com pensamento, custo real por julgamento", e a spec ("Riscos") promete "cache lido reportado à parte". Depois da sonda paga, esses números não têm como ser recuperados.
  - Reprodução: no JSON da sonda, o único campo com "token" é `max_output_tokens`.
  - Correção sugerida: gravar `usage` (as quatro contagens) no registro do julgamento do relatório e somar no Markdown. Não precisa de migração.

**P3 (registrar):**

- **P3-1.** `anthropic_llm.py:83` chama `_usage(response)` fora do `try`. Com `usage` ausente ou nulo a reserva fica `reserved` (conservador, porque `_committed` a conta) e `BudgetMeter.cost_usd` não soma. Mesmo padrão do `OpenAILLM.parse`; a API real sempre traz `usage`.
- **P3-2.** O comando do momento 3 da história não traz `--rater`. Com o padrão `owner`, o import recusa as 24 linhas ("a campanha original v080-all-r3 não tem nota de owner"), porque as notas foram gravadas por `lauro`. A recusa é correta e segura; o QA precisa acrescentar `--rater lauro`.
- **P3-3.** `--only-sample` sem `--judge-repeat` é ignorado em silêncio (`cli.py:487-508`): o `eval` roda a campanha inteira. A ajuda diz "With --judge-repeat"; uma recusa explícita evitaria uma campanha paga por engano.
- **P3-4.** `JudgeScoreV3` aceita campo extra e coerções ("4", "yes"). Na API real o esquema estrito impede, mas um `extra="forbid"` deixaria o adaptador fechado por conta própria. Mudar o modelo foi vetado nos Riscos da spec, então isso fica só registrado.
- **P3-5.** `--campaign " V080-ALL-R3 "` passa pela trava "nome novo" (`calibration.py:1130` compara depois de `_token`, que preserva maiúsculas) e cria a campanha `V080-ALL-R3`. A campanha original não é alterada (conferido); é só um nome confuso.
- **P3-6.** `--limit 100` com 24 selecionados escreve "limitadas a 100" no relatório. É só cosmético.
- **P3-7.** Com uma campanha original ligada a mais de um juiz, `original_judge` vira "a, b" (`calibration.py:1157`), e `judge_runs` não encontra nada para esse nome. Não ocorre com `v080-all-r3`.
- **Observação, sem achado:**
  - O timeout do adaptador é 120 s, e não os 30 s do adaptador OpenAI (D3 diz "como hoje"); o comentário justifica com o pensamento adaptativo e o prazo do meter continua prevalecendo.
  - D3 diz "cache lido a US$0,20 por milhão nos modelos 5.5", e a tarefa e o briefing dão 0,01 ao Haiku; o código segue a tarefa.

### Mutações (cópia `git archive c0045a5`, testes novos e de calibração)

Mortos (14):

1. `max_tokens` fora de `FAILED_STOPS`.
2. Cache lido fora da entrada.
3. `settle` pulado no erro.
4. `thinking` enviado.
5. Cache criado precificado como entrada.
6. `anthropic` fora de `JUDGE_PROVIDERS`.
7. `_has_key` lendo a chave DeepSeek.
8. `--only-sample` na ordem do relatório.
9. `--limit` ignorado.
10. `judgement_for` ignorando o juiz.
11. Notas originais não comparadas.
12. Nome da campanha original aceito.
13. `max_tokens` 400 para Anthropic.
14. Juízes trocados no bloco de consistência.

Sobrevivente (1): `refusal` fora de `FAILED_STOPS` (P2-1).

### Critérios comprovados e não verificados

- **Comprovados (offline):**
  - Adaptador conforme D3 contra o SDK instalado.
  - Preços D3.
  - D4.
  - D5 no teste e na reprodução (nenhum lançamento Anthropic no ledger do projeto).
  - `--only-sample` e `--limit`.
  - `--judge` com as notas originais intactas.
  - v0.8.0 idêntica sem `--judge`.
  - `refusal` e `max_tokens` como falha contada.
  - Nenhum teste abre rede ou lê `.env` (fixture `settings` com `_env_file=None`; provedor sobre `MockTransport`).
  - Suíte estrita verde.
- **Não verificados:**
  - Comportamento real do Opus 5.5 (aceitação do esquema estrito com pensamento adaptativo, custo real). Fica para o QA, com chamada paga, fora deste papel.
  - O teto de US$4,00 gravado ao lado do ledger (complemento de D5): fora da tarefa 79.

- **Ação externa:** nenhuma. Nenhuma chamada paga, nenhum Docker, nenhum Git de escrita. Sondas, cópias e mutações ficaram em `<scratchpad da sessão>`.
- **Próxima ação e responsável:** Developer corrige P2-1 a P2-3 (os P3 ficam a critério). Depois, nova rodada do Reviewer sobre o novo SHA, só no que mudar. QA só depois de apto.
- **Decisão humana pendente:** nenhuma.

## Rodada 2 — candidato `216c66c` (2026-11-05)

- **Papel e responsável:** Reviewer nativo, contexto frio; sem a passagem do Developer (`docs/evidence/v090-developer.md` não lida), sem o diagnóstico do Supervisor além das decisões repassadas no pedido; tarefa lida só até "## Validação".
- **Objetivo e critérios:** fechamento de P2-1, P2-2 e P2-3 da rodada 1, nas decisões do Supervisor: nome da execução (`--name`) gravado em `evaluator.run` sem migração; `eval-calibrate --import --judge <par> --judge-run <nome>` lê o juiz A só nessa execução, e sem `--judge-run`, com mais de uma execução, é erro que as lista; juiz B pela ligação `calibrations.evaluation_id`, com os julgamentos sem nome contados como execução `legado`; tokens (entrada, cache lido, cache criado, saída) por julgamento, também em recusa ou corte, somados nos dois relatórios; P3-3 só como aviso; a concordância de A exige repetição 1 completa na execução, e num rejulgamento com o mesmo `--name` vale o julgamento completo.
- **Escopo:** `820c270` e `7d1039f` sobre a base revisada `c0045a5`, nos arquivos `llm/anthropic_llm.py`, `evaluation/judge.py`, `evaluation/runner.py`, `evaluation/calibration.py`, `cli.py` (só `eval --judge-repeat` e `eval-calibrate`), `tests/unit/llm/test_anthropic_judge.py` e `tests/integration/test_v090_judge.py`. Os commits da tarefa 80 (`5d82fd0`, `c99aa90`, `94df63c`) ficam fora, porque têm revisão própria. `4a9f263` e `216c66c` são só documentação.
- **Estado:** ver "Parecer".
- **Branch e PR:** `codex/v0.9.0-juiz-retrieval`, sem PR.
- **Base e versão final:** candidato `216c66cd32fa7cf7cb3580380cd084d65d0e0d38`. Não há `v090-candidato-rN.json`, então conferi o sha256 dos 164 arquivos rastreados de `src/`, `tests/` e `pyproject.toml` no início. Durante a revisão a branch avançou até `687895c`: `8db183a` (só `v090-reviewer-t80.md`), `60ab2c8` e `687895c` (tarefa 80, rodada 2: `rag/bm25.py`, `rag/index.py`, `.env.example` e testes de `rag`). Antes desses commits, os mesmos arquivos de `rag/` apareceram alterados e não commitados na árvore, trabalho em andamento de outro papel. Nenhum arquivo do escopo da tarefa 79 mudou entre `216c66c` e o HEAD ou a árvore (`git diff 216c66c` vazio em `llm/`, `evaluation/`, `cli.py` e nos dois arquivos de teste). Por isso as sondas, as mutações e a suíte que vale como número rodaram sobre exports `git archive 216c66c` em `<scratchpad da sessão>`, e não sobre a árvore.
- **Independência:** independente. Revisei a rodada 1 do mesmo candidato, mas não implementei nem li a passagem do Developer.

### Comandos e números

| Verificação | Resultado |
| --- | --- |
| `python tools/scripts/lint_and_tests.py --strict` num export limpo `git archive 216c66c` (`PYTHONPATH` na cópia, `-p no:cacheprovider`) | **2035 passed, 1 skipped**, 0 failed, em 811 s; Ruff "All checks passed"; skills válidas; exit 0. O pulado é `test_synthetic_v040_script_logs_in_with_passwords`, que só roda com o `--basetemp` dentro de `.pytest_cache` do projeto (ambiente da cópia; não toca a tarefa 79) |
| A mesma suíte na árvore de trabalho (`--basetemp=.pytest_cache/rev-t79r2-<ts>`), que já tinha os quatro arquivos da tarefa 80 em andamento | 2036 passed, 0 skipped, em 921 s; exit 0. Vale só como referência: a árvore não era o candidato |
| `checar-caminhos-pessoais.py` | dentro das duas suítes, "nenhuma ocorrência em 727 arquivo(s)"; de novo neste arquivo depois de escrito |
| Testes do juiz no export (`test_anthropic_judge`, `test_v090_judge`) | 22 passed (eram 15 na rodada 1) |
| Os 8 arquivos de teste usados nas mutações, sem mutação | 168 passed |
| Mutação manual (20 pontos) | 20 mortos, 0 sobreviventes |
| Sondas `probe_r2.py` (`seq`, `samename`, `rejudge`) e `probe_import.py`, com rede bloqueada e provedor programado, sobre cópias do banco de QA | detalhes abaixo |
| sha256 de `.pytest_cache/qa-v080-r1/runtime/merchant.sqlite3` antes e depois | `ab3fc701…e3d6` nas duas vezes |

### O que foi re-derivado e como

1. **P2-1, recusa com JSON válido.** Com o código lido, `parse` decide pelo `stop_reason` antes de olhar o texto (`anthropic_llm.py:92-94`). O teste novo parametrizado (`test_a_failed_stop_is_never_a_score_even_with_a_valid_judgement_in_the_text`) usa o `FIXED_JUDGEMENT` válido sob `refusal`, `max_tokens` e `model_context_window_exceeded` e casa a mensagem terminada em `stop_reason=<motivo>)`, que não é a do ramo "empty text". As mutações que tiram cada motivo de `FAILED_STOPS` (`:29`) agora **morrem** (mutações 1 a 3). No fluxo completo (sonda `rejudge` abaixo), a recusa com JSON válido virou julgamento `failed`, com `scores` nulo e veredito nulo.
2. **P2-2, sonda e r3 no mesmo banco.** Sonda própria (`probe_r2.py seq`) sobre uma cópia do banco real de QA, com o provedor programado e a rede bloqueada. A sonda roda com `--limit 3` e groundedness 1, a r3 com `--judge-repeat 3` e groundedness 2. Resultado: 75 julgamentos Opus, nas execuções `v090-juiz-opus-sonda` (3) e `v090-juiz-opus-r3` (72).

   | Comando `eval-calibrate --import … --rater lauro --judge anthropic/claude-opus-5-5 --campaign v090-juiz-opus` | Resultado |
   | --- | --- |
   | sem `--judge-run` | erro: "tem mais de uma execução sobre estas respostas: 'v090-juiz-opus-r3' (72 julgamentos), 'v090-juiz-opus-sonda' (3 julgamentos) … nada foi alterado"; 0 linhas em `calibrations` e nenhum relatório |
   | `--judge-run v090-juiz-opus-r9` (inexistente) | erro listando as duas execuções encontradas |
   | `--judge-run` sem `--judge` | erro "--judge-run is used with --judge" |
   | `--judge-run v090-juiz-opus-sonda` | erro em 21 linhas: "não há julgamento … na execução 'v090-juiz-opus-sonda' (repetição 1 completa)" |
   | `--judge-run v090-juiz-opus-r3` | rc 0; as 24 ligações da campanha nova apontam para `v090-juiz-opus-r3`, repetição 1, groundedness 2 (nenhuma para a sonda); "Julgamentos considerados": A `v090-juiz-opus-r3` 24 / 72 / 72; B `legado` 24 / 72 / 72; consistência de A com 72 pares; a nota sobre `legado` aparece |

   O mesmo caminho passou por `cli.main` (argparse real, `RUNTIME_DIR` numa cópia, sem `.env` no diretório e sem chaves no ambiente): erro sem `--judge-run`, erro com nome inexistente e rc 0 com `v090-juiz-opus-r3`. O juiz B continua somando, sob `legado`, a campanha original e uma rodada DeepSeek posterior (72 julgamentos e 96 pares: 16 respostas com 4 julgamentos e 8 com 1). Isso segue a decisão do Supervisor, e agora o relatório diz isso. O teste do momento 3 (`test_v090_judge.py`) roda sonda, r3 e uma "outra-rodada" nomeada do juiz original, e confere que B fica em `legado` com 24.
3. **P2-3, tokens.** Cada julgamento grava `usage` com as quatro contagens em `run_evaluations.result` (`judge.py:177`, `:188` e `:313-314`), inclusive na recusa e no corte cobrados. Os dois relatórios somam. O `eval` da r3 escreve "Tokens do juiz (72 julgamentos com uso registrado; total / média por julgamento): entrada 224640 / 3120.0, da qual cache lido 7200 / 100.0 e cache criado 1440 / 20.0; saída (com o pensamento) 36000 / 500.0. Custo do juiz: US$ 1.59264.", e a sonda escreve o mesmo com 3 julgamentos. O `eval-calibrate` traz a tabela "Julgamentos com tokens | Entrada | Cache lido | Cache criado | Saída", com A em 72 e B em 0 (os julgamentos DeepSeek da v0.8.0 não guardaram tokens, e o relatório diz isso). Não há migração (`data/migrations.py` sem diff), e o `config_digest` não inclui `run`.
4. **Sondas pedidas pelo Supervisor:**

   | Sonda | Resultado |
   | --- | --- |
   | `--judge-run` inexistente | recusa listando as execuções; nada gravado |
   | Dois `eval` completos com o mesmo `--name v090-juiz-opus-r3` (`probe_r2.py samename`) | os dois rodam (rc 0); o segundo **sobrescreve** `v090-juiz-opus-r3.json` e `.md`; 144 julgamentos ficam sob uma execução só; o `eval-calibrate --judge-run v090-juiz-opus-r3` aceita, a concordância usa o primeiro julgamento de repetição 1 (o da primeira rodada) e a consistência de A passa a misturar as duas rodadas (144 julgamentos, 360 pares, groundedness exata 0,4 com notas 2 e 5) → P2-4 |
   | Repetição 1 falha e rejulgamento completo com o mesmo nome (`probe_r2.py rejudge`) | na r3, a repetição 1 de S01 foi recusada com JSON válido e `usage`, a de S02 recusada sem `usage`, e a repetição 2 de S03 cortada por `max_tokens`. O `eval-calibrate --judge-run v090-juiz-opus-r3` recusa S01 e S02 ("repetição 1 completa"), o que confere com a decisão. Rejulgar só S01 e S02 (`--only-sample` com um CSV de 2 linhas, `--judge-repeat 1`, mesmo `--name`) grava 2 julgamentos completos de repetição 1 na mesma execução. O import passa e liga S01 e S02 ao julgamento **completo** do rejulgamento (state `completed`, groundedness 3); S03 fica com a sua repetição 1 original. O rejulgamento também **sobrescreveu** `v090-juiz-opus-r3.json` e `.md`, que passaram de 24 para 2 casos → P2-4. A tabela mostra A com 74 julgamentos e 3 falhos; a consistência inclui o rejulgamento como mais uma repetição da mesma resposta (P3-9) |
   | Recusa com `usage` presente | julgamento `failed`, `usage` gravado (3060 / 50 / 10 / 500), custo 0,02206, lançamento `settled` |
   | Recusa com `usage` ausente | `AttributeError: 'NoneType' object has no attribute 'input_tokens'` vira julgamento `failed`, sem `usage` e com custo 0,0; o lançamento fica `reserved` (US$0,046432), conservador. É o P3-1 da rodada 1, ainda aberto |
5. **Regressão da v0.8.0, byte a byte e sobre dados reais.** Copiei `.pytest_cache/qa-v080-r1/runtime/merchant.sqlite3` (sha256 `ab3fc701…e3d6`, igual antes e depois; o original não foi aberto para escrita) para duas pastas. Rodei `import_filled` sem `--judge` (rater `lauro`, `now` fixo) com o código de `4cdb143` (v0.8.0) numa e com o de `216c66c` na outra. Os relatórios saem **idênticos** (sha256 `f090cb79…08a2`), e `calibrations` fica igual antes e depois. Contra `docs/evidence/v080-calibracao.md`, a única diferença é o parágrafo escrito à mão. Depois da sonda, da r3 e do `--judge` no mesmo banco, o import sem `--judge` volta a dar o mesmo relatório, byte a byte.
6. **Mecanismo equivalente.** Não existe outro campo de execução em `run_evaluations` (esquema e migrações lidos; sem coluna de campanha ou execução). `comparisons.aggregates` compara `evaluator` inteiro, mas só lê avaliações do principal da API (`v1.list_evaluations`), nunca as de `cli:eval`. Então o `run` acrescentado não muda o agrupamento.

### Achados

**P1:** nenhum.

**Rodada 1, fechamento:**

- **P2-1:** fechado. O teste prende o critério, e o mutante sobrevivente da rodada 1 agora morre.
- **P2-2:** fechado. A sonda fica fora, a escolha da execução é explícita e o relatório diz de onde vem cada juiz. O teste do momento 3 roda sonda, r3 e uma rodada extra do juiz original.
- **P2-3:** fechado. Os tokens são gravados por julgamento, também na recusa e no corte, e somados nos dois relatórios.
- **P3-2:** fechado (a história traz `--rater lauro` e `--judge-run`).
- **P3-3:** fechado como aviso em stderr, conforme a decisão do Supervisor, sem teste do aviso.
- **P3-1, P3-4, P3-5, P3-6 e P3-7:** continuam como registrados (a critério). O P3-1 foi reproduzido de novo, agora com o efeito em tokens: sem `usage`, o julgamento fica sem tokens e com custo 0,0, enquanto o ledger guarda a reserva.

**P2 (corrigir antes do QA):**

- **P2-4. Reusar um `--name` em `eval --judge-repeat` sobrescreve o relatório da execução paga e funde as rodadas sem aviso.**
  - Condição: `cmd_eval_rejudge` só recusa o nome que sobrescreveria o `--answers-from` (`cli.py:646`). Com um nome já usado em `--out`, `write_report` sobrescreve `<nome>.json` e `.md` (`:688`), e `_store_judgements` grava os novos julgamentos sob a mesma execução (`:690`).
  - Impacto: no rejulgamento que o Supervisor prevê ("rejulgar IDs falhos com o mesmo `--name`"), `docs/evidence/v090-juiz-opus-r3.json` e `.md` são a evidência do momento 2: 72 julgamentos pagos, variação do juiz, custo e tokens da rodada. Ela é trocada pelo relatório dos 2 IDs rejulgados. Os julgamentos continuam no banco e o `eval-calibrate` recalcula consistência, custo e tokens, mas o relatório da r3 se perde se o QA não tiver copiado antes. Uma segunda rodada completa com o mesmo nome também é aceita sem aviso: a consistência de A, que alimenta D2(c), passa a misturar duas rodadas (144 julgamentos), e só o número na tabela "Julgamentos considerados" denuncia isso.
  - Reprodução: `probe_r2.py rejudge` ("r3 report overwritten by the rejudge: True cases now: 2") e `probe_r2.py samename` ("report overwritten: True", "opus judgements: 144 runs: ['v090-juiz-opus-r3']").
  - Correção sugerida, a escolher pelo Supervisor:
    - (a) recusar `--name` cujo relatório já existe em `--out`, ou que já tem julgamentos no banco, salvo uma opção explícita de acréscimo; nesse caso o relatório do acréscimo vai para um arquivo próprio (por exemplo `<nome>-rejulgamento`), e os julgamentos ficam na mesma execução;
    - (b) decisão operacional registrada para o QA (rejulgamento com `--out` separado e nunca repetir uma rodada completa com o mesmo nome), rebaixando este achado para P3.

**P3 (registrar):**

- **P3-8.** `legado` é o nome reservado das execuções sem nome (`calibration.py:458`, `:466`), mas `eval --name legado` é aceito, e os julgamentos dessa execução se fundem com os da v0.8.0 na leitura. É improvável; uma recusa do nome no `eval` fecharia o caso.
- **P3-9.** Depois de um rejulgamento com o mesmo nome, a consistência de A conta o julgamento novo como mais uma repetição da mesma resposta, e os julgamentos falhos continuam em "Falhos" (na sonda: 74 julgamentos, 3 falhos, 70 pares). Os números são verdadeiros, mas o relatório não diz que houve rejulgamento. Se acontecer na rodada real, o QA registra isso no relatório do experimento.

### Mutações (cópia `git archive 216c66c`, 8 arquivos de teste do juiz e da calibração)

Os arquivos de teste foram `test_anthropic_judge`, `test_v090_judge`, `test_calibration`, `test_calibration_flow`, `test_judge_v3`, `test_eval_campaign`, `test_aggregate` e `test_v080_story`. Sem mutação, os 8 arquivos dão 168 passed. Morreram os 20 mutantes:

1. `refusal` fora de `FAILED_STOPS`. Era o sobrevivente da rodada 1.
2. `max_tokens` fora de `FAILED_STOPS`.
3. `model_context_window_exceeded` fora de `FAILED_STOPS`.
4. `_error` sem `usage`.
5. Julgamento falho sem tokens.
6. Cache lido e cache criado trocados em `tokens`.
7. `usage` fora de `result`.
8. `run` fora de `evaluator`.
9. `persist_judgements` sem `run`.
10. `summarize` sem `judge_usage`.
11. `judgement_for` ignorando a execução.
12. `judgement_for` aceitando julgamento falho: morto por `test_only_the_first_completed_judgement_of_the_campaign_is_the_one_compared`, da v0.8.0, que prende a escolha do julgamento completo pedida na decisão adicional.
13. `choose_run` sem erro com duas execuções.
14. `choose_run` aceitando execução inexistente.
15. Juiz A sem filtro de execução.
16. Juiz B sem filtro de execução.
17. `_run_name` sempre `legado`.
18. `judge_runs` sem tokens.
19. CLI gravando sem o nome da execução.
20. CLI sem repassar `--judge-run`.

Lacuna sem mutante: os testes chamam `cmd_eval_calibrate` com `Namespace`, e não pelo argparse. O registro de `--judge-run` em `main` foi conferido à mão por `cli.main`. Se faltasse, o argparse recusaria a opção, sem efeito silencioso.

### Critérios comprovados e não verificados

- **Comprovados (offline):**
  - P2-1, P2-2 e P2-3 fechados (acima).
  - Decisões do Supervisor: nome da execução sem migração; `--judge-run` obrigatório com mais de uma execução; B por ligação e `legado`; tokens nos dois relatórios; aviso do P3-3; repetição 1 completa, com o julgamento completo escolhido depois do rejulgamento.
  - v0.8.0 idêntica byte a byte sem `--judge`, antes e depois dos julgamentos Opus no mesmo banco.
  - Nenhum teste abre rede ou lê `.env` (provedor programado sobre `MockTransport` e `settings` com `_env_file=None`).
  - Banco de QA intacto.
- **Não verificados:**
  - O comportamento real do Opus 5.5 e o `usage` real (sonda paga do QA).
  - O teto de US$4,00 gravado ao lado do ledger (fora da tarefa 79).

### Parecer

**Correções necessárias**, só pelo P2-4. Os três P2 da rodada 1 estão fechados e comprovados por execução e por mutação (20 de 20 mortos). As decisões do Supervisor estão implementadas como pedido, e a v0.8.0 continua idêntica byte a byte. Nenhum P1.

O P2-4 não é defeito do cálculo, que escolhe o julgamento certo. É risco de perder a evidência paga da r3 e de misturar rodadas sem aviso, justamente no fluxo de rejulgamento que o Supervisor previu.

Se o Supervisor preferir a alternativa operacional (b) do P2-4, que é registrar para o QA "rejulgamento com `--out` separado e nunca repetir uma rodada completa com o mesmo `--name`", o achado vira P3. Nesse caso o candidato `216c66c` fica **apto para QA** sem nova rodada de código.

- **Ação externa:** nenhuma. Nenhuma chamada paga, nenhum Docker, nenhum Git de escrita no repositório (o `git init` foi só na cópia descartável em `<scratchpad da sessão>`, para o verificador de caminhos). O banco de QA foi só copiado. Este arquivo é o único escrito no repositório e não foi commitado.
- **Próxima ação e responsável:** o Supervisor escolhe entre (a) e (b) do P2-4. Com (a), o Developer corrige e o Reviewer revisa só o `eval --judge-repeat` e o teste novo. Com (b), a instrução vai para a passagem do QA e o QA dos momentos 1 a 3 pode começar.
- **Decisão humana pendente:** nenhuma; a escolha do P2-4 cabe ao Supervisor.
