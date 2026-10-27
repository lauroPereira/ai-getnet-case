# Relatório de avaliação: 2026-10-26-avaliacao-nucleo

Gerado em 2026-10-27T00:09:44+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "embedding": "text-embedding-3-small", "split": "all", "judge": true, "cases": 27, "rescored": "EX03/PT03 content check widened after run (evaluator false negative)"}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 27 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 7763 | 15679 | 0.05129 |
| split dev | 10 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 8439 | 15679 | 0.02461 |
| split holdout | 17 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 6913 | 12403 | 0.02668 |
| idioma en | 14 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 8056 | 12616 | 0.02573 |
| idioma pt | 13 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 7443 | 12403 | 0.02556 |

Rubrica por modelo (média 1-5, não é revisão humana): responde à pergunta 4.48, clareza e tom 4.7, honestidade 4.22.

## Casos

| Caso | Split | Rota | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EX01 | dev | knowledge | answered | sim | - | 12616 | 0.00047791 |
| EX02 | dev | general_web | answered | sim | - | 8528 | 0.01037076 |
| EX03 | dev | support | answered | sim | - | 9210 | 0.00057698 |
| EX04 | dev | knowledge | answered | sim | - | 7763 | 0.00028769 |
| EX05 | dev | knowledge_and_support | answered | sim | - | 9390 | 0.00053787 |
| EX06 | dev | knowledge | answered | sim | - | 8350 | 0.00040478 |
| EX07 | dev | general_web | answered | sim | - | 6701 | 0.01069154 |
| EX08 | dev | knowledge_and_support | answered | sim | - | 15679 | 0.00079145 |
| EX09 | dev | knowledge | answered | sim | - | 5729 | 0.00022654 |
| EX10 | dev | knowledge | answered | sim | - | 5585 | 0.0002413 |
| PT01 | holdout | knowledge | answered | sim | - | 8861 | 0.00037409 |
| PT02 | holdout | general_web | answered | sim | - | 6451 | 0.01038148 |
| PT03 | holdout | support | answered | sim | - | 9258 | 0.00058448 |
| PT04 | holdout | knowledge | answered | sim | - | 8790 | 0.0003459 |
| PT05 | holdout | knowledge_and_support | answered | sim | - | 16299 | 0.00078173 |
| PT06 | holdout | knowledge | answered | sim | - | 9169 | 0.00040726 |
| PT07 | holdout | general_web | answered | sim | - | 7443 | 0.01070106 |
| PT08 | holdout | knowledge_and_support | answered | sim | - | 12403 | 0.00069173 |
| PT09 | holdout | knowledge | answered | sim | - | 6913 | 0.00026541 |
| PT10 | holdout | knowledge | answered | sim | - | 5841 | 0.00024603 |
| UC12 | holdout | out_of_scope | refused | sim | - | 3835 | 0.0001756 |
| UC13 | holdout | support | answered | sim | - | 12289 | 0.0006894 |
| UC14 | holdout | human_handoff | handoff | sim | - | 5440 | 0.000352 |
| UC16 | holdout | out_of_scope | refused | sim | - | 1418 | 6.61e-05 |
| UC17 | holdout | support | answered | sim | - | 3138 | 0.0001888 |
| UC18 | holdout | clarify | needs_clarification | sim | - | 3114 | 0.0001636 |
| NOEV | holdout | knowledge | answered | sim | - | 6322 | 0.00026836 |
