# Tarefa: o caso do assistente guarda o `ticket_id` do ticketing

## Objetivo

Depois do primeiro evento aceito do ticketing, `GET /v1/handoffs` e `GET /v1/handoffs/{id}` mostram o `ticket_id` do ticket que trabalha o caso.

## Especificação relacionada

[Spec v0.7.0](../specs/identidade-hitl-v070.md), "Contrato entre os times / Serviço de ticketing"; [tarefa 66](66-webhooks-assinados-ticketing.md), passo 3 ("`ticket_id` gravado no caso"). Origem: observação O-8 da validação real da v0.7.0 ([v070-qa.md](../evidence/v070-qa.md)).

## Pré-condições

v0.7.0 integrada. Feita no começo da v0.8.0, antes da tarefa 69; nenhum critério de aceite da v0.7.0 depende do campo.

## Arquivos prováveis

`src/merchant_assistant/api/integrations.py` (a gravação existe na linha do `UPDATE handoff_cases SET ticket_id=…`, mas o valor não aparece no fluxo real), testes de integração com o ticketing real.

## Passos

1. Reproduzir com o ticketing real em processo: caso encaminhado, `ticket.assigned` aceito, `GET /v1/handoffs/{id}` com `ticket_id` nulo.
2. Achar por que a gravação não persiste ou não é alcançada (por exemplo, retorno antes da linha, outro caminho de aceite ou leitura de outra conexão) e corrigir sem mudar o contrato.
3. Teste que falha antes da correção: depois do primeiro evento aceito (`ticket.assigned`, `ticket.action` ou `ticket.solved`), o caso tem o `ticket_id`; recusa não grava.

## Critérios de conclusão

- [x] Reprodução registrada e teste que falhava antes da correção. *Defeito não reproduzido; o teste falha numa cópia sem a gravação.*
- [x] `ticket_id` visível na fila e no detalhe depois do primeiro evento aceito; recusa não grava.
- [x] Suíte estrita com código 0; nenhuma chamada paga.

## Resultado

O `ticket_id` já é gravado no primeiro evento aceito do ticketing, como a tarefa 66 define; nenhum código mudou. `tests/integration/test_v080_ticket_id.py` (5 testes) cobre fila, detalhe e recusa sem gravação, e falha numa cópia sem a gravação. No banco da validação real, 4 de 5 casos tinham o `ticket_id`; o quinto foi trabalhado só pela CLI. Evidência: [resultado da v0.7.0](../evidence/v070-resultado.md).

## Status

```text
concluída (v0.8.0)
```
