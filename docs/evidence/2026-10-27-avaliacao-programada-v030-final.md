# Relatório de avaliação: 2026-10-27-avaliacao-programada-v030-final

Gerado em 2026-10-27T03:40:14+00:00. Configuração: `{"mode": "scripted", "model": "scripted-v1", "split": "all", "cost_usd": 0.0, "cases": 40}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 40 | 0.625 | 1.0 | 1.0 | 1.0 | 1.0 | 0.625 | 1.0 | 1.0 | 190 | 424 | 0 |
| split dev | 23 | 0.696 | 1.0 | 1.0 | 1.0 | 1.0 | 0.696 | 1.0 | 1.0 | 220 | 395 | 0 |
| split holdout | 17 | 0.529 | 1.0 | 1.0 | 1.0 | 1.0 | 0.529 | 1.0 | 1.0 | 154 | 424 | 0 |
| idioma en | 21 | 0.667 | 1.0 | 1.0 | 1.0 | 1.0 | 0.667 | 1.0 | 1.0 | 247 | 395 | 0 |
| idioma pt | 19 | 0.579 | 1.0 | 1.0 | 1.0 | 1.0 | 0.579 | 1.0 | 1.0 | 168 | 424 | 0 |

## Casos

| Caso | Split | Rota | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EX01 | dev | knowledge | answered | não | content | 312 | 0.0 |
| EX02 | dev | general_web | answered | não | content | 393 | 0.0 |
| EX03 | dev | support | answered | sim | - | 395 | 0.0 |
| EX04 | dev | knowledge | answered | não | content | 360 | 0.0 |
| EX05 | dev | knowledge_and_support | answered | não | content | 484 | 0.0 |
| EX06 | dev | knowledge | answered | não | content | 309 | 0.0 |
| EX07 | dev | general_web | answered | sim | - | 247 | 0.0 |
| EX08 | dev | knowledge_and_support | answered | sim | - | 381 | 0.0 |
| EX09 | dev | knowledge | answered | não | content | 382 | 0.0 |
| EX10 | dev | knowledge | answered | não | content | 358 | 0.0 |
| PT01 | holdout | knowledge | answered | não | content | 362 | 0.0 |
| PT02 | holdout | general_web | answered | não | content | 327 | 0.0 |
| PT03 | holdout | support | answered | sim | - | 424 | 0.0 |
| PT04 | holdout | knowledge | answered | não | content | 364 | 0.0 |
| PT05 | holdout | knowledge_and_support | answered | não | content | 501 | 0.0 |
| PT06 | holdout | knowledge | answered | não | content | 249 | 0.0 |
| PT07 | holdout | general_web | answered | sim | - | 129 | 0.0 |
| PT08 | holdout | knowledge_and_support | answered | sim | - | 155 | 0.0 |
| PT09 | holdout | knowledge | answered | não | content | 154 | 0.0 |
| PT10 | holdout | knowledge | answered | não | content | 127 | 0.0 |
| UC12 | holdout | out_of_scope | refused | sim | - | 114 | 0.0 |
| UC13 | holdout | support | answered | sim | - | 140 | 0.0 |
| UC14 | holdout | human_handoff | handoff | sim | - | 182 | 0.0 |
| UC16 | holdout | out_of_scope | refused | sim | - | 79 | 0.0 |
| UC17 | holdout | support | answered | sim | - | 87 | 0.0 |
| UC18 | holdout | clarify | needs_clarification | sim | - | 87 | 0.0 |
| NOEV | holdout | knowledge | answered | não | content | 123 | 0.0 |
| V030-PRICE-CONSISTENT | dev | support | answered | sim | - | 296 | 0.0 |
| V030-PRICE-CONDITIONS | dev | support | answered | sim | - | 147 | 0.0 |
| V030-PRICE-DIVERGENCE | dev | support | handoff | sim | - | 199 | 0.0 |
| V030-PRICE-INSUFFICIENT | dev | support | answered | sim | - | 144 | 0.0 |
| V030-ENABLEMENT-PENDING | dev | support | answered | sim | - | 124 | 0.0 |
| V030-SALE-CANCELLATION | dev | support | answered | sim | - | 124 | 0.0 |
| V030-CONTRACT-TERMINATION | dev | human_handoff | handoff | sim | - | 143 | 0.0 |
| V030-PT-PRICE-CONSISTENT | dev | support | answered | sim | - | 163 | 0.0 |
| V030-PT-PRICE-CONDITIONS | dev | support | answered | sim | - | 168 | 0.0 |
| V030-PT-PRICE-DIVERGENCE | dev | support | handoff | sim | - | 220 | 0.0 |
| V030-PT-PRICE-INSUFFICIENT | dev | support | answered | sim | - | 198 | 0.0 |
| V030-PT-ENABLEMENT-PENDING | dev | support | answered | sim | - | 161 | 0.0 |
| V030-PT-SALE-CANCELLATION | dev | support | answered | sim | - | 116 | 0.0 |

## Conversas de vários turnos

4 de 4 conversas aprovadas em todos os turnos.

| Conversa | Turno | Rota | Status | Caso | Aprovado | Falhas |
| --- | --- | --- | --- | --- | --- | --- |
| FU01 | 1 | knowledge_and_support | answered | awaiting_customer | sim | - |
| FU01 | 2 | acknowledgement | answered | resolved | sim | - |
| FU02 | 1 | knowledge_and_support | answered | awaiting_customer | sim | - |
| FU02 | 2 | knowledge_and_support | answered | awaiting_customer | sim | - |
| FU02 | 3 | knowledge_and_support | handoff | handoff | sim | - |
| FU03 | 1 | knowledge | answered | awaiting_customer | sim | - |
| FU03 | 2 | acknowledgement | answered | awaiting_customer | sim | - |
| FU04 | 1 | knowledge_and_support | answered | awaiting_customer | sim | - |
| FU04 | 2 | human_handoff | handoff | handoff | sim | - |
| FU04 | 3 | clarify | needs_clarification | handoff | sim | - |
