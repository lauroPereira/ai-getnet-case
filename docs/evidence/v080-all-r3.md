# Relatório de avaliação: v080-all-r3

Gerado em 2026-11-04T23:10:38+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "all", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 3, "limit": null, "include_replan": true, "campaign": "v080-qa", "campaign_cap_usd": 1.1, "cases": 44}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 132 | 0.856 | 1.0 | 0.97 | 1.0 | 1.0 | 0.864 | 1.0 | 1.0 | 7400 | 15695 | 0.31213 |
| split dev | 81 | 0.815 | 1.0 | 0.963 | 1.0 | 1.0 | 0.815 | 1.0 | 1.0 | 7735 | 17443 | 0.1981 |
| split holdout | 51 | 0.922 | 1.0 | 0.98 | 1.0 | 1.0 | 0.941 | 1.0 | 1.0 | 7002 | 14297 | 0.11403 |
| idioma en | 63 | 0.889 | 1.0 | 0.984 | 1.0 | 1.0 | 0.905 | 1.0 | 1.0 | 7317 | 13783 | 0.11055 |
| idioma pt | 69 | 0.826 | 1.0 | 0.957 | 1.0 | 1.0 | 0.826 | 1.0 | 1.0 | 7540 | 17639 | 0.20158 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 4.56, correção factual 4.62, relevância 4.77, utilidade 4.53. Afirmações sem suporte: 0.144 das respostas julgadas. Custo do juiz: US$ 0.06544.

Respostas julgadas sob a nota de busca web: 24 de 132. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 9 foram marcadas como afirmação sem suporte.

Evidência truncada em 5 de 132 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Afirmações sem suporte (veredito crítico)

Listadas uma a uma, nunca diluídas na média.

| Caso | Rep | Rota | Julgamentos marcados | Fundamentação (primeiro julgamento marcado) |
| --- | --- | --- | --- | --- |
| REPLAN-WEB | 1 | knowledge | 1 de 1 | Reply cites a 'Get Mini' and a consultation date, neither present in the evidence; NFC acceptance is supported generally. |
| EX02 | 1 | general_web | 1 de 1 | Web text not available; only source title is weather provider, and the reply's specific date and forecast details cannot be traced. |
| EX04 | 1 | knowledge | 1 de 1 | Web search text was not available; only the claim about needing one Pix key tied to the receiving account matches the passage. |
| PT02 | 1 | general_web | 1 de 1 | No web text available; specific date, weather details and temperatures cannot be traced, though source title is weather provider. |
| PT07 | 1 | general_web | 1 de 1 | Web source text not available; the date and rate R$ 6,13 cannot be confirmed against the listed source. |
| V030-PRICE-DIVERGENCE | 1 | support | 1 de 1 | All amounts, dates and comparison results match the simulate_pricing tool result; handoff fits the support status. |
| V030-CONTRACT-TERMINATION | 1 | human_handoff | 1 de 1 | The handoff and protocol number are not traceable to evidence, though no account facts were invented. |
| V030-PT-PRICE-DIVERGENCE | 1 | support | 1 de 1 | Sale date, amounts, fee and divergence all match the tool result; the protocol number HO-20261104-1EC9E8 is not in evidence. |
| EX07 | 2 | general_web | 1 de 1 | Web text unavailable; the rate figure and date cannot be confirmed by the source title, which only mentions historical euro-real data. |
| EX10 | 2 | knowledge | 1 de 1 | Most of the reply is supported by the passage, but the R$1.00 per link price is not in the evidence. |
| PT07 | 2 | general_web | 1 de 1 | Web text unavailable; reply gives specific rate R$6.13 and R$6.12 at 16h29 and date, unverifiable from titles alone. |
| UC14 | 2 | human_handoff | 1 de 1 | Handoff is supported by the route, but the protocol number HO-20261104-60795A appears nowhere in the evidence. |
| V030-PT-PRICE-DIVERGENCE | 2 | support | 1 de 1 | Amounts, date and net value come from the tool result, but the protocol number has no source in the evidence. |
| EX04 | 3 | knowledge | 1 de 1 | The key-linked-to-receiving-account part is supported, but the payment account statement and key-optional claim are not in the listed evidence. |
| EX07 | 3 | general_web | 1 de 1 | Web text unavailable; the specific rate 6.16 and date are not confirmable from the listed source title alone. |
| PT06 | 3 | knowledge | 1 de 1 | Most content traces to the passages, but 'concessão depende de avaliação individual de crédito' is not in the evidence. |
| UC14 | 3 | human_handoff | 1 de 1 | Handoff to a human is supported, but the protocol number HO-20261104-EF81C0 appears nowhere in the evidence. |
| V030-PRICE-DIVERGENCE | 3 | support | 1 de 1 | All amounts and the sale date match the tool result, but the protocol number HO-20261104-5D2E5F appears in no evidence. |
| V030-CONTRACT-TERMINATION | 3 | human_handoff | 1 de 1 | Handoff and protocol are consistent with the handoff status, but no evidence shows the protocol code or the agent will reply here. |

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| clarify | - | 3 |
| general_web | knowledge | 12 |
| human_handoff | escalation | 6 |
| knowledge | knowledge | 28 |
| knowledge | knowledge → customer_support → web | 3 |
| knowledge | knowledge → web | 8 |
| knowledge_and_support | knowledge → customer_support | 14 |
| out_of_scope | - | 6 |
| support | customer_support | 45 |
| support | customer_support → escalation | 6 |
| support | customer_support → knowledge → web | 1 |

## Variação: variação do assistente (o agente roda cada caso N vezes e o juiz avalia cada resposta uma vez)

Repetições por caso: 3. Desvio: média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou com diferença de até 1 ponto (±1).

> Ressalva de amostra pequena (D19): 44 casos com 3 repetições cada; os recortes por rota e por split têm menos casos ainda (marcados com * quando há menos de 10). Médias, desvios e concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno.

| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 44 | groundedness | 4.56 | 0.32 | 0.705 | 0.932 | 132 |
| geral | 44 | factual_correctness | 4.62 | 0.26 | 0.75 | 0.962 | 132 |
| geral | 44 | relevance | 4.77 | 0.17 | 0.803 | 1.0 | 132 |
| geral | 44 | usefulness | 4.53 | 0.3 | 0.682 | 0.97 | 132 |
| geral | 44 | unsupported_claim (taxa de verdadeiro) | 0.144 | - | 0.818 | - | 132 |
| rota clarify | 1* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |
| rota general_web | 4* | groundedness | 2.75 | 0.79 | 0.167 | 0.833 | 12 |
| rota general_web | 4* | factual_correctness | 3.0 | 0.43 | 0.5 | 1.0 | 12 |
| rota general_web | 4* | relevance | 4.75 | 0.29 | 0.667 | 1.0 | 12 |
| rota general_web | 4* | usefulness | 3.92 | 0.14 | 0.833 | 1.0 | 12 |
| rota general_web | 4* | unsupported_claim (taxa de verdadeiro) | 0.5 | - | 0.333 | - | 12 |
| rota human_handoff | 2* | groundedness | 3.83 | 0.79 | 0.167 | 0.833 | 6 |
| rota human_handoff | 2* | factual_correctness | 3.83 | 0.79 | 0.167 | 0.833 | 6 |
| rota human_handoff | 2* | relevance | 4.33 | 0.29 | 0.667 | 1.0 | 6 |
| rota human_handoff | 2* | usefulness | 4.0 | 0.58 | 0.333 | 1.0 | 6 |
| rota human_handoff | 2* | unsupported_claim (taxa de verdadeiro) | 0.667 | - | 0.333 | - | 6 |
| rota knowledge | 13 | groundedness | 4.54 | 0.53 | 0.59 | 0.846 | 39 |
| rota knowledge | 13 | factual_correctness | 4.59 | 0.49 | 0.59 | 0.897 | 39 |
| rota knowledge | 13 | relevance | 4.64 | 0.27 | 0.692 | 1.0 | 39 |
| rota knowledge | 13 | usefulness | 4.41 | 0.36 | 0.692 | 0.897 | 39 |
| rota knowledge | 13 | unsupported_claim (taxa de verdadeiro) | 0.128 | - | 0.795 | - | 39 |
| rota knowledge_and_support | 4* | groundedness | 4.92 | 0.14 | 0.833 | 1.0 | 12 |
| rota knowledge_and_support | 4* | factual_correctness | 4.83 | 0.29 | 0.667 | 1.0 | 12 |
| rota knowledge_and_support | 4* | relevance | 4.75 | 0.0 | 1.0 | 1.0 | 12 |
| rota knowledge_and_support | 4* | usefulness | 4.58 | 0.43 | 0.5 | 1.0 | 12 |
| rota knowledge_and_support | 4* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 12 |
| rota out_of_scope | 2* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota support | 18 | groundedness | 4.91 | 0.1 | 0.889 | 1.0 | 54 |
| rota support | 18 | factual_correctness | 4.98 | 0.03 | 0.963 | 1.0 | 54 |
| rota support | 18 | relevance | 4.87 | 0.13 | 0.852 | 1.0 | 54 |
| rota support | 18 | usefulness | 4.72 | 0.29 | 0.667 | 1.0 | 54 |
| rota support | 18 | unsupported_claim (taxa de verdadeiro) | 0.074 | - | 0.926 | - | 54 |
| split dev | 27 | groundedness | 4.54 | 0.34 | 0.716 | 0.914 | 81 |
| split dev | 27 | factual_correctness | 4.6 | 0.28 | 0.753 | 0.951 | 81 |
| split dev | 27 | relevance | 4.81 | 0.17 | 0.802 | 1.0 | 81 |
| split dev | 27 | usefulness | 4.54 | 0.36 | 0.63 | 0.951 | 81 |
| split dev | 27 | unsupported_claim (taxa de verdadeiro) | 0.16 | - | 0.802 | - | 81 |
| split holdout | 17 | groundedness | 4.59 | 0.29 | 0.686 | 0.961 | 51 |
| split holdout | 17 | factual_correctness | 4.65 | 0.23 | 0.745 | 0.98 | 51 |
| split holdout | 17 | relevance | 4.69 | 0.17 | 0.804 | 1.0 | 51 |
| split holdout | 17 | usefulness | 4.51 | 0.2 | 0.765 | 1.0 | 51 |
| split holdout | 17 | unsupported_claim (taxa de verdadeiro) | 0.118 | - | 0.843 | - | 51 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REPLAN-WEB | 1 | dev | knowledge | knowledge → web | answered | sim | - | 13647 | 0.01147127 |
| REPLAN-PROCEDURE | 1 | dev | support | customer_support → knowledge → web | answered | não | content | 23064 | 0.01177444 |
| REPLAN-TOOL-DOWN | 1 | dev | support | customer_support | answered | não | status, content | 23363 | 0.00061737 |
| REPLAN-ACCOUNT | 1 | dev | knowledge | knowledge → customer_support → web | answered | sim | - | 16753 | 0.01157239 |
| EX01 | 1 | dev | knowledge | knowledge | answered | sim | - | 8127 | 0.00061897 |
| EX02 | 1 | dev | general_web | knowledge | answered | sim | - | 5960 | 0.01085997 |
| EX03 | 1 | dev | support | customer_support | answered | sim | - | 8609 | 0.00068639 |
| EX04 | 1 | dev | knowledge | knowledge → web | answered | sim | - | 11232 | 0.0110411 |
| EX05 | 1 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 14187 | 0.00100861 |
| EX06 | 1 | dev | knowledge | knowledge | answered | sim | - | 9226 | 0.00060777 |
| EX07 | 1 | dev | general_web | knowledge | answered | sim | - | 5884 | 0.0106598 |
| EX08 | 1 | dev | knowledge_and_support | knowledge → customer_support | answered | não | content | 12537 | 0.00096756 |
| EX09 | 1 | dev | knowledge | knowledge | answered | sim | - | 5316 | 0.00039647 |
| EX10 | 1 | dev | knowledge | knowledge | answered | sim | - | 5935 | 0.00042677 |
| PT01 | 1 | holdout | knowledge | knowledge | answered | sim | - | 9025 | 0.00065327 |
| PT02 | 1 | holdout | general_web | knowledge | answered | sim | - | 5954 | 0.01045681 |
| PT03 | 1 | holdout | support | customer_support | answered | sim | - | 8830 | 0.00068659 |
| PT04 | 1 | holdout | knowledge | knowledge | answered | sim | - | 6074 | 0.00044837 |
| PT05 | 1 | holdout | knowledge_and_support | knowledge → customer_support | answered | sim | - | 11419 | 0.00095334 |
| PT06 | 1 | holdout | knowledge | knowledge | answered | sim | - | 8534 | 0.00060897 |
| PT07 | 1 | holdout | general_web | knowledge | answered | sim | - | 7540 | 0.01066181 |
| PT08 | 1 | holdout | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13425 | 0.00102915 |
| PT09 | 1 | holdout | knowledge | knowledge | answered | sim | - | 6385 | 0.00049897 |
| PT10 | 1 | holdout | knowledge | knowledge | answered | sim | - | 6090 | 0.00043327 |
| UC12 | 1 | holdout | out_of_scope | - | refused | sim | - | 2881 | 0.00014807 |
| UC13 | 1 | holdout | support | customer_support | answered | sim | - | 7595 | 0.00062986 |
| UC14 | 1 | holdout | human_handoff | escalation | handoff | sim | - | 5475 | 0.00035417 |
| UC16 | 1 | holdout | out_of_scope | - | refused | sim | - | 1303 | 0.0001 |
| UC17 | 1 | holdout | support | customer_support | answered | sim | - | 2779 | 0.00015911 |
| UC18 | 1 | holdout | clarify | - | needs_clarification | sim | - | 3202 | 0.00013647 |
| NOEV | 1 | holdout | knowledge | knowledge → web | answered | não | content | 9911 | 0.01102201 |
| V030-PRICE-CONSISTENT | 1 | dev | support | customer_support | answered | sim | - | 6958 | 0.00056794 |
| V030-PRICE-CONDITIONS | 1 | dev | support | customer_support | answered | não | content | 7060 | 0.00042061 |
| V030-PRICE-DIVERGENCE | 1 | dev | support | customer_support → escalation | handoff | não | content | 10647 | 0.00065324 |
| V030-PRICE-INSUFFICIENT | 1 | dev | support | customer_support | answered | sim | - | 7735 | 0.00033804 |
| V030-ENABLEMENT-PENDING | 1 | dev | support | customer_support | answered | sim | - | 6664 | 0.00028593 |
| V030-SALE-CANCELLATION | 1 | dev | support | customer_support | answered | sim | - | 7013 | 0.00045185 |
| V030-CONTRACT-TERMINATION | 1 | dev | human_handoff | escalation | handoff | sim | - | 5264 | 0.00033277 |
| V030-PT-PRICE-CONSISTENT | 1 | dev | support | customer_support | answered | sim | - | 7178 | 0.00056508 |
| V030-PT-PRICE-CONDITIONS | 1 | dev | support | customer_support | answered | sim | - | 8096 | 0.00044955 |
| V030-PT-PRICE-DIVERGENCE | 1 | dev | support | customer_support → escalation | handoff | sim | - | 11029 | 0.00065433 |
| V030-PT-PRICE-INSUFFICIENT | 1 | dev | support | customer_support | answered | não | content | 7250 | 0.00034146 |
| V030-PT-ENABLEMENT-PENDING | 1 | dev | support | customer_support | answered | sim | - | 6364 | 0.00047076 |
| V030-PT-SALE-CANCELLATION | 1 | dev | support | customer_support | answered | não | content | 6216 | 0.00026384 |
| REPLAN-WEB | 2 | dev | knowledge | knowledge → web | answered | não | content | 10480 | 0.01077137 |
| REPLAN-PROCEDURE | 2 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 17639 | 0.00134283 |
| REPLAN-TOOL-DOWN | 2 | dev | support | customer_support | answered | não | status, content | 6771 | 0.0003751 |
| REPLAN-ACCOUNT | 2 | dev | knowledge | knowledge → customer_support → web | answered | sim | - | 18979 | 0.01134053 |
| EX01 | 2 | dev | knowledge | knowledge | answered | sim | - | 9818 | 0.00044615 |
| EX02 | 2 | dev | general_web | knowledge | answered | sim | - | 5219 | 0.01044065 |
| EX03 | 2 | dev | support | customer_support | answered | sim | - | 7915 | 0.00066323 |
| EX04 | 2 | dev | knowledge | knowledge | answered | sim | - | 6758 | 0.00028562 |
| EX05 | 2 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 14157 | 0.00104562 |
| EX06 | 2 | dev | knowledge | knowledge | answered | sim | - | 8612 | 0.00040834 |
| EX07 | 2 | dev | general_web | knowledge | answered | sim | - | 7317 | 0.01066591 |
| EX08 | 2 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13929 | 0.00087776 |
| EX09 | 2 | dev | knowledge | knowledge | answered | sim | - | 5575 | 0.00021049 |
| EX10 | 2 | dev | knowledge | knowledge | answered | sim | - | 6389 | 0.00023911 |
| PT01 | 2 | holdout | knowledge | knowledge | answered | sim | - | 7254 | 0.00033423 |
| PT02 | 2 | holdout | general_web | knowledge | answered | sim | - | 7404 | 0.01045528 |
| PT03 | 2 | holdout | support | customer_support | answered | sim | - | 8735 | 0.00068152 |
| PT04 | 2 | holdout | knowledge | knowledge | answered | sim | - | 7397 | 0.00025382 |
| PT05 | 2 | holdout | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13862 | 0.00081858 |
| PT06 | 2 | holdout | knowledge | knowledge | answered | sim | - | 9076 | 0.00043048 |
| PT07 | 2 | holdout | general_web | knowledge | answered | sim | - | 7140 | 0.01069394 |
| PT08 | 2 | holdout | knowledge_and_support | knowledge → customer_support | answered | sim | - | 16920 | 0.00092138 |
| PT09 | 2 | holdout | knowledge | knowledge | answered | sim | - | 6457 | 0.00023572 |
| PT10 | 2 | holdout | knowledge | knowledge | answered | sim | - | 5069 | 0.00022096 |
| UC12 | 2 | holdout | out_of_scope | - | refused | sim | - | 3060 | 0.00014284 |
| UC13 | 2 | holdout | support | customer_support | answered | sim | - | 9293 | 0.00077397 |
| UC14 | 2 | holdout | human_handoff | escalation | handoff | sim | - | 6175 | 0.00034569 |
| UC16 | 2 | holdout | out_of_scope | - | refused | sim | - | 1258 | 0.0001 |
| UC17 | 2 | holdout | support | customer_support | answered | sim | - | 3705 | 0.00015711 |
| UC18 | 2 | holdout | clarify | - | needs_clarification | sim | - | 5577 | 0.00013114 |
| NOEV | 2 | holdout | knowledge | knowledge → web | answered | não | content | 15132 | 0.01073088 |
| V030-PRICE-CONSISTENT | 2 | dev | support | customer_support | answered | sim | - | 7593 | 0.00056457 |
| V030-PRICE-CONDITIONS | 2 | dev | support | customer_support | answered | sim | - | 7839 | 0.00060017 |
| V030-PRICE-DIVERGENCE | 2 | dev | support | customer_support → escalation | handoff | não | content | 12374 | 0.00062084 |
| V030-PRICE-INSUFFICIENT | 2 | dev | support | customer_support | answered | sim | - | 7636 | 0.0003422 |
| V030-ENABLEMENT-PENDING | 2 | dev | support | customer_support | answered | sim | - | 7895 | 0.00027258 |
| V030-SALE-CANCELLATION | 2 | dev | support | customer_support | answered | sim | - | 6776 | 0.00026986 |
| V030-CONTRACT-TERMINATION | 2 | dev | human_handoff | escalation | handoff | sim | - | 5476 | 0.00032767 |
| V030-PT-PRICE-CONSISTENT | 2 | dev | support | customer_support | answered | sim | - | 6846 | 0.00056614 |
| V030-PT-PRICE-CONDITIONS | 2 | dev | support | customer_support | answered | sim | - | 10663 | 0.0004252 |
| V030-PT-PRICE-DIVERGENCE | 2 | dev | support | customer_support → escalation | handoff | sim | - | 15695 | 0.00063356 |
| V030-PT-PRICE-INSUFFICIENT | 2 | dev | support | customer_support | answered | não | content | 7232 | 0.00032776 |
| V030-PT-ENABLEMENT-PENDING | 2 | dev | support | customer_support | answered | sim | - | 6730 | 0.00027518 |
| V030-PT-SALE-CANCELLATION | 2 | dev | support | customer_support | answered | sim | - | 5975 | 0.0004689 |
| REPLAN-WEB | 3 | dev | knowledge | knowledge → web | answered | sim | - | 12621 | 0.01078827 |
| REPLAN-PROCEDURE | 3 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13533 | 0.00100743 |
| REPLAN-TOOL-DOWN | 3 | dev | support | customer_support | answered | não | status, content | 9218 | 0.0003768 |
| REPLAN-ACCOUNT | 3 | dev | knowledge | knowledge → customer_support → web | answered | sim | - | 17443 | 0.01137522 |
| EX01 | 3 | dev | knowledge | knowledge | answered | sim | - | 7526 | 0.00034765 |
| EX02 | 3 | dev | general_web | knowledge | answered | sim | - | 5519 | 0.01044735 |
| EX03 | 3 | dev | support | customer_support | answered | sim | - | 9016 | 0.00067593 |
| EX04 | 3 | dev | knowledge | knowledge → web | answered | sim | - | 10630 | 0.01083302 |
| EX05 | 3 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 11962 | 0.00073299 |
| EX06 | 3 | dev | knowledge | knowledge | answered | sim | - | 10739 | 0.00045474 |
| EX07 | 3 | dev | general_web | knowledge | answered | sim | - | 7187 | 0.01064591 |
| EX08 | 3 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13783 | 0.00089708 |
| EX09 | 3 | dev | knowledge | knowledge | answered | sim | - | 4926 | 0.00019169 |
| EX10 | 3 | dev | knowledge | knowledge | answered | sim | - | 7864 | 0.00027601 |
| PT01 | 3 | holdout | knowledge | knowledge | answered | sim | - | 7002 | 0.00034783 |
| PT02 | 3 | holdout | general_web | knowledge | answered | sim | - | 5636 | 0.01045448 |
| PT03 | 3 | holdout | support | customer_support | answered | sim | - | 8531 | 0.00068032 |
| PT04 | 3 | holdout | knowledge | knowledge | answered | sim | - | 6095 | 0.00024332 |
| PT05 | 3 | holdout | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13111 | 0.00083902 |
| PT06 | 3 | holdout | knowledge | knowledge | answered | sim | - | 9616 | 0.00044138 |
| PT07 | 3 | holdout | general_web | knowledge | answered | sim | - | 7944 | 0.01067674 |
| PT08 | 3 | holdout | knowledge_and_support | knowledge → customer_support | answered | sim | - | 14297 | 0.00092189 |
| PT09 | 3 | holdout | knowledge | knowledge | answered | sim | - | 6084 | 0.00025472 |
| PT10 | 3 | holdout | knowledge | knowledge | answered | sim | - | 5761 | 0.00026096 |
| UC12 | 3 | holdout | out_of_scope | - | refused | sim | - | 3197 | 0.00014334 |
| UC13 | 3 | holdout | support | customer_support | needs_clarification | não | status | 10389 | 0.00080697 |
| UC14 | 3 | holdout | human_handoff | escalation | handoff | sim | - | 5970 | 0.00035689 |
| UC16 | 3 | holdout | out_of_scope | - | refused | sim | - | 1372 | 0.0001 |
| UC17 | 3 | holdout | support | customer_support | answered | sim | - | 3006 | 0.00015711 |
| UC18 | 3 | holdout | clarify | - | needs_clarification | sim | - | 2911 | 0.00013314 |
| NOEV | 3 | holdout | knowledge | knowledge → web | answered | não | content | 10509 | 0.01080678 |
| V030-PRICE-CONSISTENT | 3 | dev | support | customer_support | answered | sim | - | 6898 | 0.00057037 |
| V030-PRICE-CONDITIONS | 3 | dev | support | customer_support | answered | não | content | 7348 | 0.00042454 |
| V030-PRICE-DIVERGENCE | 3 | dev | support | customer_support → escalation | handoff | sim | - | 11849 | 0.00064254 |
| V030-PRICE-INSUFFICIENT | 3 | dev | support | customer_support | answered | não | content | 8289 | 0.00051993 |
| V030-ENABLEMENT-PENDING | 3 | dev | support | customer_support | answered | sim | - | 6775 | 0.00027578 |
| V030-SALE-CANCELLATION | 3 | dev | support | customer_support | answered | sim | - | 6224 | 0.00026016 |
| V030-CONTRACT-TERMINATION | 3 | dev | human_handoff | escalation | handoff | sim | - | 5277 | 0.00033537 |
| V030-PT-PRICE-CONSISTENT | 3 | dev | support | customer_support | answered | não | content | 7264 | 0.00055714 |
| V030-PT-PRICE-CONDITIONS | 3 | dev | support | customer_support | answered | sim | - | 8002 | 0.0004405 |
| V030-PT-PRICE-DIVERGENCE | 3 | dev | support | customer_support → escalation | handoff | sim | - | 12234 | 0.00084048 |
| V030-PT-PRICE-INSUFFICIENT | 3 | dev | support | customer_support | answered | sim | - | 6696 | 0.00033626 |
| V030-PT-ENABLEMENT-PENDING | 3 | dev | support | customer_support | answered | sim | - | 6718 | 0.00026788 |
| V030-PT-SALE-CANCELLATION | 3 | dev | support | customer_support | answered | sim | - | 5594 | 0.00026578 |

## Conversas de vários turnos

3 de 4 conversas aprovadas em todos os turnos.

| Conversa | Turno | Rota | Status | Caso | Aprovado | Falhas |
| --- | --- | --- | --- | --- | --- | --- |
| FU01 | 1 | knowledge_and_support | answered | awaiting_customer | sim | - |
| FU01 | 2 | knowledge_and_support | answered | resolved | não | route |
| FU02 | 1 | knowledge_and_support | answered | awaiting_customer | sim | - |
| FU02 | 2 | knowledge_and_support | handoff | handoff | sim | - |
| FU02 | 3 | knowledge_and_support | handoff | handoff | sim | - |
| FU03 | 1 | knowledge | answered | awaiting_customer | sim | - |
| FU03 | 2 | acknowledgement | answered | awaiting_customer | sim | - |
| FU04 | 1 | knowledge_and_support | answered | awaiting_customer | sim | - |
| FU04 | 2 | human_handoff | handoff | handoff | sim | - |
| FU04 | 3 | human_handoff | handoff | handoff | sim | - |
