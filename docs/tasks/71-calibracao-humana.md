# Tarefa: calibração humana do juiz

## Objetivo

Gerar uma amostra de respostas para o responsável avaliar com a mesma rubrica do juiz, sem ver os scores dele, e calcular a concordância humano × juiz por critério.

## Especificação relacionada

[Spec v0.8.0](../specs/orquestracao-avaliacao-v080.md) — D10; [spec 0.2](../specs/evolucao-pos-feedback.md) RF-91, CA-50; [plano](../specs/evolucao-pos-feedback-plano.md) decisão técnica 14.

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

Developer (2026-11-04), worktree do Time B, branch `codex/v0.8.0-avaliacao`, base `3598a48` (a rodada P3 da tarefa 70, commit anterior a este). Passagem em [v080-developer.md](../evidence/v080-developer.md), seção "Tarefa 71" (os P3 da revisão da 70 estão na seção "Tarefa 70, P3 da rodada 2").

- **`eval-calibrate --sample 24 --from <relatório>`:** `evaluation/calibration.py` (novo) e o subcomando em `cli.py` (só acréscimo). Amostra balanceada por (rota, split): uma resposta de cada estrato por vez, em ordem decidida só pela semente (hash, não o gerador do Python), até completar 24; todo estrato aparece antes de algum aparecer duas vezes. Semente padrão `20261104`, `--seed` muda; a semente, a campanha, o relatório de origem, as quantidades e a rubrica vão numa linha `# amostra:` do cabeçalho. CSV em UTF-8 com BOM (a planilha lê os acentos), separador `;` (o Excel pt-BR abre; `--delimiter ,` troca), 10 linhas `#` de instruções em português com a rubrica dos quatro critérios 1-5 e o veredito, e as colunas `sample_id`, `route`, `split`, `status`, `message`, `answer`, `sources`, `evidence`, as seis do avaliador (vazias) e `request_id`, `case_id`. Mensagem e resposta passam de novo por `mask_sensitive`; a evidência é um resumo de 2 000 caracteres; célula que começaria com `=`, `+`, `-` ou `@` ganha um espaço.
- **Sem nenhum score do juiz:** o gerador só lê `judge_input` (a mesma entrada do juiz) e os rótulos da linha; nunca o registro `judge`. O teste monta um relatório cujo juiz tem notas distintas (2, 3, 1, 4), justificativas, `evaluation_id`, modelo e provedor com marcas inconfundíveis e procura cada valor, em JSON, `chave=valor`, `chave: valor` e `chave;valor`, além de conferir que as colunas do avaliador estão vazias e que o cabeçalho é exatamente o esperado. Três mutantes que passam o juiz para a nota livre, para uma coluna do avaliador ou para o `case_id` morrem.
- **`eval-calibrate --import <csv>`:** lê o separador do cabeçalho (`;`, `,` ou tabulação, com ou sem aspas, como a planilha regrava), valida todas as linhas e mostra todos os problemas de uma vez (até 25), cada um com a linha física do arquivo e o `sample_id`: inteiro de 1 a 5, `sim`/`nao` (e variantes), campo vazio em linha meio preenchida, `sample_id` repetido, `request_id` vazio, colunas a mais, cabeçalho sem colunas obrigatórias, arquivo que não está em UTF-8. Linha com os cinco campos vazios é pulada e contada; nota solta não conta. Nada é gravado se uma linha for inválida ou se faltar o julgamento. Grava em `calibrations` (campanha, amostra, avaliador, caso, rota, split, `request_id`, `evaluation_id`, versão da rubrica, notas, veredito, nota livre), ligado ao **primeiro julgamento completo da repetição 1 do principal `cli:eval`** da mesma `request_id`; importar o mesmo arquivo de novo atualiza as linhas (campanha + amostra + avaliador são únicos).
- **Medidas e relatório (`docs/evidence/v080-calibracao.md` ou `--out`):** por critério, concordância exata, ±1 e kappa quadrático ponderado, mais médias e viés (juiz − humano); para o veredito, concordância exata, kappa (com dois valores é o de Cohen) e a tabela 2×2. Intervalos de 95%: Wilson para as proporções e bootstrap com semente para o kappa (D19). Ressalva de amostra pequena no topo, divergências de 2 pontos ou mais (ou veredito oposto) listadas, cobertura por rota e split, e uma seção "Como ler". Casos de borda: uma linha ou duas notas constantes e iguais, kappa "n/d" com a explicação; um lado sem variação, kappa 0 por construção, sem intervalo; notas iguais com variação, kappa 1; discordância total, -1. `docs/evidence/v080-calibracao-modelo.md` mostra o formato com dados inventados (marcado como modelo no topo).
- **Testes (sem chamada paga, sem rede):** `tests/unit/evaluation/test_calibration.py` (57) e `tests/integration/test_calibration_flow.py` (5, sobre uma campanha de 30 casos com o agente e o juiz programados). Kappa e concordâncias com números conferidos à mão no teste (por exemplo, `[1,2,3,4,5]` × `[1,3,3,4,4]`: exata 0,6, ±1 1,0, kappa 0,875 = 1 - 5·2/80; 12 notas: kappa 1 - 60/376 = 0,8404), casos de borda, 400 pares aleatórios contra uma fórmula independente (sem tabela), Wilson (24/24 → 0,862 a 1,0; 12/24 → 0,314 a 0,686). Mutação: 35 mutantes do módulo e 10 da CLI, todos mortos (na primeira passada sobreviveram 4, por teste fraco; reforcei e um deles era intermitente por depender do segundo do relógio, agora com horários fixos no teste).
- **Contagens:** `tests/unit` 368 aprovados em 117 s (eram 304 na rodada 2 da tarefa 70; mais 7 dos P3 e 57 desta tarefa); integração, um pytest por vez: `test_eval_campaign` (22), `test_calibration_flow` (5), `test_evaluation_runner`, `test_evaluator_settings`, `test_v060_api` e `test_v060_r2` em um só grupo de 88 aprovados em 135 s. ruff `check src tests` sem achados. Lacre do holdout `91aa5158…4f1bac` inalterado (`sha256sum` e `test_holdout_v080.py` verdes; o conteúdo não foi aberto). A suíte estrita completa fica com o Supervisor.
- **Não verificado:** o fluxo com o responsável numa planilha real (Excel pt-BR, LibreOffice); uma amostra de campanha real; o juiz real. Uma campanha `--scripted` grava os julgamentos num banco temporário que se perde, então só a campanha real do QA, no banco do runtime, pode ser importada.

## Status

```text
implementada pelo Developer (2026-11-04); aguardando a revisão independente. Critérios de conclusão não marcados: a marcação é do Supervisor depois da revisão e do QA. O CSV real e a calibração do responsável dependem da campanha `v080-qa`.
```
