---
id: KB-DEMO-SALE-CANCELLATION-001
version: 0.1.1
source_kind: simulated_internal
environment: demo
domain: sale_cancellation
---

# Cancelamento de venda

Documento operacional fictício, válido somente na demonstração. SalesMock é um nome genérico de backend simulado e não identifica o sistema real responsável na empresa.

> Disponibilidade nesta versão: as consultas especializadas deste procedimento ainda não estão habilitadas no assistente. Explique o conceito com fontes oficiais e ofereça encaminhamento para análise.

## Identificação da intenção

Cancelar uma transação é diferente de encerrar contrato, descredenciar estabelecimento ou devolver equipamento. Uma mensagem ambígua pede esclarecimento antes de consultar ou propor uma operação diferente da pretendida.

## Evidências e procedimento

get_sale_cancellation_context retorna a venda, sua situação, pedidos de cancelamento existentes, elegibilidade da simulação e requisitos disponíveis. Após histórico e healthcheck, localizar a venda e conferir se já existe um pedido ou conclusão para evitar duplicação.

Uma consulta não executa o cancelamento. Nesta versão, o atendimento explica status, elegibilidade e próxima ação ou prepara encaminhamento. A execução é uma evolução com preparação, confirmação explícita, validação no backend e idempotência; não pertence ao catálogo inicial de operações disponíveis.

## Resultado

Só afirmar que houve cancelamento se o sistema retornar esse estado para a venda correta. Pedido recebido não confirma conclusão nem crédito ao comprador. Um pedido de encerramento contratual segue o procedimento de dúvidas, retenção e passagem, respeitando a intenção do lojista.
