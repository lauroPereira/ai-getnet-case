# Tarefa: Acompanhamento técnico em dois ciclos

## Objetivo

Conduzir problemas técnicos em até dois ciclos de orientação, sem repetir passos já tentados, e encaminhar com contexto no limite ou a pedido.

## Especificação relacionada

[Especificação principal](../specs/assistente-multiagente-lojista.md): RF-30, RF-23, CA-18. [Complementar](../specs/incrementos-pos-nucleo.md): UC-19, CA-29.

## Pré-condições

- Tarefa 17 concluída.

## Arquivos prováveis

- `src/merchant_assistant/agents/support.py`, `escalation.py`, `prompts/support.v4.md`
- `src/merchant_assistant/cases.py`
- `tests/integration/test_technical_followup.py`, `tests/scenarios/followup.jsonl`

## Passos

1. Passos de orientação recebem identificador estável a partir do procedimento recuperado; o caso registra quais foram dados e o resultado relatado.
2. O Support recebe a lista do que já foi tentado e não repete; no segundo ciclo sem sucesso, encaminha.
3. O pacote de encaminhamento inclui passos, resultados, sinais do dispositivo e a questão pendente.
4. Cenários multi-turno: sucesso no primeiro ciclo, sucesso no segundo e falha nos dois; pedido de atendente no meio do ciclo.
5. Rodada real limitada dos cenários multi-turno, com custo registrado.

## Critérios de conclusão

- [ ] "Já fiz isso e continua igual" não repete o passo (UC-19).
- [ ] No limite de dois ciclos, encaminha com o histórico completo.
- [ ] Pedido de atendente a qualquer momento encaminha sem esperar o limite.

## Validação

A preencher na execução.

## Status

```text
pendente
```
