# Relatório de avaliação: v080-r5-658c70ad-healthy

Gerado em 2026-11-05T07:07:15+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "all", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 3, "limit": null, "include_replan": true, "campaign": "v080-qa", "campaign_cap_usd": 1.4, "cases": 12}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 36 | 0.722 | 1.0 | 1.0 | 1.0 | 1.0 | 0.722 | 1.0 | 1.0 | 7779 | 15641 | 0.01901 |
| split dev | 36 | 0.722 | 1.0 | 1.0 | 1.0 | 1.0 | 0.722 | 1.0 | 1.0 | 7779 | 15641 | 0.01901 |
| idioma en | 18 | 0.611 | 1.0 | 1.0 | 1.0 | 1.0 | 0.611 | 1.0 | 1.0 | 7178 | 10767 | 0.0082 |
| idioma pt | 18 | 0.833 | 1.0 | 1.0 | 1.0 | 1.0 | 0.833 | 1.0 | 1.0 | 8520 | 17079 | 0.01081 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 4.97, correção factual 4.97, relevância 4.97, utilidade 4.89. Afirmações sem suporte: 0.0 das respostas julgadas. Custo do juiz: US$ 0.02091.

Respostas julgadas sob a nota de busca web: 0 de 36. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 0 foram marcadas como afirmação sem suporte.

Evidência truncada em 1 de 36 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| human_handoff | escalation | 3 |
| knowledge_and_support | knowledge → customer_support | 3 |
| support | customer_support | 24 |
| support | customer_support → escalation | 6 |

## Variação: variação do assistente (o agente roda cada caso N vezes e o juiz avalia cada resposta uma vez)

Repetições por caso: 3. Desvio: média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou com diferença de até 1 ponto (±1).

> Ressalva de amostra pequena (D19): 12 casos com 3 repetições cada; os recortes por rota e por split têm menos casos ainda (marcados com * quando há menos de 10). Médias, desvios e concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno.

| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 12 | groundedness | 4.97 | 0.05 | 0.944 | 1.0 | 36 |
| geral | 12 | factual_correctness | 4.97 | 0.05 | 0.944 | 1.0 | 36 |
| geral | 12 | relevance | 4.97 | 0.05 | 0.944 | 1.0 | 36 |
| geral | 12 | usefulness | 4.89 | 0.14 | 0.833 | 1.0 | 36 |
| geral | 12 | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 36 |
| rota human_handoff | 1* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota human_handoff | 1* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota human_handoff | 1* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota human_handoff | 1* | usefulness | 4.33 | 0.58 | 0.333 | 1.0 | 3 |
| rota human_handoff | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |
| rota knowledge_and_support | 1* | groundedness | 4.67 | 0.58 | 0.333 | 1.0 | 3 |
| rota knowledge_and_support | 1* | factual_correctness | 4.67 | 0.58 | 0.333 | 1.0 | 3 |
| rota knowledge_and_support | 1* | relevance | 4.67 | 0.58 | 0.333 | 1.0 | 3 |
| rota knowledge_and_support | 1* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota knowledge_and_support | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |
| rota support | 10 | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 30 |
| rota support | 10 | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 30 |
| rota support | 10 | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 30 |
| rota support | 10 | usefulness | 4.93 | 0.12 | 0.867 | 1.0 | 30 |
| rota support | 10 | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 30 |
| split dev | 12 | groundedness | 4.97 | 0.05 | 0.944 | 1.0 | 36 |
| split dev | 12 | factual_correctness | 4.97 | 0.05 | 0.944 | 1.0 | 36 |
| split dev | 12 | relevance | 4.97 | 0.05 | 0.944 | 1.0 | 36 |
| split dev | 12 | usefulness | 4.89 | 0.14 | 0.833 | 1.0 | 36 |
| split dev | 12 | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 36 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REPLAN-PROCEDURE | 1 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 22702 | 0.00161235 |
| V030-PRICE-CONSISTENT | 1 | dev | support | customer_support | answered | sim | - | 9981 | 0.00057014 |
| V030-PRICE-CONDITIONS | 1 | dev | support | customer_support | answered | sim | - | 9580 | 0.00059794 |
| V030-PRICE-DIVERGENCE | 1 | dev | support | customer_support → escalation | handoff | não | content | 12493 | 0.00066581 |
| V030-PRICE-INSUFFICIENT | 1 | dev | support | customer_support | answered | sim | - | 7805 | 0.00034154 |
| V030-SALE-CANCELLATION | 1 | dev | support | customer_support | answered | sim | - | 8977 | 0.00025982 |
| V030-CONTRACT-TERMINATION | 1 | dev | human_handoff | escalation | handoff | sim | - | 6655 | 0.00032967 |
| V030-PT-PRICE-CONSISTENT | 1 | dev | support | customer_support | answered | sim | - | 10849 | 0.00056658 |
| V030-PT-PRICE-CONDITIONS | 1 | dev | support | customer_support | answered | sim | - | 10010 | 0.00044375 |
| V030-PT-PRICE-DIVERGENCE | 1 | dev | support | customer_support → escalation | handoff | sim | - | 12890 | 0.00062033 |
| V030-PT-PRICE-INSUFFICIENT | 1 | dev | support | customer_support | answered | não | content | 7271 | 0.00033988 |
| V030-PT-SALE-CANCELLATION | 1 | dev | support | customer_support | answered | sim | - | 6656 | 0.00026704 |
| REPLAN-PROCEDURE | 2 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 15641 | 0.00105041 |
| V030-PRICE-CONSISTENT | 2 | dev | support | customer_support | answered | sim | - | 6784 | 0.00056527 |
| V030-PRICE-CONDITIONS | 2 | dev | support | customer_support | answered | não | content | 7274 | 0.00040764 |
| V030-PRICE-DIVERGENCE | 2 | dev | support | customer_support → escalation | handoff | não | content | 10578 | 0.00063274 |
| V030-PRICE-INSUFFICIENT | 2 | dev | support | customer_support | answered | não | content | 6890 | 0.0003258 |
| V030-SALE-CANCELLATION | 2 | dev | support | customer_support | answered | não | content | 5869 | 0.00043089 |
| V030-CONTRACT-TERMINATION | 2 | dev | human_handoff | escalation | handoff | sim | - | 5048 | 0.00033037 |
| V030-PT-PRICE-CONSISTENT | 2 | dev | support | customer_support | answered | sim | - | 6433 | 0.00056244 |
| V030-PT-PRICE-CONDITIONS | 2 | dev | support | customer_support | answered | não | content | 8104 | 0.0004383 |
| V030-PT-PRICE-DIVERGENCE | 2 | dev | support | customer_support → escalation | handoff | sim | - | 10296 | 0.00063696 |
| V030-PT-PRICE-INSUFFICIENT | 2 | dev | support | customer_support | answered | sim | - | 7847 | 0.00034336 |
| V030-PT-SALE-CANCELLATION | 2 | dev | support | customer_support | answered | sim | - | 6235 | 0.00025268 |
| REPLAN-PROCEDURE | 3 | dev | knowledge_and_support | knowledge → customer_support | answered | sim | - | 17079 | 0.00118479 |
| V030-PRICE-CONSISTENT | 3 | dev | support | customer_support | answered | sim | - | 7753 | 0.00056787 |
| V030-PRICE-CONDITIONS | 3 | dev | support | customer_support | answered | sim | - | 7061 | 0.00043624 |
| V030-PRICE-DIVERGENCE | 3 | dev | support | customer_support → escalation | handoff | não | content | 10767 | 0.00064394 |
| V030-PRICE-INSUFFICIENT | 3 | dev | support | customer_support | answered | não | content | 7082 | 0.0003325 |
| V030-SALE-CANCELLATION | 3 | dev | support | customer_support | answered | sim | - | 6133 | 0.00043059 |
| V030-CONTRACT-TERMINATION | 3 | dev | human_handoff | escalation | handoff | sim | - | 5249 | 0.00033107 |
| V030-PT-PRICE-CONSISTENT | 3 | dev | support | customer_support | answered | sim | - | 7035 | 0.00056674 |
| V030-PT-PRICE-CONDITIONS | 3 | dev | support | customer_support | answered | sim | - | 8936 | 0.0004723 |
| V030-PT-PRICE-DIVERGENCE | 3 | dev | support | customer_support → escalation | handoff | sim | - | 12066 | 0.00066306 |
| V030-PT-PRICE-INSUFFICIENT | 3 | dev | support | customer_support | answered | não | content | 7435 | 0.00033726 |
| V030-PT-SALE-CANCELLATION | 3 | dev | support | customer_support | answered | sim | - | 7542 | 0.0004511 |
