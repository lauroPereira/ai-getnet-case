---
id: KB-DEMO-ENABLEMENT-001
version: 0.1.1
source_kind: simulated_internal
environment: demo
domain: enablement
---

# Habilitação de bandeiras e produtos

Documento operacional fictício, válido somente na demonstração.

> Disponibilidade nesta versão: as consultas especializadas deste procedimento ainda não estão habilitadas no assistente. Explique o conceito com fontes oficiais e ofereça encaminhamento para análise.

## Evidências necessárias

get_contract_snapshot identifica os produtos do cliente. get_enablement_requests consulta pedidos e workflow pelo assunto ou identificador autorizado. get_device_status é pertinente quando a habilitação consta ativa no backend, mas o problema envolve a disponibilidade em um equipamento.

## Estados e interpretação

O workflow simulado distingue received, validating, pending, active, rejected e unknown. O pedido tem created_at, updated_at, etapa, motivo disponível e expected_completion_at quando informado pelo backend. Um prazo não informado permanece desconhecido; o modelo não cria um prazo padrão.

Recebimento de uma solicitação não comprova habilitação ativa. Habilitação ativa no workflow não comprova, sozinha, atualização do equipamento. O cliente e o recurso de cada consulta precisam corresponder ao contexto da sessão.

## Procedimento

Consultar histórico e healthcheck. Identificar pedido existente antes de abrir um novo caso. Recuperar o status e explicar etapa e próxima ação sustentadas pelo retorno. Se estiver active e houver falha no terminal, consultar o dispositivo e seguir o procedimento técnico correspondente.

Em rejeição ou inconsistência, comunicar somente o motivo disponível e preparar análise com as referências. Em pendência, preservar protocolo e prazo retornado, se existir. A criação de solicitação ou alteração da habilitação não é uma operação deste procedimento.

## Evidência de resultado

Uma pergunta sobre status pode ser esclarecida com o registro correspondente. Uma reclamação de impossibilidade de vender continua pendente enquanto não houver evidência adequada de funcionamento. Evitar duplicar um caso aberto sobre o mesmo pedido.
