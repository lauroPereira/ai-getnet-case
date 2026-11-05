# Relatório de avaliação: v080-r5-658c70ad-tool-down

Gerado em 2026-11-05T07:08:51+00:00. Configuração: `{"mode": "real", "model": "gpt-6-luna", "agent_provider": "openai", "embedding": "text-embedding-3-small", "split": "all", "judge": true, "judge_config": {"provider": "deepseek", "model": "deepseek-flash", "rubric": "judge", "rubric_version": "3", "prompt": "judge@3", "independence": "different_provider", "parameters": {"max_output_tokens": 400, "effort": "none"}}, "repeat": 3, "limit": null, "include_replan": true, "campaign": "v080-qa", "campaign_cap_usd": 1.4, "cases": 1}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 3 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 11319 | 11525 | 0.00139 |
| split dev | 3 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 11319 | 11525 | 0.00139 |
| idioma en | 0 | None | None | None | None | None | None | None | None | - | - | 0 |
| idioma pt | 3 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 11319 | 11525 | 0.00139 |

Rubrica por modelo (média 1-5, não é revisão humana): fundamentação 5.0, correção factual 5.0, relevância 5.0, utilidade 5.0. Afirmações sem suporte: 0.0 das respostas julgadas. Custo do juiz: US$ 0.00104.

Respostas julgadas sob a nota de busca web: 0 de 3. O texto da busca não é gravado e o juiz só vê os títulos das fontes: o `judge.v3` não rebaixa o que não pode conferir, mas mantém a afirmação sem suporte sobre dado da conta do lojista sem resultado de ferramenta. Dessas respostas, 0 foram marcadas como afirmação sem suporte.

Evidência truncada em 0 de 3 respostas (limite de 6000 caracteres para o juiz; o registro de cada corte está na linha do relatório em JSON).

## Rota planejada e caminho executado

A rota avaliada (coluna Rota) é a escolhida pelo Router, o plano inicial. O caminho executado vem da lista de agentes da resposta e não entra em `route_ok` (D16).

| Rota | Caminho executado | Respostas |
| --- | --- | --- |
| support | customer_support → escalation | 3 |

## Variação: variação do assistente (o agente roda cada caso N vezes e o juiz avalia cada resposta uma vez)

Repetições por caso: 3. Desvio: média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou com diferença de até 1 ponto (±1).

> Ressalva de amostra pequena (D19): 1 casos com 3 repetições cada; os recortes por rota e por split têm menos casos ainda (marcados com * quando há menos de 10). Médias, desvios e concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno.

| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 1* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| geral | 1* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| geral | 1* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| geral | 1* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| geral | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |
| rota support | 1* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota support | 1* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota support | 1* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota support | 1* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota support | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |
| split dev | 1* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| split dev | 1* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| split dev | 1* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| split dev | 1* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| split dev | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |

## Casos

| Caso | Rep | Split | Rota | Caminho executado | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REPLAN-TOOL-DOWN | 1 | dev | support | customer_support → escalation | handoff | sim | - | 11525 | 0.00059147 |
| REPLAN-TOOL-DOWN | 2 | dev | support | customer_support → escalation | handoff | sim | - | 11319 | 0.00040232 |
| REPLAN-TOOL-DOWN | 3 | dev | support | customer_support → escalation | handoff | sim | - | 10873 | 0.00039972 |
