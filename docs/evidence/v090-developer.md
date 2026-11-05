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
