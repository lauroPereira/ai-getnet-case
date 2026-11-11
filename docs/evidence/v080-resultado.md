# Resultado da v0.8.0

Replanejamento, juiz independente e calibração humana. Spec: [orquestracao-avaliacao-v080.md](../specs/orquestracao-avaliacao-v080.md); história: [orquestracao-avaliacao-v080.md](../historias/orquestracao-avaliacao-v080.md); [ADR 0019](../architecture/decisions/0019-replanejamento.md).

## Capacidades

- Um nó `replan`, depois de Knowledge, Web e Support, decide o passo seguinte: terminar, chamar outro especialista, encaminhar ou pedir esclarecimento. Casos claros são decididos por regras nomeadas; o modelo decide só quando nenhuma regra se aplica ou duas discordam. Cada especialista roda no máximo uma vez por pedido, o plano muda no máximo 3 vezes (`MAX_PLAN_HOPS`), e cada decisão fica no trace com a origem (`rule:<nome>` ou `model`).
- Um juiz de outro provedor (`deepseek/deepseek-flash`, rubrica `judge.v3`) dá notas de 1 a 5 em fundamentação, correção factual, relevância e utilidade e o veredito de afirmação sem suporte, contra a evidência mascarada da resposta. A campanha recusa, antes de qualquer chamada, um juiz igual ao agente.
- `eval --repeat N` mede a variação do assistente e `eval --judge-repeat N` a do juiz, sem misturar as duas.
- `eval-calibrate` sorteia uma amostra estratificada para rotulagem humana, sem as notas do juiz, e mede a concordância por critério.
- Cada chamada paga de uma campanha é reservada num ledger de campanha com teto fixo; `eval-estimate` projeta o custo a partir de uma amostra real medida.
- O split selado `holdout_v080` (25 casos novos) e quatro cenários de replanejamento entram no catálogo, conferidos por hash na suíte.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte estrita | 1.997 testes aprovados, Ruff e skills limpos, no candidato `1baa7b31` ([manifesto r11](v080-candidato-r11.json)) |
| Replanejamento (CA-49) | 4 de 4 cenários, 3 de 3 execuções em cada; toda decisão com origem; no máximo 2 saltos ([validação pré-holdout](v080-d12-pre-holdout-r6.md)) |
| Jornadas de negócio (CA-51) | 13/13, 12/13 e 12/13 pela régua literal (portão 12/13) e 13/13 pelo juiz nas três execuções ([validação pré-holdout](v080-d12-pre-holdout-r6.md)) |
| Campanha de desenvolvimento | 44 casos, 3 execuções: 132 respostas, 0,856 aprovadas; médias do juiz 4,56 / 4,62 / 4,77 / 4,53; p50 de 7,4 s; US$0,0024 por resposta; conversas de acompanhamento 4 de 4 ([v080-all-r3.md](v080-all-r3.md), [conversas](v080-conversations-r4.md)) |
| Juiz repetido | 132 julgamentos das 44 respostas de desenvolvimento, nenhuma falha; acordo ±1 de 0,985 a 0,992 por critério ([variação do juiz](v080-judge-repeat-r6.md)) |
| Docker | Smoke 10/10; a pergunta mista de conta e procedimento replanejou de Support para Knowledge por `rule:procedure_gap`, visível no trace ([validação pré-holdout](v080-d12-pre-holdout-r6.md)) |
| Holdout `holdout_v080` (25 casos, 3 execuções) | 62 de 75 (0,827) pela régua literal; médias do juiz 4,67 / 4,61 / 4,83 / 4,64. Rodou uma vez, como último passo técnico da versão ([holdout](v080-holdout-r7.md), [relatório](v080-avaliacao-holdout-r7.md)); na v0.11.0 rodou de novo, já marcado como visto, para compor a amostra da calibração ([v0110-qa-holdout-v080.md](v0110-qa-holdout-v080.md)) |
| Calibração humana (24 respostas, `judge.v3`) | Acordo exato de 0,58 a 0,75 e ±1 de 0,83 a 1,00 por critério; o juiz é o avaliador mais rigoroso (viés de −0,17 a −0,42); no veredito, acordo exato 0,667 ([calibração](v080-calibracao.md)). A calibração da v0.11.0, contra rótulos de referência, a substitui ([v0110-calibracao.md](v0110-calibracao.md)) |

## Gasto

| Ledger | US$ |
| --- | ---: |
| Campanha `v080-qa` | 0,84031389 |
| Ledger do volume Docker | 0,02844823 |
| **Total** (teto US$1,40) | **0,86876212** |

Registro dos ledgers: [holdout](v080-holdout-r7.md), seção "Custo e ledgers".

## Decisão

O desenho do replanejamento, com regras nomeadas antes do modelo e limite de saltos em código, está na [ADR 0019](../architecture/decisions/0019-replanejamento.md). A régua literal das jornadas deu lugar, na v0.11.0, à régua combinada de verificações determinísticas e conteúdo julgado ([v0110-resultado.md](v0110-resultado.md)).
