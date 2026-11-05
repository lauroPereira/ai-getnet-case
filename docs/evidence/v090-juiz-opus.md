# Calibração humana do juiz: dois juízes (v0.9.0)

Gerado em 2026-11-05T21:12:16+00:00. Campanha `v090-juiz-opus`, avaliador humano `lauro`, rubrica `judge.v3`, juiz `anthropic/claude-opus-5-5`.
Amostra de `v080-all-r3.json` com a semente 20261104 (24 sorteadas de 44 respostas elegíveis, balanceadas por estrato de rota e split, sem ponderar pelo tamanho de cada um). Avaliadas: 24. Sem avaliação (linhas puladas): 0.

> Ressalva de amostra pequena (D19): 24 respostas avaliadas por uma pessoa. A concordância e o kappa têm margem grande com tão poucas linhas (os intervalos abaixo mostram o tamanho dela) e cada recorte por rota ou split tem poucos casos. Leia como indicação de quanto confiar no juiz, não como prova.

## Decisão pela regra D2 (Supervisor, 2026-11-05)

Regra escrita na spec antes do experimento: o Opus vira o juiz padrão se (a) a concordância ±1 não piorar em nenhum critério, (b) a concordância do veredito de afirmação sem suporte passar de 0,667 e pelo menos 2 das 4 respostas com frase genérica (S01, S13, S16, S21) forem marcadas "sim", e (c) a consistência exata entre repetições for ≥ 0,70.

- (a) **atendida**: ±1 de 0,958 / 0,958 / 1,000 / 0,958 contra 0,833 / 0,833 / 1,000 / 0,917 do DeepSeek.
- (b) **não atendida**: a concordância do veredito subiu para 0,875 (kappa 0,357, contra 0,667 e −0,200), mas só S01 foi marcada "sim"; S13, S16 e S21 ficaram "não" nas três repetições (1 de 4, mínimo 2).
- (c) **atendida**: consistência exata 0,972 / 1,000 / 0,889 / 0,806 e 1,000 no veredito, 72 pares, 0 falhas.

Resultado: o caso que a regra chama de lacuna da rubrica. O juiz padrão continua `deepseek/deepseek-flash`; a rubrica `judge.v3` ganha, na próxima versão, a linha sobre afirmação genérica sem fonte; o Opus fica disponível por configuração (`JUDGE_PROVIDER=anthropic JUDGE_MODEL=claude-opus-5-5`). Leitura: o modelo mais forte concorda mais com o humano em tudo o que a rubrica pede e custa 54 vezes mais por julgamento (US$0,0178 contra US$0,00033); o que ele não marca é o que a rubrica não pede. Decisão reversível pelo responsável; registrada também na spec (D2) e no ADR 0021.

As notas humanas são as 24 da v0.8.0, reaproveitadas sem nova avaliação; a localização das evidências por afirmação naquela calibração foi assistida por IA em material não versionado.

## Concordância por critério

| Critério | n | Exata | ±1 | Kappa quadrático | Média humano | Média juiz | Viés (juiz − humano) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| groundedness (fundamentação) | 24 | 0.625 (IC 95%: 0.43 a 0.79) | 0.958 (IC 95%: 0.80 a 0.99) | 0.020 (IC 95%: -0.26 a 0.43) | 4.79 | 4.62 | -0.17 |
| factual_correctness (correção factual) | 24 | 0.625 (IC 95%: 0.43 a 0.79) | 0.958 (IC 95%: 0.80 a 0.99) | 0.163 (IC 95%: 0.00 a 0.45) | 4.92 | 4.58 | -0.33 |
| relevance (relevância) | 24 | 0.833 (IC 95%: 0.64 a 0.93) | 1.000 (IC 95%: 0.86 a 1.00) | 0.000 (sem intervalo) | 5.00 | 4.83 | -0.17 |
| usefulness (utilidade) | 24 | 0.417 (IC 95%: 0.24 a 0.61) | 0.958 (IC 95%: 0.80 a 0.99) | 0.171 (IC 95%: -0.08 a 0.43) | 4.71 | 4.25 | -0.46 |

## Afirmação sem suporte (veredito)

Concordância exata: 0.875 (IC 95%: 0.69 a 0.96). Kappa (com dois valores, o kappa quadrático é o kappa de Cohen): 0.357 (IC 95%: 0.00 a 1.00).

| | Juiz: sim | Juiz: não |
| --- | --- | --- |
| Humano: sim | 1 | 3 |
| Humano: não | 0 | 20 |

Casos de borda no kappa:
- relevance: um dos lados não varia: o kappa é 0 por construção; leia a concordância exata

## Divergências grandes (diferença de 2 pontos ou mais, ou veredito oposto)

| Amostra | Caso | Rota | Split | Critério | Humano | Juiz |
| --- | --- | --- | --- | --- | --- | --- |
| S04 | NOEV | knowledge | holdout | factual_correctness | 5 | 3 |
| S06 | UC18 | clarify | holdout | usefulness | 5 | 3 |
| S13 | PT05 | knowledge_and_support | holdout | groundedness | 3 | 5 |
| S13 | PT05 | knowledge_and_support | holdout | unsupported_claim | sim | não |
| S16 | EX01 | knowledge | dev | unsupported_claim | sim | não |
| S21 | PT09 | knowledge | holdout | unsupported_claim | sim | não |

## Dois juízes contra as mesmas notas humanas

A = `anthropic/claude-opus-5-5` (campanha `v090-juiz-opus`); B = `deepseek/deepseek-flash`, o juiz da campanha original `v080-all-r3`. As 24 notas humanas são as gravadas na campanha original, conferidas linha a linha; não houve avaliação humana nova. A entra com o julgamento da repetição 1 de cada resposta na execução `v090-juiz-opus-r3`; B, com o julgamento ao qual cada nota foi ligada na campanha original (execução `legado`). Os dois julgaram a mesma evidência gravada.

| Critério | Exata A | Exata B | ±1 A | ±1 B | Kappa A | Kappa B | Viés A | Viés B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| groundedness (fundamentação) | 0.625 | 0.583 | 0.958 | 0.833 | 0.020 (IC 95%: -0.26 a 0.43) | -0.120 (IC 95%: -0.29 a 0.08) | -0.17 | -0.33 |
| factual_correctness (correção factual) | 0.625 | 0.625 | 0.958 | 0.833 | 0.163 (IC 95%: 0.00 a 0.45) | -0.083 (IC 95%: -0.22 a 0.00) | -0.33 | -0.42 |
| relevance (relevância) | 0.833 | 0.750 | 1.000 | 1.000 | 0.000 (sem intervalo) | 0.000 (sem intervalo) | -0.17 | -0.25 |
| usefulness (utilidade) | 0.417 | 0.583 | 0.958 | 0.917 | 0.171 (IC 95%: -0.08 a 0.43) | -0.027 (IC 95%: -0.30 a 0.36) | -0.46 | -0.17 |
| unsupported_claim | 0.875 | 0.667 | - | - | 0.357 (IC 95%: 0.00 a 1.00) | -0.200 (IC 95%: -0.33 a 0.00) | - | - |

Matriz do veredito `unsupported_claim` (humano × juiz):

| Juiz | Ambos sim | Só humano | Só juiz | Nenhum |
| --- | --- | --- | --- | --- |
| A `anthropic/claude-opus-5-5` | 1 | 3 | 0 | 20 |
| B `deepseek/deepseek-flash` | 0 | 4 | 4 | 16 |

Respostas que o humano ou algum juiz marcou como afirmação sem suporte:

| Amostra | Caso | Rota | Humano | A | B |
| --- | --- | --- | --- | --- | --- |
| S01 | PT06 | knowledge | sim | sim | não |
| S11 | EX02 | general_web | não | não | sim |
| S13 | PT05 | knowledge_and_support | sim | não | não |
| S16 | EX01 | knowledge | sim | não | não |
| S17 | PT02 | general_web | não | não | sim |
| S18 | PT07 | general_web | não | não | sim |
| S21 | PT09 | knowledge | sim | não | não |
| S22 | V030-CONTRACT-TERMINATION | human_handoff | não | não | sim |

## Julgamentos considerados

Execuções de cada juiz que entram no relatório (o `--name` do `eval` que gravou os julgamentos) e quantos julgamentos entram em cada bloco. Outras execuções do mesmo juiz sobre estas respostas, como a sonda, ficam de fora.

| Juiz | Execuções | Concordância | Consistência | Custo e tokens |
| --- | --- | --- | --- | --- |
| A `anthropic/claude-opus-5-5` | `v090-juiz-opus-r3` | 24 | 72 | 72 |
| B `deepseek/deepseek-flash` | `legado` | 24 | 72 | 72 |

`legado`: julgamentos gravados antes da v0.9.0, que não guardam o nome da execução; contam como uma execução só, então podem somar mais de uma rodada do mesmo juiz.

## Consistência de cada juiz entre repetições

Os julgamentos `judge.v3` de cada juiz sobre estas respostas, das execuções da tabela acima. Exata: parte dos pares de julgamentos da mesma resposta com a mesma nota; ±1: diferença de até 1 ponto. Sem pares, o juiz julgou cada resposta uma vez só.

| Juiz | Respostas | Julgamentos | Falhos | Critério | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A `anthropic/claude-opus-5-5` | 24 | 72 | 0 | groundedness | 0.972 | 1.0 | 72 |
| A `anthropic/claude-opus-5-5` | 24 | 72 | 0 | factual_correctness | 1.0 | 1.0 | 72 |
| A `anthropic/claude-opus-5-5` | 24 | 72 | 0 | relevance | 0.889 | 1.0 | 72 |
| A `anthropic/claude-opus-5-5` | 24 | 72 | 0 | usefulness | 0.806 | 1.0 | 72 |
| A `anthropic/claude-opus-5-5` | 24 | 72 | 0 | unsupported_claim | 1.0 | - | 72 |
| B `deepseek/deepseek-flash` | 24 | 72 | 0 | groundedness | 0.771 | 0.99 | 96 |
| B `deepseek/deepseek-flash` | 24 | 72 | 0 | factual_correctness | 0.74 | 0.979 | 96 |
| B `deepseek/deepseek-flash` | 24 | 72 | 0 | relevance | 0.729 | 0.969 | 96 |
| B `deepseek/deepseek-flash` | 24 | 72 | 0 | usefulness | 0.719 | 0.969 | 96 |
| B `deepseek/deepseek-flash` | 24 | 72 | 0 | unsupported_claim | 0.969 | - | 96 |

## Custo por julgamento

Custo gravado em cada julgamento (`run_evaluations.cost_usd`; um julgamento falho custa o que foi reservado ou cobrado).

| Juiz | Julgamentos | Falhos | Custo total (US$) | Custo por julgamento (US$) |
| --- | --- | --- | --- | --- |
| A `anthropic/claude-opus-5-5` | 72 | 0 | 1.284220 | 0.017836 |
| B `deepseek/deepseek-flash` | 72 | 0 | 0.023773 | 0.000330 |

Tokens gravados em cada julgamento (desde a v0.9.0; os anteriores não os guardam), total / média por julgamento. A entrada inclui o cache lido e o criado; a saída inclui o pensamento.

| Juiz | Julgamentos com tokens | Entrada | Cache lido | Cache criado | Saída |
| --- | --- | --- | --- | --- | --- |
| A `anthropic/claude-opus-5-5` | 72 | 222255 / 3086.9 | 0 / 0.0 | 0 / 0.0 | 19760 / 274.4 |
| B `deepseek/deepseek-flash` | 0 | - | - | - | - |

## Cobertura da amostra avaliada

Rotas: clarify 1, general_web 4, human_handoff 2, knowledge 6, knowledge_and_support 4, out_of_scope 2, support 5. Splits: dev 11, holdout 13.

## Como ler

- Exata: parte das respostas em que humano e juiz deram a mesma nota. ±1: parte em que a diferença é de até um ponto. Os intervalos de ambas são de Wilson (95%).
- Kappa quadrático ponderado: 1 é concordância perfeita; 0 é o que o acaso daria com as mesmas distribuições de notas; negativo é pior que o acaso. Diferenças maiores pesam mais (peso = quadrado da diferença). O intervalo é por reamostragem (bootstrap) das respostas, com a semente da amostra. Quando quase todas as notas são 4 ou 5, o kappa fica baixo mesmo com concordância exata alta; por isso as três medidas aparecem juntas.
- Viés: média das notas do juiz menos a média das notas humanas; positivo é um juiz mais generoso.
- Amostra: balanceada por estrato (rota e split), não ponderada. Cada estrato entra com quantidades parecidas, mesmo quando é raro na campanha; as médias e as concordâncias valem para estas respostas e não estimam as da campanha inteira.
- Dados: respostas do sistema sobre a conta sintética, mascaradas; o arquivo da amostra não traz nenhuma nota do juiz.
