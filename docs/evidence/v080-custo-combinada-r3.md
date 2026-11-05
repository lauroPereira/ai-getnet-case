# Relatório de avaliação: v080-custo-combinada-r3

Gerado em 2026-11-04T22:41:50+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "dev", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 1, "limit": null, "include_replan": true, "campaign": null, "campaign_cap_usd": null, "cases": 11, "conversations_included": false, "combined_source_reports": ["v080-custo-combinada-r2.json", "v080-price-retry-r3.json"], "combination_method": "retain original valid sample rows; substitute each environment-invalid pricing attempt with its single complete valid retry by case ID; prior failed attempts remain in their separate original artifact and ledger costs remain charged", "attempts_preserved_separately": ["v080-custo-combinada-r2.json", "v080-price-retry-r3.json"]}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 11 | 0.727 | 0.909 | 0.909 | 1.0 | 1.0 | 0.727 | 1.0 | 1.0 | 12317 | 18582 | 0.04004 |
| split dev | 11 | 0.727 | 0.909 | 0.909 | 1.0 | 1.0 | 0.727 | 1.0 | 1.0 | 12317 | 18582 | 0.04004 |
| idioma en | 6 | 0.667 | 0.833 | 0.833 | 1.0 | 1.0 | 0.667 | 1.0 | 1.0 | 9825 | 15319 | 0.01444 |
| idioma pt | 5 | 0.8 | 1.0 | 1.0 | 1.0 | 1.0 | 0.8 | 1.0 | 1.0 | 12504 | 18582 | 0.0256 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 4.82, correção factual 4.82, relevância 4.73, utilidade 4.73. Afirmações sem suporte: 0.0 das respostas julgadas. Custo do juiz: US$ 0.00642.

Respostas julgadas sob a nota de busca web: 3 de 11. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 0 foram marcadas como afirmação sem suporte.

Evidência truncada em 1 de 11 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| clarify | - | 1 |
| general_web | knowledge | 1 |
| knowledge | knowledge | 1 |
| knowledge | knowledge → customer_support → web | 1 |
| knowledge | knowledge → web | 1 |
| knowledge_and_support | knowledge → customer_support | 2 |
| support | customer_support | 2 |
| support | customer_support → escalation | 2 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REPLAN-WEB | 1 | dev | knowledge | knowledge → web | answered | sim | - | 12317 | 0.0116089 |
| REPLAN-PROCEDURE | 1 | dev | knowledge_and_support | knowledge → customer_support | answered | não | content | 18582 | 0.00130939 |
| REPLAN-TOOL-DOWN | 1 | dev | support | customer_support → escalation | handoff | sim | - | 12504 | 0.00061087 |
| REPLAN-ACCOUNT | 1 | dev | knowledge | knowledge → customer_support → web | answered | sim | - | 17478 | 0.01154691 |
| EX01 | 1 | dev | knowledge | knowledge | answered | sim | - | 8507 | 0.00056127 |
| EX02 | 1 | dev | general_web | knowledge | answered | sim | - | 8263 | 0.0110205 |
| EX03 | 1 | dev | support | customer_support | answered | sim | - | 11143 | 0.00068469 |
| EX05 | 1 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 14062 | 0.00103332 |
| V030-PRICE-DIVERGENCE | 1 | dev | support | customer_support → escalation | handoff | não | content | 15319 | 0.00099217 |
| V030-CONTRACT-TERMINATION | 1 | dev | clarify | - | needs_clarification | não | route, status, content | 3153 | 0.00015007 |
| V030-PT-PRICE-INSUFFICIENT | 1 | dev | support | customer_support | answered | sim | - | 6702 | 0.0005245 |
