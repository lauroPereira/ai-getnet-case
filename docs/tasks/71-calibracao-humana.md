# Tarefa: calibração humana do juiz

## Objetivo

Gerar uma amostra de respostas para o responsável avaliar com a mesma rubrica do juiz, sem ver os scores dele, e calcular a concordância humano × juiz por critério.

## Especificação relacionada

[Spec v0.8.0](../specs/orquestracao-avaliacao-v080.md) (rascunho) — D10; [spec 0.2](../specs/evolucao-pos-feedback.md) RF-91, CA-50; [plano](../specs/evolucao-pos-feedback-plano.md) decisão técnica 14.

## Pré-condições

Tarefa 70 com parecer apto (rubrica, migração 0011 e tabela `calibrations`). Mesmo worktree e limites da 70.

## Arquivos prováveis

`evaluation/calibration.py` (novo), `cli.py` (`eval-calibrate`, só por acréscimo), testes, `docs/evidence/` (modelo do relatório).

## Passos

1. `eval-calibrate --sample 24 --from <relatório da campanha>`: amostra estratificada por rota e split, CSV com mensagem, resposta mascarada, evidências resumidas e colunas vazias dos quatro critérios e do veredito, mais um cabeçalho de instruções; nenhum score do juiz no arquivo; semente registrada.
2. `eval-calibrate --import <csv>`: valida o preenchimento (faixa 1–5, booleano), grava em `calibrations` e calcula, por critério, concordância exata, ±1 e kappa ponderado quadrático; relatório em `docs/evidence/v080-calibracao.md`.
3. CSV e relatório só com dados sintéticos.

## Critérios de conclusão

- [ ] CSV gerado sem nenhum score do juiz (teste procura os valores).
- [ ] Kappa e concordâncias conferidos com números fixos em teste, inclusive casos de borda (todos iguais, uma linha).
- [ ] CSV malformado → erro claro com a linha.
- [ ] Suíte estrita com código 0; nenhuma chamada paga.

## Validação

A preencher pelo Developer.

## Status

```text
pendente (aguarda aprovação da spec v0.8.0)
```
