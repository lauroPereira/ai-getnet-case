# Tarefa 83 — Rubrica `judge.v4` e remedição dos dois juízes

## Objetivo

Fechar a lacuna que o experimento da v0.9.0 expôs: a rubrica não pede ao juiz que marque frase genérica sem fonte. Criar `judge.v4` com essa única diferença e permitir rejulgar a amostra calibrada sob a v4 com qualquer juiz, comparando v3 × v4 contra as mesmas notas humanas.

## Especificação relacionada

[Rubrica `judge.v4` e operação v0.10.0](../specs/rubrica-operacao-v0100.md): D1, D2, CA-57. Base: `prompts/judge.v3.md`, `evaluation/judge.py` (`RUBRIC`, `RUBRIC_VERSION`, `load_prompt`), `evaluation/calibration.py` (`judgement_for`, `--judge`, `--judge-run`), `cli.py` (`eval --judge-repeat`, `eval-calibrate --import`). [ADR 0021](../architecture/decisions/0021-juiz-modelo-e-regua.md).

## Pré-condições

Branch `codex/v0.10.0-rubrica-operacao` criada da `main` com a v0.9.0. Nenhuma chamada paga.

## Arquivos prováveis

`prompts/judge.v4.md` (novo; `judge.v3.md` não muda), `evaluation/judge.py` (rubrica selecionável; `JudgeScoreV3` reaproveitado: o esquema não muda), `cli.py` (`--rubric v3|v4` em `eval --judge-repeat` e em `eval-calibrate --import`), `evaluation/calibration.py` (ligação por rubrica; relatório com blocos por juiz × rubrica), `config.py` só por acréscimo se houver setting, testes em `tests/unit/evaluation/` e `tests/integration/`.

## Passos

1. **Prompt.** `prompts/judge.v4.md` = v3 com a definição de `unsupported_claim` estendida: "…or a general claim stated as fact with no source in the evidence (for example 'rates vary by contract' or 'approval depends on analysis' when no passage says so)". Nada mais muda. Registre o diff na passagem.
2. **Seleção da rubrica.** `eval --judge-repeat ... --rubric v3|v4` (padrão `v3`) carrega `judge.<v>.md`; cada julgamento grava `rubric_version` (já existe) com o valor certo; o nome da execução continua obrigatório para o `--judge-run`.
3. **Comparação.** `eval-calibrate --import <csv> --rater lauro --judge <par> --judge-run <nome> --rubric v4 --campaign <novo> --out <md>`: liga as notas humanas aos julgamentos do juiz pedido **sob a rubrica pedida**; o relatório traz quatro blocos quando existirem no banco: juiz original v3 (ligação de `calibrations.evaluation_id`), juiz pedido v3 (se houver execução v3 do mesmo juiz: para o Opus, `v090-juiz-opus-r3`), juiz pedido v4 e, se `--also-judge <par> --also-run <nome>` for passado, o segundo juiz sob v4. Simplifique se preferir: o relatório aceita uma lista de pares `(juiz, execução, rubrica)` e renderiza um bloco por par mais o original; a tabela de frases genéricas (S01, S13, S16, S21) mostra o veredito de cada bloco.
4. **Regra D2 da v0.10.0** no relatório como linha informativa: condição do veredito e ±1 com tolerância 0,05, calculada, sem decidir.
5. **Testes sem rede:** provedor programado; v4 carregada e gravada com `rubric_version` certo; v3 continua byte a byte igual (relatório da v0.9.0 regenerado idêntico); comparação com quatro blocos; CSV e ligações inválidas recusadas como na v0.9.0.

## Critérios de conclusão

- `judge.v3.md` intocado; `judge.v4.md` difere em uma frase.
- `--rubric` nos dois comandos; relatório multi-bloco com a tabela de frases genéricas e a linha da regra.
- Suíte estrita verde; `checar-caminhos-pessoais.py` limpo.

## Validação

(Preenchida pelo Developer.)

## Status

Pendente. Aberta pelo Supervisor em 2026-11-05.
