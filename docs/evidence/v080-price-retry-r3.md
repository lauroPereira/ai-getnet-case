# Relatório de avaliação: v080-price-retry-r3

Gerado em 2026-11-04T22:38:42+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "dev", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 1, "limit": null, "include_replan": false, "campaign": null, "campaign_cap_usd": null, "cases": 2}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 2 | 0.5 | 1.0 | 1.0 | 1.0 | 1.0 | 0.5 | 1.0 | 1.0 | 11010 | 15319 | 0.00152 |
| split dev | 2 | 0.5 | 1.0 | 1.0 | 1.0 | 1.0 | 0.5 | 1.0 | 1.0 | 11010 | 15319 | 0.00152 |
| idioma en | 1 | 0.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 | 15319 | 15319 | 0.00099 |
| idioma pt | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 6702 | 6702 | 0.00052 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 5.0, correção factual 5.0, relevância 5.0, utilidade 4.5. Afirmações sem suporte: 0.0 das respostas julgadas. Custo do juiz: US$ 0.00121.

Respostas julgadas sob a nota de busca web: 0 de 2. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 0 foram marcadas como afirmação sem suporte.

Evidência truncada em 0 de 2 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| support | customer_support | 1 |
| support | customer_support → escalation | 1 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V030-PRICE-DIVERGENCE | 1 | dev | support | customer_support → escalation | handoff | não | content | 15319 | 0.00099217 |
| V030-PT-PRICE-INSUFFICIENT | 1 | dev | support | customer_support | answered | sim | - | 6702 | 0.0005245 |
