# Tarefa 86 — Fechamento da v0.10.0

## Objetivo

Fixar o candidato, revisar, rodar o QA real (remedição dos juízes sob a v4; comparação interrompida e retomada; `/metrics` ao vivo), decidir o padrão da rubrica pela regra D2 e fechar README, CHANGELOG e ADR 0022 antes de 2026-11-06 às 08h.

## Especificação relacionada

[Rubrica `judge.v4` e operação v0.10.0](../specs/rubrica-operacao-v0100.md). História: [rubrica-operacao-v0100.md](../historias/rubrica-operacao-v0100.md).

## Pré-condições

Tarefas 83 a 85 com parecer apto (83 pode ir ao QA antes de 84 e 85, momentos 1 a 3). Cap Anthropic restante US$2,52; teto desta versão no projeto US$0,25.

## Passos

1. Suíte estrita; manifesto `docs/evidence/v0100-candidato-rN.json`.
2. Revisão independente em contexto frio; correções como rodadas.
3. QA momentos 1 a 3 (rejulgamento v4 com DeepSeek e Opus; relatório v3 × v4); decisão D2 pelo Supervisor; se a v4 vira padrão, mudança de `RUBRIC_VERSION` com suíte focada.
4. QA momentos 4 a 7 (comparação interrompida por reinício real e retomada; `/metrics`; regras), seed ressemeada se após a meia-noite.
5. ADR 0022 (rubrica v4 e operação retomável/métricas); README (resposta ao feedback: linhas Memory, Observability, Production e Evaluation; Observability; Limitations; Next steps); CHANGELOG 0.10.0; história; relatório do Supervisor; merge local na `main`; push e tag `v0.10.0` pelo responsável.

## Critérios de conclusão

- CA-57 a CA-59 com prova real, ou a parte não medida declarada como não medida.
- README e CHANGELOG coerentes; nenhum caminho pessoal; CI verde na `main`.

## Validação

(Preenchida pelo Supervisor.)

## Status

Pendente. Aberta pelo Supervisor em 2026-11-05.
