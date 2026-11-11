# Comparação pareada de avaliações

- **A:** `v0120-qa-off.json`, configuração `{"replan": "off", "mode": "real", "model": "gpt-6-luna", "split": "all", "repeat": 1, "cases": 44, "judge": true, "ruler": "combined", "include_replan": true}`.
- **B:** `v0120-qa-on.json`, configuração `{"replan": "on", "mode": "real", "model": "gpt-6-luna", "split": "all", "repeat": 1, "cases": 44, "judge": true, "ruler": "combined", "include_replan": true}`.

Pareamento por caso e repetição: 44 pares. Em cada critério, A e B são as médias (1 = aprovado; notas do juiz de 1 a 5), B − A é a média das diferenças pareadas e o intervalo de 95% vem do bootstrap dos pares (2000 reamostras, semente 93). Com A sem replanejamento (`REPLAN=off`) e B com ele, uma diferença positiva é ganho do replanejamento. Sem chamada de modelo.

## Por critério

| Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- |
| passed | 44 | 0.886 | 0.932 | +0.045 | [-0.045, +0.136] | não |
| deterministic | 44 | 0.955 | 0.977 | +0.023 | [+0.000, +0.068] | não |
| content | 44 | 0.932 | 0.955 | +0.023 | [-0.045, +0.114] | não |
| route_ok | 44 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| status_ok | 44 | 0.977 | 0.977 | +0.000 | [+0.000, +0.000] | não |
| language_ok | 44 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| tools_ok | 44 | 0.977 | 1.000 | +0.023 | [+0.000, +0.068] | não |
| amounts_ok | 44 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| content_ok | 44 | 0.886 | 0.818 | -0.068 | [-0.159, +0.000] | não |
| forbidden_ok | 44 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| sources_ok | 44 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| grounded_ok | 44 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| judge:groundedness | 44 | 4.773 | 4.841 | +0.068 | [-0.023, +0.182] | não |
| judge:factual_correctness | 44 | 4.795 | 4.841 | +0.045 | [-0.114, +0.205] | não |
| judge:relevance | 44 | 4.864 | 4.932 | +0.068 | [-0.023, +0.159] | não |
| judge:usefulness | 44 | 4.682 | 4.795 | +0.114 | [-0.045, +0.273] | não |

## Por rota

Rota do Router no relatório A (o plano inicial).

| Rota | Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- | --- |
| clarify | passed | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | deterministic | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | content | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | route_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | status_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | language_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | tools_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | amounts_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | content_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | forbidden_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | sources_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | grounded_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| clarify | judge:groundedness | 1 | 5.000 | 5.000 | +0.000 | - | não |
| clarify | judge:factual_correctness | 1 | 5.000 | 5.000 | +0.000 | - | não |
| clarify | judge:relevance | 1 | 5.000 | 5.000 | +0.000 | - | não |
| clarify | judge:usefulness | 1 | 5.000 | 5.000 | +0.000 | - | não |
| general_web | passed | 4 | 0.500 | 0.750 | +0.250 | [+0.000, +0.750] | não |
| general_web | deterministic | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | content | 4 | 0.500 | 0.750 | +0.250 | [+0.000, +0.750] | não |
| general_web | route_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | status_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | language_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | tools_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | amounts_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | content_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | forbidden_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | sources_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | grounded_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | judge:groundedness | 4 | 3.500 | 4.000 | +0.500 | [+0.000, +1.000] | não |
| general_web | judge:factual_correctness | 4 | 3.500 | 4.500 | +1.000 | [+0.250, +1.750] | sim |
| general_web | judge:relevance | 4 | 4.750 | 5.000 | +0.250 | [+0.000, +0.750] | não |
| general_web | judge:usefulness | 4 | 4.250 | 5.000 | +0.750 | [+0.000, +1.500] | não |
| human_handoff | passed | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | deterministic | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | content | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | route_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | status_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | language_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | tools_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | amounts_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | content_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | forbidden_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | sources_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | grounded_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | judge:groundedness | 2 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | judge:factual_correctness | 2 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | judge:relevance | 2 | 4.500 | 5.000 | +0.500 | [+0.000, +1.000] | não |
| human_handoff | judge:usefulness | 2 | 4.500 | 5.000 | +0.500 | [+0.000, +1.000] | não |
| knowledge | passed | 13 | 0.923 | 1.000 | +0.077 | [+0.000, +0.231] | não |
| knowledge | deterministic | 13 | 0.923 | 1.000 | +0.077 | [+0.000, +0.231] | não |
| knowledge | content | 13 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | route_ok | 13 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | status_ok | 13 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | language_ok | 13 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | tools_ok | 13 | 0.923 | 1.000 | +0.077 | [+0.000, +0.231] | não |
| knowledge | amounts_ok | 13 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | content_ok | 13 | 1.000 | 0.923 | -0.077 | [-0.231, +0.000] | não |
| knowledge | forbidden_ok | 13 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | sources_ok | 13 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | grounded_ok | 13 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | judge:groundedness | 13 | 4.846 | 4.923 | +0.077 | [+0.000, +0.231] | não |
| knowledge | judge:factual_correctness | 13 | 4.923 | 4.846 | -0.077 | [-0.231, +0.000] | não |
| knowledge | judge:relevance | 13 | 4.923 | 4.923 | +0.000 | [-0.231, +0.231] | não |
| knowledge | judge:usefulness | 13 | 4.462 | 4.615 | +0.154 | [-0.154, +0.462] | não |
| knowledge_and_support | passed | 5 | 1.000 | 0.800 | -0.200 | [-0.600, +0.000] | não |
| knowledge_and_support | deterministic | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | content | 5 | 1.000 | 0.800 | -0.200 | [-0.600, +0.000] | não |
| knowledge_and_support | route_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | status_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | language_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | tools_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | amounts_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | content_ok | 5 | 1.000 | 0.800 | -0.200 | [-0.600, +0.000] | não |
| knowledge_and_support | forbidden_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | sources_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | grounded_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | judge:groundedness | 5 | 4.800 | 4.600 | -0.200 | [-0.600, +0.000] | não |
| knowledge_and_support | judge:factual_correctness | 5 | 4.800 | 4.400 | -0.400 | [-1.200, +0.000] | não |
| knowledge_and_support | judge:relevance | 5 | 4.800 | 4.800 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | judge:usefulness | 5 | 4.800 | 4.600 | -0.200 | [-0.600, +0.000] | não |
| out_of_scope | passed | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | deterministic | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | content | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | route_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | status_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | language_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | tools_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | amounts_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | content_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | forbidden_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | sources_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | grounded_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | judge:groundedness | 2 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | judge:factual_correctness | 2 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | judge:relevance | 2 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| out_of_scope | judge:usefulness | 2 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| support | passed | 17 | 0.882 | 0.941 | +0.059 | [+0.000, +0.176] | não |
| support | deterministic | 17 | 0.941 | 0.941 | +0.000 | [+0.000, +0.000] | não |
| support | content | 17 | 0.941 | 1.000 | +0.059 | [+0.000, +0.176] | não |
| support | route_ok | 17 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | status_ok | 17 | 0.941 | 0.941 | +0.000 | [+0.000, +0.000] | não |
| support | language_ok | 17 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | tools_ok | 17 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | amounts_ok | 17 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | content_ok | 17 | 0.706 | 0.647 | -0.059 | [-0.176, +0.000] | não |
| support | forbidden_ok | 17 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | sources_ok | 17 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | grounded_ok | 17 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | judge:groundedness | 17 | 4.941 | 5.000 | +0.059 | [+0.000, +0.176] | não |
| support | judge:factual_correctness | 17 | 4.941 | 5.000 | +0.059 | [+0.000, +0.176] | não |
| support | judge:relevance | 17 | 4.882 | 4.941 | +0.059 | [+0.000, +0.176] | não |
| support | judge:usefulness | 17 | 4.882 | 4.882 | +0.000 | [-0.176, +0.176] | não |

## Decisões do replanejamento por origem

Todas as decisões do passo `replan` gravadas nos traces de cada relatório (ADR 0024, medida 1).

| Origem | A | B |
| --- | --- | --- |
| `model` | 0 | 2 |
| `rule:complete` | 0 | 31 |
| `rule:evidence_insufficient_web` | 0 | 4 |
| `rule:gap_declared` | 0 | 5 |
| `rule:plan_pending` | 0 | 5 |
| `rule:support_asked_for_human` | 0 | 2 |
| total | 0 | 49 |

Parte das decisões de origem `model`: A -; B 0.041.

Cada decisão conta pela origem final: a guarda do replanejador tem a última palavra, e a escolha do modelo que ela recusou conta como `rule:<guarda>`. Modelo consultado e recusado pela guarda: A 0; B 0.

## Diferença pareada por origem das decisões

Pares separados pelas decisões do `replan` dos dois lados (ADR 0024, medida 2).

### Pares com pelo menos uma decisão `model`: 1

| Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- |
| passed | 1 | 0.000 | 1.000 | +1.000 | - | não |
| deterministic | 1 | 0.000 | 1.000 | +1.000 | - | não |
| content | 1 | 1.000 | 1.000 | +0.000 | - | não |
| route_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| status_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| language_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| tools_ok | 1 | 0.000 | 1.000 | +1.000 | - | não |
| amounts_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| content_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| forbidden_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| sources_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| grounded_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| judge:groundedness | 1 | 5.000 | 5.000 | +0.000 | - | não |
| judge:factual_correctness | 1 | 5.000 | 5.000 | +0.000 | - | não |
| judge:relevance | 1 | 5.000 | 5.000 | +0.000 | - | não |
| judge:usefulness | 1 | 5.000 | 5.000 | +0.000 | - | não |

### Pares só decisões por regra: 38

| Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- |
| passed | 38 | 0.895 | 0.921 | +0.026 | [-0.053, +0.105] | não |
| deterministic | 38 | 0.974 | 0.974 | +0.000 | [+0.000, +0.000] | não |
| content | 38 | 0.921 | 0.947 | +0.026 | [-0.053, +0.105] | não |
| route_ok | 38 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| status_ok | 38 | 0.974 | 0.974 | +0.000 | [+0.000, +0.000] | não |
| language_ok | 38 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| tools_ok | 38 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| amounts_ok | 38 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| content_ok | 38 | 0.868 | 0.789 | -0.079 | [-0.184, +0.000] | não |
| forbidden_ok | 38 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| sources_ok | 38 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| grounded_ok | 38 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| judge:groundedness | 38 | 4.737 | 4.816 | +0.079 | [-0.026, +0.184] | não |
| judge:factual_correctness | 38 | 4.763 | 4.816 | +0.053 | [-0.132, +0.237] | não |
| judge:relevance | 38 | 4.868 | 4.921 | +0.053 | [-0.053, +0.158] | não |
| judge:usefulness | 38 | 4.658 | 4.763 | +0.105 | [-0.079, +0.289] | não |

### Pares sem decisão do `replan`: 5

| Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- |
| passed | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| deterministic | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| content | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| route_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| status_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| language_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| tools_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| amounts_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| content_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| forbidden_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| sources_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| grounded_ok | 5 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| judge:groundedness | 5 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| judge:factual_correctness | 5 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| judge:relevance | 5 | 4.800 | 5.000 | +0.200 | [+0.000, +0.600] | não |
| judge:usefulness | 5 | 4.800 | 5.000 | +0.200 | [+0.000, +0.600] | não |

### Pares com mudança de plano (`hops > 0` em algum lado): 7

| Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- |
| passed | 7 | 0.857 | 1.000 | +0.143 | [+0.000, +0.429] | não |
| deterministic | 7 | 0.857 | 1.000 | +0.143 | [+0.000, +0.429] | não |
| content | 7 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| route_ok | 7 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| status_ok | 7 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| language_ok | 7 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| tools_ok | 7 | 0.857 | 1.000 | +0.143 | [+0.000, +0.429] | não |
| amounts_ok | 7 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| content_ok | 7 | 1.000 | 0.857 | -0.143 | [-0.429, +0.000] | não |
| forbidden_ok | 7 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| sources_ok | 7 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| grounded_ok | 7 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| judge:groundedness | 7 | 4.714 | 4.857 | +0.143 | [+0.000, +0.429] | não |
| judge:factual_correctness | 7 | 4.857 | 4.714 | -0.143 | [-0.429, +0.000] | não |
| judge:relevance | 7 | 4.857 | 4.857 | +0.000 | [-0.429, +0.429] | não |
| judge:usefulness | 7 | 4.286 | 4.571 | +0.286 | [+0.000, +0.571] | não |

## Decisões de origem `model`

| Lado | Caso | Rep | Rota | Observação | Candidatos | Escolha | Motivo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B | REPLAN-ACCOUNT | 1 | knowledge | `{"account_dependent": true, "controlled_answer": false, "customer_known": true, "evidence_sufficient": false, "failed_tools": [], "hops": 0, "how_to": false, "just_ran": "knowledge", "knowledge_gap": ["Os trechos não confirmam se a antecipação está disponível no plano específico do estabelecimento nem informam as condições do contrato do merchant."], "knowledge_mode": "rag", "knowledge_unavailable": false, "pending": [], "ran": ["knowledge"], "route": "knowledge", "support_escalate": false, "support_missing": [], "support_needs_selection": false, "support_points": false}` | support, web | support (incomplete) | A disponibilidade depende do plano específico deste estabelecimento, que pode ser verificado nos dados da conta. |
| B | REPLAN-ACCOUNT | 1 | knowledge | `{"account_dependent": true, "controlled_answer": false, "customer_known": true, "evidence_sufficient": false, "failed_tools": [], "hops": 1, "how_to": false, "just_ran": "support", "knowledge_gap": ["Os trechos não confirmam se a antecipação está disponível no plano específico do estabelecimento nem informam as condições do contrato do merchant."], "knowledge_mode": "rag", "knowledge_unavailable": false, "pending": [], "ran": ["knowledge", "support"], "route": "knowledge", "support_escalate": false, "support_missing": [], "support_needs_selection": false, "support_points": true}` | nenhum | finish (incomplete) | Não foi possível confirmar se a antecipação de recebíveis está disponível no plano do estabelecimento. |

## Modelo consultado e recusado pela guarda

Nenhuma.

## Casos sem par

Nenhum.

## Conversas de vários turnos

| Conversa | A | B |
| --- | --- | --- |
| FU01 | sim | sim |
| FU02 | sim | sim |
| FU03 | sim | sim |
| FU04 | sim | sim |

| Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- |
| passed | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
