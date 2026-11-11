# Tarefa 94 — Cancelamento de venda com confirmação

## Objetivo

O assistente pode solicitar o cancelamento de uma venda, mas só conclui a escrita depois de mostrar o que será cancelado e receber confirmação explícita do lojista. A operação é idempotente e auditada.

## Especificação relacionada

[v0.12.0](../specs/memoria-escrita-v0120.md): D5, D6, CA-67. Plano: [decisão 13](../specs/roadmap-v0110-v100-plano.md).

## Arquivos prováveis

`data/migrations.py`, `tools/domain.py`, `tools/registry.py`, `api/identity.py`, `agents/router.py`, `prompts/router.v7.md`, `prompts/support.v9.md`, `orchestration/graph.py`, catálogo de cenários e testes.

## Passos

1. Adicionar `sale_cancellation_requests` na migração 0014 e implementar operações idempotentes com estados `pending_confirmation`, `confirmed`, `declined` e `expired`.
2. Conceder `support:write` apenas a tokens de lojista. Validar a confirmação em código contra o pedido pendente; texto ambíguo como “sim, mas…” não confirma. Expirar o pedido depois de dois turnos sem resposta.
3. Mostrar venda, valor e data antes de pedir confirmação. Manter funções de confirmação fora das listas de ferramentas do modelo e executá-las no fluxo da conversa.
4. Restringir a venda ao próprio lojista, deixar a conta intacta até um sim explícito e auditar tentativas e resultados.
5. Cobrir com testes roteirizados confirmação, recusa, silêncio, repetição idempotente, acesso entre lojistas e escopo ausente.

## Critérios de conclusão

- CA-67 coberto por testes roteirizados; nenhuma escrita ocorre sem confirmação explícita.
- Repetições retornam o mesmo pedido e protocolo; recusa ou expiração deixa a conta intacta.
- Restrições da migração e adições da API preservam o comportamento de leitura existente.

## Resultado

Cancelamento só com confirmação explícita; confirmação, idempotência, recusa, expiração e isolamento entre lojistas verificados.
Evidência: [resultado da v0.12.0](../evidence/v0120-resultado.md).

## Status

```text
concluída (v0.12.0)
```
