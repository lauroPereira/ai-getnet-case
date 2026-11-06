# Relatório de avaliação: v0100-juiz-opus-v4

Gerado em 2026-11-06T03:25:40+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "all", "judge": true, "judge_config": {"provider": "anthropic", "model": "claude-opus-5-5", "rubric": "judge", "rubric_version": "4", "prompt": "judge@4", "independence": "different_provider", "parameters": {"max_output_tokens": 2000, "effort": "default", "thinking": "default"}}, "repeat": 1, "judge_repeat": 3, "answers_from": "v080-all-r3.json", "recorded_answers": 44, "only_sample": "v080-calibracao-amostra.csv", "only_sample_ids": 24, "selected_answers": 24, "campaign": null, "campaign_cap_usd": null, "cases": 24}`.

Respostas julgadas: 24 de 44 gravadas, filtradas pelos 24 request_id de `v080-calibracao-amostra.csv`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 24 | 0.833 | 1.0 | 0.958 | 1.0 | 1.0 | 0.833 | 1.0 | 1.0 | 6524 | 16753 | 0 |
| split dev | 11 | 0.727 | 1.0 | 0.909 | 1.0 | 1.0 | 0.727 | 1.0 | 1.0 | 6664 | 23363 | 0 |
| split holdout | 13 | 0.923 | 1.0 | 1.0 | 1.0 | 1.0 | 0.923 | 1.0 | 1.0 | 6385 | 11419 | 0 |
| idioma en | 11 | 0.909 | 1.0 | 1.0 | 1.0 | 1.0 | 0.909 | 1.0 | 1.0 | 5935 | 14187 | 0 |
| idioma pt | 13 | 0.769 | 1.0 | 0.923 | 1.0 | 1.0 | 0.769 | 1.0 | 1.0 | 8534 | 16753 | 0 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 4.61, correção factual 4.54, relevância 4.76, utilidade 4.38. Afirmações sem suporte: 0.097 das respostas julgadas. Custo do juiz: US$ 1.31557.

Tokens do juiz (72 julgamentos com uso registrado; total / média por julgamento): entrada 225927 / 3137.9, da qual cache lido 0 / 0.0 e cache criado 0 / 0.0; saída (com o pensamento) 20593 / 286.0. Custo do juiz: US$ 1.31557.

Respostas julgadas sob a nota de busca web: 6 de 24. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v4` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 1 foram marcadas como afirmação sem suporte.

Evidência truncada em 1 de 24 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Afirmações sem suporte (veredito crítico)

Listadas uma a uma, nunca diluídas na média.

| Caso | Rep | Rota | Julgamentos marcados | Fundamentação (primeiro julgamento marcado) |
| --- | --- | --- | --- | --- |
| PT06 | 1 | knowledge | 3 de 3 | Most steps, the R$50 minimum, 48 hours and individual evaluation are supported, but 'taxas variam conforme o contrato' has no source. |
| NOEV | 1 | knowledge | 1 de 3 | The web text was unavailable; the general rate-variation statement fits the sources, but no source mentions a Get Ultra Pro 9000. |
| PT09 | 1 | knowledge | 3 de 3 | The 48x limit, issuer variation and where to check the MDR are supported; 'depend on the contract' and 'issuer credit policies' are not. |

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| clarify | - | 1 |
| general_web | knowledge | 4 |
| human_handoff | escalation | 2 |
| knowledge | knowledge | 4 |
| knowledge | knowledge → customer_support → web | 1 |
| knowledge | knowledge → web | 1 |
| knowledge_and_support | knowledge → customer_support | 4 |
| out_of_scope | - | 2 |
| support | customer_support | 5 |

## Variação: variação do juiz (as mesmas respostas gravadas avaliadas N vezes)

Repetições por caso: 3. Desvio: média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou com diferença de até 1 ponto (±1).

> Ressalva de amostra pequena (D19): 24 casos com 3 repetições cada; os recortes por rota e por split têm menos casos ainda (marcados com * quando há menos de 10). Médias, desvios e concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno.

| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 24 | groundedness | 4.61 | 0.02 | 0.972 | 1.0 | 72 |
| geral | 24 | factual_correctness | 4.54 | 0.0 | 1.0 | 1.0 | 72 |
| geral | 24 | relevance | 4.76 | 0.07 | 0.917 | 1.0 | 72 |
| geral | 24 | usefulness | 4.38 | 0.17 | 0.806 | 1.0 | 72 |
| geral | 24 | unsupported_claim (taxa de verdadeiro) | 0.097 | - | 0.972 | - | 72 |
| rota clarify | 1* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | usefulness | 4.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |
| rota general_web | 4* | groundedness | 4.0 | 0.0 | 1.0 | 1.0 | 12 |
| rota general_web | 4* | factual_correctness | 4.0 | 0.0 | 1.0 | 1.0 | 12 |
| rota general_web | 4* | relevance | 4.75 | 0.29 | 0.667 | 1.0 | 12 |
| rota general_web | 4* | usefulness | 4.75 | 0.29 | 0.667 | 1.0 | 12 |
| rota general_web | 4* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 12 |
| rota human_handoff | 2* | groundedness | 4.33 | 0.29 | 0.667 | 1.0 | 6 |
| rota human_handoff | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | usefulness | 4.5 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota knowledge | 6* | groundedness | 4.33 | 0.0 | 1.0 | 1.0 | 18 |
| rota knowledge | 6* | factual_correctness | 4.0 | 0.0 | 1.0 | 1.0 | 18 |
| rota knowledge | 6* | relevance | 4.56 | 0.1 | 0.889 | 1.0 | 18 |
| rota knowledge | 6* | usefulness | 4.22 | 0.38 | 0.556 | 1.0 | 18 |
| rota knowledge | 6* | unsupported_claim (taxa de verdadeiro) | 0.389 | - | 0.889 | - | 18 |
| rota knowledge_and_support | 4* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 12 |
| rota knowledge_and_support | 4* | factual_correctness | 4.75 | 0.0 | 1.0 | 1.0 | 12 |
| rota knowledge_and_support | 4* | relevance | 4.75 | 0.0 | 1.0 | 1.0 | 12 |
| rota knowledge_and_support | 4* | usefulness | 4.17 | 0.14 | 0.833 | 1.0 | 12 |
| rota knowledge_and_support | 4* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 12 |
| rota out_of_scope | 2* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | usefulness | 4.5 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota support | 5* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 15 |
| rota support | 5* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 15 |
| rota support | 5* | relevance | 4.8 | 0.0 | 1.0 | 1.0 | 15 |
| rota support | 5* | usefulness | 4.4 | 0.0 | 1.0 | 1.0 | 15 |
| rota support | 5* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 15 |
| split dev | 11 | groundedness | 4.79 | 0.05 | 0.939 | 1.0 | 33 |
| split dev | 11 | factual_correctness | 4.64 | 0.0 | 1.0 | 1.0 | 33 |
| split dev | 11 | relevance | 4.79 | 0.1 | 0.879 | 1.0 | 33 |
| split dev | 11 | usefulness | 4.3 | 0.16 | 0.818 | 1.0 | 33 |
| split dev | 11 | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 33 |
| split holdout | 13 | groundedness | 4.46 | 0.0 | 1.0 | 1.0 | 39 |
| split holdout | 13 | factual_correctness | 4.46 | 0.0 | 1.0 | 1.0 | 39 |
| split holdout | 13 | relevance | 4.74 | 0.04 | 0.949 | 1.0 | 39 |
| split holdout | 13 | usefulness | 4.44 | 0.18 | 0.795 | 1.0 | 39 |
| split holdout | 13 | unsupported_claim (taxa de verdadeiro) | 0.179 | - | 0.949 | - | 39 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PT06 | 1 | holdout | knowledge | knowledge | answered | sim | - | 8534 | 0.0 |
| V030-ENABLEMENT-PENDING | 1 | dev | support | customer_support | answered | sim | - | 6664 | 0.0 |
| REPLAN-ACCOUNT | 1 | dev | knowledge | knowledge → customer_support → web | answered | sim | - | 16753 | 0.0 |
| NOEV | 1 | holdout | knowledge | knowledge → web | answered | não | content | 9911 | 0.0 |
| EX10 | 1 | dev | knowledge | knowledge | answered | sim | - | 5935 | 0.0 |
| UC18 | 1 | holdout | clarify | - | needs_clarification | sim | - | 3202 | 0.0 |
| EX08 | 1 | dev | knowledge_and_support | knowledge → customer_support | answered | não | content | 12537 | 0.0 |
| UC16 | 1 | holdout | out_of_scope | - | refused | sim | - | 1303 | 0.0 |
| EX05 | 1 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 14187 | 0.0 |
| PT03 | 1 | holdout | support | customer_support | answered | sim | - | 8830 | 0.0 |
| EX02 | 1 | dev | general_web | knowledge | answered | sim | - | 5960 | 0.0 |
| UC12 | 1 | holdout | out_of_scope | - | refused | sim | - | 2881 | 0.0 |
| PT05 | 1 | holdout | knowledge_and_support | knowledge → customer_support | answered | sim | - | 11419 | 0.0 |
| V030-PT-SALE-CANCELLATION | 1 | dev | support | customer_support | answered | não | content | 6216 | 0.0 |
| UC14 | 1 | holdout | human_handoff | escalation | handoff | sim | - | 5475 | 0.0 |
| EX01 | 1 | dev | knowledge | knowledge | answered | sim | - | 8127 | 0.0 |
| PT02 | 1 | holdout | general_web | knowledge | answered | sim | - | 5954 | 0.0 |
| PT07 | 1 | holdout | general_web | knowledge | answered | sim | - | 7540 | 0.0 |
| EX07 | 1 | dev | general_web | knowledge | answered | sim | - | 5884 | 0.0 |
| UC17 | 1 | holdout | support | customer_support | answered | sim | - | 2779 | 0.0 |
| PT09 | 1 | holdout | knowledge | knowledge | answered | sim | - | 6385 | 0.0 |
| V030-CONTRACT-TERMINATION | 1 | dev | human_handoff | escalation | handoff | sim | - | 5264 | 0.0 |
| REPLAN-TOOL-DOWN | 1 | dev | support | customer_support | answered | não | status, content | 23363 | 0.0 |
| PT08 | 1 | holdout | knowledge_and_support | knowledge → customer_support | answered | sim | - | 13425 | 0.0 |
