# Tarefa 75 — Equivalências de redação em `PRICE-INSUFFICIENT` (v0.8.0)

## Objetivo

Fazer a medição de CA-51 aceitar as respostas corretas sobre falta de evidência de taxa nas jornadas `V030-PRICE-INSUFFICIENT` e `V030-PT-PRICE-INSUFFICIENT`, sem aceitar contradições.

## Especificação relacionada

[Orquestração e avaliação v0.8.0](../specs/orquestracao-avaliacao-v080.md), CA-51 e D15.

## Pré-condições

Campanha `v080-qa`, ambiente válido para estes dois IDs: a pergunta usa a venda mais recente, não "ontem".

## Contexto

- **Feito:** o lojista perguntou "Is there insufficient evidence for a 2-installment credit fee?" e "Há evidência insuficiente para comparar a taxa de crédito em duas parcelas?", três vezes cada.
- **Esperado:** resposta que diga que não há regra aplicável nem cobrança registrada para comparar, aprovada pela rubrica.
- **Observado:** as respostas dizem isso, e o juiz independente deu 5 ou 4 em todos os critérios, sem afirmação sem suporte; `content_ok` recusou 2 de 3 execuções de cada idioma:
  - `req_evalbccfe360ff22` (EN, rep. 1): "no fee rule or recorded charge was available to compare".
  - `req_evaldf38c4d80b5e` (EN, rep. 2): "the available data isn't enough to confirm either the expected fee or the fee charged … no pricing-rule details or recorded charge to compare".
  - `req_evale8ee4429374a` (PT, rep. 2): "Não há uma taxa esperada disponível na regra de preços nem uma taxa registrada para comparação".
  - `req_eval51b2a1d763e0` (PT, rep. 3): "não havia uma regra de preço aplicável nem uma cobrança registrada para comparação".

## Arquivos prováveis

`tests/scenarios/business_journeys.jsonl` (rótulos dev) e o catálogo espelhado, com teste de contradição. Não tocar no holdout.

## Critérios de conclusão

- As quatro respostas acima passam `content_ok` na reavaliação offline das respostas arquivadas.
- As contradições (dizer que a taxa está correta ou incorreta) continuam recusadas.

## Resultado

O cotejo do runner passou a tratar apóstrofo tipográfico, travessão e ressalvas adjacentes, e os rótulos ganharam as formas das respostas reais e as contradições de taxa. As quatro respostas passam; 165 testes de formas aceitas e recusadas; a re-pontuação de 195 respostas arquivadas (1.755 checagens) não muda nenhuma. Evidência: [validação pré-holdout](../evidence/v080-d12-pre-holdout-r6.md).

## Status

```text
concluída (v0.8.0)
```
