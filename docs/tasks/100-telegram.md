# Tarefa 100 — Operador no Telegram

## Objetivo

O operador recebe o caso encaminhado no Telegram e o resolve de lá; a resposta chega ao lojista na mesma conversa.

## Especificação relacionada

[v0.13.0](../specs/identidade-operacao-v0130.md): D3, CA-69. Plano: [decisão 16](../specs/roadmap-v0110-v100-plano.md). ADR 0018.

## Pré-condições

Tarefas 97 e 99 concluídas; o cliente de serviço `telegram-operator` dispõe do papel `operator` e do escopo de handoff necessário.

## Arquivos prováveis

`integrations/telegram.py` (novo), `docker-compose.yml` (serviço `telegram`, perfil `telegram`), `.env.example` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_OPERATOR_CHAT_ID`, vazios), configuração do destino de webhook, testes.

## Passos

1. Serviço que recebe `handoff.created` como destino de webhook assinado e envia ao chat do operador o resumo do caso já mascarado, com o protocolo.
2. Long polling dos comandos `/claim`, `/approve`, `/reply <texto>`, `/reject <instrução>`; cada um vira chamada a `/v1/handoffs/{id}/claim|actions` com token de um principal `operator` de serviço (`client_credentials`), com chave de idempotência derivada do `update_id`.
3. Só o chat configurado é aceito; comandos de outro chat são ignorados.
4. Desligado sem `TELEGRAM_BOT_TOKEN`.
5. Testes com Bot API falsa em processo: caso enviado; cada comando; idempotência por `update_id`; chat estranho ignorado; resposta do operador chega ao lojista como `via=operator`; nenhum dado de cartão sai.

## Critérios de conclusão

- CA-69 coberto por testes; desligado por padrão; suíte estrita verde.
