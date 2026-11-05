# Relatório de avaliação: v090-juiz-opus-sonda2

Gerado em 2026-11-05T21:06:24+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "all", "judge": true, "judge_config": {"provider": "anthropic", "model": "claude-opus-5-5", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 2000, "effort": "default", "thinking": "default"}}, "repeat": 1, "judge_repeat": 1, "answers_from": "v080-all-r3.json", "recorded_answers": 44, "only_sample": "v080-calibracao-amostra.csv", "only_sample_ids": 24, "limit": 3, "selected_answers": 3, "campaign": null, "campaign_cap_usd": null, "cases": 3}`.

Respostas julgadas: 3 de 44 gravadas, filtradas pelos 24 request_id de `v080-calibracao-amostra.csv`, limitadas a 3.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 3 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 8534 | 16753 | 0 |
| split dev | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 11708 | 16753 | 0 |
| split holdout | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 8534 | 8534 | 0 |
| idioma en | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 6664 | 6664 | 0 |
| idioma pt | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 12643 | 16753 | 0 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 4.67, correção factual 4.33, relevância 5.0, utilidade 4.33. Afirmações sem suporte: 0.333 das respostas julgadas. Custo do juiz: US$ 0.05631.

Tokens do juiz (3 julgamentos com uso registrado; total / média por julgamento): entrada 9178 / 3059.3, da qual cache lido 0 / 0.0 e cache criado 0 / 0.0; saída (com o pensamento) 980 / 326.7. Custo do juiz: US$ 0.05631.

Respostas julgadas sob a nota de busca web: 1 de 3. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 0 foram marcadas como afirmação sem suporte.

Evidência truncada em 0 de 3 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Afirmações sem suporte (veredito crítico)

Listadas uma a uma, nunca diluídas na média.

| Caso | Rep | Rota | Julgamentos marcados | Fundamentação (primeiro julgamento marcado) |
| --- | --- | --- | --- | --- |
| PT06 | 1 | knowledge | 1 de 1 | Most steps, the R$50 minimum, 48 hours and individual evaluation are supported; 'taxas variam conforme o contrato' is not explicitly stated. |

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| knowledge | knowledge | 1 |
| knowledge | knowledge → customer_support → web | 1 |
| support | customer_support | 1 |

## Variação: variação do juiz (as mesmas respostas gravadas avaliadas N vezes)

Repetições por caso: 1. Desvio: média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou com diferença de até 1 ponto (±1).

> Ressalva de amostra pequena (D19): 3 casos com 1 repetições cada; os recortes por rota e por split têm menos casos ainda (marcados com * quando há menos de 10). Médias, desvios e concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno.

| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 3* | groundedness | 4.67 | - | - | - | 0 |
| geral | 3* | factual_correctness | 4.33 | - | - | - | 0 |
| geral | 3* | relevance | 5.0 | - | - | - | 0 |
| geral | 3* | usefulness | 4.33 | - | - | - | 0 |
| geral | 3* | unsupported_claim (taxa de verdadeiro) | 0.333 | - | - | - | 0 |
| rota knowledge | 2* | groundedness | 4.5 | - | - | - | 0 |
| rota knowledge | 2* | factual_correctness | 4.0 | - | - | - | 0 |
| rota knowledge | 2* | relevance | 5.0 | - | - | - | 0 |
| rota knowledge | 2* | usefulness | 4.5 | - | - | - | 0 |
| rota knowledge | 2* | unsupported_claim (taxa de verdadeiro) | 0.5 | - | - | - | 0 |
| rota support | 1* | groundedness | 5.0 | - | - | - | 0 |
| rota support | 1* | factual_correctness | 5.0 | - | - | - | 0 |
| rota support | 1* | relevance | 5.0 | - | - | - | 0 |
| rota support | 1* | usefulness | 4.0 | - | - | - | 0 |
| rota support | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | - | - | 0 |
| split dev | 2* | groundedness | 5.0 | - | - | - | 0 |
| split dev | 2* | factual_correctness | 4.5 | - | - | - | 0 |
| split dev | 2* | relevance | 5.0 | - | - | - | 0 |
| split dev | 2* | usefulness | 4.0 | - | - | - | 0 |
| split dev | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | - | - | 0 |
| split holdout | 1* | groundedness | 4.0 | - | - | - | 0 |
| split holdout | 1* | factual_correctness | 4.0 | - | - | - | 0 |
| split holdout | 1* | relevance | 5.0 | - | - | - | 0 |
| split holdout | 1* | usefulness | 5.0 | - | - | - | 0 |
| split holdout | 1* | unsupported_claim (taxa de verdadeiro) | 1.0 | - | - | - | 0 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PT06 | 1 | holdout | knowledge | knowledge | answered | sim | - | 8534 | 0.0 |
| V030-ENABLEMENT-PENDING | 1 | dev | support | customer_support | answered | sim | - | 6664 | 0.0 |
| REPLAN-ACCOUNT | 1 | dev | knowledge | knowledge → customer_support → web | answered | sim | - | 16753 | 0.0 |
