# Passagens do Developer — v0.9.0

## Tarefa 79 — Juiz Anthropic e experimento de calibração (rodada 1)

- **Papel e responsável:** Developer, subagente despachado pelo Supervisor (time único).
- **Objetivo e critérios:** [tarefa 79](../tasks/79-juiz-anthropic-opus-calibracao.md); [spec v0.9.0](../specs/juiz-retrieval-v090.md) D1 a D5, D10, RF-108, CA-56; [história](../historias/juiz-retrieval-v090.md) momentos 1 a 3.
- **Escopo:** código, testes, `pyproject.toml`, `.env.example`, Validação e Status da tarefa 79 e esta passagem. Nenhum prompt, rótulo, cenário, migração, snapshot ou ledger mudou.
- **Estado:** implementado; aguarda revisão.
- **Branch e base:** `codex/v0.9.0-juiz-retrieval`, base `4cdb143` (mais `2ea993f`, commit do Supervisor com o cap de US$4,00, que chegou durante o trabalho e só toca a spec). Commits: `ffe9803` (adaptador, preços, juiz), `c0045a5` (CLI e calibração) e o commit desta passagem. Identidade conferida antes de cada commit: `lauroPereira <lauro.s.pereira@gmail.com>`. Sem push.
- **Independência:** não se aplica (implementação).

### Arquivos

- Novos: `src/merchant_assistant/llm/anthropic_llm.py` (`AnthropicLLM`: só `parse`), `src/merchant_assistant/llm/scripted_anthropic.py` (provedor programado), `tests/unit/llm/test_anthropic_judge.py` (10 testes), `tests/integration/test_v090_judge.py` (5 testes, momentos 1 a 3).
- Alterados: `llm/base.py` (`Usage.cache_creation_tokens`, último campo, padrão 0), `llm/pricing.py` (cache criado precificado à parte; `cache_creation_price`), `llm/prices.json` (Opus, Sonnet e Haiku 5.5, fonte Anthropic), `config.py` (`anthropic_api_key`, por acréscimo), `main.py` (`anthropic_client`, ramo `anthropic` em `model_factory`), `evaluation/judge.py` (`JUDGE_PROVIDERS`, `_has_key`, `max_output_tokens` por provedor), `evaluation/runner.py` (linha "Respostas julgadas" no relatório), `evaluation/calibration.py` (`sample_request_ids`, `judgement_for(judge=)`, `original_pairs`, `judge_runs`, `render_comparison`, `import_filled(judge=)`), `cli.py` (`--only-sample`, `--limit` no `--judge-repeat`, `--judge` no `eval-calibrate`), `pyproject.toml` (`anthropic>=2.5`), `.env.example` (`ANTHROPIC_API_KEY=` e o par Claude comentado no bloco do juiz).

### SDK conferido no pacote instalado

`anthropic 2.5.0` instalado na `.venv` (`uv pip install`). Lido em `anthropic/resources/messages/messages.py` e `anthropic/types/`: `Messages.create` aceita `output_config: OutputConfigParam` com `format: JSONOutputFormatParam` (`{"type": "json_schema", "schema": {...}}`) e `effort`; `thinking` é parâmetro próprio; `StopReason` inclui `refusal`, `max_tokens` e `model_context_window_exceeded`; `Usage` traz `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` (o `input_tokens` da Anthropic **exclui** as duas partes de cache). `JSONOutputFormatParam` **não tem campo `strict`**: o esquema estrito vem de `anthropic.transform_schema` (exportado pelo pacote), que põe `additionalProperties: false` e mantém todos os campos em `required`; é o que o adaptador usa. O teste confere o corpo enviado.

### Evidência

- Testes novos: **15 passed** (`tests/unit/llm`, `tests/integration/test_v090_judge.py`). Suítes afetadas antes dos testes novos (`test_eval_campaign`, `test_calibration_flow`, `tests/unit/evaluation`, `test_budget_and_router`, `test_evaluator_settings`): todas verdes.
- `python tools/scripts/lint_and_tests.py --strict`: 2012 passed, exit 0 (detalhe em "Suíte estrita").
- `python -I tools/scripts/checar-caminhos-pessoais.py`: nenhuma ocorrência em 718 arquivos.
- Provedor programado: o cliente real do SDK (`anthropic.Anthropic`) sobre `httpx2.MockTransport`; a requisição passa pela serialização do SDK e a resposta pelo parser do SDK. Nenhum teste abre rede; nenhuma chamada paga; `.env` não lido.
- Cobertura dos critérios de conclusão (programada): `eval --judge-repeat 3 --only-sample` grava 72 julgamentos `anthropic` na ordem do CSV e o relatório com a variação do juiz; `--limit 3` grava 3; ledger Anthropic recebe 75 lançamentos `settled` e o do projeto nenhum `claude%`; `refusal` e `max_tokens` viram `failed` (`scores` e veredito nulos) e o relatório diz "2 julgamentos falharam"; `eval-calibrate --import --judge anthropic/claude-opus-5-5 --campaign v090-juiz-opus` gera o relatório com os dois juízes; sem `--judge`, o relatório gerado depois de existirem julgamentos Claude é **idêntico** ao gerado antes (mesmo `now`).

### Suíte estrita

`python tools/scripts/lint_and_tests.py --strict` (venv 3.13.3) no HEAD `c0045a5`, com `PYTEST_ADDOPTS="--basetemp=.pytest_cache/t79-suite-basetemp -p no:cacheprovider"`: **2012 passed** em 1262,80 s (1997 da linha de base da v0.8.0 + 15 novos, sem skip), ruff `All checks passed!`, caminhos pessoais limpos (722 arquivos), skills válidas, exit 0, 1310 s no total. Log em `.pytest_cache/t79-suite.log`, SHA-256 `a24943ee…f875`. Uma primeira execução com o diretório temporário padrão foi interrompida por mim a 17% por lentidão (máquina carregada por outros processos); não houve falha nela até ali.

### Decisões tomadas além do texto do plano (todas reversíveis)

1. **`max_tokens` 2000 só para o juiz Anthropic.** D1 pede 2000 com pensamento adaptativo; o juiz usava 400 para todos. `MAX_OUTPUT_TOKENS_BY_PROVIDER = {"anthropic": 2000}`; DeepSeek e OpenAI continuam com 400. A reserva por julgamento no Opus fica em cerca de US$0,05 (3.500 tokens estimados × 4 + 2.000 × 20, por milhão). `Judge.config()["parameters"]` para Anthropic é `{"max_output_tokens": 2000, "effort": "default", "thinking": "default"}` (não diz `effort: none`, que seria falso).
2. **Timeout de 120 s no adaptador Anthropic** (o OpenAI usa 30 s, pensado para os agentes). Com pensamento e 2.000 tokens de saída, 30 s cortaria julgamentos e cada corte custaria a reserva inteira. Um prazo de requisição no `Meter`, quando existe, continua prevalecendo; o rejulgamento não tem prazo. Reverter: `CALL_TIMEOUT_S` em `anthropic_llm.py`.
3. **`--judge` exige `--campaign` novo.** Importar sob a campanha do CSV (`v080-all-r3`) trocaria o `evaluation_id` das notas da v0.8.0 pelo do Opus. Com `--judge`, campanha igual à do arquivo ou ausente é erro. As notas do arquivo são conferidas linha a linha contra `calibrations` da campanha original (pedido, quatro notas e veredito); faltar ou divergir é erro e nada é gravado.
4. **Juiz "original" do relatório** = o julgamento ao qual cada nota foi ligada quando a campanha original foi importada (`calibrations.evaluation_id`), não "o DeepSeek" por nome. No runtime do QA isso é o `deepseek/deepseek-flash`.
5. **Consistência e custo por juiz** contam todos os julgamentos `judge.v3` daquele juiz sobre os 24 pedidos (inclui a sonda: 3 pedidos terão 4 julgamentos do Opus se a sonda e as 72 rodarem no mesmo banco). Sem pares, o relatório mostra `-`.
6. **Seção extra no relatório:** tabela das respostas que o humano ou algum juiz marcou como afirmação sem suporte (humano, A, B por amostra), que é o que D2(b) lê (S01, S13, S16, S21).
7. **`--limit` no `--judge-repeat`:** o `--limit` existente era ignorado nesse caminho; agora corta as respostas depois do `--only-sample`. Sem `--only-sample` também vale.
8. **Arquivo `anthropic_llm.py`** (como na tarefa), não `anthropic.py` (como na tabela da spec), para não sombrear o pacote `anthropic` na leitura.

### Achados e limitações

- **Cap da campanha `v090-juiz-opus` (D5) não virou opção da CLI.** `eval --campaign` só aceita `v080-qa`, e o `FixedBudgetGuard` limita caps a US$0,50 (US$1,40 só para `v080-qa`); um cap de US$4,00 exige mexer nas guardas de orçamento, fora dos passos da tarefa. Caminho que já funciona sem código: o ledger Anthropic é novo e exclusivo, então rodar a primeira vez com `BUDGET_RUNTIME_DIR=data/runtime/anthropic BUDGET_LIMIT_USD=4.00` grava o teto de US$4,00 no `budget.sqlite3.limit` ao lado do ledger, e nenhuma execução posterior pode subir esse valor (é o mesmo mecanismo do teto primário). Os relatórios ganham o nome da campanha por `--name` (por exemplo `v090-juiz-opus-sonda` e `v090-juiz-opus-r3`). **Decisão do Supervisor:** aceitar esse arranjo ou abrir correção para um cap nomeado.
- `RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime` com `BUDGET_RUNTIME_DIR` vazio é recusado pela CLI (regra da v0.8.0); o QA precisa dos dois.
- Comando da sonda, para o roteiro do QA: `eval --judge-repeat 1 --answers-from docs/evidence/v080-all-r3.json --only-sample docs/evidence/v080-calibracao-amostra.csv --limit 3 --name v090-juiz-opus-sonda`, com `JUDGE_PROVIDER=anthropic JUDGE_MODEL=claude-opus-5-5`.
- O comportamento real do Opus (aceitar o esquema estrito do `JudgeScoreV3`, recusas, consumo de pensamento) só a sonda mostra; o teste prova o corpo enviado e o tratamento das respostas, não a API.
- `model_factory` também atende perfis e o avaliador `/v1`; nenhum deles lista modelos Claude no catálogo, então nada muda para eles.

### Próxima ação

Revisor: revisar `ffe9803` e `c0045a5`. Supervisor: decidir o cap (achado 1) antes da sonda do QA.

## Tarefa 79 — rodada 2 (correções da revisão)

- **Papel e responsável:** Developer, subagente despachado pelo Supervisor (time único), rodada de correção da mesma tarefa.
- **Objetivo e critérios:** fechar P2-1, P2-2 e P2-3 do [parecer da rodada 1](v090-reviewer-t79.md) com as decisões do Supervisor; P3 registrados (P3-3 implementado por ser trivial).
- **Escopo:** `llm/anthropic_llm.py`, `evaluation/judge.py`, `evaluation/runner.py`, `evaluation/calibration.py`, `cli.py` (só os blocos de `eval`/`--judge-repeat` e `eval-calibrate`), `tests/unit/llm/test_anthropic_judge.py`, `tests/integration/test_v090_judge.py`, Validação e Status da tarefa 79 e esta seção. Nenhum prompt, rótulo, cenário, migração, snapshot ou ledger mudou; nenhum arquivo da tarefa 80 tocado.
- **Estado:** corrigido; aguarda nova rodada do Reviewer.
- **Branch e base:** `codex/v0.9.0-juiz-retrieval`, base da rodada `fee7a78`. Durante o trabalho chegaram `5d82fd0` e `c99aa90` (tarefa 80; o `cli.py` deles só no bloco de `eval-retrieval`, conferido que não levaram nenhum trecho meu). Commits desta rodada: `820c270` (juiz: paradas falhas, tokens e nome da execução), `7d1039f` (calibração e CLI: `--judge-run`) e o commit desta passagem. Identidade conferida antes de cada commit: `lauroPereira <lauro.s.pereira@gmail.com>`. Commits só com os meus arquivos, adicionados por nome. Sem push.
- **Independência:** não se aplica (implementação).

### Como cada P2 foi fechado

- **P2-1 (recusa nunca vira nota).** Testes novos com o julgamento válido de `FIXED_JUDGEMENT` no bloco de texto: no adaptador, parametrizado em `refusal`, `max_tokens` e `model_context_window_exceeded` (strings literais, não lidas de `FAILED_STOPS`, para a mutação não encolher o teste), exigindo `LLMError` que termina em `stop_reason=<motivo>)`, ou seja, o ramo da parada e não o de texto vazio; em `Judge.evaluate` (`refusal` e `max_tokens` com corpo válido viram `failed`, sem nota nem veredito); e no fluxo da CLI (`test_a_refusal_or_a_cut_judgement_is_counted_as_a_failure` agora manda corpo válido nas duas falhas). Mutações numa cópia (`<scratchpad da sessão>`): os três mutantes (um motivo fora por vez) morrem; o sobrevivente da rodada 1 (`refusal` fora) agora derruba o teste do adaptador e o da CLI.
- **P2-2 (sonda misturada às repetições).**
  - Gravação: `save_evaluation(..., run=)` e `persist_judgements(..., run=)` põem o nome da execução em `evaluator.run` (JSON, sem migração; `config_digest` não muda). O `eval` passa o nome do relatório (`--name`, ou o padrão `avaliacao`, `avaliacao-juiz…`), no caminho normal com `--judge` e no `--judge-repeat`; a CLI imprime `judgements stored in run_evaluations: N (execution <nome>)`.
  - Leitura: `eval-calibrate --import --judge <par> --judge-run <nome>`. O juiz A é lido só nessa execução: a concordância usa a repetição 1 completa da execução (`judgement_for(..., run=)`), e a consistência, o custo e os tokens usam só os julgamentos dela (`judge_runs(..., runs=[nome])`). Sem `--judge-run`, se o juiz tiver mais de uma execução sobre os pedidos do arquivo, é erro antes de gravar, com a lista (`'v090-juiz-opus-r3' (72 julgamentos), 'v090-juiz-opus-sonda' (3 julgamentos)`); com uma só, ela é usada. `--judge-run` inexistente é erro com as execuções encontradas; `--judge-run` sem `--judge` é erro.
  - Juiz B: a concordância continua pela ligação `calibrations.evaluation_id`; a consistência, o custo e os tokens usam os julgamentos de B nas execuções desses `evaluation_id` (os gravados sem `run` formam a execução `legado`). Uma rodada posterior do mesmo juiz com outro nome fica de fora (testado com uma rodada `outra-rodada` do juiz original).
  - Relatório: nova seção "Julgamentos considerados" (juiz, execuções, julgamentos na concordância, na consistência e no custo e tokens) e a nota sobre `legado` quando aparece; o texto da consistência diz que só entram as execuções da tabela; a linha da CLI diz a execução de cada juiz.
  - Teste do momento 3: roda a sonda (3) e depois a r3 (72, com outra nota de fundamentação para provar que a concordância lê a r3), recusa sem `--judge-run`, recusa com execução inexistente e confere `| A … | \`v090-juiz-opus-r3\` | 24 | 72 | 72 |`, `| B … | \`legado\` | 24 | 24 | 24 |`, a consistência com 72 pares e o custo de 72 julgamentos.
- **P2-3 (tokens não gravados).** `Judge.evaluate` grava `usage` = `{input_tokens, cache_read_tokens, cache_creation_tokens, output_tokens}` no registro (vai para o JSON do relatório e para `run_evaluations.result.usage`; a falha sem uso conhecido, como erro de rede, fica sem a chave). Uma recusa ou um corte cobrados guardam os tokens: o adaptador Anthropic anexa o `Usage` ao `LLMError` (`error.usage`). `summary.judge_usage` traz total e média por julgamento; o Markdown do `eval` ganha a linha "Tokens do juiz (N julgamentos com uso registrado; total / média por julgamento): entrada …, da qual cache lido … e cache criado …; saída (com o pensamento) …. Custo do juiz: US$ …". O relatório dos dois juízes ganha a tabela de tokens por juiz (total / média) abaixo do custo. Julgamentos gravados antes desta rodada não têm tokens e aparecem com `0 | - | …`.

### P3

- **P3-1** (`_usage` fora do `try`): registrado, sem mudança.
- **P3-2** (`--rater`): o momento 3 usa `--rater lauro` (roteiro abaixo); o Supervisor ajusta a história.
- **P3-3** (`--only-sample` sem `--judge-repeat`): aviso em stderr, como decidido; a campanha ainda roda. Uma recusa seria uma linha, se o Supervisor preferir. Sem teste dedicado (o caminho roda o agente inteiro).
- **P3-4** (`extra="forbid"`), **P3-5** (maiúsculas no nome da campanha), **P3-6** ("limitadas a 100"): registrados, sem mudança.
- **P3-7** (juiz original "a, b"): sem mudança no nome; os blocos do relatório passaram a ser indexados por `A`/`B`, então `--judge` igual ao juiz original não sobrescreve mais um bloco com o outro.

### Decisões tomadas além do texto (reversíveis)

1. **Nome da execução = nome do relatório.** Repetir o mesmo `--name` junta as execuções numa só; o roteiro usa nomes distintos. Um `--name legado` se confundiria com a execução sem nome.
2. **Tokens em `result`, nome em `evaluator`.** O nome identifica quem e quando julgou (vai com o avaliador, como decidido); os tokens são do julgamento. A entrada é a total (como em `Usage`), da qual cache lido e criado são partes; o relatório diz isso.
3. **A concordância do juiz A exige a repetição 1 completa na execução escolhida.** Se a repetição 1 de uma resposta falhar (recusa) na r3, o import recusa aquela linha com a execução no texto; não há recuo para a repetição 2 nem para outra execução. Se isso acontecer no QA, o Supervisor decide entre aceitar o recuo para a repetição seguinte da mesma execução (mudança pequena) ou rejulgar.
4. **Fixture do teste com `created_at` fixo para a campanha original.** Ao pôr a sonda no momento 3 apareceu uma intermitência: `created_at` tem resolução de segundo, e o caminho da v0.8.0 sem `--judge` (`judgement_for` sem juiz, ordenado por `created_at, evaluation_id`) podia escolher o julgamento da sonda quando ela caía no mesmo segundo da campanha original. No banco real a campanha da v0.8.0 é de outro dia; o código da v0.8.0 não mudou. O fixture grava a campanha original em `2026-11-04T12:00:00+00:00`.

### Roteiro do QA (comandos, com `JUDGE_PROVIDER=anthropic JUDGE_MODEL=claude-opus-5-5`, `BUDGET_RUNTIME_DIR=data/runtime/anthropic`, `BUDGET_LIMIT_USD=4.00`, `RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime`)

1. Sonda: `eval --judge-repeat 1 --answers-from docs/evidence/v080-all-r3.json --only-sample docs/evidence/v080-calibracao-amostra.csv --limit 3 --name v090-juiz-opus-sonda`. Os tokens de cada julgamento saem no relatório e no JSON.
2. Repetições: `eval --judge-repeat 3 --answers-from docs/evidence/v080-all-r3.json --only-sample docs/evidence/v080-calibracao-amostra.csv --name v090-juiz-opus-r3` (ou `--judge-repeat 1 --name v090-juiz-opus-r1`, pela projeção).
3. Comparação: `eval-calibrate --import docs/evidence/v080-calibracao-amostra.csv --judge anthropic/claude-opus-5-5 --judge-run v090-juiz-opus-r3 --campaign v090-juiz-opus --rater lauro --out docs/evidence/v090-juiz-opus.md`. Sem `--judge-run`, o comando recusa e lista as duas execuções. B (`deepseek/deepseek-flash`) sai como `legado`, que no runtime de QA soma todas as rodadas DeepSeek da v0.8.0 sobre esses pedidos (o achado do Reviewer sobre B: 16 respostas com 4 julgamentos e 8 com 1); a tabela "Julgamentos considerados" mostra o número.

### Evidência

- Testes da tarefa: 22 passed (`tests/unit/llm/test_anthropic_judge.py`, 17, sendo 7 novos; `tests/integration/test_v090_judge.py`, 5, com o momento 3 e o de falhas reescritos).
- Suítes focadas (`tests/unit/evaluation tests/unit/llm tests/integration/test_v090_judge.py tests/integration/test_calibration_flow.py tests/integration/test_eval_campaign.py tests/integration/test_evaluator_settings.py tests/integration/test_v080_story.py`): 1011 passed, nenhuma falha.
- Mutações (cópia do código em `<scratchpad da sessão>`, testes da tarefa): 11 de 11 mortos, com a linha de base verde (22 passed): `refusal`, `max_tokens` e `model_context_window_exceeded` fora de `FAILED_STOPS` (um por vez); `judgement_for` ignorando a execução; `judge_runs` ignorando as execuções; sem o erro de ambiguidade; tokens não gravados em `result`; `run` não gravado em `evaluator`; falha cobrada sem tokens; `--judge-repeat` gravando sem nome de execução; relatório do `eval` sem a linha de tokens.
- `lint_and_tests.py --strict` no HEAD `94df63c` (meus commits mais os da tarefa 80), com `PYTEST_ADDOPTS="--basetemp=.pytest_cache/t79r2-suite -p no:cacheprovider"`: **2036 passed** em 1069 s, ruff `All checks passed!`, caminhos pessoais limpos (727 arquivos), skills válidas, exit 0. Log em `.pytest_cache/t79r2-suite.log`, SHA-256 `f98f8d35…56cc`.
- `ruff check` sem achados nos arquivos alterados. Nenhuma chamada paga, nenhuma rede (provedor programado sobre `MockTransport`), `.env` não lido.

### Próxima ação

Reviewer: nova rodada sobre `820c270` e `7d1039f` (só o que mudou). Supervisor: a história já recebeu `--judge-run` e `--rater lauro` em `4a9f263`; decidir o item 3 das decisões se aparecer no QA.

## Tarefa 80 — Retrieval híbrido BM25 + RRF (rodada 1)

- **Papel e responsável:** Developer, subagente despachado pelo Supervisor (time único).
- **Objetivo e critérios:** [tarefa 80](../tasks/80-retrieval-hibrido-bm25-rrf.md); [spec v0.9.0](../specs/juiz-retrieval-v090.md) D7, D10, CA-52 (parte programada); [história](../historias/juiz-retrieval-v090.md) momentos 4 e 7; plano, decisões técnicas 17 a 19.
- **Escopo:** código do `rag/`, ligação do modo (`config.py`, `main.py`, `testing.py`, `rag/kb.py`), `eval-retrieval --mode` (`cli.py`, `evaluation/retrieval.py`), `pyproject.toml`, 5 perguntas novas em `tests/scenarios/retrieval.jsonl`, testes, Validação e Status da tarefa 80 e esta passagem. Nenhum prompt, rótulo existente, migração, snapshot ou ledger mudou; o agente Knowledge não mudou.
- **Estado:** implementado; aguarda revisão.
- **Branch e base:** `codex/v0.9.0-juiz-retrieval`, base `fee7a78`. Commits: `5d82fd0` (BM25, RRF, modo), `c99aa90` (`eval-retrieval --mode` e perguntas de termo exato) e o commit desta passagem. Depois deles entraram `820c270` e `7d1039f` (rodada 2 da tarefa 79, outro escritor). Identidade conferida: `lauroPereira <lauro.s.pereira@gmail.com>`. Sem push.
- **Independência:** não se aplica (implementação).

### Arquivos

- Novos: `src/merchant_assistant/rag/bm25.py` (tokenização, `corpus_hash`, `Bm25Index`, `load_or_build`), `tests/unit/rag/test_bm25_hybrid.py` (15 testes), `tests/integration/test_v090_hybrid.py` (2 testes).
- Alterados: `rag/index.py` (`Hit.origin`, `rrf`, `KnowledgeIndex(mode=, bm25_dir=)`, `bm25_index()`, `search(mode=None)` com o denso antigo em `_dense`, manifesto com `bm25_corpus_hash` e `retrieval_modes`), `rag/kb.py` (`capture_active` mantém `mode` e `bm25_dir`), `config.py` (`retrieval_mode`, por acréscimo), `main.py` (passa `RETRIEVAL_MODE` e `<runtime>` ao índice), `testing.py` (passa `RETRIEVAL_MODE`), `evaluation/retrieval.py` (`evaluate(mode=)`), `cli.py` (bloco `eval-retrieval`: `--mode`, saída com `mode` e `bm25_corpus_hash`), `pyproject.toml` (`rank-bm25>=0.2.2`), `tests/scenarios/retrieval.jsonl` (+5 `EXACT-TERM`).

### Evidência

- `rank-bm25 0.2.2` instalado na `.venv` com `uv pip install` (depende só de `numpy`, já presente).
- Testes novos: **17** (15 + 2), verdes. Testes focados antes da suíte (`tests/unit/rag`, `test_v090_hybrid.py`, `test_cli_index_guard.py`, `test_t74_product_corrections.py`, `test_v060_doc_effect.py`, `test_kb_safety.py`): todos verdes.
- Equivalência do denso: `search(q)` e `search(q, mode="dense")` comparados com a busca da v0.8.0 reproduzida no teste (uma consulta Qdrant, `Hit(score, payload)`), nas 19 perguntas e em três combinações de `k`, `source_kinds` e `min_score`: mesma ordem, mesmos payloads, `origin="dense"`, scores iguais com `approx(rel=1e-6)`. O `approx` é necessário porque o Qdrant em memória devolve scores diferentes no último dígito em duas consultas idênticas (observado: `0.3881427196…` e `0.3881427599…` para a mesma pergunta, no caminho denso puro).
- Referência com embeddings de hash (número de referência, não prova real), `eval-retrieval --fake --mode`, k=6, 19 perguntas de `dev`, `bm25_corpus_hash` `ca4109c8…5a98`:

| Modo | Recall@6 (19) | MRR (19) | Recall@6 (5 termo exato) | MRR (5 termo exato) | Recall@6 (14 anteriores) | MRR (14 anteriores) |
| --- | --- | --- | --- | --- | --- | --- |
| dense | 0,632 | 0,500 | 0,000 | 0,000 | 0,857 | 0,679 |
| hybrid | 1,000 | 0,789 | 1,000 | 0,500 | 1,000 | 0,893 |

- Perguntas novas (`case: EXACT-TERM`; a passagem correta existe no corpus): `R-EXACT-SP630-pt` "O que é o SP630?" e `R-EXACT-SP630-en` "Which terminal is the SP630?" (`todas-as-maquininhas`); `R-EXACT-ADQ491-en` e `R-EXACT-ADQ491-pt` sobre "ADQ 4-91" (`erro-adq-4-91`); `R-EXACT-D30-en` "Which rates apply when I receive in D30?" (`todas-as-maquininhas`). Escolhidas entre 14 candidatas porque o denso de hash não as acha no top 6; em reformulações mais longas ele acha o SP630, então o ganho medido aqui é o da pergunta curta com código.

### Suíte estrita

`python tools/scripts/lint_and_tests.py --strict` (venv 3.13.3) com `PYTEST_ADDOPTS="--basetemp=.pytest_cache/t80-suite-basetemp -p no:cacheprovider"`, sobre o HEAD `c99aa90` **mais edições não commitadas de outro escritor** (rodada 2 da tarefa 79 em `cli.py`, `evaluation/judge.py`, `evaluation/calibration.py`, `evaluation/runner.py`, `llm/anthropic_llm.py`): **2028 passed, 1 failed** em 994,84 s (2029 = 2012 da tarefa 79 + 17 novos), ruff `All checks passed!`, caminhos pessoais limpos (727 arquivos), exit 1, 1042 s no total. Log em `.pytest_cache/t80-suite.log`, SHA-256 `20178555…0926`.

A falha é `tests/integration/test_v090_judge.py::test_moment_3_both_judges_against_the_same_human_ratings`: o teste espera a linha `judges: … (campaign v090-juiz-opus) beside …` e a `cli.py` em edição já imprimia `(campaign …, execution …)`. É a área da tarefa 79, não desta. Depois que o outro escritor commitou `820c270` e `7d1039f`, rodei no HEAD `7d1039f` `test_v090_judge.py` e os testes da tarefa 80 (`tests/unit/rag`, `test_v090_hybrid.py`, `test_cli_index_guard.py`): **53 passed**. Não rodei a suíte estrita de novo (memória da máquina; instrução de uma execução só): a suíte completa no HEAD final fica para o Reviewer ou o Supervisor.

### Decisões tomadas além do texto do plano (todas reversíveis)

1. **`min_score` no híbrido filtra só a lista densa.** O score devolvido é o do RRF (no máximo cerca de 0,033), então o limiar do Knowledge (`RETRIEVAL_MIN_SCORE`, 0,30) não corta os itens fundidos, e um item só do BM25 entra sem limiar denso (é o caso que o híbrido existe para pegar). Se o Supervisor preferir piso também no BM25, cabe na tarefa 81.
2. **BM25 só devolve chunks com ao menos um termo da pergunta**, ordenados por score e depois por `chunk_id`; o filtro `source_kinds` vale nas duas listas.
3. **Tokenização:** palavra com hífen e dígito fica inteira (`e-1023`, `4-91`); sem dígito, o hífen separa (`pré-pago` → `pre`, `pago`). Siglas viram minúsculas (`mdr`) e continuam token.
4. **Hash do BM25 separado do `corpus_hash` existente.** O existente (só ids, em ordem) continua como estava; o do BM25 é o sha256 dos pares (id, texto) ordenados por id, registrado no manifesto como `bm25_corpus_hash`, ao lado de `retrieval_modes: ["dense", "hybrid"]`.
5. **Onde o arquivo vai:** `KnowledgeIndex(bm25_dir=)`; `main.py` passa `<runtime>`, então o serviço grava `<runtime>/bm25-<hash>.pkl` na primeira busca híbrida. `testing.py` e `eval-retrieval` deixam o BM25 em memória (`bm25_dir=None`), como o Qdrant deles; `eval-retrieval` não grava nada em disco. Arquivos de hashes antigos não são apagados (versões da base convivem; o retorno do plano já prevê removê-los).
6. **Cache em processo por (cliente, coleção)**, com chave fraca no cliente para um cliente fechado não emprestar o cache a outro; `rebuild(replace_existing=True)` descarta o cache daquela coleção. O BM25 é montado com os payloads da coleção ativa (scroll no Qdrant), não com os documentos em disco.
7. **O modo mora no índice:** `KnowledgeIndex(mode=)` (padrão `dense`; modo inválido é `ValueError`); `search()` sem `mode` usa o do índice, e `capture_active` repassa `mode` e `bm25_dir` ao índice da versão ativa. `RETRIEVAL_MODE` é `Literal["dense", "hybrid"]`.
8. **Desempate do RRF:** score, depois posição no denso, depois posição no BM25.

### Achados e limitações

- **`origin` não aparece no trace do Knowledge.** `Hit.origin` existe, mas o passo `knowledge` do trace grava `doc`, `score`, `chunk_id` e `excerpt` em `agents/knowledge.py`, e a tarefa pede que o Knowledge não mude. Acrescentar `"origin": h.origin` lá é uma linha; **decisão do Supervisor** (muda o trace também no modo denso).
- **Incidente de commit, corrigido antes de qualquer push.** O primeiro commit da parte de CLI (`a9772da`) levou junto, sem querer, cerca de 40 linhas não commitadas de outro escritor em `cli.py` (`_store_judgements(run=)`, `--judge-run`, aviso de `--only-sample`), porque estavam no mesmo arquivo da árvore de trabalho. Refiz o commit local (`--amend`, com só as minhas linhas de `cli.py`, montadas a partir do arquivo do commit anterior) sem tocar na árvore: as edições do outro escritor voltaram a ficar não commitadas como estavam, e ele as commitou depois em `7d1039f`. `a9772da` não foi publicado; o commit vigente é `c99aa90`.
- **`.env` carregado uma vez, sem efeito pago.** A primeira medição exploratória (`python -m merchant_assistant.cli eval-retrieval --fake`) rodou com o repositório como diretório corrente, e o `Settings` carrega `.env` de lá. Com `--fake` o embedder é o de hash, sem chamada e sem orçamento. As medições seguintes, inclusive a tabela acima, usaram `Settings(_env_file=None)` fora do repositório.
- Os números acima são do embedder de hash, que também é lexical; o ganho real do híbrido só aparece com embeddings reais na campanha do QA (tarefa 82). Holdout de retrieval, nDCG@6, `--split` e reranker são da tarefa 81.

### Próxima ação

Reviewer: revisar `5d82fd0` e `c99aa90` e rodar a suíte estrita no HEAD final. Supervisor: decidir sobre `origin` no trace e sobre o piso do BM25 (decisão 1).

## Tarefa 80 — rodada 2 (correções da revisão)

- **Papel e responsável:** Developer, subagente despachado pelo Supervisor (time único), rodada de correção da mesma tarefa.
- **Objetivo e critérios:** fechar P2-1, P2-2 e P2-3 do [parecer da rodada 1](v090-reviewer-t80.md) com as decisões do Supervisor; `RETRIEVAL_MODE` no `.env.example` (P3-5); demais P3 só registrados.
- **Escopo:** `rag/bm25.py`, `rag/index.py`, `tests/unit/rag/test_bm25_hybrid.py`, `tests/integration/test_v090_hybrid.py`, `.env.example`, Validação e Status da tarefa 80 e esta seção. `agents/knowledge.py`, `main.py`, `cli.py`, `llm/` e `evaluation/` não mudaram; nenhum prompt, rótulo, cenário, migração, snapshot ou ledger mudou.
- **Estado:** corrigido; aguarda nova rodada do Reviewer.
- **Branch e base:** `codex/v0.9.0-juiz-retrieval`, base da rodada `8db183a`. Commits: `60ab2c8` (correções e testes), `687895c` (`.env.example`) e o commit desta passagem. Identidade conferida: `lauroPereira <lauro.s.pereira@gmail.com>`. Arquivos adicionados por nome. Sem push.
- **Independência:** não se aplica (implementação).

### Como cada P2 foi fechado

- **P2-1 (pickle com metadados velhos).** Opção preferida do Supervisor. O arquivo `bm25-<hash>.pkl` guarda agora só `{"format": 2, "corpus_hash", "chunk_ids", "bm25"}`, ou seja, os ids e as estatísticas do `BM25Okapi` (frequências de termos por chunk, idf), sem payload. `Bm25Index.from_persisted(state, records, digest)` junta essas estatísticas aos payloads dos registros que `bm25_index()` acabou de ler da coleção ativa no Qdrant. Por isso URL, `collected_at`, `procedure_id` e o `source_kind` do filtro vêm sempre da coleção atual. O arquivo é recusado e reconstruído quando o formato, o hash ou o conjunto de ids não confere, ou quando o objeto não é um `BM25Okapi` do mesmo tamanho. Arquivos da rodada 1 (objeto `Bm25Index` com payloads) caem nesse caso e são regravados. Sonda 9 do parecer virou teste: `v1` e `v2` com mesmo id e texto, metadados diferentes, mesmo diretório e mesmo cliente; um único arquivo; `v2.search("E-1023", mode="hybrid", source_kinds=["public_official"], min_score=0.99)` dá `[]`, e com `simulated_internal` dá `("bm25", "https://new.example", "simulated_internal")`. Outro teste confere que o arquivo não contém a URL.
  - Interpretação de "no momento da busca": os payloads vêm da leitura da coleção feita quando o BM25 entra no cache do processo (por cliente e coleção), não de uma releitura a cada busca. A coleção publicada é imutável, e `rebuild(replace_existing=True)` descarta o cache, como na rodada 1. Ler o payload no Qdrant a cada busca exigiria buscar mais de `3×k` candidatos para o filtro de `source_kind`. Fica registrado caso o Reviewer veja diferença.
- **P2-2 (construção concorrente).** Três mudanças:
  - Temporário `bm25-<hash>.pkl.<pid>-<thread id>-<uuid>.tmp` e `os.replace` atômico.
  - Trava em processo por arquivo de destino em `load_or_build`. Quem espera relê o arquivo pronto e não reconstrói.
  - Trava por (cliente, coleção) em `bm25_index()`, guardada em `WeakKeyDictionary` como o cache. Ela cobre também o caso sem diretório (`testing.py`, `eval-retrieval`).

  Se a escrita falhar (`OSError`: arquivo preso por outro processo no Windows, disco cheio), o temporário é apagado e o índice em memória é devolvido. A busca não cai em `knowledge_unavailable`. Testes no Windows, com 4 threads e `threading.Barrier`, num corpus de 3000 chunks:
  - `load_or_build`: 0 erro, 1 construção, um só arquivo, nenhum `.tmp` restante.
  - `_write` simultâneo sem a trava (simula processos diferentes): 0 erro.
  - Primeira busca híbrida simultânea pelo índice, com e sem `bm25_dir`: 1 construção.
  - `os.replace` falhando: a busca responde da memória e não sobra arquivo.
- **P2-3 (mutantes).** Testes novos:
  - `rrf` com números fixos `1/62 + 1/61` e `1/61`, não lidos de `RRF_K`.
  - Profundidade `3×k`: com `k=2`, `e` está em 5º no denso e em 3º no BM25. Ela só sai em 1º, como `both` e com `1/65 + 1/63`, se as duas listas forem até 6. O teste confere também as profundidades pedidas (`dense` 6, `bm25` 6).
  - `min_score` só na lista densa: com `min_score=0.99`, o denso dá `[]` e o híbrido dá `[("d2#0", "bm25")]` com `1/61`. Sem limiar, a lista densa participa.
  - `main.build_orchestrator` com `retrieval_mode` `dense` e `hybrid`, LLM programado e embedder de hash: o índice do orquestrador (o mesmo do `KnowledgeBase`) tem o modo e `bm25_dir == runtime_path`. Uma busca sem `mode` grava um `bm25-*.pkl` no runtime e traz `origin` não denso no híbrido; no denso, não grava nada e tudo é `dense`.
  - `cmd_eval_retrieval` nos dois modos: as 5 `EXACT-TERM` têm rank no híbrido e pelo menos 3 sem rank no denso; o MRR do híbrido é maior.

  Mutação manual numa cópia do HEAD em `<scratchpad da sessão>` (`git archive` + os 4 arquivos), com `PYTHONPATH` para o `src/` da cópia (conferido) e os dois arquivos de teste da tarefa. **12 mutantes, 12 mortos**:
  - M01 (híbrido ignora `min_score`), M02 (profundidade `k`), M03 (`RRF_K=1`).
  - M10 (`main.py` sem `mode=` e `bm25_dir=`), M10b (só sem `bm25_dir=`), M12 (`cmd_eval_retrieval` não passa `mode`).
  - Payloads lidos do arquivo, junto com o arquivo guardando payloads; e o arquivo guardando payloads, sozinho.
  - Temporário só com o pid.
  - Sem a trava de `load_or_build`; sem a trava de `bm25_index()`. Esta sobreviveu na primeira tentativa, porque a construção de 2 chunks cabia numa fatia do GIL; o teste ganhou uma construção lenta (`sleep` de 0,2 s no espião) e o caso sem `bm25_dir`.
  - Escrita que falha propaga a exceção.

  M15 (hash interno do arquivo) fica como estava: hoje o hash é conferido, junto com o formato e os ids.

### Limitação para a decisão D7 (Supervisor leva ao relatório; o Knowledge não mudou)

No modo híbrido, o `min_score` (`RETRIEVAL_MIN_SCORE`, 0,30 no serviço) corta só a lista densa. Em `agents/knowledge.py:168`, o atalho `no_evidence` (`if not hits`) só dispara quando nenhuma das duas listas devolve nada. Na prática, isso acontece quando a pergunta não tem nenhum token da base depois das stopwords e o denso também não passa do limiar. Uma pergunta fora do domínio que compartilhe uma palavra com algum chunk ("taxa", "cartão") chega ao modelo com passagens só do BM25, e o portão de evidência passa a depender do prompt e do juiz da evidência, não do limiar. O `score` do passo `knowledge` no trace muda de escala, de cosseno (cerca de 0,3 a 0,6) para RRF (no máximo cerca de 0,033): quem lê o trace ou compara scores entre modos precisa saber o modo. A campanha real do QA (tarefa 82) deve olhar `NOEV` e as perguntas fora do domínio no híbrido antes de a D7 trocar o padrão. Alternativas, se o Supervisor quiser: piso de score no BM25 ou exigir ao menos um item denso acima do limiar para responder.

### P3 (registrados)

- **P3-1** `origin` fora do trace e das linhas do `eval-retrieval`: continua para a tarefa 81 ou 82 (campo aditivo em `hits`, no `knowledge.py`).
- **P3-2** versão do tokenizador e parâmetros fora da chave: o campo `format` do arquivo existe agora (2), mas não muda com o tokenizador. Mudança de `tokenize`, `STOPWORDS`, `k1` ou `b` precisa subir esse número ou entrar no hash. Não implementado.
- **P3-3** hífen não ASCII e `E1023`/`E 1023`: não tratado.
- **P3-4** arquivos `bm25-*.pkl` nunca podados; cache e travas por coleção crescem com as coleções consultadas pelo cliente (as travas por arquivo em `bm25._BUILD_LOCKS` também). Volume pequeno, uma entrada por versão da base.
- **P3-5** `RETRIEVAL_MODE` agora está no `.env.example`, comentado, com padrão `dense`. Falta alinhar no ADR 0020 o nome `bm25-<hash>.pkl` (decisão 17 do plano diz `bm25.pkl`) e registrar o manifesto aditivo (`bm25_corpus_hash`, `retrieval_modes`).
- **P3-6** `pickle.load` lê só o runtime do próprio serviço. Agora o conteúdo é um dicionário com um `BM25Okapi`, conferido por tipo, mas o `pickle.load` em si continua confiando no diretório. Registrar no ADR.

### Evidência

- Testes novos: **14** (11 em `test_bm25_hybrid.py`, que passa de 15 para 26 itens, e 3 em `test_v090_hybrid.py`, de 2 para 5). Os dois arquivos: 31 passed. Com `tests/unit/rag`, `test_identity.py` e `test_v070_identity_r2.py` (os que leem `.env.example`): verdes (1 skip esperado do `test_v070_identity_r2.py`).
- Referência com embeddings de hash (`cmd_eval_retrieval` com `Settings(_env_file=None, openai_api_key=None)`, runtime no scratchpad), igual à rodada 1: denso R@6 0,632 e MRR 0,500; híbrido 1,000 e 0,789; ranks das 5 `EXACT-TERM` `[None ×5]` contra `[2, 4, 1, 4, 2]`; `bm25_corpus_hash` `ca4109c8ccf9…`; 0 token de embedding.
- Suíte estrita: `python tools/scripts/lint_and_tests.py --strict` com `PYTEST_ADDOPTS="--basetemp=.pytest_cache/t80r2-suite-basetemp -p no:cacheprovider"`, sobre `687895c` (só a Validação da tarefa 80 modificada na árvore; durante a execução outro escritor commitou `80a0853` e `97b8141`, só documentação, fora dos meus arquivos): **2050 passed** em 836,31 s, 0 failed, 0 skipped (2036 da rodada 1 com o skip do basetemp resolvido + 14 novos); ruff `All checks passed!`; caminhos pessoais limpos (728 arquivos); exit 0. Log `.pytest_cache/t80r2-suite.log`, SHA-256 `00260f3a…be48`. Esperei a suíte estrita do outro agente terminar antes de começar a minha.

### Próxima ação

Reviewer, em contexto novo: re-verificar `rag/bm25.py`, `rag/index.py` e os testes; repetir as sondas 9, 10 e 11 e os mutantes M01, M02, M03, M10 e M12. Supervisor: levar a limitação do `min_score` à decisão D7 e decidir o destino de P3-1 e P3-2.

## Tarefa 81 — Reranker, holdout de retrieval e `eval-retrieval` com nDCG (rodada 1)

- **Papel e responsável:** Developer (subagente), 2026-11-05.
- **Objetivo e critérios:** tarefa 81; spec `juiz-retrieval-v090.md` D7, D8, D10 e CA-52 (prova determinística); história, momentos 5 e 6.
- **Escopo:** holdout de retrieval lacrado, nDCG@6, reranker `rerank.v1`, `RERANK`, `eval-retrieval --mode --rerank --split --out`.
- **Estado:** apto para revisão.
- **Branch e PR:** `codex/v0.9.0-juiz-retrieval`, sem PR, sem push.
- **Base e versão final:** base `41fb745`. Commits `8c1970b` (holdout e lacre), `2856be1` (reranker), `37dfbf6` (avaliação e CLI) e `4c27e4a` (`.env.example`). Entre a base e o meu primeiro commit, outro escritor commitou `dd804d3` e `fad0eb2`, só documentação do juiz.
- **Independência:** não se aplica (implementação).

### Arquivos

- `tests/scenarios/retrieval_holdout_v090.jsonl` e `.sha256`, mais `tests/unit/test_retrieval_holdout_v090.py` (novos, no mesmo commit `8c1970b`).
- `prompts/rerank.v1.md` e `src/merchant_assistant/rag/rerank.py` (novos).
- `rag/index.py`: `search(..., reranker=, meter=, notes=)`, aplicado depois da fusão.
- `config.py`: `rerank: Literal["on", "off"] = "off"` e um validador (`RERANK=on` exige `RETRIEVAL_MODE=hybrid`), só por acréscimo.
- `agents/knowledge.py`: 6 linhas. Com `RERANK=on`, passa o reranker, o `ctx` como `Meter` e `ctx.step_notes` (trace). Com `off`, a chamada a `search` é a mesma de antes, sem argumentos novos.
- `evaluation/scripted_policy.py`: reranker programado (agente `rerank`).
- `evaluation/retrieval.py`: nDCG, splits, lacre, tempo por consulta, relatório acumulado e linha D7.
- `cli.py`: só o bloco `eval-retrieval` (função, parser e `_retrieval_reranker`). Os blocos `eval --judge-repeat` e `eval-calibrate` não mudaram.
- `.env.example`: `# RERANK=off` comentado.
- Testes novos: `tests/unit/rag/test_rerank.py`, `tests/unit/evaluation/test_retrieval_metrics.py` e `tests/integration/test_v090_rerank.py`.

### Holdout

São 25 perguntas, 13 em português e 12 em inglês: 6 de taxas, 6 de produtos, 6 de procedimentos e 7 de termos exatos (ADQ 1-50, ADQ 4-83, gravame, "Qr Code Expirado", código 51 da demonstração, Dock IP, conciliador Auttar).

Escrevi as perguntas lendo o texto dos chunks (`load_all` e `chunk_document` sobre `data/`). Cada uma tem a passagem correta com grau 2 e, em 12 delas, uma segunda passagem relevante com grau 1, nos casos em que o mesmo fato aparece no chunk vizinho. Não rodei nenhum modo de busca sobre essas perguntas, nem antes nem depois do lacre, nem com embeddings de hash. Evitei os assuntos do `dev` (SP630, ADQ 4-91, D30, Wi-Fi, parcelas do crediário, WhatsApp).

O lacre é o sha256 do conteúdo com fim de linha LF (`d8381ddd7d7f…0d12d`), como no `holdout_v080`. O teste confere:

- o lacre, inclusive com CRLF e com edição;
- a forma: no mínimo 20 perguntas, metade em pt, as 4 categorias, exatamente um grau 2 por pergunta;
- que todo `chunk_id` existe no corpus versionado;
- ids e perguntas novos;
- que nenhum outro arquivo de `tests/` cita o holdout.

### Decisões tomadas além do texto do plano (todas reversíveis)

1. **Relevância e métricas.** No holdout, a relevância é por chunk, com grau. Recall@6 e MRR contam a primeira passagem com grau de pelo menos 1. O nDCG@6 usa ganho linear (`g / log2(posição + 1)`) e o ideal é o dos graus rotulados. No `dev`, os rótulos são por documento e "qualquer um serve". Lá o nDCG usa um alvo só (ideal `[1]`, ganho só no primeiro relevante), o que equivale a `1 / log2(1 + rank)`. Recall e MRR do `dev` não mudaram.
2. **Regra D7 operacional.** "Melhorar" quer dizer nDCG@6 estritamente maior nos dois splits: híbrido contra denso e, depois, híbrido+reranker contra híbrido. O reranker só é sugerido se o híbrido for. Enquanto faltar alguma das 6 combinações, a linha diz "indisponível: faltam …". A linha é só sugestão; a decisão é do Supervisor na 82.
3. **Reranker.**
   - Rótulos curtos `P1`…`P12` no lugar dos `chunk_id` longos, para caber em 150 tokens de saída. `effort` fica `none`, e cada passagem é cortada em 700 caracteres.
   - Rótulo desconhecido, lista vazia, saída que não valida, `LLMError`, `BudgetExceeded` e `LimitExceeded` contam como falha. A falha mantém a ordem da fusão e grava `rerank.status = failed` com o erro nas notas.
   - Rótulos deixados de fora vão para o fim, na ordem da fusão, e um rótulo repetido conta uma vez. Com menos de 2 candidatos não há chamada (`skipped`).
4. **Com reranker, a fusão é calculada para 12** (profundidade 36) e devolve os 6 primeiros depois da nova ordem. Por isso, a base do híbrido+reranker pode diferir do híbrido com `k=6` (profundidade 18) em posições baixas.
5. **`RERANK=on` exige o híbrido**, no `Settings`, na CLI e em `search(mode="dense", reranker=…)`.
6. **No serviço**, o reranker usa `ctx.llm_for("rerank")`, que é o modelo do agente (`gpt-6-luna`) quando nenhum perfil o substitui. A chamada é medida pelo `RunContext`: entra no orçamento da requisição, em `max_model_calls` e em `usage_by_agent["rerank"]`. O trace do passo `knowledge` ganha `rerank` com prompt, candidatos, status e ordem (posições da fusão).
7. **`eval-retrieval` pago com `--rerank on`.** O modelo do agente passa por `BudgetMeter` no ledger do projeto (`request_id` `eval-retrieval-rerank`), com teto de US$0,05 por execução (`RERANK_EVAL_CAP_USD`). A estimativa é de cerca de US$0,0003 por chamada. Se o teto estourar, o reranker falha nas consultas que faltam, e `rerank_failures` mostra quantas foram.
8. **`--out <arquivo>.md`.**
   - Acumula num `.json` ao lado uma linha por split e configuração e gera a tabela com Recall@6, MRR, nDCG@6, tempo médio e execuções. Gera também a frase do lacre e a linha "Modo padrão sugerido".
   - Medir de novo a mesma configuração no holdout marca "holdout já visto".
   - Recusa misturar embeddings ou `k` no mesmo relatório.
   - Sem `--out`, a saída continua sendo o JSON no stdout (com os campos novos `split`, `rerank`, `holdout`, `rerank_usage`, `ndcg_at_k` e `mean_ms`).
9. **P3-1 da tarefa 80, parcial.** As linhas do `eval-retrieval` ganham `origins` (os 3 primeiros). O trace do Knowledge não ganhou `origin`, para não mexer além do necessário. O `evaluation/evidence.py` só lê `doc` e `excerpt`, então a mudança seria inofensiva para o juiz se o Supervisor quiser.

### Evidência

- Testes novos: **47 itens**.
  - `test_retrieval_holdout_v090.py`: 6.
  - `test_rerank.py`: 16. Sucesso; corte de entrada; ordem parcial e repetida; 4 falhas do modelo; orçamento e limite da requisição; menos de 2 candidatos; limite de tokens com `OpenAILLM` sobre um cliente falso que devolve `incomplete`, com `max_output_tokens=150` conferido no pedido e a chamada truncada liquidada no `Meter`; e, no índice, os 12 da fusão, a ordem mantida na falha, a nota do trace e o modo denso recusado.
  - `test_retrieval_metrics.py`: 17. nDCG com números fixos: ideal 1,0; invertido `[1, 2]` contra `[2, 1]` = 0,859719; relevante em 6º = 0,356207; em 2º = 0,630930; 7º fora do @6 = 0. Também o `evaluate`, o lacre, a regra D7 em 5 casos, "indisponível", "já visto" e embeddings misturados.
  - `test_v090_rerank.py`: 8. Os 3 modos nos 2 splits pela CLI com hash, sem rede. O holdout é sintético e lacrado num diretório temporário, e o real não é lido. Também: lacre quebrado recusado antes de qualquer caminho pago, `--mode dense --rerank on` recusado, o parser, e o Knowledge com `RERANK=on` (ok e falha) e com `off` (nenhuma chamada).
- Testes focados (os novos, `tests/unit/rag`, `test_v090_hybrid.py`, `test_holdout_v080.py` e `test_v080_journeys.py`): 193 passed.
- Referência com embeddings de hash, **só `dev`** (19 perguntas; o holdout não foi medido por mim): denso R@6 0,632, MRR 0,500, nDCG@6 0,534, 0,6 ms; híbrido 1,000, 0,789, 0,843, 3,0 ms; híbrido+reranker programado 1,000, 0,765, 0,825, 5,9 ms, 19 chamadas medidas, 0 falha; 0 token de embedding. O reranker programado (sobreposição de tokens) não mede qualidade: serve para provar o caminho, e o número dele não decide nada.
- Suíte estrita: `python tools/scripts/lint_and_tests.py --strict` no HEAD `4c27e4a`, sem alterações locais nos meus arquivos: **2096 passed, 1 skipped** em 735,80 s, 0 failed. São 2050 da tarefa 80 mais 47 novos. O skip é o `test_v070_identity_r2.py:277`, que só roda com basetemp dentro de `.pytest_cache`; rodei sem `--basetemp`. Ruff `All checks passed!`, caminhos pessoais limpos (746 arquivos), estrutura e skills válidas, exit 0. Antes de começar, conferi que nenhuma outra suíte estava rodando

### Achados e limitações

- O holdout não foi medido em nenhum modo. A primeira medição é do QA, com embeddings reais, por último e uma vez por configuração (D8).
- O "já visto" só é registrado dentro do mesmo relatório `--out`. Uma execução sem `--out`, ou com outro arquivo, não é contada. A regra continua operacional para o QA, como no `holdout_v080`.
- A limitação do `min_score` registrada na tarefa 80 vale também para o reranker. Ele reordena o que a fusão trouxe e não corta nada, então não muda o portão `no_evidence`.
- Com `RERANK=on` no serviço, cada pergunta de conhecimento faz uma chamada a mais. Ela conta no `max_model_calls` (8) e no custo por requisição, sem limite de latência novo.
- Os rótulos grau 1 dos vizinhos e as categorias são julgamento meu. Se o Reviewer achar um rótulo errado, registro como nota e não altero o arquivo lacrado: qualquer edição quebra o lacre e exige novo holdout.

### Roteiro do QA (momentos 5 e 6; embeddings reais, ledger do projeto)

Rodar na ordem, sempre com o mesmo `--out`:

1. `eval-retrieval --mode dense --split dev --out docs/evidence/v090-retrieval.md`.
2. O mesmo com `--mode hybrid`.
3. O mesmo com `--mode hybrid --rerank on`.
4. Por último, uma vez cada: os três com `--split holdout_v090`.

O relatório traz a tabela, o lacre e a linha D7. Custo estimado: embeddings de 145 chunks mais 19 ou 25 perguntas por execução (frações de centavo), mais 19 + 25 chamadas curtas do reranker (cerca de US$0,015).

### Próxima ação

Reviewer, em contexto novo: o reranker (falhas e limite), o lacre e a ordem dos commits (holdout em `8c1970b`, antes do código que mede), a regra D7 e o `eval-retrieval`. Depois, o QA (momentos 5 e 6) e a decisão D7 na tarefa 82 (Supervisor).
