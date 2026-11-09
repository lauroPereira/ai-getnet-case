# Calibração humana do juiz (v0.8.0)

Gerado em 2026-11-06T12:00:00+00:00. Campanha `v080-all`, avaliador humano `lauro`, rubrica `judge.v3`, juiz `scripted/scripted-judge-v3`.
Amostra de `v080-all.json` com a semente 20261104 (24 sorteadas de 30 respostas elegíveis, balanceadas por estrato de rota e split, sem ponderar pelo tamanho de cada um). Avaliadas: 23. Sem avaliação (linhas puladas): 1.

> Ressalva de amostra pequena (D19): 23 respostas avaliadas por uma pessoa. A concordância e o kappa têm margem grande com tão poucas linhas (os intervalos abaixo mostram o tamanho dela) e cada recorte por rota ou split tem poucos casos. Leia como indicação de quanto confiar no juiz, não como prova.

## Concordância por critério

| Critério | n | Exata | ±1 | Kappa quadrático | Média humano | Média juiz | Viés (juiz − humano) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| groundedness (fundamentação) | 23 | 0.522 (IC 95%: 0.33 a 0.71) | 1.000 (IC 95%: 0.86 a 1.00) | 0.860 (IC 95%: 0.73 a 0.93) | 2.96 | 2.91 | -0.04 |
| factual_correctness (correção factual) | 23 | 0.565 (IC 95%: 0.37 a 0.74) | 1.000 (IC 95%: 0.86 a 1.00) | 0.900 (IC 95%: 0.81 a 0.95) | 3.00 | 3.00 | +0.00 |
| relevance (relevância) | 23 | 0.435 (IC 95%: 0.26 a 0.63) | 1.000 (IC 95%: 0.86 a 1.00) | 0.858 (IC 95%: 0.74 a 0.92) | 2.74 | 2.87 | +0.13 |
| usefulness (utilidade) | 23 | 0.652 (IC 95%: 0.45 a 0.81) | 1.000 (IC 95%: 0.86 a 1.00) | 0.000 (sem intervalo) | 1.35 | 1.00 | -0.35 |

## Afirmação sem suporte (veredito)

Concordância exata: 0.783 (IC 95%: 0.58 a 0.90). Kappa (com dois valores, o kappa quadrático é o kappa de Cohen): 0.475 (IC 95%: 0.02 a 0.83).

| | Juiz: sim | Juiz: não |
| --- | --- | --- |
| Humano: sim | 4 | 4 |
| Humano: não | 1 | 14 |

Casos de borda no kappa:
- usefulness: um dos lados não varia: o kappa é 0 por construção; leia a concordância exata

## Divergências grandes (diferença de 2 pontos ou mais, ou veredito oposto)

| Amostra | Caso | Rota | Split | Critério | Humano | Juiz |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | V80-004 | knowledge_and_support | dev | unsupported_claim | não | sim |
| S06 | V80-030 | knowledge | dev | unsupported_claim | sim | não |
| S11 | V80-014 | knowledge_and_support | dev | unsupported_claim | sim | não |
| S16 | V80-019 | knowledge_and_support | holdout | unsupported_claim | sim | não |
| S21 | V80-010 | knowledge | dev | unsupported_claim | sim | não |

## Cobertura da amostra avaliada

Rotas: general_web 4, human_handoff 5, knowledge 5, knowledge_and_support 5, support 4. Splits: dev 12, holdout 11.

## Como ler

- Exata: parte das respostas em que humano e juiz deram a mesma nota. ±1: parte em que a diferença é de até um ponto. Os intervalos de ambas são de Wilson (95%).
- Kappa quadrático ponderado: 1 é concordância perfeita; 0 é o que o acaso daria com as mesmas distribuições de notas; negativo é pior que o acaso. Diferenças maiores pesam mais (peso = quadrado da diferença). O intervalo é por reamostragem (bootstrap) das respostas, com a semente da amostra. Quando quase todas as notas são 4 ou 5, o kappa fica baixo mesmo com concordância exata alta; por isso as três medidas aparecem juntas.
- Viés: média das notas do juiz menos a média das notas humanas; positivo é um juiz mais generoso.
- Amostra: balanceada por estrato (rota e split), não ponderada. Cada estrato entra com quantidades parecidas, mesmo quando é raro na campanha; as médias e as concordâncias valem para estas respostas e não estimam as da campanha inteira.
- Dados: respostas do sistema sobre a conta sintética, mascaradas; o arquivo da amostra não traz nenhuma nota do juiz.
