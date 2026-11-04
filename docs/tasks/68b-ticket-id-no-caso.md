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

A preencher pelo Developer.

## Status

```text
pendente (começo da v0.8.0, Time A, antes da 69)
```
