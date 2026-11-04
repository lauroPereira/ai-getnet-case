# Relatório de avaliação: v070-qa-regressao-real

Gerado em 2026-11-04T04:06:15+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "embedding": "text-embedding-3-small", "split": "all", "judge": true, "cases": 40}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 40 | 0.825 | 0.95 | 0.95 | 0.95 | 1.0 | 0.85 | 0.95 | 1.0 | 7418 | 13926 | 0.06066 |
| split dev | 23 | 0.696 | 0.913 | 0.913 | 0.913 | 1.0 | 0.739 | 0.913 | 1.0 | 7597 | 13617 | 0.03171 |
| split holdout | 17 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 7240 | 13926 | 0.02894 |
| idioma en | 21 | 0.762 | 0.952 | 0.952 | 0.952 | 1.0 | 0.762 | 0.952 | 1.0 | 7597 | 13617 | 0.03049 |
| idioma pt | 19 | 0.895 | 0.947 | 0.947 | 0.947 | 1.0 | 0.947 | 0.947 | 1.0 | 7240 | 13926 | 0.03016 |

Rubrica por modelo (média 1-5, não é revisão humana): responde à pergunta 4.4, clareza e tom 4.72, honestidade 4.47.

## Casos

| Caso | Split | Rota | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EX01 | dev | knowledge | answered | sim | - | 11000 | 0.0007038 |
| EX02 | dev | general_web | answered | sim | - | 6058 | 0.01097026 |
| EX03 | dev | support | answered | sim | - | 9942 | 0.00065358 |
| EX04 | dev | knowledge | answered | sim | - | 7597 | 0.00043056 |
| EX05 | dev | knowledge_and_support | answered | sim | - | 13617 | 0.00097203 |
| EX06 | dev | knowledge | answered | sim | - | 8004 | 0.00055086 |
| EX07 | dev | general_web | answered | sim | - | 6545 | 0.01065409 |
| EX08 | dev | knowledge_and_support | answered | sim | - | 14662 | 0.00104445 |
| EX09 | dev | knowledge | answered | sim | - | 5302 | 0.00038196 |
| EX10 | dev | knowledge | answered | sim | - | 5410 | 0.00038426 |
| PT01 | holdout | knowledge | answered | sim | - | 8404 | 0.00059606 |
| PT02 | holdout | general_web | answered | sim | - | 5503 | 0.01098016 |
| PT03 | holdout | support | answered | sim | - | 8517 | 0.00065548 |
| PT04 | holdout | knowledge | answered | sim | - | 6989 | 0.00045926 |
| PT05 | holdout | knowledge_and_support | answered | sim | - | 13926 | 0.00101079 |
| PT06 | holdout | knowledge | answered | sim | - | 10601 | 0.00059276 |
| PT07 | holdout | general_web | answered | sim | - | 8442 | 0.0106675 |
| PT08 | holdout | knowledge_and_support | answered | sim | - | 15967 | 0.00107065 |
| PT09 | holdout | knowledge | answered | sim | - | 8690 | 0.00041696 |
| PT10 | holdout | knowledge | answered | sim | - | 6625 | 0.00045036 |
| UC12 | holdout | out_of_scope | refused | sim | - | 4625 | 0.00013236 |
| UC13 | holdout | support | answered | sim | - | 10717 | 0.00074547 |
| UC14 | holdout | human_handoff | handoff | sim | - | 5716 | 0.00033076 |
| UC16 | holdout | out_of_scope | refused | sim | - | 1263 | 8.77e-05 |
| UC17 | holdout | support | answered | sim | - | 3046 | 0.0001419 |
| UC18 | holdout | clarify | needs_clarification | sim | - | 3576 | 0.00012086 |
| NOEV | holdout | knowledge | answered | sim | - | 7240 | 0.00048466 |
| V030-PRICE-CONSISTENT | dev | support | answered | não | content | 7744 | 0.00055593 |
| V030-PRICE-CONDITIONS | dev | clarify | needs_clarification | não | route, status, tools, content, sources | 3285 | 0.00012526 |
| V030-PRICE-DIVERGENCE | dev | support | handoff | não | content | 11586 | 0.0006235 |
| V030-PRICE-INSUFFICIENT | dev | support | answered | sim | - | 7732 | 0.00031053 |
| V030-ENABLEMENT-PENDING | dev | support | answered | não | content | 6510 | 0.00026402 |
| V030-SALE-CANCELLATION | dev | support | answered | sim | - | 7899 | 0.00044024 |
| V030-CONTRACT-TERMINATION | dev | human_handoff | handoff | não | content | 5189 | 0.00032036 |
| V030-PT-PRICE-CONSISTENT | dev | support | answered | sim | - | 6877 | 0.00055357 |
| V030-PT-PRICE-CONDITIONS | dev | clarify | needs_clarification | não | route, status, tools, sources | 2694 | 0.00013116 |
| V030-PT-PRICE-DIVERGENCE | dev | support | handoff | sim | - | 11151 | 0.00061152 |
| V030-PT-PRICE-INSUFFICIENT | dev | support | answered | não | content | 9772 | 0.00032037 |
| V030-PT-ENABLEMENT-PENDING | dev | support | answered | sim | - | 6717 | 0.00025713 |
| V030-PT-SALE-CANCELLATION | dev | support | answered | sim | - | 6770 | 0.00045275 |

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
| FU04 | 3 | support | answered | handoff | sim | - |
