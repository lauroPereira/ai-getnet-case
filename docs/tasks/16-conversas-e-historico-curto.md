# Tarefa: Conversas com dono e histórico curto

## Objetivo

Persistir conversas e mensagens por cliente, verificar o dono antes de ler ou gravar e entregar aos agentes um histórico curto limitado por tokens.

## Especificação relacionada

[Especificação principal](../specs/assistente-multiagente-lojista.md): RF-28. [Complementar](../specs/incrementos-pos-nucleo.md): RF-44, UC-21, CA-29.

## Pré-condições

- Tarefa 15 concluída.

## Arquivos prováveis

- `src/merchant_assistant/data/migrations/0002_conversations.py`
- `src/merchant_assistant/conversations.py` (novo)
- `src/merchant_assistant/orchestration/graph.py`, `state.py`
- `src/merchant_assistant/agents/router.py`, `support.py`, `personality.py`
- `tests/integration/test_conversations.py`

## Passos

1. Tabelas `conversations` (dono, estado, assunto, datas) e `messages` (papel, texto mascarado, tokens estimados).
2. `POST /messages` com `conversation_id`: conversa inexistente ou de outro cliente é recusada sem revelar se existe; sem `conversation_id`, cria nova.
3. Histórico curto (últimos turnos dentro de um limite de tokens) entregue ao Router, ao Support e à Personality como dado, não como instrução.
4. Prefixo de histórico e healthcheck guardado por conversa com validade; refeito quando vencido ou quando o assunto muda.
5. Testes multi-turno com o modelo programado; isolamento entre clientes.

## Critérios de conclusão

- [x] Continuação da conversa usa o histórico; outra conversa ou outro cliente não o enxergam.
- [x] `conversation_id` de outro cliente é recusado (UC-21).
- [x] O prefixo não é repetido a cada mensagem e é refeito quando necessário.

## Validação

2026-10-26: conversas e mensagens (migração 0002) com dono verificado, histórico curto de até 10 mensagens e 1.200 tokens para Router, Support e Personality, prefixo reaproveitado por 30 minutos no mesmo assunto. Testes em `tests/integration/test_conversations.py` e conversa real de 3 turnos. Ver [evidência](../evidence/2026-10-26-v020-memoria-e-acompanhamento.md). Revisão não independente.

## Status

```text
concluída
```
