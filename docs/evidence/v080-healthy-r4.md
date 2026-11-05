# Relatório de avaliação: v080-r4-4c3c8a98-healthy

Gerado em 2026-11-05T03:54:49+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "all", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 3, "limit": null, "include_replan": true, "campaign": "v080-qa", "campaign_cap_usd": 1.1, "cases": 21}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 63 | 0.492 | 0.968 | 0.889 | 0.937 | 0.762 | 0.524 | 0.714 | 0.873 | 7418 | 16511 | 0.16562 |
| split dev | 54 | 0.407 | 0.963 | 0.87 | 0.926 | 0.722 | 0.444 | 0.667 | 0.852 | 7402 | 16511 | 0.11978 |
| split holdout | 9 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 10145 | 11484 | 0.04584 |
| idioma en | 30 | 0.5 | 0.967 | 0.867 | 1.0 | 0.8 | 0.567 | 0.7 | 0.933 | 7378 | 12967 | 0.04468 |
| idioma pt | 33 | 0.485 | 0.97 | 0.909 | 0.879 | 0.727 | 0.485 | 0.727 | 0.818 | 7418 | 18317 | 0.12093 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 4.92, correção factual 4.87, relevância 4.76, utilidade 4.56. Afirmações sem suporte: 0.0 das respostas julgadas. Custo do juiz: US$ 0.02748.

Respostas julgadas sob a nota de busca web: 12 de 63. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 0 foram marcadas como afirmação sem suporte.

Evidência truncada em 1 de 63 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| clarify | - | 2 |
| human_handoff | escalation | 5 |
| knowledge | knowledge → customer_support → web | 3 |
| knowledge | knowledge → web | 9 |
| knowledge_and_support | knowledge → customer_support | 6 |
| support | customer_support | 38 |

## Variação: variação do assistente (o agente roda cada caso N vezes e o juiz avalia cada resposta uma vez)

Repetições por caso: 3. Desvio: média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou com diferença de até 1 ponto (±1).

> Ressalva de amostra pequena (D19): 21 casos com 3 repetições cada; os recortes por rota e por split têm menos casos ainda (marcados com * quando há menos de 10). Médias, desvios e concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno.

| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 21 | groundedness | 4.92 | 0.08 | 0.905 | 1.0 | 63 |
| geral | 21 | factual_correctness | 4.87 | 0.16 | 0.81 | 1.0 | 63 |
| geral | 21 | relevance | 4.76 | 0.27 | 0.73 | 0.952 | 63 |
| geral | 21 | usefulness | 4.56 | 0.38 | 0.635 | 0.921 | 63 |
| geral | 21 | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 63 |
| rota clarify | 1* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | usefulness | 4.67 | 0.58 | 0.333 | 1.0 | 3 |
| rota clarify | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |
| rota human_handoff | 1* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota human_handoff | 1* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota human_handoff | 1* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota human_handoff | 1* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota human_handoff | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |
| rota knowledge | 4* | groundedness | 4.75 | 0.29 | 0.667 | 1.0 | 12 |
| rota knowledge | 4* | factual_correctness | 4.58 | 0.58 | 0.333 | 1.0 | 12 |
| rota knowledge | 4* | relevance | 4.83 | 0.29 | 0.667 | 1.0 | 12 |
| rota knowledge | 4* | usefulness | 4.25 | 0.0 | 1.0 | 1.0 | 12 |
| rota knowledge | 4* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 12 |
| rota knowledge_and_support | 2* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota knowledge_and_support | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota knowledge_and_support | 2* | relevance | 4.67 | 0.29 | 0.667 | 1.0 | 6 |
| rota knowledge_and_support | 2* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota knowledge_and_support | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota support | 13 | groundedness | 4.95 | 0.04 | 0.949 | 1.0 | 39 |
| rota support | 13 | factual_correctness | 4.92 | 0.09 | 0.897 | 1.0 | 39 |
| rota support | 13 | relevance | 4.72 | 0.3 | 0.718 | 0.923 | 39 |
| rota support | 13 | usefulness | 4.54 | 0.57 | 0.462 | 0.872 | 39 |
| rota support | 13 | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 39 |
| split dev | 18 | groundedness | 4.91 | 0.1 | 0.889 | 1.0 | 54 |
| split dev | 18 | factual_correctness | 4.87 | 0.16 | 0.815 | 1.0 | 54 |
| split dev | 18 | relevance | 4.72 | 0.31 | 0.685 | 0.944 | 54 |
| split dev | 18 | usefulness | 4.56 | 0.41 | 0.611 | 0.907 | 54 |
| split dev | 18 | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 54 |
| split holdout | 3* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 9 |
| split holdout | 3* | factual_correctness | 4.89 | 0.19 | 0.778 | 1.0 | 9 |
| split holdout | 3* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 9 |
| split holdout | 3* | usefulness | 4.56 | 0.19 | 0.778 | 1.0 | 9 |
| split holdout | 3* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 9 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REPLAN-WEB | 1 | dev | knowledge | knowledge → web | answered | sim | - | 16511 | 0.0116577 |
| REPLAN-PROCEDURE | 1 | dev | knowledge_and_support | knowledge → customer_support | answered | não | tools, amounts, content | 15912 | 0.0011749 |
| REPLAN-ACCOUNT | 1 | dev | knowledge | knowledge → customer_support → web | answered | sim | - | 18731 | 0.01158262 |
| EX04 | 1 | dev | knowledge | knowledge → web | answered | sim | - | 12508 | 0.01147447 |
| EX08 | 1 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13152 | 0.00105577 |
| UC13 | 1 | holdout | support | customer_support | answered | sim | - | 10145 | 0.00067814 |
| UC14 | 1 | holdout | human_handoff | escalation | handoff | sim | - | 5491 | 0.00035417 |
| NOEV | 1 | holdout | knowledge | knowledge → web | answered | sim | - | 11375 | 0.02102042 |
| V030-PRICE-CONSISTENT | 1 | dev | support | customer_support | answered | não | amounts, sources | 7072 | 0.00043664 |
| V030-PRICE-CONDITIONS | 1 | dev | support | customer_support | answered | não | content, sources | 6738 | 0.00026171 |
| V030-PRICE-DIVERGENCE | 1 | dev | support | customer_support | answered | não | status, amounts, sources | 8262 | 0.00027121 |
| V030-PRICE-INSUFFICIENT | 1 | dev | support | customer_support | answered | não | content | 7467 | 0.00033424 |
| V030-ENABLEMENT-PENDING | 1 | dev | support | customer_support | answered | sim | - | 7290 | 0.00026953 |
| V030-SALE-CANCELLATION | 1 | dev | support | customer_support | answered | não | content | 6516 | 0.00042765 |
| V030-CONTRACT-TERMINATION | 1 | dev | clarify | - | needs_clarification | não | route, status, content | 2874 | 0.00014677 |
| V030-PT-PRICE-CONSISTENT | 1 | dev | support | customer_support | answered | não | amounts, content, sources, grounded | 7308 | 0.00046998 |
| V030-PT-PRICE-CONDITIONS | 1 | dev | support | customer_support | answered | não | content, sources, grounded | 7409 | 0.00025385 |
| V030-PT-PRICE-DIVERGENCE | 1 | dev | support | customer_support | answered | não | status, amounts, content, sources, grounded | 6913 | 0.00025163 |
| V030-PT-PRICE-INSUFFICIENT | 1 | dev | support | customer_support | answered | sim | - | 7854 | 0.00033318 |
| V030-PT-ENABLEMENT-PENDING | 1 | dev | support | customer_support | answered | sim | - | 7036 | 0.00026614 |
| V030-PT-SALE-CANCELLATION | 1 | dev | support | customer_support | answered | não | content | 6423 | 0.00043006 |
| REPLAN-WEB | 2 | dev | knowledge | knowledge → web | answered | sim | - | 12124 | 0.01102453 |
| REPLAN-PROCEDURE | 2 | dev | knowledge_and_support | knowledge → customer_support | answered | não | tools, amounts, content | 13945 | 0.00091206 |
| REPLAN-ACCOUNT | 2 | dev | knowledge | knowledge → customer_support → web | answered | sim | - | 18317 | 0.01142928 |
| EX04 | 2 | dev | knowledge | knowledge → web | answered | sim | - | 11497 | 0.01080983 |
| EX08 | 2 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 12868 | 0.00084271 |
| UC13 | 2 | holdout | support | customer_support | answered | sim | - | 11484 | 0.00083353 |
| UC14 | 2 | holdout | human_handoff | escalation | handoff | sim | - | 5872 | 0.00034039 |
| NOEV | 2 | holdout | knowledge | knowledge → web | answered | sim | - | 10199 | 0.01079229 |
| V030-PRICE-CONSISTENT | 2 | dev | support | customer_support | answered | não | amounts, content, sources | 6746 | 0.00043727 |
| V030-PRICE-CONDITIONS | 2 | dev | support | customer_support | answered | não | content, sources | 7286 | 0.00026754 |
| V030-PRICE-DIVERGENCE | 2 | dev | support | customer_support | answered | não | status, amounts, content, sources, grounded | 6363 | 0.00026754 |
| V030-PRICE-INSUFFICIENT | 2 | dev | support | customer_support | answered | não | content | 8378 | 0.0003351 |
| V030-ENABLEMENT-PENDING | 2 | dev | support | customer_support | answered | sim | - | 7954 | 0.00029038 |
| V030-SALE-CANCELLATION | 2 | dev | support | customer_support | answered | não | content | 8325 | 0.00023406 |
| V030-CONTRACT-TERMINATION | 2 | dev | human_handoff | escalation | handoff | sim | - | 6068 | 0.00033407 |
| V030-PT-PRICE-CONSISTENT | 2 | dev | support | customer_support | answered | não | amounts, content, sources, grounded | 6765 | 0.00048254 |
| V030-PT-PRICE-CONDITIONS | 2 | dev | support | customer_support | answered | não | content, sources, grounded | 9531 | 0.0002735 |
| V030-PT-PRICE-DIVERGENCE | 2 | dev | support | customer_support | answered | não | status, amounts, content, sources | 6262 | 0.00023406 |
| V030-PT-PRICE-INSUFFICIENT | 2 | dev | support | customer_support | answered | não | content | 6369 | 0.00033026 |
| V030-PT-ENABLEMENT-PENDING | 2 | dev | support | customer_support | answered | sim | - | 6918 | 0.00027538 |
| V030-PT-SALE-CANCELLATION | 2 | dev | support | customer_support | answered | não | content | 6256 | 0.00023638 |
| REPLAN-WEB | 3 | dev | knowledge | knowledge → web | answered | sim | - | 9453 | 0.01080438 |
| REPLAN-PROCEDURE | 3 | dev | knowledge_and_support | knowledge → customer_support | answered | não | tools, amounts, content | 14335 | 0.00100896 |
| REPLAN-ACCOUNT | 3 | dev | knowledge | knowledge → customer_support → web | answered | sim | - | 18787 | 0.01139787 |
| EX04 | 3 | dev | knowledge | knowledge → web | answered | sim | - | 11943 | 0.01085063 |
| EX08 | 3 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 11887 | 0.00081735 |
| UC13 | 3 | holdout | support | customer_support | answered | sim | - | 9642 | 0.00067153 |
| UC14 | 3 | holdout | human_handoff | escalation | handoff | sim | - | 5519 | 0.00035339 |
| NOEV | 3 | holdout | knowledge | knowledge → web | answered | sim | - | 10891 | 0.01079749 |
| V030-PRICE-CONSISTENT | 3 | dev | support | customer_support | answered | não | amounts, content, sources | 6759 | 0.00044617 |
| V030-PRICE-CONDITIONS | 3 | dev | support | customer_support | answered | não | content, sources | 6609 | 0.00045707 |
| V030-PRICE-DIVERGENCE | 3 | dev | support | customer_support | answered | não | status, amounts, content, sources, grounded | 6798 | 0.00024684 |
| V030-PRICE-INSUFFICIENT | 3 | dev | support | customer_support | answered | sim | - | 12967 | 0.0003391 |
| V030-ENABLEMENT-PENDING | 3 | dev | support | customer_support | answered | sim | - | 6882 | 0.00027928 |
| V030-SALE-CANCELLATION | 3 | dev | support | customer_support | answered | não | content | 5600 | 0.00023556 |
| V030-CONTRACT-TERMINATION | 3 | dev | human_handoff | escalation | handoff | sim | - | 5090 | 0.00033297 |
| V030-PT-PRICE-CONSISTENT | 3 | dev | support | customer_support | answered | não | amounts, content, sources | 7396 | 0.00044504 |
| V030-PT-PRICE-CONDITIONS | 3 | dev | support | customer_support | answered | não | content, sources, grounded | 6439 | 0.00046202 |
| V030-PT-PRICE-DIVERGENCE | 3 | dev | clarify | - | needs_clarification | não | route, status, tools, amounts, content, sources | 1781 | 0.0004947 |
| V030-PT-PRICE-INSUFFICIENT | 3 | dev | support | customer_support | answered | não | content | 7514 | 0.00034326 |
| V030-PT-ENABLEMENT-PENDING | 3 | dev | support | customer_support | answered | sim | - | 7418 | 0.00027248 |
| V030-PT-SALE-CANCELLATION | 3 | dev | support | customer_support | answered | não | content | 9449 | 0.00042919 |
