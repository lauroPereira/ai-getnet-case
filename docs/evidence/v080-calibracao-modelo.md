# Calibração humana do juiz (v0.8.0)

> **MODELO com dados sintéticos de teste.** Nenhum número abaixo é a calibração do responsável: as respostas, o juiz e o avaliador são inventados (48 respostas fictícias, 24 sorteadas, notas sorteadas com semente fixa) só para mostrar o formato do relatório que `eval-calibrate --import` grava em `docs/evidence/v080-calibracao.md`. O relatório real vem da campanha `v080-qa` e das notas do responsável.

Gerado em 2026-11-04T12:00:00+00:00. Campanha `avaliacao`, avaliador humano `avaliador-ficticio`, rubrica `judge.v3`, juiz `scripted/scripted-judge-v3`.
Amostra de `avaliacao.json` com a semente 20261104 (24 sorteadas de 48 respostas elegíveis, balanceadas por estrato de rota e split, sem ponderar pelo tamanho de cada um). Avaliadas: 24. Sem avaliação (linhas puladas): 0.

> Ressalva de amostra pequena (D19): 24 respostas avaliadas por uma pessoa. A concordância e o kappa têm margem grande com tão poucas linhas (os intervalos abaixo mostram o tamanho dela) e cada recorte por rota ou split tem poucos casos. Leia como indicação de quanto confiar no juiz, não como prova.

## Concordância por critério

| Critério | n | Exata | ±1 | Kappa quadrático | Média humano | Média juiz | Viés (juiz − humano) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| groundedness (fundamentação) | 24 | 0.750 (IC 95%: 0.55 a 0.88) | 0.958 (IC 95%: 0.80 a 0.99) | 0.842 (IC 95%: 0.59 a 0.96) | 4.00 | 4.21 | +0.21 |
| factual_correctness (correção factual) | 24 | 0.750 (IC 95%: 0.55 a 0.88) | 1.000 (IC 95%: 0.86 a 1.00) | 0.868 (IC 95%: 0.73 a 0.95) | 4.08 | 4.17 | +0.08 |
| relevance (relevância) | 24 | 0.875 (IC 95%: 0.69 a 0.96) | 1.000 (IC 95%: 0.86 a 1.00) | 0.940 (IC 95%: 0.83 a 1.00) | 4.21 | 4.08 | -0.12 |
| usefulness (utilidade) | 24 | 0.625 (IC 95%: 0.43 a 0.79) | 0.875 (IC 95%: 0.69 a 0.96) | 0.712 (IC 95%: 0.35 a 0.89) | 3.79 | 4.04 | +0.25 |

## Afirmação sem suporte (veredito)

Concordância exata: 0.833 (IC 95%: 0.64 a 0.93). Kappa (com dois valores, o kappa quadrático é o kappa de Cohen): 0.407 (IC 95%: -0.11 a 0.83).

| | Juiz: sim | Juiz: não |
| --- | --- | --- |
| Humano: sim | 2 | 3 |
| Humano: não | 1 | 18 |

## Divergências grandes (diferença de 2 pontos ou mais, ou veredito oposto)

| Amostra | Caso | Rota | Split | Critério | Humano | Juiz |
| --- | --- | --- | --- | --- | --- | --- |
| S05 | SYN-033 | general_web | holdout | unsupported_claim | sim | não |
| S06 | SYN-008 | knowledge_and_support | holdout | unsupported_claim | sim | não |
| S10 | SYN-002 | knowledge_and_support | dev | usefulness | 5 | 3 |
| S11 | SYN-047 | out_of_scope | holdout | usefulness | 3 | 5 |
| S11 | SYN-047 | out_of_scope | holdout | unsupported_claim | não | sim |
| S12 | SYN-027 | general_web | dev | usefulness | 2 | 4 |
| S20 | SYN-001 | support | dev | unsupported_claim | sim | não |
| S24 | SYN-041 | out_of_scope | dev | groundedness | 2 | 4 |

## Cobertura da amostra avaliada

Rotas: general_web 4, human_handoff 4, knowledge 4, knowledge_and_support 4, out_of_scope 4, support 4. Splits: dev 12, holdout 12.

## Como ler

- Exata: parte das respostas em que humano e juiz deram a mesma nota. ±1: parte em que a diferença é de até um ponto. Os intervalos de ambas são de Wilson (95%).
- Kappa quadrático ponderado: 1 é concordância perfeita; 0 é o que o acaso daria com as mesmas distribuições de notas; negativo é pior que o acaso. Diferenças maiores pesam mais (peso = quadrado da diferença). O intervalo é por reamostragem (bootstrap) das respostas, com a semente da amostra. Quando quase todas as notas são 4 ou 5, o kappa fica baixo mesmo com concordância exata alta; por isso as três medidas aparecem juntas.
- Viés: média das notas do juiz menos a média das notas humanas; positivo é um juiz mais generoso.
- Amostra: balanceada por estrato (rota e split), não ponderada. Cada estrato entra com quantidades parecidas, mesmo quando é raro na campanha; as médias e as concordâncias valem para estas respostas e não estimam as da campanha inteira.
- Dados: respostas do sistema sobre a conta sintética, mascaradas; o arquivo da amostra não traz nenhuma nota do juiz.
