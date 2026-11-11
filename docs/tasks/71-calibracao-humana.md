# Tarefa: calibração humana do juiz

## Objetivo

Gerar uma amostra de respostas para o responsável avaliar com a mesma rubrica do juiz, sem ver os scores dele, e calcular a concordância humano × juiz por critério.

## Especificação relacionada

[Spec v0.8.0](../specs/orquestracao-avaliacao-v080.md) — D10; [spec 0.2](../specs/evolucao-producao-v070-v0100.md) RF-91, CA-50; [plano](../specs/evolucao-producao-v070-v0100-plano.md) decisão técnica 14.

## Pré-condições

Tarefa 70 com revisão apta (rubrica, migração 0011 e tabela `calibrations`). Mesmos limites da 70.

## Arquivos prováveis

`evaluation/calibration.py` (novo), `cli.py` (`eval-calibrate`, só por acréscimo), testes, `docs/evidence/` (modelo do relatório).

## Passos

1. `eval-calibrate --sample 24 --from <relatório da campanha>`: amostra estratificada por rota e split, CSV com mensagem, resposta mascarada, evidências resumidas e colunas vazias dos quatro critérios e do veredito, mais um cabeçalho de instruções; nenhum score do juiz no arquivo; semente registrada.
2. `eval-calibrate --import <csv>`: valida o preenchimento (faixa 1–5, booleano), grava em `calibrations` e calcula, por critério, concordância exata, ±1 e kappa ponderado quadrático; relatório em `docs/evidence/v080-calibracao.md`.
3. CSV e relatório só com dados sintéticos.

## Critérios de conclusão

- [x] CSV gerado sem nenhum score do juiz (teste procura os valores).
- [x] Kappa e concordâncias conferidos com números fixos em teste, inclusive casos de borda (todos iguais, uma linha).
- [x] CSV malformado → erro claro com a linha.
- [x] Suíte estrita com código 0; nenhuma chamada paga.

## Resultado

`eval-calibrate --sample` gera CSV balanceado por rota e split, sem nenhum score do juiz; `--import` valida, grava e calcula concordância exata, ±1 e kappa ponderado com intervalos de 95%. Testes: `test_calibration` (72) e o fluxo (7), com os mutantes do módulo e da CLI mortos. Calibração de 24 respostas importada: [relatório](../evidence/v080-calibracao.md).

## Status

```text
concluída (v0.8.0)
```
