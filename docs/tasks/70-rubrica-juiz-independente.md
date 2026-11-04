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

A preencher pelo Developer.

## Status

```text
pendente (spec aprovada; começa depois do merge da v0.7.0)
```
