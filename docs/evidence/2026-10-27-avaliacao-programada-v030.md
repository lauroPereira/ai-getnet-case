# Relatório de avaliação: 2026-10-27-avaliacao-programada-v030

Gerado em 2026-10-27T03:36:53+00:00. Configuração: `{"mode": "scripted", "model": "scripted-v1", "split": "all", "cost_usd": 0.0, "cases": 40}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 40 | 0.625 | 0.975 | 1.0 | 1.0 | 1.0 | 0.625 | 1.0 | 1.0 | 198 | 478 | 0 |
| split dev | 23 | 0.696 | 1.0 | 1.0 | 1.0 | 1.0 | 0.696 | 1.0 | 1.0 | 214 | 478 | 0 |
| split holdout | 17 | 0.529 | 0.941 | 1.0 | 1.0 | 1.0 | 0.529 | 1.0 | 1.0 | 169 | 343 | 0 |
| idioma en | 21 | 0.667 | 1.0 | 1.0 | 1.0 | 1.0 | 0.667 | 1.0 | 1.0 | 194 | 305 | 0 |
| idioma pt | 19 | 0.579 | 0.947 | 1.0 | 1.0 | 1.0 | 0.579 | 1.0 | 1.0 | 210 | 510 | 0 |

## Casos

| Caso | Split | Rota | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EX01 | dev | knowledge | answered | não | content | 198 | 0.0 |
| EX02 | dev | general_web | answered | não | content | 158 | 0.0 |
| EX03 | dev | support | answered | sim | - | 232 | 0.0 |
| EX04 | dev | knowledge | answered | não | content | 305 | 0.0 |
| EX05 | dev | knowledge_and_support | answered | não | content | 320 | 0.0 |
| EX06 | dev | knowledge | answered | não | content | 251 | 0.0 |
| EX07 | dev | general_web | answered | sim | - | 150 | 0.0 |
| EX08 | dev | knowledge_and_support | answered | sim | - | 236 | 0.0 |
| EX09 | dev | knowledge | answered | não | content | 168 | 0.0 |
| EX10 | dev | knowledge | answered | não | content | 202 | 0.0 |
| PT01 | holdout | knowledge | answered | não | content | 181 | 0.0 |
| PT02 | holdout | general_web | answered | não | content | 217 | 0.0 |
| PT03 | holdout | support | answered | sim | - | 169 | 0.0 |
| PT04 | holdout | knowledge | answered | não | content | 156 | 0.0 |
| PT05 | holdout | knowledge_and_support | answered | não | content | 343 | 0.0 |
| PT06 | holdout | knowledge | answered | não | content | 173 | 0.0 |
| PT07 | holdout | general_web | answered | sim | - | 164 | 0.0 |
| PT08 | holdout | knowledge_and_support | answered | sim | - | 202 | 0.0 |
| PT09 | holdout | knowledge | answered | não | content | 157 | 0.0 |
| PT10 | holdout | knowledge | answered | não | content | 165 | 0.0 |
| UC12 | holdout | out_of_scope | refused | sim | - | 121 | 0.0 |
| UC13 | holdout | support | answered | sim | - | 186 | 0.0 |
| UC14 | holdout | human_handoff | handoff | sim | - | 210 | 0.0 |
| UC16 | holdout | out_of_scope | refused | sim | - | 94 | 0.0 |
| UC17 | holdout | support | answered | sim | - | 140 | 0.0 |
| UC18 | holdout | clarify | needs_clarification | sim | - | 158 | 0.0 |
| NOEV | holdout | support | answered | não | route, content | 714 | 0.0 |
| V030-PRICE-CONSISTENT | dev | support | answered | sim | - | 192 | 0.0 |
| V030-PRICE-CONDITIONS | dev | support | answered | sim | - | 171 | 0.0 |
| V030-PRICE-DIVERGENCE | dev | support | handoff | sim | - | 249 | 0.0 |
| V030-PRICE-INSUFFICIENT | dev | support | answered | sim | - | 198 | 0.0 |
| V030-ENABLEMENT-PENDING | dev | support | answered | sim | - | 184 | 0.0 |
| V030-SALE-CANCELLATION | dev | support | answered | sim | - | 200 | 0.0 |
| V030-CONTRACT-TERMINATION | dev | human_handoff | handoff | sim | - | 194 | 0.0 |
| V030-PT-PRICE-CONSISTENT | dev | support | answered | sim | - | 214 | 0.0 |
| V030-PT-PRICE-CONDITIONS | dev | support | answered | sim | - | 478 | 0.0 |
| V030-PT-PRICE-DIVERGENCE | dev | support | handoff | sim | - | 510 | 0.0 |
| V030-PT-PRICE-INSUFFICIENT | dev | support | answered | sim | - | 352 | 0.0 |
| V030-PT-ENABLEMENT-PENDING | dev | support | answered | sim | - | 347 | 0.0 |
| V030-PT-SALE-CANCELLATION | dev | support | answered | sim | - | 371 | 0.0 |

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
