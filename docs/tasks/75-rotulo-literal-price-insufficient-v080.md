# Tarefa 75 — Rótulo literal recusa resposta correta em `PRICE-INSUFFICIENT` (v0.8.0)

## Objetivo

Fazer a medição de CA-51 aceitar as respostas corretas sobre falta de evidência de taxa nas jornadas `V030-PRICE-INSUFFICIENT` e `V030-PT-PRICE-INSUFFICIENT`, sem aceitar contradições.

## Especificação relacionada

[Orquestração e avaliação v0.8.0](../specs/orquestracao-avaliacao-v080.md), CA-51 e D15. Parecer: [v080-d12-pre-holdout-r4.md](../evidence/v080-d12-pre-holdout-r4.md).

## Pré-condições

Candidato `4c3c8a98ddfc4f7af7bba877177f3479152159b5`, campanha `v080-qa`, ambiente válido para estes dois IDs: a pergunta usa a venda mais recente, não "ontem".

## O que foi feito, o esperado e o observado

- **Feito:** o lojista perguntou "Is there insufficient evidence for a 2-installment credit fee?" e "Há evidência insuficiente para comparar a taxa de crédito em duas parcelas?", três vezes cada.
- **Esperado:** resposta que diga que não há regra aplicável nem cobrança registrada para comparar, aprovada pela rubrica.
- **Observado:** as respostas dizem isso, e o juiz independente deu 5 ou 4 em todos os critérios, sem afirmação sem suporte. Mesmo assim, `content_ok` falhou em 2 de 3 execuções de cada idioma:
  - `req_evalbccfe360ff22` (EN, rep. 1): "no fee rule or recorded charge was available to compare".
  - `req_evaldf38c4d80b5e` (EN, rep. 2): "the available data isn't enough to confirm either the expected fee or the fee charged … no pricing-rule details or recorded charge to compare".
  - `req_evale8ee4429374a` (PT, rep. 2): "Não há uma taxa esperada disponível na regra de preços nem uma taxa registrada para comparação".
  - `req_eval51b2a1d763e0` (PT, rep. 3): "não havia uma regra de preço aplicável nem uma cobrança registrada para comparação".
- **Critério violado:** CA-51. Essas falhas levam as repetições 1 e 2 a no máximo 11/13.

## Arquivos prováveis

`tests/scenarios/business_journeys.jsonl` (rótulos dev) e o catálogo espelhado, com teste de contradição. Não tocar no holdout.

## Critérios de conclusão

- As quatro respostas acima passam `content_ok` na reavaliação offline das respostas arquivadas.
- As contradições (dizer que a taxa está correta ou incorreta) continuam recusadas.

## Validação

Developer (2026-11-05), branch `codex/v0.8.0-replan`:

- Rótulos dev em `tests/scenarios/business_journeys.jsonl`: `must_include_any` ganhou duas formas por idioma, tiradas das respostas reais (`no fee rule or recorded charge`, `no pricing-rule details or recorded charge`; `não há uma taxa esperada disponível`, `não havia uma regra de preço aplicável`). `must_not_assert` ganhou as contradições de taxa correta, incorreta, confirmada e divergente nos dois idiomas. O catálogo da bancada não espelha estes dois IDs (nenhum `source_case` aponta para eles), então não muda.
- Reavaliação offline pela função `_checks` do runner (`tests/unit/evaluation/test_t75_price_insufficient_archived.py`, 54 testes): as quatro `request_id` passam em todas as checagens determinísticas; as 12 respostas arquivadas da r3 e da r4 destes IDs continuam passando; 51 controles negativos são recusados (17 contradições sozinhas e 34 anexadas a uma das quatro respostas aceitas).
- Testes focados (rótulos, runner, jornadas, catálogo da v0.7.0): 224 passed. Suíte estrita no `HEAD` `94bf7b3`: 1247 passed, ruff e skills ok, exit 0 ([passagem](../evidence/v080-developer.md)).
- Pendente: revisão independente e QA (campanha real).

## Status

implementada; aguarda revisão
