# Tarefa: rubrica `judge.v3`, juiz independente e repetições

## Objetivo

A avaliação real passa a usar quatro critérios com evidência e um veredito de afirmação sem suporte, um juiz de outro provedor ou modelo registrado em cada avaliação, e `eval --repeat N` com média, dispersão e concordância.

## Especificação relacionada

[Spec v0.8.0](../specs/orquestracao-avaliacao-v080.md) — D9, D11, D12, D13, D14; [spec 0.2](../specs/evolucao-pos-feedback.md) RF-89, RF-90, CA-50; [plano](../specs/evolucao-pos-feedback-plano.md) decisões técnicas 12 e 13 e "Modelo de dados" (migração 0011).

## Pré-condições

Spec v0.8.0 aprovada; a branch `codex/v0.8.0-avaliacao` (worktree `time-b`, `.venv` próprio) atualizada com a `main` que contém a v0.7.0, com o lacre do holdout reconferido depois do merge. Time B: não editar `orchestration/`, `agents/`, `api/`, `evaluation/scripted_policy.py`, `data/scenarios/catalog.json` nem `prompts/` além de `prompts/judge.v3.md` (D18). Não abrir o conteúdo de `tests/scenarios/holdout_v080.jsonl`.

## Arquivos prováveis

`prompts/judge.v3.md` (novo), `evaluation/runner.py`, `evaluation/aggregate.py` (novo, se ajudar), `data/migrations.py` (0011), `config.py` (`EVALUATOR_MODEL`, provedor), `llm/` (cliente do segundo provedor, se faltar), `cli.py` (`eval --repeat`, `--split holdout_v080`, só por acréscimo), testes.

## Passos

1. Migração 0011 (D13), reversível com dados, com teste de subida e descida.
2. `judge.v3` (D9): quatro critérios 1–5 com justificativa e `unsupported_claim`; entrada com o conteúdo mascarado das evidências, até 6 000 caracteres, truncamento registrado. `judge.v2` continua carregável.
3. Juiz independente (D11): `EVALUATOR_MODEL` e provedor configuráveis, diferentes do agente; provedor e modelo gravados em cada avaliação; sem chave do provedor configurado, a avaliação paga recusa com mensagem clara (sem trocar de juiz por conta própria).
4. Repetições sem misturar variações (D12): `eval --repeat N` repete o agente (juiz uma vez por resposta); `eval --judge-repeat N` repete só o juiz sobre respostas já gravadas. Agregação de cada lado por critério, rota e split com média, desvio, concordância exata e ±1; relatório JSON e Markdown em `docs/evidence/`.
5. Substituto programado do `judge.v3` num módulo novo do Time B; `evaluation/scripted_policy.py` é do Time A neste período (D18).
6. `--split holdout_v080` reportado à parte (D14).

## Critérios de conclusão

- [ ] Agregação e concordância conferidas com números fixos em teste.
- [ ] `judge.v3` com modelo programado devolve os quatro critérios e o veredito; evidência longa é truncada e o truncamento aparece.
- [ ] Juiz igual ao agente ou sem chave → recusa clara antes de qualquer chamada.
- [ ] Migração 0011 sobe e desce com dados sintéticos.
- [ ] Suíte estrita com código 0 no worktree; nenhuma chamada paga; lacre do holdout verde.

## Validação

Developer, rodada 1 (2026-11-04), worktree do Time B, branch `codex/v0.8.0-avaliacao`, base `8f2baa6` (a `main` com a v0.7.0). Commits: `75edaf2` (migração), `dbb9d5b` (`judge.v3`, evidência e juiz independente), `8897809` (repetições, agregação e caminho executado), `c974e2c` (afirmações sem suporte listadas). Passagem em [v080-developer.md](../evidence/v080-developer.md), seção "Tarefa 70".

- **Migração 0011 (D13):** `run_evaluations.scores`, `repetition`, `unsupported_claim` e a tabela `calibrations`. `rubric_version` e o provedor/modelo do avaliador (`evaluator`) já existiam desde a 0008. A descida mantém todas as avaliações (o `result` guarda o julgamento inteiro) e recusa enquanto houver nota humana em `calibrations`. `tests/unit/data/test_migrations.py` (22 testes, 5 novos): subida e descida com dados sintéticos, defaults das linhas antigas, `CHECK` do veredito, avaliador único por amostra, recusa da descida sem alterar nada e pelo `migrate` da CLI.
- **`judge.v3` (D9):** `prompts/judge.v3.md`; quatro critérios 1-5 com justificativa e `unsupported_claim`. Evidência mascarada (trechos citados e resultados de ferramenta), até 6 000 caracteres: os itens longos dividem o limite e os curtos ficam inteiros; o registro de truncamento (`limit_chars`, `original_chars`, `kept_chars`, `items_cut`, `truncated`) vai na entrada do juiz e na linha do relatório. `judge.v2` carrega por `load_prompt(dir, "judge", "2")` e a avaliação sob demanda de `/v1` continua nele.
- **Juiz independente (D11):** `EVALUATOR_PROVIDER`/`EVALUATOR_MODEL`, padrão `deepseek`/`deepseek-flash` (antes `openai`/`gpt-6-luna`, igual ao agente); cliente DeepSeek do projeto (`OpenAILLM` com `deepseek_client`). Recusa antes de construir qualquer cliente: par igual ao do agente, sem chave, sem preço ou provedor sem saída estruturada. Provedor, modelo e independência vão em cada julgamento e em `run_evaluations.evaluator`.
- **Repetições (D12):** `eval --repeat N` repete o agente e julga cada resposta uma vez; `eval --judge-repeat N --answers-from <relatório>` julga N vezes as respostas da primeira execução sem rodar o agente; as duas opções juntas são recusadas. Agregação (`evaluation/aggregate.py`) com média, desvio, concordância exata e ±1 por critério, rota e split; relatório JSON e Markdown, com a ressalva de amostra pequena (D19).
- **D16:** `executed_path` em cada linha, derivado de `agents`; `route_ok` inalterado. **D14:** `--split holdout_v080` carrega o arquivo só quando pedido, fora do `all` e sem as conversas de dev.
- **Testes novos (sem chamada paga, sem rede):** `tests/unit/evaluation/` (34 testes: `judge.v3`, evidência, truncamento, independência, persistência, agregação com números fixos) e `tests/integration/test_eval_campaign.py` (14 testes: caminho executado, evidência por resposta, `--repeat`, `--judge-repeat`, split sintético, recusas na CLI).
- **Contagens:** `tests/unit` 294 aprovados em 84 s; `tests/integration`, 24 arquivos em quatro grupos e um pytest por vez, 407 aprovados (80, 88, 97 e 142), sem falha; total 701. Depois só mudou o teto de saída do juiz (400 tokens): `tests/unit/evaluation`, `test_eval_campaign.py` e `test_holdout_v080.py` reexecutados, 56 aprovados. ruff (`check src tests`) sem achados. Lacre do holdout: `tests/scenarios/holdout_v080.jsonl` com SHA-256 `91aa5158…4f1bac`, inalterado; `test_holdout_v080.py` com 8 testes verdes.
- **Correção do que o merge da v0.7.0 quebrou:** `test_tool_backed_amounts_come_from_the_calls_of_each_case` (72a) montava `CustomerContext(MAIN_CUSTOMER, True)` sem escopos e falhava fechado; agora usa `CustomerContext.for_principal(Principal.merchant(...))`. O holdout e o lacre não foram tocados.
- A suíte estrita completa (`lint_and_tests.py --strict`) fica com o Supervisor. Nenhum teste usou rede ou chave; `.env` não foi lido (não existe no worktree).

## Status

```text
implementada pelo Developer na rodada 1 (2026-11-04); aguardando revisão independente. Critérios de conclusão não marcados: a marcação é do Supervisor depois da revisão e do QA.
```
