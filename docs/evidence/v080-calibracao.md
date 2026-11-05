# Calibração humana do juiz (v0.8.0)

Gerado em 2026-11-05T16:12:14+00:00. Campanha `v080-all-r3`, avaliador humano `lauro`, rubrica `judge.v3`, juiz `deepseek/deepseek-flash`.
Amostra de `v080-all-r3.json` com a semente 20261104 (24 sorteadas de 44 respostas elegíveis, balanceadas por estrato de rota e split, sem ponderar pelo tamanho de cada um). Avaliadas: 24. Sem avaliação (linhas puladas): 0.

As notas e o veredito de cada linha são do avaliador humano; a localização das evidências por afirmação (qual passagem ou resultado de ferramenta sustenta cada frase da resposta, sem notas) foi assistida por IA em material de apoio não versionado. Conferência do CSV e importação: 2026-11-05.

> Ressalva de amostra pequena (D19): 24 respostas avaliadas por uma pessoa. A concordância e o kappa têm margem grande com tão poucas linhas (os intervalos abaixo mostram o tamanho dela) e cada recorte por rota ou split tem poucos casos. Leia como indicação de quanto confiar no juiz, não como prova.

## Concordância por critério

| Critério | n | Exata | ±1 | Kappa quadrático | Média humano | Média juiz | Viés (juiz − humano) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| groundedness (fundamentação) | 24 | 0.583 (IC 95%: 0.39 a 0.76) | 0.833 (IC 95%: 0.64 a 0.93) | -0.120 (IC 95%: -0.29 a 0.08) | 4.79 | 4.46 | -0.33 |
| factual_correctness (correção factual) | 24 | 0.625 (IC 95%: 0.43 a 0.79) | 0.833 (IC 95%: 0.64 a 0.93) | -0.083 (IC 95%: -0.22 a 0.00) | 4.92 | 4.50 | -0.42 |
| relevance (relevância) | 24 | 0.750 (IC 95%: 0.55 a 0.88) | 1.000 (IC 95%: 0.86 a 1.00) | 0.000 (sem intervalo) | 5.00 | 4.75 | -0.25 |
| usefulness (utilidade) | 24 | 0.583 (IC 95%: 0.39 a 0.76) | 0.917 (IC 95%: 0.74 a 0.98) | -0.027 (IC 95%: -0.30 a 0.36) | 4.71 | 4.54 | -0.17 |

## Afirmação sem suporte (veredito)

Concordância exata: 0.667 (IC 95%: 0.47 a 0.82). Kappa (com dois valores, o kappa quadrático é o kappa de Cohen): -0.200 (IC 95%: -0.33 a 0.00).

| | Juiz: sim | Juiz: não |
| --- | --- | --- |
| Humano: sim | 0 | 4 |
| Humano: não | 4 | 16 |

Casos de borda no kappa:
- relevance: um dos lados não varia: o kappa é 0 por construção; leia a concordância exata

## Divergências grandes (diferença de 2 pontos ou mais, ou veredito oposto)

| Amostra | Caso | Rota | Split | Critério | Humano | Juiz |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | PT06 | knowledge | holdout | unsupported_claim | sim | não |
| S11 | EX02 | general_web | dev | groundedness | 5 | 2 |
| S11 | EX02 | general_web | dev | factual_correctness | 5 | 2 |
| S11 | EX02 | general_web | dev | unsupported_claim | não | sim |
| S13 | PT05 | knowledge_and_support | holdout | groundedness | 3 | 5 |
| S13 | PT05 | knowledge_and_support | holdout | factual_correctness | 3 | 5 |
| S13 | PT05 | knowledge_and_support | holdout | usefulness | 3 | 5 |
| S13 | PT05 | knowledge_and_support | holdout | unsupported_claim | sim | não |
| S16 | EX01 | knowledge | dev | unsupported_claim | sim | não |
| S17 | PT02 | general_web | holdout | groundedness | 5 | 2 |
| S17 | PT02 | general_web | holdout | factual_correctness | 5 | 3 |
| S17 | PT02 | general_web | holdout | unsupported_claim | não | sim |
| S18 | PT07 | general_web | holdout | groundedness | 5 | 3 |
| S18 | PT07 | general_web | holdout | factual_correctness | 5 | 3 |
| S18 | PT07 | general_web | holdout | unsupported_claim | não | sim |
| S21 | PT09 | knowledge | holdout | unsupported_claim | sim | não |
| S22 | V030-CONTRACT-TERMINATION | human_handoff | dev | usefulness | 5 | 3 |
| S22 | V030-CONTRACT-TERMINATION | human_handoff | dev | unsupported_claim | não | sim |

## Cobertura da amostra avaliada

Rotas: clarify 1, general_web 4, human_handoff 2, knowledge 6, knowledge_and_support 4, out_of_scope 2, support 5. Splits: dev 11, holdout 13.

## Como ler

- Exata: parte das respostas em que humano e juiz deram a mesma nota. ±1: parte em que a diferença é de até um ponto. Os intervalos de ambas são de Wilson (95%).
- Kappa quadrático ponderado: 1 é concordância perfeita; 0 é o que o acaso daria com as mesmas distribuições de notas; negativo é pior que o acaso. Diferenças maiores pesam mais (peso = quadrado da diferença). O intervalo é por reamostragem (bootstrap) das respostas, com a semente da amostra. Quando quase todas as notas são 4 ou 5, o kappa fica baixo mesmo com concordância exata alta; por isso as três medidas aparecem juntas.
- Viés: média das notas do juiz menos a média das notas humanas; positivo é um juiz mais generoso.
- Amostra: balanceada por estrato (rota e split), não ponderada. Cada estrato entra com quantidades parecidas, mesmo quando é raro na campanha; as médias e as concordâncias valem para estas respostas e não estimam as da campanha inteira.
- Dados: respostas do sistema sobre a conta sintética, mascaradas; o arquivo da amostra não traz nenhuma nota do juiz.
