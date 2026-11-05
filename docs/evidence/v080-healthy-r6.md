# Relatório de avaliação: v080-r6-1baa7b31-healthy

Gerado em 2026-11-05T10:10:34+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "all", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 3, "limit": null, "include_replan": true, "campaign": "v080-qa", "campaign_cap_usd": 1.4, "cases": 6}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 18 | 0.889 | 1.0 | 1.0 | 1.0 | 1.0 | 0.889 | 1.0 | 1.0 | 8076 | 13694 | 0.00917 |
| split dev | 18 | 0.889 | 1.0 | 1.0 | 1.0 | 1.0 | 0.889 | 1.0 | 1.0 | 8076 | 13694 | 0.00917 |
| idioma en | 12 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 7916 | 13694 | 0.00626 |
| idioma pt | 6 | 0.667 | 1.0 | 1.0 | 1.0 | 1.0 | 0.667 | 1.0 | 1.0 | 8383 | 9306 | 0.00291 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 5.0, correção factual 5.0, relevância 5.0, utilidade 4.89. Afirmações sem suporte: 0.0 das respostas julgadas. Custo do juiz: US$ 0.00973.

Respostas julgadas sob a nota de busca web: 0 de 18. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 0 foram marcadas como afirmação sem suporte.

Evidência truncada em 0 de 18 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| support | customer_support | 15 |
| support | customer_support → escalation | 3 |

## Variação: variação do assistente (o agente roda cada caso N vezes e o juiz avalia cada resposta uma vez)

Repetições por caso: 3. Desvio: média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou com diferença de até 1 ponto (±1).

> Ressalva de amostra pequena (D19): 6 casos com 3 repetições cada; os recortes por rota e por split têm menos casos ainda (marcados com * quando há menos de 10). Médias, desvios e concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno.

| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 6* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 18 |
| geral | 6* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 18 |
| geral | 6* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 18 |
| geral | 6* | usefulness | 4.89 | 0.19 | 0.778 | 1.0 | 18 |
| geral | 6* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 18 |
| rota support | 6* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 18 |
| rota support | 6* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 18 |
| rota support | 6* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 18 |
| rota support | 6* | usefulness | 4.89 | 0.19 | 0.778 | 1.0 | 18 |
| rota support | 6* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 18 |
| split dev | 6* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 18 |
| split dev | 6* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 18 |
| split dev | 6* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 18 |
| split dev | 6* | usefulness | 4.89 | 0.19 | 0.778 | 1.0 | 18 |
| split dev | 6* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 18 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V030-PRICE-CONDITIONS | 1 | dev | support | customer_support | answered | sim | - | 13694 | 0.00080117 |
| V030-PRICE-DIVERGENCE | 1 | dev | support | customer_support → escalation | handoff | sim | - | 15358 | 0.00098257 |
| V030-PRICE-INSUFFICIENT | 1 | dev | support | customer_support | answered | sim | - | 7928 | 0.00033094 |
| V030-SALE-CANCELLATION | 1 | dev | support | customer_support | answered | sim | - | 7256 | 0.00026242 |
| V030-PT-PRICE-CONDITIONS | 1 | dev | support | customer_support | answered | sim | - | 8556 | 0.00063907 |
| V030-PT-PRICE-INSUFFICIENT | 1 | dev | support | customer_support | answered | sim | - | 7753 | 0.00034288 |
| V030-PRICE-CONDITIONS | 2 | dev | support | customer_support | answered | sim | - | 7605 | 0.00061604 |
| V030-PRICE-DIVERGENCE | 2 | dev | support | customer_support → escalation | handoff | sim | - | 11899 | 0.00066044 |
| V030-PRICE-INSUFFICIENT | 2 | dev | support | customer_support | answered | sim | - | 7676 | 0.0003385 |
| V030-SALE-CANCELLATION | 2 | dev | support | customer_support | answered | sim | - | 7904 | 0.00025746 |
| V030-PT-PRICE-CONDITIONS | 2 | dev | support | customer_support | answered | não | content | 9306 | 0.00062772 |
| V030-PT-PRICE-INSUFFICIENT | 2 | dev | support | customer_support | answered | sim | - | 8210 | 0.00033426 |
| V030-PRICE-CONDITIONS | 3 | dev | support | customer_support | answered | sim | - | 7776 | 0.00059857 |
| V030-PRICE-DIVERGENCE | 3 | dev | support | customer_support → escalation | handoff | sim | - | 12313 | 0.00064124 |
| V030-PRICE-INSUFFICIENT | 3 | dev | support | customer_support | answered | sim | - | 7135 | 0.0003197 |
| V030-SALE-CANCELLATION | 3 | dev | support | customer_support | answered | sim | - | 9711 | 0.00045319 |
| V030-PT-PRICE-CONDITIONS | 3 | dev | support | customer_support | answered | sim | - | 9217 | 0.00063902 |
| V030-PT-PRICE-INSUFFICIENT | 3 | dev | support | customer_support | answered | não | content | 7942 | 0.00032706 |
