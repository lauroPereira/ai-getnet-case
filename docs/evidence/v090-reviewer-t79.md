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
