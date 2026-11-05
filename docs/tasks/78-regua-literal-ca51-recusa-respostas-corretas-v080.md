# Tarefa 78 — Régua literal do CA-51 recusa respostas corretas em seis jornadas (v0.8.0)

## Objetivo

Fazer a medição de CA-51 reconhecer as respostas corretas das jornadas de preço e de cancelamento, que hoje falham só em `content_ok` por redação, sem passar a aceitar contradições.

## Especificação relacionada

[Orquestração e avaliação v0.8.0](../specs/orquestracao-avaliacao-v080.md), CA-51 e D15. Parecer: [v080-d12-pre-holdout-r5.md](../evidence/v080-d12-pre-holdout-r5.md). Mesma classe da [tarefa 75](75-rotulo-literal-price-insufficient-v080.md), agora em mais jornadas.

## Pré-condições

Candidato r7 `658c70adc69cb956c931737b8a1caf38ed638dd5`, campanha `v080-qa`, runtime de QA ressemeado em 05/11 (vendas de "ontem" em 04/11), mock de preços saudável. Ambiente válido em todas as execuções abaixo.

## O que foi feito, o esperado e o observado

- **Feito:** o lojista fez as 11 perguntas das jornadas reexecutadas, três vezes cada (QA r5, bloco `healthy`).
- **Esperado:** resposta correta aprovada pela rubrica em pelo menos 12 de 13 jornadas, em cada repetição.
- **Observado:** rota, status, ferramentas, valores, afirmações proibidas, fontes e fundamentação passam em 13/13 nas três repetições. Só `content_ok` falha, em 10 respostas, e em todas elas a proposição esperada aparece com outra redação. O juiz independente deu 5 em todos os critérios (usefulness 4 em uma) e não marcou nenhuma afirmação sem suporte. CA-51 composto: **11/13, 8/13 e 10/13**.

| Jornada | Rep. | `request_id` | O que a resposta diz | Por que o rótulo recusa |
|---|---:|---|---|---|
| `V030-PRICE-DIVERGENCE` | 1 | `req_eval531ac9146987` | "found a difference in yesterday’s Pix charge… expected fee R$ 0,00, recorded R$ 0,75" | nenhum dos termos aceitos ("divergence", "fee difference", "found a discrepancy"…) |
| `V030-PRICE-DIVERGENCE` | 2 | `req_evalb84c1106aea3` | "the pricing rule shows a fee of R$ 0,00, but the recorded charge is R$ 0,75… requires human review" | idem |
| `V030-PRICE-DIVERGENCE` | 3 | `req_eval9a0b07470114` | "shows a difference… I’ve escalated the discrepancy" | idem |
| `V030-PRICE-CONDITIONS` | 2 | `req_eval64b06f9b7f24` | "the charge and expected conditions used different pricing plans" | não casa "plans differed", "plans were different"… |
| `V030-PT-PRICE-CONDITIONS` | 2 | `req_eval45e5804e758a` | "regra… plano demo_standard, mas a cobrança… plano demo_legacy… Essa diferença entre as condições" | não casa "condições diferentes", "planos distintos"… |
| `V030-PRICE-INSUFFICIENT` | 2 | `req_eval3180af09b4e0` | "no expected fee or recorded charge was available" | não casa "no recorded charge", "no expected pricing fee or recorded charge"… |
| `V030-PRICE-INSUFFICIENT` | 3 | `req_evalb8354030edbd` | "there was no expected fee or recorded charge to compare" | idem |
| `V030-PT-PRICE-INSUFFICIENT` | 1 | `req_evalaf77a604682c` | "Não havia uma taxa esperada calculável nem uma cobrança registrada para comparação" | não casa as formas aceitas |
| `V030-PT-PRICE-INSUFFICIENT` | 3 | `req_eval025b4ed82d6f` | "não há evidências suficientes para comparar a taxa" | o rótulo tem só o singular "não há evidência suficiente para comparar" |
| `V030-SALE-CANCELLATION` | 2 | `req_eval932e426373de` | "Your request to cancel yesterday’s sale has been received, but the cancellation has not been processed yet." | o rótulo exige a palavra literal "requested" |

- **Critério violado:** CA-51 (≥ 12/13 em cada repetição). As mesmas jornadas oscilaram também na r3 (9, 11 e 10 de 13) e na r4, sempre em `content_ok`: cada execução real produz uma redação nova, e a lista literal só cobre as que já foram vistas.

## Pergunta de produto associada (para o Supervisor)

O QA mediu CA-51 pela checagem determinística `passed`, como na r3 e na r4. Na mesma composição, a rubrica `judge.v3` (todos os critérios ≥ 4 e sem `unsupported_claim`) dá 13/13 nas três repetições, e as checagens sem `content_ok` também dão 13/13. Cabe ao Supervisor ou ao responsável decidir qual rubrica mede CA-51. Se for a determinística, a correção é de rótulo ou de cotejo (D15, com justificativa por caso). Se passar a ser o juiz, ou uma combinação dos dois, a decisão é de critério. O QA não muda rótulo, rubrica nem critério.

## Decisão do Supervisor (2026-11-05, 04h30)

Nesta versão, CA-51 continua medido pela checagem determinística `passed` (inclusive `content_ok`), como nas rodadas r3, r4 e r5: trocar a régua para o juiz ou para uma combinação é redução de critério de aceite, reservada ao responsável pelo plano. A correção segue a D15: o rótulo muda só onde a resposta real está correta, com justificativa por caso, sem aceitar contradições. Prova offline obrigatória nas respostas arquivadas (`v080-healthy-r5.json`, `v080-healthy-r4.json`, `v080-all-r3.json`) com o cotejo real do runner; depois, reteste pago só das seis jornadas afetadas, três repetições, no mesmo dia da seed.

Orientação: preferir formas semanticamente equivalentes e específicas (plural/singular, sinônimos de divergência e de planos diferentes, "received, not processed yet" para o cancelamento) a padrões genéricos; manter e, se preciso, ampliar `must_not_include`/`must_not_assert` com as contradições listadas nos critérios de conclusão. Nenhuma alteração em `runner.py` nesta tarefa, salvo necessidade demonstrada.

**Pendente do responsável (não bloqueia a v0.8.0):** se, a partir da v0.9.0, CA-51 e equivalentes passam a ser medidos pelo `judge.v3` (critérios ≥ 4 e sem `unsupported_claim`), pela checagem determinística, ou pela combinação. O relatório da versão traz os dois números de cada repetição.

## Arquivos prováveis

Rótulos dev em `tests/scenarios/business_journeys.jsonl` e, se a decisão for de cotejo, `src/merchant_assistant/evaluation/runner.py`. Não tocar no holdout.

## Critérios de conclusão

- As 10 respostas acima passam na reavaliação offline das respostas arquivadas (`v080-healthy-r5.json`), e as respostas da r3 e da r4 que passavam continuam passando.
- Contradições continuam recusadas (dizer que não há divergência, que as condições são as mesmas, que a taxa está correta ou incorreta, que o cancelamento foi concluído).
- Decisão registrada sobre a rubrica do CA-51, se o Supervisor a tomar.

## Validação

Developer, rodada 1 (2026-11-05), passagem em [v080-developer.md](../evidence/v080-developer.md#tarefa-78-rodada-1-régua-literal-do-ca-51). Mudaram só os rótulos das seis jornadas em `tests/scenarios/business_journeys.jsonl`, com justificativa por caso. `runner.py` e o catálogo ficaram como estavam: nenhum `source_case` espelha essas jornadas.

- Prova offline com `runner._checks` real, em `tests/unit/evaluation/test_t78_ca51_archived.py` (166 testes):
  - As 10 respostas passam em todas as checagens.
  - Comparei 111 respostas arquivadas das 13 jornadas (r3, r4 e r5), 999 checagens. Mudaram 13: as 10 falsas recusas e 3 `forbidden_ok` em respostas da r4 que já reprovavam.
  - Nenhuma aprovada passou a reprovar: eram 76 e agora são 86.
  - 53 contradições, em EN e PT, foram recusadas, e outras 10 sondas que negam as formas novas também.
- CA-51 recalculado na composição da r5: 13/13, 13/13 e 13/13.
- Suíte estrita: 1545 passed (1.379 + 166), Ruff e skills ok, exit 0.
- Pendente: revisão e reteste pago das seis jornadas pelo QA.

## Status

Aberta pelo QA (r5), 2026-11-05. Implementada pelo Developer (rodada 1), 2026-11-05; aguarda revisão.
