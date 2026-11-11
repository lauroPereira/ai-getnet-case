# Tarefa 86 — Fechamento da v0.10.0

## Objetivo

Fixar o candidato, submetê-lo a revisão independente e à validação com modelos reais (remedição dos juízes sob a v4; comparação interrompida e retomada; `/metrics` ao vivo), decidir o padrão da rubrica pela regra D2 e fechar README, CHANGELOG e ADR 0022 antes de 2026-11-06 às 08h.

## Especificação relacionada

[Rubrica `judge.v4` e operação v0.10.0](../specs/rubrica-operacao-v0100.md). História: [rubrica-operacao-v0100.md](../historias/rubrica-operacao-v0100.md).

## Pré-condições

Tarefas 83 a 85 implementadas e revisadas (a 83 pode ser validada antes da 84 e da 85, momentos 1 a 3). Teto desta versão: US$0,25.

## Passos

1. Suíte estrita; manifesto `docs/evidence/v0100-candidato-rN.json`.
2. Revisão independente do candidato; correções nas próprias tarefas.
3. Validação com modelos reais, momentos 1 a 3 (rejulgamento v4 com DeepSeek e Opus; relatório v3 × v4); decisão D2; se a v4 vira padrão, mudança de `RUBRIC_VERSION` com suíte focada.
4. Validação operacional, momentos 4 a 7 (comparação interrompida por reinício real e retomada; `/metrics`; regras), seed ressemeada se após a meia-noite.
5. ADR 0022 (rubrica v4 e operação retomável/métricas); README (tabela por área: linhas Memory, Observability, Production e Evaluation; Observability; Limitations; Next steps); CHANGELOG 0.10.0; história; integração na `main` e tag `v0.10.0`.

## Critérios de conclusão

- CA-57 a CA-59 com prova real, ou a parte não medida declarada como não medida.
- README e CHANGELOG coerentes; nenhum caminho pessoal; CI verde na `main`.

## Resultado

Candidato r1 fixado ([manifesto](../evidence/v0100-candidato-r1.json)); juiz e operação validados com modelos reais; D2 decidida pela regra escrita antes da medição (`judge.v3` continua o padrão).
ADR 0022 aceita; CHANGELOG 0.10.0, README, contrato e história atualizados; versão 0.10.0 no pacote com a suíte estrita completa.
Evidência: [`judge.v4` contra a calibração humana](../evidence/v0100-juiz-v4.md) e [validação operacional](../evidence/v0100-qa-ops-r1.md).

## Status

```text
concluída (v0.10.0)
```
