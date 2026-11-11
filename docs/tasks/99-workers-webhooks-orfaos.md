# Tarefa 99 — Múltiplos workers, reenvio de webhook e caso órfão

## Objetivo

A API roda com dois workers sem estado por processo; entregas esgotadas podem ser reenviadas; casos abertos sem ticket são completados na subida.

## Especificação relacionada

[v0.13.0](../specs/identidade-operacao-v0130.md): D4, D5, CA-70, CA-71. Plano: [decisões 17 e 18](../specs/roadmap-v0110-v100-plano.md). ADRs 0018 e 0022.

## Pré-condições

Migração 0015 aplicada; a migração **0016** acrescenta os leases e a recuperação dos webhooks à cadeia existente.

## Arquivos prováveis

`comparisons.py` (lease), `handoffs.py` (locks por processo; `recover_orphans`), `api/webhooks.py` e `data/webhook_outbox.py` (`exhausted`, reenvio), `api/v1.py` (rota de reenvio, aditiva), `data/migrations.py` (0016), `docker/entrypoint.sh` e `docker-compose.yml` (`--workers 2`), `api/app.py` (subida), testes.

## Passos

1. Migração 0016 reversível: `comparisons.worker_id`, `comparisons.heartbeat_at`; `webhook_outbox.status` aceita `exhausted`; `webhook_outbox.resend_count`.
2. Lease: a thread renova o heartbeat a cada 5 s; órfã com heartbeat há mais de 20 s; retomada reivindica em `BEGIN IMMEDIATE`; o registro em memória sai; a janela entre leitura e reivindicação deixa de existir.
3. Locks por caso em memória saem onde `BEGIN IMMEDIATE` já serializa; WAL confirmado na abertura.
4. `exhausted`, reenvio manual com escopo de operador, reenvio automático na subida para esgotadas há mais de 1 h; eventos posteriores do mesmo destino deixam de ficar presos.
5. `recover_orphans()` na subida.
6. Compose e entrypoint com `--workers 2` (o comentário do entrypoint muda).
7. Testes: dois processos reais com uma comparação; o dono é morto no meio; o outro retoma só as células que faltam; ledger sem célula duplicada; rate limit, handoffs e outbox com dois processos; reenvio; caso órfão; migração nos dois sentidos.

## Critérios de conclusão

- CA-70 e CA-71 cobertos por testes; suíte estrita verde.

## Resultado

Dono de uma comparação suspenso antes e depois da reserva paga: nenhuma célula paga duas vezes. Reenvio de webhook e caso órfão validados no sistema com Docker.
Evidência: [resultado da v0.13.0](../evidence/v0130-resultado.md).

## Status

```text
concluída (v0.13.0)
```
