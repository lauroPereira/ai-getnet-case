# Tarefa 85 — `/metrics` e regras de alerta versionadas

## Objetivo

Expor métricas operacionais em texto Prometheus a partir do que o sistema já grava (traces e ledger) e versionar regras de alerta sobre elas.

## Especificação relacionada

[Rubrica `judge.v4` e operação v0.10.0](../specs/rubrica-operacao-v0100.md): D4, D5, CA-59; especificação 0.2 RF-97. Código: `observability/traces.py` (`TraceStore`), tabelas `requests` e `steps` em `traces.sqlite3`, ledger `budget.sqlite3`, `api/app.py` (`/health`, `/ready`).

## Pré-condições

Tarefa 84 commitada. Nenhuma dependência nova.

## Arquivos prováveis

`src/merchant_assistant/observability/metrics.py` (novo), `api/app.py` (rota `GET /metrics`, só por acréscimo), `alerts/rules.yml` (novo, raiz do repositório), `docker-compose.yml` só se precisar expor algo (não deve), README (seção Observability), testes.

## Passos

1. **Coleta.** Consulta agregada em `traces.sqlite3`: `requests_total{route,status}`, `model_calls_total{agent}`, `tool_calls_total{tool,outcome}`, `tool_failures_total{tool}`, `handoffs_total`, `replan_total{origin}`, `request_duration_seconds` (histograma com buckets fixos ou sumário com quantis calculados), e do ledger `cost_usd_total{provider}` e `budget_remaining_usd`. Nenhum rótulo com texto de mensagem, `request_id`, lojista ou operador.
2. **Exposição.** `GET /metrics` em `text/plain; version=0.0.4`, com `# HELP` e `# TYPE`; cache de 5 s em processo; autenticação: mesma política do `/ready` (se `/ready` é público, `/metrics` é público; se não, token com escopo de leitura); registre a escolha.
3. **Regras.** `alerts/rules.yml` no formato Prometheus (`groups: - name: merchant-assistant`): orçamento abaixo de 10% do teto; taxa de falha de ferramenta acima de 5% em 15 min; taxa de encaminhamento acima de 30% em 1 h; p95 de duração acima de 20 s em 15 min; cada regra com `summary`, `description` e `runbook_url` para a seção do README.
4. **Teste de coerência.** Um teste lê `rules.yml`, extrai os nomes de métrica das expressões e confere que todos existem na saída de `/metrics` do app de teste; outro testa o formato (parser simples por linha) e os valores contra o trace gravado em um fluxo programado.
5. **README.** Seção Observability: o endpoint, as métricas, o arquivo de regras e como ligar um Prometheus local (duas linhas de `scrape_config`), sem prometer painel.

## Critérios de conclusão

- `/metrics` válido e coerente com o trace; sem dado pessoal nos rótulos.
- `alerts/rules.yml` com quatro regras sobre métricas existentes, testado.
- Suíte estrita verde; `checar-caminhos-pessoais.py` limpo.

## Validação

Developer, 2026-11-05, branch `codex/v0.10.0-rubrica-operacao`, base `023dc61` (o `b802c36` do Reviewer entrou no meio, só documentação). Commits `29add9c` (`metrics.py` e rota), `7638f18` (regras e testes), `2a561db` (README). Tudo com modelo programado, embedder de hash, Qdrant em memória e SQLite temporário; nenhuma chamada paga, `.env` não lido.

- Autenticação: `/ready` é público, então `/metrics` também é (sem token). O conteúdo são só contagens agregadas.
- `tests/integration/test_v0100_metrics.py` (novo, 8 testes): formato 0.0.4 por um parser de linha (`# HELP` e `# TYPE` uma vez por família e antes das amostras, nome de amostra dentro da família, rótulos bem formados, `Content-Type` exato); valores contra os traces de um fluxo programado (3 requisições em `knowledge`, `support` e `knowledge_and_support`, `get_device_status` em falha forçando 1 encaminhamento): `requests_total`, `handoffs_total`, `tool_calls_total`, `tool_failures_total`, `model_calls_total` por agente, `replan_total`, histograma (buckets cumulativos, `+Inf` = `_count`, `_sum`), `cost_usd_total`, `budget_remaining_usd` e `budget_limit_usd` iguais ao `BudgetGuard`; rótulos dentro de vocabulários fechados do código e sem `cliente1988`, `request_id` ou `conversation_id`; nome de ferramenta não registrado e rota com texto livre viram `other`; scrape não cria banco ausente; custo conta o liquidado e o restante desconta o reservado; cache de 5 s com relógio injetado; coerência: cada nome de métrica extraído das `expr` de `alerts/rules.yml` existe na saída de `/metrics`, quatro regras no grupo `merchant-assistant`, `summary`, `description` e `runbook_url` para `README.md#observability`.
- Focados: `test_v0100_metrics.py` + `test_health.py` com **10 passed**; `test_messages_contract.py`, `test_v1_api.py`, `test_v060_r4.py` e `test_v070_story.py` com **38 passed**. `ruff check` e `ruff format --check` limpos nos arquivos tocados.
- Suíte estrita: `python tools/scripts/lint_and_tests.py --strict` (`.venv`) com HEAD `2a561db`: **2132 passed, 1 skipped** em 960,31 s; ruff `All checks passed!`; caminhos pessoais: nenhuma ocorrência em 770 arquivos; estrutura e skills válidas; "Validação estrita concluída sem falhas", exit 0. Durante a rodada, outro escritor tinha alterações não commitadas em `cli.py`, `evaluation/`, `llm/prompts.py` e testes da tarefa 83, e a coleta incluiu essas alterações. Por isso o total é 2121 + 8 desta tarefa + 3 de lá.

## Status

Implementada pelo Developer em 2026-11-05; aguarda revisão independente e o `/metrics` ao vivo do QA (momento 6). Critérios de aceite da spec não marcados (cabe ao Supervisor).
