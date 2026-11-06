# Calibração humana do juiz: juízes e rubricas (v0.10.0)

Gerado em 2026-11-06T03:26:08+00:00. Campanha `v0100-juiz-v4`, avaliador humano `lauro`, rubrica `judge.v4`, juiz `deepseek/deepseek-flash`.
Amostra de `v080-all-r3.json` com a semente 20261104 (24 sorteadas de 44 respostas elegíveis, balanceadas por estrato de rota e split, sem ponderar pelo tamanho de cada um). Avaliadas: 24. Sem avaliação (linhas puladas): 0.

> Ressalva de amostra pequena (D19): 24 respostas avaliadas por uma pessoa. A concordância e o kappa têm margem grande com tão poucas linhas (os intervalos abaixo mostram o tamanho dela) e cada recorte por rota ou split tem poucos casos. Leia como indicação de quanto confiar no juiz, não como prova.

## Decisão pela regra D2 da v0.10.0 (Supervisor, 2026-11-06)

Regra escrita na spec antes de rodar: a `judge.v4` vira padrão se, com o DeepSeek, (i) a concordância do veredito com o humano não cair, (ii) pelo menos 2 das 4 frases genéricas (S01, S13, S16, S21) forem marcadas e (iii) a concordância ±1 de nenhum critério piorar mais de 0,05. O Opus é reportado, não decide.

- DeepSeek v4 × v3: (i) **sim**, 0,792 contra 0,667; (ii) **não**, 0 de 4 (S01 só em duas das três repetições); (iii) **sim**, variações de até 0,042.
- Opus v4 × v3 (reportado): (i) sim, 0,917 contra 0,875; (ii) sim, S01 e S21 nas três repetições; (iii) sim.

Resultado: a `judge.v4` **não vira padrão nesta versão**; `judge.v3` continua, e a v4 fica disponível por `--rubric v4`. Leitura: a frase nova da rubrica funciona quando o modelo consegue aplicá-la (o Opus passou a marcar metade das genéricas sem piorar nada), e o juiz padrão não a aplica; a lacuna é de rubrica **e** de modelo, e fechá-la exige trocar os dois, o que a regra D2 da v0.9.0 (custo 54×) não autoriza sozinha. Fica como próximo passo: avaliar o Sonnet 5.5 sob v4 como meio-termo de custo. Decisão reversível pelo responsável; registrada na spec (D2) e no ADR 0022.

As notas humanas são as 24 da v0.8.0, reaproveitadas sem nova avaliação.

## Concordância por critério

| Critério | n | Exata | ±1 | Kappa quadrático | Média humano | Média juiz | Viés (juiz − humano) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| groundedness (fundamentação) | 24 | 0.625 (IC 95%: 0.43 a 0.79) | 0.792 (IC 95%: 0.60 a 0.91) | -0.121 (IC 95%: -0.29 a 0.12) | 4.79 | 4.54 | -0.25 |
| factual_correctness (correção factual) | 24 | 0.625 (IC 95%: 0.43 a 0.79) | 0.792 (IC 95%: 0.60 a 0.91) | -0.091 (IC 95%: -0.23 a 0.00) | 4.92 | 4.50 | -0.42 |
| relevance (relevância) | 24 | 0.792 (IC 95%: 0.60 a 0.91) | 1.000 (IC 95%: 0.86 a 1.00) | 0.000 (sem intervalo) | 5.00 | 4.79 | -0.21 |
| usefulness (utilidade) | 24 | 0.542 (IC 95%: 0.35 a 0.72) | 0.958 (IC 95%: 0.80 a 0.99) | -0.031 (IC 95%: -0.34 a 0.37) | 4.71 | 4.54 | -0.17 |

## Afirmação sem suporte (veredito)

Concordância exata: 0.792 (IC 95%: 0.60 a 0.91). Kappa (com dois valores, o kappa quadrático é o kappa de Cohen): -0.071 (IC 95%: -0.19 a 0.00).

| | Juiz: sim | Juiz: não |
| --- | --- | --- |
| Humano: sim | 0 | 4 |
| Humano: não | 1 | 19 |

Casos de borda no kappa:
- relevance: um dos lados não varia: o kappa é 0 por construção; leia a concordância exata

## Divergências grandes (diferença de 2 pontos ou mais, ou veredito oposto)

| Amostra | Caso | Rota | Split | Critério | Humano | Juiz |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | PT06 | knowledge | holdout | unsupported_claim | sim | não |
| S04 | NOEV | knowledge | holdout | groundedness | 5 | 3 |
| S04 | NOEV | knowledge | holdout | factual_correctness | 5 | 3 |
| S11 | EX02 | general_web | dev | groundedness | 5 | 3 |
| S11 | EX02 | general_web | dev | factual_correctness | 5 | 3 |
| S13 | PT05 | knowledge_and_support | holdout | groundedness | 3 | 5 |
| S13 | PT05 | knowledge_and_support | holdout | factual_correctness | 3 | 5 |
| S13 | PT05 | knowledge_and_support | holdout | usefulness | 3 | 5 |
| S13 | PT05 | knowledge_and_support | holdout | unsupported_claim | sim | não |
| S16 | EX01 | knowledge | dev | unsupported_claim | sim | não |
| S17 | PT02 | general_web | holdout | groundedness | 5 | 3 |
| S17 | PT02 | general_web | holdout | factual_correctness | 5 | 3 |
| S18 | PT07 | general_web | holdout | groundedness | 5 | 3 |
| S18 | PT07 | general_web | holdout | factual_correctness | 5 | 3 |
| S18 | PT07 | general_web | holdout | unsupported_claim | não | sim |
| S21 | PT09 | knowledge | holdout | unsupported_claim | sim | não |

## Juízes e rubricas contra as mesmas notas humanas

As 24 notas humanas são as gravadas na campanha original `v080-all-r3`, conferidas linha a linha; não houve avaliação humana nova. O é o juiz ao qual cada nota foi ligada na campanha original; cada outro bloco entra com o julgamento da repetição 1 de cada resposta na execução e sob a rubrica indicadas. As notas desta campanha (`v0100-juiz-v4`) ficam ligadas ao bloco A. Todos julgaram a mesma evidência gravada.

| Bloco | Juiz | Rubrica | Execuções |
| --- | --- | --- | --- |
| O | `deepseek/deepseek-flash` | `judge.v3` | `legado` |
| A | `deepseek/deepseek-flash` | `judge.v4` | `v0100-juiz-deepseek-v4` |
| B | `anthropic/claude-opus-5-5` | `judge.v3` | `v090-juiz-opus-r3` |
| C | `anthropic/claude-opus-5-5` | `judge.v4` | `v0100-juiz-opus-v4` |

## Concordância de cada bloco com o humano

| Critério | Bloco | Exata | ±1 | Kappa quadrático | Viés (juiz − humano) |
| --- | --- | --- | --- | --- | --- |
| groundedness (fundamentação) | O `deepseek/deepseek-flash` judge.v3 | 0.583 | 0.833 | -0.120 (IC 95%: -0.29 a 0.08) | -0.33 |
| groundedness (fundamentação) | A `deepseek/deepseek-flash` judge.v4 | 0.625 | 0.792 | -0.121 (IC 95%: -0.29 a 0.12) | -0.25 |
| groundedness (fundamentação) | B `anthropic/claude-opus-5-5` judge.v3 | 0.625 | 0.958 | 0.020 (IC 95%: -0.26 a 0.43) | -0.17 |
| groundedness (fundamentação) | C `anthropic/claude-opus-5-5` judge.v4 | 0.667 | 0.917 | 0.018 (IC 95%: -0.23 a 0.43) | -0.17 |
| factual_correctness (correção factual) | O `deepseek/deepseek-flash` judge.v3 | 0.625 | 0.833 | -0.083 (IC 95%: -0.22 a 0.00) | -0.42 |
| factual_correctness (correção factual) | A `deepseek/deepseek-flash` judge.v4 | 0.625 | 0.792 | -0.091 (IC 95%: -0.23 a 0.00) | -0.42 |
| factual_correctness (correção factual) | B `anthropic/claude-opus-5-5` judge.v3 | 0.625 | 0.958 | 0.163 (IC 95%: 0.00 a 0.45) | -0.33 |
| factual_correctness (correção factual) | C `anthropic/claude-opus-5-5` judge.v4 | 0.583 | 0.958 | 0.143 (IC 95%: 0.00 a 0.45) | -0.38 |
| relevance (relevância) | O `deepseek/deepseek-flash` judge.v3 | 0.750 | 1.000 | 0.000 (sem intervalo) | -0.25 |
| relevance (relevância) | A `deepseek/deepseek-flash` judge.v4 | 0.792 | 1.000 | 0.000 (sem intervalo) | -0.21 |
| relevance (relevância) | B `anthropic/claude-opus-5-5` judge.v3 | 0.833 | 1.000 | 0.000 (sem intervalo) | -0.17 |
| relevance (relevância) | C `anthropic/claude-opus-5-5` judge.v4 | 0.750 | 0.958 | 0.000 (sem intervalo) | -0.29 |
| usefulness (utilidade) | O `deepseek/deepseek-flash` judge.v3 | 0.583 | 0.917 | -0.027 (IC 95%: -0.30 a 0.36) | -0.17 |
| usefulness (utilidade) | A `deepseek/deepseek-flash` judge.v4 | 0.542 | 0.958 | -0.031 (IC 95%: -0.34 a 0.37) | -0.17 |
| usefulness (utilidade) | B `anthropic/claude-opus-5-5` judge.v3 | 0.417 | 0.958 | 0.171 (IC 95%: -0.08 a 0.43) | -0.46 |
| usefulness (utilidade) | C `anthropic/claude-opus-5-5` judge.v4 | 0.500 | 1.000 | 0.304 (IC 95%: 0.00 a 0.53) | -0.33 |

Veredito `unsupported_claim` (humano × juiz):

| Bloco | Exata | Kappa | Ambos sim | Só humano | Só juiz | Nenhum |
| --- | --- | --- | --- | --- | --- | --- |
| O `deepseek/deepseek-flash` judge.v3 | 0.667 | -0.200 (IC 95%: -0.33 a 0.00) | 0 | 4 | 4 | 16 |
| A `deepseek/deepseek-flash` judge.v4 | 0.792 | -0.071 (IC 95%: -0.19 a 0.00) | 0 | 4 | 1 | 19 |
| B `anthropic/claude-opus-5-5` judge.v3 | 0.875 | 0.357 (IC 95%: 0.00 a 1.00) | 1 | 3 | 0 | 20 |
| C `anthropic/claude-opus-5-5` judge.v4 | 0.917 | 0.625 (IC 95%: 0.00 a 1.00) | 2 | 2 | 0 | 20 |

## Frases genéricas sem fonte (S01, S13, S16, S21)

As quatro respostas em que o humano marcou uma frase genérica sem fonte na calibração da v0.8.0 e nenhum juiz marcou (ADR 0021). A `judge.v4` acrescenta esse caso à definição de afirmação sem suporte.

| Amostra | Caso | Rota | Humano | O | A | B | C |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | PT06 | knowledge | sim | não | não | sim | sim |
| S13 | PT05 | knowledge_and_support | sim | não | não | não | não |
| S16 | EX01 | knowledge | sim | não | não | não | não |
| S21 | PT09 | knowledge | sim | não | não | não | sim |
| Marcadas | - | - | 4 de 4 | 0 de 4 | 0 de 4 | 1 de 4 | 2 de 4 |

Respostas que o humano ou algum bloco marcou como afirmação sem suporte:

| Amostra | Caso | Rota | Humano | O | A | B | C |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | PT06 | knowledge | sim | não | não | sim | sim |
| S11 | EX02 | general_web | não | sim | não | não | não |
| S13 | PT05 | knowledge_and_support | sim | não | não | não | não |
| S16 | EX01 | knowledge | sim | não | não | não | não |
| S17 | PT02 | general_web | não | sim | não | não | não |
| S18 | PT07 | general_web | não | sim | sim | não | não |
| S21 | PT09 | knowledge | sim | não | não | não | sim |
| S22 | V030-CONTRACT-TERMINATION | human_handoff | não | sim | não | não | não |

## Regra D2 da v0.10.0 (informativa)

Calculada com os números acima, sem decidir. Pela D2, a `judge.v4` vira padrão se, com o juiz padrão (`deepseek/deepseek-flash`), (a) a concordância do veredito com o humano não cair, (b) pelo menos 2 das 4 frases genéricas forem marcadas e (c) a concordância ±1 de nenhum critério piorar mais de 0.05; os outros juízes são reportados e não decidem. Cada bloco `judge.v4` é comparado com o bloco `judge.v3` do mesmo juiz. A decisão é registrada na tarefa 86.

- A `deepseek/deepseek-flash` judge.v4 contra O `deepseek/deepseek-flash` judge.v3: (a) veredito 0.792 contra 0.667, não cai: sim; (b) frases genéricas marcadas: 0 de 4, pelo menos 2: não; (c) ±1 groundedness 0.792 contra 0.833 (-0.042), factual_correctness 0.792 contra 0.833 (-0.042), relevance 1.000 contra 1.000 (+0.000), usefulness 0.958 contra 0.917 (+0.042), nenhum piora mais de 0.05: sim. Três condições atendidas: não.
- C `anthropic/claude-opus-5-5` judge.v4 contra B `anthropic/claude-opus-5-5` judge.v3: (a) veredito 0.917 contra 0.875, não cai: sim; (b) frases genéricas marcadas: 2 de 4, pelo menos 2: sim; (c) ±1 groundedness 0.917 contra 0.958 (-0.042), factual_correctness 0.958 contra 0.958 (+0.000), relevance 0.958 contra 1.000 (-0.042), usefulness 1.000 contra 0.958 (+0.042), nenhum piora mais de 0.05: sim. Três condições atendidas: sim.

## Julgamentos considerados

Execuções de cada bloco que entram no relatório (o `--name` do `eval` que gravou os julgamentos) e quantos julgamentos entram em cada medida. Outras execuções do mesmo juiz, ou da mesma execução sob outra rubrica, ficam de fora.

| Bloco | Execuções | Concordância | Consistência | Custo e tokens |
| --- | --- | --- | --- | --- |
| O `deepseek/deepseek-flash` judge.v3 | `legado` | 24 | 72 | 72 |
| A `deepseek/deepseek-flash` judge.v4 | `v0100-juiz-deepseek-v4` | 24 | 72 | 72 |
| B `anthropic/claude-opus-5-5` judge.v3 | `v090-juiz-opus-r3` | 24 | 72 | 72 |
| C `anthropic/claude-opus-5-5` judge.v4 | `v0100-juiz-opus-v4` | 24 | 72 | 72 |

`legado`: julgamentos gravados antes da v0.9.0, que não guardam o nome da execução; contam como uma execução só, então podem somar mais de uma rodada do mesmo juiz.

## Consistência de cada juiz entre repetições

Os julgamentos de cada bloco sobre estas respostas, do juiz, da rubrica e das execuções da tabela acima. Exata: parte dos pares de julgamentos da mesma resposta com a mesma nota; ±1: diferença de até 1 ponto. Sem pares, o juiz julgou cada resposta uma vez só.

| Juiz | Respostas | Julgamentos | Falhos | Critério | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| O `deepseek/deepseek-flash` judge.v3 | 24 | 72 | 0 | groundedness | 0.771 | 0.99 | 96 |
| O `deepseek/deepseek-flash` judge.v3 | 24 | 72 | 0 | factual_correctness | 0.74 | 0.979 | 96 |
| O `deepseek/deepseek-flash` judge.v3 | 24 | 72 | 0 | relevance | 0.729 | 0.969 | 96 |
| O `deepseek/deepseek-flash` judge.v3 | 24 | 72 | 0 | usefulness | 0.719 | 0.969 | 96 |
| O `deepseek/deepseek-flash` judge.v3 | 24 | 72 | 0 | unsupported_claim | 0.969 | - | 96 |
| A `deepseek/deepseek-flash` judge.v4 | 24 | 72 | 0 | groundedness | 0.819 | 0.958 | 72 |
| A `deepseek/deepseek-flash` judge.v4 | 24 | 72 | 0 | factual_correctness | 0.75 | 1.0 | 72 |
| A `deepseek/deepseek-flash` judge.v4 | 24 | 72 | 0 | relevance | 0.694 | 1.0 | 72 |
| A `deepseek/deepseek-flash` judge.v4 | 24 | 72 | 0 | usefulness | 0.625 | 0.986 | 72 |
| A `deepseek/deepseek-flash` judge.v4 | 24 | 72 | 0 | unsupported_claim | 0.917 | - | 72 |
| B `anthropic/claude-opus-5-5` judge.v3 | 24 | 72 | 0 | groundedness | 0.972 | 1.0 | 72 |
| B `anthropic/claude-opus-5-5` judge.v3 | 24 | 72 | 0 | factual_correctness | 1.0 | 1.0 | 72 |
| B `anthropic/claude-opus-5-5` judge.v3 | 24 | 72 | 0 | relevance | 0.889 | 1.0 | 72 |
| B `anthropic/claude-opus-5-5` judge.v3 | 24 | 72 | 0 | usefulness | 0.806 | 1.0 | 72 |
| B `anthropic/claude-opus-5-5` judge.v3 | 24 | 72 | 0 | unsupported_claim | 1.0 | - | 72 |
| C `anthropic/claude-opus-5-5` judge.v4 | 24 | 72 | 0 | groundedness | 0.972 | 1.0 | 72 |
| C `anthropic/claude-opus-5-5` judge.v4 | 24 | 72 | 0 | factual_correctness | 1.0 | 1.0 | 72 |
| C `anthropic/claude-opus-5-5` judge.v4 | 24 | 72 | 0 | relevance | 0.917 | 1.0 | 72 |
| C `anthropic/claude-opus-5-5` judge.v4 | 24 | 72 | 0 | usefulness | 0.806 | 1.0 | 72 |
| C `anthropic/claude-opus-5-5` judge.v4 | 24 | 72 | 0 | unsupported_claim | 0.972 | - | 72 |

## Custo por julgamento

Custo gravado em cada julgamento (`run_evaluations.cost_usd`; um julgamento falho custa o que foi reservado ou cobrado).

| Juiz | Julgamentos | Falhos | Custo total (US$) | Custo por julgamento (US$) |
| --- | --- | --- | --- | --- |
| O `deepseek/deepseek-flash` judge.v3 | 72 | 0 | 0.023773 | 0.000330 |
| A `deepseek/deepseek-flash` judge.v4 | 72 | 0 | 0.025147 | 0.000349 |
| B `anthropic/claude-opus-5-5` judge.v3 | 72 | 0 | 1.284220 | 0.017836 |
| C `anthropic/claude-opus-5-5` judge.v4 | 72 | 0 | 1.315568 | 0.018272 |

Tokens gravados em cada julgamento (desde a v0.9.0; os anteriores não os guardam), total / média por julgamento. A entrada inclui o cache lido e o criado; a saída inclui o pensamento.

| Juiz | Julgamentos com tokens | Entrada | Cache lido | Cache criado | Saída |
| --- | --- | --- | --- | --- | --- |
| O `deepseek/deepseek-flash` judge.v3 | 0 | - | - | - | - |
| A `deepseek/deepseek-flash` judge.v4 | 72 | 146433 / 2033.8 | 109056 / 1514.7 | 0 / 0.0 | 11066 / 153.7 |
| B `anthropic/claude-opus-5-5` judge.v3 | 72 | 222255 / 3086.9 | 0 / 0.0 | 0 / 0.0 | 19760 / 274.4 |
| C `anthropic/claude-opus-5-5` judge.v4 | 72 | 225927 / 3137.9 | 0 / 0.0 | 0 / 0.0 | 20593 / 286.0 |

## Cobertura da amostra avaliada

Rotas: clarify 1, general_web 4, human_handoff 2, knowledge 6, knowledge_and_support 4, out_of_scope 2, support 5. Splits: dev 11, holdout 13.

## Como ler

- Exata: parte das respostas em que humano e juiz deram a mesma nota. ±1: parte em que a diferença é de até um ponto. Os intervalos de ambas são de Wilson (95%).
- Kappa quadrático ponderado: 1 é concordância perfeita; 0 é o que o acaso daria com as mesmas distribuições de notas; negativo é pior que o acaso. Diferenças maiores pesam mais (peso = quadrado da diferença). O intervalo é por reamostragem (bootstrap) das respostas, com a semente da amostra. Quando quase todas as notas são 4 ou 5, o kappa fica baixo mesmo com concordância exata alta; por isso as três medidas aparecem juntas.
- Viés: média das notas do juiz menos a média das notas humanas; positivo é um juiz mais generoso.
- Amostra: balanceada por estrato (rota e split), não ponderada. Cada estrato entra com quantidades parecidas, mesmo quando é raro na campanha; as médias e as concordâncias valem para estas respostas e não estimam as da campanha inteira.
- Dados: respostas do sistema sobre a conta sintética, mascaradas; o arquivo da amostra não traz nenhuma nota do juiz.
