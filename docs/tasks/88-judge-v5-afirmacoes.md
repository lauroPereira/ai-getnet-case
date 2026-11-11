# Tarefa 88 — `judge_claims.v1` e `judge.v5`: juiz por afirmação

## Objetivo

Trocar o veredito de uma vez só por um julgamento afirmação por afirmação: o juiz lista as afirmações da resposta, verifica cada uma contra a evidência, e `unsupported_claim` é calculado em código a partir da lista.

## Especificação relacionada

[Juiz por afirmação, evidência da web e retrieval — v0.11.0](../specs/juiz-retrieval-v0110.md): D3, CA-61. Plano do ciclo: [decisão 3](../specs/roadmap-v0110-v100-plano.md#decisões-técnicas). Base: `evaluation/judge.py` (`RUBRIC_VERSIONS`, `rubric_version`, `JudgeScoreV3`, `judge_spec_v3`, `Judge`), `prompts/judge.v4.md` (ponto de partida do texto), `evaluation/runner.py` e `aggregate.py` (agregação do veredito), `cli.py` (`--rubric`), `data/migrations.py`.

## Pré-condições

O juiz recebe os itens de evidência da tarefa 87 por `judge_input`; `judge.v3` e `judge.v4` permanecem selecionáveis para compatibilidade.

## Arquivos prováveis

`prompts/judge_claims.v1.md` (novo), `prompts/judge.v5.md` (novo; v3 e v4 intocados), `evaluation/judge.py` (duas etapas quando `--rubric v5`; esquemas `ClaimList` e `JudgeScoreV5`; cálculo do veredito), `evaluation/runner.py`, `evaluation/aggregate.py` (agregação inalterada: o veredito continua booleano), `data/migrations.py` (0013 parcial: `run_evaluations.claims` JSON; reversível), `llm/scripted.py` (julgamento programado em duas etapas), `cli.py` (`v5` aceito em `--rubric`), testes.

## Passos

1. **`judge_claims.v1`.** Entrada: mensagem do lojista, rota, status, resposta. Saída estruturada: `claims: [{n, text, kind}]`, `kind ∈ {fact, value, date, status, promise, guidance, standard}`; `standard` para frases padrão de encaminhamento, protocolo, pedido de esclarecimento e cortesia. Frases compostas viram várias afirmações. Sem evidência na entrada: a etapa 1 não julga, só lista.
2. **`judge.v5`.** Entrada: o mesmo `judge_input` de hoje mais `claims`. Saída: os quatro critérios de 1 a 5 com motivo (como v3) e `claim_verdicts: [{n, verdict, support}]`, `verdict ∈ {supported, partial, generic, not_found}`, `support` = trecho da evidência (≤ 200 caracteres) ou vazio. Texto do prompt: a partir da v4, com as regras dos itens `web_page` e `web_summary` da tarefa 87 (página é evidência; resumo da busca não prova fato) e a definição de `generic` (orientação ou generalização dita como fato sem trecho que a sustente). Sem `unsupported_claim` na saída do modelo.
3. **Veredito em código.** `unsupported_claim = any(v.verdict in {generic, not_found} for claims with kind != standard)`; `partial` não marca. Gravar `claims` e `claim_verdicts` em `run_evaluations.claims` (migração 0013, reversível, testada nos dois sentidos) e os dois `prompt` refs no registro do julgamento. Tokens das duas chamadas somados no custo do julgamento.
4. **Seleção.** `RUBRIC_VERSIONS = ("3", "4", "5")`; `judge.v5` é a rubrica padrão após a regra D6; `judge.v3` e `judge.v4` seguem disponíveis com `--rubric v3|v4`. A v5 pode ser escolhida explicitamente em `eval`, `eval --judge-repeat` e `eval-calibrate --import`. A lista de afirmações usa limite de saída próprio. Número desconhecido, ausente ou repetido invalida o julgamento; o código não completa itens faltantes.
5. **Programado.** `llm/scripted.py` responde às duas etapas de forma determinística a partir da resposta (uma afirmação por frase; `not_found` quando o número não aparece na evidência) para a suíte cobrir o fluxo inteiro.
6. **Testes:** esquema das duas saídas; veredito calculado em todos os casos (`standard` ignorado, `partial` não marca); v3 e v4 byte a byte iguais (hash); migração nos dois sentidos; `eval --rubric v5` com modelo programado gera relatório com a mesma agregação; relatório do `eval` mostra, por resposta, a contagem de afirmações por veredito.

## Critérios de conclusão

- Dois prompts novos, dois esquemas, veredito em código, `claims` persistido.
- `judge.v5` é padrão; `--rubric v3` e `--rubric v4` preservam a seleção explícita das versões anteriores.
- Testes offline cobrem os esquemas, cálculo do veredito, migração e compatibilidade de v3/v4.

## Resultado

`judge_claims.v1` e `judge.v5` julgam afirmação por afirmação, com o veredito calculado em código. `judge.v5` atingiu κ 0,647 (IC 95% 0,28 a 0,92) em 36 respostas seladas, pela regra escrita antes da medição, e é a rubrica padrão.
Evidência: [resultado da v0.11.0](../evidence/v0110-resultado.md) e [ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md).

## Status

```text
concluída (v0.11.0)
```
