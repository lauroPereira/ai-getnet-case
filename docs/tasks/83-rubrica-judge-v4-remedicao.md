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

Developer, 2026-11-05, branch `codex/v0.10.0-rubrica-operacao`, base `0266652` (árvore igual à de `ce011b5`), commits `1655e80` e `9e66d20` ([passagem](../evidence/v0100-developer.md#tarefa-83--rubrica-judgev4-e-remedição-dos-dois-juízes-rodada-1)).

- `judge.v3.md` intocado (SHA-256 igual ao da v0.9.0, conferido em teste). `judge.v4.md` difere só pelo trecho inserido na definição de `unsupported_claim` e pela linha `version: 4`; o diff está na passagem.
- `--rubric v3|v4` (padrão `v3`) em `eval --judge-repeat` (e `eval --judge`) e em `eval-calibrate --import`. Cada julgamento grava `rubric_version` e `evaluator.prompt` da rubrica pedida.
- Relatório multi-bloco: `--judge`, `--judge-run` e `--rubric` repetíveis, pareados pela ordem, com um bloco por (juiz, execução, rubrica) ao lado do original, a tabela das frases genéricas (S01, S13, S16, S21) e a linha informativa da regra D2. Com um juiz sob v3, o relatório da v0.9.0 sai idêntico byte a byte (conferido sobre o mesmo banco com o código de `ce011b5` e o da branch). Ligações inválidas são recusadas sem gravar nada.
- Testes sem rede: 8 novos (`tests/unit/evaluation/test_judge_v4.py`, `tests/integration/test_v0100_rubric.py`); um teste existente ajustado porque o arquivo mais novo agora é o v4 (ver a passagem).
- `python tools/scripts/lint_and_tests.py --strict`: 2115 passed, 1 skipped, ruff limpo, `checar-caminhos-pessoais.py` sem ocorrências em 764 arquivos, exit 0.
- Não verificado aqui: o rejulgamento real (momentos 1 e 2, pagos) e o relatório real do momento 3, que são do QA.

**Rodada 2** (correções da [revisão, rodada 1](../evidence/v0100-reviewer-t83.md)), Developer, 2026-11-05, commit `34d7f6a` ([passagem](../evidence/v0100-developer.md#tarefa-83--rodada-2)).

- P2-1: `eval --rubric` sem padrão próprio no parser (`default=None`); os dois comandos resolvem por `judge.rubric_version` (`--rubric` explícito, senão `judge.RUBRIC_VERSION`, hoje v3), e `calibration._rubric` delega a ela. Teste por `cli.main([...])`: padrão gravado sem `--rubric`, `--judge`/`--judge-run`/`--rubric` repetidos e, com `RUBRIC_VERSION` trocado no teste, os dois comandos seguem o novo padrão.
- P2-2: teste em que o Opus só tem julgamentos v3 e `eval-calibrate --judge anthropic/claude-opus-5-5 --rubric v4` sem `--judge-run` é recusado, sem calibração gravada e sem relatório.
- P3-2: a linha da nota de busca web no relatório do `eval` cita a rubrica usada (`judge.v4` quando for o caso). P3-4: a linha D2 diz qual bloco v3 é a base quando o juiz tem mais de um; `_baseline` tem teste. P3-1: `prompt_versions()` informa a rubrica configurada do juiz (v3), não o arquivo mais novo. P3-3: fechado pela delegação do P2-1.
- Mutantes reaplicados numa cópia: M12, M17, M19, M20, o padrão `"v3"` fixo no parser e o `_rubric` com padrão próprio, todos mortos.
- `python tools/scripts/lint_and_tests.py --strict`: ver a passagem.

## Status

Rodada 2 implementada pelo Developer em 2026-11-05; aguarda a rodada 2 da revisão. Rodada 1 revisada com correções necessárias (P2-1, P2-2). Aberta pelo Supervisor em 2026-11-05.
