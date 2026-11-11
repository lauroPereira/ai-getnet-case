# Tarefa: validação e aceite da v0.6.0

## Objetivo

Revisar e validar o candidato fixado contra os dez itens de aceite da v0.6.0, com validação real pequena e contabilizada.

## Especificação relacionada

[Spec v0.6.0, critérios de aceitação](../specs/fechamento-v060.md#critérios-de-aceitação), [história v1](../historias/fechamento-v060.md) e [plano](../specs/fechamento-v060-plano.md) (validação, orçamento e Docker).

## Pré-condições

Tarefas 54 a 58 concluídas. Candidato fixado com hashes dos dois repositórios. Ledgers reconciliados em modo somente leitura antes da validação.

## Arquivos prováveis

`docs/evidence/v060-candidato-rN.json`, `v060-reviewer.md`, `v060-qa.md`, `v060-qa-preparacao.md` (na tag `v0.6.0`) e `v060-resultado.md`.

## Passos

1. Revisão independente em contexto novo: implementação, requisitos e riscos contra spec, plano, contratos e triagem, sem as conclusões do implementador.
2. Correções geram novo candidato e revisão do delta.
3. Montar uma vez a campanha `v060-qa` (teto fixo US$0,50, combinada com o primário) e percorrer a história pela interface: atendimento, recuperação, toggle real, perfis, comparação, D, avaliação sob demanda, administração e permissões.
4. Regressão real limitada (40 casos + 4 conversas) e reuso de evidências anteriores que continuam válidas.
5. Docker: stack empacotada com smoke real pequeno; delta do ledger do volume somado à campanha.
6. Acesso externo com o responsável, ou impedimento concreto registrado.
7. Resultado central em `v060-resultado.md`, com custos reconciliados.

## Critérios de conclusão

- [x] Os dez itens de aceite têm evidência ou bloqueio concreto registrado.
- [x] Gasto da campanha ≤ US$0,50, sem reset, com zero reservas abertas no fim.
- [x] Sem commit, push, merge, tag ou abertura de porta sem autorização própria.

## Resultado

Apta nos dez itens de aceite, com revisão independente e validação real; suíte estrita final: backend 349 testes, web 42. Campanha `v060-qa`: US$0,08800487 de US$0,50, zero reservas abertas. Evidência: [resultado da v0.6.0](../evidence/v060-resultado.md).

## Status

```text
concluída (v0.6.0)
```
