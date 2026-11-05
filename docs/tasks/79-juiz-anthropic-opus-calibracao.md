# Tarefa 79 — Juiz Anthropic e experimento de calibração

## Objetivo

Permitir que a campanha de avaliação use um modelo Claude como juiz independente e que a concordância humano × juiz da amostra de calibração seja medida para um juiz escolhido, sem nova avaliação humana.

## Especificação relacionada

[Juiz Claude e retrieval híbrido v0.9.0](../specs/juiz-retrieval-v090.md): D1 a D5, RF-108, CA-56. Rubrica e juiz da v0.8.0: `src/merchant_assistant/evaluation/judge.py`, `calibration.py`, `runner.rejudge`.

## Pré-condições

Branch `codex/v0.9.0-juiz-retrieval` criada da `main` com a v0.8.0. Nenhuma chamada paga: o adaptador é testado com um provedor programado. `pip install anthropic` na venv é permitido (dependência nova em `pyproject.toml`).

## Arquivos prováveis

`src/merchant_assistant/llm/anthropic_llm.py` (novo), `llm/prices.json`, `llm/pricing.py` se precisar de campo de cache criado, `main.model_factory`, `evaluation/judge.py` (`JUDGE_PROVIDERS`, `_has_key`), `config.py` (`anthropic_api_key`, só por acréscimo), `cli.py` (`--only-sample` em `eval --judge-repeat`; `--judge` em `eval-calibrate --import`), `evaluation/calibration.py` (`judgement_for` por evaluador; relatório com dois juízes), `.env.example` (comentário do bloco do juiz), `pyproject.toml`, testes em `tests/unit/llm/`, `tests/unit/evaluation/`, `tests/integration/`.

## Passos

1. **Adaptador.** `AnthropicLLM(client, model)` com `parse(spec, schema, meter)` segundo D3: `messages.create(model, system=spec.instructions, messages=[{"role":"user","content":spec.input}], max_tokens=spec.max_output_tokens, output_config={"format": <json_schema do schema Pydantic, strict>}, timeout=...)`; `thinking` e `effort` omitidos. Resposta: o bloco de texto JSON validado pelo `schema`; `stop_reason` `refusal` ou `max_tokens` → `LLMError` com o motivo; `usage` com `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`. `run_tools` e `web_search` → `LLMError("not supported for the judge in v0.9.0")`. Reserva e acerto no `Meter` como no `OpenAILLM`. Confirme nomes de campos e parâmetros na documentação do SDK instalado (`anthropic` ≥ a versão corrente), não de memória; se `output_config.format` não existir na versão instalada, registre a alternativa usada e por quê.
2. **Preços.** `prices.json`: `claude-opus-5-5` (provider `anthropic`, entrada 4,00, saída 20,00, cache lido 0,20), `claude-sonnet-5-5` (2,00 / 10,00 / 0,20), `claude-haiku-5-5` (0,10 / 0,50 / 0,01), com `model_version` e nota "pensamento cobrado como saída", data 2026-11-05. Se o `BudgetMeter` não precifica cache criado, acrescente de forma compatível (campo opcional, padrão 1,25× a entrada só para `anthropic`).
3. **Fábrica e validação.** `model_factory`: `provider == "anthropic"` → `AnthropicLLM(anthropic_client(settings), model)`; cliente construído só com `ANTHROPIC_API_KEY`. `JUDGE_PROVIDERS = ("openai", "deepseek", "anthropic")`; `_has_key` cobre a chave; `check_independence` já dá `different_provider` para agente `openai`.
4. **Filtro da amostra.** `eval --judge-repeat N --answers-from <json> --only-sample <csv>`: rejulga só os `request_id` presentes no CSV de calibração (coluna `request_id`), na ordem do CSV; `--only-sample` com `--limit K` (se já existir um limitador, reutilize; senão acrescente `--limit`) permite a sonda de 3. A saída e o relatório dizem quantos IDs foram filtrados.
5. **Comparação por juiz.** `eval-calibrate --import <csv> --judge <provedor>/<modelo> [--campaign <nome>] [--out <md>]`: `judgement_for` filtra `evaluator` pelo par informado (hoje pega o primeiro `repetition=1` de qualquer juiz); sem `--judge`, comportamento atual. Com `--judge`, o relatório traz, além do bloco do juiz pedido, o bloco do juiz da campanha original (DeepSeek) para as mesmas linhas, lado a lado, e a consistência entre repetições de cada juiz quando houver mais de uma. As notas humanas vêm do CSV (reimportadas sob o `--campaign` informado) e devem ser idênticas às já gravadas em `calibrations` para `v080-all-r3`; divergência é erro.
6. **Provedor programado.** Para `anthropic` nos testes, uma implementação programada que devolve julgamentos fixos e `usage` com cache, cobrindo: esquema estrito aceito, `refusal`, `max_tokens`, erro de rede, precificação com cache lido e criado, independência, `--only-sample`, `--judge`, relatório com dois juízes.
7. **Documentação de configuração.** `.env.example`: no bloco do juiz, `JUDGE_PROVIDER=anthropic` e `JUDGE_MODEL=claude-opus-5-5` como alternativa comentada, com a chave; README e CHANGELOG ficam para a tarefa 82.

## Critérios de conclusão

- Com `JUDGE_PROVIDER=anthropic JUDGE_MODEL=claude-opus-5-5` e o provedor programado, `eval --judge-repeat 3 --answers-from <json> --only-sample <csv>` grava 72 julgamentos com `evaluator.provider = anthropic` e um relatório com a variação do juiz; `--limit 3` grava 3.
- `eval-calibrate --import <csv> --judge anthropic/claude-opus-5-5 --campaign v090-juiz-opus --out <md>` produz o relatório com os dois juízes contra as mesmas notas humanas; sem `--judge`, o relatório da v0.8.0 sai idêntico.
- `refusal` e `max_tokens` nunca viram nota; aparecem como falha contada.
- Nenhum teste chama rede; `lint_and_tests.py --strict` verde; `checar-caminhos-pessoais.py` limpo.

## Validação

Developer, 2026-11-05, commits `ffe9803` e `c0045a5` na `codex/v0.9.0-juiz-retrieval`. Passagem: [v090-developer.md](../evidence/v090-developer.md).

- SDK conferido no pacote instalado (`anthropic 2.5.0`): `messages.create(..., output_config={"format": {"type": "json_schema", "schema": ...}})`; `JSONOutputFormatParam` não tem campo `strict`, e o esquema estrito vem de `anthropic.transform_schema` (`additionalProperties: false`, todos os campos em `required`). `thinking` e `effort` omitidos.
- Provedor programado: o cliente real do SDK sobre `httpx2.MockTransport` (`llm/scripted_anthropic.py`); nenhuma rede, nenhuma chamada paga, `.env` não lido.
- Testes novos: 15 passed (`tests/unit/llm/test_anthropic_judge.py`, 10; `tests/integration/test_v090_judge.py`, 5). Cobrem esquema estrito no corpo enviado, `refusal`, `max_tokens`, erro de rede, resposta fora do esquema ou da escala, `run_tools`/`web_search` recusados, preço com cache lido e criado, independência e chave, fábrica, `--only-sample` (72 julgamentos na ordem do CSV; recusa de ID ausente), `--limit 3` (3 julgamentos), falhas contadas no relatório, ledger Anthropic separado, `--judge` com os dois juízes, consistência e custo por julgamento, recusas de `--judge` (sem julgamento do juiz, campanha original, formato, nota divergente) e relatório sem `--judge` idêntico ao anterior.
- `lint_and_tests.py --strict` no HEAD `c0045a5`: **2012 passed** (1997 + 15), ruff sem achados, skills válidas, exit 0.
- `checar-caminhos-pessoais.py`: nenhuma ocorrência (722 arquivos, dentro da suíte estrita).
- Decisões além do texto e limites (cap `v090-juiz-opus` sem opção de CLI; teto pelo ledger Anthropic novo com `BUDGET_LIMIT_USD=4.00`): na passagem.

### Rodada 2 (correções da revisão)

Developer, 2026-11-05, commits `820c270` e `7d1039f` sobre `fee7a78`, a partir do [parecer da rodada 1](../evidence/v090-reviewer-t79.md) e das decisões do Supervisor. Passagem: [v090-developer.md](../evidence/v090-developer.md), seção "Tarefa 79 — rodada 2".

- **P2-1:** testes com julgamento válido no texto sob `refusal`, `max_tokens` e `model_context_window_exceeded` (adaptador, `Judge.evaluate` e fluxo da CLI); tirar qualquer um dos três de `FAILED_STOPS` derruba a suíte (mutação conferida numa cópia).
- **P2-2:** cada julgamento gravado leva o nome da execução (`--name` do `eval`, ou o nome padrão do relatório) em `evaluator.run`, sem migração. `eval-calibrate --import --judge <par>` ganhou `--judge-run <nome>`: o juiz A é lido só nessa execução (concordância, consistência, custo e tokens); sem `--judge-run`, mais de uma execução do juiz sobre os 24 pedidos é erro que lista as execuções. O juiz B é lido nas execuções dos julgamentos ligados às notas (`legado` para os gravados sem nome). O relatório diz, por juiz, as execuções e quantos julgamentos entraram em cada bloco. O teste do momento 3 roda a sonda antes das 3 repetições e uma rodada extra do juiz original.
- **P2-3:** tokens de entrada, cache lido, cache criado e saída de cada julgamento em `run_evaluations.result.usage` (e no JSON do relatório), também quando uma recusa ou um corte foi cobrado; total e média por julgamento no relatório do `eval` e no relatório dos dois juízes, ao lado do custo.
- **P3-3:** aviso em stderr quando `--only-sample` vem sem `--judge-repeat`. Demais P3 registrados na passagem.
- Testes da tarefa: 22 passed (`tests/unit/llm/test_anthropic_judge.py`, 17, sendo 7 novos; `tests/integration/test_v090_judge.py`, 5, com o momento 3 e o de falhas reescritos); suítes focadas de avaliação e LLM: 1011 passed; mutações: 11 de 11 mortas.
- `lint_and_tests.py --strict` no HEAD `94df63c` (meus commits mais os da tarefa 80), com `PYTEST_ADDOPTS="--basetemp=.pytest_cache/t79r2-suite -p no:cacheprovider"`: **2036 passed** em 1069 s, ruff `All checks passed!`, caminhos pessoais limpos (727 arquivos), skills válidas, exit 0. Log em `.pytest_cache/t79r2-suite.log`, SHA-256 `f98f8d35…56cc`.

## Status

Rodada 2 implementada pelo Developer em 2026-11-05 (correções P2-1 a P2-3); aguarda nova rodada do Reviewer. Critérios da spec não marcados (Supervisor, depois da revisão e do QA).
