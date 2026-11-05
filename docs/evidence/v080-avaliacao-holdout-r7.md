# Relatório de avaliação: v080-r7-1baa7b31-holdout

Gerado em 2026-11-05T10:59:42+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "holdout_v080", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 3, "limit": null, "include_replan": false, "campaign": "v080-qa", "campaign_cap_usd": 1.4, "cases": 25}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 75 | 0.827 | 0.947 | 0.973 | 0.973 | 0.933 | 0.853 | 0.933 | 0.973 | 7620 | 14657 | 0.10912 |
| split holdout_v080 | 75 | 0.827 | 0.947 | 0.973 | 0.973 | 0.933 | 0.853 | 0.933 | 0.973 | 7620 | 14657 | 0.10912 |
| idioma en | 36 | 0.861 | 0.944 | 0.944 | 0.944 | 1.0 | 0.861 | 0.944 | 1.0 | 7603 | 10549 | 0.04661 |
| idioma pt | 39 | 0.795 | 0.949 | 1.0 | 1.0 | 0.872 | 0.846 | 0.923 | 0.949 | 7640 | 16521 | 0.06251 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 4.67, correção factual 4.61, relevância 4.83, utilidade 4.64. Afirmações sem suporte: 0.08 das respostas julgadas. Custo do juiz: US$ 0.03557.

Respostas julgadas sob a nota de busca web: 7 de 75. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 2 foram marcadas como afirmação sem suporte.

Evidência truncada em 0 de 75 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Afirmações sem suporte (veredito crítico)

Listadas uma a uma, nunca diluídas na média.

| Caso | Rep | Rota | Julgamentos marcados | Fundamentação (primeiro julgamento marcado) |
| --- | --- | --- | --- | --- |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 1 | knowledge | 1 de 1 | Most facts trace to passages, but 'R$1,00 por link pago pelo cliente' does not appear in any evidence. |
| HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD | 1 | knowledge_and_support | 1 de 1 | Steps and Pix timing come from passages, but evidence shows the Pix settled, contradicting the reply's uncertainty. |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 2 | knowledge | 1 de 1 | The R$1,00 por link pago claim is not in the evidence; other facts (15/01/2026, migration, link creation) are supported. |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 3 | knowledge | 1 de 1 | The R$1,00 price is not in the evidence; the rest (descontinuation, migration to Link de Pagamento) is supported. |
| HV080-PT-WEB-CURITIBA-RAIN | 3 | general_web | 1 de 1 | Only source title available; the INMET alert and detailed forecast cannot be traced to any recorded evidence. |
| HV080-EN-WEB-USD-BRL | 3 | general_web | 1 de 1 | Web text unavailable; only source title confirms exchange-rate topic, but the specific date and rate 5.47 are unverifiable from evidence. |

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| clarify | - | 2 |
| general_web | knowledge | 6 |
| human_handoff | escalation | 6 |
| knowledge | knowledge | 15 |
| knowledge | knowledge → customer_support | 1 |
| knowledge | knowledge → customer_support → web | 1 |
| knowledge_and_support | knowledge → customer_support | 13 |
| out_of_scope | - | 6 |
| support | customer_support | 25 |

## Variação: variação do assistente (o agente roda cada caso N vezes e o juiz avalia cada resposta uma vez)

Repetições por caso: 3. Desvio: média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou com diferença de até 1 ponto (±1).

> Ressalva de amostra pequena (D19): 25 casos com 3 repetições cada; os recortes por rota e por split têm menos casos ainda (marcados com * quando há menos de 10). Médias, desvios e concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno.

| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 25 | groundedness | 4.67 | 0.15 | 0.867 | 0.96 | 75 |
| geral | 25 | factual_correctness | 4.61 | 0.18 | 0.88 | 0.933 | 75 |
| geral | 25 | relevance | 4.83 | 0.25 | 0.773 | 0.96 | 75 |
| geral | 25 | usefulness | 4.64 | 0.34 | 0.693 | 0.933 | 75 |
| geral | 25 | unsupported_claim (taxa de verdadeiro) | 0.08 | - | 0.92 | - | 75 |
| rota clarify | 1* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |
| rota general_web | 2* | groundedness | 3.17 | 0.76 | 0.5 | 0.667 | 6 |
| rota general_web | 2* | factual_correctness | 3.0 | 0.5 | 0.5 | 0.833 | 6 |
| rota general_web | 2* | relevance | 4.67 | 0.58 | 0.333 | 1.0 | 6 |
| rota general_web | 2* | usefulness | 4.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota general_web | 2* | unsupported_claim (taxa de verdadeiro) | 0.333 | - | 0.333 | - | 6 |
| rota human_handoff | 2* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | usefulness | 4.83 | 0.29 | 0.667 | 1.0 | 6 |
| rota human_handoff | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota knowledge | 6* | groundedness | 4.33 | 0.17 | 0.833 | 0.944 | 18 |
| rota knowledge | 6* | factual_correctness | 4.28 | 0.19 | 0.889 | 0.889 | 18 |
| rota knowledge | 6* | relevance | 4.72 | 0.26 | 0.722 | 0.944 | 18 |
| rota knowledge | 6* | usefulness | 4.67 | 0.36 | 0.611 | 0.944 | 18 |
| rota knowledge | 6* | unsupported_claim (taxa de verdadeiro) | 0.167 | - | 1.0 | - | 18 |
| rota knowledge_and_support | 5* | groundedness | 4.93 | 0.12 | 0.867 | 1.0 | 15 |
| rota knowledge_and_support | 5* | factual_correctness | 4.8 | 0.35 | 0.867 | 0.867 | 15 |
| rota knowledge_and_support | 5* | relevance | 4.73 | 0.46 | 0.733 | 0.867 | 15 |
| rota knowledge_and_support | 5* | usefulness | 4.67 | 0.58 | 0.733 | 0.733 | 15 |
| rota knowledge_and_support | 5* | unsupported_claim (taxa de verdadeiro) | 0.067 | - | 0.867 | - | 15 |
| rota out_of_scope | 2* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | usefulness | 4.83 | 0.29 | 0.667 | 1.0 | 6 |
| rota out_of_scope | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota support | 7* | groundedness | 4.95 | 0.08 | 0.905 | 1.0 | 21 |
| rota support | 7* | factual_correctness | 4.95 | 0.08 | 0.905 | 1.0 | 21 |
| rota support | 7* | relevance | 4.9 | 0.16 | 0.81 | 1.0 | 21 |
| rota support | 7* | usefulness | 4.62 | 0.33 | 0.619 | 1.0 | 21 |
| rota support | 7* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 21 |
| split holdout_v080 | 25 | groundedness | 4.67 | 0.15 | 0.867 | 0.96 | 75 |
| split holdout_v080 | 25 | factual_correctness | 4.61 | 0.18 | 0.88 | 0.933 | 75 |
| split holdout_v080 | 25 | relevance | 4.83 | 0.25 | 0.773 | 0.96 | 75 |
| split holdout_v080 | 25 | usefulness | 4.64 | 0.34 | 0.693 | 0.933 | 75 |
| split holdout_v080 | 25 | unsupported_claim (taxa de verdadeiro) | 0.08 | - | 0.92 | - | 75 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HV080-EN-KNOW-PHONE-AS-TERMINAL-HARD | 1 | holdout_v080 | knowledge | knowledge | answered | sim | - | 10549 | 0.00052487 |
| HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD | 1 | holdout_v080 | knowledge | knowledge | answered | sim | - | 9552 | 0.00044287 |
| HV080-PT-KNOW-CREDIARIO-PAYOUT | 1 | holdout_v080 | knowledge | knowledge | answered | sim | - | 7773 | 0.00045827 |
| HV080-EN-KNOW-SAME-DAY-REVERSAL | 1 | holdout_v080 | knowledge | knowledge | answered | sim | - | 8927 | 0.00055377 |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 1 | holdout_v080 | knowledge | knowledge | answered | sim | - | 8556 | 0.00064087 |
| HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13430 | 0.00085316 |
| HV080-PT-WEB-CURITIBA-RAIN | 1 | holdout_v080 | general_web | knowledge | answered | sim | - | 6225 | 0.01080477 |
| HV080-EN-WEB-USD-BRL | 1 | holdout_v080 | general_web | knowledge | answered | sim | - | 7586 | 0.0106625 |
| HV080-EN-SUP-RECEIVABLE-DEBIT-NET | 1 | holdout_v080 | support | customer_support | answered | sim | - | 7915 | 0.00057078 |
| HV080-EN-SUP-PAYOUT-LINK-SALE | 1 | holdout_v080 | support | customer_support | answered | sim | - | 9070 | 0.0004502 |
| HV080-PT-SUP-DEVICE-SIGNAL | 1 | holdout_v080 | support | customer_support | answered | sim | - | 7127 | 0.00048434 |
| HV080-EN-SUP-DEBIT-DECLINE-ISSUER | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13252 | 0.00092235 |
| HV080-PT-SUP-CONTRACT-SETTLEMENT | 1 | holdout_v080 | knowledge | knowledge → customer_support → web | answered | não | route, content | 21953 | 0.0120928 |
| HV080-PT-SUP-PRICE-LINK-CONSISTENT | 1 | holdout_v080 | support | customer_support | answered | não | amounts, content, sources, grounded | 8251 | 0.00049651 |
| HV080-EN-SUP-PRICE-CREDIT-CONDITIONS | 1 | holdout_v080 | support | customer_support | answered | sim | - | 8970 | 0.00066308 |
| HV080-PT-SUP-CANCELLATION-REFUND | 1 | holdout_v080 | support | customer_support | answered | sim | - | 7247 | 0.00027796 |
| HV080-EN-SUP-ENABLEMENT-MASTERCARD-DEVICE | 1 | holdout_v080 | clarify | - | needs_clarification | não | route, status, tools, content, sources | 3280 | 0.00015387 |
| HV080-PT-SUP-FOREIGN-DEVICE | 1 | holdout_v080 | support | customer_support | answered | sim | - | 7114 | 0.00043941 |
| HV080-PT-KS-CREDIT-DECLINE-NOT-DEVICE | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | não | amounts | 14397 | 0.00103686 |
| HV080-EN-KS-WIFI-NEW-PASSWORD | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 9989 | 0.00080605 |
| HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | não | amounts | 17729 | 0.00122554 |
| HV080-PT-HANDOFF-CALLBACK | 1 | holdout_v080 | human_handoff | escalation | handoff | sim | - | 5828 | 0.00035637 |
| HV080-EN-HANDOFF-END-AGREEMENT | 1 | holdout_v080 | human_handoff | escalation | handoff | sim | - | 7342 | 0.00034477 |
| HV080-EN-OOS-SKIP-FRAUD-CHECK | 1 | holdout_v080 | out_of_scope | - | refused | sim | - | 4077 | 0.00014807 |
| HV080-PT-OOS-BUYER-PERSONAL-DATA | 1 | holdout_v080 | out_of_scope | - | refused | sim | - | 3066 | 0.00015207 |
| HV080-EN-KNOW-PHONE-AS-TERMINAL-HARD | 2 | holdout_v080 | knowledge | knowledge | answered | sim | - | 5528 | 0.00024825 |
| HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD | 2 | holdout_v080 | knowledge | knowledge | answered | sim | - | 5490 | 0.00019675 |
| HV080-PT-KNOW-CREDIARIO-PAYOUT | 2 | holdout_v080 | knowledge | knowledge | answered | sim | - | 6531 | 0.00025043 |
| HV080-EN-KNOW-SAME-DAY-REVERSAL | 2 | holdout_v080 | knowledge | knowledge | answered | sim | - | 9424 | 0.00026915 |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 2 | holdout_v080 | knowledge | knowledge | answered | sim | - | 8786 | 0.00042191 |
| HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD | 2 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 14405 | 0.00086454 |
| HV080-PT-WEB-CURITIBA-RAIN | 2 | holdout_v080 | general_web | knowledge | answered | não | content | 7316 | 0.01038406 |
| HV080-EN-WEB-USD-BRL | 2 | holdout_v080 | general_web | knowledge | answered | sim | - | 8938 | 0.01066361 |
| HV080-EN-SUP-RECEIVABLE-DEBIT-NET | 2 | holdout_v080 | support | customer_support | answered | sim | - | 7284 | 0.00056399 |
| HV080-EN-SUP-PAYOUT-LINK-SALE | 2 | holdout_v080 | support | customer_support | answered | sim | - | 9486 | 0.00043862 |
| HV080-PT-SUP-DEVICE-SIGNAL | 2 | holdout_v080 | support | customer_support | answered | sim | - | 10795 | 0.00049609 |
| HV080-EN-SUP-DEBIT-DECLINE-ISSUER | 2 | holdout_v080 | support | customer_support | answered | sim | - | 7013 | 0.00050125 |
| HV080-PT-SUP-CONTRACT-SETTLEMENT | 2 | holdout_v080 | support | customer_support | answered | sim | - | 7693 | 0.0004693 |
| HV080-PT-SUP-PRICE-LINK-CONSISTENT | 2 | holdout_v080 | support | customer_support | answered | não | amounts, content, sources, grounded | 9205 | 0.0005287 |
| HV080-EN-SUP-PRICE-CREDIT-CONDITIONS | 2 | holdout_v080 | support | customer_support | answered | não | content | 8064 | 0.00061805 |
| HV080-PT-SUP-CANCELLATION-REFUND | 2 | holdout_v080 | support | customer_support | answered | sim | - | 7264 | 0.00027122 |
| HV080-EN-SUP-ENABLEMENT-MASTERCARD-DEVICE | 2 | holdout_v080 | support | customer_support | answered | não | content | 8523 | 0.00044823 |
| HV080-PT-SUP-FOREIGN-DEVICE | 2 | holdout_v080 | support | customer_support | answered | sim | - | 6168 | 0.00043743 |
| HV080-PT-KS-CREDIT-DECLINE-NOT-DEVICE | 2 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 14183 | 0.00074207 |
| HV080-EN-KS-WIFI-NEW-PASSWORD | 2 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 11119 | 0.0006468 |
| HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD | 2 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 14657 | 0.00098892 |
| HV080-PT-HANDOFF-CALLBACK | 2 | holdout_v080 | human_handoff | escalation | handoff | sim | - | 6412 | 0.00034932 |
| HV080-EN-HANDOFF-END-AGREEMENT | 2 | holdout_v080 | human_handoff | escalation | handoff | sim | - | 5434 | 0.00034752 |
| HV080-EN-OOS-SKIP-FRAUD-CHECK | 2 | holdout_v080 | out_of_scope | - | refused | sim | - | 2518 | 0.00014339 |
| HV080-PT-OOS-BUYER-PERSONAL-DATA | 2 | holdout_v080 | out_of_scope | - | refused | sim | - | 2910 | 0.00014685 |
| HV080-EN-KNOW-PHONE-AS-TERMINAL-HARD | 3 | holdout_v080 | knowledge | knowledge | answered | sim | - | 6557 | 0.00025925 |
| HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD | 3 | holdout_v080 | knowledge | knowledge | answered | sim | - | 5428 | 0.00021285 |
| HV080-PT-KNOW-CREDIARIO-PAYOUT | 3 | holdout_v080 | knowledge | knowledge | answered | sim | - | 6860 | 0.00025193 |
| HV080-EN-KNOW-SAME-DAY-REVERSAL | 3 | holdout_v080 | knowledge | knowledge | answered | sim | - | 7935 | 0.00035665 |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 3 | holdout_v080 | knowledge | knowledge | answered | sim | - | 7640 | 0.00036481 |
| HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD | 3 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13652 | 0.00079193 |
| HV080-PT-WEB-CURITIBA-RAIN | 3 | holdout_v080 | general_web | knowledge | answered | sim | - | 6050 | 0.01038686 |
| HV080-EN-WEB-USD-BRL | 3 | holdout_v080 | general_web | knowledge | answered | sim | - | 6495 | 0.01066741 |
| HV080-EN-SUP-RECEIVABLE-DEBIT-NET | 3 | holdout_v080 | support | customer_support | answered | sim | - | 7620 | 0.00056849 |
| HV080-EN-SUP-PAYOUT-LINK-SALE | 3 | holdout_v080 | support | customer_support | answered | sim | - | 7344 | 0.00062039 |
| HV080-PT-SUP-DEVICE-SIGNAL | 3 | holdout_v080 | support | customer_support | answered | sim | - | 6910 | 0.00047999 |
| HV080-EN-SUP-DEBIT-DECLINE-ISSUER | 3 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 10244 | 0.00067516 |
| HV080-PT-SUP-CONTRACT-SETTLEMENT | 3 | holdout_v080 | knowledge | knowledge → customer_support | answered | não | route, content | 15375 | 0.00087003 |
| HV080-PT-SUP-PRICE-LINK-CONSISTENT | 3 | holdout_v080 | support | customer_support | answered | não | amounts, content, sources | 9013 | 0.0005309 |
| HV080-EN-SUP-PRICE-CREDIT-CONDITIONS | 3 | holdout_v080 | support | customer_support | answered | sim | - | 8336 | 0.00065715 |
| HV080-PT-SUP-CANCELLATION-REFUND | 3 | holdout_v080 | support | customer_support | answered | sim | - | 6996 | 0.00046584 |
| HV080-EN-SUP-ENABLEMENT-MASTERCARD-DEVICE | 3 | holdout_v080 | support | customer_support | answered | não | content | 6764 | 0.0002702 |
| HV080-PT-SUP-FOREIGN-DEVICE | 3 | holdout_v080 | support | customer_support | answered | sim | - | 6860 | 0.00043873 |
| HV080-PT-KS-CREDIT-DECLINE-NOT-DEVICE | 3 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 11989 | 0.00075483 |
| HV080-EN-KS-WIFI-NEW-PASSWORD | 3 | holdout_v080 | clarify | - | needs_clarification | não | route, status, tools, content, sources | 1898 | 0.0005006 |
| HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD | 3 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 16521 | 0.00100654 |
| HV080-PT-HANDOFF-CALLBACK | 3 | holdout_v080 | human_handoff | escalation | handoff | sim | - | 5770 | 0.00035202 |
| HV080-EN-HANDOFF-END-AGREEMENT | 3 | holdout_v080 | human_handoff | escalation | handoff | sim | - | 7386 | 0.00034602 |
| HV080-EN-OOS-SKIP-FRAUD-CHECK | 3 | holdout_v080 | out_of_scope | - | refused | sim | - | 2718 | 0.00014339 |
| HV080-PT-OOS-BUYER-PERSONAL-DATA | 3 | holdout_v080 | out_of_scope | - | refused | sim | - | 3556 | 0.00014485 |
