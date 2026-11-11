# Tarefa: Escalation Agent

## Objetivo

Implementar o quarto agente, que prepara e persiste o pacote de encaminhamento humano simulado de forma idempotente.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RF-22, RF-23, CA-10, UC-14.

## Pré-condições

- Tarefas 08 e 11 concluídas.

## Arquivos prováveis

- `src/merchant_assistant/agents/escalation.py`, `prompts/escalation.v1.md`
- `tests/integration/test_escalation.py`

## Passos

1. Gatilhos: pedido explícito, evidência insuficiente, divergência sem autoridade, falha de ferramenta essencial e limite de tentativas.
2. Resumo gerado pelo modelo e validado contra o contrato do pacote.
3. Persistência em `handoff_cases` com chave de idempotência derivada da conversa, da requisição e do motivo.
4. Protocolo com prefixo de simulação; a resposta ao lojista não promete contato real.
5. Funcionar mesmo quando o prefixo de suporte falhar.

## Critérios de conclusão

- [x] Repetir a mesma requisição não cria um segundo caso.
- [x] O pacote tem todos os campos de RF-22.
- [x] Falha de ferramentas não impede o encaminhamento.

## Resultado

Escalation Agent com pacote de encaminhamento idempotente em `handoff_cases`, inclusive quando o prefixo de suporte falha. 110 testes determinísticos sem rede e sem custo (`tests/integration/test_use_cases.py` e `tests/unit/`) e execução real dos 10 exemplos em 2026-10-26. Evidência: [execução real](../evidence/2026-10-26-execucao-real-desenvolvimento.md).

## Status

```text
concluída (v0.1.0)
```
