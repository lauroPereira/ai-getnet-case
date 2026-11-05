# Tarefa 82 — Fechamento da v0.9.0

## Objetivo

Fixar o candidato, revisar, rodar o QA real (experimento do juiz e medição de retrieval), registrar as decisões e fechar README, CHANGELOG e ADRs para a entrega de 2026-11-06 às 08h.

## Especificação relacionada

[Juiz Claude e retrieval híbrido v0.9.0](../specs/juiz-retrieval-v090.md): CA-52, CA-56, D2, D5, D6, D7. História: [juiz-retrieval-v090.md](../historias/juiz-retrieval-v090.md).

## Pré-condições

Tarefas 79 a 81 com parecer apto do Reviewer (79 pode ir ao QA antes de 80 e 81, momentos 1 a 3 da história). Cap Anthropic confirmado pelo responsável. Runtime `.pytest_cache/qa-v080-r1/runtime` intacto.

## Passos

1. Suíte estrita no candidato; manifesto `docs/evidence/v090-candidato-rN.json` (SHA, árvore, sha256 por arquivo, lacre do holdout de retrieval).
2. Revisão independente em contexto frio; correções como rodadas das tarefas.
3. QA, momentos 1 a 3: ledger Anthropic em `data/runtime/anthropic`, campanha `v090-juiz-opus` com o cap; sonda de 3; 72 ou 24 julgamentos; `eval-calibrate --import --judge`; relatório `docs/evidence/v090-juiz-opus.md`; decisão por D2 registrada pelo Supervisor.
4. QA, momentos 4 a 7: `eval-retrieval` real em `dev` nos três modos; holdout por último, uma vez por modo; decisão D7 registrada; ledger OpenAI dentro do plano.
5. ADR 0020 (retrieval híbrido e holdout de retrieval) e ADR 0021 (juiz: modelo padrão e régua do CA-51 como piso determinístico + juiz).
6. README: linhas da "Resposta ao feedback" para RAG e Evaluation atualizadas; "Próximos passos" sem os itens entregues; CHANGELOG 0.9.0 com validação, limitações e como voltar à v0.8.0 (`RETRIEVAL_MODE=dense`, `JUDGE_*` padrão).
7. Relatório do Supervisor em `docs/relatorios/`; merge local na `main`; tag `v0.9.0` e push pelo responsável.

## Critérios de conclusão

- CA-56 e CA-52 com prova real registrada, ou a parte não medida declarada no README como não medida.
- README e CHANGELOG coerentes com o que foi medido; nenhum caminho pessoal.
- Ledgers batem; o Anthropic separado do projeto.

## Validação

(Preenchida pelo Supervisor.)

## Status

Pendente. Aberta pelo Supervisor em 2026-11-05.
