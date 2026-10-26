# Tarefa: Router e guardrails

## Objetivo

Implementar o Router com decisão estruturada e os guardrails de entrada e de saída.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RF-04 a RF-08, CA-09, UC-12, UC-16, UC-18.

## Pré-condições

- Tarefa 08 concluída.

## Arquivos prováveis

- `src/merchant_assistant/agents/router.py`, `prompts/router.v1.md`
- `src/merchant_assistant/guardrails/` (entrada, mascaramento, saída)
- `tests/unit/guardrails/`, `tests/integration/test_router.py`

## Passos

1. Pré-checagem determinística antes do modelo: mascarar números de cartão (com verificação de Luhn), CPF, chaves e tokens; detectar padrões comuns de injeção.
2. Prompt do Router com exemplos curtos das sete rotas em português e inglês, incluindo a fronteira entre pergunta geral inofensiva e pedido a recusar.
3. Validar a decisão; decisão inválida leva a `clarify` registrado.
4. Recusa com orientação útil, no idioma da mensagem.
5. Verificação de saída: extrair valores monetários e datas da resposta e conferir com os fatos estruturados do estado.
6. Testes determinísticos com modelo programado e casos adversariais.

## Critérios de conclusão

- [ ] UC-12, UC-16 e UC-18 com o resultado esperado em testes determinísticos.
- [ ] Logs sem dados sensíveis.
- [ ] Resposta com valor não suportado pelos fatos é bloqueada.

## Validação

A preencher na execução.

## Status

```text
pendente
```
