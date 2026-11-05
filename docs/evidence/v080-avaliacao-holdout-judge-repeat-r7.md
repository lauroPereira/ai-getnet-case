# Relatório de avaliação: v080-r7-1baa7b31-holdout-judge

Gerado em 2026-11-05T11:02:54+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "holdout_v080", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 1, "judge_repeat": 3, "answers_from": "v080-r7-1baa7b31-holdout.json", "campaign": "v080-qa", "campaign_cap_usd": 1.4, "cases": 25}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 25 | 0.8 | 0.92 | 0.96 | 0.96 | 0.88 | 0.88 | 0.92 | 0.96 | 8251 | 17729 | 0 |
| split holdout_v080 | 25 | 0.8 | 0.92 | 0.96 | 0.96 | 0.88 | 0.88 | 0.92 | 0.96 | 8251 | 17729 | 0 |
| idioma en | 12 | 0.917 | 0.917 | 0.917 | 0.917 | 1.0 | 0.917 | 0.917 | 1.0 | 8948 | 10549 | 0 |
| idioma pt | 13 | 0.692 | 0.923 | 1.0 | 1.0 | 0.769 | 0.846 | 0.923 | 0.923 | 7773 | 17729 | 0 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 4.61, correção factual 4.59, relevância 4.8, utilidade 4.6. Afirmações sem suporte: 0.107 das respostas julgadas. Custo do juiz: US$ 0.01933.

Respostas julgadas sob a nota de busca web: 3 de 25. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 1 foram marcadas como afirmação sem suporte.

Evidência truncada em 0 de 25 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Afirmações sem suporte (veredito crítico)

Listadas uma a uma, nunca diluídas na média.

| Caso | Rep | Rota | Julgamentos marcados | Fundamentação (primeiro julgamento marcado) |
| --- | --- | --- | --- | --- |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 1 | knowledge | 3 de 3 | Most facts match the passage, but the statement of R$1,00 per link is not in the evidence. |
| HV080-PT-WEB-CURITIBA-RAIN | 1 | general_web | 3 de 3 | Web text not available; date and INMET alert are specifics not shown in the listed source titles, though weather forecast is consistent. |
| HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD | 1 | knowledge_and_support | 2 de 3 | Steps and Pix timing are supported, but it ignores the payout tool result showing the Pix was confirmed credited on 04/11/2026 17:31. |

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| clarify | - | 1 |
| general_web | knowledge | 2 |
| human_handoff | escalation | 2 |
| knowledge | knowledge | 5 |
| knowledge | knowledge → customer_support → web | 1 |
| knowledge_and_support | knowledge → customer_support | 5 |
| out_of_scope | - | 2 |
| support | customer_support | 7 |

## Variação: variação do juiz (as mesmas respostas gravadas avaliadas N vezes)

Repetições por caso: 3. Desvio: média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou com diferença de até 1 ponto (±1).

> Ressalva de amostra pequena (D19): 25 casos com 3 repetições cada; os recortes por rota e por split têm menos casos ainda (marcados com * quando há menos de 10). Médias, desvios e concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno.

| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 25 | groundedness | 4.61 | 0.13 | 0.853 | 0.987 | 75 |
| geral | 25 | factual_correctness | 4.59 | 0.13 | 0.88 | 0.973 | 75 |
| geral | 25 | relevance | 4.8 | 0.14 | 0.84 | 1.0 | 75 |
| geral | 25 | usefulness | 4.6 | 0.16 | 0.813 | 1.0 | 75 |
| geral | 25 | unsupported_claim (taxa de verdadeiro) | 0.107 | - | 0.973 | - | 75 |
| rota clarify | 1* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |
| rota general_web | 2* | groundedness | 2.83 | 0.29 | 0.667 | 1.0 | 6 |
| rota general_web | 2* | factual_correctness | 2.67 | 0.29 | 0.667 | 1.0 | 6 |
| rota general_web | 2* | relevance | 4.83 | 0.29 | 0.667 | 1.0 | 6 |
| rota general_web | 2* | usefulness | 3.83 | 0.29 | 0.667 | 1.0 | 6 |
| rota general_web | 2* | unsupported_claim (taxa de verdadeiro) | 0.5 | - | 1.0 | - | 6 |
| rota human_handoff | 2* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota knowledge | 6* | groundedness | 4.33 | 0.19 | 0.778 | 1.0 | 18 |
| rota knowledge | 6* | factual_correctness | 4.33 | 0.19 | 0.778 | 1.0 | 18 |
| rota knowledge | 6* | relevance | 4.56 | 0.19 | 0.778 | 1.0 | 18 |
| rota knowledge | 6* | usefulness | 4.33 | 0.19 | 0.778 | 1.0 | 18 |
| rota knowledge | 6* | unsupported_claim (taxa de verdadeiro) | 0.167 | - | 1.0 | - | 18 |
| rota knowledge_and_support | 5* | groundedness | 4.8 | 0.2 | 0.8 | 0.933 | 15 |
| rota knowledge_and_support | 5* | factual_correctness | 4.67 | 0.31 | 0.8 | 0.867 | 15 |
| rota knowledge_and_support | 5* | relevance | 4.73 | 0.12 | 0.867 | 1.0 | 15 |
| rota knowledge_and_support | 5* | usefulness | 4.73 | 0.12 | 0.867 | 1.0 | 15 |
| rota knowledge_and_support | 5* | unsupported_claim (taxa de verdadeiro) | 0.133 | - | 0.867 | - | 15 |
| rota out_of_scope | 2* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | relevance | 4.83 | 0.29 | 0.667 | 1.0 | 6 |
| rota out_of_scope | 2* | usefulness | 4.83 | 0.29 | 0.667 | 1.0 | 6 |
| rota out_of_scope | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota support | 7* | groundedness | 4.95 | 0.08 | 0.905 | 1.0 | 21 |
| rota support | 7* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 21 |
| rota support | 7* | relevance | 4.95 | 0.08 | 0.905 | 1.0 | 21 |
| rota support | 7* | usefulness | 4.71 | 0.16 | 0.81 | 1.0 | 21 |
| rota support | 7* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 21 |
| split holdout_v080 | 25 | groundedness | 4.61 | 0.13 | 0.853 | 0.987 | 75 |
| split holdout_v080 | 25 | factual_correctness | 4.59 | 0.13 | 0.88 | 0.973 | 75 |
| split holdout_v080 | 25 | relevance | 4.8 | 0.14 | 0.84 | 1.0 | 75 |
| split holdout_v080 | 25 | usefulness | 4.6 | 0.16 | 0.813 | 1.0 | 75 |
| split holdout_v080 | 25 | unsupported_claim (taxa de verdadeiro) | 0.107 | - | 0.973 | - | 75 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HV080-EN-KNOW-PHONE-AS-TERMINAL-HARD | 1 | holdout_v080 | knowledge | knowledge | answered | sim | - | 10549 | 0.0 |
| HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD | 1 | holdout_v080 | knowledge | knowledge | answered | sim | - | 9552 | 0.0 |
| HV080-PT-KNOW-CREDIARIO-PAYOUT | 1 | holdout_v080 | knowledge | knowledge | answered | sim | - | 7773 | 0.0 |
| HV080-EN-KNOW-SAME-DAY-REVERSAL | 1 | holdout_v080 | knowledge | knowledge | answered | sim | - | 8927 | 0.0 |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | 1 | holdout_v080 | knowledge | knowledge | answered | sim | - | 8556 | 0.0 |
| HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13430 | 0.0 |
| HV080-PT-WEB-CURITIBA-RAIN | 1 | holdout_v080 | general_web | knowledge | answered | sim | - | 6225 | 0.0 |
| HV080-EN-WEB-USD-BRL | 1 | holdout_v080 | general_web | knowledge | answered | sim | - | 7586 | 0.0 |
| HV080-EN-SUP-RECEIVABLE-DEBIT-NET | 1 | holdout_v080 | support | customer_support | answered | sim | - | 7915 | 0.0 |
| HV080-EN-SUP-PAYOUT-LINK-SALE | 1 | holdout_v080 | support | customer_support | answered | sim | - | 9070 | 0.0 |
| HV080-PT-SUP-DEVICE-SIGNAL | 1 | holdout_v080 | support | customer_support | answered | sim | - | 7127 | 0.0 |
| HV080-EN-SUP-DEBIT-DECLINE-ISSUER | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13252 | 0.0 |
| HV080-PT-SUP-CONTRACT-SETTLEMENT | 1 | holdout_v080 | knowledge | knowledge → customer_support → web | answered | não | route, content | 21953 | 0.0 |
| HV080-PT-SUP-PRICE-LINK-CONSISTENT | 1 | holdout_v080 | support | customer_support | answered | não | amounts, content, sources, grounded | 8251 | 0.0 |
| HV080-EN-SUP-PRICE-CREDIT-CONDITIONS | 1 | holdout_v080 | support | customer_support | answered | sim | - | 8970 | 0.0 |
| HV080-PT-SUP-CANCELLATION-REFUND | 1 | holdout_v080 | support | customer_support | answered | sim | - | 7247 | 0.0 |
| HV080-EN-SUP-ENABLEMENT-MASTERCARD-DEVICE | 1 | holdout_v080 | clarify | - | needs_clarification | não | route, status, tools, content, sources | 3280 | 0.0 |
| HV080-PT-SUP-FOREIGN-DEVICE | 1 | holdout_v080 | support | customer_support | answered | sim | - | 7114 | 0.0 |
| HV080-PT-KS-CREDIT-DECLINE-NOT-DEVICE | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | não | amounts | 14397 | 0.0 |
| HV080-EN-KS-WIFI-NEW-PASSWORD | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | sim | - | 9989 | 0.0 |
| HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD | 1 | holdout_v080 | knowledge_and_support | knowledge → customer_support | answered | não | amounts | 17729 | 0.0 |
| HV080-PT-HANDOFF-CALLBACK | 1 | holdout_v080 | human_handoff | escalation | handoff | sim | - | 5828 | 0.0 |
| HV080-EN-HANDOFF-END-AGREEMENT | 1 | holdout_v080 | human_handoff | escalation | handoff | sim | - | 7342 | 0.0 |
| HV080-EN-OOS-SKIP-FRAUD-CHECK | 1 | holdout_v080 | out_of_scope | - | refused | sim | - | 4077 | 0.0 |
| HV080-PT-OOS-BUYER-PERSONAL-DATA | 1 | holdout_v080 | out_of_scope | - | refused | sim | - | 3066 | 0.0 |
