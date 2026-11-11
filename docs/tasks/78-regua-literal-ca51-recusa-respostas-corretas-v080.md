# Tarefa 78 — Equivalências de redação do CA-51 em seis jornadas (v0.8.0)

## Objetivo

Fazer a medição de CA-51 reconhecer as respostas corretas das jornadas de preço e de cancelamento, que hoje falham só em `content_ok` por redação, sem passar a aceitar contradições.

## Especificação relacionada

[Orquestração e avaliação v0.8.0](../specs/orquestracao-avaliacao-v080.md), CA-51 e D15. Mesma classe da [tarefa 75](75-rotulo-literal-price-insufficient-v080.md), agora em mais jornadas.

## Pré-condições

Campanha `v080-qa`, runtime ressemeado em 05/11 (vendas de "ontem" em 04/11), mock de preços saudável. Ambiente válido em todas as execuções abaixo.

## Contexto

- **Feito:** o lojista fez as 11 perguntas das jornadas reexecutadas, três vezes cada (bloco `healthy`).
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

## Decisão (2026-11-05)

Nesta versão, CA-51 continua medido pela checagem determinística `passed` (inclusive `content_ok`): trocar a régua para o juiz ou para uma combinação é mudança de critério de aceite, reservada ao responsável pelo plano. A correção segue a D15: o rótulo muda só onde a resposta real está correta, com justificativa por caso, sem aceitar contradições. Prova offline obrigatória nas respostas arquivadas (`v080-healthy-r5.json`, `v080-healthy-r4.json`, `v080-all-r3.json`) com o cotejo real do runner; depois, reteste pago só das seis jornadas afetadas, três repetições, no mesmo dia da seed.

Orientação: preferir formas semanticamente equivalentes e específicas (plural/singular, sinônimos de divergência e de planos diferentes, "received, not processed yet" para o cancelamento) a padrões genéricos; manter e, se preciso, ampliar `must_not_include`/`must_not_assert` com as contradições listadas nos critérios de conclusão. Nenhuma alteração em `runner.py` nesta tarefa, salvo necessidade demonstrada.

O critério "sem aceitar contradições" vale para a lista registrada na [revisão independente](../evidence/v080-reviewer-t78.md) e no teste da tarefa; para paráfrases erradas fora da lista, o juiz independente é o controle adicional.

## Arquivos prováveis

Rótulos dev em `tests/scenarios/business_journeys.jsonl` e, se a decisão for de cotejo, `src/merchant_assistant/evaluation/runner.py`. Não tocar no holdout.

## Critérios de conclusão

- As 10 respostas acima passam na reavaliação offline das respostas arquivadas (`v080-healthy-r5.json`), e as respostas da r3 e da r4 que passavam continuam passando.
- Contradições continuam recusadas (dizer que não há divergência, que as condições são as mesmas, que a taxa está correta ou incorreta, que o cancelamento foi concluído).
- Decisão registrada sobre a rubrica do CA-51.

## Resultado

Rótulos das seis jornadas com formas equivalentes presas ao caso e proibições para cada contradição registrada; `runner.py` e catálogo inalterados. Prova offline com 618 casos de teste: as 999 checagens das respostas arquivadas não mudam indevidamente, e CA-51 recalculado dá 13/13 nas três repetições. Suíte estrita: 1.997 testes. Evidência: [validação pré-holdout](../evidence/v080-d12-pre-holdout-r6.md).

## Status

```text
concluída (v0.8.0)
```
