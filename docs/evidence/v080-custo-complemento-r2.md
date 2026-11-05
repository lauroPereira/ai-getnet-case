# Relatório de avaliação: v080-custo-complemento-r2

Gerado em 2026-11-04T18:44:14+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "dev", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 1, "limit": 6, "include_replan": true, "campaign": null, "campaign_cap_usd": null, "cases": 6}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 6 | 0.5 | 0.833 | 0.667 | 1.0 | 0.833 | 0.5 | 0.667 | 1.0 | 11792 | 14062 | 0.01411 |
| split dev | 6 | 0.5 | 0.833 | 0.667 | 1.0 | 0.833 | 0.5 | 0.667 | 1.0 | 11792 | 14062 | 0.01411 |
| idioma en | 5 | 0.6 | 0.8 | 0.8 | 1.0 | 0.8 | 0.6 | 0.8 | 1.0 | 11143 | 14062 | 0.01348 |
| idioma pt | 1 | 0.0 | 1.0 | 0.0 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 12730 | 12730 | 0.00063 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 4.33, correção factual 4.5, relevância 4.83, utilidade 4.83. Afirmações sem suporte: 0.167 das respostas julgadas. Custo do juiz: US$ 0.00286.

Respostas julgadas sob a nota de busca web: 1 de 6. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 0 foram marcadas como afirmação sem suporte.

Evidência truncada em 0 de 6 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Afirmações sem suporte (veredito crítico)

Listadas uma a uma, nunca diluídas na média.

| Caso | Rep | Rota | Julgamentos marcados | Fundamentação (primeiro julgamento marcado) |
| --- | --- | --- | --- | --- |
| V030-PRICE-DIVERGENCE | 1 | support | 1 de 1 | The pricing service unavailability and handoff are supported, but the protocol number isn't in the evidence. |

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| clarify | - | 1 |
| general_web | knowledge | 1 |
| knowledge_and_support | knowledge → customer_support | 1 |
| support | customer_support | 1 |
| support | customer_support → escalation | 2 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EX02 | 1 | dev | general_web | knowledge | answered | sim | - | 8263 | 0.0110205 |
| EX03 | 1 | dev | support | customer_support | answered | sim | - | 11143 | 0.00068469 |
| EX05 | 1 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 14062 | 0.00103332 |
| V030-PRICE-DIVERGENCE | 1 | dev | support | customer_support → escalation | handoff | não | amounts, content, sources | 12441 | 0.00059194 |
| V030-CONTRACT-TERMINATION | 1 | dev | clarify | - | needs_clarification | não | route, status, content | 3153 | 0.00015007 |
| V030-PT-PRICE-INSUFFICIENT | 1 | dev | support | customer_support → escalation | handoff | não | status, content, sources | 12730 | 0.0006262 |
