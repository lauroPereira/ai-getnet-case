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

(Preenchida pelo Developer.)

## Status

Pendente. Aberta pelo Supervisor em 2026-11-05.
