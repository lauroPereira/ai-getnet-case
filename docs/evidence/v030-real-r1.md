# Relatório de avaliação: v030-real-r1

Gerado em 2026-10-27T04:02:40+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "embedding": "text-embedding-3-small", "judge": true, "cases": 40, "additional_budget_limit_usd": 0.15}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 40 | 0.775 | 0.975 | 0.975 | 0.975 | 0.95 | 0.775 | 0.975 | 0.95 | 9389 | 16488 | 0.0593 |
| split dev | 23 | 0.652 | 0.957 | 0.957 | 0.957 | 0.957 | 0.652 | 0.957 | 0.913 | 9406 | 13540 | 0.03093 |
| split holdout | 17 | 0.941 | 1.0 | 1.0 | 1.0 | 0.941 | 0.941 | 1.0 | 1.0 | 7263 | 16488 | 0.02837 |
| idioma en | 21 | 0.857 | 1.0 | 1.0 | 1.0 | 1.0 | 0.857 | 1.0 | 0.952 | 9392 | 13540 | 0.0299 |
| idioma pt | 19 | 0.684 | 0.947 | 0.947 | 0.947 | 0.895 | 0.684 | 0.947 | 0.947 | 9386 | 16488 | 0.0294 |

Rubrica por modelo (média 1-5, não é revisão humana): responde à pergunta 4.2, clareza e tom 4.75, honestidade 4.4.

## Casos

| Caso | Split | Rota | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EX01 | dev | knowledge | answered | sim | - | 12020 | 0.0007346 |
| EX02 | dev | general_web | answered | sim | - | 8078 | 0.01072712 |
| EX03 | dev | support | answered | sim | - | 12017 | 0.00063496 |
| EX04 | dev | knowledge | answered | sim | - | 8794 | 0.00042922 |
| EX05 | dev | knowledge_and_support | answered | sim | - | 13540 | 0.00082091 |
| EX06 | dev | knowledge | answered | sim | - | 8911 | 0.00052882 |
| EX07 | dev | general_web | answered | sim | - | 9296 | 0.01063825 |
| EX08 | dev | knowledge_and_support | answered | sim | - | 20929 | 0.00098709 |
| EX09 | dev | knowledge | answered | sim | - | 7196 | 0.00036992 |
| EX10 | dev | knowledge | answered | sim | - | 7165 | 0.00038862 |
| PT01 | holdout | knowledge | answered | sim | - | 9896 | 0.00057612 |
| PT02 | holdout | general_web | answered | sim | - | 7263 | 0.01072742 |
| PT03 | holdout | support | answered | sim | - | 12008 | 0.00062676 |
| PT04 | holdout | knowledge | answered | sim | - | 7558 | 0.00046532 |
| PT05 | holdout | knowledge_and_support | answered | sim | - | 16488 | 0.00105543 |
| PT06 | holdout | knowledge | answered | sim | - | 11206 | 0.00060092 |
| PT07 | holdout | general_web | answered | sim | - | 11483 | 0.01065416 |
| PT08 | holdout | knowledge_and_support | answered | não | amounts, content | 17283 | 0.00096292 |
| PT09 | holdout | knowledge | answered | sim | - | 6292 | 0.00037522 |
| PT10 | holdout | knowledge | answered | sim | - | 7090 | 0.00037552 |
| UC12 | holdout | out_of_scope | refused | sim | - | 4301 | 0.00012152 |
| UC13 | holdout | support | answered | sim | - | 12560 | 0.00075585 |
| UC14 | holdout | human_handoff | handoff | sim | - | 6500 | 0.00030202 |
| UC16 | holdout | out_of_scope | refused | sim | - | 1551 | 7.93e-05 |
| UC17 | holdout | support | answered | sim | - | 3913 | 0.00013056 |
| UC18 | holdout | clarify | needs_clarification | sim | - | 4220 | 0.00010792 |
| NOEV | holdout | knowledge | answered | sim | - | 6847 | 0.00045242 |
| V030-PRICE-CONSISTENT | dev | support | answered | sim | - | 8575 | 0.00047615 |
| V030-PRICE-CONDITIONS | dev | support | answered | não | content | 9392 | 0.00033228 |
| V030-PRICE-DIVERGENCE | dev | support | handoff | não | content, grounded | 13427 | 0.00051028 |
| V030-PRICE-INSUFFICIENT | dev | support | answered | não | content | 9450 | 0.00046308 |
| V030-ENABLEMENT-PENDING | dev | support | answered | sim | - | 10513 | 0.0002374 |
| V030-SALE-CANCELLATION | dev | support | answered | sim | - | 9406 | 0.00023899 |
| V030-CONTRACT-TERMINATION | dev | human_handoff | handoff | sim | - | 10652 | 0.00029102 |
| V030-PT-PRICE-CONSISTENT | dev | support | answered | não | content | 11662 | 0.00046079 |
| V030-PT-PRICE-CONDITIONS | dev | support | answered | não | content | 11280 | 0.00032702 |
| V030-PT-PRICE-DIVERGENCE | dev | support | handoff | não | amounts, content, grounded | 12673 | 0.0005218 |
| V030-PT-PRICE-INSUFFICIENT | dev | clarify | needs_clarification | não | route, status, tools, content, sources | 7165 | 0.00012882 |
| V030-PT-ENABLEMENT-PENDING | dev | support | answered | sim | - | 9386 | 0.00042767 |
| V030-PT-SALE-CANCELLATION | dev | support | answered | não | content | 7426 | 0.00025331 |

## Conversas de vários turnos

4 de 4 conversas aprovadas em todos os turnos.

| Conversa | Turno | Rota | Status | Caso | Aprovado | Falhas |
| --- | --- | --- | --- | --- | --- | --- |
| FU01 | 1 | knowledge_and_support | answered | awaiting_customer | sim | - |
| FU01 | 2 | acknowledgement | answered | resolved | sim | - |
| FU02 | 1 | knowledge_and_support | answered | awaiting_customer | sim | - |
| FU02 | 2 | knowledge_and_support | handoff | handoff | sim | - |
| FU02 | 3 | knowledge_and_support | handoff | handoff | sim | - |
| FU03 | 1 | knowledge | answered | awaiting_customer | sim | - |
| FU03 | 2 | acknowledgement | answered | awaiting_customer | sim | - |
| FU04 | 1 | knowledge_and_support | answered | awaiting_customer | sim | - |
| FU04 | 2 | human_handoff | handoff | handoff | sim | - |
| FU04 | 3 | human_handoff | handoff | handoff | sim | - |
