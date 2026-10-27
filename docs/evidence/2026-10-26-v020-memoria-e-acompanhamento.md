# Evidência: memória, estado do caso e acompanhamento técnico (v0.2.0)

Tarefas: [16](../tasks/16-conversas-e-historico-curto.md), [17](../tasks/17-estado-e-evidencia-de-resolucao.md) e [18](../tasks/18-acompanhamento-tecnico-dois-ciclos.md). Data: 2026-10-26.

## Verificação automatizada (sem rede, sem custo)

`tests/integration/test_conversations.py` e `tests/unit/test_case_states.py` (18 testes, modelo programado):

- continuação com histórico de 2 turnos no Router e prefixo reaproveitado (sem nova consulta de histórico ou healthcheck);
- prefixo refeito quando o assunto muda e quando passa de 30 minutos;
- `conversation_id` de outro cliente recusado com 404 `conversation_not_found`; id novo fornecido pelo cliente aceito;
- "voltou a funcionar" resolve com `customer_confirmed` e marca as tentativas como `worked`; "obrigado" não resolve; confirmação sem histórico não resolve;
- dois ciclos técnicos sem repetir passo e encaminhamento `technical_cycles_exhausted` com as tentativas no pacote; sucesso no segundo ciclo; pedido de atendente no meio do ciclo;
- caso já encaminhado reaproveita o mesmo protocolo, sem nova chamada ao Customer Support;
- transições inválidas da máquina de estados recusadas.

## Verificação real (modelo `gpt-6-luna`)

| Conversa | Turnos | Resultado |
| --- | --- | --- |
| Maquininha sem conexão, falha persistente (PT) | 3 | Passos oficiais no 1º turno; no 2º, sem passos novos compatíveis, encaminhamento; no 3º, mesmo protocolo e caso `handoff` |
| Maquininha sem conexão, resolvida (EN) | 2 | "It works now, thanks!" → rota `acknowledgement`, caso `resolved` com `customer_confirmed`, tentativas `worked` |
| Crediário e agradecimento (PT) | 2 | "Obrigado" → `acknowledgement`, caso continua `awaiting_customer` |

Nenhuma violação na guarda de saída. Custo: US$0,0064 nas duas rodadas.

## Defeitos encontrados e corrigidos

- Uma nova mensagem numa conversa já encaminhada criava outro protocolo. Correção: o encaminhamento é único por conversa (migração 0004 com `conversation_id` em `handoff_cases`) e uma nova falha relatada vai direto ao caso existente.
- Sem passos novos, o suporte pedia ao lojista dados que as ferramentas já tinham. Correção: `support` v5.

## Contrato

- `route` ganhou o valor `acknowledgement` (reação a uma resposta anterior, sem pedido novo).
- `resolution.evidence` passa a ser `customer_confirmed` ou `tool_verified` quando o caso é resolvido.
- `POST /messages` responde 404 `conversation_not_found` para conversa de outro cliente.
