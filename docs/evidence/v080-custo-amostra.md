# Relatório de avaliação: v080-custo-amostra

Gerado em 2026-11-04T17:40:43+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "dev", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 1, "limit": 5, "include_replan": true, "campaign": null, "campaign_cap_usd": null, "cases": 5}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 5 | 0.8 | 1.0 | 1.0 | 1.0 | 1.0 | 0.8 | 1.0 | 1.0 | 12504 | 18582 | 0.02564 |
| split dev | 5 | 0.8 | 1.0 | 1.0 | 1.0 | 1.0 | 0.8 | 1.0 | 1.0 | 12504 | 18582 | 0.02564 |
| idioma en | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 8507 | 8507 | 0.00056 |
| idioma pt | 4 | 0.75 | 1.0 | 1.0 | 1.0 | 1.0 | 0.75 | 1.0 | 1.0 | 14991 | 18582 | 0.02508 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 5.0, correção factual 5.0, relevância 4.6, utilidade 4.8. Afirmações sem suporte: 0.0 das respostas julgadas. Custo do juiz: US$ 0.00312.

Respostas julgadas sob a nota de busca web: 2 de 5. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 0 foram marcadas como afirmação sem suporte.

Evidência truncada em 1 de 5 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| knowledge | knowledge | 1 |
| knowledge | knowledge → customer_support → web | 1 |
| knowledge | knowledge → web | 1 |
| knowledge_and_support | knowledge → customer_support | 1 |
| support | customer_support → escalation | 1 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REPLAN-WEB | 1 | dev | knowledge | knowledge → web | answered | sim | - | 12317 | 0.0116089 |
| REPLAN-PROCEDURE | 1 | dev | knowledge_and_support | knowledge → customer_support | answered | não | content | 18582 | 0.00130939 |
| REPLAN-TOOL-DOWN | 1 | dev | support | customer_support → escalation | handoff | sim | - | 12504 | 0.00061087 |
| REPLAN-ACCOUNT | 1 | dev | knowledge | knowledge → customer_support → web | answered | sim | - | 17478 | 0.01154691 |
| EX01 | 1 | dev | knowledge | knowledge | answered | sim | - | 8507 | 0.00056127 |
