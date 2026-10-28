# Tarefa: validação e aceite da v0.6.0

## Objetivo

Revisar e validar o candidato fixado contra os dez itens de aceite da v0.6.0, com QA real pequeno e contabilizado.

## Especificação relacionada

[Spec v0.6.0, critérios de aceitação](../specs/fechamento-v060.md#critérios-de-aceitação), [história v1](../historias/fechamento-v060.md) e [plano](../specs/fechamento-v060-plano.md) (QA, orçamento, Docker e delegação).

## Pré-condições

Tarefas 54 a 58 concluídas e passagem do Developer entregue. Candidato fixado pelo Supervisor (hashes dos dois repositórios). Ledgers reconciliados em modo somente leitura antes da rodada.

## Arquivos prováveis

`docs/evidence/v060-candidato-rN.json`, `v060-reviewer.md`, `v060-qa.md`, `v060-qa-preparacao.md`, `v060-resultado.md`; controle `.pytest_cache/v060-qa-control/`.

## Passos

1. Reviewer em contexto novo: implementação, requisitos e riscos contra spec, plano, contratos e triagem; sem conclusões do Developer.
2. Correções voltam ao mesmo Developer; novo candidato e revisão do delta.
3. QA monta uma vez a campanha `v060-qa` (teto fixo US$0,50, combinada com o primário) e percorre a história pela interface: atendimento, recuperação, toggle real, perfis, comparação, D, avaliação sob demanda, administração e permissões.
4. Regressão real limitada (40 casos + 4 conversas) e reuso de evidências anteriores que continuam válidas.
5. Docker: stack empacotada com smoke real pequeno; delta do ledger do volume somado à campanha.
6. Acesso externo com o responsável, ou impedimento concreto registrado.
7. Resultado central em `v060-resultado.md`, com custos reconciliados.

## Critérios de conclusão

- [ ] Os dez itens de aceite têm evidência ou bloqueio concreto registrado.
- [ ] Gasto da campanha ≤ US$0,50, sem reset, com zero reservas abertas no fim.
- [ ] Sem commit, push, merge, tag ou abertura de porta sem autorização própria.

## Validação

Reviewer independente apto nas rodadas 1–5 ([parecer](../evidence/v060-reviewer.md)). QA real ([relatório](../evidence/v060-qa.md)): rodada 1 no r3 reprovou o item 3 (P1-QA-01, toggle JEV), corrigido pela [tarefa 61](61-correcoes-qa-v060-r1.md); rodada 2 no r5 apta nos dez itens, com acesso de outra rede pendente. Campanha `v060-qa` US$0,08800487 de US$0,50, zero reservas abertas. Consolidação em [v060-resultado.md](../evidence/v060-resultado.md).

## Status

```text
concluída; teste de outra rede pendente com o responsável
```
