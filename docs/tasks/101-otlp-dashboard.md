# Tarefa 101 — Telemetria OTLP e dashboard

## Objetivo

Exportação OTLP opcional dos spans e um dashboard versionado sobre `/metrics`.

## Especificação relacionada

[v0.13.0](../specs/identidade-operacao-v0130.md): D6, CA-72. Plano: [decisão 19](../specs/roadmap-v0110-v100-plano.md). ADR 0022.

## Pré-condições

Traces da API e métricas `/metrics` disponíveis; a exportação fica desligada sem endpoint configurado.

## Arquivos prováveis

`observability/otel.py` (novo), `pyproject.toml` (extra `[otel]`), `observability/grafana/assistant.json` (novo), `docker-compose.yml` (coletor e Grafana por perfil `otel`), `docker/otel/collector.yaml`, `.env.example` (`OTEL_EXPORTER_OTLP_ENDPOINT` vazio), testes.

## Passos

1. Spans por passo do trace já existente, com atributos só de conjuntos fechados (rota, status, agente, origem do replanejamento); sem texto de mensagem nem id de lojista.
2. Sem o extra ou sem endpoint, nada muda.
3. Dashboard com mistura de rotas, p95, custo por provedor, orçamento, encaminhamentos e origens do replanejamento; consultas só sobre métricas que existem em `/metrics` (teste confere).
4. Testes com exportador em memória: um span por passo; atributos fechados; nada exportado sem configuração.

## Critérios de conclusão

- CA-72 coberto por testes; dashboard válido; suíte estrita verde.
