# v0.8.0 r6 — variação do juiz (composição de 44 respostas)

Respostas: 44; julgamentos: 132; falhas do juiz: 0; julgamentos com `unsupported_claim`: 8; custo do juiz (registrado): US$0.03337818.

| Origem das respostas | Respostas | Relatório | SHA-256 |
|---|---:|---|---|
| `1baa7b31` (v080-r6-1baa7b31-healthy.json) | 6 | v080-r6-1baa7b31-judge-r6-healthy.json | `1f4345727bbb52ba…` |
| `658c70ad` (v080-healthy-r5.json) | 6 | v080-r6-1baa7b31-judge-r5-healthy.json | `0bbce1cd9e0a5ca0…` |
| `658c70ad` (v080-tool-down-r5.json) | 1 | v080-r6-1baa7b31-judge-r5-tool-down.json | `63ea4eb0a57b5357…` |
| `4c3c8a98` (v080-healthy-r4.json) | 9 | v080-r6-1baa7b31-judge-r4.json | `f2385e5303858287…` |
| `f8daab03` (v080-all-r3.json) | 22 | v080-r6-1baa7b31-judge-r3.json | `9a4da74e5c4cbc91…` |

## Variação: variação do juiz (as mesmas respostas gravadas avaliadas N vezes)

Repetições por caso: 3. Desvio: média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso. Concordância: parte dos pares de repetições do mesmo caso com score igual (exata) ou com diferença de até 1 ponto (±1).

> Ressalva de amostra pequena (D19): 44 casos com 3 repetições cada; os recortes por rota e por split têm menos casos ainda (marcados com * quando há menos de 10). Médias, desvios e concordâncias indicam quanto confiar no resultado, não o provam, e um único caso muda um recorte pequeno.

| Recorte | Casos | Critério | Média | Desvio | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 44 | groundedness | 4.68 | 0.13 | 0.856 | 0.992 | 132 |
| geral | 44 | factual_correctness | 4.67 | 0.14 | 0.841 | 0.992 | 132 |
| geral | 44 | relevance | 4.81 | 0.16 | 0.818 | 0.985 | 132 |
| geral | 44 | usefulness | 4.59 | 0.22 | 0.758 | 0.985 | 132 |
| geral | 44 | unsupported_claim (taxa de verdadeiro) | 0.061 | - | 0.985 | - | 132 |
| rota clarify | 1* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 3 |
| rota clarify | 1* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 3 |
| rota general_web | 4* | groundedness | 2.5 | 0.54 | 0.417 | 0.917 | 12 |
| rota general_web | 4* | factual_correctness | 2.5 | 0.54 | 0.417 | 0.917 | 12 |
| rota general_web | 4* | relevance | 4.33 | 0.64 | 0.333 | 0.833 | 12 |
| rota general_web | 4* | usefulness | 3.67 | 0.72 | 0.333 | 0.833 | 12 |
| rota general_web | 4* | unsupported_claim (taxa de verdadeiro) | 0.667 | - | 0.833 | - | 12 |
| rota human_handoff | 2* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | usefulness | 4.5 | 0.0 | 1.0 | 1.0 | 6 |
| rota human_handoff | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota knowledge | 13 | groundedness | 4.77 | 0.13 | 0.846 | 1.0 | 39 |
| rota knowledge | 13 | factual_correctness | 4.74 | 0.13 | 0.846 | 1.0 | 39 |
| rota knowledge | 13 | relevance | 4.77 | 0.18 | 0.795 | 1.0 | 39 |
| rota knowledge | 13 | usefulness | 4.51 | 0.18 | 0.795 | 1.0 | 39 |
| rota knowledge | 13 | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 39 |
| rota knowledge_and_support | 5* | groundedness | 4.87 | 0.23 | 0.733 | 1.0 | 15 |
| rota knowledge_and_support | 5* | factual_correctness | 4.87 | 0.23 | 0.733 | 1.0 | 15 |
| rota knowledge_and_support | 5* | relevance | 4.6 | 0.35 | 0.6 | 1.0 | 15 |
| rota knowledge_and_support | 5* | usefulness | 4.73 | 0.23 | 0.733 | 1.0 | 15 |
| rota knowledge_and_support | 5* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 15 |
| rota out_of_scope | 2* | groundedness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | factual_correctness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | relevance | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | usefulness | 5.0 | 0.0 | 1.0 | 1.0 | 6 |
| rota out_of_scope | 2* | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 6 |
| rota support | 17 | groundedness | 4.98 | 0.03 | 0.961 | 1.0 | 51 |
| rota support | 17 | factual_correctness | 4.96 | 0.07 | 0.922 | 1.0 | 51 |
| rota support | 17 | relevance | 4.96 | 0.03 | 0.961 | 1.0 | 51 |
| rota support | 17 | usefulness | 4.76 | 0.2 | 0.765 | 1.0 | 51 |
| rota support | 17 | unsupported_claim (taxa de verdadeiro) | 0.0 | - | 1.0 | - | 51 |
| split dev | 27 | groundedness | 4.72 | 0.11 | 0.877 | 1.0 | 81 |
| split dev | 27 | factual_correctness | 4.73 | 0.09 | 0.901 | 1.0 | 81 |
| split dev | 27 | relevance | 4.88 | 0.14 | 0.84 | 0.988 | 81 |
| split dev | 27 | usefulness | 4.58 | 0.21 | 0.753 | 1.0 | 81 |
| split dev | 27 | unsupported_claim (taxa de verdadeiro) | 0.037 | - | 1.0 | - | 81 |
| split holdout | 17 | groundedness | 4.63 | 0.16 | 0.824 | 0.98 | 51 |
| split holdout | 17 | factual_correctness | 4.57 | 0.23 | 0.745 | 0.98 | 51 |
| split holdout | 17 | relevance | 4.71 | 0.19 | 0.784 | 0.98 | 51 |
| split holdout | 17 | usefulness | 4.61 | 0.24 | 0.765 | 0.961 | 51 |
| split holdout | 17 | unsupported_claim (taxa de verdadeiro) | 0.098 | - | 0.961 | - | 51 |
