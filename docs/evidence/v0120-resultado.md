# Resultado da v0.12.0

## Capacidades

- Conversas longas guardam um resumo rolante e fatos consultáveis (valores, datas, protocolos e status) vindos das ferramentas, nunca do texto do modelo; a guarda de saída aceita esses fatos como evidência.
- Quando o histórico está incompleto, o assistente avisa e continua com cautela.
- A comparação pareada mede o atendimento com e sem replanejamento (`--replan off|on`), com as decisões de origem `model` separadas das de regra.
- O cancelamento de venda é um pedido idempotente que só é executado depois de confirmação explícita do lojista; recusa e falta de resposta encerram o pedido.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte estrita | 2.698 testes aprovados, sem falhas nem testes pulados; Ruff, links e caminhos pessoais limpos |
| Conversa longa | 27 turnos com fatos exatos, aviso e recuperação do contexto incompleto |
| Cancelamento | Confirmação, idempotência, recusa, expiração e isolamento entre lojistas |
| Replanejamento | 4 casos pareados: 0 decisões de origem `model` com `REPLAN=off` e 8 com `REPLAN=on` |
| Arquivos selados | CSVs e prompts da v0.11.0 idênticos byte a byte; holdouts conferidos pelo hash |

Gasto da campanha real: US$0,471.

Validação momento a momento e revisão independente: [v0120-validacao.md](v0120-validacao.md).

A decisão está registrada na [ADR 0024](../architecture/decisions/0024-desenho-da-orquestracao.md).
