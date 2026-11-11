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
| Replanejamento | Ablação com modelo real, uma execução por lado. Desenvolvimento, 44 pares: aprovados +0,045 com replanejamento (IC 95% −0,045 a +0,136). Holdout, 25 pares: −0,080 (−0,240 a +0,080). Decisões pelo modelo: 4 de 76. Relatórios: [desenvolvimento](v0120-comparacao.md), [holdout](v0120-comparacao-holdout.md); revisão na [ADR 0024](../architecture/decisions/0024-desenho-da-orquestracao.md) |
| Arquivos selados | CSVs e prompts da v0.11.0 idênticos byte a byte; holdouts conferidos pelo hash |

Gasto da campanha real: US$0,471.

Validação momento a momento e revisão independente: [v0120-validacao.md](v0120-validacao.md).

A decisão está registrada na [ADR 0024](../architecture/decisions/0024-desenho-da-orquestracao.md).
