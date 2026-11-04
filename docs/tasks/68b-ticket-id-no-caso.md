# Tarefa: o caso do assistente guarda o `ticket_id` do ticketing

## Objetivo

Depois do primeiro evento aceito do ticketing, `GET /v1/handoffs` e `GET /v1/handoffs/{id}` mostram o `ticket_id` do ticket que trabalha o caso.

## Especificação relacionada

[Spec v0.7.0](../specs/identidade-hitl-v070.md), "Contrato entre os times / Serviço de ticketing"; [tarefa 66](66-webhooks-assinados-ticketing.md), passo 3 ("`ticket_id` gravado no caso"). Defeito observado no QA real da v0.7.0 ([v070-qa.md](../evidence/v070-qa.md), observação O-8).

## Pré-condições

v0.7.0 integrada. Feita no começo da v0.8.0, pelo Time A, antes da tarefa 69 (dívida da v0.7.0; o Supervisor decidiu por padrão não reabrir o candidato da v0.7.0, porque nenhum critério de aceite depende do campo).

## Arquivos prováveis

`src/merchant_assistant/api/integrations.py` (a gravação existe na linha do `UPDATE handoff_cases SET ticket_id=…`, mas o valor não aparece no fluxo real), testes de integração com o ticketing real.

## Passos

1. Reproduzir com o ticketing real em processo: caso encaminhado, `ticket.assigned` aceito, `GET /v1/handoffs/{id}` com `ticket_id` nulo.
2. Achar por que a gravação não persiste ou não é alcançada (por exemplo, retorno antes da linha, outro caminho de aceite ou leitura de outra conexão) e corrigir sem mudar o contrato.
3. Teste que falha antes da correção: depois do primeiro evento aceito (`ticket.assigned`, `ticket.action` ou `ticket.solved`), o caso tem o `ticket_id`; recusa não grava.

## Critérios de conclusão

- [ ] Reprodução registrada e teste que falhava antes da correção.
- [ ] `ticket_id` visível na fila e no detalhe depois do primeiro evento aceito; recusa não grava.
- [ ] Suíte estrita com código 0; nenhuma chamada paga.

## Validação

Developer (Time A), 2026-11-04, branch `codex/v0.8.0-replan`. Sem chamada paga e sem rede.

**Reprodução: o defeito não se reproduz, e a observação O-8 parece uma leitura incompleta do QA.**

- **No processo (ticketing real, assistente, receptor do lojista, via `AppTransport`):** `test_case_becomes_a_ticket_worked_on_the_ticketing_and_closed[*]` da v0.7.0 já exige `ticket_id` no detalhe depois de `ticket.assigned` e passa na base `5134eff`. Teste novo: fila (`GET /v1/handoffs`) e detalhe mostram o `ticket_id` depois do primeiro evento aceito, seja `ticket.assigned`, `ticket.action` ou `ticket.solved`.
- **Com soquetes reais (uvicorn em threads, assistente + ticketing + receptor, loopback):** `assign` → `delivered`/`accepted` → `GET /v1/handoffs` com `claimed_by=op_ana` e `ticket_id=tkt_9ea3eafb95c3`, igual ao ticket. Roteiro exploratório fora do repositório.
- **No banco do próprio QA da v0.7.0** (cópia somente leitura de `merchant.sqlite3` do runtime do QA): 4 dos 5 casos têm `ticket_id` gravado (inclusive `hc_154e13748dc742da` = `tkt_c6d9b62237d4`, o ticket do momento 9 da história) e todos têm `ticket.assigned` aceito em `webhook_inbox`. O único `null` (`hc_bd1b4d4e05924eb9`) não tem nenhum evento do ticketing: foi trabalhado direto por `operator:op_ana` (`handoff.approve` sem `on_behalf_of`), o caso E da O-4. Em `v070-qa-historia.md` a única amostra com `ticket_id: null` é a do momento 6, antes de qualquer evento (nulo esperado).
- **Causa:** nenhuma no código. A gravação está em `integrations.py::_apply`, depois do evento aceito, com `WHERE ticket_id IS NULL`; recusa (`4xx`) sai antes. Nenhum código mudou.
- **Lacuna, não defeito:** entre `handoff.created` e o primeiro evento do operador o assistente não conhece o ticket (a resposta do ticketing a `handoff.created` traz `ticket_id`, mas o assistente não a grava). É o que a spec da 66 definiu ("do primeiro evento aceito"); gravar na criação seria mudança de comportamento, não correção, e fica como sugestão ao Supervisor.

**Teste novo** `tests/integration/test_v080_ticket_id.py` (5 testes, passam): `[assigned|action|solved]` (nulo antes, `ticket_id` na fila e no detalhe e no banco depois), ciclo inteiro (assign → approve → solve mantém o primeiro), e recusa que não grava (operador desconhecido `422`, payload sem `ticket_id` `400`, `claimed_by_other` `409`; depois o evento do dono grava o seu e um evento posterior de outro ticket não sobrescreve).

**"Falhava antes":** como não há defeito, o teste não falha na base. Prova de que não é vazio: numa cópia da base fora do repositório (`git archive` + remoção do `UPDATE handoff_cases SET ticket_id`), os 5 testes falham; na base, os 5 passam.

```text
.venv/Scripts/python.exe -m pytest -p no:cacheprovider --basetemp .pytest_cache/t68b-dev-20261104e tests/integration/test_v080_ticket_id.py -q   -> 5 passed
cópia mutada (sem o UPDATE)                                                                                             -> 5 failed
.venv/Scripts/python.exe -m ruff check tests/integration/test_v080_ticket_id.py                                         -> All checks passed
```

Suíte estrita completa fica com o Supervisor.

## Status

```text
feito pelo Developer em 2026-11-04 (sem alteração de código; defeito não reproduzido); aguarda revisão
```
