# Relatório de avaliação: v0110-qa-holdout-v080

Gerado em 2026-11-07T03:56:39+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "holdout_v080", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 3, "limit": null, "include_replan": false, "web_evidence": "on", "ruler": "combined", "campaign": null, "campaign_cap_usd": null, "cases": 25}`.

Régua combinada (spec v0.11.0 D8): uma resposta passa quando passa a parte determinística (rota, status, idioma, ferramentas, valores, frases proibidas, fontes e sem violação da guarda) e o conteúdo julgado pelo juiz (nota ≥ 4 em correção factual e relevância e nenhuma afirmação sem suporte, no primeiro julgamento). As frases obrigatórias dos rótulos não decidem: aparecem como informação. Aprovadas: 60 de 75; pela régua literal (`--rubric literal`), 64 de 75.

## Resumo

| Recorte | n | Aprovados | Determinístico | Conteúdo (juiz) | Rota | Status | Ferramentas | Valores | Frases obrigatórias (informativo) | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 75 | 0.8 | 0.92 | 0.867 | 0.96 | 0.987 | 1.0 | 0.96 | 0.88 | 0.96 | 0.973 | 7263 | 15993 | 0.10853 |
| split holdout_v080 | 75 | 0.8 | 0.92 | 0.867 | 0.96 | 0.987 | 1.0 | 0.96 | 0.88 | 0.96 | 0.973 | 7263 | 15993 | 0.10853 |
| idioma en | 36 | 0.917 | 0.972 | 0.944 | 0.972 | 1.0 | 1.0 | 1.0 | 0.889 | 1.0 | 1.0 | 7252 | 11997 | 0.04658 |
| idioma pt | 39 | 0.692 | 0.872 | 0.795 | 0.949 | 0.974 | 1.0 | 0.923 | 0.872 | 0.923 | 0.949 | 7404 | 17299 | 0.06195 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 4.71, correção factual 4.71, relevância 4.85, utilidade 4.73. Afirmações sem suporte: 0.067 das respostas julgadas. Custo do juiz: US$ 0.03377.

Tokens do juiz (75 julgamentos com uso registrado; total / média por julgamento): entrada 152880 / 2038.4, da qual cache lido 87296 / 1163.9 e cache criado 0 / 0.0; saída (com o pensamento) 11310 / 150.8. Custo do juiz: US$ 0.03377.

Respostas julgadas sob a nota de busca web: 3 de 75. São as respostas com ao menos um passo de busca sem URL gravada no trace (ou avaliadas com `WEB_EVIDENCE=off`): desse passo o juiz não recebe o texto das páginas nem o resumo da busca, só os títulos das fontes; o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 0 foram marcadas como afirmação sem suporte.

Evidência truncada em 3 de 75 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Afirmações sem suporte (veredito crítico)

Listadas uma a uma, nunca diluídas na média.

| Caso | Rep | Rota | Julgamentos marcados | Fundamentação (primeiro julgamento marcado) |
| --- | --- | --- | --- | --- |
| HV080-EN-KNOW-SAME-DAY-REVERSAL | 1 | knowledge | 1 de 1 | The same-day rule is supported, but selecting "Estorno" and using the same card are not in the evidence. |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 1 | knowledge | 1 de 1 | The R$1,00 per link fee is not in the evidence; the rest (date, migration to Link de Pagamento) is supported. |
| HV080-EN-KNOW-SAME-DAY-REVERSAL | 2 | knowledge | 1 de 1 | Same-day rule and date step are supported, but selecting Estorno and entering amount/card details are not in the passage. |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 2 | knowledge | 1 de 1 | Migration, date and link package are supported, but the R$1,00 per paid link price appears nowhere in the evidence. |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 3 | knowledge | 1 de 1 | Most is supported by the passage, but the R$1,00 per link price is not in the evidence. |

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| general_web | knowledge | 6 |
| human_handoff | escalation | 6 |
| knowledge | knowledge | 15 |
| knowledge | knowledge → customer_support | 1 |
| knowledge | knowledge → customer_support → web | 1 |
| knowledge_and_support | knowledge → customer_support | 12 |
| out_of_scope | - | 6 |
| support | customer_support | 27 |
| support | customer_support → knowledge | 1 |

## Variação: variação do assistente (o agente roda cada caso N vezes e o juiz avalia cada resposta uma vez)

Repetições por caso: 3. Desvio: média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou com diferença de até 1 ponto (±1).

> Ressalva de amostra pequena (D19): 25 casos com 3 repetições cada; os recortes por rota e por split têm menos casos ainda (marcados com * quando há menos de 10). Médias, desvios e concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno.

| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 25 | groundedness | 4.71 | 0.14 | 0.84 | 1.0 | 75 |
| geral | 25 | factual_correctness | 4.71 | 0.12 | 0.867 | 1.0 | 75 |
| geral | 25 | relevance | 4.85 | 0.18 | 0.813 | 0.973 | 75 |
| geral | 25 | usefulness | 4.73 | 0.18 | 0.813 | 0.973 | 75 |
| geral | 25 | unsupported_claim (taxa de verdadeiro) | 0.067 | - | 0.973 | - | 75 |
| rota general_web | 2* | groundedness | 4.17 | 0.29 | 0.667 | 1.0 | 6 |
| rota general_web | 2* | factual_correctness | 4.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota general_web | 2* | relevance | 4.67 | 0.29 | 0.667 | 1.0 | 6 |
| rota general_web | 2* | usefulness | 4.33 | 0.29 | 0.667 | 1.0 | 6 |
| rota general_web | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota human_handoff | 2* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | usefulness | 4.67 | 0.29 | 0.667 | 1.0 | 6 |
| rota human_handoff | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota knowledge | 6* | groundedness | 4.28 | 0.19 | 0.778 | 1.0 | 18 |
| rota knowledge | 6* | factual_correctness | 4.33 | 0.19 | 0.778 | 1.0 | 18 |
| rota knowledge | 6* | relevance | 4.89 | 0.19 | 0.778 | 1.0 | 18 |
| rota knowledge | 6* | usefulness | 4.67 | 0.0 | 1.0 | 1.0 | 18 |
| rota knowledge | 6* | unsupported_claim (taxa de verdadeiro) | 0.278 | - | 0.889 | - | 18 |
| rota knowledge_and_support | 3* | groundedness | 4.89 | 0.19 | 0.778 | 1.0 | 9 |
| rota knowledge_and_support | 3* | factual_correctness | 4.67 | 0.38 | 0.556 | 1.0 | 9 |
| rota knowledge_and_support | 3* | relevance | 4.78 | 0.38 | 0.556 | 1.0 | 9 |
| rota knowledge_and_support | 3* | usefulness | 4.89 | 0.19 | 0.778 | 1.0 | 9 |
| rota knowledge_and_support | 3* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 9 |
| rota out_of_scope | 2* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota support | 10 | groundedness | 4.9 | 0.12 | 0.867 | 1.0 | 30 |
| rota support | 10 | factual_correctness | 4.97 | 0.06 | 0.933 | 1.0 | 30 |
| rota support | 10 | relevance | 4.83 | 0.17 | 0.867 | 0.933 | 30 |
| rota support | 10 | usefulness | 4.77 | 0.29 | 0.733 | 0.933 | 30 |
| rota support | 10 | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 30 |
| split holdout_v080 | 25 | groundedness | 4.71 | 0.14 | 0.84 | 1.0 | 75 |
| split holdout_v080 | 25 | factual_correctness | 4.71 | 0.12 | 0.867 | 1.0 | 75 |
| split holdout_v080 | 25 | relevance | 4.85 | 0.18 | 0.813 | 0.973 | 75 |
| split holdout_v080 | 25 | usefulness | 4.73 | 0.18 | 0.813 | 0.973 | 75 |
| split holdout_v080 | 25 | unsupported_claim (taxa de verdadeiro) | 0.067 | - | 0.973 | - | 75 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Determinístico | Conteúdo | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HV080-EN-KNOW-PHONE-AS-TERMINAL-HARD | 1 | holdout_v080 | knowledge | knowledge | answered | sim | sim | sim | - | 8035 | 0.00044087 |
| HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD | 1 | holdout_v080 | knowledge | knowledge | answered | sim | sim | sim | - | 6482 | 0.00042697 |
| HV080-PT-KNOW-CREDIARIO-PAYOUT | 1 | holdout_v080 | knowledge | knowledge | answered | sim | sim | sim | - | 6518 | 0.00046077 |
| HV080-EN-KNOW-SAME-DAY-REVERSAL | 1 | holdout_v080 | knowledge | knowledge | answered | sim | não | não | conteúdo | 7200 | 0.00045317 |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 1 | holdout_v080 | knowledge | knowledge | answered | sim | não | não | conteúdo | 9491 | 0.00063267 |
| HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | sim | sim | - | 18842 | 0.00109991 |
| HV080-PT-WEB-CURITIBA-RAIN | 1 | holdout_v080 | general_web | knowledge | answered | sim | não | não | conteúdo | 6476 | 0.01040151 |
| HV080-EN-WEB-USD-BRL | 1 | holdout_v080 | general_web | knowledge | answered | sim | sim | sim | - | 7242 | 0.0106318 |
| HV080-EN-SUP-RECEIVABLE-DEBIT-NET | 1 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 11909 | 0.00056528 |
| HV080-EN-SUP-PAYOUT-LINK-SALE | 1 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 10811 | 0.00064507 |
| HV080-PT-SUP-DEVICE-SIGNAL | 1 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 6453 | 0.00045964 |
| HV080-EN-SUP-DEBIT-DECLINE-ISSUER | 1 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 8748 | 0.00051431 |
| HV080-PT-SUP-CONTRACT-SETTLEMENT | 1 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 8839 | 0.00046289 |
| HV080-PT-SUP-PRICE-LINK-CONSISTENT | 1 | holdout_v080 | support | customer_support | answered | não | sim | não | amounts, sources, grounded | 9573 | 0.00053661 |
| HV080-EN-SUP-PRICE-CREDIT-CONDITIONS | 1 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 8733 | 0.00063398 |
| HV080-PT-SUP-CANCELLATION-REFUND | 1 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 6812 | 0.00046988 |
| HV080-EN-SUP-ENABLEMENT-MASTERCARD-DEVICE | 1 | holdout_v080 | knowledge | knowledge → customer_support | answered | não | sim | não | route | 11670 | 0.00086696 |
| HV080-PT-SUP-FOREIGN-DEVICE | 1 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 5453 | 0.00043391 |
| HV080-PT-KS-CREDIT-DECLINE-NOT-DEVICE | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | sim | sim | - | 12375 | 0.00092802 |
| HV080-EN-KS-WIFI-NEW-PASSWORD | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | sim | sim | - | 9597 | 0.00084298 |
| HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD | 1 | holdout_v080 | support | customer_support → knowledge | answered | não | sim | não | route | 13704 | 0.00110432 |
| HV080-PT-HANDOFF-CALLBACK | 1 | holdout_v080 | human_handoff | escalation | handoff | sim | sim | sim | - | 5582 | 0.00035137 |
| HV080-EN-HANDOFF-END-AGREEMENT | 1 | holdout_v080 | human_handoff | escalation | handoff | sim | sim | sim | - | 6046 | 0.00034997 |
| HV080-EN-OOS-SKIP-FRAUD-CHECK | 1 | holdout_v080 | out_of_scope | - | refused | sim | sim | sim | - | 2536 | 0.00014807 |
| HV080-PT-OOS-BUYER-PERSONAL-DATA | 1 | holdout_v080 | out_of_scope | - | refused | sim | sim | sim | - | 2696 | 0.00015257 |
| HV080-EN-KNOW-PHONE-AS-TERMINAL-HARD | 2 | holdout_v080 | knowledge | knowledge | answered | sim | sim | sim | - | 4905 | 0.00024227 |
| HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD | 2 | holdout_v080 | knowledge | knowledge | answered | sim | sim | sim | - | 4402 | 0.00020491 |
| HV080-PT-KNOW-CREDIARIO-PAYOUT | 2 | holdout_v080 | knowledge | knowledge | answered | sim | sim | sim | - | 5359 | 0.00025463 |
| HV080-EN-KNOW-SAME-DAY-REVERSAL | 2 | holdout_v080 | knowledge | knowledge | answered | sim | não | não | conteúdo | 6209 | 0.00029796 |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 2 | holdout_v080 | knowledge | knowledge | answered | sim | não | não | conteúdo | 12058 | 0.00035775 |
| HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD | 2 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | sim | sim | - | 14158 | 0.00079315 |
| HV080-PT-WEB-CURITIBA-RAIN | 2 | holdout_v080 | general_web | knowledge | answered | sim | não | não | conteúdo | 6249 | 0.01039506 |
| HV080-EN-WEB-USD-BRL | 2 | holdout_v080 | general_web | knowledge | answered | sim | sim | sim | - | 6262 | 0.01062271 |
| HV080-EN-SUP-RECEIVABLE-DEBIT-NET | 2 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 7263 | 0.00057119 |
| HV080-EN-SUP-PAYOUT-LINK-SALE | 2 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 9059 | 0.00045142 |
| HV080-PT-SUP-DEVICE-SIGNAL | 2 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 7025 | 0.00045849 |
| HV080-EN-SUP-DEBIT-DECLINE-ISSUER | 2 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 7359 | 0.00051315 |
| HV080-PT-SUP-CONTRACT-SETTLEMENT | 2 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | não | não | conteúdo | 13365 | 0.00088693 |
| HV080-PT-SUP-PRICE-LINK-CONSISTENT | 2 | holdout_v080 | support | customer_support | answered | não | sim | não | amounts, sources | 7404 | 0.0005017 |
| HV080-EN-SUP-PRICE-CREDIT-CONDITIONS | 2 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 13728 | 0.00062635 |
| HV080-PT-SUP-CANCELLATION-REFUND | 2 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 6830 | 0.00045504 |
| HV080-EN-SUP-ENABLEMENT-MASTERCARD-DEVICE | 2 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 7673 | 0.0002637 |
| HV080-PT-SUP-FOREIGN-DEVICE | 2 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 6441 | 0.00044023 |
| HV080-PT-KS-CREDIT-DECLINE-NOT-DEVICE | 2 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | sim | sim | - | 14341 | 0.00085491 |
| HV080-EN-KS-WIFI-NEW-PASSWORD | 2 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | sim | sim | - | 16491 | 0.00066988 |
| HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD | 2 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | sim | sim | - | 15993 | 0.00119428 |
| HV080-PT-HANDOFF-CALLBACK | 2 | holdout_v080 | human_handoff | escalation | handoff | sim | sim | sim | - | 6528 | 0.00035302 |
| HV080-EN-HANDOFF-END-AGREEMENT | 2 | holdout_v080 | human_handoff | escalation | handoff | sim | sim | sim | - | 6660 | 0.00034002 |
| HV080-EN-OOS-SKIP-FRAUD-CHECK | 2 | holdout_v080 | out_of_scope | - | refused | sim | sim | sim | - | 3379 | 0.00014339 |
| HV080-PT-OOS-BUYER-PERSONAL-DATA | 2 | holdout_v080 | out_of_scope | - | refused | sim | sim | sim | - | 2983 | 0.00014635 |
| HV080-EN-KNOW-PHONE-AS-TERMINAL-HARD | 3 | holdout_v080 | knowledge | knowledge | answered | sim | sim | sim | - | 5886 | 0.00023947 |
| HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD | 3 | holdout_v080 | knowledge | knowledge | answered | sim | sim | sim | - | 5624 | 0.00019221 |
| HV080-PT-KNOW-CREDIARIO-PAYOUT | 3 | holdout_v080 | knowledge | knowledge | answered | sim | sim | sim | - | 5842 | 0.00025753 |
| HV080-EN-KNOW-SAME-DAY-REVERSAL | 3 | holdout_v080 | knowledge | knowledge | answered | sim | sim | sim | - | 7796 | 0.00027426 |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 3 | holdout_v080 | knowledge | knowledge | answered | sim | não | não | conteúdo | 7942 | 0.00037745 |
| HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD | 3 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | sim | sim | - | 13340 | 0.00077383 |
| HV080-PT-WEB-CURITIBA-RAIN | 3 | holdout_v080 | general_web | knowledge | answered | sim | não | não | conteúdo | 5735 | 0.01040056 |
| HV080-EN-WEB-USD-BRL | 3 | holdout_v080 | general_web | knowledge | answered | sim | sim | sim | - | 6095 | 0.01062541 |
| HV080-EN-SUP-RECEIVABLE-DEBIT-NET | 3 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 7350 | 0.00056869 |
| HV080-EN-SUP-PAYOUT-LINK-SALE | 3 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 7766 | 0.00044752 |
| HV080-PT-SUP-DEVICE-SIGNAL | 3 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 6330 | 0.00048889 |
| HV080-EN-SUP-DEBIT-DECLINE-ISSUER | 3 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 6769 | 0.00050845 |
| HV080-PT-SUP-CONTRACT-SETTLEMENT | 3 | holdout_v080 | knowledge | knowledge → customer_support → web | answered | não | não | não | route, conteúdo | 17511 | 0.01156962 |
| HV080-PT-SUP-PRICE-LINK-CONSISTENT | 3 | holdout_v080 | support | customer_support | needs_clarification | não | sim | não | status, amounts, sources, grounded | 17299 | 0.0004852 |
| HV080-EN-SUP-PRICE-CREDIT-CONDITIONS | 3 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 7774 | 0.00064495 |
| HV080-PT-SUP-CANCELLATION-REFUND | 3 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 11356 | 0.00027002 |
| HV080-EN-SUP-ENABLEMENT-MASTERCARD-DEVICE | 3 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 6293 | 0.00047103 |
| HV080-PT-SUP-FOREIGN-DEVICE | 3 | holdout_v080 | support | customer_support | answered | sim | sim | sim | - | 6956 | 0.00043583 |
| HV080-PT-KS-CREDIT-DECLINE-NOT-DEVICE | 3 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | sim | sim | - | 12875 | 0.00076934 |
| HV080-EN-KS-WIFI-NEW-PASSWORD | 3 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | sim | sim | - | 11997 | 0.00066153 |
| HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD | 3 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | sim | sim | - | 15466 | 0.0010424 |
| HV080-PT-HANDOFF-CALLBACK | 3 | holdout_v080 | human_handoff | escalation | handoff | sim | sim | sim | - | 7664 | 0.00034622 |
| HV080-EN-HANDOFF-END-AGREEMENT | 3 | holdout_v080 | human_handoff | escalation | handoff | sim | sim | sim | - | 5202 | 0.00033722 |
| HV080-EN-OOS-SKIP-FRAUD-CHECK | 3 | holdout_v080 | out_of_scope | - | refused | sim | sim | sim | - | 2440 | 0.00014339 |
| HV080-PT-OOS-BUYER-PERSONAL-DATA | 3 | holdout_v080 | out_of_scope | - | refused | sim | sim | sim | - | 3211 | 0.00014635 |

## Evidência da busca web

Evidência da busca web (tarefa 87), em 75 respostas com evidência gravada: 4 com página citada buscada na avaliação, 0 com o resumo da busca no lugar de uma página indisponível e 3 sem URL gravada (só os títulos das fontes).
