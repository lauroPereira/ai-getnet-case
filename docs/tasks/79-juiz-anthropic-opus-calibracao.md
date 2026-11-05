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

(Preenchida pelo Developer.)

## Status

Pendente. Aberta pelo Supervisor em 2026-11-05.
