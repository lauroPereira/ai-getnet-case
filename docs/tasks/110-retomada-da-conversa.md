# Tarefa 110 — Lista de conversas e retomada na interface

## Objetivo

Recarregar a página e entrar de novo devolve ao lojista a última conversa, com o histórico e a resposta da atendente; ele pode começar outra.

## Especificação relacionada

[v1.1.0](../specs/tickets-retomada-v110.md): D2, CA-77, RF-131. Contrato em [api-v1.md](../contracts/api-v1.md).

## Pré-condições

Tarefa 109 concluída. Interface web (repositório `ai-getnet-case-web`) na mesma versão. Nenhuma chamada paga.

## Arquivos prováveis

Backend: `src/merchant_assistant/api/v1.py`, `conversations.py`, `docs/contracts/api-v1.md`, testes. Web: `app.py`, `src/getnet_web/api.py`, `README.md`, testes.

## Passos

1. `GET /v1/conversations` (Bearer, dono): conversas do lojista do token (mesma regra de `acting_merchant` da rota por id), por `updated_at` decrescente; `limit` de 1 a 20, padrão 5 (fora disso, `422`). Por item: `conversation_id`, `state`, `created_at`, `updated_at`, `handoff_protocol` (protocolo do caso da conversa, ou `null`) e `pending_operator_reply` (há turno da atendente ainda não entregue). Sem texto de mensagem. Principal sem lojista vinculado: `403 insufficient_scope`.
2. Contrato `api-v1.md` com a rota nova; OpenAPI com exemplo.
3. Web: cliente `list_conversations`. Depois do login de lojista ou `demo`, sem conversa no estado da sessão, buscar a lista e retomar a mais recente: `GET /v1/conversations/{id}` reconstrói o histórico (lojista, assistente e atendente, esta com a marcação `Atendente humano` que a interface já usa), guarda o `conversation_id` e mostra "Conversa retomada" com a data. Botão **Nova conversa** limpa a conversa da sessão (não apaga nada no backend). Lista vazia: comportamento atual. Falha da lista ou da conversa: aviso curto e conversa nova, sem bloquear o atendimento.
4. A aba Resultados continua listando as execuções da sessão atual.
5. README da web (comportamento ao recarregar) e testes.

## Critérios de conclusão

- Testes da rota: só conversas do dono, ordem, limite, sem texto, `403` para operador e serviço, `422` fora do limite.
- Testes da interface: depois de um novo login, a última conversa volta com o turno da atendente; **Nova conversa** começa outra; a mensagem seguinte usa o `conversation_id` retomado; lista vazia e falha não quebram a tela.
- Suítes estritas do backend e da web verdes.

## Resultado

`GET /v1/conversations` (só do dono, sem texto, `limit` de 1 a 20, padrão 5) e confirmação de exibição por `displayed_operator_message_id`; a interface retoma a última conversa depois de um novo login e oferece **Nova conversa**.
`test_v110_conversations.py` com 24 testes no backend; `test_v110_resume.py` e `test_interface.py` com 43 na interface; suítes estritas com 3.052 aprovados no backend e 202 na interface.
Com modelo real, a retomada trouxe a resposta da atendente e a pergunta seguinte recebeu resposta própria. Evidência: [resultado da v1.1.0](../evidence/v110-resultado.md).

## Status

```text
concluída (v1.1.0)
```
