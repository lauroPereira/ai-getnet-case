# Ajuste do `judge.v5` no conjunto de ajuste (v0.11.0)

**Resultado:** nas 24 respostas rotuladas na v0.8.0, o `judge.v5` marcou as 4 frases genéricas sem fonte que o `judge.v3` não marcava, e a concordância do veredito `unsupported_claim` com o rótulo humano subiu de κ −0,200 para 0,750 (0,882 com o rótulo da S04 adjudicado pelo responsável). O prompt foi congelado no blob `5430b33` antes do primeiro julgamento das 36 respostas seladas, medidas em [v0110-calibracao.md](v0110-calibracao.md). Candidato: [v0110-candidato-r3.json](v0110-candidato-r3.json).

## Método

- **Conjunto de ajuste, separado do conjunto de medição.** As 24 respostas de [v080-calibracao-amostra.csv](v080-calibracao-amostra.csv), com as notas humanas da v0.8.0. Nenhuma faz parte das 36 seladas.
- **Critério de parada, escrito antes** ([especificação](../specs/juiz-retrieval-v0110.md), D6(a)): pelo menos 3 das 4 frases genéricas marcadas e no máximo 1 falso positivo, em até três iterações do prompt.
- **Julgamento.** `deepseek/deepseek-flash` lista as afirmações de cada resposta com o prompt `judge_claims.v1` e confere cada uma contra a evidência com o `judge.v5`; o veredito `unsupported_claim` é derivado em código. Comparação com `eval-calibrate --import`, sem chamada a modelo.

## Veredito `unsupported_claim`, juiz × rótulo humano (24 respostas)

| Juiz | Concordância exata | Kappa (IC 95%) | Ambos sim | Só humano | Só juiz | Nenhum |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| `judge.v3` (campanha da v0.8.0) | 0,667 | −0,200 (−0,33 a 0,00) | 0 | 4 | 4 | 16 |
| `judge.v5`, iteração 1 | 0,667 | 0,250 (−0,08 a 0,60) | 3 | 1 | 7 | 13 |
| `judge.v5`, iteração 2 | 0,875 | 0,591 (−0,04 a 1,00) | 3 | 1 | 2 | 18 |
| `judge.v5`, iteração 3 | 0,917 | 0,750 (0,31 a 1,00) | 4 | 0 | 2 | 18 |

Na adjudicação da calibração, o responsável reviu o rótulo da S04 para "sim". Com esse rótulo, a iteração 3 tem 1 falso positivo, concordância exata de 0,958 e κ 0,882, e atende o critério de parada.

## Frases genéricas sem fonte

| Amostra | Caso | Rota | Humano | `judge.v3` | `judge.v5` iteração 1 | iteração 2 | iteração 3 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | PT06 | knowledge | sim | não | sim | sim | sim |
| S13 | PT05 | knowledge_and_support | sim | não | sim | não | sim |
| S16 | EX01 | knowledge | sim | não | sim | sim | sim |
| S21 | PT09 | knowledge | sim | não | não | sim | sim |
| Marcadas | | | 4 de 4 | 0 de 4 | 3 de 4 | 3 de 4 | **4 de 4** |

## Depois do ajuste

O prompt da iteração 3 é o `judge.v5` publicado. A medição que decide a rubrica padrão é a das 36 respostas seladas, que o juiz não viu durante o ajuste: κ 0,647 (IC 95% 0,28 a 0,92), em [v0110-calibracao.md](v0110-calibracao.md). A revisão independente do ajuste está em [v0110-reviewer-v5i3b.md](v0110-reviewer-v5i3b.md).
