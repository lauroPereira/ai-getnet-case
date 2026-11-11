# Comparação pareada de avaliações

- **A:** `v0120-qa-holdout-off.json`, configuração `{"replan": "off", "mode": "real", "model": "gpt-6-luna", "split": "holdout_v080", "repeat": 1, "cases": 25, "judge": true, "ruler": "combined", "include_replan": false}`.
- **B:** `v0120-qa-holdout-on.json`, configuração `{"replan": "on", "mode": "real", "model": "gpt-6-luna", "split": "holdout_v080", "repeat": 1, "cases": 25, "judge": true, "ruler": "combined", "include_replan": false}`.

Pareamento por caso e repetição: 25 pares. Em cada critério, A e B são as médias (1 = aprovado; notas do juiz de 1 a 5), B − A é a média das diferenças pareadas e o intervalo de 95% vem do bootstrap dos pares (2000 reamostras, semente 93). Com A sem replanejamento (`REPLAN=off`) e B com ele, uma diferença positiva é ganho do replanejamento. Sem chamada de modelo.

## Por critério

| Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- |
| passed | 25 | 0.880 | 0.800 | -0.080 | [-0.240, +0.080] | não |
| deterministic | 25 | 0.920 | 0.880 | -0.040 | [-0.160, +0.080] | não |
| content | 25 | 0.960 | 0.920 | -0.040 | [-0.120, +0.000] | não |
| route_ok | 25 | 0.960 | 0.920 | -0.040 | [-0.120, +0.000] | não |
| status_ok | 25 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| language_ok | 25 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| tools_ok | 25 | 0.960 | 1.000 | +0.040 | [+0.000, +0.120] | não |
| amounts_ok | 25 | 0.960 | 0.960 | +0.000 | [-0.120, +0.120] | não |
| content_ok | 25 | 0.880 | 0.920 | +0.040 | [-0.080, +0.160] | não |
| forbidden_ok | 25 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| sources_ok | 25 | 0.960 | 1.000 | +0.040 | [+0.000, +0.120] | não |
| grounded_ok | 25 | 0.960 | 1.000 | +0.040 | [+0.000, +0.120] | não |
| judge:groundedness | 25 | 4.800 | 4.760 | -0.040 | [-0.240, +0.120] | não |
| judge:factual_correctness | 25 | 4.840 | 4.720 | -0.120 | [-0.320, +0.000] | não |
| judge:relevance | 25 | 4.840 | 4.920 | +0.080 | [-0.120, +0.280] | não |
| judge:usefulness | 25 | 4.760 | 4.800 | +0.040 | [-0.160, +0.240] | não |

## Por rota

Rota do Router no relatório A (o plano inicial).

Pares com rota diferente em B: HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD (rep 1).

| Rota | Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- | --- |
| general_web | passed | 2 | 1.000 | 0.500 | -0.500 | [-1.000, +0.000] | não |
| general_web | deterministic | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | content | 2 | 1.000 | 0.500 | -0.500 | [-1.000, +0.000] | não |
| general_web | route_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | status_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | language_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | tools_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | amounts_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | content_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | forbidden_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | sources_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | grounded_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | judge:groundedness | 2 | 4.500 | 3.500 | -1.000 | [-2.000, +0.000] | não |
| general_web | judge:factual_correctness | 2 | 4.500 | 3.500 | -1.000 | [-2.000, +0.000] | não |
| general_web | judge:relevance | 2 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| general_web | judge:usefulness | 2 | 5.000 | 4.500 | -0.500 | [-1.000, +0.000] | não |
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
| human_handoff | judge:relevance | 2 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| human_handoff | judge:usefulness | 2 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | passed | 6 | 0.667 | 0.667 | +0.000 | [+0.000, +0.000] | não |
| knowledge | deterministic | 6 | 0.833 | 0.833 | +0.000 | [+0.000, +0.000] | não |
| knowledge | content | 6 | 0.833 | 0.833 | +0.000 | [+0.000, +0.000] | não |
| knowledge | route_ok | 6 | 0.833 | 0.833 | +0.000 | [+0.000, +0.000] | não |
| knowledge | status_ok | 6 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | language_ok | 6 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | tools_ok | 6 | 0.833 | 1.000 | +0.167 | [+0.000, +0.500] | não |
| knowledge | amounts_ok | 6 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | content_ok | 6 | 0.833 | 1.000 | +0.167 | [+0.000, +0.500] | não |
| knowledge | forbidden_ok | 6 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | sources_ok | 6 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | grounded_ok | 6 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge | judge:groundedness | 6 | 4.333 | 4.500 | +0.167 | [+0.000, +0.500] | não |
| knowledge | judge:factual_correctness | 6 | 4.500 | 4.500 | +0.000 | [+0.000, +0.000] | não |
| knowledge | judge:relevance | 6 | 4.667 | 4.667 | +0.000 | [-0.667, +0.667] | não |
| knowledge | judge:usefulness | 6 | 4.500 | 4.500 | +0.000 | [-0.500, +0.500] | não |
| knowledge_and_support | passed | 4 | 1.000 | 0.500 | -0.500 | [-1.000, +0.000] | não |
| knowledge_and_support | deterministic | 4 | 1.000 | 0.500 | -0.500 | [-1.000, +0.000] | não |
| knowledge_and_support | content | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | route_ok | 4 | 1.000 | 0.750 | -0.250 | [-0.750, +0.000] | não |
| knowledge_and_support | status_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | language_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | tools_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | amounts_ok | 4 | 1.000 | 0.750 | -0.250 | [-0.750, +0.000] | não |
| knowledge_and_support | content_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | forbidden_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | sources_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | grounded_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | judge:groundedness | 4 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| knowledge_and_support | judge:factual_correctness | 4 | 5.000 | 4.750 | -0.250 | [-0.750, +0.000] | não |
| knowledge_and_support | judge:relevance | 4 | 4.500 | 5.000 | +0.500 | [+0.000, +1.000] | não |
| knowledge_and_support | judge:usefulness | 4 | 4.750 | 5.000 | +0.250 | [+0.000, +0.750] | não |
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
| support | passed | 9 | 0.889 | 1.000 | +0.111 | [+0.000, +0.333] | não |
| support | deterministic | 9 | 0.889 | 1.000 | +0.111 | [+0.000, +0.333] | não |
| support | content | 9 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | route_ok | 9 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | status_ok | 9 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | language_ok | 9 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | tools_ok | 9 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | amounts_ok | 9 | 0.889 | 1.000 | +0.111 | [+0.000, +0.333] | não |
| support | content_ok | 9 | 0.778 | 0.778 | +0.000 | [-0.333, +0.333] | não |
| support | forbidden_ok | 9 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| support | sources_ok | 9 | 0.889 | 1.000 | +0.111 | [+0.000, +0.333] | não |
| support | grounded_ok | 9 | 0.889 | 1.000 | +0.111 | [+0.000, +0.333] | não |
| support | judge:groundedness | 9 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| support | judge:factual_correctness | 9 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| support | judge:relevance | 9 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| support | judge:usefulness | 9 | 4.778 | 4.889 | +0.111 | [-0.222, +0.444] | não |

## Decisões do replanejamento por origem

Todas as decisões do passo `replan` gravadas nos traces de cada relatório (ADR 0024, medida 1).

| Origem | A | B |
| --- | --- | --- |
| `model` | 0 | 2 |
| `rule:complete` | 0 | 18 |
| `rule:gap_declared` | 0 | 3 |
| `rule:plan_pending` | 0 | 3 |
| `rule:procedure_gap` | 0 | 1 |
| total | 0 | 27 |

Parte das decisões de origem `model`: A -; B 0.074.

Cada decisão conta pela origem final: a guarda do replanejador tem a última palavra, e a escolha do modelo que ela recusou conta como `rule:<guarda>`. Modelo consultado e recusado pela guarda: A 0; B 0.

## Diferença pareada por origem das decisões

Pares separados pelas decisões do `replan` dos dois lados (ADR 0024, medida 2).

### Pares com pelo menos uma decisão `model`: 1

| Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- |
| passed | 1 | 0.000 | 0.000 | +0.000 | - | não |
| deterministic | 1 | 0.000 | 0.000 | +0.000 | - | não |
| content | 1 | 1.000 | 1.000 | +0.000 | - | não |
| route_ok | 1 | 0.000 | 0.000 | +0.000 | - | não |
| status_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| language_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| tools_ok | 1 | 0.000 | 1.000 | +1.000 | - | não |
| amounts_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| content_ok | 1 | 0.000 | 1.000 | +1.000 | - | não |
| forbidden_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| sources_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| grounded_ok | 1 | 1.000 | 1.000 | +0.000 | - | não |
| judge:groundedness | 1 | 4.000 | 5.000 | +1.000 | - | não |
| judge:factual_correctness | 1 | 5.000 | 5.000 | +0.000 | - | não |
| judge:relevance | 1 | 4.000 | 5.000 | +1.000 | - | não |
| judge:usefulness | 1 | 4.000 | 5.000 | +1.000 | - | não |

### Pares só decisões por regra: 20

| Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- |
| passed | 20 | 0.900 | 0.800 | -0.100 | [-0.300, +0.100] | não |
| deterministic | 20 | 0.950 | 0.900 | -0.050 | [-0.200, +0.100] | não |
| content | 20 | 0.950 | 0.900 | -0.050 | [-0.150, +0.000] | não |
| route_ok | 20 | 1.000 | 0.950 | -0.050 | [-0.150, +0.000] | não |
| status_ok | 20 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| language_ok | 20 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| tools_ok | 20 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| amounts_ok | 20 | 0.950 | 0.950 | +0.000 | [-0.150, +0.150] | não |
| content_ok | 20 | 0.900 | 0.900 | +0.000 | [-0.150, +0.150] | não |
| forbidden_ok | 20 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| sources_ok | 20 | 0.950 | 1.000 | +0.050 | [+0.000, +0.150] | não |
| grounded_ok | 20 | 0.950 | 1.000 | +0.050 | [+0.000, +0.150] | não |
| judge:groundedness | 20 | 4.800 | 4.700 | -0.100 | [-0.300, +0.000] | não |
| judge:factual_correctness | 20 | 4.800 | 4.650 | -0.150 | [-0.400, +0.000] | não |
| judge:relevance | 20 | 4.850 | 4.900 | +0.050 | [-0.150, +0.300] | não |
| judge:usefulness | 20 | 4.750 | 4.750 | +0.000 | [-0.250, +0.250] | não |

### Pares sem decisão do `replan`: 4

| Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- |
| passed | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| deterministic | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| content | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| route_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| status_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| language_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| tools_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| amounts_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| content_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| forbidden_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| sources_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| grounded_ok | 4 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| judge:groundedness | 4 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| judge:factual_correctness | 4 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| judge:relevance | 4 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| judge:usefulness | 4 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |

### Pares com mudança de plano (`hops > 0` em algum lado): 2

| Critério | n | A | B | B − A | IC 95% | sem o zero |
| --- | --- | --- | --- | --- | --- | --- |
| passed | 2 | 0.500 | 0.000 | -0.500 | [-1.000, +0.000] | não |
| deterministic | 2 | 0.500 | 0.000 | -0.500 | [-1.000, +0.000] | não |
| content | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| route_ok | 2 | 0.500 | 0.000 | -0.500 | [-1.000, +0.000] | não |
| status_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| language_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| tools_ok | 2 | 0.500 | 1.000 | +0.500 | [+0.000, +1.000] | não |
| amounts_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| content_ok | 2 | 0.500 | 1.000 | +0.500 | [+0.000, +1.000] | não |
| forbidden_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| sources_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| grounded_ok | 2 | 1.000 | 1.000 | +0.000 | [+0.000, +0.000] | não |
| judge:groundedness | 2 | 4.500 | 5.000 | +0.500 | [+0.000, +1.000] | não |
| judge:factual_correctness | 2 | 5.000 | 5.000 | +0.000 | [+0.000, +0.000] | não |
| judge:relevance | 2 | 4.500 | 5.000 | +0.500 | [+0.000, +1.000] | não |
| judge:usefulness | 2 | 4.500 | 5.000 | +0.500 | [+0.000, +1.000] | não |

## Decisões de origem `model`

| Lado | Caso | Rep | Rota | Observação | Candidatos | Escolha | Motivo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B | HV080-PT-SUP-CONTRACT-SETTLEMENT | 1 | knowledge | `{"account_dependent": true, "controlled_answer": false, "customer_known": true, "evidence_sufficient": false, "failed_tools": [], "hops": 0, "how_to": false, "just_ran": "knowledge", "knowledge_gap": ["Os trechos não informam, para o seu contrato, qual conta recebe as vendas nem os prazos de recebimento de vendas no débito e no crédito."], "knowledge_mode": "rag", "knowledge_unavailable": false, "pending": [], "ran": ["knowledge"], "route": "knowledge", "support_escalate": false, "support_missing": [], "support_needs_selection": false, "support_points": false}` | support, web | support (incomplete) | A consulta ao contrato e aos dados da conta pode confirmar a conta de recebimento e os prazos de débito e crédito. |
| B | HV080-PT-SUP-CONTRACT-SETTLEMENT | 1 | knowledge | `{"account_dependent": true, "controlled_answer": false, "customer_known": true, "evidence_sufficient": false, "failed_tools": [], "hops": 1, "how_to": false, "just_ran": "support", "knowledge_gap": ["Os trechos não informam, para o seu contrato, qual conta recebe as vendas nem os prazos de recebimento de vendas no débito e no crédito."], "knowledge_mode": "rag", "knowledge_unavailable": false, "pending": [], "ran": ["knowledge", "support"], "route": "knowledge", "support_escalate": false, "support_missing": [], "support_needs_selection": false, "support_points": true}` | nenhum | web (incomplete) | A web search may clarify the deposit account and debit and credit settlement times not found in the contract results. |

## Modelo consultado e recusado pela guarda

Nenhuma.

## Casos sem par

Nenhum.
