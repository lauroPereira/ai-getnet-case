# Tarefa 109 — Tickets do lojista no Customer Support

## Objetivo

Em qualquer conversa, o lojista pergunta pelos seus tickets de atendimento humano e o assistente responde com protocolo, estado e, quando houver, a resposta da atendente.

## Especificação relacionada

[v1.1.0](../specs/tickets-retomada-v110.md): D1, CA-76, RF-130.

## Pré-condições

Nenhuma chamada paga: testes com o modelo roteirizado; conferência com modelo real na validação da versão.

## Arquivos prováveis

`src/merchant_assistant/tools/domain.py` e `tools/registry.py` (ferramenta e lista do suporte), `prompts/support.v11.md` (e a referência da versão em uso), cenários e testes (`tests/`), contrato da ferramenta na documentação de ferramentas do README, se houver tabela.

## Passos

1. Ferramenta `get_handoff_cases` (escopo `SUPPORT_READ`, especialista do `customer_support`): lê `handoff_cases` do lojista do `ToolEnv`, mais recentes primeiro, no máximo 5; argumento opcional `protocol` (completo ou final com pelo menos 4 caracteres alfanuméricos, sem diferenciar maiúsculas; valor fora disso é erro de argumento). Por caso: `protocol`, `state` (estado da fila), `reason`, `opened_at`, `claimed_at`, `answered_at`, `closed_at` e `operator_reply` (texto da resposta da atendente, quando houver, lido de onde a resposta já é guardada). Sem identificador de operador, sem caso de outro lojista. Resultado com `source` e `observed_at` como as demais.
2. Auditoria e escopo iguais às outras ferramentas de leitura (linha de auditoria por chamada; outro lojista recebe vazio ou `FORBIDDEN_RESOURCE`, sem dado).
3. `prompts/support.v11.md`: quando o lojista pergunta por ticket, protocolo, atendimento humano ou "alguma novidade" sobre um caso, consultar `get_handoff_cases` antes de dizer que não há; relatar estado e resposta da atendente com as palavras dela; não inventar prazo. A versão em uso passa a ser a 11.
4. Router: conferir com o modelo roteirizado e pelos cenários que pedidos de status de ticket ou protocolo vão a `support`. Se o prompt do Router precisar mudar, registre no Resultado e crie a versão nova; não mude se não precisar.
5. Os valores relatados vêm do resultado da ferramenta e passam pela guarda de saída como evidência (conferir com um teste).
6. Testes: argumento e filtro por final do protocolo; isolamento entre lojistas; auditoria; caso aberto, assumido, respondido (com `operator_reply`) e encerrado; conversa nova que pergunta pelo ticket aberto em outra conversa (roteirizado, fim a fim pela API).

## Critérios de conclusão

- A ferramenta aparece na lista do suporte, é auditada e nunca devolve caso de outro lojista.
- Um teste fim a fim roteirizado mostra uma conversa nova recebendo protocolo, estado e a resposta da atendente de um caso aberto em outra conversa.
- Suíte estrita verde.

## Resultado

`get_handoff_cases` na lista do suporte e do MCP: até 5 casos, filtro pelo protocolo completo ou pelo final, uma linha de auditoria por chamada, nenhum caso de outro lojista. `support.v11` em uso; `router.v7` sem mudança.
`test_v110_tickets.py` com 34 testes, incluindo o fluxo fim a fim pela API; suíte estrita com 3.015 aprovados.
Com modelo real, três formas de perguntar pelo ticket foram atendidas pelo suporte com a ferramenta. Evidência: [resultado da v1.1.0](../evidence/v110-resultado.md).

## Status

```text
concluída (v1.1.0)
```
